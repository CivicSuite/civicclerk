import { mkdir, rm, writeFile } from "node:fs/promises";
import { existsSync } from "node:fs";
import { spawn, spawnSync } from "node:child_process";
import path from "node:path";
import { fileURLToPath } from "node:url";

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const frontendDir = path.join(root, "frontend");
const evidencePath = path.join(root, "docs", "browser-qa", "cc7-api-frontend-completeness-qa-2026-05-06.json");
const summaryPath = path.join(root, "docs", "screenshots", "cc7-api-frontend-completeness-summary.md");
const chromeUserDataDir = path.join(root, ".tmp-cc7-chrome-profile");
const vitePort = 4177;
const chromePort = 9237;
const baseUrl = `http://127.0.0.1:${vitePort}`;
const chromePath = "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe";

const pages = [
  "staff-dashboard",
  "meeting-calendar",
  "meeting-detail",
  "agenda-builder",
  "agenda-intake",
  "staff-report-editor",
  "packet-builder",
  "notice-checklist",
  "live-meeting-capture",
  "minutes-review",
  "motions-votes-actions",
  "transcript-management",
  "public-comment-review",
  "closed-session-workspace",
  "archive-search",
  "public-calendar",
  "public-detail",
  "admin-settings",
  "prompt-library-admin",
  "connector-import-admin",
];
const states = ["loading", "success", "empty", "error", "partial"];
const viewports = {
  desktop: { width: 1440, height: 1100, deviceScaleFactor: 1, mobile: false },
  mobile: { width: 390, height: 1100, deviceScaleFactor: 1, mobile: true },
};

class CdpClient {
  constructor(wsUrl) {
    this.ws = new WebSocket(wsUrl);
    this.nextId = 1;
    this.pending = new Map();
    this.consoleErrors = [];
    this.exceptions = [];
    this.ws.addEventListener("message", (event) => {
      const message = JSON.parse(event.data);
      if (message.id && this.pending.has(message.id)) {
        const { resolve, reject } = this.pending.get(message.id);
        this.pending.delete(message.id);
        if (message.error) {
          reject(new Error(message.error.message));
        } else {
          resolve(message.result ?? {});
        }
        return;
      }
      if (message.method === "Runtime.consoleAPICalled" && message.params?.type === "error") {
        this.consoleErrors.push(message.params.args?.map((arg) => arg.value || arg.description || "").join(" ") || "console.error");
      }
      if (message.method === "Runtime.exceptionThrown") {
        this.exceptions.push(message.params.exceptionDetails?.text || "runtime exception");
      }
    });
  }

  async ready() {
    if (this.ws.readyState === WebSocket.OPEN) {
      return;
    }
    await new Promise((resolve, reject) => {
      this.ws.addEventListener("open", resolve, { once: true });
      this.ws.addEventListener("error", reject, { once: true });
    });
  }

  send(method, params = {}) {
    const id = this.nextId++;
    const message = { id, method, params };
    const promise = new Promise((resolve, reject) => {
      this.pending.set(id, { resolve, reject });
    });
    this.ws.send(JSON.stringify(message));
    return promise;
  }

  close() {
    this.ws.close();
  }
}

function sleep(ms) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

async function waitForUrl(url, timeoutMs = 20_000) {
  const started = Date.now();
  while (Date.now() - started < timeoutMs) {
    try {
      const response = await fetch(url);
      if (response.ok) {
        return response;
      }
    } catch {
      // keep waiting
    }
    await sleep(200);
  }
  throw new Error(`Timed out waiting for ${url}`);
}

function spawnProcess(command, args, options = {}) {
  const child = spawn(command, args, {
    stdio: ["ignore", "pipe", "pipe"],
    windowsHide: true,
    ...options,
  });
  child.stdout.on("data", () => undefined);
  child.stderr.on("data", () => undefined);
  return child;
}

