#!/usr/bin/env node
// Browser evidence probe for repeated Perspective navigation lifecycle checks.
//
// Navigates control -> target -> control for N cycles in one Chromium context
// and writes per-step timing, DOM, heap, resource, console, and WebSocket
// evidence with redacted URLs.

import fs from "node:fs/promises";
import path from "node:path";
import { pathToFileURL } from "node:url";

function parseArgs(argv) {
  const args = {
    cycles: 20,
    timeoutMs: 30000,
    settleMs: 1000,
    outDir: "",
    viewport: "1366x768",
    headless: true,
    urlAlias: "gateway",
    controlReadySelector: "body",
    targetReadySelector: "body",
    controlReadyText: "",
    targetReadyText: "",
  };
  for (let index = 2; index < argv.length; index += 1) {
    const arg = argv[index];
    const next = argv[index + 1];
    if (arg === "--control-url") {
      args.controlUrl = next;
      index += 1;
    } else if (arg === "--target-url") {
      args.targetUrl = next;
      index += 1;
    } else if (arg === "--cycles") {
      args.cycles = Number(next);
      index += 1;
    } else if (arg === "--control-ready-selector") {
      args.controlReadySelector = next;
      index += 1;
    } else if (arg === "--target-ready-selector") {
      args.targetReadySelector = next;
      index += 1;
    } else if (arg === "--control-ready-text") {
      args.controlReadyText = next;
      index += 1;
    } else if (arg === "--target-ready-text") {
      args.targetReadyText = next;
      index += 1;
    } else if (arg === "--settle-ms") {
      args.settleMs = Number(next);
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
    "Usage: node browser_navigation_cycles.mjs --control-url <url> --target-url <url> [options]",
    "",
    "Options:",
    "  --cycles <n>                         Default: 20",
    "  --control-ready-selector <selector>  Default: body",
    "  --target-ready-selector <selector>   Default: body",
    "  --control-ready-text <text>          Optional body text for control readiness",
    "  --target-ready-text <text>           Optional body text for target readiness",
    "  --settle-ms <ms>                     Extra wait after each ready marker. Default: 1000",
    "  --timeout-ms <ms>                    Per-navigation timeout. Default: 30000",
    "  --viewport <width>x<height>          Default: 1366x768",
    "  --out-dir <dir>                      Write JSON evidence files to this folder",
    "  --url-alias <alias>                  Redacted URL prefix in evidence. Default: gateway",
    "  --headed                             Run Chromium headed",
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

async function importPlaywright() {
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
    const nodePath = process.env.NODE_PATH || "";
    for (const root of nodePath.split(path.delimiter).filter(Boolean)) {
      for (const fileName of ["index.mjs", "index.js"]) {
        const candidate = path.join(root, "playwright", fileName);
        try {
          await fs.access(candidate);
          return normalize(await import(pathToFileURL(candidate).href));
        } catch {
          // Continue trying remaining NODE_PATH entries.
        }
      }
    }
    throw firstError;
  }
}

function numericStats(values) {
  const nums = values.filter((value) => Number.isFinite(value)).sort((a, b) => a - b);
  if (!nums.length) {
    return { count: 0 };
  }
  const quantile = (q) => {
    const index = Math.min(nums.length - 1, Math.max(0, Math.round((nums.length - 1) * q)));
    return nums[index];
  };
  return {
    count: nums.length,
    min: nums[0],
    median: quantile(0.5),
    p95: quantile(0.95),
    max: nums[nums.length - 1],
  };
}

function strictlyIncreasing(values) {
  if (values.length < 2) {
    return false;
  }
  for (let index = 1; index < values.length; index += 1) {
    if (!(values[index] > values[index - 1])) {
      return false;
    }
  }
  return true;
}

function lastMinusFirst(values) {
  if (values.length < 2) {
    return null;
  }
  return values[values.length - 1] - values[0];
}

function maxPairDelta(steps, metric) {
  const deltas = [];
  for (const step of steps.filter((item) => item.phase === "control-after")) {
    const before = steps.find((item) => item.cycle === step.cycle && item.phase === "control-before");
    if (!before) {
      continue;
    }
    const afterValue = step[metric];
    const beforeValue = before[metric];
    if (Number.isFinite(afterValue) && Number.isFinite(beforeValue)) {
      deltas.push(afterValue - beforeValue);
    }
  }
  return deltas.length ? Math.max(...deltas) : null;
}

async function waitForReady(page, selector, text, timeoutMs) {
  if (selector) {
    await page.waitForSelector(selector, { state: "visible", timeout: timeoutMs });
  }
  if (text) {
    await page.waitForFunction(
      (expected) => Boolean(document.body && document.body.innerText && document.body.innerText.indexOf(expected) !== -1),
      text,
      { timeout: timeoutMs },
    );
  }
}

async function resetStepObservers(page) {
  await page.evaluate(() => {
    try {
      performance.clearResourceTimings();
    } catch {
      // Ignore browser support differences.
    }
    window.__perspectivePerfCycleProbe = { longTasks: [], lcp: null };
  }).catch(() => null);
}

async function collectStepSummary(page, startedBrowserMillis, readySelector, readyText, readyTextConfigured) {
  return page.evaluate(
    ({ startedBrowserMillisValue, selector, text, textConfigured }) => {
      const navEntries = performance.getEntriesByType("navigation");
      const nav = navEntries[navEntries.length - 1];
      const resources = performance.getEntriesByType("resource");
      const probe = window.__perspectivePerfCycleProbe || {};
      const now = performance.now();
      const heap = performance.memory
        ? {
            usedJSHeapSize: performance.memory.usedJSHeapSize,
            totalJSHeapSize: performance.memory.totalJSHeapSize,
            jsHeapSizeLimit: performance.memory.jsHeapSizeLimit,
          }
        : null;
      const longTasks = Array.isArray(probe.longTasks) ? probe.longTasks : [];
      return {
        readySelector: selector,
        readyTextConfigured: textConfigured,
        readyTextMatched: textConfigured
          ? Boolean(document.body && document.body.innerText && document.body.innerText.indexOf(text) !== -1)
          : null,
        elapsedBrowserMs: now,
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
        longTaskCount: longTasks.length,
        longTaskTotalMs: longTasks.reduce((sum, row) => sum + (row.duration || 0), 0),
        longTasks: longTasks.slice(0, 100),
        heap,
      };
    },
    {
      startedBrowserMillisValue: startedBrowserMillis,
      selector: readySelector,
      text: readyText,
      textConfigured: Boolean(readyText),
    },
  );
}

async function navigateStep(page, args, step, stepNetworkStart) {
  await resetStepObservers(page);
  const startedEpochMillis = Date.now();
  const startedBrowserMillis = null;
  let ready = false;
  let readyError = null;
  try {
    await page.goto(step.url, { waitUntil: "domcontentloaded", timeout: args.timeoutMs });
    await waitForReady(page, step.readySelector, step.readyText, args.timeoutMs);
    if (args.settleMs > 0) {
      await page.waitForTimeout(args.settleMs);
    }
    ready = true;
  } catch (error) {
    readyError = String(error && error.message ? error.message : error).slice(0, 2000);
  }
  const finishedEpochMillis = Date.now();
  let browserSummary = {};
  try {
    browserSummary = await collectStepSummary(page, startedBrowserMillis, step.readySelector, step.readyText, Boolean(step.readyText));
  } catch (error) {
    ready = false;
    readyError = readyError || String(error && error.message ? error.message : error).slice(0, 2000);
  }
  return {
    cycle: step.cycle,
    phase: step.phase,
    url: redactUrl(step.url, args.urlAlias),
    startedEpochMillis,
    finishedEpochMillis,
    elapsedWallMs: finishedEpochMillis - startedEpochMillis,
    networkResponsesDuringStep: stepNetworkStart,
    ready,
    readyError,
    ...browserSummary,
  };
}

function buildStepSummary(steps) {
  const targets = steps.filter((step) => step.phase === "target");
  const targetElapsed = targets.map((step) => step.elapsedWallMs);
  const targetDom = targets.map((step) => step.domNodeCount);
  const targetHeap = targets.map((step) => step.heap && step.heap.usedJSHeapSize).filter((value) => Number.isFinite(value));
  const controlAfterElapsed = steps.filter((step) => step.phase === "control-after").map((step) => step.elapsedWallMs);
  const controlBeforeElapsed = steps.filter((step) => step.phase === "control-before").map((step) => step.elapsedWallMs);
  return {
    stepCount: steps.length,
    readyStepCount: steps.filter((step) => step.ready).length,
    targetElapsedMs: numericStats(targetElapsed),
    controlBeforeElapsedMs: numericStats(controlBeforeElapsed),
    controlAfterElapsedMs: numericStats(controlAfterElapsed),
    targetDomNodeCount: numericStats(targetDom),
    targetJSHeapUsedBytes: numericStats(targetHeap),
    targetElapsedStrictlyIncreasing: strictlyIncreasing(targetElapsed),
    targetElapsedLastMinusFirstMs: lastMinusFirst(targetElapsed),
    targetDomLastMinusFirst: lastMinusFirst(targetDom),
    maxControlAfterMinusBeforeElapsedMs: maxPairDelta(steps, "elapsedWallMs"),
    maxControlAfterMinusBeforeDomNodes: maxPairDelta(steps, "domNodeCount"),
  };
}

async function main() {
  const args = parseArgs(process.argv);
  if (args.help || !args.controlUrl || !args.targetUrl) {
    console.log(usage());
    process.exit(args.help ? 0 : 2);
  }
  if (!Number.isInteger(args.cycles) || args.cycles <= 0) {
    throw new Error("--cycles must be a positive integer");
  }

  let chromium;
  try {
    ({ chromium } = await importPlaywright());
  } catch (error) {
    throw new Error(`Playwright is not available. Install playwright before running browser evidence: ${error.message}`);
  }

  const consoleRows = [];
  const networkRows = [];
  const websocketRows = [];
  const steps = [];
  let currentStep = null;
  const viewport = parseViewport(args.viewport);
  const browser = await chromium.launch({ headless: args.headless });
  const context = await browser.newContext({ viewport });
  const page = await context.newPage();

  page.on("console", (message) => {
    consoleRows.push({
      type: message.type(),
      text: message.text().slice(0, 2000),
      location: message.location(),
      cycle: currentStep ? currentStep.cycle : null,
      phase: currentStep ? currentStep.phase : null,
      timestampEpochMillis: Date.now(),
    });
  });

  page.on("pageerror", (error) => {
    consoleRows.push({
      type: "pageerror",
      text: String(error && error.message ? error.message : error).slice(0, 2000),
      cycle: currentStep ? currentStep.cycle : null,
      phase: currentStep ? currentStep.phase : null,
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
      cycle: currentStep ? currentStep.cycle : null,
      phase: currentStep ? currentStep.phase : null,
      timestampEpochMillis: Date.now(),
    });
  });

  page.on("websocket", (socket) => {
    const row = {
      url: redactUrl(socket.url(), args.urlAlias),
      openedEpochMillis: Date.now(),
      closedEpochMillis: null,
      openedCycle: currentStep ? currentStep.cycle : null,
      openedPhase: currentStep ? currentStep.phase : null,
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
    window.__perspectivePerfCycleProbe = { longTasks: [], lcp: null };
    try {
      const longTaskObserver = new PerformanceObserver((list) => {
        for (const entry of list.getEntries()) {
          window.__perspectivePerfCycleProbe.longTasks.push({
            startTime: entry.startTime,
            duration: entry.duration,
            name: entry.name,
          });
        }
      });
      longTaskObserver.observe({ entryTypes: ["longtask"] });
    } catch (error) {
      window.__perspectivePerfCycleProbe.longTaskError = String(error && error.message ? error.message : error);
    }
    try {
      const lcpObserver = new PerformanceObserver((list) => {
        const entries = list.getEntries();
        const last = entries[entries.length - 1];
        if (last) {
          window.__perspectivePerfCycleProbe.lcp = {
            startTime: last.startTime,
            size: last.size || null,
            elementTag: last.element && last.element.tagName ? last.element.tagName : null,
          };
        }
      });
      lcpObserver.observe({ type: "largest-contentful-paint", buffered: true });
    } catch (error) {
      window.__perspectivePerfCycleProbe.lcpError = String(error && error.message ? error.message : error);
    }
  });

  const startedEpochMillis = Date.now();
  for (let cycle = 1; cycle <= args.cycles; cycle += 1) {
    const cycleSteps = [
      {
        cycle,
        phase: "control-before",
        url: args.controlUrl,
        readySelector: args.controlReadySelector,
        readyText: args.controlReadyText,
      },
      {
        cycle,
        phase: "target",
        url: args.targetUrl,
        readySelector: args.targetReadySelector,
        readyText: args.targetReadyText,
      },
      {
        cycle,
        phase: "control-after",
        url: args.controlUrl,
        readySelector: args.controlReadySelector,
        readyText: args.controlReadyText,
      },
    ];
    for (const step of cycleSteps) {
      currentStep = { cycle: step.cycle, phase: step.phase };
      const networkStart = networkRows.length;
      const row = await navigateStep(page, args, step, networkStart);
      row.networkResponsesDuringStep = networkRows.length - networkStart;
      steps.push(row);
      if (!row.ready) {
        break;
      }
    }
    if (steps.length && steps[steps.length - 1].ready === false) {
      break;
    }
  }
  currentStep = null;
  const finishedEpochMillis = Date.now();

  const summary = {
    ok: steps.length === args.cycles * 3 && steps.every((step) => step.ready),
    cyclesRequested: args.cycles,
    cyclesCompleted: Math.floor(steps.length / 3),
    stepCount: steps.length,
    startedEpochMillis,
    finishedEpochMillis,
    elapsedWallMs: finishedEpochMillis - startedEpochMillis,
    controlUrl: redactUrl(args.controlUrl, args.urlAlias),
    targetUrl: redactUrl(args.targetUrl, args.urlAlias),
    viewport,
    browserName: "chromium",
    settleMs: args.settleMs,
    readySelectors: {
      control: args.controlReadySelector,
      target: args.targetReadySelector,
    },
    readyTextConfigured: {
      control: Boolean(args.controlReadyText),
      target: Boolean(args.targetReadyText),
    },
    cycles: steps,
    aggregate: buildStepSummary(steps),
  };

  await writeJson(args.outDir, "browser-navigation-cycles.json", steps);
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
  await browser.close();

  console.log(JSON.stringify(summary, null, 2));
  process.exit(summary.ok ? 0 : 1);
}

main().catch((error) => {
  console.error(error && error.stack ? error.stack : String(error));
  process.exit(1);
});
