#!/usr/bin/env python3
"""Equium Multi-Instance Miner - Lightweight Alternative.

A simpler version of enhanced_miner.py that focuses purely on spawning and
managing multiple miner instances. Less features but easier to understand and
modify.

This script:
  - Spawns N copies of the equium-miner binary
  - Distributes them across available RPC endpoints
  - Restarts any that crash
  - Prints a live status line showing active workers

For the full-featured version with stats, health monitoring, and log rotation,
use enhanced_miner.py instead.

Usage:
  python3 multi_miner.py --workers 4 --rpc https://my-rpc.com --keypair ~/id.json
  python3 multi_miner.py --config config.env
"""

import argparse
import os
import signal
import subprocess
import sys
import threading
import time
from pathlib import Path
from typing import Dict, List, Optional

sys.path.insert(0, str(Path(__file__).parent))
from config import MinerConfig


class SimpleMinerPool:
    """Simple pool of miner subprocesses."""

    def __init__(self, config: MinerConfig):
        self.config = config
        self.processes: Dict[int, subprocess.Popen] = {}
        self.rpc_assignments: Dict[int, str] = {}
        self._shutdown = threading.Event()
        self._lock = threading.Lock()

    def run(self) -> None:
        """Start all workers and monitor them."""
        signal.signal(signal.SIGINT, self._handle_signal)
        signal.signal(signal.SIGTERM, self._handle_signal)

        binary = self.config.binary_path
        if not os.path.isfile(binary) or not os.access(binary, os.X_OK):
            print(f"ERROR: Binary not found or not executable: {binary}")
            print("Run build.sh first or set EQUIUM_BINARY_PATH")
            sys.exit(1)

        rpc_urls = self.config.get_all_rpc_urls()
        num_workers = self.config.num_workers

        print(f"Starting {num_workers} miner instances...")
        print(f"Binary: {binary}")
        print(f"RPCs: {len(rpc_urls)} endpoint(s)")
        print(f"Max nonces/round: {self.config.max_nonces_per_round}")
        print()

        # Start all workers
        for i in range(num_workers):
            rpc = rpc_urls[i % len(rpc_urls)]
            self._start_worker(i, binary, rpc)

        # Monitor loop
        restart_count = 0
        while not self._shutdown.is_set():
            time.sleep(2)

            # Check for dead workers
            for wid in list(self.processes.keys()):
                proc = self.processes[wid]
                if proc.poll() is not None:
                    if self._shutdown.is_set():
                        break
                    restart_count += 1
                    rpc = rpc_urls[restart_count % len(rpc_urls)]
                    print(f"[!] Worker {wid} died (exit={proc.returncode}), "
                          f"restarting (#{restart_count})...")
                    time.sleep(self.config.restart_delay_secs)
                    if not self._shutdown.is_set():
                        self._start_worker(wid, binary, rpc)

            # Status line
            alive = sum(1 for p in self.processes.values() if p.poll() is None)
            sys.stdout.write(
                f"\r  [{alive}/{num_workers} running] "
                f"restarts: {restart_count}  "
            )
            sys.stdout.flush()

        # Shutdown
        self._stop_all()

    def _start_worker(self, worker_id: int, binary: str, rpc_url: str) -> None:
        """Start a single worker subprocess."""
        cmd = [
            binary,
            "--rpc-url", rpc_url,
            "--keypair", self.config.keypair_path,
            "--cu-limit", str(self.config.cu_limit),
            "--max-nonces-per-round", str(self.config.max_nonces_per_round),
        ]

        log_dir = Path(self.config.log_dir)
        log_dir.mkdir(parents=True, exist_ok=True)
        log_path = log_dir / f"worker_{worker_id}.log"

        with open(log_path, "a") as lf:
            lf.write(f"\n--- Worker {worker_id} started at {time.ctime()} ---\n")

        log_fh = open(log_path, "a")
        proc = subprocess.Popen(
            cmd,
            stdout=log_fh,
            stderr=subprocess.STDOUT,
            close_fds=True,
        )

        with self._lock:
            self.processes[worker_id] = proc
            self.rpc_assignments[worker_id] = rpc_url

    def _stop_all(self) -> None:
        """Stop all workers gracefully."""
        print("\nStopping all workers...")
        for wid, proc in self.processes.items():
            if proc.poll() is None:
                proc.terminate()
        # Wait for graceful exit
        for wid, proc in self.processes.items():
            try:
                proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                proc.kill()
        print("All workers stopped.")

    def _handle_signal(self, signum: int, frame) -> None:
        """Handle termination signals."""
        self._shutdown.set()


def main() -> None:
    """CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Equium Multi-Instance Miner (lightweight)"
    )
    parser.add_argument("--config", type=str, default=None, help="Config file path")
    parser.add_argument("--workers", "-w", type=int, default=None, help="Number of workers")
    parser.add_argument("--rpc", type=str, default=None, help="Primary RPC URL")
    parser.add_argument("--keypair", "-k", type=str, default=None, help="Keypair path")
    parser.add_argument("--max-nonces", type=int, default=None, help="Max nonces per round")
    args = parser.parse_args()

    env_path = Path(args.config) if args.config else None
    config = MinerConfig.from_env(env_path)

    if args.workers:
        config.num_workers = args.workers
    if args.rpc:
        config.rpc_url = args.rpc
    if args.keypair:
        config.keypair_path = os.path.expanduser(args.keypair)
    if args.max_nonces:
        config.max_nonces_per_round = args.max_nonces

    pool = SimpleMinerPool(config)
    pool.run()


if __name__ == "__main__":
    main()
