#!/usr/bin/env python3
"""
Part 3: Comparative Analysis of Legacy (P2PKH) vs P2SH-SegWit (P2SH-P2WPKH) Transactions

This script independently runs both transaction chains and compares:
  - Transaction sizes (bytes, vbytes, weight)
  - Script structures (ScriptPubKey, ScriptSig, Witness)
  - Why SegWit transactions are smaller and the benefits thereof
"""

import os
import sys

from bitcoin import SelectParams
from bitcoin.rpc import JSONRPCError, Proxy

SelectParams("regtest")

# ── RPC connection setup ─────────────────────────────────────────────────────
user = os.getenv("BITCOIN_RPC_USER", "rpcuser").rstrip("/")
password = os.getenv("BITCOIN_RPC_PASSWORD", "rpcpass").rstrip("/")
host = os.getenv("BITCOIN_RPC_HOST", "127.0.0.1").rstrip("/")
port = 18443

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


def ensure_funds(conn, mining_addr, min_btc=10.0):
    """Mine blocks until the wallet has enough balance."""
    while conn._call("getbalance") < min_btc:
        current_height = conn._call("getblockcount")
        if current_height < 101:
            blocks_needed = 101 - current_height
            conn._call("generatetoaddress", blocks_needed, mining_addr)
        else:
            conn._call("generatetoaddress", 1, mining_addr)


def run_chain(wallet_conn, node_conn, mining_addr, addr_type, label):
    """
    Run a full A→B→C transaction chain and return decoded TX data for both
    transactions (A→B signed, B→C signed).

    addr_type: "legacy" or "p2sh-segwit"
    """
    # Generate three addresses
    addr_a = wallet_conn._call("getnewaddress", f"{label}_A", addr_type)
    addr_b = wallet_conn._call("getnewaddress", f"{label}_B", addr_type)
    addr_c = wallet_conn._call("getnewaddress", f"{label}_C", addr_type)

    # Fund A
    node_conn._call("sendtoaddress", addr_a, 5.0)
    node_conn._call("generatetoaddress", 1, mining_addr)

    fee = 0.0001  # BTC per transaction

    # ── TX 1: A → B ──────────────────────────────────────────────────────
    unspent_a = wallet_conn._call("listunspent", 1, 9999999, [addr_a])
    utxo_a = unspent_a[0]

    inputs_ab = [{"txid": utxo_a["txid"], "vout": utxo_a["vout"]}]
    send_amount_ab = round(float(utxo_a["amount"]) - fee, 8)
    outputs_ab = {addr_b: send_amount_ab}

    raw_tx_ab = wallet_conn._call("createrawtransaction", inputs_ab, outputs_ab)
    signed_ab = wallet_conn._call("signrawtransactionwithwallet", raw_tx_ab)
    txid_ab = wallet_conn._call("sendrawtransaction", signed_ab["hex"])
    decoded_ab = wallet_conn._call("decoderawtransaction", signed_ab["hex"])

    node_conn._call("generatetoaddress", 1, mining_addr)

    # ── TX 2: B → C ──────────────────────────────────────────────────────
    unspent_b = wallet_conn._call("listunspent", 1, 9999999, [addr_b])
    utxo_b = None
    for u in unspent_b:
        if u["txid"] == txid_ab:
            utxo_b = u
            break

    if not utxo_b:
        print(f"Error: {label} Address B did not receive funds from A.")
        sys.exit(1)

    inputs_bc = [{"txid": utxo_b["txid"], "vout": utxo_b["vout"]}]
    send_amount_bc = round(float(utxo_b["amount"]) - fee, 8)
    outputs_bc = {addr_c: send_amount_bc}

    raw_tx_bc = wallet_conn._call("createrawtransaction", inputs_bc, outputs_bc)
    signed_bc = wallet_conn._call("signrawtransactionwithwallet", raw_tx_bc)
    wallet_conn._call("sendrawtransaction", signed_bc["hex"])
    decoded_bc = wallet_conn._call("decoderawtransaction", signed_bc["hex"])

    node_conn._call("generatetoaddress", 1, mining_addr)

    return {
        "ab": decoded_ab,
        "bc": decoded_bc,
        "addr_a": addr_a,
        "addr_b": addr_b,
        "addr_c": addr_c,
    }


def print_tx_metrics(label, decoded):
    """Print size / vsize / weight for a decoded transaction."""
    size = decoded["size"]
    vsize = decoded["vsize"]
    weight = decoded["weight"]
    print(f"  {label:<20s}  size={size:>4d} bytes   vsize={vsize:>4d} vbytes   weight={weight:>5d} WU")
    return size, vsize, weight


def print_script_details(label, decoded, is_segwit=False):
    """Print the ScriptSig / ScriptPubKey / Witness for a signed TX."""
    vin = decoded["vin"][0]
    vout = decoded["vout"][0]

    print(f"\n  [{label}]")
    print(f"    ScriptPubKey (locking / challenge):")
    print(f"      type : {vout['scriptPubKey']['type']}")
    print(f"      asm  : {vout['scriptPubKey']['asm']}")
    print(f"      hex  : {vout['scriptPubKey']['hex']}")

    print(f"    ScriptSig (unlocking / response):")
    print(f"      asm  : {vin['scriptSig']['asm']}")
    print(f"      hex  : {vin['scriptSig']['hex']}")

    if is_segwit:
        witness = vin.get("txinwitness", [])
        print(f"    Witness Stack ({len(witness)} items):")
        for i, item in enumerate(witness):
            print(f"      [{i}]: {item}")


# ══════════════════════════════════════════════════════════════════════════════
#  MAIN
# ══════════════════════════════════════════════════════════════════════════════

