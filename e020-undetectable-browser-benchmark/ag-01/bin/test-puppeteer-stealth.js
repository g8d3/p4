#!/usr/bin/env node
/* Test: Puppeteer Extra + stealth-plugin */
const fs = require('fs');
const path = require('path');

const RESULT_FILE = path.join(__dirname, '..', 'output', 'puppeteer-stealth-result.json');
fs.mkdirSync(path.dirname(RESULT_FILE), { recursive: true });

const result = {
  browser: 'Puppeteer Extra + stealth',
  captcha: null,
  search: null,
  authenticated: null,
  error: null,
};

async function main() {
  let puppeteer, StealthPlugin;

  try {
    puppeteer = require('puppeteer-extra');
    StealthPlugin = require('puppeteer-extra-plugin-stealth');
  } catch (e) {
    result.error = `ImportError: ${e.message}`;
    fs.writeFileSync(RESULT_FILE, JSON.stringify(result, null, 2));
    process.exit(0);
  }

  puppeteer.use(StealthPlugin());

  let browser;
  try {
    browser = await puppeteer.launch({
      headless: true,
      args: [
        '--no-first-run',
        '--no-default-browser-check',
        '--window-size=1280,720',
        '--no-sandbox',
        '--disable-setuid-sandbox',
      ],
    });

    const page = await browser.newPage();
    await page.setViewport({ width: 1280, height: 720 });
    await page.goto('https://www.google.com', { waitUntil: 'load', timeout: 30000 });

    // Extra wait for any redirects/captcha
    await new Promise(r => setTimeout(r, 5000));

    const bodyText = (await page.evaluate(() => document.body.innerText)).toLowerCase();
    const pageUrl = page.url().toLowerCase();

    // Captcha check
    if (bodyText.includes('captcha') || bodyText.includes('not a robot') || pageUrl.includes('consent.google')) {
      result.captcha = true;
    } else {
      result.captcha = false;
    }

    // Authenticated check via cookies
    const cookies = await page.cookies('https://www.google.com');
    const authCookieNames = ['SID','SAPISID','HSID','SIDCC','SSID','APISID','__Secure-1PSID','__Secure-3PSID'];
    result.authenticated = cookies.some(c => authCookieNames.includes(c.name));

    // Try search
    try {
      const searchBox = await page.$('textarea[name="q"]') || await page.$('input[name="q"]');
      if (searchBox) {
        await searchBox.fill('test search');
        await searchBox.press('Enter');
        await new Promise(r => setTimeout(r, 5000));

        const resultsText = (await page.evaluate(() => document.body.innerText)).toLowerCase();
        if (resultsText.includes('resultados') || resultsText.includes('results') || resultsText.includes('about')) {
          result.search = true;
        } else {
          result.search = false;
        }
      } else {
        result.search = false;
      }
    } catch (e) {
      result.search = false;
    }

  } catch (e) {
    result.error = e.message;
  } finally {
    if (browser) {
      await browser.close().catch(() => {});
    }
    fs.writeFileSync(RESULT_FILE, JSON.stringify(result, null, 2));
  }
}

main();
