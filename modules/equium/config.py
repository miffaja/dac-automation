"""Configuration management for Equium miner.

Loads settings from environment variables or a .env file.
All settings have sensible defaults for immediate use.
"""

import os
import multiprocessing
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional


def _load_dotenv(env_path: Optional[Path] = None) -> None:
    """Load a .env file into os.environ if it exists."""
    if env_path is None:
        env_path = Path(__file__).parent / "config.env"
    if not env_path.exists():
        return
    with open(env_path, "r") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if "=" not in line:
                continue
            key, _, value = line.partition("=")
            key = key.strip()
            value = value.strip().strip('"').strip("'")
            if key and key not in os.environ:
                os.environ[key] = value


@dataclass
class MinerConfig:
    """Equium miner configuration."""

    # RPC endpoints
    rpc_url: str = "https://api.mainnet-beta.solana.com"
    rpc_fallbacks: List[str] = field(default_factory=list)

    # Wallet
    keypair_path: str = os.path.expanduser("~/.config/solana/id.json")

    # Worker settings
    num_workers: int = field(default_factory=lambda: max(1, multiprocessing.cpu_count()))
    max_nonces_per_round: int = 65536
    cu_limit: int = 1_400_000

    # Priority fee (micro-lamports per CU, 0 = disabled)
    priority_fee_microlamports: int = 0

    # Binary and build
    equium_source_dir: str = "/projects/sandbox/equium"
    binary_path: str = "/projects/sandbox/equium/target/release/equium-miner"
    auto_build: bool = True
    native_cpu_target: bool = True

    # Process management
    auto_restart: bool = True
    restart_delay_secs: float = 3.0
    max_restart_delay_secs: float = 60.0
    backoff_multiplier: float = 2.0
    health_timeout_secs: float = 300.0  # 5 min no output = dead

    # Logging
    log_dir: str = str(Path(__file__).parent / "logs")
    log_level: str = "INFO"
    max_log_size_mb: int = 50
    max_log_files: int = 10

    # Program IDs (Equium mainnet)
    program_id: str = "ZKGMUfxiRCXFPnqz9zgqAnuqJy15jk7fKbR4o6FuEQM"
    eqm_mint: str = "1MhvZzEe8gQ8Rb9CrT3Dn26Gkn9QRErzLMGkkTwveqm"

    # Poll interval between config fetches (seconds)
    poll_interval_secs: float = 2.0

    @classmethod
    def from_env(cls, env_path: Optional[Path] = None) -> "MinerConfig":
        """Load configuration from environment variables."""
        _load_dotenv(env_path)

        # Create a default instance to get computed defaults
        defaults = cls()

        rpc_fallbacks = []
        for i in range(1, 10):
            fb = os.environ.get(f"EQUIUM_RPC_FALLBACK_{i}", "")
            if fb:
                rpc_fallbacks.append(fb)

        return cls(
            rpc_url=os.environ.get("EQUIUM_RPC_URL", defaults.rpc_url),
            rpc_fallbacks=rpc_fallbacks,
            keypair_path=os.path.expanduser(
                os.environ.get("EQUIUM_KEYPAIR_PATH", defaults.keypair_path)
            ),
            num_workers=int(
                os.environ.get("EQUIUM_NUM_WORKERS", str(defaults.num_workers))
            ),
            max_nonces_per_round=int(
                os.environ.get("EQUIUM_MAX_NONCES", str(defaults.max_nonces_per_round))
            ),
            cu_limit=int(
                os.environ.get("EQUIUM_CU_LIMIT", str(defaults.cu_limit))
            ),
            priority_fee_microlamports=int(
                os.environ.get("EQUIUM_PRIORITY_FEE_LAMPORTS", "0")
            ),
            equium_source_dir=os.environ.get(
                "EQUIUM_SOURCE_DIR", defaults.equium_source_dir
            ),
            binary_path=os.environ.get(
                "EQUIUM_BINARY_PATH", defaults.binary_path
            ),
            auto_build=os.environ.get(
                "EQUIUM_AUTO_BUILD", "true"
            ).lower() == "true",
            native_cpu_target=os.environ.get(
                "EQUIUM_NATIVE_CPU", "true"
            ).lower() == "true",
            auto_restart=os.environ.get(
                "EQUIUM_AUTO_RESTART", "true"
            ).lower() == "true",
            restart_delay_secs=float(
                os.environ.get("EQUIUM_RESTART_DELAY_SECS", "3")
            ),
            max_restart_delay_secs=float(
                os.environ.get("EQUIUM_MAX_RESTART_DELAY_SECS", "60")
            ),
            backoff_multiplier=float(
                os.environ.get("EQUIUM_BACKOFF_MULTIPLIER", "2.0")
            ),
            health_timeout_secs=float(
                os.environ.get("EQUIUM_HEALTH_TIMEOUT_SECS", "300")
            ),
            log_dir=os.environ.get("EQUIUM_LOG_DIR", defaults.log_dir),
            log_level=os.environ.get("EQUIUM_LOG_LEVEL", defaults.log_level),
            max_log_size_mb=int(
                os.environ.get("EQUIUM_MAX_LOG_SIZE_MB", "50")
            ),
            max_log_files=int(os.environ.get("EQUIUM_MAX_LOG_FILES", "10")),
            program_id=os.environ.get(
                "EQUIUM_PROGRAM_ID", defaults.program_id
            ),
            eqm_mint=os.environ.get("EQUIUM_MINT", defaults.eqm_mint),
            poll_interval_secs=float(
                os.environ.get("EQUIUM_POLL_INTERVAL_SECS", "2.0")
            ),
        )

    def get_all_rpc_urls(self) -> List[str]:
        """Return primary + all fallback RPC URLs."""
        urls = [self.rpc_url]
        urls.extend(self.rpc_fallbacks)
        return urls

    def validate(self) -> List[str]:
        """Validate configuration. Returns list of error messages."""
        errors = []
        if not self.rpc_url:
            errors.append("EQUIUM_RPC_URL is required")
        if not self.keypair_path:
            errors.append("EQUIUM_KEYPAIR_PATH is required")
        elif not Path(self.keypair_path).exists():
            errors.append(f"Keypair file not found: {self.keypair_path}")
        if self.num_workers < 1:
            errors.append("EQUIUM_NUM_WORKERS must be >= 1")
        if self.max_nonces_per_round < 1:
            errors.append("EQUIUM_MAX_NONCES must be >= 1")
        if self.restart_delay_secs < 0:
            errors.append("EQUIUM_RESTART_DELAY_SECS must be >= 0")
        return errors