function killProcessTree(child) {
  if (!child || !child.pid) {
    return;
  }
  if (process.platform === "win32") {
    spawnSync("taskkill", ["/PID", String(child.pid), "/T", "/F"], { stdio: "ignore", windowsHide: true });
    return;
  }
  child.kill("SIGTERM");
}

async function newPageWsUrl(url) {
  const response = await fetch(`http://127.0.0.1:${chromePort}/json/new?${encodeURIComponent(url)}`, {
    method: "PUT",
  });
  if (!response.ok) {
    throw new Error(`Chrome target creation failed: ${response.status}`);
  }
  const payload = await response.json();
  return { wsUrl: payload.webSocketDebuggerUrl, targetId: payload.id };
}

async function closeTarget(targetId) {
  try {
    await fetch(`http://127.0.0.1:${chromePort}/json/close/${targetId}`);
  } catch {
    // Best effort; Chrome will be killed after the run.
  }
}

async function runCase(page, state, viewportName, viewport) {
  const url = `${baseUrl}/?page=${page}&state=${state}&source=demo`;
  const { wsUrl, targetId } = await newPageWsUrl("about:blank");
  const cdp = new CdpClient(wsUrl);
  await cdp.ready();
  await cdp.send("Runtime.enable");
  await cdp.send("Page.enable");
  await cdp.send("DOM.enable");
  await cdp.send("Emulation.setDeviceMetricsOverride", viewport);
  const loaded = new Promise((resolve) => {
    const listener = (event) => {
      const message = JSON.parse(event.data);
      if (message.method === "Page.loadEventFired") {
        cdp.ws.removeEventListener("message", listener);
        resolve();
      }
    };
    cdp.ws.addEventListener("message", listener);
  });
  await cdp.send("Page.navigate", { url });
  await Promise.race([loaded, sleep(5000)]);
  await sleep(250);
  await cdp.send("Input.dispatchKeyEvent", {
    type: "keyDown",
    key: "Tab",
    code: "Tab",
    windowsVirtualKeyCode: 9,
    nativeVirtualKeyCode: 9,
  });
  await cdp.send("Input.dispatchKeyEvent", {
    type: "keyUp",
    key: "Tab",
    code: "Tab",
    windowsVirtualKeyCode: 9,
    nativeVirtualKeyCode: 9,
  });
  await sleep(80);
  const evaluation = await cdp.send("Runtime.evaluate", {
    returnByValue: true,
    expression: `(() => {
      function parseRgb(value) {
        const match = String(value).match(/rgba?\\(([^)]+)\\)/);
        if (!match) return null;
        const parts = match[1].split(",").map((part) => Number.parseFloat(part.trim()));
        return { r: parts[0], g: parts[1], b: parts[2], a: parts.length > 3 ? parts[3] : 1 };
      }
      function luminance(rgb) {
        const channel = [rgb.r, rgb.g, rgb.b].map((value) => {
          const scaled = value / 255;
          return scaled <= 0.03928 ? scaled / 12.92 : Math.pow((scaled + 0.055) / 1.055, 2.4);
        });
        return 0.2126 * channel[0] + 0.7152 * channel[1] + 0.0722 * channel[2];
      }
      function contrast(foreground, background) {
        const l1 = luminance(foreground);
        const l2 = luminance(background);
        return (Math.max(l1, l2) + 0.05) / (Math.min(l1, l2) + 0.05);
      }
      function backgroundFor(element) {
        let node = element;
        while (node && node !== document.documentElement) {
          const bg = parseRgb(getComputedStyle(node).backgroundColor);
          if (bg && bg.a > 0.95) return bg;
          node = node.parentElement;
        }
        const bodyBackground = parseRgb(getComputedStyle(document.body).backgroundColor);
        return bodyBackground && bodyBackground.a > 0.95 ? bodyBackground : { r: 247, g: 243, b: 234, a: 1 };
      }
      const candidates = Array.from(document.querySelectorAll("h1,h2,h3,p,button,li,code"))
        .filter((element) => {
          const rect = element.getBoundingClientRect();
          return rect.width > 0
            && rect.height > 0
            && String(element.textContent || "").trim().length > 0
            && !element.closest(".icon,.state-mark,.status");
        })
        .slice(0, 120);
      let minContrast = 21;
      let minContrastSample = null;
      for (const element of candidates) {
        const style = getComputedStyle(element);
        const foreground = parseRgb(style.color);
        const background = backgroundFor(element);
        if (foreground && background) {
          const ratio = contrast(foreground, background);
          if (ratio < minContrast) {
            minContrast = ratio;
            minContrastSample = {
              tag: element.tagName,
              className: element.className,
              text: String(element.textContent || "").trim().slice(0, 80),
              color: style.color,
              background: getComputedStyle(element).backgroundColor,
              inheritedBackground: "rgb(" + [background.r, background.g, background.b].join(", ") + ")",
            };
          }
        }
      }
      const main = document.querySelector("main");
      const active = document.activeElement;
      const activeStyle = active ? getComputedStyle(active) : null;
      const roleMessage = document.querySelector('[role="alert"],[role="status"]');
      const bodyText = document.body.innerText || "";
      const expectedState = new URL(location.href).searchParams.get("state");
      const expectedPage = new URL(location.href).searchParams.get("page");
      const currentPage = main?.getAttribute("data-current-page") || "";
      const stateCard = document.querySelector('.state-card.' + expectedState);
      const stateOk = expectedState === "success"
        ? bodyText.includes("QA states") && bodyText.length > 500
        : Boolean(roleMessage && stateCard && bodyText.length > 180);
      return {
        currentPage,
        semanticMain: Boolean(main),
        qaToolbar: bodyText.includes("QA states"),
        stateOk,
        missingText: stateOk ? [] : ["Expected page state copy was not visible"],
        keyboard: Boolean(active && active !== document.body),
        focus: active ? {
          tag: active.tagName,
          text: (active.textContent || active.getAttribute("aria-label") || "").trim().slice(0, 80),
          outlineStyle: activeStyle?.outlineStyle || "",
          outlineWidth: activeStyle?.outlineWidth || "",
        } : null,
        focusVisible: Boolean(activeStyle && activeStyle.outlineStyle !== "none" && activeStyle.outlineWidth !== "0px"),
        horizontalOverflow: document.documentElement.scrollWidth > window.innerWidth + 1 || document.body.scrollWidth > window.innerWidth + 1,
        minContrast: Number(minContrast.toFixed(2)),
        minContrastSample,
      };
    })()`,
  });
  const value = evaluation.result?.value ?? {};
  let screenshot = null;
  let bytes = 0;
  if (state === "success") {
    const screenshotName = `cc7-${page}-${viewportName}.png`;
    const screenshotPath = path.join(root, "docs", "screenshots", screenshotName);
    const capture = await cdp.send("Page.captureScreenshot", {
      format: "png",
      captureBeyondViewport: false,
    });
    const buffer = Buffer.from(capture.data, "base64");
    await writeFile(screenshotPath, buffer);
    screenshot = `docs/screenshots/${screenshotName}`;
    bytes = buffer.length;
  }
  cdp.close();
  await closeTarget(targetId);
  return {
    name: `${page}-${state}-${viewportName}`,
    page,
    state,
    viewport: viewportName,
    viewportSize: { width: viewport.width, height: viewport.height },
    screenshot,
    bytes,
    consoleErrors: cdp.consoleErrors.length,
    exceptions: cdp.exceptions.length,
    textCheck: value.currentPage === page && value.semanticMain && value.qaToolbar && value.stateOk,
    missingText: value.currentPage === page ? value.missingText : [`Expected page ${page}, saw ${value.currentPage || "none"}`],
    semanticMain: Boolean(value.semanticMain),
    keyboard: Boolean(value.keyboard),
    focus: value.focus,
    focusVisible: Boolean(value.focusVisible),
    horizontalOverflow: Boolean(value.horizontalOverflow),
    minContrast: value.minContrast || 0,
    minContrastSample: value.minContrastSample,
  };
}

