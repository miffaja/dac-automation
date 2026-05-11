"""Equium ($EQM) mining automation module.

Multi-instance CPU miner orchestrator for the Equium on-chain PoW protocol
on Solana. Uses Equihash (96,5) proof-of-work with random nonces.

Key features:
- Multi-worker parallel mining (one instance per CPU core)
- RPC endpoint rotation and failover
- Automatic crash recovery with exponential backoff
- Health monitoring and stale worker detection
- Graceful shutdown and stats aggregation
- Log rotation per worker
"""

__version__ = "1.0.0"
__author__ = "DAC Automation"
