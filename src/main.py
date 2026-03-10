#!/usr/bin/env python3
import os
import shutil
import sys

from bitcoin import SelectParams
from bitcoin.rpc import JSONRPCError, Proxy

from runbtcdeb import run_btcdeb_steps

SelectParams("regtest")

# Environment setup
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
        print(f"Created wallet: {name}")
    except JSONRPCError as e:
        if e.error.get("code") == -4:
            print(f"Wallet '{name}' already exists on disk. Attempting to load...")
            try:
                node_conn._call("loadwallet", name)
                print(f"Wallet '{name}' loaded successfully.")
            except JSONRPCError as load_e:
                if load_e.error.get("code") == -35:
                    print(f"Wallet '{name}' was already loaded.")
                else:
                    raise load_e
        else:
            raise e

    return Proxy(service_url=f"{base_url}/wallet/{name}")


btcdeb_path = shutil.which("btcdeb")
if not btcdeb_path:
    print("Error: 'btcdeb' binary not found in PATH. Please install it first.")
    sys.exit(1)

wallet_conn = setup_wallet("modern_wallet")

# Mining address
mining_addr = wallet_conn._call("getnewaddress")

# Ensure chain has enough blocks to spend coinbase
current_height = node_conn._call("getblockcount")
if current_height < 101:
    print(f"\nChain too short to spend. Mining {101 - current_height} blocks...")
    node_conn._call("generatetoaddress", 101 - current_height, mining_addr)

# Create a transaction
print("\n--- Creating a transaction ---")

dest_addr = wallet_conn._call("getnewaddress")

txid = wallet_conn._call("sendtoaddress", dest_addr, 1.0)

print(f"Transaction created! TXID: {txid}")

print("\n--- Fetching transaction data for btcdeb ---")

# Get the spending transaction hex
raw_tx_hex = node_conn._call("getrawtransaction", txid, False)
decoded_tx = node_conn._call("decoderawtransaction", raw_tx_hex)

# Extract input details to find the previous transaction
vin = decoded_tx["vin"][0]
prev_txid = vin["txid"]

print(f"Debugging input 0 of TX: {txid}")
print(f"Which spends UTXO from TX: {prev_txid}")

# Get the full hex of the PREVIOUS transaction
prev_tx_hex = node_conn._call("getrawtransaction", prev_txid, False)

print("\n--- Launching btcdeb interactive debugger ---")
run_btcdeb_steps(raw_tx_hex, prev_tx_hex)
