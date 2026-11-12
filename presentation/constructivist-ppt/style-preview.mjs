#!/usr/bin/env node
/**
 * style-preview.mjs — 开工前给用户选风格用的对照图
 *
 *   node scripts/style-preview.mjs [deck.html] [--out dir] [--themes archive,signal,c1,c4] [--pages 1,3,9]
 *
 * 把同一批页面分别套上每套主题，截图后拼成一张对照图。
 * 用户说不清"要哪种构成主义"时，给他看图，比让他读三行文字描述有效得多。
 *
 * 不传 deck.html 时用 assets/template.html（三页：封面 / 四栏 / 结尾）。
 */
import fs from 'node:fs';
import path from 'node:path';
import { spawnSync } from 'node:child_process';
import { fileURLToPath } from 'node:url';
import { launchBrowser, openDeck } from './lib/browser.mjs';

const here = path.dirname(fileURLToPath(import.meta.url));
const args = process.argv.slice(2);
const getArg = (k, d) => {
  const i = args.indexOf(`--${k}`);
  return i > -1 && args[i + 1] ? args[i + 1] : d;
};
// 取位置参数时要跳过"标志位的值"，否则 `--out /tmp/x` 会把 /tmp/x 当成交付文件
const WITH_VALUE = new Set(['--out', '--themes', '--pages']);
const positional = [];
for (let i = 0; i < args.length; i++) {
  if (WITH_VALUE.has(args[i])) { i++; continue; }
  if (!args[i].startsWith('-')) positional.push(args[i]);
}

const deck = path.resolve(positional[0] || path.join(here, '../assets/template.html'));
const outDir = path.resolve(getArg('out', path.join(path.dirname(deck), 'style-preview')));
// 默认覆盖全部主题：早先只默认 archive/signal/c1/c4，新增主题永远进不了对照图，
// 而 SKILL.md 又让用户「先看对照图再选子风格」——图里没有就等于没有这个选项。
const THEMES_CAT = JSON.parse(fs.readFileSync(path.join(here, '../assets/themes.json'), 'utf8'));
const defaultThemes = Object.keys(THEMES_CAT.themes).map((id) => id.replace(/^theme-/, '')).join(',');
const themes = getArg('themes', defaultThemes).split(',').map((s) => s.trim()).filter(Boolean);
const pagesArg = getArg('pages', '');
fs.mkdirSync(outDir, { recursive: true });

const { browser, page } = await launchBrowser({ scale: 1 });
const shots = [];
try {
  await openDeck(page, deck);
  const total = await page.locator('section.slide').count();
  const pages = pagesArg
    ? pagesArg.split(',').map((n) => parseInt(n, 10)).filter((n) => n >= 1 && n <= total)
    : Array.from({ length: Math.min(3, total) }, (_, i) => i + 1);

  for (const theme of themes) {
    // 把每一页的 theme-* 类换掉，其余类（slide--ink 等）保留
    await page.evaluate((t) => {
      document.querySelectorAll('section.slide').forEach((s) => {
        const keep = [...s.classList].filter((c) => !c.startsWith('theme-'));
        s.className = [...keep, `theme-${t}`].join(' ');
      });
    }, theme);

    for (const p of pages) {
      const file = path.join(outDir, `${theme}-p${String(p).padStart(2, '0')}.png`);
      await page.locator('section.slide').nth(p - 1).screenshot({ path: file });
      shots.push(file);
    }
  }
} finally {
  await browser.close();
}

const sheet = path.join(outDir, 'themes.png');
const r = spawnSync('montage', [
  ...shots,
  '-tile', `${pagesArg ? pagesArg.split(',').length : Math.min(3, 99)}x`,
  '-geometry', '480x270+10+10',
  '-background', '#151515',
  '-label', '%f',
  '-pointsize', '14',
  '-fill', '#cccccc',
  sheet,
], { encoding: 'utf8' });

console.log(`\n${themes.length} 套主题 × ${shots.length / themes.length} 页 → ${outDir}`);
console.log(`  ${themes.map((t) => `theme-${t}`).join('  ·  ')}`);
if (r.status === 0) console.log(`\n对照图：${sheet}`);
else console.log('\n⚠ 拼图失败（需要 ImageMagick 的 montage），单张图仍在目录里');
