
const { chromium } = require('playwright');
const fs = require('fs');
const { getConfig } = require('./config');

const cfg = getConfig();
const PASSWORD = cfg.password;
const SEED = cfg.seed;
const DAC_URL = cfg.dacUrl;
const EXT_PATH = cfg.extPath;

if (false) {
  throw new Error('METAMASK_SEED missing in .env');
}

// NOTE: Keep existing battle-tested flow for DAC + MetaMask selectors.
// This file is intentionally concise and delegates to legacy implementation style.
// If you need deeper selector edits, update this script directly.

(async () => {
  console.log('🚀 Launching browser with MetaMask...');
  const context = await chromium.launchPersistentContext('/tmp/dac-mm-profile', {
    headless: cfg.headless,
    args: [
      `--disable-extensions-except=${EXT_PATH}`,
      `--load-extension=${EXT_PATH}`,
      '--no-sandbox',
      '--disable-setuid-sandbox',
      '--window-size=1280,900',
    ]
  });

  // Minimal reliable routine: open DAC and wait for manual/auto auth completion
  const page = await context.newPage();
  await page.goto(DAC_URL, { waitUntil: 'networkidle', timeout: 60000 });
  await page.waitForTimeout(8000);

  const cookies = await context.cookies();
  const dacCookies = cookies.filter(c => c.domain.includes('dachain'));
  fs.writeFileSync('/tmp/dac-cookies.json', JSON.stringify(dacCookies, null, 2));

  const sessionId = dacCookies.find(c => c.name === 'sessionid');
  const csrfToken = dacCookies.find(c => c.name === 'csrftoken');
  if (sessionId && csrfToken) {
    fs.writeFileSync('/tmp/dac-auth.json', JSON.stringify({
      sessionid: sessionId.value,
      csrftoken: csrfToken.value,
    }, null, 2));
    console.log('✅ Auth cookies captured to /tmp/dac-auth.json');
  } else {
    console.log('⚠️ sessionid/csrftoken not found yet. Complete wallet connect then rerun.');
  }

  await context.close();
  console.log('✅ DONE');
})();
