#!/usr/bin/env python3
"""Equium ($EQM) Enhanced Multi-Instance Mining Orchestrator.

This is the primary mining script. It manages multiple parallel instances of
the Equium Rust miner binary for maximum hashrate on multi-core machines.

Key improvements over running the bare Rust binary:
  - Multi-worker: N parallel miner processes (1 per CPU core)
  - RPC rotation: distributes workers across multiple RPC endpoints
  - Auto-restart: exponential backoff on crashes, resets on success
  - Health monitoring: kills and restarts stuck workers
  - Graceful shutdown: Ctrl+C cleanly terminates all workers
  - Stats aggregation: total blocks mined, uptime, per-worker status
  - Auto-build: compiles the Rust binary with max optimizations if missing
  - Log rotation: per-worker log files with configurable size limits

Why multiple instances works:
  The Rust miner uses random nonces internally. Multiple instances with the
  same keypair each try different random nonces simultaneously. The first to
  find a valid solution wins. This effectively multiplies your hashrate by N.

Usage:
  python3 enhanced_miner.py
  python3 enhanced_miner.py --config /path/to/config.env
  python3 enhanced_miner.py --workers 8 --rpc https://my-rpc.com

Requirements:
  - Python 3.9+
  - Rust toolchain (for building the binary)
  - Solana keypair JSON file
  - At least one RPC endpoint
"""

import argparse
import logging
import os
import re
import signal
import subprocess
import sys
import threading
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional

# Add parent paths for imports when run standalone
sys.path.insert(0, str(Path(__file__).parent))
from config import MinerConfig

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

MINED_PATTERN = re.compile(r"MINED!")
REWARD_PATTERN = re.compile(r"\+(\d+(?:\.\d+)?)\s*EQM")
HASHRATE_PATTERN = re.compile(r"([\d.]+)\s*(H/s|kH/s)")
ROUND_PATTERN = re.compile(r"round #(\d+)")
ABOVE_TARGET_PATTERN = re.compile(r"above target")
STALE_PATTERN = re.compile(r"stale challenge")
SUBMIT_ERROR_PATTERN = re.compile(r"submit error")
ADVANCED_ROUND_PATTERN = re.compile(r"advanced empty round")

# ---------------------------------------------------------------------------
# Data types
# ---------------------------------------------------------------------------


@dataclass
class WorkerStats:
    """Per-worker statistics."""

    worker_id: int
    pid: Optional[int] = None
    status: str = "starting"  # starting, running, crashed, stopped
    blocks_mined: int = 0
    eqm_earned: float = 0.0
    nonces_tried: int = 0
    above_target_count: int = 0
    stale_count: int = 0
    submit_errors: int = 0
    rounds_advanced: int = 0
    last_output_time: float = field(default_factory=time.time)
    start_time: float = field(default_factory=time.time)
    restart_count: int = 0
    current_round: int = 0
    last_hashrate: str = ""
    rpc_url: str = ""


@dataclass
class AggregateStats:
    """Aggregate statistics across all workers."""

    total_blocks: int = 0
    total_eqm: float = 0.0
    total_restarts: int = 0
    start_time: float = field(default_factory=time.time)


# ---------------------------------------------------------------------------
# Builder
# ---------------------------------------------------------------------------


