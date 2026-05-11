# Equium ($EQM) Mining Automation

Multi-instance CPU miner orchestrator for the Equium on-chain Proof-of-Work protocol on Solana.

## Overview

Equium uses Equihash (96,5) PoW bound to the miner's public key. This module wraps the official Rust CLI miner with a Python orchestrator that runs multiple parallel instances for higher hashrate.

**Key improvements over running the bare miner:**
- Multiple parallel workers (N instances = ~Nx hashrate)
- RPC endpoint rotation and failover
- Automatic crash recovery with exponential backoff
- Health monitoring (kills stuck workers)
- Stats aggregation across all workers
- Log rotation per worker
- Auto-build with native CPU optimizations

## Prerequisites

- **Python 3.9+** (tested on 3.9 and 3.11)
- **Rust toolchain** (for building the miner binary)
- **Solana keypair** JSON file with SOL for transaction fees
- **RPC endpoint** (private endpoint recommended for production mining)

## Quick Start

```bash
# 1. Navigate to the module
cd /projects/sandbox/dac-automation/modules/equium/

# 2. Copy and configure
cp config.env.example config.env
# Edit config.env with your RPC URL and keypair path

# 3. Build the optimized binary
chmod +x build.sh
./build.sh

# 4. Run the enhanced miner (recommended)
python3 enhanced_miner.py

# Or with CLI flags:
python3 enhanced_miner.py --workers 4 --rpc https://your-rpc.com --keypair ~/.config/solana/id.json
```

## File Structure

```
modules/equium/
  __init__.py              # Module init
  config.py                # Configuration management (loads from env/file)
  config.env.example       # Example configuration (copy to config.env)
  enhanced_miner.py        # MAIN SCRIPT - Full-featured orchestrator
  multi_miner.py           # Lightweight alternative (less features, simpler)
  monitor.py               # Real-time stats viewer / log monitor
  build.sh                 # Build script with optimizations
  run_miner.sh             # Single-instance launcher with auto-restart
  README_EQUIUM.md         # This file
  logs/                    # Log output directory (auto-created)
```

## Scripts Explained

### `enhanced_miner.py` (Recommended)

The full-featured orchestrator. Start here.

```bash
# Default: uses all CPU cores, reads config.env
python3 enhanced_miner.py

# Custom settings
python3 enhanced_miner.py --workers 8 --max-nonces 131072 --priority-fee 5000

# Point to pre-built binary
python3 enhanced_miner.py --binary /path/to/equium-miner --no-build
```

Features:
- Multi-worker management with per-worker stats
- Exponential backoff restart (3s -> 6s -> 12s -> ... -> max 60s)
- Health timeout: kills workers silent for 5+ minutes
- Graceful shutdown on Ctrl+C
- Auto-builds binary with native CPU optimizations
- RPC rotation across workers

### `multi_miner.py` (Lightweight)

Simpler version for those who want less overhead:

```bash
python3 multi_miner.py --workers 4 --rpc https://my-rpc.com --keypair ~/id.json
```

### `monitor.py` (Stats Viewer)

View mining statistics from log files:

```bash
# Live dashboard (refreshes every 5s)
python3 monitor.py

# One-time summary
python3 monitor.py --summary

# Tail specific worker output
python3 monitor.py --worker 0
```

### `run_miner.sh` (Single Instance)

Run just one miner with auto-restart:

```bash
chmod +x run_miner.sh
./run_miner.sh
```

### `build.sh` (Build Binary)

Build the Rust binary with max optimizations:

```bash
chmod +x build.sh
./build.sh          # Normal build
./build.sh --clean  # Clean + rebuild
```

## Configuration

### Environment Variables

All configuration is via environment variables (loaded from `config.env` if present):

| Variable | Default | Description |
|----------|---------|-------------|
| `EQUIUM_RPC_URL` | `https://api.mainnet-beta.solana.com` | Primary RPC endpoint |
| `EQUIUM_RPC_FALLBACK_1..9` | (empty) | Fallback RPC endpoints |
| `EQUIUM_KEYPAIR_PATH` | `~/.config/solana/id.json` | Wallet keypair file |
| `EQUIUM_NUM_WORKERS` | CPU cores | Parallel miner instances |
| `EQUIUM_MAX_NONCES` | `65536` | Max nonces per round per worker |
| `EQUIUM_CU_LIMIT` | `1400000` | Compute units per transaction |
| `EQUIUM_PRIORITY_FEE_LAMPORTS` | `0` | Priority fee (micro-lamports/CU) |
| `EQUIUM_AUTO_RESTART` | `true` | Auto-restart crashed workers |
| `EQUIUM_RESTART_DELAY_SECS` | `3` | Initial restart delay |
| `EQUIUM_MAX_RESTART_DELAY_SECS` | `60` | Max backoff delay |
| `EQUIUM_HEALTH_TIMEOUT_SECS` | `300` | Kill worker if silent this long |
| `EQUIUM_LOG_DIR` | `./logs/equium` | Log output directory |
| `EQUIUM_LOG_LEVEL` | `INFO` | Logging verbosity |
| `EQUIUM_SOURCE_DIR` | `/projects/sandbox/equium` | Equium source for building |
| `EQUIUM_BINARY_PATH` | `{source}/target/release/equium-miner` | Binary path |
| `EQUIUM_NATIVE_CPU` | `true` | Build with -C target-cpu=native |

