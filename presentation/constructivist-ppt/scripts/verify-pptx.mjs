#!/usr/bin/env node
/**
 * verify-pptx.mjs — 反向渲染验收：读生成的 pptx，重画一遍，和 HTML 预览逐像素比
 *
 *   node scripts/verify-pptx.mjs deck.pptx --out pptx-render [--vs preview] [--threshold 0.04]
 *
 * 为什么要这一步：这台机器没有 PowerPoint / LibreOffice，pptx 渲不出图。
 * rerender.mjs 只能验证"提取"对不对（从 spec 重画），验证不了"发射"对不对
 * （EMU 算错、旋转丢、文字框位置偏）。这里直接读 pptx 里的 XML 重画，才算把 emit 层也验了。
 *
 * 实现用 HTML 而不是 SVG：文字折行、行高这些交给浏览器，
 * 和原始 HTML 用的是同一套排版规则，比对才有意义（SVG 得自己实现折行，误差反而更大）。
 *
 * 局限：它是"另一个渲染器"，自己也可能有 bug。只用它抓几何类错误
 * （位置/大小/旋转/颜色/丢对象），字形差异给宽容差。
 */
import fs from 'node:fs';
import path from 'node:path';
import { createRequire } from 'node:module';
import { launchBrowser } from './lib/browser.mjs';
import { diffPng } from './lib/diff.mjs';

const require = createRequire(import.meta.url);
const JSZip = require('jszip');

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
const pptxPath = args._[0];
if (!pptxPath) {
  console.error('用法: node scripts/verify-pptx.mjs <deck.pptx> --out dir [--vs previewDir] [--threshold 0.04]');
  process.exit(1);
}
const outDir = path.resolve(args.out || path.join(path.dirname(pptxPath), 'pptx-render'));
fs.mkdirSync(outDir, { recursive: true });
const vsDir = args.vs ? path.resolve(args.vs) : null;
const threshold = args.threshold ? parseFloat(args.threshold) : 0.04;
// 基线：第一次跑 --write-baseline 记下每页的"正常差异"，之后只比较增量。
// 绝对阈值抓不牢小幅错位（一个 430×120 的色块转错 6° 只占 1% 画面），
// 但相对基线的增长很灵敏——这就是 svg2ooxml 的 openxml-audit 用"受控样本"的思路。
const baselinePath = path.join(outDir, 'baseline.json');
const baseline = !args['write-baseline'] && fs.existsSync(baselinePath)
  ? JSON.parse(fs.readFileSync(baselinePath, 'utf8'))
  : null;
const growth = args.growth ? parseFloat(args.growth) : 0.008;

const zip = await JSZip.loadAsync(fs.readFileSync(path.resolve(pptxPath)));
const slideNames = Object.keys(zip.files)
  .filter((n) => /^ppt\/slides\/slide\d+\.xml$/.test(n))
  .sort((a, b) => parseInt(a.match(/slide(\d+)/)[1], 10) - parseInt(b.match(/slide(\d+)/)[1], 10));

async function mediaFor(slideNo) {
  const relFile = zip.file(`ppt/slides/_rels/slide${slideNo}.xml.rels`);
  const map = {};
  if (!relFile) return map;
  const rels = await relFile.async('string');
  for (const m of rels.matchAll(/Id="(rId\d+)"[^>]*Target="([^"]+)"/g)) {
    const target = m[2].replace(/^\.\.\//, 'ppt/');
    const f = zip.file(target);
    if (!f) continue;
    const b64 = await f.async('base64');
    const ext = target.split('.').pop().toLowerCase();
    const mime = ext === 'png' ? 'image/png' : ext === 'jpg' || ext === 'jpeg' ? 'image/jpeg' : 'image/png';
    map[m[1]] = `data:${mime};base64,${b64}`;
  }
  return map;
}

