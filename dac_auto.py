#!/usr/bin/env python3
"""
DAC Inception Testnet Automation
Chain ID: 21894 | RPC: https://rpctest.dachain.tech
"""
import requests
import json
import time
import sys

# === CONFIG ===
COOKIE = "ref_code=DAC00014; csrftoken=lCxLgbdmq0UfeBnWu0MKxWEE38w9W6i8; sessionid=pdvvs61imuyjky5l1hpddzpzw0655psk"
CSRF = "lCxLgbdmq0UfeBnWu0MKxWEE38w9W6i8"
BASE = "https://inception.dachain.io/api/inception"
HEADERS = {
    "Cookie": COOKIE,
    "X-CSRFToken": CSRF,
    "Content-Type": "application/json",
    "Referer": "https://inception.dachain.io/dashboard",
    "Origin": "https://inception.dachain.io",
}

# === API ENDPOINTS FOUND IN JS ===
ENDPOINTS = {
    "profile": f"{BASE}/profile/",
    "config": f"{BASE}/config/",
    "network": f"{BASE}/network/",
    "faucet_status": f"{BASE}/faucet/status/",
    "faucet_claim": f"{BASE}/faucet/",
    "faucet_history": f"{BASE}/faucet-history/",
    "badges_catalog": f"{BASE}/badges/catalog/",
    "claim_badge": f"{BASE}/claim-badge/",
    "crate_open": f"{BASE}/crate/open/",
    "crate_history": f"{BASE}/crate/history/",
    "task": f"{BASE}/task/",
    "sync": f"{BASE}/sync/",
    "visit_explorer": f"{BASE}/visit/explorer/",
    "visit_page": f"{BASE}/visit/",
    "qe_history": f"{BASE}/qe-history/",
    "leaderboard": f"{BASE}/leaderboard/",
    "x_start": f"{BASE}/x/start/",
    "discord_start": f"{BASE}/discord/start/",
    "discord_status": f"{BASE}/discord/status/",
    "exchange_confirm_burn": f"{BASE}/exchange/confirm-burn/",
    "exchange_confirm_stake": f"{BASE}/exchange/confirm-stake/",
    "exchange_history": f"{BASE}/exchange/history/",
    "nft_claim_signature": f"{BASE}/nft/claim-signature/",
    "nft_confirm_mint": f"{BASE}/nft/confirm-mint/",
}


def api_get(endpoint):
    """GET request to DAC API"""
    try:
        r = requests.get(endpoint, headers=HEADERS, timeout=30)
        if r.status_code == 200:
            try:
                return r.json()
            except:
                return {"raw": r.text[:200], "status": r.status_code}
        return {"error": f"HTTP {r.status_code}", "body": r.text[:200]}
    except Exception as e:
        return {"error": str(e)}


def api_post(endpoint, data=None):
    """POST request to DAC API"""
    try:
        r = requests.post(endpoint, headers=HEADERS, json=data or {}, timeout=30)
        if r.status_code == 200:
            try:
                return r.json()
            except:
                return {"raw": r.text[:200], "status": r.status_code}
        return {"error": f"HTTP {r.status_code}", "body": r.text[:200]}
    except Exception as e:
        return {"error": str(e)}


def check_profile():
    """Get current profile status"""
    print("\n=== PROFILE ===")
    data = api_get(ENDPOINTS["profile"])
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
    if not data.get('faucet_available'):
        secs = data.get('faucet_seconds_left', 0)
        print(f"Faucet in: {secs//3600}h {(secs%3600)//60}m")
    print(f"Multiplier: {data.get('qe_multiplier')}x")
    print(f"Referrals: {data.get('referral_count')}")
    print(f"Discord: {data.get('discord_joined')}")
    print(f"Telegram: {data.get('telegram_joined')}")
    print(f"X Followed: {data.get('x_followed')}")
    return data


def claim_faucet():
    """Try to claim faucet"""
    print("\n=== FAUCET CLAIM ===")
    data = api_post(ENDPOINTS["faucet_claim"])
    print(json.dumps(data, indent=2))
    return data


