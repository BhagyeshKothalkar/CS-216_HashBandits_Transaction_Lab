# CS-216 Bitcoin Transaction Lab — HashBandits

A Bitcoin transaction lab that demonstrates **Legacy (P2PKH)** and **P2SH-SegWit (P2SH-P2WPKH)** transaction workflows on a regtest network, including script analysis with `btcdeb` and a comparative analysis of both transaction types.

## Team Information

**Team Name:** HashBandits

| # | Name | Roll Number |
|---|---|---|
| 1 | Kothalkar Bhagyesh Ritesh | 240041024 |
| 2 | Khush Kumar Singh | 240041023 |
| 3 | Yash Bhamare | 240041040 |
| 4 | KVL Sarath Chandra | 240001039 |

## Project Structure

```
├── compose.yaml        # Docker Compose — bitcoin_server + client
├── Dockerfile          # Multi-stage build: btcdeb + python-bitcoinlib
├── bitcoin.conf        # Bitcoin Core regtest configuration
├── report.tex          # LaTeX assignment report
├── report.pdf          # Compiled report (PDF)
├── legacy.txt          # Captured terminal output — Part 1
├── segwit.txt          # Captured terminal output — Part 2
├── comparison.txt      # Captured terminal output — Part 3
└── src/
    ├── main.py         # Interactive menu (Legacy / SegWit / Compare / Exit)
    ├── legacy.py       # Part 1 — P2PKH transactions (A → B → C)
    ├── segwit.py       # Part 2 — P2SH-P2WPKH transactions (A' → B' → C')
    ├── compare.py      # Part 3 — Size & script comparison + analysis
    └── runbtcdeb.py    # Automated btcdeb script debugger runner
```

## Prerequisites

- [Docker](https://docs.docker.com/get-docker/) & [Docker Compose](https://docs.docker.com/compose/install/)

## Setup & Run

**1. Build the Docker images:**

```bash
docker compose build
```

**2. Run the client interactively:**

```bash
docker compose run client
```

This automatically starts the `bitcoin_server` (Bitcoin Core in regtest mode) and then launches the interactive client.

**3. Choose a mode:**

```
Choose Transaction Mode:
Press 1 for Legacy
Press 2 for Segwit
Press 3 for Comparative Analysis
Press 4 to Exit
```

## Assignment Parts

| Part | Description | Code | Output |
|---|---|---|---|
| **Part 1** | Legacy (P2PKH) — A → B → C | [`legacy.py`](src/legacy.py) | [`legacy.txt`](legacy.txt) |
| **Part 2** | P2SH-SegWit (P2SH-P2WPKH) — A' → B' → C' | [`segwit.py`](src/segwit.py) | [`segwit.txt`](segwit.txt) |
| **Part 3** | Comparative Analysis (size, scripts, SegWit benefits) | [`compare.py`](src/compare.py) | [`comparison.txt`](comparison.txt) |

> **Note:** Due to the extremely long terminal outputs (decoded transactions, hex data, and `btcdeb` step-by-step traces), traditional screenshots were not feasible. Instead, we captured the complete terminal output for each part using `| tee` and provided them as text files for full traceability.

## Report

The detailed assignment report with decoded scripts, btcdeb analysis, comparison tables, and explanations is provided as a LaTeX PDF:

📄 **[report.pdf](report.pdf)** — Full assignment report

## Tools Used

| Tool | Purpose |
|---|---|
| **Bitcoin Core** (`bitcoind`) | Full node running in regtest mode |
| **python-bitcoinlib** | Python RPC interface to `bitcoind` |
| **btcdeb** | Bitcoin Script debugger for validating script execution |
| **pexpect** | Automating `btcdeb` interactive stepping |
| **Docker Compose** | Orchestrating the Bitcoin node and client containers |

## Configuration

The `bitcoin.conf` file configures the regtest node with:

- RPC authentication (`rpcuser` / `rpcpassword`)
- Fee settings (`paytxfee`, `fallbackfee`, `mintxfee`)
- Transaction index enabled (`txindex=1`)
- Confirmation target of 6 blocks