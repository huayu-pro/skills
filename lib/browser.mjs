/**
 * browser.mjs — 定位并启动 headless chromium
 *
 * 依赖 playwright-core。解析顺序：
 *   1. 环境变量 CST_CHROME（显式指定可执行文件）
 *   2. 本 skill 的 node_modules/playwright-core
 *   3. WorkBuddy 托管 workspace 的 node_modules/playwright-core
 *   4. 任意能找到的系统 chromium / chrome
 */
import fs from 'node:fs';
import path from 'node:path';
import { createRequire } from 'node:module';
import os from 'node:os';

const HOME = os.homedir();

function firstExisting(paths) {
  for (const p of paths) {
    try {
      if (fs.existsSync(p)) return p;
    } catch {}
  }
  return null;
}

function findPlaywright() {
  const here = path.dirname(new URL(import.meta.url).pathname);
  const candidates = [
    path.resolve(here, '../../node_modules/playwright-core'),
    path.join(HOME, '.workbuddy/binaries/node/workspace/node_modules/playwright-core'),
    path.join(HOME, '.workbuddy/binaries/node/versions'),
  ];
  for (const c of candidates) {
    if (fs.existsSync(path.join(c, 'index.js')) || fs.existsSync(path.join(c, 'package.json'))) {
      try {
        return createRequire(import.meta.url)(c);
      } catch {}
    }
  }
  try {
    return createRequire(import.meta.url)('playwright-core');
  } catch {
    return null;
  }
}

function findChromium() {
  if (process.env.CST_CHROME && fs.existsSync(process.env.CST_CHROME)) return process.env.CST_CHROME;

  const pwRoots = [
    path.join(HOME, '.cache/ms-playwright'),
    path.join(HOME, '.workbuddy/.cache/ms-playwright'),
    path.join(HOME, 'Library/Caches/ms-playwright'),
    path.join(HOME, 'AppData/Local/ms-playwright'),
  ];
  const out = [];
  for (const root of pwRoots) {
    let dirs = [];
    try {
      dirs = fs.readdirSync(root).filter((d) => d.startsWith('chromium-'));
    } catch {
      continue;
    }
    for (const d of dirs.sort().reverse()) {
      out.push(
        path.join(root, d, 'chrome-linux64/chrome'),
        path.join(root, d, 'chrome-linux/chrome'),
        path.join(root, d, 'chrome-mac/Chromium.app/Contents/MacOS/Chromium'),
        path.join(root, d, 'chrome-win/chrome.exe'),
      );
    }
  }
  out.push(
    '/usr/bin/chromium',
    '/usr/bin/chromium-browser',
    '/usr/bin/google-chrome',
    '/opt/google/chrome/chrome',
    '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome',
  );
  return firstExisting(out);
}

export async function launchBrowser({ width = 1280, height = 720, scale = 1 } = {}) {
  const pw = findPlaywright();
  if (!pw) {
    throw new Error(
      '找不到 playwright-core。请运行：\n' +
        '  cd <skill>/scripts && npm install\n' +
        '或安装到 WorkBuddy 托管 workspace。',
    );
  }
  const exe = findChromium();
  if (!exe) {
    throw new Error(
      '找不到 chromium 可执行文件。设置环境变量 CST_CHROME 指向它，或运行：\n' +
        '  npx playwright install chromium',
    );
  }
  const browser = await pw.chromium.launch({
    executablePath: exe,
    args: ['--no-sandbox', '--disable-dev-shm-usage', '--font-render-hinting=none', '--force-color-profile=srgb'],
  });
  const context = await browser.newContext({
    viewport: { width, height },
    deviceScaleFactor: scale,
    colorScheme: 'light',
  });
  const page = await context.newPage();
  return { browser, context, page, executablePath: exe };
}

/** 把 HTML 以 file:// 打开，等字体与图片就绪。 */
export async function openDeck(page, htmlPath) {
  const url = 'file://' + path.resolve(htmlPath);
  await page.goto(url, { waitUntil: 'load', timeout: 60000 });
  await page.evaluate(async () => {
    await document.fonts.ready;
    await Promise.all(
      Array.from(document.images)
        .filter((img) => !img.complete)
        .map((img) => new Promise((res) => {
          img.onload = res;
          img.onerror = res;
        })),
    );
  });
  // 抹掉任何用于屏幕预览的缩放，只保证 .slide 自身是 1280×720 的原始坐标系
  await page.addStyleTag({
    content: `
      html, body { margin:0 !important; padding:0 !important; background:#fff !important; }
      .deck { transform:none !important; zoom:1 !important; }
      .slide { transform:none !important; zoom:1 !important; }
      .slide { margin:0 !important; }
    `,
  });
}
