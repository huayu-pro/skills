#!/usr/bin/env node
/**
 * doctor.mjs — 运行环境体检
 *
 *   node scripts/doctor.mjs [--json] [--require-lo]
 *
 * 必需：Node ≥20、pptxgenjs、Chromium、montage、unzip、pdftoppm。
 * 可选：LibreOffice（--require-lo 时变成必需）、CJK 字体。
 * 退出码：0 必需项齐全 / 2 缺必需项。
 */
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import { createRequire } from 'node:module';
import { spawnSync } from 'node:child_process';
import { launchBrowser } from './lib/browser.mjs';

const require = createRequire(import.meta.url);
const JSON_OUT = process.argv.includes('--json');
const REQUIRE_LO = process.argv.includes('--require-lo');

const which = (cmd) => {
  const r = spawnSync('sh', ['-c', `command -v ${cmd}`], { encoding: 'utf8' });
  return (r.stdout || '').trim() || null;
};

const checks = [];
const add = (id, label, ok, detail, required = true) => {
  checks.push({ id, label, ok: !!ok, detail: detail || '', required });
};

const nodeMajor = parseInt(process.versions.node.split('.')[0], 10);
add('node', `Node ${process.versions.node}`, nodeMajor >= 20, '需要 ≥20', true);

for (const dep of ['pptxgenjs', 'jszip']) {
  let ok = false;
  let detail = '';
  try {
    const p = require.resolve(dep);
    ok = true;
    detail = p;
  } catch (err) {
    detail = err.message;
  }
  add(dep, dep, ok, detail, true);
}

let chromiumOk = false;
let chromiumDetail = '';
try {
  const { browser, executablePath } = await launchBrowser({ scale: 1 });
  chromiumOk = true;
  chromiumDetail = executablePath;
  await browser.close();
} catch (err) {
  chromiumDetail = err.message.split('\n')[0];
}
add('chromium', 'Chromium (playwright-core)', chromiumOk, chromiumDetail, true);

for (const cmd of ['montage', 'unzip', 'pdftoppm']) {
  const p = which(cmd);
  add(cmd, cmd, !!p, p || `未找到 ${cmd}`, true);
}

const soffice = [
  process.env.CST_SOFFICE,
  path.join(os.homedir(), 'opt/lo-deb/soffice'),
  path.join(os.homedir(), 'opt/libreoffice/squashfs-root/AppRun'),
  '/usr/bin/soffice',
  '/usr/bin/libreoffice',
].filter(Boolean).find((p) => { try { return fs.existsSync(p); } catch { return false; } });
add('libreoffice', 'LibreOffice (可选)', !!soffice, soffice || '未安装；verify-render 会标 skipped', REQUIRE_LO);

const fc = spawnSync('fc-list', [':lang=zh', 'family'], { encoding: 'utf8' });
const fonts = (fc.stdout || '').split('\n').map((s) => s.trim()).filter(Boolean);
const hasCJK = fonts.some((f) => /Noto Sans CJK SC|Source Han Sans SC|微软雅黑|Microsoft YaHei/i.test(f));
add('cjk-font', '中文字体', hasCJK, hasCJK ? fonts.slice(0, 3).join(' / ') : '没找到 Noto Sans CJK / 思源黑体；预览会回退', false);

const requiredBad = checks.filter((c) => c.required && !c.ok);
if (JSON_OUT) {
  console.log(JSON.stringify({ ok: requiredBad.length === 0, checks }, null, 2));
} else {
  console.log('\n运行环境体检\n');
  for (const c of checks) {
    console.log(`  ${c.ok ? '✓' : c.required ? '✖' : '△'} ${c.label.padEnd(28)} ${c.detail}`);
  }
  console.log(requiredBad.length
    ? `\n✖ ${requiredBad.length} 个必需项缺失。先修环境，再谈交付。\n`
    : '\n必需项齐全。\n');
}
process.exit(requiredBad.length ? 2 : 0);
