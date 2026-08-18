---
name: lightpanda-browser
description: 'Use when a task needs fast headless browser automation, dynamic-page interaction, crawling, or repeatable browser sessions with Puppeteer/Playwright/CDP. Includes local installation, startup, and cleanup for portable reuse on another machine.'
triggers:
  - "Lightpanda"
  - "browser automation"
  - "headless browser"
  - "Puppeteer"
  - "Playwright"
  - "CDP"
  - "crawl"
  - "dynamic web"
---

# Lightpanda Browser Automation

Use Lightpanda when the work is repeatable browser automation, not manual visual debugging.

## Use it for

- crawling and extraction
- scripted testing of dynamic pages
- AI agent browser loops
- fast startup and teardown in sessions

## Do not use it for

- manual visual inspection
- layout debugging that depends on full Chromium fidelity
- tasks where the browser UI itself matters

## Portable local setup

1. Install a current Node.js runtime.
2. Initialize a Node project.
3. Install the Lightpanda package and your browser client.
4. Start the browser process locally.
5. Connect with Puppeteer or Playwright over the local websocket endpoint.
6. Stop the browser process explicitly when finished.

## Local install

```bash
npm install --save @lightpanda/browser puppeteer-core
```

If you prefer Playwright:

```bash
npm install --save @lightpanda/browser playwright-core
```

## Local launch pattern

```js
import { lightpanda } from '@lightpanda/browser';
import puppeteer from 'puppeteer-core';

const lpdopts = {
  host: '127.0.0.1',
  port: 9222,
};

(async () => {
  const proc = await lightpanda.serve(lpdopts);
  const browser = await puppeteer.connect({
    browserWSEndpoint: 'ws://' + lpdopts.host + ':' + lpdopts.port,
  });
  const context = await browser.createBrowserContext();
  const page = await context.newPage();

  // Do your automation here.

  await page.close();
  await context.close();
  await browser.disconnect();
  proc.stdout.destroy();
  proc.stderr.destroy();
  proc.kill();
})();
```

## Cloud option

If you use the hosted browser, set `LPD_TOKEN` and connect to the websocket endpoint documented by Lightpanda.

## Verification

- `node index.js` should print the Lightpanda CDP server PID.
- The browser client should connect without downloading Chromium.
- Cleanup should terminate the Lightpanda process at the end of each run.

## Troubleshooting

- If the browser does not start, confirm Node.js is installed and the npm packages are present.
- If Puppeteer cannot connect, verify the websocket host and port.
- If you need interactive browser inspection, use the browser tools or Chrome DevTools MCP instead of Lightpanda.