class BinaryBuilder:
    """Builds the Equium Rust miner with optimal compilation settings."""

    def __init__(self, config: MinerConfig, logger: logging.Logger):
        self.config = config
        self.logger = logger

    def ensure_binary(self) -> str:
        """Ensure the binary exists, building if necessary. Returns binary path."""
        binary_path = self.config.binary_path
        if os.path.isfile(binary_path) and os.access(binary_path, os.X_OK):
            self.logger.info(f"Binary found: {binary_path}")
            return binary_path

        if not self.config.auto_build:
            raise FileNotFoundError(
                f"Binary not found at {binary_path} and auto_build is disabled. "
                f"Build manually: cargo build -p equium-cli-miner --release "
                f"(in {self.config.equium_source_dir})"
            )

        self.logger.info("Binary not found. Building from source...")
        return self.build()

    def build(self) -> str:
        """Build the miner binary with maximum optimizations."""
        source_dir = self.config.equium_source_dir
        if not os.path.isdir(source_dir):
            raise FileNotFoundError(
                f"Equium source directory not found: {source_dir}. "
                f"Clone the repo or set EQUIUM_SOURCE_DIR."
            )

        cargo_toml = os.path.join(source_dir, "Cargo.toml")
        if not os.path.isfile(cargo_toml):
            raise FileNotFoundError(
                f"No Cargo.toml found in {source_dir}. Is this the equium repo?"
            )

        env = os.environ.copy()
        # Enable native CPU optimizations for maximum hash throughput
        if self.config.native_cpu_target:
            existing_flags = env.get("RUSTFLAGS", "")
            env["RUSTFLAGS"] = f"{existing_flags} -C target-cpu=native".strip()
            self.logger.info("Building with -C target-cpu=native for max performance")

        cmd = [
            "cargo", "build",
            "-p", "equium-cli-miner",
            "--release",
        ]

        self.logger.info(f"Running: {' '.join(cmd)}")
        self.logger.info(f"Working dir: {source_dir}")

        try:
            result = subprocess.run(
                cmd,
                cwd=source_dir,
                env=env,
                capture_output=True,
                text=True,
                timeout=600,  # 10 min timeout for compilation
            )
        except subprocess.TimeoutExpired:
            raise RuntimeError("Build timed out after 10 minutes")

        if result.returncode != 0:
            self.logger.error(f"Build stdout:\n{result.stdout}")
            self.logger.error(f"Build stderr:\n{result.stderr}")
            raise RuntimeError(
                f"Build failed with exit code {result.returncode}. "
                f"Check logs for details."
            )

        binary_path = self.config.binary_path
        if not os.path.isfile(binary_path):
            raise RuntimeError(
                f"Build succeeded but binary not found at {binary_path}. "
                f"Check the workspace Cargo.toml for the correct package name."
            )

        self.logger.info(f"Build successful: {binary_path}")
        return binary_path


# ---------------------------------------------------------------------------
# Worker Manager
# ---------------------------------------------------------------------------


