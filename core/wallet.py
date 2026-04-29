from dataclasses import dataclass
from web3 import Web3

@dataclass
class WalletConfig:
    rpc_url: str
    chain_id: int
    private_key: str

class WalletClient:
    def __init__(self, cfg: WalletConfig):
        self.cfg = cfg
        self.w3 = Web3(Web3.HTTPProvider(cfg.rpc_url))
        self.acct = self.w3.eth.account.from_key(cfg.private_key)

    @property
    def address(self) -> str:
        return self.acct.address

    def balance(self) -> float:
        return float(self.w3.from_wei(self.w3.eth.get_balance(self.address), 'ether'))

    def nonce(self) -> int:
        return self.w3.eth.get_transaction_count(self.address)

    def send(self, to: str, amount_eth: float, nonce: int | None = None) -> str:
        n = self.nonce() if nonce is None else nonce
        tx = {
            "chainId": self.cfg.chain_id,
            "from": self.address,
            "to": Web3.to_checksum_address(to),
            "value": self.w3.to_wei(amount_eth, "ether"),
            "gas": 21000,
            "gasPrice": self.w3.eth.gas_price,
            "nonce": n,
        }
        signed = self.acct.sign_transaction(tx)
        tx_hash = self.w3.eth.send_raw_transaction(signed.raw_transaction)
        return tx_hash.hex()
