#!/usr/bin/env node
// Browser evidence probe for Tab Container runWhileHidden checks.

import fs from "node:fs/promises";
import { createRequire } from "node:module";
import path from "node:path";
import { pathToFileURL } from "node:url";

function parseArgs(argv) {
  const args = {
    timeoutMs: 30000,
    holdMs: 12000,
    settleMs: 500,
    outDir: "",
    markerPath: "",
    viewport: "1366x768",
    headless: true,
    urlAlias: "gateway",
    initialReadyText: "",
    workReadyText: "",
    returnReadyText: "",
    controlTabText: "Control Tab",
    workTabText: "Work Tab",
    controlTabIndex: null,
    workTabIndex: null,
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
    } else if (arg === "--marker-path") {
      args.markerPath = next;
      index += 1;
    } else if (arg === "--initial-ready-text") {
      args.initialReadyText = next;
      index += 1;
    } else if (arg === "--work-ready-text") {
      args.workReadyText = next;
      index += 1;
    } else if (arg === "--return-ready-text") {
      args.returnReadyText = next;
      index += 1;
    } else if (arg === "--control-tab-text") {
      args.controlTabText = next;
      index += 1;
    } else if (arg === "--work-tab-text") {
      args.workTabText = next;
      index += 1;
    } else if (arg === "--control-tab-index") {
      args.controlTabIndex = Number(next);
      index += 1;
    } else if (arg === "--work-tab-index") {
      args.workTabIndex = Number(next);
      index += 1;
    } else if (arg === "--hold-ms") {
      args.holdMs = Number(next);
      index += 1;
    } else if (arg === "--settle-ms") {
      args.settleMs = Number(next);
      index += 1;
    } else if (arg === "--timeout-ms") {
      args.timeoutMs = Number(next);
      index += 1;
    } else if (arg === "--viewport") {
      args.viewport = next;
      index += 1;
    } else if (arg === "--url-alias") {
      args.urlAlias = next;
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
    "Usage: node browser_tab_switch_probe.mjs --url <route-url> --out-dir <dir> [options]",
    "",
    "Options:",
    "  --initial-ready-text <text>  Text visible on first tab",
    "  --work-ready-text <text>     Text visible after activating work tab",
    "  --return-ready-text <text>   Text visible after returning to control tab",
    "  --control-tab-text <text>    Default: Control Tab",
    "  --work-tab-text <text>       Default: Work Tab",
    "  --control-tab-index <n>       Fallback tab index when text is absent",
    "  --work-tab-index <n>          Fallback tab index when text is absent",
    "  --marker-path <path>         JSON marker written when background hold starts",
    "  --hold-ms <ms>               Background hold duration. Default: 12000",
    "  --settle-ms <ms>             Delay after each tab switch. Default: 500",
    "  --timeout-ms <ms>            Per-step timeout. Default: 30000",
    "  --viewport <width>x<height>  Default: 1366x768",
    "  --url-alias <alias>          Redacted URL prefix in evidence",
    "  --headed                     Run Chromium headed",
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
      // Try NODE_PATH fallbacks below.
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
          // Continue trying remaining entries.
        }
      }
    }
    throw firstError;
  }
}

async function waitForBodyText(page, text, timeoutMs) {
  if (!text) {
    return;
  }
  await page.waitForFunction(
    (expected) => Boolean(document.body && document.body.innerText && document.body.innerText.indexOf(expected) !== -1),
    text,
    { timeout: timeoutMs },
  );
}

async function clickText(page, text, timeoutMs) {
  const target = page.getByText(text, { exact: true }).first();
  await target.waitFor({ state: "visible", timeout: timeoutMs });
  await target.click({ timeout: timeoutMs });
}