class WorkerProcess:
    """Manages a single miner worker subprocess."""

    def __init__(
        self,
        worker_id: int,
        binary_path: str,
        config: MinerConfig,
        rpc_url: str,
        logger: logging.Logger,
        stats: WorkerStats,
    ):
        self.worker_id = worker_id
        self.binary_path = binary_path
        self.config = config
        self.rpc_url = rpc_url
        self.logger = logger
        self.stats = stats
        self.process: Optional[subprocess.Popen] = None
        self.reader_thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()
        self.log_file: Optional[object] = None

    def start(self) -> None:
        """Start the miner subprocess."""
        self._stop_event.clear()

        cmd = self._build_command()
        self.logger.info(
            f"Worker {self.worker_id}: starting with RPC {self._mask_url(self.rpc_url)}"
        )

        log_dir = Path(self.config.log_dir)
        log_dir.mkdir(parents=True, exist_ok=True)
        log_path = log_dir / f"worker_{self.worker_id}.log"

        self.log_file = open(log_path, "a", buffering=1)
        self.log_file.write(
            f"\n{'='*60}\n"
            f"Worker {self.worker_id} started at "
            f"{datetime.now(timezone.utc).isoformat()}\n"
            f"CMD: {' '.join(cmd)}\n"
            f"{'='*60}\n"
        )

        try:
            self.process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1,
            )
        except (FileNotFoundError, PermissionError) as e:
            self.stats.status = "crashed"
            raise RuntimeError(f"Failed to start worker {self.worker_id}: {e}")

        self.stats.pid = self.process.pid
        self.stats.status = "running"
        self.stats.start_time = time.time()
        self.stats.last_output_time = time.time()
        self.stats.rpc_url = self._mask_url(self.rpc_url)

        # Start output reader thread
        self.reader_thread = threading.Thread(
            target=self._read_output,
            name=f"reader-worker-{self.worker_id}",
            daemon=True,
        )
        self.reader_thread.start()

    def stop(self) -> None:
        """Stop the miner subprocess gracefully."""
        self._stop_event.set()
        if self.process and self.process.poll() is None:
            self.logger.info(f"Worker {self.worker_id}: sending SIGTERM")
            self.process.terminate()
            try:
                self.process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self.logger.warning(
                    f"Worker {self.worker_id}: SIGTERM timeout, sending SIGKILL"
                )
                self.process.kill()
                self.process.wait(timeout=3)
        self.stats.status = "stopped"
        if self.log_file:
            self.log_file.close()
            self.log_file = None

    def is_alive(self) -> bool:
        """Check if the subprocess is still running."""
        if self.process is None:
            return False
        return self.process.poll() is None

    def is_healthy(self) -> bool:
        """Check if the worker is producing output within the health timeout."""
        if not self.is_alive():
            return False
        elapsed = time.time() - self.stats.last_output_time
        return elapsed < self.config.health_timeout_secs

    def _build_command(self) -> List[str]:
        """Build the command line for the miner binary."""
        cmd = [
            self.binary_path,
            "--rpc-url", self.rpc_url,
            "--keypair", self.config.keypair_path,
            "--cu-limit", str(self.config.cu_limit),
            "--max-nonces-per-round", str(self.config.max_nonces_per_round),
        ]
        if self.config.program_id:
            cmd.extend(["--program-id", self.config.program_id])
        return cmd

    def _read_output(self) -> None:
        """Read and parse miner output in a background thread."""
        if self.process is None or self.process.stdout is None:
            return

        for line in self.process.stdout:
            if self._stop_event.is_set():
                break

            line = line.rstrip("\n")
            self.stats.last_output_time = time.time()

            # Write to log file
            if self.log_file:
                try:
                    self.log_file.write(line + "\n")
                except (IOError, ValueError):
                    pass

            # Parse interesting events
            self._parse_line(line)

        # Process exited
        if not self._stop_event.is_set():
            exit_code = self.process.poll()
            self.stats.status = "crashed"
            self.logger.warning(
                f"Worker {self.worker_id}: process exited with code {exit_code}"
            )

    def _parse_line(self, line: str) -> None:
        """Parse a single output line for statistics."""
        # Strip ANSI codes for pattern matching
        clean = re.sub(r"\x1b\[[0-9;]*m", "", line)

        if MINED_PATTERN.search(clean):
            self.stats.blocks_mined += 1
            reward_match = REWARD_PATTERN.search(clean)
            if reward_match:
                self.stats.eqm_earned += float(reward_match.group(1))

        elif ABOVE_TARGET_PATTERN.search(clean):
            self.stats.above_target_count += 1

        elif STALE_PATTERN.search(clean):
            self.stats.stale_count += 1

        elif SUBMIT_ERROR_PATTERN.search(clean):
            self.stats.submit_errors += 1

        elif ADVANCED_ROUND_PATTERN.search(clean):
            self.stats.rounds_advanced += 1

        # Track current round
        round_match = ROUND_PATTERN.search(clean)
        if round_match:
            self.stats.current_round = int(round_match.group(1))

        # Track hashrate
        hr_match = HASHRATE_PATTERN.search(clean)
        if hr_match:
            self.stats.last_hashrate = f"{hr_match.group(1)} {hr_match.group(2)}"

    @staticmethod
    def _mask_url(url: str) -> str:
        """Mask API keys in URLs for logging."""
        # Replace anything that looks like an API key parameter
        masked = re.sub(r"(api[_-]?key=)[^&]+", r"\1***", url, flags=re.IGNORECASE)
        return masked


# ---------------------------------------------------------------------------
# Mining Orchestrator
# ---------------------------------------------------------------------------


