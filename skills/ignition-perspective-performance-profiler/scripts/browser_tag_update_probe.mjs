#!/usr/bin/env node
// Browser probe for Perspective tag update latency fixtures.

import fs from "node:fs/promises";
import { createRequire } from "node:module";
import path from "node:path";
import { pathToFileURL } from "node:url";

function parseArgs(argv) {
  const args = {
    outDir: "",
    viewport: "1366x768",
    headless: true,
    urlAlias: "gateway",
    readySelector: "body",
    initialText: "",
    updatedText: "",
    initialReadyFile: "",
    updateSignalFile: "",
    timeoutMs: 30000,
    signalTimeoutMs: 30000,
    updateTimeoutMs: 30000,
    waitAfterUpdateMs: 1000,
  };
  for (let index = 2; index < argv.length; index += 1) {
    const arg = argv[index];
    const next = argv[index + 1];
    if (arg === "--url") {
      args.url = next;
      index += 1;
    } else if (arg === "--out-dir") {
      args.outDir = next;
      index += 1;
    } else if (arg === "--url-alias") {
      args.urlAlias = next;
      index += 1;
    } else if (arg === "--ready-selector") {
      args.readySelector = next;
      index += 1;
    } else if (arg === "--initial-text") {
      args.initialText = next;
      index += 1;
    } else if (arg === "--updated-text") {
      args.updatedText = next;
      index += 1;
    } else if (arg === "--initial-ready-file") {
      args.initialReadyFile = next;
      index += 1;
    } else if (arg === "--update-signal-file") {
      args.updateSignalFile = next;
      index += 1;
    } else if (arg === "--timeout-ms") {
      args.timeoutMs = Number(next);
      index += 1;
    } else if (arg === "--signal-timeout-ms") {
      args.signalTimeoutMs = Number(next);
      index += 1;
    } else if (arg === "--update-timeout-ms") {
      args.updateTimeoutMs = Number(next);
      index += 1;
    } else if (arg === "--wait-after-update-ms") {
      args.waitAfterUpdateMs = Number(next);
      index += 1;
    } else if (arg === "--viewport") {
      args.viewport = next;
      index += 1;
    } else if (arg === "--headed") {
      args.headless = false;
    } else if (arg === "--help" || arg === "-h") {
      args.help = true;
    } else {
      throw new Error(`Unknown argument: ${arg}`);
    }
  }
  return args;
}

function usage() {
  return [
    "Usage: node browser_tag_update_probe.mjs --url <route-url> --initial-text <text> --updated-text <text> [options]",
    "",
    "Options:",
    "  --out-dir <dir>                 Evidence output folder",
    "  --url-alias <alias>             Redacted URL prefix in evidence",
    "  --ready-selector <selector>     Selector that must be visible before text checks. Default: body",
    "  --initial-ready-file <path>     File to write after initial text is visible",
    "  --update-signal-file <path>     File to wait for before measuring updated text",
    "  --timeout-ms <ms>               Initial route/text timeout. Default: 30000",
    "  --signal-timeout-ms <ms>        Timeout waiting for update signal. Default: 30000",
    "  --update-timeout-ms <ms>        Timeout waiting for updated text. Default: 30000",
    "  --wait-after-update-ms <ms>     Extra capture time after update. Default: 1000",
    "  --viewport <width>x<height>     Default: 1366x768",
    "  --headed                        Run Chromium headed",
  ].join("\n");
}

function parseViewport(raw) {
  const match = /^(\d+)x(\d+)$/.exec(raw || "");
  if (!match) {
    throw new Error(`Invalid viewport '${raw}'. Use WIDTHxHEIGHT, such as 1366x768.`);
  }
  return { width: Number(match[1]), height: Number(match[2]) };
}