async function clickTabByIndex(page, tabIndex, timeoutMs) {
  if (!Number.isInteger(tabIndex) || tabIndex < 0) {
    throw new Error("No tab text matched and no valid tab index fallback was supplied");
  }
  const deadline = Date.now() + timeoutMs;
  let lastError = "";
  while (Date.now() < deadline) {
    try {
      const clicked = await page.evaluate((index) => {
        const isVisible = (element) => {
          const rect = element.getBoundingClientRect();
          const style = window.getComputedStyle(element);
          return rect.width > 8 && rect.height > 8 && style.visibility !== "hidden" && style.display !== "none";
        };
        const all = Array.from(document.querySelectorAll('[role="tab"], [class*="tab"], [class*="Tab"]'));
        const candidates = all
          .filter((element) => {
            if (!isVisible(element)) {
              return false;
            }
            const rect = element.getBoundingClientRect();
            const role = (element.getAttribute("role") || "").toLowerCase();
            const className = String(element.className || "").toLowerCase();
            const clickable = role === "tab" || className.includes("tab");
            return clickable && rect.top >= 0 && rect.top < Math.max(220, window.innerHeight * 0.35);
          })
          .sort((left, right) => {
            const a = left.getBoundingClientRect();
            const b = right.getBoundingClientRect();
            return a.top === b.top ? a.left - b.left : a.top - b.top;
          });
        window.__tabSwitchProbe = window.__tabSwitchProbe || {};
        window.__tabSwitchProbe.tabCandidates = candidates.slice(0, 20).map((element) => {
          const rect = element.getBoundingClientRect();
          return {
            tag: element.tagName,
            role: element.getAttribute("role") || "",
            className: String(element.className || "").slice(0, 200),
            text: (element.innerText || element.textContent || "").trim().slice(0, 200),
            left: Math.round(rect.left),
            top: Math.round(rect.top),
            width: Math.round(rect.width),
            height: Math.round(rect.height),
          };
        });
        const target = candidates[index];
        if (!target) {
          return false;
        }
        target.dispatchEvent(new MouseEvent("click", { bubbles: true, cancelable: true, view: window }));
        return true;
      }, tabIndex);
      if (clicked) {
        return;
      }
    } catch (error) {
      lastError = String(error && error.message ? error.message : error);
    }
    await page.waitForTimeout(250);
  }
  throw new Error(`Could not click tab index ${tabIndex}: ${lastError || "no clickable tab candidates"}`);
}

async function clickTab(page, text, tabIndex, timeoutMs) {
  if (text) {
    try {
      await clickText(page, text, Number.isInteger(tabIndex) ? Math.min(timeoutMs, 3000) : timeoutMs);
      return;
    } catch (error) {
      if (!Number.isInteger(tabIndex)) {
        throw error;
      }
    }
  }
  await clickTabByIndex(page, tabIndex, timeoutMs);
}

