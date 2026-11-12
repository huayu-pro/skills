#!/usr/bin/env node
/**
 * verify-render.mjs — 用真渲染器（LibreOffice）把 pptx 渲成图，和 HTML 预览比对
 *
 *   node scripts/verify-render.mjs deck.pptx --out render [--vs preview] [--threshold 0.12]
 *
 * 和 verify-pptx.mjs 的分工：
 *   · verify-pptx  读 XML 自己重画 —— 验的是"我们写进去的几何"，不需要外部渲染器；
 *   · verify-render 交给 LibreOffice 真渲染 —— 验的是"文件能不能被 Office 正常打开并画出来"。
 *
 * 后者是唯一能证明"timing 没把文件搞坏"的手段：动画 XML 写错时，
 * PowerPoint/LibreOffice 要么拒绝打开，要么整页丢内容，这在 XML 层面看不出来。
 *
 * 注意：LibreOffice 的字体替换和排版与 PowerPoint 不完全一致，
 * 所以阈值要放宽（默认 12%），它抓的是**整块丢失、位置错乱**这类硬伤。
 *
 * LibreOffice 路径查找顺序：$CST_SOFFICE → ~/opt/libreoffice/squashfs-root/AppRun → PATH 里的 soffice。
 */
import fs from 'node:fs';
import path from 'node:path';
import os from 'node:os';
import { spawnSync } from 'node:child_process';
import { launchBrowser } from './lib/browser.mjs';
import { diffPng } from './lib/diff.mjs';

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
const pptx = args._[0];
if (!pptx) {
  console.error('用法: node scripts/verify-render.mjs <deck.pptx> --out dir [--vs previewDir] [--threshold 0.12]');
  process.exit(2);
}
const pptxPath = path.resolve(pptx);
const outDir = path.resolve(args.out || path.join(path.dirname(pptxPath), 'render'));
fs.mkdirSync(outDir, { recursive: true });
const vsDir = args.vs ? path.resolve(args.vs) : null;
const threshold = args.threshold ? parseFloat(args.threshold) : 0.12;
const dpi = args.dpi ? parseInt(args.dpi, 10) : 96;
// 布局级比对：默认降到 640×360。全幅网点/颗粒图在 LO 里的重采样
// 会在 1:1 像素上制造大量假差异；降采样后仍能抓住整块丢失/错位。
const compareW = args['compare-width'] ? parseInt(args['compare-width'], 10) : 1280;
const compareH = args['compare-height'] ? parseInt(args['compare-height'], 10) : 720;

/* ── 找 LibreOffice ─────────────────────────────────── */
function findSoffice() {
  const cands = [
    process.env.CST_SOFFICE,
    path.join(os.homedir(), 'opt/lo-deb/soffice'),
    path.join(os.homedir(), 'opt/libreoffice/squashfs-root/AppRun'),
    path.join(os.homedir(), 'opt/libreoffice/squashfs-root/usr/bin/soffice'),
    '/usr/bin/soffice',
    '/usr/bin/libreoffice',
  ].filter(Boolean);
  for (const c of cands) if (fs.existsSync(c)) return c;
  const which = spawnSync('sh', ['-c', 'command -v soffice || command -v libreoffice'], { encoding: 'utf8' });
  const p = (which.stdout || '').trim();
  return p && fs.existsSync(p) ? p : null;
}

const soffice = findSoffice();
if (!soffice) {
  console.error('\n✖ 找不到 LibreOffice。三种装法（都不需要 root）：');
  console.error('  1) AppImage（推荐，解包即可）:');
  console.error('     mkdir -p ~/opt/libreoffice && cd ~/opt/libreoffice');
  console.error('     curl -L -o lo.AppImage https://appimages.libreitalia.org/LibreOffice-26.8.1.1.basic-x86_64.AppImage');
  console.error('     chmod +x lo.AppImage && ./lo.AppImage --appimage-extract');
  console.error('  2) 已有 soffice 的话：export CST_SOFFICE=/path/to/soffice');
  console.error('  3) 有 root：sudo apt install libreoffice-impress\n');
  process.exit(1);
}

const tmpDir = fs.mkdtempSync(path.join(os.tmpdir(), 'cst-render-'));

console.log(`\n渲染器：${soffice}`);
const conv = spawnSync(
  soffice,
  [
    '--headless', '--norestore',
    // 注意：不要传 -env:UserInstallation。从 deb 解包出来的精简安装里，
    // 新建 profile 会静默失败（退出码 0 但不产出 PDF），用默认 profile 才正常。
    // 必须显式指定过滤器：解包安装的 LO 无法自动解析 "pdf" 别名，会静默不产出
    '--convert-to', 'pdf:impress_pdf_Export',
    '--outdir', tmpDir,
    pptxPath,
  ],
  // 不要覆盖 HOME：包装脚本按自身位置定位安装树，覆盖 HOME 会把它带偏
  { encoding: 'utf8', timeout: 180000 },
);

