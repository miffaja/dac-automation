const { chromium } = require('playwright');
const fs = require('fs');

const SEED = "eager rib labor denial suffer fix match find chapter sketch pull panel";
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

  // Wait for MetaMask to load
  console.log("⏳ Waiting for MetaMask extension...");
  await new Promise(r => setTimeout(r, 10000));

  // Find MetaMask page
  let mm = context.pages().find(p => p.url().includes('chrome-extension'));
  if (!mm) {
    // Try to find via CDP
    const cdp = await context.pages()[0].context().newCDPSession(context.pages()[0]);
    const { targetInfos } = await cdp.send('Target.getTargets');
    const ext = targetInfos.find(t => t.url.includes('chrome-extension') && t.type === 'service_worker');
    if (ext) {
      mm = await context.newPage();
      await mm.goto(`chrome-extension://${new URL(ext.url).host}/home.html`);
    }
  }

  if (!mm) {
    console.log("❌ MetaMask not found, trying to open it...");
    // Try opening MetaMask directly
    mm = await context.newPage();
    await mm.goto('chrome-extension://nkbihfbeogaeaoehlefnkodbefgpgknn/home.html');
    await new Promise(r => setTimeout(r, 5000));
  }

  console.log("🦊 MetaMask URL:", mm.url());
  await mm.screenshot({ path: '/tmp/mm-01-initial.png' });

  try {
    await mm.waitForLoadState('networkidle', { timeout: 15000 });
  } catch (e) {
    console.log("Load state timeout, continuing...");
  }
  await new Promise(r => setTimeout(r, 3000));

  // Check what page we're on
  const pageText = await mm.evaluate(() => document.body?.innerText?.substring(0, 500) || 'empty');
  console.log("📄 Page text:", pageText.substring(0, 200));

  // If already set up, we might see the main wallet page
  if (pageText.includes('Import an existing wallet') || pageText.includes('Create a new wallet')) {
    console.log("📱 MetaMask setup page detected, importing wallet...");
    
    // Click "Import an existing wallet"
    try {
      await mm.click('button:has-text("Import an existing wallet")', { timeout: 10000 });
      await new Promise(r => setTimeout(r, 5000));
      await mm.screenshot({ path: '/tmp/mm-02-import.png' });
    } catch (e) {
      console.log("Could not click import:", e.message);
    }

    // Enter seed phrase
    console.log("📝 Entering seed phrase...");
    try {
      // Try textarea first
      const textarea = await mm.$('textarea');
      if (textarea) {
        await textarea.fill(SEED);
        console.log("  ✅ Filled textarea");
      } else {
        // Try individual word inputs
        const words = SEED.split(' ');
        for (let i = 0; i < words.length; i++) {
          const input = await mm.$(`[data-testid="srp-input-word-${i}"]`);
          if (input) {
            await input.fill(words[i]);
          }
        }
      }
    } catch (e) {
      console.log("Error entering seed:", e.message);
    }

    await new Promise(r => setTimeout(r, 2000));
    await mm.screenshot({ path: '/tmp/mm-03-seed.png' });

    // Click Continue/Import
    try {
      await mm.click('button:has-text("Continue")', { timeout: 5000 });
      await new Promise(r => setTimeout(r, 3000));
    } catch (e) {
      try {
        await mm.click('button:has-text("Import")', { timeout: 5000 });
      } catch (e2) {
        console.log("Could not click continue/import");
      }
    }

    // Set password
    console.log("🔐 Setting password...");
    await new Promise(r => setTimeout(r, 2000));
    await mm.screenshot({ path: '/tmp/mm-04-password.png' });
    
    try {
      const pwdInputs = await mm.$$('input[type="password"]');
      console.log(`  Found ${pwdInputs.length} password inputs`);
      
      if (pwdInputs.length >= 4) {
        // New UI: new password + confirm + 2 checkbox-like fields
        await pwdInputs[0].fill(PASSWORD);
        await pwdInputs[1].fill(PASSWORD);
      } else if (pwdInputs.length >= 2) {
        await pwdInputs[0].fill(PASSWORD);
        await pwdInputs[1].fill(PASSWORD);
      }
      
      // Check terms checkbox
      try {
        await mm.click('[data-testid="create-new-vault__terms-checkbox"]', { timeout: 3000 });
      } catch (e) {
        try {
          await mm.click('input[type="checkbox"]', { timeout: 3000 });
        } catch (e2) {}
      }
      
      await mm.screenshot({ path: '/tmp/mm-05-pwd-filled.png' });
      
      // Click Import/Create button
      try {
        await mm.click('button[data-testid="create-new-vault-submit-button"]', { timeout: 5000 });
      } catch (e) {
        try {
          await mm.click('button:has-text("Import my wallet")', { timeout: 5000 });
        } catch (e2) {
          try {
            await mm.click('button:has-text("Create")', { timeout: 5000 });
          } catch (e3) {
            console.log("Could not click create/import button");
          }
        }
      }
      
      await new Promise(r => setTimeout(r, 8000));
      await mm.screenshot({ path: '/tmp/mm-06-done.png' });
    } catch (e) {
      console.log("Error setting password:", e.message);
    }

    // Skip "What's new" or completion screens
    try {
      await mm.click('button:has-text("Done")', { timeout: 5000 });
      await new Promise(r => setTimeout(r, 2000));
    } catch (e) {}
    try {
      await mm.click('button:has-text("Got it")', { timeout: 5000 });
      await new Promise(r => setTimeout(r, 2000));
    } catch (e) {}
    try {
      await mm.click('button:has-text("Next")', { timeout: 5000 });
      await new Promise(r => setTimeout(r, 2000));
    } catch (e) {}
    try {
      await mm.click('[data-testid="onboarding-complete-done"]', { timeout: 5000 });
      await new Promise(r => setTimeout(r, 2000));
    } catch (e) {}
  } else if (pageText.includes('Welcome back') || pageText.includes('Unlock')) {
    // Already imported, just unlock
    console.log("🔓 MetaMask locked, unlocking...");
    try {
      await mm.fill('input[type="password"]', PASSWORD);
      await mm.click('button[type="submit"]', { timeout: 5000 });
      await new Promise(r => setTimeout(r, 5000));
    } catch (e) {
      console.log("Unlock failed:", e.message);
    }
  }

  await mm.screenshot({ path: '/tmp/mm-07-wallet.png' });
  console.log("📄 Wallet page text:", (await mm.evaluate(() => document.body?.innerText?.substring(0, 500) || 'empty')).substring(0, 200));

  // Now navigate to DAC site in a new tab
  console.log("\n🌐 Navigating to DAC Inception...");
  const dacPage = await context.newPage();
  await dacPage.goto(DAC_URL, { waitUntil: 'networkidle', timeout: 30000 });
  await new Promise(r => setTimeout(r, 5000));
  await dacPage.screenshot({ path: '/tmp/dac-01-loaded.png' });

  // Click Connect button
  console.log("🔗 Clicking Connect...");
  try {
    await dacPage.click('button:has-text("Connect")', { timeout: 10000 });
    await new Promise(r => setTimeout(r, 3000));
    await dacPage.screenshot({ path: '/tmp/dac-02-connect.png' });

    // Click WALLET option
    await dacPage.click('button:has-text("WALLET")', { timeout: 10000 });
    await new Promise(r => setTimeout(r, 3000));
    await dacPage.screenshot({ path: '/tmp/dac-03-wallet.png' });

    // Click MetaMask
    await dacPage.click('button:has-text("MetaMask")', { timeout: 10000 });
    await new Promise(r => setTimeout(r, 3000));
    
    // Click Browser tab
    try {
      await dacPage.click('button:has-text("Browser")', { timeout: 5000 });
      await new Promise(r => setTimeout(r, 2000));
    } catch (e) {}
    
    await dacPage.screenshot({ path: '/tmp/dac-04-metamask-option.png' });
  } catch (e) {
    console.log("Error during connect flow:", e.message);
  }

  // Wait for MetaMask popup
  console.log("⏳ Waiting for MetaMask popup...");
  await new Promise(r => setTimeout(r, 10000));

  // Check all pages for MetaMask popup
  const allPages = context.pages();
  console.log(`📄 Total pages: ${allPages.length}`);
  for (let i = 0; i < allPages.length; i++) {
    console.log(`  Page ${i}: ${allPages[i].url().substring(0, 80)}`);
  }

  // Find MetaMask popup
  let mmPopup = allPages.find(p => 
    p.url().includes('chrome-extension') && 
    (p.url().includes('notification') || p.url().includes('popup') || p.url().includes('confirm'))
  );

  if (!mmPopup) {
    // Try the main MM page
    mmPopup = allPages.find(p => p.url().includes('chrome-extension') && p !== mm);
  }

  if (mmPopup) {
    console.log("🦊 MetaMask popup found:", mmPopup.url());
    await mmPopup.screenshot({ path: '/tmp/mm-popup-01.png' });
    
    // Click Connect/Approve
    try {
      await mmPopup.click('[data-testid="confirm-btn"]', { timeout: 10000 });
      await new Promise(r => setTimeout(r, 5000));
      await mmPopup.screenshot({ path: '/tmp/mm-popup-02.png' });
    } catch (e) {
      try {
        await mmPopup.click('button:has-text("Connect")', { timeout: 5000 });
        await new Promise(r => setTimeout(r, 5000));
      } catch (e2) {
        try {
          await mmPopup.click('button:has-text("Approve")', { timeout: 5000 });
          await new Promise(r => setTimeout(r, 5000));
        } catch (e3) {
          console.log("Could not click connect/approve on popup");
        }
      }
    }

    // Handle sign request
    await new Promise(r => setTimeout(r, 5000));
    await mmPopup.screenshot({ path: '/tmp/mm-popup-03.png' });
    
    try {
      await mmPopup.click('[data-testid="confirm-footer-button"]', { timeout: 10000 });
      await new Promise(r => setTimeout(r, 5000));
    } catch (e) {
      try {
        await mmPopup.click('button:has-text("Sign")', { timeout: 5000 });
        await new Promise(r => setTimeout(r, 5000));
      } catch (e2) {
        try {
          await mmPopup.click('button:has-text("Confirm")', { timeout: 5000 });
          await new Promise(r => setTimeout(r, 5000));
        } catch (e3) {
          console.log("Could not click sign/confirm");
        }
      }
    }
    
    await mmPopup.screenshot({ path: '/tmp/mm-popup-04.png' });
  } else {
    console.log("❌ No MetaMask popup found");
  }

  // Wait for auth to complete
  await new Promise(r => setTimeout(r, 10000));
  await dacPage.screenshot({ path: '/tmp/dac-05-after-auth.png' });

  // Extract cookies
  const cookies = await context.cookies();
  const dacCookies = cookies.filter(c => c.domain.includes('dachain'));
  console.log("\n🍪 DAC Cookies:");
  for (const c of dacCookies) {
    console.log(`  ${c.name}=${c.value.substring(0, 50)}...`);
  }

  // Save cookies
  fs.writeFileSync('/tmp/dac-cookies.json', JSON.stringify(dacCookies, null, 2));
  
  // Also extract sessionid and csrftoken specifically
  const sessionId = dacCookies.find(c => c.name === 'sessionid');
  const csrfToken = dacCookies.find(c => c.name === 'csrftoken');
  
  if (sessionId && csrfToken) {
    console.log("\n✅ AUTH SUCCESS!");
    console.log(`sessionid: ${sessionId.value}`);
    console.log(`csrftoken: ${csrfToken.value}`);
    
    // Save to file for the automation script
    fs.writeFileSync('/tmp/dac-auth.json', JSON.stringify({
      sessionid: sessionId.value,
      csrftoken: csrfToken.value,
    }, null, 2));
  } else {
    console.log("\n❌ Auth cookies not found");
    console.log("Available cookies:", dacCookies.map(c => c.name).join(', '));
  }

  // Check current page URL
  console.log("\n📍 DAC page URL:", dacPage.url());
  
  await context.close();
  console.log("\n✅ DONE");
})();