async function collectSummary(page, args, interaction, startedEpochMillis, finishedEpochMillis) {
  const browserSummary = await page.evaluate(
    ({ initialText, workText, returnText }) => {
      const nav = performance.getEntriesByType("navigation")[0];
      const resources = performance.getEntriesByType("resource");
      const probe = window.__tabSwitchProbe || {};
      const longTasks = Array.isArray(probe.longTasks) ? probe.longTasks : [];
      const bodyText = document.body && document.body.innerText ? document.body.innerText : "";
      const heap = performance.memory
        ? {
            usedJSHeapSize: performance.memory.usedJSHeapSize,
            totalJSHeapSize: performance.memory.totalJSHeapSize,
            jsHeapSizeLimit: performance.memory.jsHeapSizeLimit,
          }
        : null;
      return {
        elapsedBrowserMs: performance.now(),
        bodyTextSnippet: bodyText.slice(0, 4000),
        tabCandidates: Array.isArray(probe.tabCandidates) ? probe.tabCandidates : [],
        initialReadyTextMatched: initialText ? bodyText.indexOf(initialText) !== -1 : null,
        workReadyTextMatched: workText ? bodyText.indexOf(workText) !== -1 : null,
        returnReadyTextMatched: returnText ? bodyText.indexOf(returnText) !== -1 : null,
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
    { initialText: args.initialReadyText, workText: args.workReadyText, returnText: args.returnReadyText },
  );
  return {
    ok: interaction.ok,
    url: redactUrl(args.url, args.urlAlias),
    startedEpochMillis,
    finishedEpochMillis,
    elapsedWallMs: finishedEpochMillis - startedEpochMillis,
    viewport: parseViewport(args.viewport),
    browserName: "chromium",
    holdMs: args.holdMs,
    settleMs: args.settleMs,
    interaction,
    ...browserSummary,
  };
}

async function main() {
  const args = parseArgs(process.argv);
  if (args.help || !args.url || !args.outDir) {
    console.log(usage());
    process.exit(args.help ? 0 : 2);
  }

  const { chromium } = await importPlaywright();
  const consoleRows = [];
  const networkRows = [];
  const websocketRows = [];
  const browser = await chromium.launch({ headless: args.headless });
  const context = await browser.newContext({ viewport: parseViewport(args.viewport) });
  const page = await context.newPage();

  page.on("console", (message) => {
    consoleRows.push({ type: message.type(), text: message.text().slice(0, 2000), location: message.location(), timestampEpochMillis: Date.now() });
  });
  page.on("pageerror", (error) => {
    consoleRows.push({ type: "pageerror", text: String(error && error.message ? error.message : error).slice(0, 2000), timestampEpochMillis: Date.now() });
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
    const row = { url: redactUrl(socket.url(), args.urlAlias), openedEpochMillis: Date.now(), closedEpochMillis: null, framesSent: 0, framesReceived: 0, bytesSent: 0, bytesReceived: 0, errors: [] };
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
    window.__tabSwitchProbe = { longTasks: [], lcp: null };
    try {
      const longTaskObserver = new PerformanceObserver((list) => {
        for (const entry of list.getEntries()) {
          window.__tabSwitchProbe.longTasks.push({ startTime: entry.startTime, duration: entry.duration, name: entry.name });
        }
      });
      longTaskObserver.observe({ entryTypes: ["longtask"] });
    } catch (error) {
      window.__tabSwitchProbe.longTaskError = String(error && error.message ? error.message : error);
    }
    try {
      const lcpObserver = new PerformanceObserver((list) => {
        const entries = list.getEntries();
        const last = entries[entries.length - 1];
        if (last) {
          window.__tabSwitchProbe.lcp = { startTime: last.startTime, size: last.size || null, elementTag: last.element && last.element.tagName ? last.element.tagName : null };
        }
      });
      lcpObserver.observe({ type: "largest-contentful-paint", buffered: true });
    } catch (error) {
      window.__tabSwitchProbe.lcpError = String(error && error.message ? error.message : error);
    }
  });

  const startedEpochMillis = Date.now();
  const interaction = { ok: false, phases: [], error: null };
  try {
    await page.goto(args.url, { waitUntil: "domcontentloaded", timeout: args.timeoutMs });
    await waitForBodyText(page, args.initialReadyText, args.timeoutMs);
    interaction.phases.push({ phase: "initial-ready", epochMillis: Date.now() });
    if (args.settleMs > 0) {
      await page.waitForTimeout(args.settleMs);
    }
    await clickTab(page, args.workTabText, args.workTabIndex, args.timeoutMs);
    await waitForBodyText(page, args.workReadyText, args.timeoutMs);
    interaction.phases.push({ phase: "work-ready", epochMillis: Date.now() });
    if (args.settleMs > 0) {
      await page.waitForTimeout(args.settleMs);
    }
    await clickTab(page, args.controlTabText, args.controlTabIndex, args.timeoutMs);
    await waitForBodyText(page, args.returnReadyText || args.initialReadyText, args.timeoutMs);
    const holdStartedEpochMillis = Date.now();
    interaction.phases.push({ phase: "background-hold-start", epochMillis: holdStartedEpochMillis });
    if (args.markerPath) {
      await fs.mkdir(path.dirname(args.markerPath), { recursive: true });
      await fs.writeFile(args.markerPath, `${JSON.stringify({ ok: true, holdStartedEpochMillis }, null, 2)}\n`, "utf8");
    }
    await page.waitForTimeout(args.holdMs);
    interaction.phases.push({ phase: "background-hold-finish", epochMillis: Date.now() });
    interaction.ok = true;
  } catch (error) {
    interaction.error = String(error && error.message ? error.message : error).slice(0, 2000);
  }
  const finishedEpochMillis = Date.now();
  const summary = await collectSummary(page, args, interaction, startedEpochMillis, finishedEpochMillis);

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
