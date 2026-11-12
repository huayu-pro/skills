#!/usr/bin/env node
/* verify_motion.mjs — runtime probe for the ui-design motion components.
 *
 * Three-layer acceptance's middle layer. Requires Playwright + a Chromium-based
 * browser; if either is missing it exits 2 and says so (never silently passes).
 *
 * Usage:
 *   node scripts/verify_motion.mjs --component assets/motion/code/components/10-scroll-narrative
 *   PLAYWRIGHT_PATH=/path/to/playwright/index.mjs BROWSER_PATH=/usr/bin/microsoft-edge \
 *     node scripts/verify_motion.mjs --dir evals/motion
 */
import fs from "node:fs";
import http from "node:http";
import path from "node:path";
import { pathToFileURL } from "node:url";

const MIME = {
  ".html": "text/html; charset=utf-8",
  ".css": "text/css; charset=utf-8",
  ".js": "text/javascript; charset=utf-8",
  ".mjs": "text/javascript; charset=utf-8",
  ".json": "application/json; charset=utf-8",
  ".svg": "image/svg+xml",
  ".png": "image/png",
  ".jpg": "image/jpeg",
  ".jpeg": "image/jpeg",
  ".webp": "image/webp",
  ".mp4": "video/mp4",
  ".webm": "video/webm",
};

function parseArgs(argv) {
  if (argv.includes("--help") || argv.includes("-h")) {
    console.log("usage: verify_motion.mjs --component <dir> | --dir <parent> [--viewports 1280,375] [--json] [--timeout ms]");
    process.exit(0);
  }
  const args = { components: [], dirs: [], url: null, trace: false, viewports: [1280, 768, 375], json: false, timeout: 20000 };
  for (let i = 0; i < argv.length; i++) {
    const arg = argv[i];
    if (arg === "--component") args.components.push(argv[++i]);
    else if (arg === "--dir") args.dirs.push(argv[++i]);
    else if (arg === "--viewports") args.viewports = argv[++i].split(",").map(Number).filter(Boolean);
    else if (arg === "--url") args.url = argv[++i];
    else if (arg === "--trace") args.trace = true;
    else if (arg === "--profile") args.profile = argv[++i];
    else if (arg === "--throttle") args.throttle = true;
    else if (arg === "--json") args.json = true;
    else if (arg === "--timeout") args.timeout = Number(argv[++i]) || 20000;
  }
  return args;
}

async function loadPlaywright() {
  const candidates = [];
  if (process.env.PLAYWRIGHT_PATH) candidates.push(pathToFileURL(process.env.PLAYWRIGHT_PATH).href);
  candidates.push("playwright");
  candidates.push(pathToFileURL(path.join(process.cwd(), "node_modules", "playwright", "index.mjs")).href);
  for (const candidate of candidates) {
    try {
      return await import(candidate);
    } catch (error) {
      // try the next candidate
    }
  }
  return null;
}

function startServer(root) {
  return new Promise((resolve) => {
    const server = http.createServer((req, res) => {
      const urlPath = decodeURIComponent((req.url || "/").split("?")[0]);
      if (urlPath === "/favicon.ico") { res.writeHead(204); res.end(); return; }
      const safe = path.normalize(urlPath).replace(/^(\.\.(\/|\\|$))+/, "");
      let file = path.join(root, safe);
      if (!file.startsWith(root)) {
        res.writeHead(403); res.end("forbidden"); return;
      }
      if (fs.existsSync(file) && fs.statSync(file).isDirectory()) file = path.join(file, "index.html");
      if (!fs.existsSync(file)) {
        res.writeHead(404); res.end("not found"); return;
      }
      res.writeHead(200, { "content-type": MIME[path.extname(file)] || "application/octet-stream" });
      fs.createReadStream(file).pipe(res);
    });
    server.listen(0, "127.0.0.1", () => {
      const port = server.address().port;
      resolve({ server, base: "http://127.0.0.1:" + port, close: () => server.close() });
    });
  });
}

function browserPath() {
  if (process.env.BROWSER_PATH && fs.existsSync(process.env.BROWSER_PATH)) return process.env.BROWSER_PATH;
  return undefined;
}