function redactUrl(raw, alias = "gateway") {
  try {
    const parsed = new URL(raw);
    const safePrefix = alias ? String(alias).replace(/[?#]/g, "") : `${parsed.protocol}//${parsed.host}`;
    return `${safePrefix}${parsed.pathname}`;
  } catch {
    return String(raw).split("?")[0].split("#")[0];
  }
}

function responseSize(headers) {
  const value = headers["content-length"] || headers["Content-Length"];
  const parsed = Number(value);
  return Number.isFinite(parsed) ? parsed : null;
}

function payloadSize(payload) {
  if (typeof payload === "string") {
    return Buffer.byteLength(payload, "utf8");
  }
  if (Buffer.isBuffer(payload)) {
    return payload.length;
  }
  if (payload && Number.isFinite(payload.byteLength)) {
    return payload.byteLength;
  }
  return 0;
}

async function writeJson(outDir, name, value) {
  if (!outDir) {
    return;
  }
  await fs.mkdir(outDir, { recursive: true });
  await fs.writeFile(path.join(outDir, name), `${JSON.stringify(value, null, 2)}\n`, "utf8");
}

async function writeSignalFile(filePath, value) {
  if (!filePath) {
    return;
  }
  await fs.mkdir(path.dirname(filePath), { recursive: true });
  await fs.writeFile(filePath, `${JSON.stringify(value, null, 2)}\n`, "utf8");
}

async function importPlaywright() {
  const require = createRequire(import.meta.url);
  const normalize = (module) => {
    const candidate = module && module.chromium ? module : module && module.default;
    if (!candidate || !candidate.chromium) {
      throw new Error("playwright module did not expose chromium");
    }
    return candidate;
  };
  try {
    return normalize(await import("playwright"));
  } catch (firstError) {
    try {
      return normalize(require("playwright"));
    } catch {
      // Continue trying absolute fallback paths from NODE_PATH.
    }
    const nodePath = process.env.NODE_PATH || "";
    for (const root of nodePath.split(path.delimiter).filter(Boolean)) {
      for (const fileName of ["index.js", "index.mjs"]) {
        const candidate = path.join(root, "playwright", fileName);
        try {
          await fs.access(candidate);
          if (fileName.endsWith(".js")) {
            return normalize(require(candidate));
          }
          return normalize(await import(pathToFileURL(candidate).href));
        } catch {
          // Continue trying remaining NODE_PATH entries.
        }
      }
    }
    throw firstError;
  }
}

async function waitForFile(filePath, timeoutMs) {
  const started = Date.now();
  while (Date.now() - started <= timeoutMs) {
    try {
      await fs.access(filePath);
      const raw = await fs.readFile(filePath, "utf8").catch(() => "");
      let parsed = null;
      try {
        parsed = raw.trim() ? JSON.parse(raw) : null;
      } catch {
        parsed = null;
      }
      return { ok: true, elapsedMs: Date.now() - started, parsed };
    } catch {
      await new Promise((resolve) => setTimeout(resolve, 100));
    }
  }
  return { ok: false, elapsedMs: Date.now() - started, parsed: null };
}

async function bodyContains(page, text) {
  return page.evaluate((value) => Boolean(document.body && document.body.innerText && document.body.innerText.includes(value)), text);
}

async function main() {
  const args = parseArgs(process.argv);
  if (args.help) {
    console.log(usage());
    return;
  }
  if (!args.url) {
    throw new Error("--url is required");
  }
  if (!args.initialText || !args.updatedText) {
    throw new Error("--initial-text and --updated-text are required");
  }
  if (!args.initialReadyFile || !args.updateSignalFile) {
    throw new Error("--initial-ready-file and --update-signal-file are required");
  }

  const startedAtEpochMs = Date.now();
  const redactedUrl = redactUrl(args.url, args.urlAlias);
  const consoleRows = [];
  const pageErrors = [];
  const responses = [];
  const webSockets = [];
  const websocketStats = new Map();

  const playwright = await importPlaywright();
  const browser = await playwright.chromium.launch({ headless: args.headless });
  const context = await browser.newContext({ viewport: parseViewport(args.viewport) });
  const page = await context.newPage();

  page.on("console", (message) => {
    consoleRows.push({
      type: message.type(),
      text: message.text(),
      location: message.location(),
    });
  });
  page.on("pageerror", (error) => {
    pageErrors.push({ message: error.message, stack: error.stack || "" });
  });
  page.on("response", (response) => {
    responses.push({
      url: redactUrl(response.url(), args.urlAlias),
      status: response.status(),
      resourceType: response.request().resourceType(),
      size: responseSize(response.headers()),
    });
  });
  page.on("websocket", (ws) => {
    const redacted = redactUrl(ws.url(), args.urlAlias);
    const stats = { url: redacted, sentFrames: 0, receivedFrames: 0, sentBytes: 0, receivedBytes: 0 };
    websocketStats.set(ws, stats);
    webSockets.push(stats);
    ws.on("framesent", (frame) => {
      stats.sentFrames += 1;
      stats.sentBytes += payloadSize(frame.payload);
    });
    ws.on("framereceived", (frame) => {
      stats.receivedFrames += 1;
      stats.receivedBytes += payloadSize(frame.payload);
    });
  });

  let summary = {
    ok: false,
    url: redactedUrl,
    viewport: args.viewport,
    startedAtEpochMs,
    initialTextMatched: false,
    updatedTextMatched: false,
    updateSignalObserved: false,
    initialReadyElapsedMs: null,
    signalWaitElapsedMs: null,
    updateVisibleElapsedMs: null,
    totalElapsedMs: null,
    domNodeCount: null,
    jsHeapUsedSize: null,
    consoleErrorCount: 0,
    consoleWarningCount: 0,
    pageErrorCount: 0,
  };

  try {
    await page.goto(args.url, { waitUntil: "domcontentloaded", timeout: args.timeoutMs });
    await page.locator(args.readySelector).first().waitFor({ state: "visible", timeout: args.timeoutMs });
    await page.waitForFunction((text) => document.body && document.body.innerText && document.body.innerText.includes(text), args.initialText, { timeout: args.timeoutMs });
    summary.initialTextMatched = await bodyContains(page, args.initialText);
    summary.initialReadyElapsedMs = Date.now() - startedAtEpochMs;
    await writeSignalFile(args.initialReadyFile, {
      ok: summary.initialTextMatched,
      elapsedMs: summary.initialReadyElapsedMs,
      observedAtEpochMs: Date.now(),
    });

    const signal = await waitForFile(args.updateSignalFile, args.signalTimeoutMs);
    summary.updateSignalObserved = signal.ok;
    summary.signalWaitElapsedMs = signal.elapsedMs;
    if (!signal.ok) {
      throw new Error("Timed out waiting for update signal file");
    }

    const updateStart = Date.now();
    await page.waitForFunction((text) => document.body && document.body.innerText && document.body.innerText.includes(text), args.updatedText, { timeout: args.updateTimeoutMs });
    summary.updatedTextMatched = await bodyContains(page, args.updatedText);
    summary.updateVisibleElapsedMs = Date.now() - updateStart;
    if (args.waitAfterUpdateMs > 0) {
      await page.waitForTimeout(args.waitAfterUpdateMs);
    }
    summary.domNodeCount = await page.evaluate(() => document.querySelectorAll("*").length).catch(() => null);
    summary.jsHeapUsedSize = await page.evaluate(() => performance.memory ? performance.memory.usedJSHeapSize : null).catch(() => null);
    summary.ok = Boolean(summary.initialTextMatched && summary.updatedTextMatched && summary.updateSignalObserved);
  } catch (error) {
    summary.error = String(error && error.stack ? error.stack : error);
  } finally {
    summary.totalElapsedMs = Date.now() - startedAtEpochMs;
    summary.consoleErrorCount = consoleRows.filter((row) => row.type === "error").length;
    summary.consoleWarningCount = consoleRows.filter((row) => row.type === "warning" || row.type === "warn").length;
    summary.pageErrorCount = pageErrors.length;
    await browser.close().catch(() => {});
  }

  const statusCounts = {};
  let knownTransferBytes = 0;
  for (const response of responses) {
    statusCounts[String(response.status)] = (statusCounts[String(response.status)] || 0) + 1;
    if (typeof response.size === "number") {
      knownTransferBytes += response.size;
    }
  }
  const network = {
    ok: true,
    responseCount: responses.length,
    statusCounts,
    knownTransferBytes,
    responses,
    webSockets,
  };

  await writeJson(args.outDir, "browser-tag-update-summary.json", summary);
  await writeJson(args.outDir, "browser-console.json", consoleRows);
  await writeJson(args.outDir, "page-errors.json", pageErrors);
  await writeJson(args.outDir, "network-summary.json", network);

  if (!summary.ok) {
    process.exitCode = 1;
  }
}

main().catch(async (error) => {
  const outDir = process.argv.includes("--out-dir") ? process.argv[process.argv.indexOf("--out-dir") + 1] : "";
  await writeJson(outDir, "browser-tag-update-summary.json", { ok: false, error: String(error && error.stack ? error.stack : error) });
  process.exitCode = 1;
});
