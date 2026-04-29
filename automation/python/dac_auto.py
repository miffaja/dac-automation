#!/usr/bin/env python3
"""DAC Inception Testnet Automation (Agent-ready)."""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import requests
from web3 import Web3


def load_dotenv(path: str = ".env") -> None:
    p = Path(path)
    if not p.exists():
        return
    for line in p.read_text(encoding="utf-8").splitlines():
        s = line.strip()
        if not s or s.startswith("#") or "=" not in s:
            continue
        k, v = s.split("=", 1)
        k = k.strip()
        v = v.strip().strip('"').strip("'")
        if k and k not in os.environ:
            os.environ[k] = v


@dataclass
class Settings:
    base_api: str
    rpc_url: str
    chain_id: int
    csrf_token: str
    cookie: str
    wallet_private_key: str
    default_tx_amount: float

    @classmethod
    def from_env(cls) -> "Settings":
        load_dotenv()
        base_api = os.getenv("DAC_API_BASE", "https://inception.dachain.io/api/inception").rstrip("/")
        rpc_url = os.getenv("RPC_URL", "https://rpctest.dachain.tech")
        chain_id = int(os.getenv("CHAIN_ID", "21894"))

        sessionid = os.getenv("DAC_SESSIONID", "").strip()
        csrftoken = os.getenv("DAC_CSRFTOKEN", "").strip()
        ref_code = os.getenv("DAC_REF_CODE", "").strip()

        cookie = os.getenv("DAC_COOKIE", "").strip()
        if not cookie and sessionid and csrftoken:
            cookie = f"ref_code={ref_code}; csrftoken={csrftoken}; sessionid={sessionid}"

        wallet_private_key = os.getenv("WALLET_PRIVATE_KEY", "").strip()
        default_tx_amount = float(os.getenv("DEFAULT_TX_AMOUNT", "0.001"))

        return cls(
            base_api=base_api,
            rpc_url=rpc_url,
            chain_id=chain_id,
            csrf_token=csrftoken,
            cookie=cookie,
            wallet_private_key=wallet_private_key,
            default_tx_amount=default_tx_amount,
        )


class DACClient:
    def __init__(self, settings: Settings):
        self.settings = settings
        self.session = requests.Session()
        self.session.headers.update(
            {
                "Content-Type": "application/json",
                "Referer": "https://inception.dachain.io/dashboard",
                "Origin": "https://inception.dachain.io",
            }
        )
        if settings.csrf_token:
            self.session.headers["X-CSRFToken"] = settings.csrf_token
        if settings.cookie:
            self.session.headers["Cookie"] = settings.cookie

        b = settings.base_api
        self.endpoints = {
            "profile": f"{b}/profile/",
            "faucet_claim": f"{b}/faucet/",
            "crate_open": f"{b}/crate/open/",
            "crate_history": f"{b}/crate/history/",
            "badges_catalog": f"{b}/badges/catalog/",
            "claim_badge": f"{b}/claim-badge/",
            "visit_explorer": f"{b}/visit/explorer/",
            "qe_history": f"{b}/qe-history/",
        }

    def get(self, endpoint: str) -> dict[str, Any]:
        try:
            r = self.session.get(endpoint, timeout=30)
            if r.status_code == 200:
                try:
                    return r.json()
                except Exception:
                    return {"raw": r.text[:200], "status": r.status_code}
            return {"error": f"HTTP {r.status_code}", "body": r.text[:200]}
        except Exception as e:
            return {"error": str(e)}

    def post(self, endpoint: str, data: dict[str, Any] | None = None) -> dict[str, Any]:
        try:
            r = self.session.post(endpoint, json=data or {}, timeout=30)
            if r.status_code == 200:
                try:
                    return r.json()
                except Exception:
                    return {"raw": r.text[:200], "status": r.status_code}
            return {"error": f"HTTP {r.status_code}", "body": r.text[:200]}
        except Exception as e:
            return {"error": str(e)}


