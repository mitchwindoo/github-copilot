#!/usr/bin/env node
// Browser evidence probe for repeated Perspective Carousel rotation checks.

import fs from "node:fs";
import path from "node:path";
import { Buffer } from "node:buffer";
import { createRequire } from "node:module";
import { pathToFileURL } from "node:url";

function parseArgs(argv) {
  const args = {
    url: "",
    outDir: "",
    readySelector: "body",
    readyText: "",
    clickText: "Next slide",
    cycles: 12,
    cycleDelayMs: 500,
    timeoutMs: 60000,
    viewport: "1366x768",
    urlAlias: "target-gateway",
  };
  for (let index = 2; index < argv.length; index += 1) {
    const arg = argv[index];
    const next = argv[index + 1];
    if (arg === "--url") {
      args.url = next || "";
      index += 1;
    } else if (arg === "--out-dir") {
      args.outDir = next || "";
      index += 1;
    } else if (arg === "--ready-selector") {
      args.readySelector = next || "body";
      index += 1;
    } else if (arg === "--ready-text") {
      args.readyText = next || "";
      index += 1;
    } else if (arg === "--click-text") {
      args.clickText = next || "Next slide";
      index += 1;
    } else if (arg === "--cycles") {
      args.cycles = Number(next);
      index += 1;
    } else if (arg === "--cycle-delay-ms") {
      args.cycleDelayMs = Number(next);
      index += 1;
    } else if (arg === "--timeout-ms") {
      args.timeoutMs = Number(next);
      index += 1;
    } else if (arg === "--viewport") {
      args.viewport = next || "1366x768";
      index += 1;
    } else if (arg === "--url-alias") {
      args.urlAlias = next || "target-gateway";
      index += 1;
    } else if (arg === "--help" || arg === "-h") {
      console.log([
        "Usage: node browser_carousel_cycle_probe.mjs --url <url> --out-dir <dir> [options]",
        "  --ready-selector <selector>  Default: body",
        "  --ready-text <text>          Optional body text required before cycles",
        "  --click-text <text>          Exact button text to click. Default: Next slide",
        "  --cycles <n>                 Rotation clicks. Default: 12",
        "  --cycle-delay-ms <ms>        Delay after each observed rotation. Default: 500",
        "  --timeout-ms <ms>            Per-step timeout. Default: 60000",
        "  --viewport <WxH>             Default: 1366x768",
        "  --url-alias <alias>          Non-secret URL alias for evidence",
      ].join("\n"));
      process.exit(0);
    }
  }
  if (!args.url || !args.outDir) {
    throw new Error("--url and --out-dir are required");
  }
  if (!Number.isFinite(args.cycles) || args.cycles < 1) {
    throw new Error("--cycles must be >= 1");
  }
  return args;
}

function parseViewport(value) {
  const match = String(value || "").match(/^(\d+)x(\d+)$/);
  if (!match) {
    return { width: 1366, height: 768 };
  }
  return { width: Number(match[1]), height: Number(match[2]) };
}

function ensureDir(dir) {
  fs.mkdirSync(dir, { recursive: true });
}

function writeJson(filePath, data) {
  ensureDir(path.dirname(filePath));
  fs.writeFileSync(filePath, JSON.stringify(data, null, 2) + "\n", "utf8");
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
      // Try absolute fallback paths from NODE_PATH below.
    }
    const nodePath = process.env.NODE_PATH || "";
    for (const root of nodePath.split(path.delimiter).filter(Boolean)) {
      for (const fileName of ["index.js", "index.mjs"]) {
        const candidate = path.join(root, "playwright", fileName);
        try {
          if (!fs.existsSync(candidate)) {
            continue;
          }
          if (fileName.endsWith(".js")) {
            return normalize(require(candidate));
          }
          return normalize(await import(pathToFileURL(candidate).href));
        } catch {
          // Continue trying remaining entries.
        }
      }
    }
    throw firstError;
  }
}

function nowIso() {
  return new Date().toISOString().replace(/\.\d{3}Z$/, "Z");
}

async function bodyContains(page, text) {
  if (!text) {
    return true;
  }
  return page.evaluate((expected) => Boolean(document.body && document.body.innerText && document.body.innerText.indexOf(expected) !== -1), text);
}