const { browser, page } = await launchBrowser({ scale: 1 });
const results = [];
try {
  for (let i = 0; i < slideNames.length; i++) {
    const xml = await zip.file(slideNames[i]).async('string');
    const media = await mediaFor(i + 1);
    const html = await page.evaluate(buildHtml, { xml, media });
    await page.setContent(
      `<!DOCTYPE html><html><head><meta charset="utf-8"><style>html,body{margin:0;padding:0}
       #s{position:relative;width:1280px;height:720px;overflow:hidden;font-kerning:none;font-variant-ligatures:none}
       </style></head><body><div id="s">${html}</div></body></html>`,
      { waitUntil: 'load' },
    );
    await page.evaluate(() => document.fonts.ready);
    const file = path.join(outDir, `slide-${String(i + 1).padStart(2, '0')}.png`);
    await page.screenshot({ path: file, clip: { x: 0, y: 0, width: 1280, height: 720 } });
    results.push({ page: i + 1, file });
  }

  if (!results.length) {
    console.error('✖ pptx 里 0 页——空文件不是"通过"');
    process.exitCode = 1;
  }
  console.log(`\n${results.length} 页反渲 → ${outDir}`);

  if (vsDir) {
    console.log(baseline
      ? `\n与 HTML 预览比对（基线模式，允许每页增长 ${(growth * 100).toFixed(1)} 个百分点）：`
      : '\n与 HTML 预览逐像素比对：');
    let bad = 0;
    let missing = 0;
    const record = {};
    for (const r of results) {
      const ref = path.join(vsDir, `slide-${String(r.page).padStart(2, '0')}.png`);
      if (!fs.existsSync(ref)) {
        console.log(`  ✖ P${String(r.page).padStart(2, '0')}  缺参照图：${ref}`);
        missing++;
        continue;
      }
      const d = await diffPng(page, ref, r.file, path.join(outDir, `diff-${String(r.page).padStart(2, '0')}.png`));
      record[r.page] = d.ratio;
      const base = baseline ? baseline[r.page] : null;
      const over = base != null
        ? d.ratio > base + growth
        : d.ratio > threshold;
      const near = base != null ? d.ratio > base + growth * 0.6 : d.ratio > threshold * 0.6;
      if (over) bad++;
      const extra = base != null ? `  基线 ${(base * 100).toFixed(2)}%  ${d.ratio > base ? '+' : ''}${((d.ratio - base) * 100).toFixed(2)}pp` : `  （阈值 ${(threshold * 100).toFixed(0)}%）`;
      console.log(`  ${over ? '✖' : near ? '△' : '✓'} P${String(r.page).padStart(2, '0')}  差异 ${(d.ratio * 100).toFixed(2)}%${extra}`);
    }
    if (missing) {
      console.error(`\n✖ ${missing} 页缺参照图：--vs 给了就必须逐页可比，不能静默跳过\n`);
      bad += missing;
    }
    if (args['write-baseline']) {
      // 先判红再写基线。早先是先写后判，一次坏运行就被固化成参照，
      // 之后每次比对都对着错的基线跑，问题被永久掩盖。
      if (bad) {
        console.error(`\n✖ ${bad} 页超出阈值——拒绝写入基线。基线只在全绿时更新。\n`);
        process.exitCode = 1;
      } else {
        fs.writeFileSync(baselinePath, JSON.stringify(record, null, 2));
        console.log(`\n基线已写入 ${baselinePath}（下次跑会自动按增量比对）\n`);
        process.exitCode = 0;
      }
    } else {
      console.log(bad ? `\n${bad} 页异常——看 diff-XX.png 热力图，红点是位置/大小对不上的地方\n` : '\n全部正常。\n');
      process.exitCode = bad ? 1 : 0;
    }
  }

  // 讲稿验证：plan 契约要求每页 notes（purpose/talk）必填——PPTX 侧必须有对应
  // 非空 notesSlide。链路断了（extract 没填 / emit 没写）在这里必须红，不能静默绿。
  // 样张/特殊 deck 用 --no-notes 豁免。
  if (!args['no-notes']) {
    let notesBad = 0;
    for (let i = 1; i <= slideNames.length; i++) {
      const rels = zip.file(`ppt/slides/_rels/slide${i}.xml.rels`);
      const relsText = rels ? await rels.async('string') : '';
      const m = relsText.match(/Target="\.\.\/notesSlides\/(notesSlide\d+\.xml)"/);
      const nFile = m ? zip.file(`ppt/notesSlides/${m[1]}`) : null;
      if (!nFile) {
        console.log(`  ✖ P${String(i).padStart(2, '0')} 缺讲者备注（无 notesSlide）`);
        notesBad++;
        continue;
      }
      const nXml = await nFile.async('string');
      const texts = [...nXml.matchAll(/<a:t>([^<]*)<\/a:t>/g)].map((x) => x[1]).join('');
      if (!texts.trim()) {
        console.log(`  ✖ P${String(i).padStart(2, '0')} 讲者备注为空`);
        notesBad++;
      }
    }
    if (notesBad) {
      console.error(`\n✖ ${notesBad} 页讲者备注缺失/为空——notes 链路断裂不是"通过"（样张场景可 --no-notes 豁免）\n`);
      process.exitCode = 1;
    } else {
      console.log(`\n讲者备注：${slideNames.length} 页全部非空`);
    }
  }
} finally {
  await browser.close();
}

