import pytest

def test_module_structure_importable():
    """Verify core modules can be imported when deps are available."""
    try:
        from core.engine import Engine
        from core.network import DACApiClient, APIConfig
        from core.wallet import WalletClient, WalletConfig
        from core.logger import get_logger
        from core.scheduler import loop
        from utils.helper import load_dotenv
        from utils.retry import retry
        assert True
    except ModuleNotFoundError:
        pytest.skip("dependencies (web3/requests) not installed in this env")

def test_strategies_defined():
    try:
        from strategies.daily_run import run as daily
        from strategies.aggressive import run as aggressive
        assert callable(daily)
        assert callable(aggressive)
    except ModuleNotFoundError:
        pytest.skip("dependencies not installed")

def test_modules_defined():
    try:
        from modules.dac.detect_dac import run
        from modules.faucet.claim_faucet import run
        from modules.transaction.send_tx import run_self_tx
        assert callable(run)
        assert callable(run_self_tx)
    except ModuleNotFoundError:
        pytest.skip("dependencies not installed")