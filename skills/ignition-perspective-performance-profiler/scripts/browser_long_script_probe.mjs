#!/usr/bin/env node
// Browser probe for bounded long-running Perspective script fixtures.

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
    readyText: "",
    buttonText: "",
    resultText: "",
    clickSignalFile: "",
    timeoutMs: 30000,
    resultTimeoutMs: 30000,
    waitAfterResultMs: 1000,
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
    } else if (arg === "--ready-text") {
      args.readyText = next;
      index += 1;
    } else if (arg === "--button-text") {
      args.buttonText = next;
      index += 1;
    } else if (arg === "--result-text") {
      args.resultText = next;
      index += 1;
    } else if (arg === "--click-signal-file") {
      args.clickSignalFile = next;
      index += 1;
    } else if (arg === "--timeout-ms") {
      args.timeoutMs = Number(next);
      index += 1;
    } else if (arg === "--result-timeout-ms") {
      args.resultTimeoutMs = Number(next);
      index += 1;
    } else if (arg === "--wait-after-result-ms") {
      args.waitAfterResultMs = Number(next);
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
    "Usage: node browser_long_script_probe.mjs --url <route-url> --ready-text <text> --button-text <text> --result-text <text> [options]",
    "",
    "Options:",
    "  --out-dir <dir>                 Evidence output folder",
    "  --url-alias <alias>             Redacted URL prefix in evidence",
    "  --ready-selector <selector>     Selector visible before text checks. Default: body",
    "  --click-signal-file <path>      File to write immediately after click dispatch",
    "  --timeout-ms <ms>               Initial route/text timeout. Default: 30000",
    "  --result-timeout-ms <ms>        Timeout waiting for result text. Default: 30000",
    "  --wait-after-result-ms <ms>     Extra capture time after result. Default: 1000",
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

async function captureScreenshot(page, outDir, name) {
  const evidence = {
    ok: false,
    file: name,
    atEpochMs: null,
    elapsedMs: null,
    error: null,
  };
  if (!outDir) {
    evidence.error = "outDir was not configured";
    return evidence;
  }
  const started = Date.now();
  try {
    await fs.mkdir(outDir, { recursive: true });
    await page.screenshot({ path: path.join(outDir, name), fullPage: true });
    evidence.ok = true;
    evidence.atEpochMs = Date.now();
    evidence.elapsedMs = evidence.atEpochMs - started;
  } catch (error) {
    evidence.atEpochMs = Date.now();
    evidence.elapsedMs = evidence.atEpochMs - started;
    evidence.error = String(error && error.message ? error.message : error).slice(0, 1000);
  }
  return evidence;
}

async function withTimeout(promise, timeoutMs, label) {
  let timer = null;
  try {
    return await Promise.race([
      promise,
      new Promise((resolve) => {
        timer = setTimeout(() => resolve({ timedOut: true, label }), timeoutMs);
      }),
    ]);
  } finally {
    if (timer) {
      clearTimeout(timer);
    }
  }
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

async function bodyContains(page, text) {
  return page.evaluate((value) => Boolean(document.body && document.body.innerText && document.body.innerText.includes(value)), text);
}

async function main() {
  const args = parseArgs(process.argv);
  if (args.help) {
    console.log(usage());
    return;
  }
  if (!args.url || !args.readyText || !args.buttonText || !args.resultText) {
    throw new Error("--url, --ready-text, --button-text, and --result-text are required");
  }
  if (!args.clickSignalFile) {
    throw new Error("--click-signal-file is required");
  }

  const startedAtEpochMs = Date.now();
  const redactedUrl = redactUrl(args.url, args.urlAlias);
  const consoleRows = [];
  const pageErrors = [];
  const responses = [];
  const websocketStats = new Map();
  const webSockets = [];
  const progressRows = [];
  const progress = async (stage, details = {}) => {
    progressRows.push({
      stage,
      atEpochMs: Date.now(),
      elapsedMs: Date.now() - startedAtEpochMs,
      ...details,
    });
    await writeJson(args.outDir, "browser-progress.json", progressRows).catch(() => {});
  };

  await progress("start", { url: redactedUrl });
  await progress("import-playwright-start");
  const playwright = await importPlaywright();
  await progress("import-playwright-done");
  await progress("launch-browser-start");
  const browser = await playwright.chromium.launch({ headless: args.headless });
  await progress("launch-browser-done");
  const context = await browser.newContext({ viewport: parseViewport(args.viewport) });
  await progress("context-created");
  const page = await context.newPage();
  await progress("page-created");

  page.on("console", (message) => {
    consoleRows.push({ type: message.type(), text: message.text(), location: message.location() });
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
    const stats = { url: redactUrl(ws.url(), args.urlAlias), sentFrames: 0, receivedFrames: 0, sentBytes: 0, receivedBytes: 0 };
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

  const summary = {
    ok: false,
    url: redactedUrl,
    viewport: args.viewport,
    startedAtEpochMs,
    readyTextMatched: false,
    clicked: false,
    resultTextMatched: false,
    readyElapsedMs: null,
    clickedAtEpochMs: null,
    resultMatchedAtEpochMs: null,
    clickDispatchElapsedMs: null,
    clickToResultElapsedMs: null,
    activeWindowScreenshot: {
      ok: false,
      file: "active-window-screenshot.png",
      atEpochMs: null,
      elapsedMs: null,
      error: null,
    },
    totalElapsedMs: null,
    domNodeCount: null,
    jsHeapUsedSize: null,
    consoleErrorCount: 0,
    consoleWarningCount: 0,
    pageErrorCount: 0,
  };

  try {
    await progress("goto-start");
    await page.goto(args.url, { waitUntil: "domcontentloaded", timeout: args.timeoutMs });
    await progress("goto-done");
    await page.locator(args.readySelector).first().waitFor({ state: "visible", timeout: args.timeoutMs });
    await progress("ready-selector-visible");
    await page.waitForFunction((text) => document.body && document.body.innerText && document.body.innerText.includes(text), args.readyText, { timeout: args.timeoutMs });
    summary.readyTextMatched = await bodyContains(page, args.readyText);
    summary.readyElapsedMs = Date.now() - startedAtEpochMs;
    await progress("ready-text-matched", { readyElapsedMs: summary.readyElapsedMs });

    const button = page.getByRole("button", { name: args.buttonText }).first();
    await button.waitFor({ state: "visible", timeout: args.timeoutMs });
    await progress("button-visible");
    const clickStarted = Date.now();
    await button.click({ timeout: args.timeoutMs });
    summary.clicked = true;
    summary.clickedAtEpochMs = Date.now();
    summary.clickDispatchElapsedMs = Date.now() - clickStarted;
    await progress("click-dispatched", { clickedAtEpochMs: summary.clickedAtEpochMs, clickDispatchElapsedMs: summary.clickDispatchElapsedMs });
    await writeSignalFile(args.clickSignalFile, {
      ok: true,
      clickedAtEpochMs: summary.clickedAtEpochMs,
      clickDispatchElapsedMs: summary.clickDispatchElapsedMs,
    });
    summary.activeWindowScreenshot = await captureScreenshot(page, args.outDir, "active-window-screenshot.png");
    await progress("active-window-screenshot", summary.activeWindowScreenshot);

    await page.waitForFunction((text) => document.body && document.body.innerText && document.body.innerText.includes(text), args.resultText, { timeout: args.resultTimeoutMs });
    summary.resultTextMatched = await bodyContains(page, args.resultText);
    summary.resultMatchedAtEpochMs = Date.now();
    summary.clickToResultElapsedMs = Date.now() - clickStarted;
    await progress("result-text-matched", { resultMatchedAtEpochMs: summary.resultMatchedAtEpochMs, clickToResultElapsedMs: summary.clickToResultElapsedMs });
    if (args.waitAfterResultMs > 0) {
      await page.waitForTimeout(args.waitAfterResultMs);
    }
    summary.domNodeCount = await page.evaluate(() => document.querySelectorAll("*").length).catch(() => null);
    summary.jsHeapUsedSize = await page.evaluate(() => performance.memory ? performance.memory.usedJSHeapSize : null).catch(() => null);
    summary.ok = Boolean(summary.readyTextMatched && summary.clicked && summary.resultTextMatched);
  } catch (error) {
    summary.error = String(error && error.stack ? error.stack : error);
    await progress("error", { error: summary.error });
    await writeSignalFile(args.clickSignalFile, {
      ok: false,
      clickedAtEpochMs: Date.now(),
      error: summary.error,
    }).catch(() => {});
    await writeJson(args.outDir, "browser-long-script-summary.json", summary).catch(() => {});
  } finally {
    summary.totalElapsedMs = Date.now() - startedAtEpochMs;
    summary.consoleErrorCount = consoleRows.filter((row) => row.type === "error").length;
    summary.consoleWarningCount = consoleRows.filter((row) => row.type === "warning" || row.type === "warn").length;
    summary.pageErrorCount = pageErrors.length;
    await writeJson(args.outDir, "browser-long-script-summary.json", summary).catch(() => {});
    await writeJson(args.outDir, "browser-console.json", consoleRows).catch(() => {});
    await writeJson(args.outDir, "page-errors.json", pageErrors).catch(() => {});
    await progress("browser-close-start");
    const closeResult = await withTimeout(browser.close(), 5000, "browser.close");
    if (closeResult && closeResult.timedOut) {
      summary.browserCloseError = `${closeResult.label} timed out`;
      await writeJson(args.outDir, "browser-long-script-summary.json", summary).catch(() => {});
      await progress("browser-close-timeout");
    } else {
      await progress("browser-close-done");
    }
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

  await writeJson(args.outDir, "browser-long-script-summary.json", summary);
  await writeJson(args.outDir, "browser-console.json", consoleRows);
  await writeJson(args.outDir, "page-errors.json", pageErrors);
  await writeJson(args.outDir, "network-summary.json", network);

  if (!summary.ok) {
    process.exitCode = 1;
  }
}

main().catch(async (error) => {
  const outDir = process.argv.includes("--out-dir") ? process.argv[process.argv.indexOf("--out-dir") + 1] : "";
  await writeJson(outDir, "browser-long-script-summary.json", { ok: false, error: String(error && error.stack ? error.stack : error) });
  process.exitCode = 1;
});
