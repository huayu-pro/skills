#!/usr/bin/env node
/**
 * run.mjs — evals 的运行器
 *
 *   node evals/run.mjs --list
 *   node evals/run.mjs --pipeline [case]       # 确定性断言（不需要 agent）
 *   node evals/run.mjs --agent <case> --dir <产物目录>
 *   node evals/run.mjs --score                 # TRACE 四态汇总
 *   node evals/run.mjs --update-baseline <case> --reason "…"
 *
 * 判据只断言可观察产物。03/07 的“拒绝是否得体 / 触发了没有”留人工。
 * INCOMPLETE 不等于通过；--require-complete 会把待人工也算失败。
 */
import fs from 'node:fs';
import path from 'node:path';
import os from 'node:os';
import crypto from 'node:crypto';
import { execFileSync } from 'node:child_process';

const ROOT = path.resolve(import.meta.dirname, '..');
const HERE = import.meta.dirname;
const argv = process.argv.slice(2);
const flag = (name) => {
  let i = argv.indexOf(`--${name}`);
  return i === -1 ? null : (argv[i + 1] && !argv[i + 1].startsWith('--') ? argv[++i] : true);
};
const has = (name) => argv.includes(`--${name}`);

const NODE = process.execPath;
const CASES_META = {
  '00-converter': { dims: ['T', 'R'], desc: 'FORBID 全量、写盘前失败、data URI' },
  '01-normal': { dims: ['E', 'C'], desc: '结构完整、验证链、文字真可编辑' },
  '02-edge': { dims: ['R', 'E'], desc: '色板豁免、圆描边、单行正文、竖排' },
  '03-negative': { dims: ['A'], desc: '不该出活时不出活' },
  '04-recovery': { dims: ['R'], desc: '坏 deck 的检测/修复' },
  '05-delivery': { dims: ['C', 'E'], desc: 'pptx/预览/联系表/真渲染' },
  '06-structure': { dims: ['R', 'C', 'E'], desc: 'plan→scaffold→validate→build、确定性、坏 plan' },
  '07-trigger': { dims: ['A'], desc: '正例与近义负例（人工）' },
  '08-pack-security': { dims: ['T'], desc: 'pack-html 正白名单、隐藏路径、非 HTML 输入' },
};
const DIMS = {
  T: ['00-converter', '01-normal', '08-pack-security'],
  R: ['00-converter', '02-edge', '04-recovery', '06-structure'],
  A: ['03-negative', '07-trigger'],
  C: ['01-normal', '05-delivery', '06-structure'],
  E: ['01-normal', '02-edge', '05-delivery', '06-structure'],
};

function listCases() {
  return fs.readdirSync(path.join(HERE, 'cases'), { withFileTypes: true })
    .filter((d) => d.isDirectory())
    .map((d) => d.name)
    .sort();
}

function run(cmdline) {
  const r = { code: 0, stdout: '', stderr: '' };
  try {
    r.stdout = execFileSync('/bin/bash', ['-lc', cmdline], {
      encoding: 'utf8', cwd: ROOT, maxBuffer: 64e6,
    });
  } catch (err) {
    r.code = err.status ?? 1;
    r.stdout = err.stdout || '';
    r.stderr = err.stderr || '';
  }
  return r;
}

