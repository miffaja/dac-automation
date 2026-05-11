#!/usr/bin/env python3
"""Equium Mining Monitor - Real-time stats viewer.

Reads log files produced by the enhanced miner and displays a live dashboard
with aggregate hashrate, blocks mined, EQM earned, uptime, and per-worker
status.

Can also be used to tail logs of specific workers.

Usage:
  python3 monitor.py                   # Live dashboard
  python3 monitor.py --worker 0        # Tail worker 0 output
  python3 monitor.py --summary         # One-time summary
"""

import argparse
import os
import re
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional

sys.path.insert(0, str(Path(__file__).parent))
from config import MinerConfig

# Pattern matchers (same as enhanced_miner)
MINED_PATTERN = re.compile(r"MINED!")
REWARD_PATTERN = re.compile(r"\+(\d+(?:\.\d+)?)\s*EQM")
HASHRATE_PATTERN = re.compile(r"([\d.]+)\s*(H/s|kH/s)")
ROUND_PATTERN = re.compile(r"round #(\d+)")
ABOVE_TARGET_PATTERN = re.compile(r"above target")
ANSI_ESCAPE = re.compile(r"\x1b\[[0-9;]*m")


class WorkerLogStats:
    """Stats parsed from a single worker log file."""

    def __init__(self, worker_id: int):
        self.worker_id = worker_id
        self.blocks_mined: int = 0
        self.eqm_earned: float = 0.0
        self.above_target_count: int = 0
        self.last_hashrate: str = "N/A"
        self.current_round: int = 0
        self.last_activity: Optional[datetime] = None
        self.start_count: int = 0
        self.line_count: int = 0

    def parse_line(self, line: str) -> None:
        """Parse a log line and update stats."""
        clean = ANSI_ESCAPE.sub("", line)
        self.line_count += 1

        if MINED_PATTERN.search(clean):
            self.blocks_mined += 1
            reward_match = REWARD_PATTERN.search(clean)
            if reward_match:
                self.eqm_earned += float(reward_match.group(1))

        if ABOVE_TARGET_PATTERN.search(clean):
            self.above_target_count += 1

        round_match = ROUND_PATTERN.search(clean)
        if round_match:
            self.current_round = int(round_match.group(1))

        hr_match = HASHRATE_PATTERN.search(clean)
        if hr_match:
            self.last_hashrate = f"{hr_match.group(1)} {hr_match.group(2)}"

        if "Worker" in clean and "started at" in clean:
            self.start_count += 1


def scan_worker_logs(log_dir: str) -> Dict[int, WorkerLogStats]:
    """Scan all worker log files and parse stats."""
    log_path = Path(log_dir)
    stats: Dict[int, WorkerLogStats] = {}

    if not log_path.exists():
        return stats

    for log_file in sorted(log_path.glob("worker_*.log")):
        match = re.match(r"worker_(\d+)\.log", log_file.name)
        if not match:
            continue

        worker_id = int(match.group(1))
        ws = WorkerLogStats(worker_id)

        try:
            with open(log_file, "r", errors="replace") as f:
                for line in f:
                    ws.parse_line(line.rstrip("\n"))
            ws.last_activity = datetime.fromtimestamp(
                log_file.stat().st_mtime, tz=timezone.utc
            )
        except (IOError, OSError):
            pass

        stats[worker_id] = ws

    return stats


