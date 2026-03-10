#!/usr/bin/env python3
import os
import shutil
import sys

from bitcoin import SelectParams
from bitcoin.rpc import JSONRPCError, Proxy

from runbtcdeb import run_btcdeb_steps

SelectParams("regtest")

# Configuration constants
RPC_PORT = 18443
INITIAL_FUNDING = 5.0  # BTC
TRANSACTION_FEE = 0.0001  # BTC
MIN_BLOCK_HEIGHT = 101  # For coinbase maturity

# Environment setup
user = os.getenv("BITCOIN_RPC_USER", "rpcuser").rstrip("/")
password = os.getenv("BITCOIN_RPC_PASSWORD", "rpcpass").rstrip("/")
host = os.getenv("BITCOIN_RPC_HOST", "127.0.0.1").rstrip("/")
port = RPC_PORT

base_url = f"http://{user}:{password}@{host}:{port}"
node_conn = Proxy(service_url=base_url)


def setup_wallet(name):
    """Ensures the wallet is both created AND loaded."""
    try:
        node_conn._call("createwallet", name)
    except JSONRPCError as e:
        if e.error.get("code") == -4:
            try:
                node_conn._call("loadwallet", name)
            except JSONRPCError as load_e:
                if load_e.error.get("code") != -35:
                    raise load_e
        else:
            raise e
    return Proxy(service_url=f"{base_url}/wallet/{name}")


