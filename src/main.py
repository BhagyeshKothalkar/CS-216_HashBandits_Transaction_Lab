#!/usr/bin/env python3
import os
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
        # Code -4 means "Wallet already exists"
        if e.error.get("code") == -4:
            print(f"Wallet '{name}' already exists on disk. Attempting to load...")
            try:
                node_conn._call("loadwallet", name)
                print(f"Wallet '{name}' loaded successfully.")
            except JSONRPCError as load_e:
                # Code -35 means "Wallet is already loaded"
                if load_e.error.get("code") == -35:
                    print(f"Wallet '{name}' was already loaded.")
                else:
                    raise load_e
        else:
            raise e

    return Proxy(service_url=f"{base_url}/wallet/{name}")


wallet_conn = setup_wallet("modern_wallet")

mining_addr = wallet_conn.getnewaddress()
print(f"New Address: {mining_addr}")

current_height = node_conn.getblockcount()
print(f"Starting test at height: {current_height}")

if current_height < 101:
    print(f"Chain too short to spend. Mining {101 - current_height} more...")
    node_conn._call("generatetoaddress", 101 - current_height, str(mining_addr))

balance = wallet_conn.getbalance()
print(f"Current Balance: {balance} BTC")
sys.exit(0)