def open_crates(max_opens=5):
    """Open quantum crates"""
    print(f"\n=== OPEN CRATES (max {max_opens}) ===")
    for i in range(max_opens):
        data = api_post(ENDPOINTS["crate_open"])
        print(f"Crate {i+1}: {json.dumps(data)}")
        if "error" in data:
            print(f"Stopped: {data['error']}")
            break
        if data.get("daily_limit_reached"):
            print("Daily limit reached!")
            break
        time.sleep(1)
    return data


def claim_exploration_badges():
    """Claim exploration-based badges"""
    print("\n=== EXPLORATION BADGES ===")
    results = []
    
    # Visit explorer
    data = api_post(ENDPOINTS["visit_explorer"])
    print(f"Explorer visit: {json.dumps(data)}")
    results.append(("explorer", data))
    
    return results


def claim_badge(badge_key):
    """Try to claim a specific badge"""
    data = api_post(ENDPOINTS["claim_badge"], {"badge_key": badge_key})
    return data


def send_transactions(count=5):
    """Send transactions to random addresses for tx badges"""
    import subprocess
    print(f"\n=== SENDING {count} SELF-TRANSACTIONS ===")
    
    script = '''
import sys
from web3 import Web3

w3 = Web3(Web3.HTTPProvider("https://rpctest.dachain.tech"))
pk = "0xc50c22e8648a580618a40cce6cee411cc6f5f94fa26e1a1e229216ae9c1ca8a8"
acct = w3.eth.account.from_key(pk)
nonce = w3.eth.get_transaction_count(acct.address)
count = int(sys.argv[1]) if len(sys.argv) > 1 else 5

print(f"Balance: {w3.from_wei(w3.eth.get_balance(acct.address), 'ether')} DACC | Nonce: {nonce}")

for i in range(count):
    try:
        tx = {
            "chainId": 21894,
            "from": acct.address,
            "to": acct.address,
            "value": w3.to_wei(0.001, "ether"),
            "gas": 21000,
            "gasPrice": w3.eth.gas_price,
            "nonce": nonce + i,
        }
        signed = acct.sign_transaction(tx)
        tx_hash = w3.eth.send_raw_transaction(signed.raw_transaction)
        print(f"  TX {i+1}/{count}: {tx_hash.hex()[:20]}...")
    except Exception as e:
        print(f"  TX {i+1} FAILED: {e}")
        break
print("Done!")
'''
    result = subprocess.run(
        ["/usr/bin/python3", "-c", script, str(count)],
        capture_output=True, text=True, timeout=60
    )
    print(result.stdout)
    if result.stderr:
        print(f"STDERR: {result.stderr[:200]}")
    return result.returncode == 0


def send_to_addresses():
    """Send 0.0001 DACC to specific addresses for tx_3_wallets badge"""
    import subprocess
    ADDRS = [
        "0xAf53878bFc9C00E37202Dd47090Fd36D353D7745",
        "0x43e51344fb7df0769b1ede9aed211780a376549d",
        "0x6661497c8d3e27c4aff8587301a289058a7d7103",
        "0x73FFFCfD2AEd996918B4956dA60FfB49fe4b0175",
        "0x18982D7aa3C841237844f5914Fc4e6823EA0929F",
    ]
    AMOUNT = 0.001  # DACC per address
    print(f"\n=== SEND TO {len(ADDRS)} ADDRESSES ({AMOUNT} DACC each) ===")
    
    script = '''
import sys, json
from web3 import Web3

w3 = Web3(Web3.HTTPProvider("https://rpctest.dachain.tech"))
pk = "0xc50c22e8648a580618a40cce6cee411cc6f5f94fa26e1a1e229216ae9c1ca8a8"
acct = w3.eth.account.from_key(pk)
addrs = json.loads(sys.argv[1])
amount = float(sys.argv[2])
nonce = w3.eth.get_transaction_count(acct.address)

print(f"Balance: {w3.from_wei(w3.eth.get_balance(acct.address), 'ether')} DACC | Nonce: {nonce}")

for i, addr in enumerate(addrs):
    try:
        tx = {
            "chainId": 21894,
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
        print(f"  {addr[:10]}... FAILED: {e}")
        break
print("Done!")
'''
    result = subprocess.run(
        ["/usr/bin/python3", "-c", script, json.dumps(ADDRS), str(AMOUNT)],
        capture_output=True, text=True, timeout=60
    )
    print(result.stdout)
    if result.stderr:
        print(f"STDERR: {result.stderr[:200]}")
    return result.returncode == 0


