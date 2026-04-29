from core.engine import Engine

def run(engine: Engine) -> dict:
    return engine.api.get(engine.ep['profile'])
