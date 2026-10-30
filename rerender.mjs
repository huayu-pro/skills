#!/usr/bin/env node
/**
 * rerender.mjs — 用 deck-spec 在浏览器里重画一遍，验证"提取"没有走样
 *
 *   node scripts/rerender.mjs deck.spec.json --out preview-rerender [--font-profile office]
 *
 * 为什么要这一步：这台机器没有 LibreOffice，无法把 pptx 渲成图。
 * 重画页严格按 spec 的坐标/字号/行距摆放，等于把 PPTX 里会发生的事先画一遍；
 * 和原始截图像素比对，就能判断是"提取错了"还是"设计本来如此"。
 */
import fs from 'node:fs';
import path from 'node:path';
import { launchBrowser } from './lib/browser.mjs';
import { px2pt } from './lib/units.mjs';

function parseArgs(argv) {
  const a = { _: [] };
  for (let i = 0; i < argv.length; i++) {
    const t = argv[i];
    if (t.startsWith('-') && t !== '-') {
      const v = argv[i + 1] && !argv[i + 1].startsWith('-') ? argv[++i] : true;
      a[t.replace(/^--?/, '')] = v;
    } else a._.push(t);
  }
  return a;
}

const args = parseArgs(process.argv.slice(2));
const specPath = args._[0];
if (!specPath) {
  console.error('用法: node scripts/rerender.mjs <deck.spec.json> [--out dir] [--font-profile office]');
  process.exit(1);
}
const outDir = path.resolve(args.out || path.join(path.dirname(specPath), 'rerender'));
fs.mkdirSync(outDir, { recursive: true });

const spec = JSON.parse(fs.readFileSync(specPath, 'utf8'));
const FONTS = {
  // 注意：字体栈必须用单引号，否则会撞坏 HTML 属性的双引号
  office: {
    cjk: "微软雅黑, 'Noto Sans CJK SC', sans-serif",
    narrow: "'Arial Narrow', 'Liberation Sans Narrow', sans-serif",
    mono: "Consolas, 'DejaVu Sans Mono', monospace",
    latin: "Arial, sans-serif",
  },
  source: {
    cjk: "'思源黑体 CN', 'Noto Sans CJK SC', sans-serif",
    narrow: "'Arial Narrow', 'Liberation Sans Narrow', sans-serif",
    mono: "Consolas, 'DejaVu Sans Mono', monospace",
    latin: "Arial, sans-serif",
  },
  asis: null,
};
const profile = args['font-profile'] || 'office';
const F = FONTS[profile];

const esc = (s) => String(s).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');

function fontFor(run) {
  if (!F) return `'${run.family}', sans-serif`;
  if (/Mono|Consolas|Courier/i.test(run.stack || '')) return F.mono;
  if (/Narrow/i.test(run.stack || '')) return F.narrow;
  if (/CJK|Han Sans|YaHei|PingFang|Heiti/i.test(run.stack || '')) return F.cjk;
  return F.latin;
}

function shapeHtml(sh) {
  if (sh.kind === 'rect' || sh.kind === 'ellipse' || sh.kind === 'poly') {
    const st = [
      `left:${sh.x}px`, `top:${sh.y}px`, `width:${sh.w}px`, `height:${sh.h}px`,
      `background:${sh.fill ? '#' + sh.fill : 'transparent'}`,
      sh.rotate ? `transform:rotate(${sh.rotate}deg)` : '',
      sh.kind === 'ellipse' ? 'border-radius:50%' : '',
      sh.kind === 'poly' ? `clip-path:polygon(${sh.points.map((p) => `${p.x}px ${p.y}px`).join(',')})` : '',
      sh.outline ? `border:${sh.outline.width}px solid #${sh.outline.color}` : '',
    ].filter(Boolean).join(';');
    return `<div style="position:absolute;${st}"></div>`;
  }
  if (sh.kind === 'image') {
    const src = 'file://' + sh.src;
    return `<img src="${src}" style="position:absolute;left:${sh.x}px;top:${sh.y}px;width:${sh.w}px;height:${sh.h}px;object-fit:cover;${sh.rotate ? `transform:rotate(${sh.rotate}deg);` : ''}">`;
  }
  if (sh.kind === 'text') {
    const paras = sh.paragraphs.map((p) => {
      const inner = p.runs.map((r) => {
        const st = [
          `font-family:${fontFor(r)}`,
          `font-size:${r.size}px`,
          `font-weight:${r.weight}`,
          `color:#${r.color}`,
          r.italic ? 'font-style:italic' : '',
          r.letterSpacing ? `letter-spacing:${r.letterSpacing}px` : '',
        ].filter(Boolean).join(';');
        return `<span style="${st}">${esc(r.text)}</span>`;
      }).join('');
      return `<div style="text-align:${p.align}">${inner}</div>`;
    }).join('');
    const st = [
      `left:${sh.x}px`, `top:${sh.y}px`,
      sh.vertical ? `height:${sh.h}px` : `width:${sh.w}px`,
      `line-height:${sh.lineHeight}px`,
      `white-space:${sh.wrap ? 'pre-wrap' : 'nowrap'}`,
      sh.vertical ? 'writing-mode:vertical-rl' : '',
      sh.rotate ? `transform:rotate(${sh.rotate}deg)` : '',
    ].filter(Boolean).join(';');
    return `<div style="position:absolute;${st}">${paras}</div>`;
  }
  return '';
}

const pages = spec.slides.map((sl) => `
<section style="position:relative;width:1280px;height:720px;overflow:hidden;background:#${sl.bg}">
  ${sl.shapes.map(shapeHtml).join('\n  ')}
</section>`).join('\n');

const html = `<!DOCTYPE html><html><head><meta charset="utf-8"><style>
  html,body{margin:0;padding:0;background:#fff}
  section{display:block;margin:0;font-kerning:none;font-variant-ligatures:none}
</style></head><body>${pages}</body></html>`;

const tmpHtml = path.join(outDir, '_rerender.html');
fs.writeFileSync(tmpHtml, html);

const { browser, page } = await launchBrowser({ scale: 2 });
try {
  await page.goto('file://' + tmpHtml, { waitUntil: 'load' });
  await page.evaluate(() => document.fonts.ready);
  const n = await page.locator('section').count();
  for (let i = 0; i < n; i++) {
    await page.locator('section').nth(i).screenshot({
      path: path.join(outDir, `slide-${String(i + 1).padStart(2, '0')}.png`),
    });
  }
  console.log(`${n} 页重画 → ${outDir}`);
  console.log(`字体配置：${profile}（${F ? '会按目标机器的字体族重画' : '原样'}）`);
} finally {
  await browser.close();
}
