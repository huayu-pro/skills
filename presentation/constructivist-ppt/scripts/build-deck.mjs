#!/usr/bin/env node
/**
 * build-deck.mjs — deck.html → deck.pptx（可选同时出预览图）
 *
 *   node scripts/build-deck.mjs deck.html -o out/deck.pptx \
 *        [--font-profile office|source|asis] \
 *        [--mode native|hybrid|image] \
 *        [--preview] [--spec out/deck.spec.json] [--allow-forbid]
 *
 * 三种模式：
 *   native  全部原生化，颗粒/网点叠层也作为图片（默认）
 *   hybrid  同 native，但对 --raster-slides 指定的页整页栅格化
 *   image   所有页整页栅格化，100% 保全视觉、完全不可编辑
 */
import fs from 'node:fs';
import path from 'node:path';
import os from 'node:os';
import { createRequire } from 'node:module';
import { launchBrowser, openDeck } from './lib/browser.mjs';
import { extractDeck } from './lib/extract.mjs';
import { emitDeck, FONT_PROFILES } from './lib/emit.mjs';
import { applyAnimations, verifyXml } from './lib/anim.mjs';

const ALLOW_FORBID = process.argv.includes('--allow-forbid');
const require = createRequire(import.meta.url);
const pptxgen = require('pptxgenjs');

class ForbidError extends Error {
  constructor(warnings) {
    super('FORBID');
    this.warnings = warnings;
  }
}
class CheckDone extends Error {}

function parseArgs(argv) {
  const a = { _: [] };
  const alias = { o: 'o', h: 'help' };
  for (let i = 0; i < argv.length; i++) {
    const t = argv[i];
    if (t.startsWith('-') && t !== '-') {
      const isLong = t.startsWith('--');
      let k = isLong ? t.slice(2) : alias[t.slice(1)] || t.slice(1);
      let v;
      if (k.includes('=')) {
        // 支持 --anim-mode=click 这种写法
        const eq = k.indexOf('=');
        v = k.slice(eq + 1);
        k = k.slice(0, eq);
      } else {
        v = argv[i + 1] && !argv[i + 1].startsWith('-') ? argv[++i] : true;
      }
      a[k] = v;
    } else a._.push(t);
  }
  return a;
}

const args = parseArgs(process.argv.slice(2));
const html = args._[0];
if (!html) {
  console.error('用法: node scripts/build-deck.mjs <deck.html> -o <out.pptx> [--font-profile office] [--mode native] [--preview]');
  process.exit(1);
}
const output = path.resolve(args.o || args.out || path.join(path.dirname(html), 'deck.pptx'));
const mode = args.mode || 'native';
const fontProfile = args['font-profile'] || 'office';
const wantPreview = !!args.preview;
const CHECK = !!args.check;
const specOut = args.spec ? path.resolve(args.spec) : null;

fs.mkdirSync(path.dirname(output), { recursive: true });