if (conv.status !== 0) {
  console.error('✖ 转换失败：');
  console.error((conv.stderr || conv.stdout || '').slice(0, 800));
  console.error('\n这一步失败通常说明 pptx 本身有问题——比如动画 XML 不合法，Office 拒绝打开。');
  process.exit(1);
}

const pdf = path.join(tmpDir, path.basename(pptxPath).replace(/\.pptx$/i, '.pdf'));
if (!fs.existsSync(pdf)) {
  console.error('✖ 没生成 PDF：' + (conv.stdout || '').slice(0, 400));
  process.exit(1);
}

/* ── PDF → PNG ──────────────────────────────────────── */
const prefix = path.join(outDir, 'p');
for (const f of fs.readdirSync(outDir)) if (/^p-\d+\.png$/.test(f)) fs.unlinkSync(path.join(outDir, f));
const ppm = spawnSync('pdftoppm', ['-png', '-r', String(dpi), pdf, prefix], { encoding: 'utf8' });
if (ppm.status !== 0) {
  console.error('✖ pdftoppm 失败：' + (ppm.stderr || '').slice(0, 400));
  process.exit(1);
}

const rendered = fs
  .readdirSync(outDir)
  .filter((f) => /^p-\d+\.png$/.test(f))
  .map((f) => ({ f, n: parseInt(f.match(/p-(\d+)/)[1], 10) }))
  .sort((a, b) => a.n - b.n); // pdftoppm 不补零，字典序会把 p-10 排到 p-2 前面
const pages = rendered.map(({ f }, i) => {
  const to = path.join(outDir, `slide-${String(i + 1).padStart(2, '0')}.png`);
  fs.renameSync(path.join(outDir, f), to);
  return { page: i + 1, file: to };
});

if (!pages.length) {
  console.error('✖ 渲染出 0 页——空 PDF 不是"通过"');
  process.exit(1);
}
const pptxList = spawnSync('unzip', ['-l', pptxPath], { encoding: 'utf8' });
const expectedPages = (pptxList.stdout.match(/ppt\/slides\/slide\d+\.xml/g) || []).length;
if (expectedPages && pages.length !== expectedPages) {
  console.error(`✖ PDF 页数 ${pages.length} 与 pptx 页数 ${expectedPages} 不一致——有页在渲染时丢了`);
  process.exit(1);
}

console.log(`${pages.length} 页渲染 → ${outDir}`);

/* ── 与 HTML 预览比对 ───────────────────────────────── */
if (vsDir) {
  const { browser, page } = await launchBrowser({ scale: 1 });
  try {
    console.log('\n与 HTML 预览比对（LibreOffice 的排版/字体与 PowerPoint 不完全一致，阈值放宽）：');
    let bad = 0;
    let missing = 0;
    for (const r of pages) {
      const ref = path.join(vsDir, `slide-${String(r.page).padStart(2, '0')}.png`);
      if (!fs.existsSync(ref)) {
        console.log(`  ✖ P${String(r.page).padStart(2, '0')}  缺参照图：${ref}`);
        missing++;
        continue;
      }
      const d = await diffPng(page, ref, r.file, path.join(outDir, `diff-${String(r.page).padStart(2, '0')}.png`), { width: compareW, height: compareH });
      if (d.ratio > threshold) bad++;
      const flag = d.ratio > threshold ? '✖' : d.ratio > threshold * 0.6 ? '△' : '✓';
      console.log(`  ${flag} P${String(r.page).padStart(2, '0')}  差异 ${(d.ratio * 100).toFixed(2)}%  （阈值 ${(threshold * 100).toFixed(0)}%）`);
    }
    fs.rmSync(tmpDir, { recursive: true, force: true });
    if (missing) {
      console.error(`\n✖ ${missing} 页缺参照图：--vs 给了就必须逐页可比，不能静默跳过\n`);
      bad += missing;
    }
    if (bad) {
      console.log(`\n${bad} 页差异偏大——看 diff-XX.png。若是整块丢失/错位，说明 pptx 有问题；`);
      console.log(`若只是字体宽度不同，属 LibreOffice 替换字体的正常现象。\n`);
      process.exitCode = 1;
    } else {
      console.log('\n全部在阈值内。\n');
    }
  } finally {
    await browser.close();
  }
} else {
  fs.rmSync(tmpDir, { recursive: true, force: true });
}