// 没给 --vs 就没做任何比对：只出图 + 查备注，不能算「反渲通过」。
// 早先这里直接 exit 0，用户手工跑一遍会以为验过了。
if (!vsDir) {
  console.error('\n✖ 未传 --vs <preview 目录>：本次只反渲出图并检查了备注，没有和 HTML 预览做逐像素比对。');
  console.error('   要验「转换器没走样」，必须给参照目录，例如：');
  console.error('   node scripts/verify-pptx.mjs deck.pptx --out pptx-render --vs preview');
  console.error('   确认只需出图时加 --no-compare 明确表示放弃比对。\n');
  if (!args['no-compare']) process.exitCode = 1;
}

/* ───────────── 跑在浏览器里：OOXML → HTML ───────────── */
function buildHtml({ xml, media }) {
  const EMU = 9525;
  const P = 'http://schemas.openxmlformats.org/presentationml/2006/main';
  const A = 'http://schemas.openxmlformats.org/drawingml/2006/main';
  const R = 'http://schemas.openxmlformats.org/officeDocument/2006/relationships';

  const doc = new DOMParser().parseFromString(xml, 'application/xml');
  if (doc.querySelector('parsererror')) return '<div style="width:1280px;height:720px;background:#f00"></div>';

  const first = (root, ns, name) => (root ? root.getElementsByTagNameNS(ns, name)[0] || null : null);
  const attr = (el, n) => (el ? el.getAttribute(n) : null);
  // 只取直接子节点：spPr 下面还嵌着 a:ln，里面的 solidFill 是描边色，
  // 用 getElementsByTagName 会把描边色误当成填充色（"空心圆"会被画成实心方块）
  const childOf = (root, name) => (root ? Array.from(root.children).find((c) => c.localName === name) || null : null);
  const px = (emu) => (Number(emu) || 0) / EMU;
  const esc = (s) => String(s).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
  // pptx 里写的是"目标机器的字体"，本机没有。比对前映射回本机度量兼容的那一支，
  // 否则 Arial Narrow 会回退成普通无衬线，宽度差 30%，diff 全是字体造成的假阳性。
  const FONT_SUB = {
    '微软雅黑': "'Noto Sans CJK SC'",
    '思源黑体 CN': "'Noto Sans CJK SC'",
    'Arial Narrow': "'Liberation Sans Narrow'",
    'Arial': "'Liberation Sans'",
    'Consolas': "'DejaVu Sans Mono'",
    'Courier New': "'DejaVu Sans Mono'",
  };
  const colorOf = (el) => {
    const c = first(el, A, 'srgbClr');
    return c ? '#' + c.getAttribute('val') : null;
  };

  const slide = first(doc, P, 'sld');
  const bg = colorOf(first(slide, P, 'bg')) || '#ffffff';
  const parts = [`<div style="position:absolute;inset:0;background:${bg}"></div>`];

  const spTree = first(slide, P, 'spTree');
  if (!spTree) return parts.join('');

  const shapes = Array.from(spTree.childNodes).filter((n) => n.nodeType === 1 && ['sp', 'pic'].includes(n.localName));

  for (const sh of shapes) {
    const xfrm = first(sh, A, 'xfrm');
    if (!xfrm) continue;
    const off = first(xfrm, A, 'off');
    const ext = first(xfrm, A, 'ext');
    const x = px(attr(off, 'x'));
    const y = px(attr(off, 'y'));
    const w = px(attr(ext, 'cx'));
    const h = px(attr(ext, 'cy'));
    const rot = Number(attr(xfrm, 'rot') || 0) / 60000;

    const base = `position:absolute;left:${x}px;top:${y}px;width:${w}px;height:${h}px;` +
      (rot ? `transform:rotate(${rot}deg);` : '');

    if (sh.localName === 'pic') {
      const blip = first(sh, A, 'blip');
      const rid = blip && blip.getAttributeNS(R, 'embed');
      const href = media[rid] || '';
      parts.push(`<div style="${base}overflow:hidden"><img src="${href}" style="width:100%;height:100%;object-fit:cover"></div>`);
      continue;
    }

    const spPr = first(sh, P, 'spPr');
    const custGeom = first(spPr, A, 'custGeom');
    const prst = first(spPr, A, 'prstGeom');
    const kind = prst ? prst.getAttribute('prst') : 'rect';
    const fillEl = childOf(spPr, 'solidFill');
    const fill = fillEl ? colorOf(fillEl) : null;
    const ln = childOf(spPr, 'ln');
    const stroke = ln ? colorOf(childOf(ln, 'solidFill')) : null;
    const sw = ln ? Number(attr(ln, 'w') || 0) / EMU : 0;

    let style = base;
    if (fill) style += `background:${fill};`;
    if (stroke) style += `border:${sw}px solid ${stroke};box-sizing:border-box;`;
    if (kind === 'ellipse') style += 'border-radius:50%;';

    if (custGeom) {
      const pathEl = first(custGeom, A, 'path');
      const pts = pathEl
        ? Array.from(pathEl.getElementsByTagNameNS(A, 'pt')).map(
          (pt) => `${((px(pt.getAttribute('x')) / w) * 100).toFixed(2)}% ${((px(pt.getAttribute('y')) / h) * 100).toFixed(2)}%`,
        )
        : [];
      if (pts.length >= 3) style += `clip-path:polygon(${pts.join(',')});`;
    }

    if (fill || stroke || custGeom) parts.push(`<div style="${style}"></div>`);

    // 文字
    const txBody = first(sh, P, 'txBody');
    if (!txBody) continue;
    const bodyPr = first(txBody, A, 'bodyPr');
    const wrap = attr(bodyPr, 'wrap') !== 'none';
    const vert = attr(bodyPr, 'vert');

    const paras = Array.from(txBody.childNodes).filter((n) => n.nodeType === 1 && n.localName === 'p');
    const inner = [];
    let lh = 0;
    let family = 'sans-serif';

    for (const p of paras) {
      const pPr = first(p, A, 'pPr');
      const algn = attr(pPr, 'algn') || 'l';
      const runs = Array.from(p.childNodes).filter((n) => n.nodeType === 1 && n.localName === 'r');
      if (!runs.length) continue;

      const rPr0 = first(runs[0], A, 'rPr');
      const szPt = Number(attr(rPr0, 'sz') || 1800) / 100;
      const sizePx = (szPt * 96) / 72;
      const latin = first(rPr0, A, 'latin');
      family = (latin && latin.getAttribute('typeface')) || family;
      const lnSpc = first(pPr, A, 'lnSpc');
      const spcPts = lnSpc ? Number(attr(first(lnSpc, A, 'spcPts'), 'val') || 0) / 100 : szPt * 1.2;
      lh = lh || (spcPts * 96) / 72;

      const html = runs
        .map((r) => {
          const rp = first(r, A, 'rPr');
          const t = first(r, A, 't');
          const rsz = Number(attr(rp, 'sz') || attr(rPr0, 'sz') || 1800) / 100;
          const s = [`font-size:${(rsz * 96) / 72}px`];
          if (attr(rp, 'b') === '1') s.push('font-weight:700');
          if (attr(rp, 'i') === '1') s.push('font-style:italic');
          const spc = Number(attr(rp, 'spc') || 0) / 100;
          if (spc) s.push(`letter-spacing:${(spc * 96) / 72}px`);
          const c = colorOf(rp);
          if (c) s.push(`color:${c}`);
          return `<span style="${s.join(';')}">${esc(t ? t.textContent : '')}</span>`;
        })
        .join('');

      const align = algn === 'ctr' ? 'center' : algn === 'r' ? 'right' : 'left';
      inner.push(`<div style="text-align:${align}">${html}</div>`);
    }
    if (!inner.length) continue;

    const tstyle = base +
      `line-height:${lh}px;` +
      `font-family:${FONT_SUB[family] || `'${family}'`},sans-serif;` +
      `white-space:${wrap ? 'pre-wrap' : 'nowrap'};` +
      (vert === 'eaVert' ? 'writing-mode:vertical-rl;' : '');
    parts.push(`<div style="${tstyle}">${inner.join('')}</div>`);
  }

  return parts.join('');
}