def bootstrap_session_from_tmp() -> bool:
    p = Path("/tmp/dac-auth.json")
    if not p.exists():
        return False
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
        sessionid = data.get("sessionid", "")
        csrftoken = data.get("csrftoken", "")
        if not sessionid or not csrftoken:
            return False

        env_path = Path(".env")
        lines = env_path.read_text(encoding="utf-8").splitlines() if env_path.exists() else []
        kv = {}
        for line in lines:
            if "=" in line and not line.strip().startswith("#"):
                k, v = line.split("=", 1)
                kv[k.strip()] = v

        kv["DAC_SESSIONID"] = f'"{sessionid}"'
        kv["DAC_CSRFTOKEN"] = f'"{csrftoken}"'
        kv["DAC_COOKIE"] = '"ref_code=${DAC_REF_CODE}; csrftoken=${DAC_CSRFTOKEN}; sessionid=${DAC_SESSIONID}"'

        out: list[str] = []
        used = set()
        for line in lines:
            if "=" in line and not line.strip().startswith("#"):
                k = line.split("=", 1)[0].strip()
                if k in kv:
                    out.append(f"{k}={kv[k]}")
                    used.add(k)
                else:
                    out.append(line)
            else:
                out.append(line)
        for k, v in kv.items():
            if k not in used:
                out.append(f"{k}={v}")

        env_path.write_text("\n".join(out).rstrip() + "\n", encoding="utf-8")
        return True
    except Exception:
        return False


def require_auth(settings: Settings) -> None:
    if settings.cookie and settings.csrf_token:
        return
    if bootstrap_session_from_tmp():
        load_dotenv()
        return
    print("ERROR: Missing DAC session env. Run: npm run auth or npm run refresh-auth", file=sys.stderr)
    sys.exit(2)


def check_profile(client: DACClient) -> dict[str, Any] | None:
    print("\n=== PROFILE ===")
    data = client.get(client.endpoints["profile"])
    if "error" in data:
        print(f"ERROR: {data['error']}")
        return None
    print(f"Username: {data.get('username')}")
    print(f"QE Balance: {data.get('qe_balance')}")
    print(f"DACC Balance: {data.get('dacc_balance')}")
    print(f"Rank: {data.get('user_rank')}")
    print(f"Badges: {len(data.get('badges', []))}")
    print(f"Streak: {data.get('streak_days')} days")
    print(f"Faucet available: {data.get('faucet_available')}")
    return data


def claim_faucet(client: DACClient) -> dict[str, Any]:
    print("\n=== FAUCET CLAIM ===")
    data = client.post(client.endpoints["faucet_claim"])
    print(json.dumps(data, indent=2))
    return data


def open_crates(client: DACClient, max_opens: int = 5) -> dict[str, Any] | None:
    print(f"\n=== OPEN CRATES (max {max_opens}) ===")
    last = None
    for i in range(max_opens):
        data = client.post(client.endpoints["crate_open"])
        print(f"Crate {i+1}: {json.dumps(data)}")
        last = data
        if "error" in data or data.get("daily_limit_reached"):
            break
        time.sleep(1)
    return last


def claim_exploration_badges(client: DACClient) -> None:
    print("\n=== EXPLORATION BADGES ===")
    data = client.post(client.endpoints["visit_explorer"])
    print(f"Explorer visit: {json.dumps(data)}")


def check_all_badges(client: DACClient) -> set[str]:
    print("\n=== BADGE STATUS ===")
    profile = client.get(client.endpoints["profile"])
    earned = {b["badge__key"] for b in profile.get("badges", [])} if isinstance(profile, dict) else set()
    print(f"Earned: {len(earned)} badges")
    catalog = client.get(client.endpoints["badges_catalog"])
    if "badges" in catalog:
        unearned = [b for b in catalog["badges"] if b["key"] not in earned]
        for b in unearned[:20]:
            print(f"  {b['key']:30s} | {b['name']:20s} | QE: {b['qe_reward']:5d}")
    return earned


def send_transactions(settings: Settings, count: int = 5, amount: float | None = None) -> bool:
    if not settings.wallet_private_key:
        print("ERROR: WALLET_PRIVATE_KEY missing in .env")
        return False
    amount = amount if amount is not None else settings.default_tx_amount
    print(f"\n=== SENDING {count} SELF-TRANSACTIONS ({amount} DACC each) ===")
    w3 = Web3(Web3.HTTPProvider(settings.rpc_url))
    acct = w3.eth.account.from_key(settings.wallet_private_key)
    nonce = w3.eth.get_transaction_count(acct.address)
    print(f"Balance: {w3.from_wei(w3.eth.get_balance(acct.address), 'ether')} DACC | Nonce: {nonce}")
    ok = True
    for i in range(count):
        try:
            tx = {
                "chainId": settings.chain_id,
                "from": acct.address,
                "to": acct.address,
                "value": w3.to_wei(amount, "ether"),
                "gas": 21000,
                "gasPrice": w3.eth.gas_price,
                "nonce": nonce + i,
            }
            signed = acct.sign_transaction(tx)
            tx_hash = w3.eth.send_raw_transaction(signed.raw_transaction)
            print(f"  TX {i+1}/{count}: {tx_hash.hex()[:20]}...")
        except Exception as e:
            ok = False
            print(f"  TX {i+1} FAILED: {e}")
            break
    return ok


