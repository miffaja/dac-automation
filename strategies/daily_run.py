from core.engine import Engine
from modules.dac.detect_dac import run as profile
from modules.faucet.claim_faucet import run as faucet

def run(engine: Engine) -> dict:
    p = profile(engine)
    result = {"profile": p}
    if isinstance(p, dict) and p.get('faucet_available'):
        result['faucet'] = faucet(engine)
    return result
