from core.engine import Engine

def run_self_tx(engine: Engine, count: int = 5, amount: float | None = None) -> list[str]:
    if not engine.wallet:
        raise RuntimeError('WALLET_PRIVATE_KEY missing')
    amount = amount if amount is not None else engine.cfg.default_tx_amount
    nonce = engine.wallet.nonce()
    out = []
    for i in range(count):
        out.append(engine.wallet.send(engine.wallet.address, amount, nonce + i))
    return out
