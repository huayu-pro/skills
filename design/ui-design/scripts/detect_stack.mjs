#!/usr/bin/env node
/* detect_stack.mjs — v5.0 Step 0 runtime probe for a real project page.
 * Usage: node scripts/detect_stack.mjs --url http://localhost:3000/settings [--json]
 * No Playwright available: print a skipped report, never a fake success. */
import fs from "node:fs";
import path from "node:path";
import { pathToFileURL } from "node:url";

function parseArgs(argv) {
  const args = { url: null, json: false, timeout: 15000 };
  for (let i = 0; i < argv.length; i++) {
    if (argv[i] === "--url") args.url = argv[++i];
    else if (argv[i] === "--json") args.json = true;
    else if (argv[i] === "--timeout") args.timeout = Number(argv[++i]) || 15000;
  }
  return args;
}

async function loadPlaywright() {
  const candidates = [];
  if (process.env.PLAYWRIGHT_PATH) candidates.push(pathToFileURL(process.env.PLAYWRIGHT_PATH).href);
  candidates.push("playwright", pathToFileURL(path.join(process.cwd(), "node_modules", "playwright", "index.mjs")).href);
  for (const candidate of candidates) { try { return await import(candidate); } catch {} }
  return null;
}

async function main() {
  const args = parseArgs(process.argv.slice(2));
  if (!args.url) { console.error("usage: --url <page> [--json]"); process.exit(2); }
  const base = { url: args.url, detected: {}, confidence: {}, skipped: [], evidence: "runtime" };
  const playwright = await loadPlaywright();
  if (!playwright || !playwright.chromium) {
    base.skipped.push("no playwright/browser; use text heuristics and mark inferred");
    base.evidence = "skipped";
    if (args.json) console.log(JSON.stringify(base, null, 2)); else console.log(JSON.stringify(base, null, 2));
    return;
  }
  const browser = await playwright.chromium.launch({ headless: true, executablePath: process.env.BROWSER_PATH && fs.existsSync(process.env.BROWSER_PATH) ? process.env.BROWSER_PATH : undefined, args: ["--no-sandbox"] });
  const page = await browser.newPage({ viewport: { width: 1280, height: 900 } });
  await page.goto(args.url, { waitUntil: "load", timeout: args.timeout });
  const data = await page.evaluate(() => {
    const styles = Array.from(document.querySelectorAll("style")).map(n => n.textContent || "").join("\n");
    const vars = Array.from(new Set((styles + document.documentElement.outerHTML).match(/--[\w-]+\s*:/g) || [])).slice(0, 80);
    const scripts = Array.from(document.scripts).map(s => s.src).filter(Boolean);
    return {
      title: document.title,
      framework: document.querySelector("[data-reactroot],[data-reactid],#__next,#root") ? "react-like" : (window.__VUE__ ? "vue-like" : "unknown"),
      tailwind: styles.includes("@theme") ? "v4-css" : (document.documentElement.outerHTML.includes("tailwind") ? "v3-heuristic" : "unknown"),
      cssVariables: vars,
      darkMode: matchMedia("(prefers-color-scheme: dark)").matches,
      reducedMotion: matchMedia("(prefers-reduced-motion: reduce)").matches,
      animationApis: { viewTimeline: "animationTimeline" in document.documentElement.style, startingStyle: CSS.supports("selector(:has(*))"), viewTransitions: "startViewTransition" in document },
      externalScripts: scripts,
      hydrationBoundary: document.querySelectorAll("[data-server-rendered],[data-hydrated],#__NEXT_DATA__").length,
      rscBoundary: document.querySelectorAll("script[self\\:i]").length,
      monorepoHint: location.pathname.split("/").filter(Boolean).slice(0, 2),
      cssInJs: styles.length > 0 && /(?:css|emotion|styled)/i.test(styles)
    };
  });
  base.detected = data;
  base.confidence = Object.fromEntries(Object.keys(data).map(k => [k, typeof data[k] === "string" && data[k] === "unknown" ? "low" : "observed"]));
  base.skipped.push("package.json/theme source files not inspected; run text scan in project root");
  if (args.json || !args.json) console.log(JSON.stringify(base, null, 2));
  await browser.close();
}
main().catch(e => { console.error("detect_stack crashed:", e.message); process.exit(2); });
