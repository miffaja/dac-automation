import time
from core.engine import Engine
from strategies.daily_run import run as daily

def loop(interval_seconds: int = 3600) -> None:
    engine = Engine()
    while True:
        result = daily(engine)
        engine.log.info('daily_run=%s', result)
        time.sleep(interval_seconds)