### CLI Arguments (override config)

```
--workers N          Number of parallel workers
--rpc URL            Primary RPC URL
--keypair PATH       Keypair JSON path
--max-nonces N       Max nonces per round
--cu-limit N         CU limit per tx
--priority-fee N     Priority fee (micro-lamports/CU)
--binary PATH        Pre-built binary path
--no-build           Skip auto-build
--config PATH        Config file path
--log-level LEVEL    DEBUG/INFO/WARNING/ERROR
```

## Performance Tips

### 1. Maximize Workers

Run one worker per CPU core. The Equihash solver is CPU-bound and single-threaded per instance, so N cores = N parallel solvers.

```bash
# Use all cores (default)
python3 enhanced_miner.py

# Or explicit
python3 enhanced_miner.py --workers $(nproc)
```

### 2. Increase Nonces Per Round

Higher `--max-nonces` means more attempts before re-fetching on-chain state. Since fetching takes an RPC round-trip, fewer fetches = more solving time.

```bash
# Default is 65536, try higher on fast machines
python3 enhanced_miner.py --max-nonces 131072
```

### 3. Use Private RPC

The public `api.mainnet-beta.solana.com` rate-limits aggressively. Use a private endpoint:
- Helius (free tier: 100k requests/day)
- Triton
- QuickNode
- Alchemy

### 4. Multiple RPC Endpoints

Distribute workers across multiple RPCs to avoid rate limits:

```env
EQUIUM_RPC_URL=https://mainnet.helius-rpc.com/?api-key=KEY1
EQUIUM_RPC_FALLBACK_1=https://solana-mainnet.g.alchemy.com/v2/KEY2
EQUIUM_RPC_FALLBACK_2=https://rpc.shyft.to?api_key=KEY3
```

### 5. Native CPU Build

The build script uses `-C target-cpu=native` by default, which enables AVX2/SSE4 instructions for the Blake2b hashing used in Equihash. This is already enabled - just make sure you build on the same machine you run on.

### 6. Priority Fees During Congestion

When the network is congested, add priority fees to land transactions faster:

```bash
# 1000 micro-lamports/CU = ~0.0014 SOL per mine tx
python3 enhanced_miner.py --priority-fee 1000
```

### 7. Run on Bare Metal

VMs and containers add overhead to the CPU-intensive Equihash solver. Bare metal gives the best performance.

## Troubleshooting

### Binary build fails

```
ERROR: Build failed with exit code 1
```

- Ensure Rust toolchain is installed: `curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh`
- Check disk space (release build needs ~2GB)
- Try clean build: `./build.sh --clean`

### "Keypair file not found"

- Verify path: `ls ~/.config/solana/id.json`
- Generate new: `solana-keygen new --outfile ~/.config/solana/id.json`
- Fund with SOL for tx fees (0.01 SOL is enough for many blocks)

### Workers keep crashing

- Check logs: `python3 monitor.py --worker 0`
- Common causes:
  - RPC rate limiting (switch to private endpoint)
  - Insufficient SOL for fees
  - Network issues

### "above target" continuously

This is normal! The miner tries random nonces and most will not meet the difficulty target. It means the miner is working. A solution is found when the difficulty requirement is met.

### Round stalled / no new blocks

The miner automatically calls `advance_empty_round` after 75 seconds of no new block. This is normal and handled automatically.

### High CPU usage

Expected! Each worker uses 100% of one CPU core for Equihash solving. Total CPU = N workers x 1 core.

## Architecture Notes

- **Program ID**: `ZKGMUfxiRCXFPnqz9zgqAnuqJy15jk7fKbR4o6FuEQM`
- **EQM Mint**: `1MhvZzEe8gQ8Rb9CrT3Dn26Gkn9QRErzLMGkkTwveqm`
- **Equihash params**: n=96, k=5 (memory-bound, CPU-friendly, ASIC-resistant)
- **Block time**: ~1 minute
- **Block reward**: 25 EQM (halves every 378,000 blocks)
- **Round timeout**: 150 slots (~75 seconds)
- **Difficulty retarget**: every 60 blocks
- **Solutions bound to miner pubkey** (cannot be frontrun)

## AI Agent Prompt

If you want to run this from an AI agent, use this prompt:

```
Run the Equium ($EQM) mining automation. Steps:
1. cd /projects/sandbox/dac-automation/modules/equium/
2. Ensure config.env exists with valid RPC_URL and KEYPAIR_PATH
3. Run: python3 enhanced_miner.py --workers 4
4. Monitor output for "MINED!" events indicating successful blocks
5. Check stats with: python3 monitor.py --summary
```
