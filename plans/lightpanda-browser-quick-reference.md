# Lightpanda Browser Quick Reference

**Last Updated:** 2026-08-18  
**Status:** Ready to use  
**Scope:** Fast headless browser automation for crawling, testing, and agent sessions

---

## Why this is here

Lightpanda is a fit when the work needs a browser that can execute JavaScript, start quickly, and be driven through Puppeteer or Playwright without the cost of a full Chromium download.

Use it for:

- repeatable browser automation
- dynamic page scraping and extraction
- scripted testing against JS-heavy pages
- AI agent browser loops

Do not use it for:

- manual visual debugging
- UI fidelity checks that depend on Chromium rendering
- workflows that need a human browser session

---

## Portable setup

### Prerequisites

- Node.js
- npm

### Install

```bash
npm install --save @lightpanda/browser puppeteer-core
```

For Playwright-based automation:

```bash
npm install --save @lightpanda/browser playwright-core
```

### Start locally

```js
import { lightpanda } from '@lightpanda/browser';

const proc = await lightpanda.serve({
  host: '127.0.0.1',
  port: 9222,
});
```

### Connect

Use the local websocket endpoint:

```js
browserWSEndpoint: 'ws://127.0.0.1:9222'
```

### Stop

Always shut the process down after the run:

```js
proc.stdout.destroy();
proc.stderr.destroy();
proc.kill();
```

---

## Validation checklist

- `node index.js` starts Lightpanda without errors
- the browser client connects successfully
- the automation run completes
- the browser process is cleaned up at the end

---

## Environment notes

- No repo secrets are required for local Lightpanda use
- Add `LPD_TOKEN` only if you use the hosted Lightpanda browser
- Keep the browser endpoint and port in one place so the setup is easy to reproduce on another machine

---

## References

- [Lightpanda Quickstart](https://lightpanda.io/docs/quickstart)
- [Lightpanda CDP / Puppeteer docs](https://lightpanda.io/docs/usage/cdp/puppeteer)
- [Lightpanda CDP / Playwright docs](https://lightpanda.io/docs/usage/cdp/playwright)