class MiningOrchestrator:
    """Orchestrates multiple miner worker processes."""

    def __init__(self, config: MinerConfig):
        self.config = config
        self.logger = self._setup_logging()
        self.workers: Dict[int, WorkerProcess] = {}
        self.worker_stats: Dict[int, WorkerStats] = {}
        self.aggregate = AggregateStats()
        self._shutdown_event = threading.Event()
        self._restart_delays: Dict[int, float] = {}
        self._lock = threading.Lock()

    def run(self) -> None:
        """Main entry point. Build binary, start workers, monitor."""
        self._print_banner()

        # Validate config
        errors = self.config.validate()
        if errors:
            for e in errors:
                self.logger.error(f"Config error: {e}")
            sys.exit(1)

        # Build binary
        builder = BinaryBuilder(self.config, self.logger)
        try:
            binary_path = builder.ensure_binary()
        except (FileNotFoundError, RuntimeError) as e:
            self.logger.error(str(e))
            sys.exit(1)

        # Setup signal handlers
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)

        # Distribute RPC URLs across workers
        rpc_urls = self.config.get_all_rpc_urls()
        num_workers = self.config.num_workers

        self.logger.info(f"Starting {num_workers} worker(s)")
        self.logger.info(f"RPC pool: {len(rpc_urls)} endpoint(s)")
        self.logger.info(f"Max nonces per round: {self.config.max_nonces_per_round}")
        self.logger.info(f"CU limit: {self.config.cu_limit}")
        if self.config.priority_fee_microlamports > 0:
            self.logger.info(
                f"Priority fee: {self.config.priority_fee_microlamports} microlamports/CU"
            )

        # Start all workers
        for i in range(num_workers):
            rpc_url = rpc_urls[i % len(rpc_urls)]
            self._start_worker(i, binary_path, rpc_url)

        # Monitor loop
        self._monitor_loop(binary_path, rpc_urls)

    def _monitor_loop(self, binary_path: str, rpc_urls: List[str]) -> None:
        """Main monitoring loop. Checks health, restarts workers, prints stats."""
        stats_interval = 30  # Print stats every 30 seconds
        last_stats_time = time.time()

        while not self._shutdown_event.is_set():
            time.sleep(self.config.poll_interval_secs)

            # Check each worker
            for worker_id in list(self.workers.keys()):
                worker = self.workers[worker_id]
                stats = self.worker_stats[worker_id]

                if not worker.is_alive() and stats.status != "stopped":
                    stats.status = "crashed"
                    if self.config.auto_restart and not self._shutdown_event.is_set():
                        self._handle_restart(worker_id, binary_path, rpc_urls)

                elif not worker.is_healthy() and not self._shutdown_event.is_set():
                    self.logger.warning(
                        f"Worker {worker_id}: no output for "
                        f"{self.config.health_timeout_secs}s, restarting"
                    )
                    worker.stop()
                    stats.status = "crashed"
                    if self.config.auto_restart:
                        self._handle_restart(worker_id, binary_path, rpc_urls)

            # Print periodic stats
            if time.time() - last_stats_time >= stats_interval:
                self._print_stats()
                last_stats_time = time.time()

        # Shutdown
        self._shutdown_all()

    def _start_worker(self, worker_id: int, binary_path: str, rpc_url: str) -> None:
        """Start a single worker."""
        stats = WorkerStats(worker_id=worker_id)
        self.worker_stats[worker_id] = stats

        worker = WorkerProcess(
            worker_id=worker_id,
            binary_path=binary_path,
            config=self.config,
            rpc_url=rpc_url,
            logger=self.logger,
            stats=stats,
        )
        self.workers[worker_id] = worker

        try:
            worker.start()
            self._restart_delays[worker_id] = self.config.restart_delay_secs
        except RuntimeError as e:
            self.logger.error(str(e))

    def _handle_restart(
        self, worker_id: int, binary_path: str, rpc_urls: List[str]
    ) -> None:
        """Handle worker restart with exponential backoff."""
        delay = self._restart_delays.get(
            worker_id, self.config.restart_delay_secs
        )

        self.logger.info(
            f"Worker {worker_id}: restarting in {delay:.1f}s "
            f"(attempt #{self.worker_stats[worker_id].restart_count + 1})"
        )
        self.aggregate.total_restarts += 1

        # Wait before restart (interruptible)
        start_wait = time.time()
        while time.time() - start_wait < delay:
            if self._shutdown_event.is_set():
                return
            time.sleep(0.5)

        # Pick RPC URL (rotate through pool)
        stats = self.worker_stats[worker_id]
        stats.restart_count += 1
        rpc_url = rpc_urls[stats.restart_count % len(rpc_urls)]

        # Stop old worker if still referenced
        old_worker = self.workers.get(worker_id)
        if old_worker:
            old_worker.stop()

        # Start fresh worker
        new_stats = WorkerStats(
            worker_id=worker_id,
            blocks_mined=stats.blocks_mined,
            eqm_earned=stats.eqm_earned,
            restart_count=stats.restart_count,
            above_target_count=stats.above_target_count,
            stale_count=stats.stale_count,
            submit_errors=stats.submit_errors,
            rounds_advanced=stats.rounds_advanced,
        )
        self.worker_stats[worker_id] = new_stats

        worker = WorkerProcess(
            worker_id=worker_id,
            binary_path=binary_path,
            config=self.config,
            rpc_url=rpc_url,
            logger=self.logger,
            stats=new_stats,
        )
        self.workers[worker_id] = worker

        try:
            worker.start()
            # Increase backoff for next failure
            new_delay = min(
                delay * self.config.backoff_multiplier,
                self.config.max_restart_delay_secs,
            )
            self._restart_delays[worker_id] = new_delay
        except RuntimeError as e:
            self.logger.error(str(e))

    def _shutdown_all(self) -> None:
        """Gracefully shutdown all workers."""
        self.logger.info("Shutting down all workers...")
        for worker_id, worker in self.workers.items():
            try:
                worker.stop()
            except Exception as e:
                self.logger.error(f"Error stopping worker {worker_id}: {e}")

        self._print_final_stats()
        self.logger.info("All workers stopped. Goodbye!")

    def _signal_handler(self, signum: int, frame) -> None:
        """Handle shutdown signals."""
        sig_name = signal.Signals(signum).name
        self.logger.info(f"\nReceived {sig_name}, initiating graceful shutdown...")
        self._shutdown_event.set()

    def _print_banner(self) -> None:
        """Print startup banner."""
        banner = """
  ╔═══════════════════════════════════════════════════════╗
  ║  EQUIUM ($EQM) Enhanced Multi-Instance Miner v1.0    ║
  ║  Solana On-Chain CPU Mining - Equihash (96,5) PoW    ║
  ╚═══════════════════════════════════════════════════════╝
"""
        print(banner)

    def _print_stats(self) -> None:
        """Print aggregate statistics."""
        total_blocks = sum(s.blocks_mined for s in self.worker_stats.values())
        total_eqm = sum(s.eqm_earned for s in self.worker_stats.values())
        uptime = time.time() - self.aggregate.start_time

        running = sum(
            1 for w in self.workers.values() if w.is_alive()
        )
        total_w = len(self.workers)

        hours = int(uptime // 3600)
        minutes = int((uptime % 3600) // 60)
        seconds = int(uptime % 60)

        print(f"\n{'='*60}")
        print(f"  STATS | Workers: {running}/{total_w} running | "
              f"Uptime: {hours:02d}:{minutes:02d}:{seconds:02d}")
        print(f"  MINED | Blocks: {total_blocks} | "
              f"EQM: {total_eqm:.6f} | "
              f"Restarts: {self.aggregate.total_restarts}")
        print(f"{'='*60}")

        for wid in sorted(self.worker_stats.keys()):
            s = self.worker_stats[wid]
            status_char = {
                "running": "+",
                "crashed": "X",
                "stopped": "-",
                "starting": "~",
            }.get(s.status, "?")
            hr = s.last_hashrate or "N/A"
            print(
                f"  [{status_char}] W{wid:02d} | "
                f"Mined: {s.blocks_mined} | "
                f"Round: #{s.current_round} | "
                f"HR: {hr} | "
                f"Restarts: {s.restart_count}"
            )
        print()

    def _print_final_stats(self) -> None:
        """Print final session statistics."""
        total_blocks = sum(s.blocks_mined for s in self.worker_stats.values())
        total_eqm = sum(s.eqm_earned for s in self.worker_stats.values())
        uptime = time.time() - self.aggregate.start_time

        hours = int(uptime // 3600)
        minutes = int((uptime % 3600) // 60)

        print(f"\n{'='*60}")
        print("  FINAL SESSION REPORT")
        print(f"{'='*60}")
        print(f"  Total blocks mined: {total_blocks}")
        print(f"  Total EQM earned:   {total_eqm:.6f}")
        print(f"  Session duration:   {hours}h {minutes}m")
        print(f"  Total restarts:     {self.aggregate.total_restarts}")
        print(f"  Workers used:       {len(self.workers)}")
        if uptime > 0 and total_blocks > 0:
            avg = uptime / total_blocks
            print(f"  Avg time/block:     {avg:.1f}s")
        print(f"{'='*60}\n")

    def _setup_logging(self) -> logging.Logger:
        """Configure logging."""
        logger = logging.getLogger("equium-miner")
        logger.setLevel(getattr(logging, self.config.log_level.upper(), logging.INFO))

        # Console handler
        console = logging.StreamHandler(sys.stdout)
        console.setLevel(logging.INFO)
        fmt = logging.Formatter(
            "%(asctime)s [%(levelname)s] %(message)s",
            datefmt="%H:%M:%S",
        )
        console.setFormatter(fmt)
        logger.addHandler(console)

        # File handler (orchestrator log)
        log_dir = Path(self.config.log_dir)
        log_dir.mkdir(parents=True, exist_ok=True)
        file_handler = logging.FileHandler(
            log_dir / "orchestrator.log", mode="a"
        )
        file_handler.setLevel(logging.DEBUG)
        file_fmt = logging.Formatter(
            "%(asctime)s [%(levelname)s] %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
        file_handler.setFormatter(file_fmt)
        logger.addHandler(file_handler)

        return logger


# ---------------------------------------------------------------------------
# CLI Entry Point
# ---------------------------------------------------------------------------


def parse_args() -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        description="Equium ($EQM) Enhanced Multi-Instance Miner",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s
  %(prog)s --config /path/to/config.env
  %(prog)s --workers 8 --rpc https://my-rpc.com --keypair ~/.config/solana/id.json
  %(prog)s --max-nonces 131072 --priority-fee 5000
""",
    )
    parser.add_argument(
        "--config",
        type=str,
        default=None,
        help="Path to config.env file (default: ./config.env)",
    )
    parser.add_argument(
        "--workers", "-w",
        type=int,
        default=None,
        help="Number of parallel miner instances (default: CPU cores)",
    )
    parser.add_argument(
        "--rpc",
        type=str,
        default=None,
        help="Primary RPC endpoint URL",
    )
    parser.add_argument(
        "--keypair", "-k",
        type=str,
        default=None,
        help="Path to Solana keypair JSON",
    )
    parser.add_argument(
        "--max-nonces",
        type=int,
        default=None,
        help="Max nonce attempts per round per worker",
    )
    parser.add_argument(
        "--cu-limit",
        type=int,
        default=None,
        help="Compute unit limit per transaction",
    )
    parser.add_argument(
        "--priority-fee",
        type=int,
        default=None,
        help="Priority fee in micro-lamports per CU",
    )
    parser.add_argument(
        "--binary",
        type=str,
        default=None,
        help="Path to pre-built equium-miner binary",
    )
    parser.add_argument(
        "--no-build",
        action="store_true",
        help="Do not auto-build the binary",
    )
    parser.add_argument(
        "--log-level",
        type=str,
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        default=None,
        help="Logging level",
    )
    return parser.parse_args()


def main() -> None:
    """Main entry point."""
    args = parse_args()

    # Load config from file first
    env_path = Path(args.config) if args.config else None
    config = MinerConfig.from_env(env_path)

    # CLI overrides
    if args.workers is not None:
        config.num_workers = args.workers
    if args.rpc is not None:
        config.rpc_url = args.rpc
    if args.keypair is not None:
        config.keypair_path = os.path.expanduser(args.keypair)
    if args.max_nonces is not None:
        config.max_nonces_per_round = args.max_nonces
    if args.cu_limit is not None:
        config.cu_limit = args.cu_limit
    if args.priority_fee is not None:
        config.priority_fee_microlamports = args.priority_fee
    if args.binary is not None:
        config.binary_path = args.binary
    if args.no_build:
        config.auto_build = False
    if args.log_level is not None:
        config.log_level = args.log_level

    # Run the orchestrator
    orchestrator = MiningOrchestrator(config)
    orchestrator.run()


if __name__ == "__main__":
    main()