async function waitForBodyText(page, text, timeoutMs) {
  if (!text) {
    return true;
  }
  await page.waitForFunction(
    (expected) => Boolean(document.body && document.body.innerText && document.body.innerText.indexOf(expected) !== -1),
    text,
    { timeout: timeoutMs },
  );
  return true;
}

async function collectObservation(page, cycleIndex) {
  return page.evaluate((cycle) => {
    const probe = window.__carouselPerfProbe || {};
    const longTasks = Array.isArray(probe.longTasks) ? probe.longTasks : [];
    const bodyText = document.body && document.body.innerText ? document.body.innerText : "";
    const rotationMatch = bodyText.match(/Rotation count:\s*(\d+)\s+active pane:\s*(\d+)/);
    const slideMatches = Array.from(new Set((bodyText.match(/Carousel slide\s+\d+/g) || []).slice(0, 20)));
    const heap = performance.memory
      ? {
          usedJSHeapSize: performance.memory.usedJSHeapSize,
          totalJSHeapSize: performance.memory.totalJSHeapSize,
          jsHeapSizeLimit: performance.memory.jsHeapSizeLimit,
        }
      : null;
    return {
      cycle,
      sampledAt: new Date().toISOString().replace(/\.\d{3}Z$/, "Z"),
      domNodeCount: document.querySelectorAll("*").length,
      heap,
      longTaskCount: longTasks.length,
      longTaskTotalMs: longTasks.reduce((sum, row) => sum + (row.duration || 0), 0),
      rotationCount: rotationMatch ? Number(rotationMatch[1]) : null,
      activePane: rotationMatch ? Number(rotationMatch[2]) : null,
      visibleSlideLabels: slideMatches,
    };
  }, cycleIndex);
}

function summarizeObservations(observations) {
  const domValues = observations.map((row) => row.domNodeCount).filter((value) => Number.isFinite(value));
  const heapValues = observations
    .map((row) => (row.heap && Number.isFinite(row.heap.usedJSHeapSize) ? row.heap.usedJSHeapSize : null))
    .filter((value) => value !== null);
  const activePanes = observations.map((row) => row.activePane).filter((value) => Number.isFinite(value));
  const slideLabels = Array.from(new Set(observations.flatMap((row) => (Array.isArray(row.visibleSlideLabels) ? row.visibleSlideLabels : [])))).sort();
  return {
    sampleCount: observations.length,
    domFirst: domValues.length ? domValues[0] : null,
    domLast: domValues.length ? domValues[domValues.length - 1] : null,
    domMin: domValues.length ? Math.min(...domValues) : null,
    domMax: domValues.length ? Math.max(...domValues) : null,
    heapFirst: heapValues.length ? heapValues[0] : null,
    heapLast: heapValues.length ? heapValues[heapValues.length - 1] : null,
    heapMin: heapValues.length ? Math.min(...heapValues) : null,
    heapMax: heapValues.length ? Math.max(...heapValues) : null,
    activePaneSequence: activePanes,
    uniqueActivePanes: Array.from(new Set(activePanes)).sort((left, right) => left - right),
    uniqueSlideLabels: slideLabels,
  };
}

