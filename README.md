# DAC Inception Testnet Automation

Automated toolkit for interacting with [DAC Inception](https://inception.dachain.io) testnet — claim faucet, open crates, earn QE badges, and manage wallet connections via MetaMask.

## Overview

| Item | Detail |
|------|--------|
| **Chain ID** | 21894 |
| **RPC** | `https://rpctest.dachain.tech` |
| **API Base** | `https://inception.dachain.io/api/inception/` |
| **Network** | DAC Inception Testnet |
| **Wallet** | MetaMask (seed-phrase imported) |

## Project Structure

```
dac-automation/
├── dac_auth.js          # Initial MetaMask auth → extract session cookies
├── dac_refresh.js      # Session refresh / re-authenticate
├── dac_auto.py         # Main automation: faucet, crates, badges, tx
├── package.json        # Node.js dependencies (playwright)
└── README.md
```

## Features

- **🔐 MetaMask Authentication** — Browser automation to connect MetaMask wallet to DAC site and extract session cookies
- **💧 Faucet Claiming** — Auto-claim testnet tokens with cooldown tracking
- **📦 Crate Opening** — Open quantum crates (daily limit: 5)
- **🏅 Badge System** — Query catalog, check earned/unearned badges, claim exploration badges
- **💸 Transaction Sending** — Self-send and multi-address transactions for badge requirements
- **📊 Profile Monitoring** — QE balance, rank, streak, multiplier, referral stats

## Prerequisites

### System
- **OS**: Linux (Ubuntu 20.04+)
- **Python**: 3.10+
- **Node.js**: 18+

### Dependencies
```bash
# Python
pip install requests web3

# Node.js
npm install
```

### MetaMask Extension
```bash
# Install MetaMask extension to expected path
PLAYWRIGHT_BROWSERS_PATH=/home/ubuntu/metamask-agent
# Extension should be at: /home/ubuntu/metamask-agent/metamask/
```

## Installation

```bash
# Clone / navigate
cd ~/dac-automation

# Install Node dependencies
npm install

# Install Python dependencies
pip install requests web3
```

## Configuration

Edit these constants at the top of each file as needed:

### `dac-auth.js` / `dac-refresh.js`
```javascript
const SEED = "your 12-word seed phrase";
const PASSWORD = "your metamask password";
const DAC_URL = "https://inception.dachain.io/dashboard";
const EXT_PATH = "/home/ubuntu/metamask-agent/metamask";
```

### `dac_auto.py`
```python
COOKIE = "ref_code=DAC00014; csrftoken=YOUR_CSRFTOKEN; sessionid=YOUR_SESSIONID"
CSRF = "your_csrf_token"
BASE = "https://inception.dachain.io/api/inception"
```

## Usage

### Step 1 — Authenticate (Browser)

Extract fresh session cookies via MetaMask browser automation:

```bash
# Initial auth
node dac-auth.js

# Refresh / re-auth (if session expired)
node dac-refresh.js
```

This opens a visible Chromium browser with MetaMask extension, navigates to DAC, connects wallet, and saves cookies to `/tmp/dac-auth.json`.

> ⚠️ **Headful mode** — requires a display. Use `xvfb-run` on headless servers:
> ```bash
> xvfb-run node dac-auth.js
> ```

### Step 2 — Run Automation

```bash
# Full auto (all features)
python3 dac_auto.py

# Individual commands
python3 dac_auto.py profile      # Show account status
python3 dac_auto.py faucet      # Claim faucet
python3 dac_auto.py crates      # Open 5 crates
python3 dac_auto.py crates 3    # Open 3 crates
python3 dac_auto.py badges      # List all badges
python3 dac_auto.py explore     # Claim exploration badges
python3 dac_auto.py tx           # Send 5 self-TXs
python3 dac_auto.py tx 10       # Send 10 self-TXs
python3 dac_auto.py sendto       # Send to 5 preset addresses
python3 dac_auto.py claim <key>  # Claim specific badge
```

### Step 3 — Scheduled Automation (Cron)

Cron jobs handle ongoing automation:

| Job | Schedule | Command |
|-----|----------|---------|
| Auto Faucet Claim | Every 8h | `cd ~/dac-automation && python3 dac_auto.py` |
| Send to Addresses | Every 24h | `cd ~/dac-automation && python3 dac_auto.py sendto` |

## API Endpoints

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/profile/` | GET | Account info, QE balance, streak |
| `/faucet/status/` | GET | Faucet cooldown status |
| `/faucet/` | POST | Claim faucet tokens |
| `/crate/open/` | POST | Open quantum crate |
| `/badges/catalog/` | GET | All available badges |
| `/claim-badge/` | POST | Claim specific badge |
| `/visit/explorer/` | POST | Exploration badge credit |
| `/x/start/` | POST | Twitter task start |
| `/qe-history/` | GET | QE earnings history |

## Wallet & Keys

| Item | Value |
|------|-------|
| **Wallet Address** | `0xB594...0D2B` (redacted) |
| **Private Key** | `0xc50c...ca8a8` (hardcoded in `send_transactions`) |
| **Referral Code** | `DAC00014` |

> ⚠️ **Security Notice**: Private keys are hardcoded in source. For production, use environment variables or a secrets manager.

## Troubleshooting

### "Session expired" / 401 errors
Re-run `node dac-auth.js` to get fresh session cookies, then update `COOKIE` and `CSRF` in `dac_auto.py`.

### MetaMask popup not detected
The DAC site may have updated its UI. Check screenshots in `/tmp/`:
- `/tmp/dac-01-loaded.png` — DAC site loaded
- `/tmp/mm-popup-01.png` — MetaMask connect popup
- `/tmp/mm-popup-04.png` — MetaMask sign confirmation

### Faucet "not available" / cooldown
Normal behavior — faucet has a cooldown. The script prints remaining time:
```
Faucet in: 7h 23m
```

### Chromium sandbox errors on VPS
Add `--no-sandbox` flags (already included). On some VPS you may need:
```bash
sudo sysctl kernel.unprivileged_userns_clone=1
```

### Playwright browser not found
```bash
npx playwright install chromium
```

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                        User / Cron                          │
└──────────────────────────┬──────────────────────────────────┘
                           │
         ┌─────────────────┼─────────────────┐
         ▼                 ▼                 ▼
   ┌───────────┐    ┌───────────┐    ┌───────────────┐
   │ dac-auth.js│    │dac-refresh│    │  dac_auto.py  │
   │ (Node.js) │    │  .js      │    │  (Python)     │
   └─────┬─────┘    └─────┬─────┘    └───────┬───────┘
         │                 │                   │
         ▼                 │                   ▼
   Playwright +        Same as          DAC REST API
   MetaMask Ext       above            (requests)
         │                                 │
         ▼                                 ▼
   /tmp/dac-auth.json            ┌──────────────┐
   (sessionid,                    │ DAC Inception │
    csrftoken)                    │  Testnet      │
         │                        └──────────────┘
         └──────────────────────────────────────▶ (copy to
                                                    dac_auto.py)
```

## License

MIT — use at your own risk. Testnet tokens have no real value.
