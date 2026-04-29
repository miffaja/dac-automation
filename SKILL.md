# DAC Automation Agent Skill

## Tujuan
Bikin agent lain bisa langsung jalanin DAC automation end-to-end: login, refresh session, run auto tasks, debug error, dan schedule.

## Project Context
- Chain ID: `21894`
- RPC: `https://rpctest.dachain.tech`
- API: `https://inception.dachain.io/api/inception`
- Core files:
  - `dac_auto.py` (automation utama)
  - `dac-auth.js` (init auth + cookie extraction)
  - `dac-refresh.js` (refresh auth)

## Quick Start (Agent)
1. `cd /home/ubuntu/dac-automation`
2. `python3 --version && node --version`
3. `npm install`
4. `pip install requests web3`
5. `cp .env.example .env` lalu isi variable sensitif
6. Jalankan auth:
   - Server headless: `xvfb-run node dac-auth.js`
   - Desktop: `node dac-auth.js`
7. Run automation: `python3 dac_auto.py`

## Command Matrix
- `python3 dac_auto.py profile` → cek status akun
- `python3 dac_auto.py faucet` → claim faucet
- `python3 dac_auto.py crates 5` → buka crate
- `python3 dac_auto.py badges` → cek badge
- `python3 dac_auto.py tx 5` → self tx farming
- `python3 dac_auto.py sendto` → kirim ke address list

## Operational Loop (Agent-based)
1. Health check `profile`
2. Jika 401/session expired → run `xvfb-run node dac-refresh.js`
3. Retry `profile`
4. Jalankan `python3 dac_auto.py` full sequence
5. Simpan output/log error
6. Jika selector MetaMask fail, cek screenshot `/tmp/*.png`

## Error Playbook
- **HTTP 401**: session expired → refresh auth
- **No MetaMask popup**: UI selector berubah → update selector di js
- **Faucet cooldown**: bukan error, tunggu timer
- **Nonce/tx failed**: cek balance + nonce latest

## Cron Suggested
- 8 jam: `python3 dac_auto.py`
- 24 jam: `python3 dac_auto.py sendto`

## Security Rules
- Jangan commit `.env`, cookie, session, seed, private key real
- Pakai `.env.example` untuk template
- Redact credential di log/report