def print_dashboard(log_dir: str) -> None:
    """Print a one-time dashboard of mining status."""
    stats = scan_worker_logs(log_dir)

    if not stats:
        print("No worker logs found. Is the miner running?")
        print(f"Log directory: {log_dir}")
        return

    total_blocks = sum(s.blocks_mined for s in stats.values())
    total_eqm = sum(s.eqm_earned for s in stats.values())
    total_attempts = sum(s.above_target_count + s.blocks_mined for s in stats.values())

    # Check orchestrator log for start time
    orch_log = Path(log_dir) / "orchestrator.log"
    start_time_str = "Unknown"
    if orch_log.exists():
        try:
            with open(orch_log, "r") as f:
                first_line = f.readline()
            if first_line:
                ts_match = re.match(r"(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})", first_line)
                if ts_match:
                    start_time_str = ts_match.group(1)
        except IOError:
            pass

    print()
    print("=" * 62)
    print("  EQUIUM MINING MONITOR")
    print("=" * 62)
    print(f"  Log directory:    {log_dir}")
    print(f"  Session start:    {start_time_str}")
    print(f"  Workers tracked:  {len(stats)}")
    print()
    print(f"  Total blocks mined:   {total_blocks}")
    print(f"  Total EQM earned:     {total_eqm:.6f}")
    print(f"  Total solve attempts: {total_attempts}")
    if total_attempts > 0:
        win_rate = (total_blocks / total_attempts) * 100
        print(f"  Win rate:             {win_rate:.2f}%")
    print()
    print("-" * 62)
    print(f"  {'WID':<5} {'Blocks':<8} {'EQM':<12} {'Round':<8} {'Hashrate':<12} {'Restarts'}")
    print("-" * 62)

    for wid in sorted(stats.keys()):
        s = stats[wid]
        print(
            f"  W{wid:<3} {s.blocks_mined:<8} "
            f"{s.eqm_earned:<12.6f} "
            f"#{s.current_round:<7} "
            f"{s.last_hashrate:<12} "
            f"{s.start_count - 1}"  # first start is not a restart
        )
    print("=" * 62)
    print()


def tail_worker_log(log_dir: str, worker_id: int, follow: bool = True) -> None:
    """Tail a specific worker's log file."""
    log_file = Path(log_dir) / f"worker_{worker_id}.log"

    if not log_file.exists():
        print(f"Log file not found: {log_file}")
        return

    print(f"Tailing {log_file}...")
    print("-" * 60)

    with open(log_file, "r") as f:
        # Print last 50 lines first
        lines = f.readlines()
        start = max(0, len(lines) - 50)
        for line in lines[start:]:
            print(line, end="")

        if not follow:
            return

        # Follow mode
        try:
            while True:
                line = f.readline()
                if line:
                    print(line, end="")
                else:
                    time.sleep(0.5)
        except KeyboardInterrupt:
            print("\nStopped.")


def live_dashboard(log_dir: str, interval: float = 5.0) -> None:
    """Continuously refresh the dashboard."""
    try:
        while True:
            # Clear screen
            os.system("clear" if os.name == "posix" else "cls")
            print(f"  [Auto-refresh every {interval}s | Ctrl+C to stop]")
            print_dashboard(log_dir)
            time.sleep(interval)
    except KeyboardInterrupt:
        print("\nMonitor stopped.")


def main() -> None:
    """CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Equium Mining Monitor",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--log-dir",
        type=str,
        default=None,
        help="Path to log directory",
    )
    parser.add_argument(
        "--config",
        type=str,
        default=None,
        help="Path to config.env file",
    )
    parser.add_argument(
        "--worker",
        type=int,
        default=None,
        help="Tail a specific worker's log (by ID)",
    )
    parser.add_argument(
        "--summary",
        action="store_true",
        help="Print one-time summary and exit",
    )
    parser.add_argument(
        "--interval",
        type=float,
        default=5.0,
        help="Dashboard refresh interval in seconds (default: 5)",
    )
    args = parser.parse_args()

    # Determine log directory
    if args.log_dir:
        log_dir = args.log_dir
    else:
        env_path = Path(args.config) if args.config else None
        config = MinerConfig.from_env(env_path)
        log_dir = config.log_dir

    if args.worker is not None:
        tail_worker_log(log_dir, args.worker, follow=not args.summary)
    elif args.summary:
        print_dashboard(log_dir)
    else:
        live_dashboard(log_dir, args.interval)


if __name__ == "__main__":
    main()