def run_compare():
    print("=" * 70)
    print("  Part 3: Comparative Analysis — P2PKH (Legacy) vs P2SH-P2WPKH (SegWit)")
    print("=" * 70)

    # ── Setup ─────────────────────────────────────────────────────────────
    default_conn = setup_wallet("default")
    mining_addr = default_conn._call("getnewaddress")
    ensure_funds(default_conn, mining_addr)

    legacy_wallet = setup_wallet("compare_legacy")
    segwit_wallet = setup_wallet("compare_segwit")

    # ── Run both chains ───────────────────────────────────────────────────
    print("\n• Running Legacy (P2PKH) transaction chain A → B → C ...")
    legacy = run_chain(legacy_wallet, default_conn, mining_addr, "legacy", "Legacy")

    print("• Running SegWit (P2SH-P2WPKH) transaction chain A' → B' → C' ...")
    segwit = run_chain(segwit_wallet, default_conn, mining_addr, "p2sh-segwit", "SegWit")

    # ══════════════════════════════════════════════════════════════════════
    print("\n" + "=" * 70)
    print("  3.1  Transaction Size Comparison (bytes, vbytes, weight)")
    print("=" * 70)

    print("\n  Transaction A → B (Legacy) vs A' → B' (SegWit):")
    l_ab_size, l_ab_vsize, l_ab_weight = print_tx_metrics("Legacy  A→B", legacy["ab"])
    s_ab_size, s_ab_vsize, s_ab_weight = print_tx_metrics("SegWit  A'→B'", segwit["ab"])

    print(f"\n  Δ A→B:  size={l_ab_size - s_ab_size:+d}   vsize={l_ab_vsize - s_ab_vsize:+d}   weight={l_ab_weight - s_ab_weight:+d}  (Legacy − SegWit)")

    print("\n  Transaction B → C (Legacy) vs B' → C' (SegWit):")
    l_bc_size, l_bc_vsize, l_bc_weight = print_tx_metrics("Legacy  B→C", legacy["bc"])
    s_bc_size, s_bc_vsize, s_bc_weight = print_tx_metrics("SegWit  B'→C'", segwit["bc"])

    print(f"\n  Δ B→C:  size={l_bc_size - s_bc_size:+d}   vsize={l_bc_vsize - s_bc_vsize:+d}   weight={l_bc_weight - s_bc_weight:+d}  (Legacy − SegWit)")

    # ══════════════════════════════════════════════════════════════════════
    print("\n" + "=" * 70)
    print("  3.2  Script Structure Comparison")
    print("=" * 70)

    print("\n  ── Legacy (P2PKH) Scripts ──")
    print_script_details("A → B (signed)", legacy["ab"], is_segwit=False)
    print_script_details("B → C (signed)", legacy["bc"], is_segwit=False)

    print("\n  ── P2SH-SegWit (P2SH-P2WPKH) Scripts ──")
    print_script_details("A' → B' (signed)", segwit["ab"], is_segwit=True)
    print_script_details("B' → C' (signed)", segwit["bc"], is_segwit=True)

    # ══════════════════════════════════════════════════════════════════════
    print("\n" + "=" * 70)
    print("  3.3  Why Are SegWit Transactions Smaller? — Analysis")
    print("=" * 70)

    savings_vsize = ((l_bc_vsize - s_bc_vsize) / l_bc_vsize) * 100 if l_bc_vsize else 0

    print(f"""
  Observed data:
    Legacy  B→C :  size={l_bc_size} bytes,  vsize={l_bc_vsize} vbytes,  weight={l_bc_weight} WU
    SegWit  B'→C':  size={s_bc_size} bytes,  vsize={s_bc_vsize} vbytes,  weight={s_bc_weight} WU
    Virtual size saving: {savings_vsize:.1f}%

  Key reasons why SegWit (P2SH-P2WPKH) transactions are smaller:

  1. WITNESS DISCOUNT
     Bitcoin's block weight limit counts witness data at 1/4 of the rate of
     non-witness data. The formula is:
       weight = (non-witness bytes × 4) + (witness bytes × 1)
       vsize  = weight / 4
     Since signatures (the largest part of a transaction) are moved to the
     witness, the effective virtual size is significantly reduced.

  2. SEGREGATION OF SIGNATURE DATA
     In legacy P2PKH, the ScriptSig contains both the full signature (~71 bytes)
     and the public key (~33 bytes) inline in the transaction body.
     In P2SH-P2WPKH, the ScriptSig only carries a short redeem script (~23 bytes),
     while the signature and public key are placed in the separate witness field
     which benefits from the 75% discount.

  3. SCRIPT STRUCTURE DIFFERENCES
     • Legacy ScriptPubKey: OP_DUP OP_HASH160 <PubKeyHash> OP_EQUALVERIFY OP_CHECKSIG
       ScriptSig: <Sig> <PubKey>  —  everything counted at full weight.
     • SegWit ScriptPubKey: OP_HASH160 <RedeemScriptHash> OP_EQUAL
       ScriptSig: <RedeemScript>  —  tiny, only the P2SH wrapper.
       Witness: <Sig> <PubKey>  —  counted at 1/4 weight.

  4. PRACTICAL BENEFITS
     • Lower fees: Miners charge by vsize, so the witness discount directly
       reduces the fee required for confirmation.
     • More transactions per block: The 4 MW block weight limit can fit more
       SegWit transactions than legacy ones.
     • Transaction malleability fix: Signatures in the witness cannot be
       altered by intermediaries, enabling second-layer protocols like
       the Lightning Network.
""")


if __name__ == "__main__":
    run_compare()
