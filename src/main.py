#!/usr/bin/env python3
import os
import shutil
import subprocess
import sys

from bitcoin import SelectParams
from bitcoin.rpc import JSONRPCError, Proxy

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
mining_addr = wallet_conn._call("getnewaddress")

current_height = node_conn._call("getblockcount")
if current_height < 101:
    print(f"\nChain too short to spend. Mining {101 - current_height} blocks...")
    node_conn._call("generatetoaddress", 101 - current_height, mining_addr)

# Create a simple transaction
print("\n--- Creating a transaction ---")
dest_addr = wallet_conn._call("getnewaddress")
# Send 1 BTC to the new address
txid = wallet_conn._call("sendtoaddress", dest_addr, 1.0)
print(f"Transaction created! TXID: {txid}")
print("\n--- Fetching transaction data for btcdeb ---")
raw_tx_hex = node_conn._call("getrawtransaction", txid, False)
decoded_tx = node_conn._call("decoderawtransaction", raw_tx_hex)
prev_txid = decoded_tx["vin"][0]["txid"]
prev_tx_hex = node_conn._call("getrawtransaction", prev_txid, False)
print(f"Debugging input 0 of TX: {txid}")
print(f"Which spends UTXO from TX: {prev_txid}")

print("\n--- btcdeb Execution Logs ---")
btcdeb_cmd = [
    btcdeb_path,
    "--tx",
    raw_tx_hex,
    "--prevtx",
    prev_tx_hex,
    "--txin",
    "0",
    "-e",
    "run",
]

try:
    result = subprocess.run(btcdeb_cmd, capture_output=True, text=True)

    if result.stdout:
        print(result.stdout)
    if result.stderr:
        print("Errors/Warnings:")
        print(result.stderr)

    if result.returncode == 0:
        print("\nSuccess: Script evaluated to valid!")
    else:
        print(f"\nFailure: btcdeb exited with code {result.returncode}")

except Exception as e:
    print(f"Error running btcdeb: {e}")

sys.exit(0)
