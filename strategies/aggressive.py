from core.engine import Engine
from modules.transaction.send_tx import run_self_tx

def run(engine: Engine) -> dict:
    hashes = run_self_tx(engine, count=5)
    return {"tx_count": len(hashes), "tx_hashes": hashes}