def send_to_addresses(settings: Settings, addresses: list[str], amount: float) -> bool:
    if not settings.wallet_private_key:
        print("ERROR: WALLET_PRIVATE_KEY missing in .env")
        return False
    print(f"\n=== SEND TO {len(addresses)} ADDRESSES ({amount} DACC each) ===")
    w3 = Web3(Web3.HTTPProvider(settings.rpc_url))
    acct = w3.eth.account.from_key(settings.wallet_private_key)
    nonce = w3.eth.get_transaction_count(acct.address)
    print(f"Balance: {w3.from_wei(w3.eth.get_balance(acct.address), 'ether')} DACC | Nonce: {nonce}")
    ok = True
    for i, addr in enumerate(addresses):
        try:
            tx = {
                "chainId": settings.chain_id,
                "from": acct.address,
                "to": Web3.to_checksum_address(addr),
                "value": w3.to_wei(amount, "ether"),
                "gas": 21000,
                "gasPrice": w3.eth.gas_price,
                "nonce": nonce + i,
            }
            signed = acct.sign_transaction(tx)
            tx_hash = w3.eth.send_raw_transaction(signed.raw_transaction)
            print(f"  {addr[:10]}...{addr[-4:]}: {tx_hash.hex()[:20]}...")
        except Exception as e:
            ok = False
            print(f"  {addr[:10]}... FAILED: {e}")
            break
    return ok


def full_auto(client: DACClient, settings: Settings) -> None:
    print("=" * 60)
    print("DAC INCEPTION AUTOMATION")
    print("=" * 60)

    profile = check_profile(client)
    if not profile:
        print("Cannot load profile. Session may be expired.")
        sys.exit(1)

    claim_exploration_badges(client)

    if profile.get("faucet_available"):
        claim_faucet(client)

    crate_data = client.get(client.endpoints["crate_history"])
    if "opens_today" in crate_data:
        remaining = crate_data.get("daily_open_limit", 5) - crate_data.get("opens_today", 0)
        if remaining > 0:
            open_crates(client, remaining)

    send_transactions(settings, 5)
    check_all_badges(client)


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="DAC Inception automation toolkit")
    sub = p.add_subparsers(dest="command")
    sub.add_parser("profile")
    sub.add_parser("faucet")
    c = sub.add_parser("crates")
    c.add_argument("count", nargs="?", type=int, default=5)
    sub.add_parser("badges")
    sub.add_parser("explore")
    tx = sub.add_parser("tx")
    tx.add_argument("count", nargs="?", type=int, default=5)
    tx.add_argument("--amount", type=float, default=None)
    st = sub.add_parser("sendto")
    st.add_argument("--amount", type=float, default=0.001)
    st.add_argument("--addresses-file", default="automation/config/addresses.txt")
    sub.add_parser("full")
    sub.add_parser("bootstrap-session")
    return p


def load_addresses(path: str) -> list[str]:
    p = Path(path)
    if not p.exists():
        return []
    return [line.strip() for line in p.read_text(encoding="utf-8").splitlines() if line.strip() and not line.strip().startswith("#")]


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()

    if args.command == "bootstrap-session":
        ok = bootstrap_session_from_tmp()
        print("OK" if ok else "FAILED")
        return

    settings = Settings.from_env()
    require_auth(settings)
    settings = Settings.from_env()
    client = DACClient(settings)

    cmd = args.command or "full"
    if cmd == "profile":
        check_profile(client)
    elif cmd == "faucet":
        claim_faucet(client)
    elif cmd == "crates":
        open_crates(client, args.count)
    elif cmd == "badges":
        check_all_badges(client)
    elif cmd == "explore":
        claim_exploration_badges(client)
    elif cmd == "tx":
        send_transactions(settings, args.count, args.amount)
    elif cmd == "sendto":
        addresses = load_addresses(args.addresses_file)
        if not addresses:
            print(f"No addresses found in {args.addresses_file}")
            sys.exit(1)
        send_to_addresses(settings, addresses, args.amount)
    else:
        full_auto(client, settings)


if __name__ == "__main__":
    main()