const { browser, page } = await launchBrowser({ scale: 2 });
let spec;
let report;
let animReport = null;
let fontReport = [];
let forbidFailure = null;
let checkDone = false;
let tempOutput = null;
try {
  await openDeck(page, html);
  spec = await extractDeck(page, html);

  if (specOut) fs.writeFileSync(specOut, JSON.stringify(spec, null, 2));

  // FORBID 是"画面会残"级别的失败：在写任何交付物之前停住。
  const forbidWarnings = spec.slides.flatMap((s) => s.warnings
    .filter((w) => String(w).startsWith('FORBID:'))
    .map((w) => `第 ${s.index + 1} 页：${w}`));
  if (forbidWarnings.length && !ALLOW_FORBID) throw new ForbidError(forbidWarnings);
  if (CHECK) throw new CheckDone();

  if (mode === 'image' || (mode === 'hybrid' && args['raster-slides'])) {
    // 整页栅格化：把每页截图当全幅图片塞进 PPTX
    const raster = new Set(
      String(args['raster-slides'] || '')
        .split(',')
        .map((n) => parseInt(n, 10))
        .filter(Boolean),
    );
    const previewDir = path.resolve(args['raster-dir'] || path.join(path.dirname(output), 'raster'));
    fs.mkdirSync(previewDir, { recursive: true });
    for (const sl of spec.slides) {
      const n = sl.index + 1;
      if (mode === 'image' || raster.has(n)) {
        const el = page.locator('section.slide').nth(sl.index);
        await el.screenshot({ path: path.join(previewDir, `slide-${String(n).padStart(2, '0')}.png`) });
        sl.raster = path.join(previewDir, `slide-${String(n).padStart(2, '0')}.png`);
      }
    }
  }

  // data-fidelity="raster"：把关键标题连同它的底色一起截成小图，压回原位。
  // 只解决"目标机器没有黑体导致字重走样"这一个问题，因此：
  //   · 标题必须落在纯色区（纸底或墨底），不要压在别的形状上；
  //   · 截图区域严格等于字的 ink 盒，通过临时把行高撑到自然行高实现，避免切字。
  const rasterShapes = spec.slides.flatMap((sl) => sl.shapes.filter((sh) => sh.kind === 'raster'));
  if (rasterShapes.length) {
    const dir = path.resolve(args['raster-dir'] || path.join(path.dirname(output), 'raster'));
    fs.mkdirSync(dir, { recursive: true });
    for (const sh of rasterShapes) {
      await page.evaluate((rid) => {
        const el = document.querySelector(`[data-cst-raster="${rid}"]`);
        if (!el) return;
        el.setAttribute('data-cst-prev-lh', el.style.lineHeight || '');
        el.setAttribute('data-cst-prev-top', el.style.top || '');
        const h0 = el.offsetHeight;
        el.style.lineHeight = 'normal';
        const h1 = el.offsetHeight;
        if (h1 > h0) {
          const t = parseFloat(getComputedStyle(el).top) || 0;
          el.style.top = `${t - (h1 - h0) / 2}px`;
        }
      }, sh.rasterId);

      const file = path.join(dir, `${sh.rasterId}.png`);
      await page.locator(`[data-cst-raster="${sh.rasterId}"]`).first().screenshot({ path: file });

      await page.evaluate((rid) => {
        const el = document.querySelector(`[data-cst-raster="${rid}"]`);
        if (!el) return;
        el.style.lineHeight = el.getAttribute('data-cst-prev-lh') || '';
        el.style.top = el.getAttribute('data-cst-prev-top') || '';
        el.removeAttribute('data-cst-prev-lh');
        el.removeAttribute('data-cst-prev-top');
      }, sh.rasterId);

      sh.kind = 'image';
      sh.src = file;
      sh.fit = 'cover';
      delete sh.rasterId;
    }
  }

  if (wantPreview) {
    const dir = path.resolve(args['preview-dir'] || path.join(path.dirname(output), 'preview'));
    fs.mkdirSync(dir, { recursive: true });
    for (const sl of spec.slides) {
      const el = page.locator('section.slide').nth(sl.index);
      await el.screenshot({ path: path.join(dir, `slide-${String(sl.index + 1).padStart(2, '0')}.png`) });
    }
    console.log(`预览图 → ${path.resolve(args['preview-dir'] || path.join(path.dirname(output), 'preview'))}`);
  }

  // 全页栅格化模式：直接把 spec 换成"每页一张图"
  if (mode === 'image' || spec.slides.some((s) => s.raster)) {
    spec = {
      ...spec,
      slides: spec.slides.map((s) => (s.raster
        ? {
          ...s,
          shapes: [{ kind: 'image', x: 0, y: 0, w: spec.canvas.w, h: spec.canvas.h, src: s.raster, fit: 'cover' }],
        }
        : s)),
    };
  }

  // 纹理与示例图在包里是纯文本 SVG（发布平台不接受二进制），但 PPTX 的图片槽
  // 只认 PNG/JPEG——把 SVG 直接交给 pptxgenjs 会产出"名字叫 .png、内容是 SVG 文本"
  // 的媒体文件，PowerPoint 打开必残。所以这里用浏览器（本来就是硬依赖）把 SVG
  // 栅格化成临时 PNG，再交给 emit；临时文件在 finally 里清理，不落进交付目录。
  await rasterizeSvgShapes(page, spec, html);

  const emitted = emitDeck(pptxgen, spec, { fontProfile, title: spec.meta.title });
  report = emitted.report;
  tempOutput = path.join(path.dirname(output), `.${path.basename(output)}.tmp-${process.pid}.pptx`);
  await emitted.pptx.writeFile({ fileName: tempOutput });

  // 字体探针：document.fonts.check() 对缺失字体也返回 true，
  // 只能拿 canvas 量宽度、和一个一定不存在的字体比（Slidev 的 walker 用同一招）。
  const outFonts = Object.values(FONT_PROFILES[fontProfile] || {});
  if (outFonts.length) {
    fontReport = await page.evaluate((names) => {
      const ctx = document.createElement('canvas').getContext('2d');
      const w = (f) => {
        ctx.font = `72px ${f}`;
        return ctx.measureText('mmmmmmmmmmlli').width;
      };
      const ghost = w(`"__cst_ghost__", monospace`);
      return names.map((n) => ({ name: n, ok: Math.abs(w(`"${n}", monospace`) - ghost) > 0.5 }));
    }, outFonts);
  }

  // 入场动画：默认关，只有页面里出现 data-anim 才动手
  const hasAnim = spec.slides.some((sl) => sl.shapes.some((sh) => sh.anim));
  if (hasAnim && !args['no-anim']) {
    animReport = await applyAnimations(tempOutput, spec, { mode: args['anim-mode'] || 'chain' });
    const bad = await verifyXml(page, tempOutput);
    for (const b of bad) animReport.warnings.push(`XML 不良构：${b}`);
  }

  if (animReport && animReport.errors.length) {
    try { fs.unlinkSync(tempOutput); } catch {}
    tempOutput = null;
  } else {
    fs.renameSync(tempOutput, output);
    tempOutput = null;
  }
} catch (err) {
  if (err instanceof ForbidError) forbidFailure = err;
  else if (err instanceof CheckDone) checkDone = true;
  else {
    if (tempOutput) { try { fs.unlinkSync(tempOutput); } catch {} }
    throw err;
  }
} finally {
  await browser.close();
}