async function snapshot(page) {
  return page.evaluate(() => {
    const animations = document.getAnimations().map((animation) => {
      const timing = animation.effect && animation.effect.getTiming ? animation.effect.getTiming() : {};
      return {
        duration: typeof timing.duration === "number" ? Math.round(timing.duration) : null,
        iterations: timing.iterations,
        easing: timing.easing || null,
        playState: animation.playState,
      };
    });
    const infinite = animations.filter((item) => item.iterations === Infinity).length;
    const stats = window.__rfStats ? JSON.parse(JSON.stringify(window.__rfStats)) : null;
    const motionBudget = {
      attention: document.querySelectorAll('[data-motion-role="attention"]').length,
      ambient: document.querySelectorAll('[data-motion-role="ambient"]').length,
      feedback: document.querySelectorAll('[data-motion-role="feedback"]').length,
      catalog: document.querySelectorAll('[data-motion-role="catalog"]').length,
      running: document.getAnimations().filter(a => a.playState === "running").length,
      profile: document.body.dataset.motion || document.documentElement.dataset.motion || "unknown",
      trace: Boolean(window.__motionTrace)
    };
    const focusables = Array.from(document.querySelectorAll(
      "a[href], button, input, select, textarea, [tabindex]:not([tabindex='-1'])"
    )).length;
    const bodyStyle = getComputedStyle(document.body);
    return {
      animations: animations,
      infinite: infinite,
      stats: stats,
      motionBudget: motionBudget,
      focusables: focusables,
      bodyVisibility: bodyStyle.visibility,
      bodyOpacity: bodyStyle.opacity,
      scrollY: window.scrollY,
      scrollHeight: document.documentElement.scrollHeight,
      scrollWidth: document.documentElement.scrollWidth,
      innerWidth: window.innerWidth,
      errors: window.__verifyErrors || [],
    };
  });
}

function sumFrames(stats) {
  if (!stats || typeof stats !== "object") return 0;
  let total = 0;
  for (const value of Object.values(stats)) {
    if (!value || typeof value !== "object") continue;
    if (typeof value.frames === "number") total += value.frames;
    if (typeof value.renders === "number") total += value.renders;
    if (typeof value.animations === "number") total += value.animations;
  }
  return total;
}

function hasRunningInfinite(animations) {
  return animations.some((item) => item.iterations === Infinity && item.playState === "running");
}

async function runOne(context, base, entry, viewports, timeout) {
  const page = await context.newPage();
  const consoleErrors = [];
  page.on("console", (message) => {
    if (message.type() === "error") consoleErrors.push(message.text());
  });
  page.on("pageerror", (error) => consoleErrors.push(String(error)));

  const result = { component: entry.name, viewports: {}, console_errors: [], overflow: {} };
  for (const width of viewports) {
    const height = width <= 480 ? 844 : 900;
    await page.setViewportSize({ width, height });
    await page.goto(base + "/" + entry.file, { waitUntil: "load", timeout: timeout });
    await page.waitForTimeout(900);
    const snap = await snapshot(page);
    result.viewports[String(width)] = snap;
    if (snap.scrollWidth > snap.innerWidth + 1) {
      result.overflow[String(width)] = { scrollWidth: snap.scrollWidth, innerWidth: snap.innerWidth };
      if (width === 375) {
        result.overflow_375 = { scrollWidth: snap.scrollWidth, innerWidth: snap.innerWidth };
      }
    }
  }

  // Interaction probe at 1280: wheel + drag + first button + keyboard.
  await page.setViewportSize({ width: 1280, height: 900 });
  await page.goto(base + "/" + entry.file, { waitUntil: "load", timeout: timeout });
  await page.waitForTimeout(700);
  const before = await snapshot(page);
  await page.mouse.move(640, 450);
  await page.mouse.wheel(0, 900);
  await page.mouse.down();
  await page.mouse.move(820, 450, { steps: 8 });
  await page.mouse.up();
  await page.evaluate(() => {
    const max = Math.max(0, document.documentElement.scrollHeight - window.innerHeight);
    window.scrollTo(0, Math.min(max, Math.round(window.innerHeight * 1.6)));
  });
  await page.waitForTimeout(400);
  const afterScroll = await snapshot(page);
  const buttons = page.locator("button");
  if (await buttons.count() > 0) {
    try { await buttons.first().click({ timeout: 800 }); } catch (error) { /* not fatal */ }
  }
  await page.keyboard.press("Tab");
  await page.keyboard.press("ArrowRight");
  await page.keyboard.press("ArrowRight");
  await page.waitForTimeout(500);
  const after = await snapshot(page);

  const beforeFrames = sumFrames(before.stats);
  const afterFrames = Math.max(sumFrames(afterScroll.stats), sumFrames(after.stats));
  const frameDelta = afterFrames - beforeFrames;
  const statsChanged =
    JSON.stringify(afterScroll.stats) !== JSON.stringify(before.stats) ||
    JSON.stringify(after.stats) !== JSON.stringify(before.stats);
  const animationDelta =
    Math.max(afterScroll.animations.length, after.animations.length) - before.animations.length;
  const beforeRunning = before.animations.some(
    (item) => item.playState === "running" && typeof item.duration === "number" && item.duration > 0
  );
  const hasMotion =
    beforeRunning ||
    frameDelta > 0 ||
    animationDelta > 0 ||
    statsChanged;
  result.interaction = {
    beforeFrames: beforeFrames,
    afterFrames: afterFrames,
    frameDelta: frameDelta,
    animationDelta: animationDelta,
    statsChanged: statsChanged,
    hasMotion: hasMotion,
    beforeStats: before.stats,
    afterScrollStats: afterScroll.stats,
    afterStats: after.stats,
    beforeScrollY: before.scrollY,
    afterScrollY: afterScroll.scrollY,
    scrollHeight: before.scrollHeight,
  };

  // Reduced motion: a fresh page so media emulation applies before load.
  const reducedErrors = [];
  const reducedPage = await context.newPage();
  reducedPage.on("console", (message) => {
    if (message.type() === "error") reducedErrors.push(message.text());
  });
  reducedPage.on("pageerror", (error) => reducedErrors.push(String(error)));
  await reducedPage.emulateMedia({ reducedMotion: "reduce" });
  await reducedPage.setViewportSize({ width: 1280, height: 900 });
  await reducedPage.goto(base + "/" + entry.file, { waitUntil: "load", timeout: timeout });
  await reducedPage.waitForTimeout(500);
  const reduced1 = await snapshot(reducedPage);
  await reducedPage.waitForTimeout(500);
  const reduced2 = await snapshot(reducedPage);
  const reducedProgress =
    hasRunningInfinite(reduced2.animations) ||
    reduced2.animations.some(
      (item) => item.playState === "running" && typeof item.duration === "number" && item.duration > 0
    ) ||
    sumFrames(reduced2.stats) > sumFrames(reduced1.stats);
  result.reduced = reduced2;

  // Keyboard: one Tab should leave the body if there are focusables.
  const focusables = result.viewports[String(viewports[0])].focusables;
  let tabMoved = null;
  if (focusables > 0) {
    await page.setViewportSize({ width: 1280, height: 900 });
    await page.goto(base + "/" + entry.file, { waitUntil: "load", timeout: timeout });
    await page.waitForTimeout(300);
    await page.keyboard.press("Tab");
    tabMoved = await page.evaluate(() => document.activeElement !== document.body);
  }
  result.keyboard_tab = tabMoved;

  const first = result.viewports[String(viewports[0])];
  const bodyVisible = first.bodyVisibility !== "hidden" && first.bodyOpacity !== "0";
  result.console_errors = consoleErrors.concat(reducedErrors);
  result.verified =
    result.console_errors.length === 0 &&
    Object.keys(result.overflow).length === 0 &&
    reduced2.infinite === 0 &&
    !reducedProgress &&
    bodyVisible &&
    hasMotion;
  result.notes = [];
  if (!hasMotion) result.notes.push("no observed motion (frames/animations/stats unchanged)");
  if (!bodyVisible) result.notes.push("body hidden or opacity 0");
  if (reducedProgress) result.notes.push("reduced-motion still progressing");
  if (first.stats === null) result.notes.push("no __rfStats (animations only)");

  await reducedPage.close();
  await page.close();
  return result;
}

