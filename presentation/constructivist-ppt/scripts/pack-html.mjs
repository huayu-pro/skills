#!/usr/bin/env node
/**
 * pack-html.mjs — 把 deck 打包成单个自包含 HTML
 *
 *   node scripts/pack-html.mjs deck.html [-o out.html] [--root dir] [--dry-run]
 *
 * 内联 <link rel=stylesheet>、CSS 里的 url(...)、以及 <img src>。
 *
 * 安全围栏：
 *   · 每个被读的文件必须真实位于 --root / 页面所在目录 / 本 skill 目录之内（符号链接要解析后再判）；
 *   · 只允许内联图片、字体与样式表扩展名；其余扩展名、无扩展名文件一律拒绝；
 *   · 路径中不允许出现隐藏段（以 . 开头的目录/文件名），避免误读凭据目录；
 *   · SVG/CSS 等文本资源额外扫一遍密钥特征串；
 *   · 有任何一条不过就**不写盘**，直接退出 —— 打包产物是要发出去的，
 *     把凭据或私钥 base64 进一个可分享的 HTML 是不可挽回的事故。
 */
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const here = path.dirname(fileURLToPath(import.meta.url));
const args = process.argv.slice(2);
const roots = [];
const positional = [];
for (let i = 0; i < args.length; i++) {
  if (args[i] === '--root') { roots.push(path.resolve(args[++i])); continue; }
  if (args[i] === '-o' || args[i] === '--out') { i++; continue; }
  if (!args[i].startsWith('-')) positional.push(args[i]);
}
const input = positional[0];
if (!input) {
  console.error('用法: node scripts/pack-html.mjs <deck.html> [-o out.html] [--root dir] [--dry-run]');
  process.exit(2);
}
const inputPath = path.resolve(input);
if (!/\.html?$/i.test(inputPath) || !fs.existsSync(inputPath) || !fs.statSync(inputPath).isFile()) {
  console.error('✖ 输入必须是存在的 .html/.htm 文件；不读取其他类型的文件');
  process.exit(2);
}
const dryRun = args.includes('--dry-run');
const outIdx = args.findIndex((a) => a === '-o' || a === '--out');
const output = path.resolve(
  outIdx > -1 ? args[outIdx + 1] : input.replace(/\.html?$/i, '') + '.packed.html',
);
const baseDir = path.dirname(inputPath);
const skillDir = path.resolve(here, '..');

const MIME = {
  '.png': 'image/png', '.jpg': 'image/jpeg', '.jpeg': 'image/jpeg', '.webp': 'image/webp',
  '.gif': 'image/gif', '.svg': 'image/svg+xml', '.woff2': 'font/woff2', '.woff': 'font/woff',
};

/* ── 围栏：正白名单，不靠敏感文件名黑名单 ───────────── */
const real = (p) => { try { return fs.realpathSync(p); } catch { return null; } };
const FENCE = [...new Set([...roots, baseDir, skillDir])].map(real).filter(Boolean);
const inside = (f) => FENCE.some((d) => f === d || f.startsWith(d.endsWith(path.sep) ? d : d + path.sep));

// 只允许这些扩展名进入内联流程。样式表单独允许，但不会走 toDataUri。
const ALLOW_EXT = new Set([...Object.keys(MIME), '.css']);
const SECRET_TEXT = /sk-ant-|sk-[A-Za-z0-9]{32,}|AKIA[0-9A-Z]{16}|-----BEGIN [A-Z0-9 ]{0,48}-----|gh[pousr]_[A-Za-z0-9]{30,}|github_pat_[A-Za-z0-9_]{30,}|xox[abeprs]-[A-Za-z0-9-]{10,}|AIza[0-9A-Za-z_-]{30,}/;

const errors = [];
const refused = new Set();
const reject = (ref, msg) => {
  if (refused.has(ref)) return;
  refused.add(ref);
  errors.push(msg);
};

/** 返回相对某个围栏根的路径；找不到返回 null。 */
function relInside(f) {
  for (const d of FENCE) {
    const rel = path.relative(d, f);
    if (rel && !rel.startsWith('..') && !path.isAbsolute(rel)) return rel;
  }
  return null;
}