def run_legacy():
    btcdeb_path = shutil.which("btcdeb")
    if not btcdeb_path:
        print("Error: 'btcdeb' binary not found in PATH. Please install it first.")
        sys.exit(1)

    node_conn = setup_wallet("default")
    current_height = node_conn._call("getblockcount")
    mining_addr = node_conn._call("getnewaddress")

    while node_conn._call("getbalance") < 5.0:
        current_height = node_conn._call("getblockcount")

        if current_height < 101:
            blocks_needed = 101 - current_height
            print(
                f"Insufficient funds. Mining {blocks_needed} blocks to mature coinbase rewards..."
            )
            node_conn._call("generatetoaddress", blocks_needed, mining_addr)
        else:
            print("Insufficient funds. Mining 1 block to generate more funds...")
            node_conn._call("generatetoaddress", 1, mining_addr)

    print(f"Funding wallet balance: {node_conn._call('getbalance')} BTC")

    # ==============================================================================
    print("\n" + "=" * 70)
    print("1. Program Setup: Connect RPC, Wallets, Legacy Addresses & Funding")
    print("=" * 70)

    wallet_conn = setup_wallet("legacy_wallet")
    print("• Connected to bitcoind using RPC and loaded/created wallet.")

    # Generate three LEGACY addresses: A, B, and C
    # We MUST use 'legacy' (P2PKH) so we get a traditional ScriptSig instead of SegWit.
    addr_a = wallet_conn._call("getnewaddress", "AddressA", "legacy")
    addr_b = wallet_conn._call("getnewaddress", "AddressB", "legacy")
    addr_c = wallet_conn._call("getnewaddress", "AddressC", "legacy")

    print(f"• Generated legacy address A: {addr_a}")
    print(f"• Generated legacy address B: {addr_b}")
    print(f"• Generated legacy address C: {addr_c}")

    # Fund Address A
    txid_fund_a = node_conn._call("sendtoaddress", addr_a, 5.0)
    print(f"• Funded address A (TXID: {txid_fund_a})")

    # Mine 1 block to confirm the funding
    node_conn._call("generatetoaddress", 1, mining_addr)

    # ==============================================================================
    print("\n" + "=" * 70)
    print("2. Create a Transaction from Address A to Address B")
    print("=" * 70)

    # Get UTXO for Address A
    unspent_a = wallet_conn._call("listunspent", 1, 9999999, [addr_a])
    if not unspent_a:
        print("Error: No unspent outputs found for Address A.")
        sys.exit(1)

    utxo_a = unspent_a[0]
    fee = 0.0001  # BTC per transaction

    # Create a raw transaction sending coins from A to B
    inputs_ab = [{"txid": utxo_a["txid"], "vout": utxo_a["vout"]}]
    send_amount_ab = round(float(utxo_a["amount"]) - fee, 8)
    outputs_ab = {addr_b: send_amount_ab}
    print(f"• UTXO amount: {utxo_a['amount']} BTC, fee: {fee} BTC, sending: {send_amount_ab} BTC")

    raw_tx_ab = wallet_conn._call("createrawtransaction", inputs_ab, outputs_ab)
    print("• Created raw transaction A -> B")

    # Decode the raw transactions to extract the locking script for Address B
    decoded_ab = wallet_conn._call("decoderawtransaction", raw_tx_ab)

    # Find the exact vout for Address B to get its ScriptPubKey
    script_pubkey_b = ""
    for vout in decoded_ab["vout"]:
        # For legacy addresses, Bitcoin Core returns "address", sometimes inside "scriptPubKey"
        if "address" in vout["scriptPubKey"] and vout["scriptPubKey"]["address"] == addr_b:
            script_pubkey_b = vout["scriptPubKey"]["hex"]
            script_pubkey_asm = vout["scriptPubKey"]["asm"]

    print(
        f"• Extracted ScriptPubKey (Locking Script) for B:\n  ASM: {script_pubkey_asm}\n  HEX: {script_pubkey_b}"
    )

    # Sign the transaction using signrawtransactionwithwallet
    signed_ab = wallet_conn._call("signrawtransactionwithwallet", raw_tx_ab)

    # Broadcast the transaction
    txid_ab = wallet_conn._call("sendrawtransaction", signed_ab["hex"])
    print(f"• Signed and Broadcasted Transaction A -> B (TXID: {txid_ab})")

    # Mine 1 block to confirm the A -> B transaction
    node_conn._call("generatetoaddress", 1, mining_addr)

    # ==============================================================================
    print("\n" + "=" * 70)
    print("3. Write another program to send B to C and Validate Scripts")
    print("=" * 70)

    # Get the listunspent enlisting the txid that shows address B as UTXO
    unspent_b = wallet_conn._call("listunspent", 1, 9999999, [addr_b])
    print("• Found listunspent for Address B:")

    utxo_b = None
    for u in unspent_b:
        if u["txid"] == txid_ab:
            utxo_b = u
            print(f"  -> Selected UTXO from previous TX: {u['txid']} (vout {u['vout']})")
            break

    if not utxo_b:
        print("Error: Address B did not receive the funds from A.")
        sys.exit(1)

    # Create a Transaction from Address B to Address C funded by this txid
    inputs_bc = [{"txid": utxo_b["txid"], "vout": utxo_b["vout"]}]
    send_amount_bc = round(float(utxo_b["amount"]) - fee, 8)
    outputs_bc = {addr_c: send_amount_bc}
    print(f"• UTXO amount: {utxo_b['amount']} BTC, fee: {fee} BTC, sending: {send_amount_bc} BTC")

    raw_tx_bc = wallet_conn._call("createrawtransaction", inputs_bc, outputs_bc)
    print("• Created raw transaction B -> C")

    # Sign and broadcast
    signed_bc = wallet_conn._call("signrawtransactionwithwallet", raw_tx_bc)
    txid_bc = wallet_conn._call("sendrawtransaction", signed_bc["hex"])
    print(f"• Signed and Broadcasted Transaction B -> C (TXID: {txid_bc})")

    # Decode the rawtransaction and analyze the response part (ScriptSig)
    decoded_bc = wallet_conn._call("decoderawtransaction", signed_bc["hex"])
    script_sig_b = decoded_bc["vin"][0]["scriptSig"]["hex"]
    script_sig_asm = decoded_bc["vin"][0]["scriptSig"]["asm"]

    print("\n--- Script Analysis ---")
    print(
        f"• Unlocking Script (ScriptSig) provided by B to spend A's output:\n  ASM: {script_sig_asm}\n  HEX: {script_sig_b}"
    )
    print(f"• Challenge Script (ScriptPubKey) locked by A:\n  HEX: {script_pubkey_b}")
    print(
        "• Check: Does the ScriptSig successfully unlock the ScriptPubKey? Yes, because bitcoind accepted and broadcasted it."
    )

    # Validate the scripts using the Bitcoin Debugger
    print("\n--- Validating using Bitcoin Debugger (btcdeb) ---")

    # btcdeb requires the hex of the spending TX, and the full hex of the PREVIOUS TX
    raw_tx_hex_bc = signed_bc["hex"]
    prev_tx_hex_ab = node_conn._call("getrawtransaction", txid_ab, False)

    print("Launching btcdeb interactive debugger to evaluate ScriptSig + ScriptPubKey...")
    run_btcdeb_steps(raw_tx_hex_bc, prev_tx_hex_ab)