/* ── 断言工具 ─────────────────────────────────────────────── */
function fileAssert(p, minBytes = 1) {
  const exists = fs.existsSync(p);
  const size = exists ? fs.statSync(p).size : 0;
  return { ok: exists && size >= minBytes, expected: `存在且 ≥${minBytes}B`, actual: exists ? `${size}B` : '不存在', detail: p };
}
function sizeAssert(p, max) {
  const size = fs.existsSync(p) ? fs.statSync(p).size : 0;
  return { ok: size > 0 && size <= max, expected: `≤${Math.round(max / 1024)}KB`, actual: `${Math.round(size / 1024)}KB`, detail: p };
}
function exitAssert(code, expected, detail = '') {
  return { ok: code === expected, expected: `exit ${expected}`, actual: `exit ${code}`, detail: String(detail).slice(0, 400) };
}
function textAssert(text, needle, id, expected = `包含「${needle}」`) {
  return { id, ok: String(text).includes(needle), expected, actual: String(text).includes(needle) ? '有' : '没有', detail: needle };
}
function counts(pptx) {
  if (!fs.existsSync(pptx)) return { runs: 0, sps: 0, pages: 0 };
  const list = execFileSync('unzip', ['-l', pptx], { encoding: 'utf8' });
  const slides = [...list.matchAll(/ppt\/slides\/slide(\d+)\.xml/g)].map((m) => Number(m[1]));
  let runs = 0, sps = 0;
  for (const n of slides) {
    const xml = execFileSync('unzip', ['-p', pptx, `ppt/slides/slide${n}.xml`], { encoding: 'utf8', maxBuffer: 64e6 });
    runs += (xml.match(/<a:t>/g) || []).length;
    sps += (xml.match(/<p:sp>/g) || []).length;
  }
  return { runs, sps, pages: slides.length };
}
function sectionCount(htmlPath) {
  const html = fs.readFileSync(htmlPath, 'utf8');
  return (html.match(/<section\b[^>]*class=["'][^"']*\bslide\b/g) || []).length;
}
function findSoffice() {
  return [
    process.env.CST_SOFFICE,
    path.join(os.homedir(), 'opt/lo-deb/soffice'),
    path.join(os.homedir(), 'opt/libreoffice/squashfs-root/AppRun'),
    '/usr/bin/soffice',
    '/usr/bin/libreoffice',
  ].filter(Boolean).find((p) => { try { return fs.existsSync(p); } catch { return false; } });
}
function sha(p) {
  return crypto.createHash('sha256').update(fs.readFileSync(p)).digest('hex');
}

/* ── cases ────────────────────────────────────────────────── */
const CASES = {
  '00-converter': (work) => {
    const fixture = path.join(work.dir, 'fixture.html');
    const pptx = path.join(work.out, 'must-not-exist.pptx');
    fs.rmSync(pptx, { force: true });
    const r = run(`${NODE} scripts/build-deck.mjs "${fixture}" -o "${pptx}" --check`);
    const out = r.stdout + r.stderr;
    const ids = ['gradient', 'shadow', 'filter', 'blend', 'zindex', 'fixed', 'pseudo',
      'nested', 'overflow', 'svg', 'transform', 'translate', 'clip', 'radius', 'remote'];
    const res = [
      { id: 'check-fails', ...exitAssert(r.code, 1, out) },
      { id: 'no-pptx-written', ok: !fs.existsSync(pptx), expected: '不留下 pptx', actual: fs.existsSync(pptx) ? '仍在' : '没有', detail: pptx },
      { id: 'no-reference-error', ok: !/ReferenceError/.test(out), expected: '没有 ReferenceError', actual: /ReferenceError/.test(out) ? '有' : '没有', detail: out.slice(0, 200) },
    ];
    for (const id of ids) res.push(textAssert(out, `FORBID:${id}`, `forbid-${id}`, `报出 FORBID:${id}`));
    return res;
  },

  '01-normal': (work) => {
    const src = fs.readFileSync(work.deck, 'utf8');
    const out = [
      { id: 'deck-exists', ...fileAssert(work.deck, 2000) },
      { id: 'page-count', ok: sectionCount(work.deck) >= 8, expected: '≥8 页', actual: `${sectionCount(work.deck)} 页`, detail: work.deck },
      { id: 'notes-per-page', ok: (src.match(/data-notes=/g) || []).length >= sectionCount(work.deck), expected: '每页 data-notes', actual: `${(src.match(/data-notes=/g) || []).length} 处`, detail: work.deck },
    ];
    out.push({ id: 'validate-clean', ...exitAssert(run(`${NODE} scripts/validate.mjs "${work.deck}"`).code, 0) });
    out.push({ id: 'audit-clean', ...exitAssert(run(`${NODE} scripts/audit-text.mjs "${work.deck}"`).code, 0) });
    out.push({ id: 'selfcheck-clean', ...exitAssert(run(`${NODE} scripts/selfcheck.mjs`).code, 0) });

    const pptx = path.join(work.out, 'deck.pptx');
    const build = run(`${NODE} scripts/build-deck.mjs "${work.deck}" -o "${pptx}" --preview --spec "${path.join(work.out, 'deck.spec.json')}"`);
    out.push({ id: 'build-ok', ...exitAssert(build.code, 0, build.stdout + build.stderr) });
    out.push({ id: 'no-forbid', ok: !/FORBID:/.test(build.stdout + build.stderr), expected: '无 FORBID', actual: /FORBID:/.test(build.stdout + build.stderr) ? '有' : '无', detail: build.stdout });
    out.push({ id: 'pptx-exists', ...fileAssert(pptx, 20000) });
    const c = counts(pptx);
    out.push({ id: 'text-editable', ok: c.runs >= 40, expected: '≥40 <a:t>', actual: `${c.runs}`, detail: pptx });
    out.push({ id: 'shapes-native', ok: c.sps >= 20, expected: '≥20 <p:sp>', actual: `${c.sps}`, detail: pptx });
    return out;
  },

  '02-edge': (work) => {
    const html = path.join(work.dir, 'fixture.html');
    const src = fs.readFileSync(html, 'utf8');
    const out = [
      { id: 'has-sun-outline', ok: src.includes('sun--outline'), expected: '用到 .sun--outline', actual: src.includes('sun--outline') ? '是' : '否', detail: html },
      { id: 'has-palette-ok', ok: /data-palette-ok/.test(src), expected: '色板页加 data-palette-ok', actual: /data-palette-ok/.test(src) ? '是' : '否', detail: html },
      { id: 'has-lead-grid', ok: src.includes('grid4--lead'), expected: '用到 1.9fr 首栏', actual: src.includes('grid4--lead') ? '是' : '否', detail: html },
    ];
    const specPath = path.join(work.out, 'deck.spec.json');
    const build = run(`${NODE} scripts/build-deck.mjs "${html}" -o "${path.join(work.out, 'deck.pptx')}" --spec "${specPath}"`);
    out.push({ id: 'build-ok', ...exitAssert(build.code, 0, build.stdout + build.stderr) });
    if (fs.existsSync(specPath)) {
      const spec = JSON.parse(fs.readFileSync(specPath, 'utf8'));
      const texts = spec.slides.flatMap((s) => s.shapes.filter((x) => x.kind === 'text'));
      const p = spec.slides.find((s) => s.shapes.some((x) => x.kind === 'ellipse' && x.outline));
      const thin = p ? p.shapes.filter((x) => x.kind === 'rect'
        && (x.h === 10 || x.w === 10) && (x.w >= 150 || x.h >= 150)).length : 999;
      out.push({ id: 'sun-outline-not-squared', ok: p ? thin === 0 : false, expected: '圆不派生 4 条 10px 直条', actual: p ? `${thin} 条` : '没找到带 outline 的圆', detail: specPath });
      const single = texts.find((x) => x.paragraphs.flatMap((q) => q.runs).map((r) => r.text).join('').includes('这一行只有一次折行'));
      out.push({ id: 'single-line-body-wraps', ok: !!single && single.wrap === true && single.lines === 1, expected: '单行正文 wrap=true / 1 行', actual: single ? `wrap=${single.wrap} lines=${single.lines}` : '没找到', detail: specPath });
      const v = texts.find((x) => x.paragraphs.flatMap((q) => q.runs).map((r) => r.text).join('').includes('SERIAL EXPERIMENTS'));
      out.push({ id: 'vertical-text-tall', ok: !!v && v.vertical && v.h > v.w, expected: '竖排 h > w', actual: v ? `w=${v.w} h=${v.h} vertical=${v.vertical}` : '没找到', detail: specPath });
      const display = texts.filter((x) => !x.wrap && x.w < 400);
      out.push({ id: 'display-text-nowrap', ok: display.length > 0, expected: '展示字 wrap=false', actual: `${display.length} 个`, detail: specPath });
    }
    const val = run(`${NODE} scripts/validate.mjs "${html}"`);
    out.push({ id: 'validate-clean-with-exemption', ok: val.code === 0, expected: 'data-palette-ok 生效后 exit 0', actual: `exit ${val.code}`, detail: val.stdout + val.stderr });
    return out;
  },

  '03-negative': (work) => {
    const replyPath = work.reply || path.join(work.out, 'reply.md');
    if (!fs.existsSync(replyPath)) {
      return [{ id: 'needs-agent-run', ok: null, expected: '需 --agent 提供 reply.md', actual: '未提供', detail: replyPath }];
    }
    const pptxs = fs.existsSync(work.out) ? fs.readdirSync(work.out).filter((f) => f.endsWith('.pptx')) : [];
    const reply = fs.readFileSync(replyPath, 'utf8');
    return [
      { id: 'no-artifact', ok: pptxs.length === 0, expected: '0 个 .pptx', actual: `${pptxs.length} 个`, detail: work.out },
      { id: 'refusal-stated', ok: /不适合|不建议|别再|硬套|换一种|不推荐/.test(reply), expected: '明确说不适合', actual: /不适合|不建议|别再|硬套|换一种|不推荐/.test(reply) ? '有' : '没有', detail: replyPath },
      { id: 'alternative-offered', ok: /表格|报表|数据页|常规版式|商务|逐条|年报/.test(reply), expected: '给替代方向', actual: /表格|报表|数据页|常规版式|商务|逐条|年报/.test(reply) ? '有' : '没有', detail: replyPath },
      { id: 'manual-review', ok: null, expected: '人工盲评：拒绝是否得体', actual: '需人工', detail: '脚本不判好坏' },
    ];
  },

  '04-recovery': (work) => {
    const fixture = path.join(work.dir, 'fixture.html');
    const fixed = path.join(work.dir, 'fixed.html');
    // --agent 模式：agent 产出 fixed.html；--pipeline 模式：只验检测，不自动修
    if (!fs.existsSync(fixed)) {
      const r = run(`${NODE} scripts/validate.mjs "${fixture}"`);
      const out = r.stdout + r.stderr;
      return [
        { id: 'detects-bad-deck', ...exitAssert(r.code, 1, out) },
        textAssert(out, '[CLASS', 'detect-class'),
        textAssert(out, '[WEIGHT', 'detect-weight'),
        textAssert(out, '[FORBID', 'detect-forbid'),
        textAssert(out, '[BOUNDS', 'detect-bounds'),
        { id: 'not-empty', ok: !/0 页/.test(out), expected: '不是 0 页', actual: /0 页/.test(out) ? '0 页' : '有页', detail: out.slice(0, 200) },
      ];
    }
    const out = [];
    out.push({ id: 'validate-clean', ...exitAssert(run(`${NODE} scripts/validate.mjs "${fixed}"`).code, 0) });
    const src = fs.readFileSync(fixed, 'utf8');
    out.push({ id: 'no-ghost-class', ok: !/quote-mark/.test(src), expected: '幽灵类已移除', actual: /quote-mark/.test(src) ? '仍在' : '已移除', detail: fixed });
    out.push({ id: 'no-hairline', ok: !/border:\s*1px/.test(src) && !/height:\s*1px/.test(src), expected: '1px 线已移除', actual: /border:\s*1px|height:\s*1px/.test(src) ? '仍在' : '已移除', detail: fixed });
    out.push({ id: 'no-inline-svg', ok: !/<svg/.test(src), expected: '内联 svg 已移除', actual: /<svg/.test(src) ? '仍在' : '已移除', detail: fixed });
    const cjk = (src.match(/[\u4e00-\u9fa5]/g) || []).length;
    const cjk0 = (fs.readFileSync(fixture, 'utf8').match(/[\u4e00-\u9fa5]/g) || []).length;
    out.push({ id: 'content-preserved', ok: cjk0 === 0 || cjk / cjk0 >= 0.9, expected: `≥90% 汉字保留（${cjk0}）`, actual: cjk0 === 0 ? '原文件无汉字' : `${cjk}/${cjk0}`, detail: fixed });
    return out;
  },

  '05-delivery': (work) => {
    const out = [];
    const preview = path.join(work.out, 'preview');
    fs.rmSync(preview, { recursive: true, force: true });
    const render = run(`${NODE} scripts/render.mjs "${work.deck}" --out "${preview}" --sheet`);
    out.push({ id: 'render-ok', ...exitAssert(render.code, 0, render.stdout + render.stderr) });
    const pptx = path.join(work.out, 'deck.pptx');
    const build = run(`${NODE} scripts/build-deck.mjs "${work.deck}" -o "${pptx}"`);
    out.push({ id: 'build-ok', ...exitAssert(build.code, 0, build.stdout + build.stderr) });
    out.push({ id: 'no-forbid', ok: !/FORBID:/.test(build.stdout + build.stderr), expected: '无 FORBID', actual: /FORBID:/.test(build.stdout + build.stderr) ? '有' : '无', detail: build.stdout });
    out.push({ id: 'pptx-exists', ...fileAssert(pptx, 20000) });
    out.push({ id: 'pptx-size', ...sizeAssert(pptx, 1.5 * 1024 * 1024) });
    const pages = counts(pptx).pages;
    const imgs = fs.existsSync(preview) ? fs.readdirSync(preview).filter((f) => /^slide-\d+\.png$/.test(f)).length : 0;
    out.push({ id: 'preview-equals-pages', ok: pages > 0 && imgs === pages, expected: `预览张数 == pptx 页数（${pages}）`, actual: `${imgs} 张`, detail: preview });
    const sheet = path.join(preview, 'contact-sheet.png');
    out.push({ id: 'contact-sheet-fresh', ok: fs.existsSync(sheet) && fs.statSync(sheet).mtimeMs >= fs.statSync(work.deck).mtimeMs, expected: '联系表存在且新于 deck', actual: fs.existsSync(sheet) ? '存在' : '没有', detail: sheet });
    const replyPath = work.reply || path.join(work.out, 'reply.md');
    if (fs.existsSync(replyPath)) {
      const reply = fs.readFileSync(replyPath, 'utf8');
      out.push({ id: 'reply-editable', ok: /可编辑|原生|文本框|改字/.test(reply), expected: '说明哪些可编辑', actual: /可编辑|原生|文本框|改字/.test(reply) ? '有' : '没有', detail: replyPath });
      out.push({ id: 'reply-images', ok: /图片|PNG|栅格|raster/.test(reply), expected: '说明哪些是图', actual: /图片|PNG|栅格|raster/.test(reply) ? '有' : '没有', detail: replyPath });
    } else {
      out.push({ id: 'needs-agent-run', ok: null, expected: '需 --agent 提供 reply.md', actual: '未提供', detail: replyPath });
    }
    const c = counts(pptx);
    out.push({ id: 'text-editable', ok: c.runs >= 40, expected: '≥40 <a:t>', actual: `${c.runs}`, detail: pptx });
    if (findSoffice()) {
      const rr = run(`${NODE} scripts/verify-render.mjs "${pptx}" --out "${path.join(work.out, 'render')}" --vs "${preview}" --compare-width 640 --compare-height 360`);
      out.push({ id: 'verify-render', ok: rr.code === 0, expected: '每页 ≤12%', actual: `exit ${rr.code}`, detail: rr.stdout + rr.stderr });
    } else {
      out.push({ id: 'verify-render', ok: null, expected: '未安装 LO，标 skipped', actual: 'skipped', detail: '不记为 pass' });
    }
    return out;
  },

  '06-structure': (work) => {
    const out = [];
    const plan = path.join(ROOT, 'examples', 'plan.json');
    const deck = path.join(ROOT, 'examples', 'structured.html');
    out.push({ id: 'plan-valid', ...exitAssert(run(`${NODE} scripts/plan.mjs check "${plan}" --strict`).code, 0) });
    out.push({ id: 'plan-deck-binding', ...exitAssert(run(`${NODE} scripts/plan.mjs check --deck "${deck}" --plan "${plan}"`).code, 0) });
    out.push({ id: 'validate-clean', ...exitAssert(run(`${NODE} scripts/validate.mjs "${deck}" --strict`).code, 0) });
    out.push({ id: 'audit-clean', ...exitAssert(run(`${NODE} scripts/audit-text.mjs "${deck}" --strict`).code, 0) });
    const a = path.join(work.out, 'scaffold-a.html');
    const b = path.join(work.out, 'scaffold-b.html');
    const s1 = run(`${NODE} scripts/scaffold.mjs "${plan}" -o "${a}" --force`);
    const s2 = run(`${NODE} scripts/scaffold.mjs "${plan}" -o "${b}" --force`);
    out.push({ id: 'scaffold-ok', ...exitAssert(s1.code, 0, s1.stdout + s1.stderr) });
    out.push({ id: 'scaffold-deterministic', ok: s2.code === 0 && fs.existsSync(a) && fs.existsSync(b) && sha(a) === sha(b), expected: '两次输出字节一致', actual: fs.existsSync(a) && fs.existsSync(b) ? (sha(a) === sha(b) ? '一致' : '不一致') : '缺文件', detail: work.out });
    const src = fs.readFileSync(deck, 'utf8');
    const pages = sectionCount(deck);
    const planIds = (src.match(/data-plan-id=/g) || []).length;
    const roles = (src.match(/data-role=/g) || []).length;
    const layouts = (src.match(/data-layout=/g) || []).length;
    out.push({ id: 'all-pages-bound', ok: pages > 0 && planIds === pages && roles === pages && layouts === pages, expected: `${pages} 页都有 plan-id/role/layout`, actual: `${planIds}/${roles}/${layouts}`, detail: deck });
    const check = run(`${NODE} scripts/build-deck.mjs "${deck}" -o "${path.join(work.out, 'structured.pptx')}" --check`);
    out.push({ id: 'build-check-ok', ...exitAssert(check.code, 0, check.stdout + check.stderr) });

    // 坏 plan：每个都必须被拒绝，并给出对应的原因
    const base = JSON.parse(fs.readFileSync(plan, 'utf8'));
    const clone = () => JSON.parse(JSON.stringify(base));
    const badDir = path.join(work.out, 'bad');
    fs.mkdirSync(badDir, { recursive: true });
    const badPlans = [];
    const p1 = clone(); p1.slides[0].role = 'method'; p1.slides[0].layout = 'L01'; badPlans.push(['role-mismatch', p1, '不支持 role']);
    const p2 = clone(); delete p2.slides[0].slots.title1; badPlans.push(['missing-slot', p2, '缺必填槽位']);
    const p3 = clone(); p3.slides[0].slots.title1 = '构成主义构成主义构成主义构成主义构成主义'; badPlans.push(['over-budget', p3, '超过']);
    const p4 = clone(); p4.slides[1].claim = p4.slides[0].claim; badPlans.push(['duplicate-claim', p4, '重复']);
    const p5 = clone(); p5.durationMin = 60; badPlans.push(['minutes-drift', p5, '相差']);
    const p6 = clone();
    const l06 = p6.slides[3];
    p6.slides[1] = { ...JSON.parse(JSON.stringify(l06)), id: 's02', role: 'context', minutes: 2, claim: '连续版式测试一' };
    p6.slides[2] = { ...JSON.parse(JSON.stringify(l06)), id: 's03', role: 'thesis', minutes: 2, claim: '连续版式测试二' };
    badPlans.push(['layout-run', p6, '连续']);
    for (const [name, obj, needle] of badPlans) {
      const f = path.join(badDir, `${name}.json`);
      fs.writeFileSync(f, JSON.stringify(obj, null, 2));
      const r = run(`${NODE} scripts/plan.mjs check "${f}"`);
      const text = r.stdout + r.stderr;
      out.push({
        id: `bad-${name}`,
        ok: r.code === 1 && text.includes(needle),
        expected: `exit 1 且包含「${needle}」`,
        actual: `exit ${r.code}`,
        detail: text.slice(0, 300),
      });
    }
    // plan↔deck 漂移：删掉一页
    const broken = path.join(work.out, 'broken.html');
    fs.writeFileSync(broken, src.replace(/<section\b[\s\S]*?<\/section>/, ''));
    const drift = run(`${NODE} scripts/plan.mjs check --deck "${broken}" --plan "${plan}"`);
    out.push({ id: 'plan-deck-drift', ok: drift.code === 1, expected: '删页后 plan↔deck 失败', actual: `exit ${drift.code}`, detail: drift.stdout + drift.stderr });
    return out;
  },

  '08-pack-security': (work) => {
    const dir = path.join(work.out, 'fixture');
    fs.rmSync(dir, { recursive: true, force: true });
    fs.mkdirSync(path.join(dir, '.hidden'), { recursive: true });
    fs.writeFileSync(path.join(dir, 'deck.html'), '<!doctype html><html><head><title>pack security</title></head><body><img src="asset.xyz"><img src=".hidden/asset.png"></body></html>');
    fs.writeFileSync(path.join(dir, 'asset.xyz'), 'dummy');
    fs.writeFileSync(path.join(dir, '.hidden', 'asset.png'), 'dummy');
    const bad = run(`${NODE} scripts/pack-html.mjs "${path.join(dir, 'deck.html')}" --dry-run`);
    const badOut = bad.stdout + bad.stderr;
    const badInput = run(`${NODE} scripts/pack-html.mjs "${path.join(dir, 'asset.xyz')}"`);
    const badInputOut = badInput.stdout + badInput.stderr;
    const good = run(`${NODE} scripts/pack-html.mjs "examples/structured.html" --dry-run`);
    return [
      { id: 'reject-non-asset', ...exitAssert(bad.code, 1, badOut) },
      textAssert(badOut, '允许的图片/字体/样式扩展名', 'allowlist-message'),
      textAssert(badOut, '隐藏路径段', 'hidden-path-message'),
      { id: 'no-packed-output', ok: !fs.existsSync(path.join(dir, 'deck.packed.html')), expected: '失败不写盘', actual: fs.existsSync(path.join(dir, 'deck.packed.html')) ? '仍在' : '没有', detail: dir },
      { id: 'reject-non-html-input', ...exitAssert(badInput.code, 2, badInputOut) },
      textAssert(badInputOut, '输入必须是存在的 .html/.htm 文件', 'non-html-message'),
      { id: 'normal-deck-packs', ...exitAssert(good.code, 0, good.stdout + good.stderr) },
    ];
  },

  '07-trigger': (work) => {
    const replyPath = work.reply || path.join(work.out, 'reply.md');
    if (!fs.existsSync(replyPath)) {
      return [{ id: 'needs-agent-run', ok: null, expected: '需按 task.md 跑正例/负例并给 reply.md', actual: '未提供', detail: replyPath }];
    }
    return [
      { id: 'manual-trigger-review', ok: null, expected: '人工/agent 对正例与近义负例逐条记录', actual: '需人工', detail: replyPath },
    ];
  },
};

/* ── 报告与运行 ───────────────────────────────────────────── */
function report(caseName, results) {
  console.log(`\n── ${caseName} ─────────────────────────────`);
  let bad = 0;
  for (const r of results) {
    const mark = r.ok === true ? '✓' : r.ok === false ? '✖' : '○';
    if (r.ok === false) bad++;
    console.log(`  ${mark} ${r.id.padEnd(30)} ${r.expected || ''}`);
    if (r.ok === false) console.log(`      actual: ${r.actual}`);
    if (r.ok !== true && r.detail) console.log(`      detail: ${String(r.detail).slice(0, 140)}`);
  }
  const unknown = results.filter((r) => r.ok === null).length;
  console.log(`  ${results.length - bad - unknown}/${results.length - unknown} 通过，${bad} 失败，${unknown} 待人工`);
  return { bad, unknown };
}

function runCase(name, work) {
  try {
    const results = CASES[name](work);
    const summary = report(name, results);
    return { name, results, ...summary };
  } catch (err) {
    console.log(`\n── ${name} ── 抛出：${err.message}`);
    return { name, results: [{ id: 'exception', ok: false, expected: '不抛异常', actual: err.message, detail: err.stack }], bad: 1, unknown: 0 };
  }
}

function caseWork(name) {
  const out = path.join(HERE, 'runs', name);
  fs.mkdirSync(out, { recursive: true });
  const dir = path.join(HERE, 'cases', name);
  const base = {
    dir, out, reply: path.join(out, 'reply.md'),
    deck: path.join(ROOT, 'examples', 'constructivism.html'),
    pptx: path.join(out, 'deck.pptx'),
    preview: path.join(out, 'preview'),
  };
  if (name === '02-edge') base.deck = path.join(dir, 'fixture.html');
  if (name === '05-delivery') base.deck = path.join(ROOT, 'examples', 'constructivism.html');
  return base;
}

function pipeline(caseName) {
  const names = caseName ? [caseName] : listCases().filter((n) => CASES[n]);
  const runs = [];
  for (const n of names) {
    if (!CASES[n]) continue;
    runs.push(runCase(n, caseWork(n)));
  }
  const totalBad = runs.reduce((n, r) => n + r.bad, 0);
  const incomplete = runs.reduce((n, r) => n + r.unknown, 0);
  const blocked = totalBad || (has('require-complete') && incomplete);
  console.log(blocked
    ? `\npipeline 未通过：${totalBad} 项失败，${incomplete} 项待人工${has('require-complete') ? '（--require-complete 下待人工算失败）' : ''}`
    : '\npipeline 全部通过');
  if (has('score')) scorecard(runs);
  return { runs, totalBad };
}

function statusOf(run) {
  if (run.results.some((r) => r.ok === false)) return 'FAIL';
  if (run.results.some((r) => r.ok === null)) return 'INCOMPLETE';
  return 'PASS';
}

function scorecard(runs) {
  const byName = new Map(runs.map((r) => [r.name, r]));
  console.log('\nTRACE 记分卡');
  console.log('  维度  状态        证据');
  for (const [dim, cases] of Object.entries(DIMS)) {
    const statuses = cases.map((c) => (byName.has(c) ? statusOf(byName.get(c)) : 'INCOMPLETE'));
    const status = statuses.includes('FAIL') ? 'FAIL' : statuses.includes('INCOMPLETE') ? 'INCOMPLETE' : 'PASS';
    const detail = cases.map((c, i) => `${c}:${statuses[i]}`).join(' ');
    console.log(`  ${dim}     ${status.padEnd(10)} ${detail}`);
  }
  const incomplete = runs.reduce((n, r) => n + r.unknown, 0);
  const failed = runs.reduce((n, r) => n + r.bad, 0);
  console.log(`\n  自动通过 ${runs.length - failed - runs.filter((r) => r.unknown).length} 个 case，失败 ${failed}，待人工项 ${incomplete}`);
  console.log('  INCOMPLETE 不等于通过；--require-complete 会把它算失败。\n');
}

function updateBaseline(caseName, reason, repeats = 1) {
  const runs = [];
  for (let i = 0; i < repeats; i++) runs.push(runCase(caseName, caseWork(caseName)));
  const dir = path.join(HERE, 'baselines', caseName);
  fs.mkdirSync(dir, { recursive: true });
  const metrics = {
    case: caseName,
    updated: new Date().toISOString(),
    reason,
    repeats,
    results: runs.map((r) => ({ bad: r.bad, unknown: r.unknown, results: r.results.map(({ id, ok, expected, actual }) => ({ id, ok, expected, actual })) })),
  };
  fs.writeFileSync(path.join(dir, 'metrics.json'), JSON.stringify(metrics, null, 2));
  const log = path.join(HERE, 'baselines', 'CHANGELOG.md');
  const line = `- ${new Date().toISOString().slice(0, 10)} · ${caseName} · ${reason} · repeats=${repeats}\n`;
  fs.appendFileSync(log, fs.existsSync(log) ? line : `# Baseline CHANGELOG\n\n${line}`);
  console.log(`\n✔ baseline 已更新：${path.relative(ROOT, path.join(dir, 'metrics.json'))}`);
  return runs.some((r) => r.bad);
}

/* ── CLI ──────────────────────────────────────────────────── */
if (has('list')) {
  console.log(listCases().join('\n'));
  process.exit(0);
}

if (has('update-baseline')) {
  const name = flag('update-baseline');
  const reason = flag('reason');
  if (!name || name === true || !reason || reason === true) {
    console.error('用法: node evals/run.mjs --update-baseline <case> --reason "为什么改基线"');
    process.exit(2);
  }
  const rv = flag('repeats');
  const repeats = rv && rv !== true ? Math.max(1, parseInt(rv, 10) || 1) : 1;
  const failed = updateBaseline(name, reason, repeats);
  process.exit(failed ? 1 : 0);
}

if (has('pipeline') || has('score')) {
  const which = flag('pipeline');
  const { runs, totalBad } = pipeline(which && which !== true ? which : null);
  const incomplete = runs.reduce((n, r) => n + r.unknown, 0);
  process.exit(totalBad || (has('require-complete') && incomplete) ? 1 : 0);
} else if (has('agent')) {
  const which = flag('agent');
  const dir = flag('dir');
  if (!which || !dir) {
    console.error('用法: node evals/run.mjs --agent <case> --dir <产物目录>');
    process.exit(2);
  }
  const out = path.resolve(dir);
  const work = {
    dir: out, out, deck: path.join(out, 'deck.html'), pptx: path.join(out, 'deck.pptx'),
    preview: path.join(out, 'preview'), reply: path.join(out, 'reply.md'),
  };
  const r = runCase(which, work);
  process.exit(r.bad ? 1 : 0);
} else {
  console.log(`用法:
  node evals/run.mjs --list
  node evals/run.mjs --pipeline [case]
  node evals/run.mjs --agent <case> --dir <产物目录>
  node evals/run.mjs --score
  node evals/run.mjs --update-baseline <case> --reason "…" [--repeats N]`);
}
