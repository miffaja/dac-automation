from dataclasses import dataclass
import os
from core.network import DACApiClient, APIConfig
from core.wallet import WalletClient, WalletConfig
from core.logger import get_logger
from utils.helper import load_dotenv

@dataclass
class AppConfig:
    base_api: str
    rpc_url: str
    chain_id: int
    cookie: str
    csrf: str
    private_key: str
    default_tx_amount: float

def load_config() -> AppConfig:
    load_dotenv()
    base_api = os.getenv('DAC_API_BASE', 'https://inception.dachain.io/api/inception').rstrip('/')
    rpc_url = os.getenv('RPC_URL', 'https://rpctest.dachain.tech')
    chain_id = int(os.getenv('CHAIN_ID', '21894'))
    sessionid = os.getenv('DAC_SESSIONID', '').strip()
    csrftoken = os.getenv('DAC_CSRFTOKEN', '').strip()
    ref_code = os.getenv('DAC_REF_CODE', '').strip()
    cookie = os.getenv('DAC_COOKIE', '').strip() or f"ref_code={ref_code}; csrftoken={csrftoken}; sessionid={sessionid}"
    private_key = os.getenv('WALLET_PRIVATE_KEY', '').strip()
    default_tx_amount = float(os.getenv('DEFAULT_TX_AMOUNT', '0.001'))
    return AppConfig(base_api, rpc_url, chain_id, cookie, csrftoken, private_key, default_tx_amount)

class Engine:
    def __init__(self) -> None:
        self.cfg = load_config()
        self.log = get_logger('engine')
        self.api = DACApiClient(APIConfig(self.cfg.base_api, self.cfg.csrf, self.cfg.cookie))
        self.wallet = WalletClient(WalletConfig(self.cfg.rpc_url, self.cfg.chain_id, self.cfg.private_key)) if self.cfg.private_key else None

    @property
    def ep(self) -> dict[str, str]:
        b = self.cfg.base_api
        return {
            'profile': f'{b}/profile/',
            'faucet': f'{b}/faucet/',
            'crate_open': f'{b}/crate/open/',
            'crate_history': f'{b}/crate/history/',
            'visit_explorer': f'{b}/visit/explorer/',
        }
