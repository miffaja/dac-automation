#!/usr/bin/env python3
import argparse
import json
from core.engine import Engine
from strategies.daily_run import run as daily
from strategies.aggressive import run as aggressive
from modules.dac.detect_dac import run as profile
from modules.faucet.claim_faucet import run as faucet
from modules.transaction.send_tx import run_self_tx

def main() -> None:
    p = argparse.ArgumentParser(description='DAC Automation entrypoint')
    sub = p.add_subparsers(dest='cmd')
    sub.add_parser('profile')
    sub.add_parser('faucet')
    tx = sub.add_parser('tx')
    tx.add_argument('count', nargs='?', type=int, default=5)
    tx.add_argument('--amount', type=float, default=None)
    sub.add_parser('daily')
    sub.add_parser('aggressive')
    args = p.parse_args()

    eng = Engine()
    cmd = args.cmd or 'daily'
    if cmd == 'profile':
        out = profile(eng)
    elif cmd == 'faucet':
        out = faucet(eng)
    elif cmd == 'tx':
        out = {'tx_hashes': run_self_tx(eng, args.count, args.amount)}
    elif cmd == 'aggressive':
        out = aggressive(eng)
    else:
        out = daily(eng)
    print(json.dumps(out, indent=2, default=str))

if __name__ == '__main__':
    main()