function resolveRef(ref, label, base = baseDir) {
  const cand = path.resolve(base, ref);
  if (!fs.existsSync(cand)) {
    errors.push(`${label}：「${ref}」不存在`);
    return null;
  }
  const f = real(cand);
  if (!f || !inside(f)) {
    reject(ref, `${label}：「${ref}」解析到围栏之外（${f || cand}），拒绝读取。需要的话加 --root <项目根>`);
    return null;
  }
  const rel = relInside(f);
  if (rel && rel.split(path.sep).some((s) => s.startsWith('.'))) {
    reject(ref, `${label}：「${ref}」包含隐藏路径段，拒绝读取`);
    return null;
  }
  const ext = path.extname(f).toLowerCase();
  if (!ALLOW_EXT.has(ext)) {
    reject(ref, `${label}：「${ref}」不是允许的图片/字体/样式扩展名，拒绝内联`);
    return null;
  }
  return f;
}

function toDataUri(file, label) {
  const ext = path.extname(file).toLowerCase();
  const mime = MIME[ext];
  if (!mime) {
    errors.push(`${label}：「${path.basename(file)}」不是可内联的图片/字体`);
    return null;
  }
  const buf = fs.readFileSync(file);
  if (ext === '.svg' && SECRET_TEXT.test(buf.toString('utf8'))) {
    errors.push(`${label}：「${path.basename(file)}」内容疑似含密钥，拒绝内联`);
    return null;
  }
  return `data:${mime};base64,${buf.toString('base64')}`;
}

/* ── 打包 ───────────────────────────────────────────── */
let html = fs.readFileSync(inputPath, 'utf8');
let cssCount = 0;
let imgCount = 0;

html = html.replace(/<link[^>]+rel=["']stylesheet["'][^>]*>/gi, (tag) => {
  const m = tag.match(/href=["']([^"']+)["']/i);
  if (!m) return tag;
  const cssPath = resolveRef(m[1], '样式表');
  if (!cssPath) return tag;
  let css = fs.readFileSync(cssPath, 'utf8');
  if (SECRET_TEXT.test(css)) {
    errors.push(`样式表：「${m[1]}」内容疑似含密钥，拒绝内联`);
    return tag;
  }
  css = css.replace(/url\((["']?)([^"')]+)\1\)/g, (full, q, ref) => {
    if (/^(data:|https?:)/.test(ref)) return full;
    const p = resolveRef(ref, 'CSS 资源', path.dirname(cssPath));
    if (!p) return full;
    const uri = toDataUri(p, 'CSS 资源');
    if (!uri) return full;
    cssCount++;
    return `url("${uri}")`;
  });
  return `<style>\n/* packed from ${m[1]} */\n${css}\n</style>`;
});

html = html.replace(/<img([^>]*?)src=["']([^"']+)["']/gi, (full, pre, src) => {
  if (/^(data:|https?:)/.test(src)) return full;
  const p = resolveRef(src, '图片');
  if (!p) return full;
  const uri = toDataUri(p, '图片');
  if (!uri) return full;
  imgCount++;
  return `<img${pre}src="${uri}"`;
});

/* ── 交付前检查（"出错不写盘"）────────────────────── */
if (!/<title>[^<]+<\/title>/i.test(html)) errors.push('缺少 <title>：标签页和分享卡片都靠它');
const ids = new Map();
for (const m of html.matchAll(/\sid=["']([^"']+)["']/g)) {
  const line = html.slice(0, m.index).split('\n').length;
  if (ids.has(m[1])) errors.push(`id="${m[1]}" 重复（第 ${ids.get(m[1])} 行与第 ${line} 行）`);
  else ids.set(m[1], line);
}

if (errors.length) {
  console.error(`\n✖ ${errors.length} 个问题，未写盘：`);
  for (const e of errors) console.error('  · ' + e);
  process.exit(1);
}

if (dryRun) {
  console.log(`\n✔ 检查通过（--dry-run 未写盘）  将内联 CSS 资源 ${cssCount} 个 / 图片 ${imgCount} 个`);
  process.exit(0);
}

fs.writeFileSync(output, html);
const kb = (n) => (n / 1024).toFixed(0) + ' KB';
console.log(`\n✔ ${path.basename(output)}  ${kb(Buffer.byteLength(html))}`);
console.log(`  内联样式表 / CSS 资源 ${cssCount} 个 / 图片 ${imgCount} 个`);
console.log(`  自包含：拷到任何目录、单独发给别人都能直接打开\n`);