async function main() {
  const args = parseArgs(process.argv);
  ensureDir(args.outDir);
  const { chromium } = await importPlaywright();
  const viewport = parseViewport(args.viewport);
  const consoleRows = [];
  const pageErrors = [];
  const responseStatusCounts = {};
  const resourceTypeCounts = {};
  const websocket = { opened: 0, framesSent: 0, framesReceived: 0, bytesSent: 0, bytesReceived: 0 };
  const browser = await chromium.launch({ headless: true });
  const context = await browser.newContext({ viewport });
  const page = await context.newPage();
  await page.addInitScript(() => {
    window.__carouselPerfProbe = { longTasks: [] };
    try {
      const observer = new PerformanceObserver((list) => {
        for (const entry of list.getEntries()) {
          window.__carouselPerfProbe.longTasks.push({
            name: entry.name,
            startTime: entry.startTime,
            duration: entry.duration,
          });
        }
      });
      observer.observe({ entryTypes: ["longtask"] });
    } catch (error) {
      window.__carouselPerfProbe.longTaskError = String(error && error.message ? error.message : error);
    }
  });
  page.on("console", (message) => {
    consoleRows.push({
      type: message.type(),
      text: message.text().slice(0, 2000),
      location: message.location(),
    });
  });
  page.on("pageerror", (error) => {
    pageErrors.push({ message: String(error && error.message ? error.message : error).slice(0, 2000) });
  });
  page.on("response", (response) => {
    const status = String(response.status());
    responseStatusCounts[status] = (responseStatusCounts[status] || 0) + 1;
    const resourceType = response.request().resourceType();
    resourceTypeCounts[resourceType] = (resourceTypeCounts[resourceType] || 0) + 1;
  });
  page.on("websocket", (ws) => {
    websocket.opened += 1;
    ws.on("framesent", (event) => {
      websocket.framesSent += 1;
      websocket.bytesSent += Buffer.byteLength(String(event.payload || ""), "utf8");
    });
    ws.on("framereceived", (event) => {
      websocket.framesReceived += 1;
      websocket.bytesReceived += Buffer.byteLength(String(event.payload || ""), "utf8");
    });
  });

  const startedAt = nowIso();
  const startedEpochMillis = Date.now();
  const observations = [];
  let ready = false;
  let errorText = null;
  try {
    await page.goto(args.url, { waitUntil: "domcontentloaded", timeout: args.timeoutMs });
    if (args.readySelector) {
      await page.waitForSelector(args.readySelector, { state: "visible", timeout: args.timeoutMs });
    }
    if (args.readyText) {
      await waitForBodyText(page, args.readyText, args.timeoutMs);
    }
    ready = true;
    observations.push(await collectObservation(page, 0));
    for (let cycle = 1; cycle <= args.cycles; cycle += 1) {
      await page.getByText(args.clickText, { exact: true }).first().click({ timeout: args.timeoutMs });
      await waitForBodyText(page, `Rotation count: ${cycle}`, args.timeoutMs);
      if (args.cycleDelayMs > 0) {
        await page.waitForTimeout(args.cycleDelayMs);
      }
      observations.push(await collectObservation(page, cycle));
    }
  } catch (error) {
    errorText = String(error && error.message ? error.message : error);
  }

  const finishedAt = nowIso();
  const elapsedMs = Date.now() - startedEpochMillis;
  const observationSummary = summarizeObservations(observations);
  const consoleErrorCount = consoleRows.filter((row) => row.type === "error").length + pageErrors.length;
  const consoleWarningCount = consoleRows.filter((row) => row.type === "warning").length;
  const renderWarningCount = consoleRows.filter((row) => /ComponentRegistry\.NotFound|Error rendering component/i.test(row.text || "")).length;
  const ok = Boolean(
    ready &&
      !errorText &&
      observations.length === args.cycles + 1 &&
      observationSummary.uniqueActivePanes.length >= Math.min(2, args.cycles + 1) &&
      observationSummary.uniqueSlideLabels.length >= Math.min(2, args.cycles + 1) &&
      consoleErrorCount === 0 &&
      renderWarningCount === 0,
  );
  const summary = {
    ok,
    urlAlias: args.urlAlias,
    startedAt,
    finishedAt,
    elapsedMs,
    ready,
    readyTextConfigured: Boolean(args.readyText),
    readyTextMatched: args.readyText ? await bodyContains(page, args.readyText).catch(() => false) : null,
    error: errorText,
    clickTextConfigured: Boolean(args.clickText),
    cyclesRequested: args.cycles,
    cyclesObserved: Math.max(0, observations.length - 1),
    observations,
    observationSummary,
    consoleErrorCount,
    consoleWarningCount,
    renderWarningCount,
    network: {
      responseStatusCounts,
      resourceTypeCounts,
      websocket,
    },
  };

  writeJson(path.join(args.outDir, "browser-carousel-cycles.json"), summary);
  writeJson(path.join(args.outDir, "browser-summary.json"), summary);
  writeJson(path.join(args.outDir, "browser-console.json"), { console: consoleRows, pageErrors });
  writeJson(path.join(args.outDir, "network-summary.json"), summary.network);
  await context.close().catch(() => {});
  await browser.close().catch(() => {});
  process.exit(ok ? 0 : 1);
}

main().catch((error) => {
  const message = String(error && error.stack ? error.stack : error);
  try {
    const outIndex = process.argv.indexOf("--out-dir");
    if (outIndex >= 0 && process.argv[outIndex + 1]) {
      writeJson(path.join(process.argv[outIndex + 1], "browser-summary.json"), { ok: false, error: message });
    }
  } catch (_ignored) {
    // Best-effort failure evidence only.
  }
  console.error(message);
  process.exit(1);
});