if (checkDone) {
  const warns = spec.slides.flatMap((s) => s.warnings.map((w) => `第 ${s.index + 1} 页：${w}`));
  console.log(`\n✔ check  ${path.relative(process.cwd(), html)}  ${spec.slides.length} 页  未写盘`);
  if (warns.length) {
    console.log(`\n⚠ ${warns.length} 条提示：`);
    for (const w of warns.slice(0, 40)) console.log('  · ' + w);
  } else {
    console.log('  无警告。');
  }
  process.exit(0);
}

if (forbidFailure) {
  console.error(`\n✖ ${forbidFailure.warnings.length} 处转换器表达不了的写法，已停止写盘：`);
  for (const w of forbidFailure.warnings) console.error('  · ' + w);
  console.error('  逐条改掉；确认要保留就加 --allow-forbid（只用于定位，不用于交付）。');
  process.exit(1);
}

// ---- 控制台报告
const warns = spec.slides.flatMap((s) => s.warnings.map((w) => `第 ${s.index + 1} 页：${w}`));
const all = [...warns, ...report.warnings];

console.log(`\n✔ ${path.relative(process.cwd(), output)}  ${spec.slides.length} 页  字体=${fontProfile}  模式=${mode}`);
console.log(
  report.slides.map((s) => `  P${String(s.index).padStart(2, '0')}  形状${String(s.shape).padStart(3)}  文本${String(s.text).padStart(2)}  图${String(s.image).padStart(2)}`).join('\n'),
);

const missingFonts = fontReport.filter((f) => !f.ok);
if (missingFonts.length) {
  console.log(`\n▸ 字体：${missingFonts.map((f) => f.name).join(' / ')} 本机不存在，预览已回退`);
  console.log('  写进 pptx 的是这些字体名——目标机器需装有它们；否则用 font-map.mjs 换掉，或改 --font-profile');
  // office 档的字体本来就不在 Linux 上，这属于预期状态，只在 source 档（用户想要思源）才计入警告
  if (fontProfile !== 'office') {
    all.push(...missingFonts.map((f) => `输出字体「${f.name}」本机不存在（预览已回退，交付前请确认目标机器有该字体）`));
  }
}

