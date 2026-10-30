#!/usr/bin/env node
/**
 * render.mjs — 把 deck.html 的每一页截成 PNG
 *
 *   node scripts/render.mjs deck.html --out preview --scale 2
 *
 * 输出 preview/slide-01.png …，并打印每页尺寸。
 * 这一步只证明"浏览器里长什么样"，不代表 PPTX 里不溢出——后者靠 validate。
 */
import fs from 'node:fs';
import path from 'node:path';
import { spawnSync } from 'node:child_process';
import { launchBrowser, openDeck } from './lib/browser.mjs';

function parseArgs(argv) {
  const a = { _: [] };
  for (let i = 0; i < argv.length; i++) {
    const t = argv[i];
    if (t.startsWith('--')) {
      const k = t.slice(2);
      const v = argv[i + 1] && !argv[i + 1].startsWith('--') ? argv[++i] : true;
      a[k] = v;
    } else a._.push(t);
  }
  return a;
}

const args = parseArgs(process.argv.slice(2));
const html = args._[0];
if (!html) {
  console.error('用法: node scripts/render.mjs <deck.html> [--out preview] [--scale 2]');
  process.exit(1);
}
const outDir = path.resolve(args.out || path.join(path.dirname(html), 'preview'));
const scale = Number(args.scale || 2);
fs.mkdirSync(outDir, { recursive: true });

const { browser, page } = await launchBrowser({ scale });
try {
  await openDeck(page, html);
  const count = await page.locator('section.slide').count();
  if (!count) throw new Error('没有找到 section.slide');

  for (let i = 0; i < count; i++) {
    const el = page.locator('section.slide').nth(i);
    const name = String(i + 1).padStart(2, '0');
    const file = path.join(outDir, `slide-${name}.png`);
    await el.screenshot({ path: file });
    const box = await el.boundingBox();
    console.log(`slide-${name}.png  ${Math.round(box.width)}×${Math.round(box.height)}`);
  }
  // 联系表：一眼看完整份，查节奏和重复版式（借自 pptx-skill 的 thumbnail.py）
  if (args.sheet) {
    const files = Array.from({ length: count }, (_, i) =>
      path.join(outDir, `slide-${String(i + 1).padStart(2, '0')}.png`));
    const sheet = path.join(outDir, 'contact-sheet.png');
    const r = spawnSync('montage', [
      ...files,
      '-tile', String(args.cols || 4) + 'x',
      '-geometry', '440x248+8+8',
      '-background', '#151515',
      '-label', '%f',
      '-pointsize', '16',
      '-fill', '#cccccc',
      sheet,
    ], { encoding: 'utf8' });
    if (r.status === 0) console.log(`联系表 → ${sheet}`);
    else {
      // 联系表是交付 gate 之一，失败不能只是印个 ⚠ 就 exit 0
      console.error('✖ 联系表生成失败（需要 ImageMagick 的 montage）');
      console.error('  apt install imagemagick / brew install imagemagick，或去掉 --sheet');
      process.exitCode = 1;
    }
  }

  console.log(`\n${count} 页 → ${outDir}`);
} finally {
  await browser.close();
}
