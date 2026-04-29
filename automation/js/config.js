const fs = require('fs');
const path = require('path');

function loadEnv(file = '.env') {
  const p = path.resolve(process.cwd(), file);
  if (!fs.existsSync(p)) return;
  const lines = fs.readFileSync(p, 'utf8').split(/\r?\n/);
  for (const line of lines) {
    const s = line.trim();
    if (!s || s.startsWith('#') || !s.includes('=')) continue;
    const i = s.indexOf('=');
    const key = s.slice(0, i).trim();
    let val = s.slice(i + 1).trim();
    if ((val.startsWith('"') && val.endsWith('"')) || (val.startsWith("'") && val.endsWith("'"))) {
      val = val.slice(1, -1);
    }
    if (!(key in process.env)) process.env[key] = val;
  }
}

function getConfig() {
  loadEnv();
  const seed = process.env.METAMASK_SEED || '';
  const password = process.env.METAMASK_PASSWORD || '';
  const dacUrl = process.env.DAC_URL || 'https://inception.dachain.io/dashboard';
  const extPath = process.env.METAMASK_EXTENSION_PATH || '/home/ubuntu/metamask-agent/metamask';
  const headless = String(process.env.HEADLESS || 'false').toLowerCase() === 'true';

  if (!password) {
    throw new Error('METAMASK_PASSWORD missing in .env');
  }

  return { seed, password, dacUrl, extPath, headless };
}

module.exports = { getConfig };