if (animReport && animReport.errors.length) {
  console.error('\n✖ 动画自检失败（未写入，避免"看着有、播不出来"）：');
  for (const e of animReport.errors) console.error('  · ' + e);
  process.exitCode = 1;
}

if (animReport && (animReport.slides || animReport.warnings.length)) {
  all.push(...animReport.warnings);
  if (animReport.targets) {
    console.log(`\n▸ 动画：${animReport.slides} 页 / ${animReport.targets} 个对象（--no-anim 可关闭）`);
  }
}

if (all.length) {
  console.log(`\n⚠ ${all.length} 条提示：`);
  for (const w of all.slice(0, 40)) console.log('  · ' + w);
  if (all.length > 40) console.log(`  … 另有 ${all.length - 40} 条`);
} else {
  console.log('\n无警告。');
}

/* FORBID 是"画面会残"级别的失败，不能只印在提示里。
   文件照常写出（便于定位），但退出码必须是 1，否则 CI 与 agent 会以为交付成功。 */
if (!ALLOW_FORBID) {
  const bad = all.filter((w) => String(w).startsWith('FORBID:'));
  if (bad.length) {
    console.error(`\n✖ ${bad.length} 处转换器表达不了的写法，成品会残：`);
    for (const w of bad.slice(0, 10)) console.error('  ' + w);
    console.error('  逐条改掉；确认要保留就加 --allow-forbid（会在交付说明里注记录）。');
    process.exitCode = 1;
  }
}

/**
 * 把 spec 里的 SVG 图片槽栅格化成临时 PNG。
 *
 * 为什么需要：包内只放纯文本 SVG（发布平台不接受二进制），而 pptxgenjs 会把
 * .svg 原样塞进 ppt/media，得到后缀 .png 内容却是文本的媒体文件——PowerPoint
 * 打不开。浏览器是本脚本的既有硬依赖，用它栅格化最可靠（ImageMagick 的 SVG
 * 渲染器不支持 feTurbulence 这类滤镜，不能用来做这件事）。
 */
async function rasterizeSvgShapes(page, spec, htmlPath) {
  const svgShapes = spec.slides.flatMap((s) => s.shapes.filter((sh) => sh.kind === 'image' && /\.svg$/i.test(sh.src || '')));
  if (!svgShapes.length) return;

  const tmpDir = fs.mkdtempSync(path.join(os.tmpdir(), 'cst-svg-'));
  const cache = new Map();
  for (const sh of svgShapes) {
    const abs = path.resolve(path.dirname(htmlPath), sh.src);
    if (!fs.existsSync(abs)) {
      sh.missing = true;
      continue;
    }
    if (!cache.has(abs)) {
      const out = path.join(tmpDir, `${cache.size}.png`);
      const svgText = fs.readFileSync(abs, 'utf8');
      // 用 SVG 自身的宽高（或视口）作为栅格尺寸，纹理才不会被拉伸
      const wm = svgText.match(/\bwidth=["']?(\d+)/);
      const hm = svgText.match(/\bheight=["']?(\d+)/);
      const w = wm ? Number(wm[1]) : 1280;
      const h = hm ? Number(hm[1]) : 720;
      const dataUri = `data:image/svg+xml;base64,${Buffer.from(svgText, 'utf8').toString('base64')}`;
      const ok = await page.evaluate(async ({ uri, w, h }) => {
        const img = new Image();
        img.width = w; img.height = h;
        await new Promise((res, rej) => {
          img.onload = res; img.onerror = rej;
          img.src = uri;
        });
        const c = document.createElement('canvas');
        c.width = w; c.height = h;
        c.getContext('2d').drawImage(img, 0, 0, w, h);
        return c.toDataURL('image/png');
      }, { uri: dataUri, w, h }).catch(() => null);
      if (!ok) { sh.missing = true; continue; }
      fs.writeFileSync(out, Buffer.from(ok.split(',')[1], 'base64'));
      cache.set(abs, out);
    }
    sh.src = cache.get(abs);
  }
  if (cache.size) {
    console.log(`▸ 纹理/图片：${cache.size} 个 SVG 已栅格化为临时 PNG（包内保持纯文本）`);
  }
}
