#!/usr/bin/env node
/**
 * gate.mjs — 一条命令跑完交付验证链
 *
 *   node scripts/gate.mjs deck.html [--plan plan.json] [--out gate.json]
 *        [--preview dir] [--pptx deck.pptx] [--compat v2] [--strict]
 *        [--skip-render] [--allow-forbid]
 *
 * 顺序：doctor → plan check → validate → audit-text → render --sheet
 *       → build → verify-pptx → verify-render（有 LO 才跑）→ 写 gate.json
 * 任一失败 exit 1；没跑完 gate 不算交付。
 */
import fs from 'node:fs';
import path from 'node:path';
import os from 'node:os';
import { spawnSync } from 'node:child_process';

const ROOT = path.resolve(import.meta.dirname, '..');
const argv = process.argv.slice(2);
const getArg = (name, fallback) => {
  let i = argv.indexOf(`--${name}`);
  return i === -1 ? fallback : (argv[i + 1] && !argv[i + 1].startsWith('--') ? argv[++i] : true);
};
const has = (name) => argv.includes(`--${name}`);

const deck = argv.find((a) => !a.startsWith('-'));
if (!deck) {
  console.error('用法: node scripts/gate.mjs <deck.html> [--plan plan.json] [--out gate.json]');
  process.exit(2);
}
const deckPath = path.resolve(deck);
if (!fs.existsSync(deckPath)) {
  console.error(`✖ 找不到 deck：${deckPath}`);
  process.exit(2);
}
const dir = path.dirname(deckPath);
const planPath = getArg('plan', null) ? path.resolve(getArg('plan')) : null;
const outPath = path.resolve(getArg('out', path.join(dir, 'gate.json')));
const preview = path.resolve(getArg('preview', path.join(dir, 'preview')));
const pptx = path.resolve(getArg('pptx', path.join(dir, 'deck.pptx')));
const compat = getArg('compat', null);
// 默认 strict：SKILL.md 声称 gate 是「总门禁、全绿」，非 strict 下 validate/audit-text
// 的 warn 一律放行，等于把总门禁降级成提示汇总。要放宽必须显式 --no-strict。
const strict = argv.includes('--no-strict') ? false : true;
const skipRender = has('skip-render');
const allowForbid = has('allow-forbid');
const requireLo = has('require-render');

// 版本单一真相源：读 scripts/package.json，不再在代码里硬编码（曾与包版本漂移三版）
const PKG_VERSION = JSON.parse(
  fs.readFileSync(path.join(ROOT, 'scripts/package.json'), 'utf8'),
).version;

const html = fs.readFileSync(deckPath, 'utf8');
const pages = (html.match(/<section\b[^>]*class=["'][^"']*\bslide\b/g) || []).length;

const steps = [];
function record(name, code, started, extra = {}) {
  steps.push({ name, code, ok: code === 0, ms: Date.now() - started, ...extra });
  if (code !== 0) {
    finish(false);
  }
}
function finish(ok) {
  const data = {
    version: PKG_VERSION,
    ok,
    strict,
    deck: deckPath,
    plan: planPath,
    pages,
    generatedAt: new Date().toISOString(),
    node: process.versions.node,
    steps,
    artifacts: { preview, pptx, pptxRender: path.join(dir, 'pptx-render'), render: path.join(dir, 'render') },
  };
  fs.writeFileSync(outPath, JSON.stringify(data, null, 2));
  console.log(`\n${ok ? '✔ gate 通过' : '✖ gate 未通过'} → ${outPath}\n`);
  process.exit(ok ? 0 : 1);
}
function run(name, args, extra = {}) {
  const started = Date.now();
  console.log(`\n── ${name} ─────────────────────────────`);
  const r = spawnSync(process.execPath, args, { cwd: ROOT, stdio: 'inherit' });
  record(name, r.status ?? 1, started, extra);
}

// 0. 环境
run('doctor', ['scripts/doctor.mjs', ...(requireLo ? ['--require-lo'] : [])]);

// 1. 结构化：≥8 页必须有 plan
if (pages >= 8 && !planPath) {
  console.error(`\n✖ ${pages} 页的 deck 必须先有 plan.json（scaffold 的输入），再交付。`);
  console.error('  用 node scripts/plan.mjs check plan.json，然后 node scripts/scaffold.mjs plan.json -o deck.html');
  finish(false);
}
if (planPath) {
  if (!fs.existsSync(planPath)) {
    console.error(`✖ 找不到 plan：${planPath}`);
    finish(false);
  }
  run('plan-check', ['scripts/plan.mjs', 'check', planPath, ...(strict ? ['--strict'] : [])]);
  run('plan-deck', ['scripts/plan.mjs', 'check', '--deck', deckPath, '--plan', planPath]);
}

// 2. 版式与内容
run('validate', ['scripts/validate.mjs', deckPath, ...(strict ? ['--strict'] : []), ...(compat ? ['--compat', compat] : []), ...(allowForbid ? ['--allow-forbid'] : [])]);
run('audit-text', ['scripts/audit-text.mjs', deckPath, ...(strict ? ['--strict'] : [])]);

// 3. 预览 + 编译
run('render', ['scripts/render.mjs', deckPath, '--out', preview, '--sheet']);
run('build', ['scripts/build-deck.mjs', deckPath, '-o', pptx, ...(allowForbid ? ['--allow-forbid'] : [])]);
run('verify-pptx', ['scripts/verify-pptx.mjs', pptx, '--out', path.join(dir, 'pptx-render'), '--vs', preview]);

// 4. 真渲染（可选）
const hasLo = !!([
  process.env.CST_SOFFICE,
  path.join(os.homedir(), 'opt/lo-deb/soffice'),
  path.join(os.homedir(), 'opt/libreoffice/squashfs-root/AppRun'),
  '/usr/bin/soffice',
  '/usr/bin/libreoffice',
].filter(Boolean).find((p) => { try { return fs.existsSync(p); } catch { return false; } }));
if (!skipRender && hasLo) {
  run('verify-render', ['scripts/verify-render.mjs', pptx, '--out', path.join(dir, 'render'), '--vs', preview, '--compare-width', '640', '--compare-height', '360']);
} else if (!skipRender) {
  console.log('\n▸ verify-render：未安装 LibreOffice，标记 skipped（gate.json 里不记为通过）');
  steps.push({ name: 'verify-render', code: null, ok: null, ms: 0, skipped: true });
}

finish(true);
