const { chromium } = require('playwright');
const fs = require('fs');

const PASSWORD = "DacAuto2026!";
const DAC_URL = "https://inception.dachain.io/dashboard";
const EXT_PATH = "/home/ubuntu/metamask-agent/metamask";

(async () => {
  console.log("🚀 Launching browser with MetaMask...");

  const context = await chromium.launchPersistentContext('/tmp/dac-mm-profile', {
    headless: false,
    args: [
      `--disable-extensions-except=${EXT_PATH}`,
      `--load-extension=${EXT_PATH}`,
      '--no-sandbox',
      '--disable-setuid-sandbox',
      '--window-size=1280,900',
    ]
  });

  console.log("⏳ Waiting for MetaMask extension...");
  await new Promise(r => setTimeout(r, 10000));

  // Find MetaMask page and unlock it first
  let mm = context.pages().find(p => p.url().includes('chrome-extension'));
  if (mm) {
    console.log("🦊 MetaMask page:", mm.url());
    
    // Try to find and fill password input
    try {
      // Wait for the page to load
      await mm.waitForLoadState('domcontentloaded', { timeout: 10000 });
      
      // Try multiple selectors for password input
      let pwdInput = await mm.$('input[id="password"]');
      if (!pwdInput) pwdInput = await mm.$('input[type="password"]');
      if (!pwdInput) pwdInput = await mm.$('input[data-testid="unlock-password"]');
      
      if (pwdInput) {
        console.log("🔓 Found password input, filling...");
        await pwdInput.fill(PASSWORD);
        await new Promise(r => setTimeout(r, 500));
        
        // Try to find and click unlock button
        let unlockBtn = await mm.$('button[data-testid="unlock-submit"]');
        if (!unlockBtn) unlockBtn = await mm.$('button[type="submit"]');
        if (!unlockBtn) {
          // Just press Enter
          await pwdInput.press('Enter');
        } else {
          await unlockBtn.click();
        }
        console.log("🔓 Submitted unlock");
        await new Promise(r => setTimeout(r, 8000));
      } else {
        console.log("ℹ️ No password input found on MM page");
      }
    } catch (e) {
      console.log("MM unlock error:", e.message);
    }
    
    await mm.screenshot({ path: '/tmp/mm-after-unlock.png' });
    
    // If MM is still on unlock page, try pressing Enter in password field
    if (mm.url().includes('unlock')) {
      console.log("🔄 Still on unlock page, trying alternative approach...");
      try {
        // Use keyboard to fill and submit
        await mm.keyboard.type(PASSWORD);
        await mm.keyboard.press('Enter');
        await new Promise(r => setTimeout(r, 8000));
      } catch (e) {
        console.log("Keyboard approach failed:", e.message);
      }
      await mm.screenshot({ path: '/tmp/mm-after-unlock2.png' });
    }
  }

  // Now navigate to DAC
  console.log("\n🌐 Navigating to DAC Inception...");
  const dacPage = await context.newPage();
  await dacPage.goto(DAC_URL, { waitUntil: 'networkidle', timeout: 30000 });
  await new Promise(r => setTimeout(r, 5000));
  await dacPage.screenshot({ path: '/tmp/dac-page.png' });

  // Click Connect
  console.log("🔗 Clicking Connect...");
  try {
    await dacPage.click('button:has-text("Connect")', { timeout: 10000 });
    await new Promise(r => setTimeout(r, 3000));

    // Click WALLET
    console.log("🔗 Clicking WALLET...");
    await dacPage.click('button:has-text("WALLET")', { timeout: 10000, force: true });
    await new Promise(r => setTimeout(r, 3000));
    await dacPage.screenshot({ path: '/tmp/dac-wallet-modal.png' });

    // Click MetaMask
    console.log("🔗 Clicking MetaMask...");
    // Use locator with nth to get the right button
    const mmButtons = dacPage.locator('button:has-text("MetaMask")');
    const count = await mmButtons.count();
    console.log(`  Found ${count} MetaMask buttons`);
    if (count > 0) {
      await mmButtons.last().click({ force: true, timeout: 10000 });
    }
    await new Promise(r => setTimeout(r, 5000));
    await dacPage.screenshot({ path: '/tmp/dac-after-mm-click.png' });
  } catch (e) {
    console.log("Connect flow error:", e.message);
  }

  // Wait for MetaMask popup
  console.log("⏳ Waiting for MetaMask popup...");
  await new Promise(r => setTimeout(r, 10000));

  // List all pages
  const allPages = context.pages();
  console.log(`📄 Total pages: ${allPages.length}`);
  for (let i = 0; i < allPages.length; i++) {
    console.log(`  Page ${i}: ${allPages[i].url()}`);
  }

  // Find MetaMask popup
  let mmPopup = allPages.find(p => 
    p.url().includes('chrome-extension') && 
    p !== mm &&
    (p.url().includes('notification') || p.url().includes('popup') || p.url().includes('confirm'))
  );

  if (!mmPopup) {
    mmPopup = allPages.find(p => p.url().includes('chrome-extension') && p !== mm);
  }

  if (mmPopup) {
    console.log("🦊 MetaMask popup found:", mmPopup.url());
    await new Promise(r => setTimeout(r, 3000));
    await mmPopup.screenshot({ path: '/tmp/mm-popup-found.png' });
    
    // Try clicking connect/approve
    const connectSelectors = [
      '[data-testid="confirm-btn"]',
      'button:has-text("Connect")',
      'button:has-text("Approve")',
      'button:has-text("Next")',
      'button:has-text("Confirm")',
    ];
    
    for (const sel of connectSelectors) {
      try {
        const btn = await mmPopup.$(sel);
        if (btn) {
          const visible = await btn.isVisible();
          if (visible) {
            await btn.click();
            console.log(`✅ Clicked: ${sel}`);
            await new Promise(r => setTimeout(r, 5000));
            break;
          }
        }
      } catch (e) {}
    }

    await mmPopup.screenshot({ path: '/tmp/mm-popup-after-connect.png' });

    // Handle sign
    await new Promise(r => setTimeout(r, 3000));
    const signSelectors = [
      '[data-testid="confirm-footer-button"]',
      'button:has-text("Sign")',
      'button:has-text("Confirm")',
    ];
    
    for (const sel of signSelectors) {
      try {
        const btn = await mmPopup.$(sel);
        if (btn) {
          const visible = await btn.isVisible();
          if (visible) {
            await btn.click();
            console.log(`✅ Clicked sign: ${sel}`);
            await new Promise(r => setTimeout(r, 5000));
            break;
          }
        }
      } catch (e) {}
    }

    await mmPopup.screenshot({ path: '/tmp/mm-popup-final.png' });
  } else {
    console.log("❌ No MetaMask popup found");
  }

  // Wait for auth
  console.log("⏳ Waiting for auth...");
  await new Promise(r => setTimeout(r, 15000));
  await dacPage.screenshot({ path: '/tmp/dac-final.png' });

  // Extract cookies
  const cookies = await context.cookies();
  const dacCookies = cookies.filter(c => c.domain.includes('dachain'));
  console.log("\n🍪 DAC Cookies:");
  for (const c of dacCookies) {
    console.log(`  ${c.name}=${c.value.substring(0, 80)}`);
  }

  fs.writeFileSync('/tmp/dac-cookies.json', JSON.stringify(dacCookies, null, 2));
  
  const sessionId = dacCookies.find(c => c.name === 'sessionid');
  const csrfToken = dacCookies.find(c => c.name === 'csrftoken');
  
  if (sessionId && csrfToken) {
    console.log("\n✅ AUTH SUCCESS!");
    console.log(`sessionid: ${sessionId.value}`);
    console.log(`csrftoken: ${csrfToken.value}`);
    
    fs.writeFileSync('/tmp/dac-auth.json', JSON.stringify({
      sessionid: sessionId.value,
      csrftoken: csrfToken.value,
    }, null, 2));
  } else {
    console.log("\n❌ Auth cookies not found");
    console.log("Available cookies:", dacCookies.map(c => c.name).join(', '));
  }

  console.log("\n📍 DAC page URL:", dacPage.url());
  
  await context.close();
  console.log("\n✅ DONE");
})();