function entriesFrom(componentDir) {
  const html = fs.readdirSync(componentDir).filter((name) => name.endsWith(".html"));
  if (html.includes("index.html")) return [{ name: path.basename(componentDir), file: "index.html" }];
  return html.map((name) => ({ name: path.basename(componentDir) + "/" + name, file: name }));
}

async function main() {
  const args = parseArgs(process.argv.slice(2));
  if (args.url) {
    const playwright = await loadPlaywright();
    if (!playwright || !playwright.chromium) {
      console.error("SKIP: playwright not available for --url");
      process.exit(2);
    }
    const browser = await playwright.chromium.launch({ headless: true, executablePath: browserPath(), args: ["--no-sandbox"] });
    const page = await browser.newPage({ viewport: { width: 1280, height: 900 } });
    await page.route("**/favicon.ico", route => route.fulfill({ status: 204, body: "" }));
    const errors = [];
    page.on("console", m => { if (m.type() === "error") errors.push(m.text()); });
    page.on("pageerror", e => errors.push(String(e)));
    let throttle = null;
    if (args.throttle) {
      const cdp = await page.context().newCDPSession(page);
      await cdp.send("Emulation.setCPUThrottlingRate", { rate: 4 });
      await cdp.send("Network.enable");
      await cdp.send("Network.emulateNetworkConditions", {
        offline: false, latency: 150,
        downloadThroughput: 1.6 * 1024 * 1024 / 8,
        uploadThroughput: 750 * 1024 / 8,
      });
      throttle = { cpuRate: 4, latencyMs: 150, profile: "Fast-3G-like" };
    }
    const views = args.viewports && args.viewports.length ? args.viewports : [1280, 375];
    const snapshots = {};
    for (const width of views) {
      const height = width <= 480 ? 844 : 900;
      await page.setViewportSize({ width, height });
      await page.goto(args.url, { waitUntil: "load", timeout: args.timeout });
      await page.waitForTimeout(700);
      snapshots[String(width)] = await snapshot(page);
    }
    // Restore desktop for trace/profile reporting.
    await page.setViewportSize({ width: 1280, height: 900 });
    await page.goto(args.url, { waitUntil: "load", timeout: args.timeout });
    await page.waitForTimeout(500);
    let trace = "skipped";
    if (args.trace) {
      await page.evaluate(() => {
        window.__motionTrace = [];
        const targets = Array.from(document.querySelectorAll('[data-motion-role], [data-motion], body')).slice(0, 12);
        const started = performance.now();
        const timer = setInterval(() => {
          const t = Math.round(performance.now() - started);
          const samples = targets.map(el => {
            const cs = getComputedStyle(el);
            return { role: el.dataset.motionRole || el.tagName.toLowerCase(), transform: cs.transform, opacity: cs.opacity };
          });
          window.__motionTrace.push({ t, samples });
          if (t >= 1000) clearInterval(timer);
        }, 16);
      });
      await page.waitForTimeout(1100);
      trace = await page.evaluate(() => window.__motionTrace || []);
    }
    const snap = await snapshot(page);
    const overflow = {};
    for (const [width, item] of Object.entries(snapshots)) {
      if (item.scrollWidth > item.innerWidth + 1) {
        overflow[width] = { scrollWidth: item.scrollWidth, innerWidth: item.innerWidth };
      }
    }
    const report = { mode: "url", url: args.url, profile: args.profile || snap.motionBudget.profile,
      throttle: throttle, trace: trace,
      console_errors: errors, viewports: snapshots, overflow: overflow, motionBudget: snap.motionBudget,
      verified: errors.length === 0 && Object.keys(overflow).length === 0,
      accepted: false, notes: ["compliance only; quality and appropriateness require human review", "trace is sampled computed style, not a quality verdict"] };
    if (args.json) console.log(JSON.stringify(report, null, 2)); else console.log(JSON.stringify(report, null, 2));
    await browser.close();
    process.exit(report.verified ? 0 : 1);
  }
  if (!args.components.length && !args.dirs.length) {
    console.error("usage: --component <dir> | --dir <parent-dir> | --url <page>");
    process.exit(2);
  }
  const playwright = await loadPlaywright();
  if (!playwright || !playwright.chromium) {
    console.error("SKIP: playwright not available. Set PLAYWRIGHT_PATH to playwright/index.mjs.");
    process.exit(2);
  }

  const jobs = [];
  for (const dir of args.components) {
    const root = path.resolve(dir);
    const entries = entriesFrom(root);
    if (!entries.length) {
      console.error("no html entries under " + root);
      process.exit(2);
    }
    jobs.push({ root: root, entries: entries });
  }
  for (const parent of args.dirs) {
    const base = path.resolve(parent);
    for (const name of fs.readdirSync(base)) {
      const dir = path.join(base, name);
      if (fs.statSync(dir).isDirectory() && fs.readdirSync(dir).some((f) => f.endsWith(".html"))) {
        const entries = entriesFrom(dir);
        if (entries.length) jobs.push({ root: dir, entries: entries });
      }
    }
  }
  if (!jobs.length) {
    console.error("no html entries found");
    process.exit(2);
  }

  const browser = await playwright.chromium.launch({
    headless: true,
    executablePath: browserPath(),
    args: ["--no-sandbox", "--autoplay-policy=no-user-gesture-required"],
  });

  const results = [];
  for (const job of jobs) {
    const server = await startServer(job.root);
    const context = await browser.newContext({ viewport: { width: 1280, height: 900 } });
    try {
      for (const entry of job.entries) {
        const result = await runOne(context, server.base, entry, args.viewports, args.timeout);
        results.push(result);
      }
    } finally {
      await context.close();
      server.close();
    }
  }

  await browser.close();
  const passed = results.filter((item) => item.verified).length;
  const report = { total: results.length, passed: passed, results: results };
  if (args.json) {
    console.log(JSON.stringify(report, null, 2));
  } else {
    for (const item of results) {
      console.log(
        (item.verified ? "PASS " : "FAIL ") + item.component +
        "  console=" + item.console_errors.length +
        "  overflow375=" + Boolean(item.overflow_375) +
        "  reducedInfinite=" + item.reduced.infinite +
        (item.notes.length ? "  notes=" + item.notes.join(";") : "")
      );
    }
    console.log("verify_motion: " + passed + "/" + results.length);
  }
  process.exit(passed === results.length ? 0 : 1);
}

main().catch((error) => {
  console.error("verify_motion crashed:", error);
  process.exit(2);
});