function aggregate(cases) {
  return {
    consoleErrors: cases.reduce((total, item) => total + item.consoleErrors, 0),
    exceptions: cases.reduce((total, item) => total + item.exceptions, 0),
    textCheckFailures: cases.filter((item) => !item.textCheck).length,
    minContrast: Number(Math.min(...cases.map((item) => item.minContrast || 0)).toFixed(2)),
    keyboardFailures: cases.filter((item) => !item.keyboard).length,
    focusFailures: cases.filter((item) => !item.focusVisible).length,
    horizontalOverflowFailures: cases.filter((item) => item.horizontalOverflow).length,
  };
}

async function main() {
  if (!existsSync(chromePath)) {
    throw new Error(`Chrome not found at ${chromePath}`);
  }
  await mkdir(path.dirname(evidencePath), { recursive: true });
  await mkdir(path.dirname(summaryPath), { recursive: true });
  await rm(chromeUserDataDir, { recursive: true, force: true });
  const vite = spawnProcess("cmd.exe", ["/c", "npm", "run", "dev", "--", "--host", "127.0.0.1", "--port", String(vitePort)], {
    cwd: frontendDir,
  });
  const chrome = spawnProcess(chromePath, [
    "--headless=new",
    `--remote-debugging-port=${chromePort}`,
    `--user-data-dir=${chromeUserDataDir}`,
    "--disable-gpu",
    "--no-first-run",
    "--no-default-browser-check",
    "about:blank",
  ]);
  try {
    await waitForUrl(baseUrl);
    await waitForUrl(`http://127.0.0.1:${chromePort}/json/version`);
    const cases = [];
    for (const page of pages) {
      for (const state of states) {
        for (const [viewportName, viewport] of Object.entries(viewports)) {
          cases.push(await runCase(page, state, viewportName, viewport));
        }
      }
    }
    const totals = aggregate(cases);
    const evidence = {
      page: "frontend React CC-7 spec surfaces",
      reviewed_at: new Date().toISOString(),
      pages,
      states,
      viewports: Object.fromEntries(Object.entries(viewports).map(([name, viewport]) => [name, { width: viewport.width, height: viewport.height }])),
      cases,
      totals,
    };
    await writeFile(evidencePath, JSON.stringify(evidence, null, 2) + "\n", "utf8");
    await writeFile(summaryPath, [
      "# CC-7 API and Frontend Completeness Browser QA",
      "",
      "- Scope: 20 pages x 5 states x desktop/mobile.",
      `- Cases: ${cases.length}`,
      `- Console errors: ${totals.consoleErrors}`,
      `- Exceptions: ${totals.exceptions}`,
      `- Text check failures: ${totals.textCheckFailures}`,
      `- Keyboard failures: ${totals.keyboardFailures}`,
      `- Focus failures: ${totals.focusFailures}`,
      `- Horizontal overflow failures: ${totals.horizontalOverflowFailures}`,
      `- Minimum sampled contrast: ${totals.minContrast}`,
      "- Success screenshots: one desktop and one mobile screenshot for every CC-7 page.",
      "",
    ].join("\n"), "utf8");
    console.log(`CC7 browser QA cases: ${cases.length}`);
    console.log(`consoleErrors=${totals.consoleErrors} exceptions=${totals.exceptions} textFailures=${totals.textCheckFailures}`);
    console.log(`keyboardFailures=${totals.keyboardFailures} focusFailures=${totals.focusFailures} overflowFailures=${totals.horizontalOverflowFailures}`);
    console.log(`minContrast=${totals.minContrast}`);
  } finally {
    killProcessTree(chrome);
    killProcessTree(vite);
  }
}

main().then(() => {
  process.exit(0);
}).catch((error) => {
  console.error(error);
  process.exitCode = 1;
});
