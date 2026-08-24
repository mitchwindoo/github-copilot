#!/usr/bin/env node
// Browser evidence probe for Perspective route profiling.
//
// Requires Playwright to be installed in the environment running the skill.
// Captures browser-summary.json, browser-console.json, and network-summary.json.

import fs from "node:fs/promises";
import { createRequire } from "node:module";
import path from "node:path";
import { pathToFileURL } from "node:url";

function parseArgs(argv) {
  const args = {
    readySelector: '[data-testid="perf-ready"]',
    timeoutMs: 30000,
    outDir: "",
    viewport: "1366x768",
    headless: true,
    userDataDir: "",
    readyText: "",
    secondaryReadySelector: "",
    secondaryReadyText: "",
    waitAfterReadyMs: 1000,
    urlAlias: "gateway",
    clickSelector: "",
    clickText: "",
    clickLabel: "",
    clickAfterReadyDelayMs: 0,
    clickRepeatCount: 1,
    clickRepeatIntervalMs: 0,
    clickRepeatMode: "playwright",
    clickResultSelector: "",
    clickResultText: "",
    clickTimeoutMs: 10000,
    postInteractionWaitMs: 0,
    networkThrottleAfterReady: false,
    networkLatencyMs: 0,
    networkDownloadKbps: 0,
    networkUploadKbps: 0,
    timelineSampleIntervalMs: 0,
    watchTextSelector: "",
    watchTextRegex: "",
    watchTextLabel: "",
    watchTextTimeoutMs: 10000,
  };
  for (let index = 2; index < argv.length; index += 1) {
    const arg = argv[index];
    const next = argv[index + 1];
    if (arg === "--url") {
      args.url = next;
      index += 1;
    } else if (arg === "--ready-selector") {
      args.readySelector = next;
      index += 1;
    } else if (arg === "--ready-text") {
      args.readyText = next;
      index += 1;
    } else if (arg === "--secondary-ready-selector") {
      args.secondaryReadySelector = next;
      index += 1;
    } else if (arg === "--secondary-ready-text") {
      args.secondaryReadyText = next;
      index += 1;
    } else if (arg === "--wait-after-ready-ms") {
      args.waitAfterReadyMs = Number(next);
      index += 1;
    } else if (arg === "--timeout-ms") {
      args.timeoutMs = Number(next);
      index += 1;
    } else if (arg === "--out-dir") {
      args.outDir = next;
      index += 1;
    } else if (arg === "--url-alias") {
      args.urlAlias = next;
      index += 1;
    } else if (arg === "--click-selector") {
      args.clickSelector = next;
      index += 1;
    } else if (arg === "--click-text") {
      args.clickText = next;
      index += 1;
    } else if (arg === "--click-label") {
      args.clickLabel = next;
      index += 1;
    } else if (arg === "--click-after-ready-delay-ms") {
      args.clickAfterReadyDelayMs = Number(next);
      index += 1;
    } else if (arg === "--click-repeat-count") {
      args.clickRepeatCount = Number(next);
      index += 1;
    } else if (arg === "--click-repeat-interval-ms") {
      args.clickRepeatIntervalMs = Number(next);
      index += 1;
    } else if (arg === "--click-repeat-mode") {
      args.clickRepeatMode = next;
      index += 1;
    } else if (arg === "--click-result-selector") {
      args.clickResultSelector = next;
      index += 1;
    } else if (arg === "--click-result-text") {
      args.clickResultText = next;
      index += 1;
    } else if (arg === "--click-timeout-ms") {
      args.clickTimeoutMs = Number(next);
      index += 1;
    } else if (arg === "--post-interaction-wait-ms") {
      args.postInteractionWaitMs = Number(next);
      index += 1;
    } else if (arg === "--network-throttle-after-ready") {
      args.networkThrottleAfterReady = true;
    } else if (arg === "--network-latency-ms") {
      args.networkLatencyMs = Number(next);
      index += 1;
    } else if (arg === "--network-download-kbps") {
      args.networkDownloadKbps = Number(next);
      index += 1;
    } else if (arg === "--network-upload-kbps") {
      args.networkUploadKbps = Number(next);
      index += 1;
    } else if (arg === "--timeline-sample-interval-ms") {
      args.timelineSampleIntervalMs = Number(next);
      index += 1;
    } else if (arg === "--watch-text-selector") {
      args.watchTextSelector = next;
      index += 1;
    } else if (arg === "--watch-text-regex") {
      args.watchTextRegex = next;
      index += 1;
    } else if (arg === "--watch-text-label") {
      args.watchTextLabel = next;
      index += 1;
    } else if (arg === "--watch-text-timeout-ms") {
      args.watchTextTimeoutMs = Number(next);
      index += 1;
    } else if (arg === "--viewport") {
      args.viewport = next;
      index += 1;
    } else if (arg === "--user-data-dir") {
      args.userDataDir = next;
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
    "Usage: node browser_route_probe.mjs --url <route-url> [options]",
    "",
    "Options:",
    '  --ready-selector <selector>   Default: [data-testid="perf-ready"]',
    "  --ready-text <text>            Optional text that must appear in document.body",
    "  --secondary-ready-selector <selector> Optional second selector for total-ready timing",
    "  --secondary-ready-text <text>   Optional second body text for total-ready timing",
    "  --wait-after-ready-ms <ms>     Extra collection time after ready. Default: 1000",
    "  --timeout-ms <ms>             Default: 30000",
    "  --viewport <width>x<height>   Default: 1366x768",
    "  --user-data-dir <dir>         Use a persistent Chromium profile/cache directory",
    "  --out-dir <dir>               Write JSON evidence files to this folder",
    "  --url-alias <alias>           Redacted URL prefix in evidence. Default: gateway",
    "  --click-selector <selector>   Optional selector to click after route readiness",
    "  --click-text <text>           Optional text filter for the click target",
    "  --click-label <label>         Non-secret interaction label for reports",
    "  --click-after-ready-delay-ms <ms>  Delay after ready before clicking. Default: 0",
    "  --click-repeat-count <count>  Dispatch the click this many times. Default: 1",
    "  --click-repeat-interval-ms <ms> Delay between repeated clicks. Default: 0",
    "  --click-repeat-mode <mode>    playwright, mouse, or dom. Default: playwright",
    "  --click-result-selector <selector> Selector that must be visible after click",
    "  --click-result-text <text>    Body text that must appear after click",
    "  --click-timeout-ms <ms>       Click/result timeout. Default: 10000",
    "  --post-interaction-wait-ms <ms> Keep session open after click. Default: 0",
    "  --network-throttle-after-ready Apply requested network throttle after primary readiness",
    "  --network-latency-ms <ms>      Optional Chromium network latency. Default: 0",
    "  --network-download-kbps <kbps> Optional Chromium download throughput cap. Default: 0",
    "  --network-upload-kbps <kbps>   Optional Chromium upload throughput cap. Default: 0",
    "  --timeline-sample-interval-ms <ms> Optional browser timeline sample interval during wait-after-ready. Default: 0",
    "  --watch-text-selector <selector> Selector whose text must change after click",
    "  --watch-text-regex <regex>    Optional regex; first capture group is compared",
    "  --watch-text-label <label>    Non-secret watched-text label for reports",
    "  --watch-text-timeout-ms <ms>  Watched-text change timeout. Default: 10000",
    "  --headed                      Run Chromium headed",
  ].join("\n");
}

function parseViewport(raw) {
  const match = /^(\d+)x(\d+)$/.exec(raw || "");
  if (!match) {
    throw new Error(`Invalid viewport '${raw}'. Use WIDTHxHEIGHT, such as 1366x768.`);
  }
  return { width: Number(match[1]), height: Number(match[2]) };
}

function requireNonNegativeNumber(value, label) {
  if (!Number.isFinite(Number(value)) || Number(value) < 0) {
    throw new Error(`${label} must be a non-negative number.`);
  }
}

function validateArgs(args) {
  requireNonNegativeNumber(args.networkLatencyMs, "--network-latency-ms");
  requireNonNegativeNumber(args.networkDownloadKbps, "--network-download-kbps");
  requireNonNegativeNumber(args.networkUploadKbps, "--network-upload-kbps");
  requireNonNegativeNumber(args.timelineSampleIntervalMs, "--timeline-sample-interval-ms");
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

function networkThrottleRequested(args) {
  return Number(args.networkLatencyMs || 0) > 0 || Number(args.networkDownloadKbps || 0) > 0 || Number(args.networkUploadKbps || 0) > 0;
}

function networkThrottlePayload(args) {
  const kbpsToBytes = (value) => (Number(value || 0) > 0 ? Math.max(1, (Number(value) * 1024) / 8) : -1);
  return {
    offline: false,
    latency: Math.max(0, Number(args.networkLatencyMs || 0)),
    downloadThroughput: kbpsToBytes(args.networkDownloadKbps),
    uploadThroughput: kbpsToBytes(args.networkUploadKbps),
    connectionType: "other",
  };
}

async function applyNetworkThrottle(cdpSession, args, phase) {
  const requested = networkThrottleRequested(args);
  const result = {
    requested,
    applied: false,
    phase,
    afterReady: Boolean(args.networkThrottleAfterReady),
    latencyMs: Math.max(0, Number(args.networkLatencyMs || 0)),
    downloadKbps: Math.max(0, Number(args.networkDownloadKbps || 0)),
    uploadKbps: Math.max(0, Number(args.networkUploadKbps || 0)),
    error: null,
  };
  if (!requested) {
    return result;
  }
  try {
    await cdpSession.send("Network.enable");
    await cdpSession.send("Network.emulateNetworkConditions", networkThrottlePayload(args));
    result.applied = true;
  } catch (error) {
    result.error = String(error && error.message ? error.message : error).slice(0, 1000);
  }
  return result;
}

async function bodyContainsText(page, text) {
  if (!text) {
    return null;
  }
  return page.evaluate((value) => Boolean(document.body && document.body.innerText && document.body.innerText.indexOf(value) !== -1), text);
}

async function selectorVisible(page, selector) {
  if (!selector) {
    return null;
  }
  return page.locator(selector).first().isVisible().catch(() => false);
}

async function watchTextSnapshot(page, args) {
  const configured = Boolean(args.watchTextSelector);
  const snapshot = {
    configured,
    label: args.watchTextLabel || null,
    selector: args.watchTextSelector || null,
    regexConfigured: Boolean(args.watchTextRegex),
    matched: null,
    value: null,
    textLength: null,
    error: null,
  };
  if (!configured) {
    return snapshot;
  }
  try {
    const result = await page.evaluate(
      ({ selector, regexText }) => {
        const element = document.querySelector(selector);
        if (!element) {
          return { matched: false, value: null, textLength: null, error: "selector did not match" };
        }
        const text = element.innerText || element.textContent || "";
        if (!regexText) {
          return { matched: true, value: text.slice(0, 500), textLength: text.length, error: null };
        }
        let regex;
        try {
          regex = new RegExp(regexText);
        } catch (error) {
          return { matched: false, value: null, textLength: text.length, error: `invalid regex: ${error.message || error}` };
        }
        const match = regex.exec(text);
        if (!match) {
          return { matched: false, value: null, textLength: text.length, error: "regex did not match" };
        }
        return { matched: true, value: String(match[1] === undefined ? match[0] : match[1]).slice(0, 500), textLength: text.length, error: null };
      },
      { selector: args.watchTextSelector, regexText: args.watchTextRegex },
    );
    return { ...snapshot, ...result };
  } catch (error) {
    return { ...snapshot, error: String(error && error.message ? error.message : error).slice(0, 1000) };
  }
}

async function runInteraction(page, args) {
  const interaction = {
    configured: Boolean(args.clickSelector),
    ok: null,
    label: args.clickLabel || null,
    clickSelector: args.clickSelector || null,
    clickTextConfigured: Boolean(args.clickText),
    resultSelector: args.clickResultSelector || null,
    resultTextConfigured: Boolean(args.clickResultText),
    resultAlreadyMatchedBeforeClick: null,
    postInteractionWaitMs: args.postInteractionWaitMs || 0,
    watchText: {
      configured: Boolean(args.watchTextSelector),
      label: args.watchTextLabel || null,
      selector: args.watchTextSelector || null,
      regexConfigured: Boolean(args.watchTextRegex),
      before: null,
      after: null,
      changed: null,
    },
    startedEpochMillis: null,
    finishedEpochMillis: null,
    clickElapsedMs: null,
    clickRepeatCount: null,
    clickRepeatIntervalMs: null,
    clickRepeatMode: null,
    resultElapsedMs: null,
    error: null,
  };
  if (!args.clickSelector) {
    return interaction;
  }
  try {
    if (args.clickAfterReadyDelayMs > 0) {
      await page.waitForTimeout(args.clickAfterReadyDelayMs);
    }
    const beforeSelector = await selectorVisible(page, args.clickResultSelector);
    const beforeText = await bodyContainsText(page, args.clickResultText);
    interaction.resultAlreadyMatchedBeforeClick = Boolean(beforeSelector || beforeText);
    const beforeWatch = await watchTextSnapshot(page, args);
    interaction.watchText.before = beforeWatch;
    let target = page.locator(args.clickSelector);
    if (args.clickText) {
      target = target.filter({ hasText: args.clickText });
    }
    target = target.first();
    await target.waitFor({ state: "visible", timeout: args.clickTimeoutMs });
    const repeatCount = Math.max(1, Math.floor(Number(args.clickRepeatCount) || 1));
    const repeatIntervalMs = Math.max(0, Math.floor(Number(args.clickRepeatIntervalMs) || 0));
    const repeatMode = String(args.clickRepeatMode || "playwright").toLowerCase();
    if (!["playwright", "mouse", "dom"].includes(repeatMode)) {
      throw new Error(`Unsupported click repeat mode: ${args.clickRepeatMode}`);
    }
    interaction.clickRepeatCount = repeatCount;
    interaction.clickRepeatIntervalMs = repeatIntervalMs;
    interaction.clickRepeatMode = repeatMode;
    interaction.startedEpochMillis = Date.now();
    const startBrowserMs = await page.evaluate(() => performance.now()).catch(() => null);
    if (repeatMode === "mouse" && repeatCount > 1) {
      const box = await target.boundingBox();
      if (!box) {
        throw new Error("Click target bounding box was unavailable for mouse repeat mode.");
      }
      const x = box.x + box.width / 2;
      const y = box.y + box.height / 2;
      for (let clickIndex = 0; clickIndex < repeatCount; clickIndex += 1) {
        await page.mouse.click(x, y);
        if (repeatIntervalMs > 0 && clickIndex < repeatCount - 1) {
          await page.waitForTimeout(repeatIntervalMs);
        }
      }
    } else if (repeatMode === "dom" && repeatCount > 1) {
      const handle = await target.elementHandle({ timeout: args.clickTimeoutMs });
      if (!handle) {
        throw new Error("Click target element handle was unavailable for DOM repeat mode.");
      }
      await handle.evaluate(
        async (element, repeat) => {
          const sleep = (ms) => new Promise((resolve) => setTimeout(resolve, ms));
          for (let clickIndex = 0; clickIndex < repeat.count; clickIndex += 1) {
            element.click();
            if (repeat.intervalMs > 0 && clickIndex < repeat.count - 1) {
              await sleep(repeat.intervalMs);
            }
          }
        },
        { count: repeatCount, intervalMs: repeatIntervalMs },
      );
      await handle.dispose();
    } else {
      for (let clickIndex = 0; clickIndex < repeatCount; clickIndex += 1) {
        await target.click({ timeout: args.clickTimeoutMs });
        if (repeatIntervalMs > 0 && clickIndex < repeatCount - 1) {
          await page.waitForTimeout(repeatIntervalMs);
        }
      }
    }
    const afterClickBrowserMs = await page.evaluate(() => performance.now()).catch(() => null);
    if (startBrowserMs !== null && afterClickBrowserMs !== null) {
      interaction.clickElapsedMs = afterClickBrowserMs - startBrowserMs;
    }
    const waits = [];
    if (args.clickResultSelector) {
      waits.push(page.waitForSelector(args.clickResultSelector, { state: "visible", timeout: args.clickTimeoutMs }));
    }
    if (args.clickResultText) {
      waits.push(
        page.waitForFunction(
          (text) => Boolean(document.body && document.body.innerText && document.body.innerText.indexOf(text) !== -1),
          args.clickResultText,
          { timeout: args.clickTimeoutMs },
        ),
      );
    }
    if (args.watchTextSelector) {
      waits.push(
        page.waitForFunction(
          ({ selector, regexText, beforeValue }) => {
            const element = document.querySelector(selector);
            if (!element) {
              return false;
            }
            const text = element.innerText || element.textContent || "";
            let value = text;
            if (regexText) {
              let regex;
              try {
                regex = new RegExp(regexText);
              } catch {
                return false;
              }
              const match = regex.exec(text);
              if (!match) {
                return false;
              }
              value = String(match[1] === undefined ? match[0] : match[1]);
            }
            return value !== null && value !== "" && value !== beforeValue;
          },
          { selector: args.watchTextSelector, regexText: args.watchTextRegex, beforeValue: beforeWatch.value },
          { timeout: args.watchTextTimeoutMs || args.clickTimeoutMs },
        ),
      );
    }
    if (waits.length > 0) {
      await Promise.all(waits);
    }
    const afterWatch = await watchTextSnapshot(page, args);
    interaction.watchText.after = afterWatch;
    interaction.watchText.changed = Boolean(
      args.watchTextSelector &&
        beforeWatch &&
        afterWatch &&
        beforeWatch.value !== null &&
        afterWatch.value !== null &&
        beforeWatch.value !== afterWatch.value,
    );
    const afterResultBrowserMs = await page.evaluate(() => performance.now()).catch(() => null);
    if (args.postInteractionWaitMs > 0) {
      await page.waitForTimeout(args.postInteractionWaitMs);
    }
    interaction.finishedEpochMillis = Date.now();
    if (startBrowserMs !== null && afterResultBrowserMs !== null) {
      interaction.resultElapsedMs = afterResultBrowserMs - startBrowserMs;
    }
    interaction.ok = waits.length > 0;
    if (waits.length === 0) {
      interaction.error = "No click result selector or text was provided; latency-to-visible-state is not measurable.";
    }
  } catch (error) {
    interaction.finishedEpochMillis = Date.now();
    interaction.ok = false;
    interaction.error = String(error && error.message ? error.message : error).slice(0, 2000);
  }
  return interaction;
}

async function browserTimelineSnapshot(page, label, sampleIndex) {
  try {
    const result = await page.evaluate(
      ({ labelValue, sampleIndexValue }) => {
        const resources = performance.getEntriesByType("resource");
        const probe = window.__perspectivePerfProbe || {};
        const longTasks = Array.isArray(probe.longTasks) ? probe.longTasks : [];
        const heap = performance.memory
          ? {
              usedJSHeapSize: performance.memory.usedJSHeapSize,
              totalJSHeapSize: performance.memory.totalJSHeapSize,
              jsHeapSizeLimit: performance.memory.jsHeapSizeLimit,
            }
          : null;
        return {
          ok: true,
          label: labelValue,
          sampleIndex: sampleIndexValue,
          performanceNowMs: performance.now(),
          domNodeCount: document.querySelectorAll("*").length,
          resourceCount: resources.length,
          resourceTransferSize: resources.reduce((sum, row) => sum + (row.transferSize || 0), 0),
          longTaskCount: longTasks.length,
          longTaskTotalMs: longTasks.reduce((sum, row) => sum + (row.duration || 0), 0),
          heap,
        };
      },
      { labelValue: label, sampleIndexValue: sampleIndex },
    );
    return { ...result, epochMillis: Date.now() };
  } catch (error) {
    return {
      ok: false,
      label,
      sampleIndex,
      epochMillis: Date.now(),
      error: String(error && error.message ? error.message : error).slice(0, 1000),
    };
  }
}

async function waitAfterReadyWithTimeline(page, args, timelineSamples) {
  const waitMs = Math.max(0, Number(args.waitAfterReadyMs || 0));
  const intervalMs = Math.max(0, Number(args.timelineSampleIntervalMs || 0));
  if (waitMs <= 0) {
    return;
  }
  if (intervalMs <= 0) {
    await page.waitForTimeout(waitMs);
    return;
  }
  let sampleIndex = timelineSamples.length;
  timelineSamples.push(await browserTimelineSnapshot(page, "post-ready", sampleIndex));
  let remainingMs = waitMs;
  while (remainingMs > 0) {
    const sleepMs = Math.min(intervalMs, remainingMs);
    await page.waitForTimeout(sleepMs);
    remainingMs -= sleepMs;
    sampleIndex = timelineSamples.length;
    timelineSamples.push(await browserTimelineSnapshot(page, "post-ready", sampleIndex));
  }
}

async function main() {
  const args = parseArgs(process.argv);
  if (args.help || !args.url) {
    console.log(usage());
    process.exit(args.help ? 0 : 2);
  }
  validateArgs(args);

  let chromium;
  try {
    ({ chromium } = await importPlaywright());
  } catch (error) {
    throw new Error(`Playwright is not available. Install playwright before running browser evidence: ${error.message}`);
  }

  const consoleRows = [];
  const networkRows = [];
  const websocketRows = [];
  const timelineSamples = [];
  const viewport = parseViewport(args.viewport);
  let browser = null;
  let context = null;
  if (args.userDataDir) {
    await fs.mkdir(args.userDataDir, { recursive: true });
    context = await chromium.launchPersistentContext(args.userDataDir, { headless: args.headless, viewport });
    browser = context.browser();
  } else {
    browser = await chromium.launch({ headless: args.headless });
    context = await browser.newContext({ viewport });
  }
  const page = await context.newPage();
  const cdpSession = await context.newCDPSession(page);
  const networkThrottle = {
    requested: networkThrottleRequested(args),
    afterReady: Boolean(args.networkThrottleAfterReady),
    beforeNavigation: null,
    afterPrimaryReady: null,
  };

  page.on("console", (message) => {
    consoleRows.push({
      type: message.type(),
      text: message.text().slice(0, 2000),
      location: message.location(),
      timestampEpochMillis: Date.now(),
    });
  });

  page.on("pageerror", (error) => {
    consoleRows.push({
      type: "pageerror",
      text: String(error && error.message ? error.message : error).slice(0, 2000),
      timestampEpochMillis: Date.now(),
    });
  });

  page.on("response", async (response) => {
    const request = response.request();
    const headers = response.headers();
    networkRows.push({
      url: redactUrl(response.url(), args.urlAlias),
      method: request.method(),
      resourceType: request.resourceType(),
      status: response.status(),
      fromServiceWorker: response.fromServiceWorker(),
      sizeBytes: responseSize(headers),
      timestampEpochMillis: Date.now(),
    });
  });

  page.on("websocket", (socket) => {
    const row = {
      url: redactUrl(socket.url(), args.urlAlias),
      openedEpochMillis: Date.now(),
      closedEpochMillis: null,
      framesSent: 0,
      framesReceived: 0,
      bytesSent: 0,
      bytesReceived: 0,
      errors: [],
    };
    websocketRows.push(row);
    socket.on("framesent", (event) => {
      row.framesSent += 1;
      row.bytesSent += payloadSize(event && event.payload);
    });
    socket.on("framereceived", (event) => {
      row.framesReceived += 1;
      row.bytesReceived += payloadSize(event && event.payload);
    });
    socket.on("socketerror", (error) => {
      row.errors.push(String(error && error.message ? error.message : error).slice(0, 1000));
    });
    socket.on("close", () => {
      row.closedEpochMillis = Date.now();
    });
  });

  await page.addInitScript(() => {
    window.__perspectivePerfProbe = { longTasks: [], lcp: null };
    try {
      const longTaskObserver = new PerformanceObserver((list) => {
        for (const entry of list.getEntries()) {
          window.__perspectivePerfProbe.longTasks.push({
            startTime: entry.startTime,
            duration: entry.duration,
            name: entry.name,
          });
        }
      });
      longTaskObserver.observe({ entryTypes: ["longtask"] });
    } catch (error) {
      window.__perspectivePerfProbe.longTaskError = String(error && error.message ? error.message : error);
    }
    try {
      const lcpObserver = new PerformanceObserver((list) => {
        const entries = list.getEntries();
        const last = entries[entries.length - 1];
        if (last) {
          window.__perspectivePerfProbe.lcp = {
            startTime: last.startTime,
            size: last.size || null,
            elementTag: last.element && last.element.tagName ? last.element.tagName : null,
          };
        }
      });
      lcpObserver.observe({ type: "largest-contentful-paint", buffered: true });
    } catch (error) {
      window.__perspectivePerfProbe.lcpError = String(error && error.message ? error.message : error);
    }
  });

  const startedEpochMillis = Date.now();
  let startedBrowserMillis = null;
  let ready = false;
  let readyError = null;
  let primaryReadyBrowserMillis = null;
  let primaryReadyEpochMillis = null;
  let secondaryReadyBrowserMillis = null;
  let secondaryReadyEpochMillis = null;
  let interaction = { configured: Boolean(args.clickSelector), ok: null };
  try {
    if (networkThrottle.requested && !networkThrottle.afterReady) {
      networkThrottle.beforeNavigation = await applyNetworkThrottle(cdpSession, args, "before-navigation");
      if (networkThrottle.beforeNavigation.error) {
        throw new Error(`Network throttle failed before navigation: ${networkThrottle.beforeNavigation.error}`);
      }
    }
    await page.goto(args.url, { waitUntil: "domcontentloaded", timeout: args.timeoutMs });
    startedBrowserMillis = 0;
    if (args.readySelector) {
      await page.waitForSelector(args.readySelector, { state: "visible", timeout: args.timeoutMs });
    }
    if (args.readyText) {
      await page.waitForFunction(
        (text) => Boolean(document.body && document.body.innerText && document.body.innerText.indexOf(text) !== -1),
        args.readyText,
        { timeout: args.timeoutMs },
      );
    }
    primaryReadyBrowserMillis = await page.evaluate(() => performance.now()).catch(() => null);
    primaryReadyEpochMillis = Date.now();
    if (networkThrottle.requested && networkThrottle.afterReady) {
      networkThrottle.afterPrimaryReady = await applyNetworkThrottle(cdpSession, args, "after-primary-ready");
      if (networkThrottle.afterPrimaryReady.error) {
        throw new Error(`Network throttle failed after ready: ${networkThrottle.afterPrimaryReady.error}`);
      }
    }
    if (args.secondaryReadySelector) {
      await page.waitForSelector(args.secondaryReadySelector, { state: "visible", timeout: args.timeoutMs });
    }
    if (args.secondaryReadyText) {
      await page.waitForFunction(
        (text) => Boolean(document.body && document.body.innerText && document.body.innerText.indexOf(text) !== -1),
        args.secondaryReadyText,
        { timeout: args.timeoutMs },
      );
    }
    if (args.secondaryReadySelector || args.secondaryReadyText) {
      secondaryReadyBrowserMillis = await page.evaluate(() => performance.now()).catch(() => null);
      secondaryReadyEpochMillis = Date.now();
    }
    await waitAfterReadyWithTimeline(page, args, timelineSamples);
    interaction = await runInteraction(page, args);
    ready = true;
  } catch (error) {
    readyError = String(error && error.message ? error.message : error);
  }
  const finishedEpochMillis = Date.now();

  const browserSummary = await page.evaluate(
    ({ startedBrowserMillisValue, readySelector, readyText, readyTextConfigured, secondaryReadySelector, secondaryReadyText, secondaryReadyTextConfigured }) => {
      const nav = performance.getEntriesByType("navigation")[0];
      const resources = performance.getEntriesByType("resource");
      const probe = window.__perspectivePerfProbe || {};
      const now = performance.now();
      const heap = performance.memory
        ? {
            usedJSHeapSize: performance.memory.usedJSHeapSize,
            totalJSHeapSize: performance.memory.totalJSHeapSize,
            jsHeapSizeLimit: performance.memory.jsHeapSizeLimit,
          }
        : null;
      return {
        readySelector,
        readyTextConfigured,
        readyTextMatched: readyTextConfigured
          ? Boolean(document.body && document.body.innerText && document.body.innerText.indexOf(readyText) !== -1)
          : null,
        secondaryReadySelector,
        secondaryReadySelectorConfigured: Boolean(secondaryReadySelector),
        secondaryReadyTextConfigured,
        secondaryReadyTextMatched: secondaryReadyTextConfigured
          ? Boolean(document.body && document.body.innerText && document.body.innerText.indexOf(secondaryReadyText) !== -1)
          : null,
        elapsedBrowserMs: startedBrowserMillisValue === null ? null : now - startedBrowserMillisValue,
        domNodeCount: document.querySelectorAll("*").length,
        documentTitle: document.title,
        navigation: nav
          ? {
              startTime: nav.startTime,
              domContentLoadedEventEnd: nav.domContentLoadedEventEnd,
              loadEventEnd: nav.loadEventEnd,
              transferSize: nav.transferSize,
              encodedBodySize: nav.encodedBodySize,
              decodedBodySize: nav.decodedBodySize,
            }
          : null,
        resourceCount: resources.length,
        resourceTransferSize: resources.reduce((sum, row) => sum + (row.transferSize || 0), 0),
        largestContentfulPaint: probe.lcp || null,
        longTaskCount: Array.isArray(probe.longTasks) ? probe.longTasks.length : null,
        longTaskTotalMs: Array.isArray(probe.longTasks)
          ? probe.longTasks.reduce((sum, row) => sum + (row.duration || 0), 0)
          : null,
        longTasks: Array.isArray(probe.longTasks) ? probe.longTasks.slice(0, 100) : [],
        heap,
      };
    },
    {
      startedBrowserMillisValue: startedBrowserMillis,
      readySelector: args.readySelector,
      readyText: args.readyText,
      readyTextConfigured: Boolean(args.readyText),
      secondaryReadySelector: args.secondaryReadySelector,
      secondaryReadyText: args.secondaryReadyText,
      secondaryReadyTextConfigured: Boolean(args.secondaryReadyText),
    },
  );

  const summary = {
    ok: ready,
    url: redactUrl(args.url, args.urlAlias),
    startedEpochMillis,
    finishedEpochMillis,
    elapsedWallMs: finishedEpochMillis - startedEpochMillis,
    ready,
    readyError,
    primaryReadyEpochMillis,
    primaryReadyElapsedWallMs: primaryReadyEpochMillis === null ? null : primaryReadyEpochMillis - startedEpochMillis,
    primaryReadyElapsedBrowserMs:
      startedBrowserMillis === null || primaryReadyBrowserMillis === null ? null : primaryReadyBrowserMillis - startedBrowserMillis,
    secondaryReadyEpochMillis,
    secondaryReadyElapsedWallMs: secondaryReadyEpochMillis === null ? null : secondaryReadyEpochMillis - startedEpochMillis,
    secondaryReadyElapsedBrowserMs:
      startedBrowserMillis === null || secondaryReadyBrowserMillis === null ? null : secondaryReadyBrowserMillis - startedBrowserMillis,
    secondaryReadyConfigured: Boolean(args.secondaryReadySelector || args.secondaryReadyText),
    networkThrottle,
    persistentContext: Boolean(args.userDataDir),
    viewport,
    browserName: "chromium",
    waitAfterReadyMs: args.waitAfterReadyMs,
    timelineSampleIntervalMs: args.timelineSampleIntervalMs,
    timelineSamples,
    interaction,
    ...browserSummary,
  };
  summary.ok = Boolean(ready && (!interaction.configured || interaction.ok === true));

  await writeJson(args.outDir, "browser-summary.json", summary);
  await writeJson(args.outDir, "browser-console.json", consoleRows);
  await writeJson(args.outDir, "network-summary.json", {
    requestCount: networkRows.length,
    statusCounts: networkRows.reduce((counts, row) => {
      counts[row.status] = (counts[row.status] || 0) + 1;
      return counts;
    }, {}),
    knownContentLengthBytes: networkRows.reduce((sum, row) => sum + (row.sizeBytes || 0), 0),
    webSocketCount: websocketRows.length,
    webSocketFramesSent: websocketRows.reduce((sum, row) => sum + row.framesSent, 0),
    webSocketFramesReceived: websocketRows.reduce((sum, row) => sum + row.framesReceived, 0),
    webSocketBytesSent: websocketRows.reduce((sum, row) => sum + row.bytesSent, 0),
    webSocketBytesReceived: websocketRows.reduce((sum, row) => sum + row.bytesReceived, 0),
    responses: networkRows,
    webSockets: websocketRows,
  });

  await context.close();
  if (!args.userDataDir && browser) {
    await browser.close();
  }

  console.log(JSON.stringify(summary, null, 2));
  process.exit(summary.ok ? 0 : 1);
}

main().catch((error) => {
  console.error(error && error.stack ? error.stack : String(error));
  process.exit(1);
});