def check_all_badges():
    """Check which badges can be claimed"""
    print("\n=== BADGE STATUS ===")
    profile = api_get(ENDPOINTS["profile"])
    earned = {b["badge__key"] for b in profile.get("badges", [])}
    print(f"Earned: {len(earned)} badges")
    
    catalog = api_get(ENDPOINTS["badges_catalog"])
    if "badges" in catalog:
        unearned = [b for b in catalog["badges"] if b["key"] not in earned]
        print(f"\nUnearned badges ({len(unearned)}):")
        for b in unearned[:20]:
            print(f"  {b['key']:30s} | {b['name']:20s} | QE: {b['qe_reward']:5d} | {b['description'][:50]}")
    
    return earned


def full_auto():
    """Run full automation sequence"""
    print("=" * 60)
    print("DAC INCEPTION AUTOMATION")
    print("=" * 60)
    
    # 1. Check profile
    profile = check_profile()
    if not profile:
        print("Cannot load profile. Session may be expired.")
        sys.exit(1)
    
    # 2. Claim exploration badges
    claim_exploration_badges()
    
    # 3. Try faucet claim
    if profile.get("faucet_available"):
        claim_faucet()
    else:
        secs = profile.get("faucet_seconds_left", 0)
        print(f"\nFaucet not ready. Wait {secs//3600}h {(secs%3600)//60}m")
    
    # 4. Open crates (check daily limit)
    crate_data = api_get(ENDPOINTS["crate_history"])
    if "opens_today" in crate_data:
        remaining = crate_data.get("daily_open_limit", 5) - crate_data.get("opens_today", 0)
        if remaining > 0:
            open_crates(remaining)
        else:
            print(f"\nCrates: {crate_data['opens_today']}/{crate_data['daily_open_limit']} used today")
    
    # 5. Send transactions for tx badges
    send_transactions(5)
    
    # 6. Check all badges
    check_all_badges()
    
    # 6. Check QE history
    print("\n=== QE SUMMARY ===")
    qe = api_get(ENDPOINTS["qe_history"])
    if "totals_by_category" in qe:
        for cat, total in qe["totals_by_category"].items():
            print(f"  {cat:15s}: {total:5d} QE")
        print(f"  {'TOTAL':15s}: {qe.get('total_earned_qe', 0):5d} QE")
    
    print("\n" + "=" * 60)
    print("AUTOMATION COMPLETE")
    print("=" * 60)


if __name__ == "__main__":
    if len(sys.argv) > 1:
        cmd = sys.argv[1]
        if cmd == "profile":
            check_profile()
        elif cmd == "faucet":
            claim_faucet()
        elif cmd == "crates":
            open_crates(int(sys.argv[2]) if len(sys.argv) > 2 else 5)
        elif cmd == "badges":
            check_all_badges()
        elif cmd == "explore":
            claim_exploration_badges()
        elif cmd == "tx":
            send_transactions(int(sys.argv[2]) if len(sys.argv) > 2 else 5)
        elif cmd == "sendto":
            send_to_addresses()
        elif cmd == "claim":
            if len(sys.argv) > 2:
                result = claim_badge(sys.argv[2])
                print(json.dumps(result, indent=2))
            else:
                print("Usage: dac_auto.py claim <badge_key>")
        else:
            print(f"Unknown command: {cmd}")
            print("Commands: profile, faucet, crates [N], badges, explore, tx [N], claim <key>")
    else:
        full_auto()
