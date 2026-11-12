#!/usr/bin/env node
/**
 * plan.mjs — 叙事计划的结构门禁
 *
 *   node scripts/plan.mjs check plan.json [--strict] [--json]
 *   node scripts/plan.mjs check --deck deck.html --plan plan.json [--json]
 *
 * 检查：页数/时长、角色顺序、版式轮换、版式↔角色、必填槽位、字数预算、
 * claim 重复、notes 完整、theme/substyle 一致、媒体文件存在。
 * --check-deck 还会比对 HTML 里的 data-plan-id/data-role/data-layout。
 */
import fs from 'node:fs';
import path from 'node:path';
import { loadLayouts, expandSlots, layoutById, planThresholds, SKILL_ROOT } from './lib/layouts.mjs';

/* 主题合法性以 themes.json 为准（单一真相源），这里不做任何点名 */
const THEMES = JSON.parse(fs.readFileSync(path.join(SKILL_ROOT, 'assets', 'themes.json'), 'utf8'));
const themeSubstyle = (id) => THEMES.themes[id]?.substyle || '';

const argv = process.argv.slice(2);
const has = (n) => argv.includes(`--${n}`);
const getArg = (n, d = null) => {
  let i = argv.indexOf(`--${n}`);
  return i === -1 ? d : (argv[i + 1] && !argv[i + 1].startsWith('--') ? argv[++i] : true);
};
const JSON_OUT = has('json');
const STRICT = has('strict');

if (argv[0] !== 'check') {
  console.error('用法: node scripts/plan.mjs check <plan.json> [--strict] [--json]');
  console.error('      node scripts/plan.mjs check --deck deck.html --plan plan.json');
  process.exit(2);
}

const planPath = path.resolve(getArg('plan') || argv.find((a) => !a.startsWith('-') && a !== 'check') || '');
if (!planPath || !fs.existsSync(planPath)) {
  console.error(`✖ 找不到 plan：${planPath || '(未提供)'}`);
  process.exit(2);
}
let cat;
try {
  cat = loadLayouts();
} catch (err) {
  console.error(`✖ ${err.message}`);
  process.exit(2);
}
const P = planThresholds(cat);
let plan;
try {
  plan = JSON.parse(fs.readFileSync(planPath, 'utf8'));
} catch (err) {
  console.error(`✖ plan 不是合法 JSON：${err.message}`);
  process.exit(2);
}

const issues = [];
const err = (msg, page = 0) => issues.push({ page, level: 'error', code: 'PLAN', msg });
const warn = (msg, page = 0) => issues.push({ page, level: 'warn', code: 'PLAN', msg });
const CJK = (s) => (String(s).match(/[\u4e00-\u9fa5]/g) || []).length;
const str = (s) => typeof s === 'string' && s.trim().length > 0;
const num = (n) => typeof n === 'number' && Number.isFinite(n);

/* ── 顶层 ───────────────────────────────────────────────────── */
if (plan.version !== 1) err('version 必须是 1');
if (!str(plan.title)) err('缺 title');
if (!str(plan.audience)) err('缺 audience');
if (!num(plan.durationMin) || plan.durationMin <= 0) err('durationMin 必须是正数');
if (!str(plan.theme) || !/^theme-[a-z][a-z0-9-]*$/.test(plan.theme) || !THEMES.themes[plan.theme]) err(`theme 非法：${plan.theme}`);
if (!['A', 'B', 'C'].includes(plan.substyle)) err('substyle 必须是 A/B/C');
if (plan.theme && plan.substyle) {
  if (themeSubstyle(plan.theme) !== plan.substyle) err(`substyle ${plan.substyle} 与 ${plan.theme} 不匹配`);
}
if (plan.axisDeg !== undefined && !num(plan.axisDeg)) err('axisDeg 必须是数字');
if (num(plan.axisDeg) && Math.abs(plan.axisDeg) > 20) warn(`主斜线 ${plan.axisDeg}° 超出 ±20° 的常规范围`);
if (num(plan.axisDeg) && Math.abs(plan.axisDeg) < 4) warn(`主斜线 ${plan.axisDeg}° 太小，读起来像画歪了`);

const slides = Array.isArray(plan.slides) ? plan.slides : [];
const n = slides.length;
if (n < P.hardMin) err(`页数 ${n} 少于硬下限 ${P.hardMin}`);
if (n > P.hardMax) err(`页数 ${n} 超过硬上限 ${P.hardMax}`);
if (n < P.minSlides) warn(`页数 ${n} 少于推荐下限 ${P.minSlides}；短稿可以不用 plan`);
if (n > P.maxSlides) warn(`页数 ${n} 超过推荐上限 ${P.maxSlides}`);

/* ── 逐页 ───────────────────────────────────────────────────── */
const ids = new Set();
const claims = new Map();
const layoutsSeen = [];
let totalMin = 0;

slides.forEach((s, i) => {
  const page = i + 1;
  const where = `第 ${page} 页`;
  if (!str(s.id)) err(`${where} 缺 id`, page);
  else if (ids.has(s.id)) err(`${where} id 重复：${s.id}`, page);
  else ids.add(s.id);
  if (!str(s.role)) err(`${where} 缺 role`, page);
  if (!str(s.layout)) err(`${where} 缺 layout`, page);
  if (!str(s.claim)) err(`${where} 缺 claim`, page);
  else {
    if (CJK(s.claim) > 40) warn(`${where} claim 超过 40 汉字，可能说了两件事`, page);
    const key = s.claim.replace(/\s+/g, '');
    if (claims.has(key)) err(`${where} claim 与第 ${claims.get(key)} 页重复`, page);
    else claims.set(key, page);
  }
  if (!num(s.minutes) || s.minutes <= 0) err(`${where} 缺 minutes（正数）`, page);
  else totalMin += s.minutes;
  if (s.theme && s.theme !== plan.theme) err(`${where} theme 与整份 plan 不一致`, page);
  if (s.axisDeg !== undefined && !num(s.axisDeg)) err(`${where} axisDeg 必须是数字`, page);

  const layout = layoutById(cat, s.layout);
  if (!layout) {
    err(`${where} layout "${s.layout}" 不在 layouts.json 里`, page);
    return;
  }
  layoutsSeen.push(layout);
  if (!layout.roles.includes(s.role)) {
    err(`${where} layout ${s.layout} 不支持 role "${s.role}"（支持：${layout.roles.join('/')}）`, page);
  }
  if (num(s.axisDeg) && s.axisDeg > 0 && layout.axisDegSign === 'negative') {
    warn(`${where} ${s.layout} 标记为 axisDegSign=negative：横置斜带几何只对负角安全，翻正角会压住标题区。要镜像方向就换骨架，或只调角度绝对值`, page);
  }

  const expected = expandSlots(layout);
  const slots = s.slots && typeof s.slots === 'object' ? s.slots : {};
  const groups = s.groups && typeof s.groups === 'object' ? s.groups : {};

  for (const [name, def] of expected) {
    if (name.includes('.')) continue; // group 槽位单独查
    if (def.form === 'media') {
      const media = s.media && typeof s.media === 'object' ? s.media : {};
      const src = media[name] || media.hero;
      if (!src) {
        if (def.required) err(`${where} 缺媒体 ${name}（media.${name} 或 media.hero）`, page);
      } else if (/^https?:/i.test(src)) {
        err(`${where} 媒体 ${name} 是远程地址；先下载到本地`, page);
      } else {
        const abs = path.resolve(path.dirname(planPath), src);
        if (!fs.existsSync(abs)) err(`${where} 媒体 ${name} 不存在：${src}`, page);
      }
      continue;
    }
    const value = slots[name];
    if (!str(value)) {
      if (def.required) err(`${where} 缺必填槽位 ${name}`, page);
      continue;
    }
    if (CJK(value) > def.maxCJK) {
      err(`${where} 槽位 ${name} 有 ${CJK(value)} 汉字，超过 ${def.maxCJK}`, page);
    }
  }

  // 未知槽位
  for (const name of Object.keys(slots)) {
    if (!expected.has(name)) warn(`${where} 未知槽位 ${name}（layouts.json 里没有）`, page);
  }

  // group
  for (const [gname, g] of Object.entries(layout.groups || {})) {
    const items = groups[gname];
    if (!Array.isArray(items)) {
      err(`${where} 缺 group ${gname}（${g.min || g.count}–${g.max || g.count} 项）`, page);
      continue;
    }
    const min = g.exact ? g.count : (g.min || g.count);
    const max = g.max || g.count;
    if (g.exact && items.length !== g.count) err(`${where} ${gname} 必须是 ${g.count} 项，实际 ${items.length}`, page);
    if (!g.exact && (items.length < min || items.length > max)) err(`${where} ${gname} 需要 ${min}–${max} 项，实际 ${items.length}`, page);
    items.forEach((item, j) => {
      if (!item || typeof item !== 'object') { err(`${where} ${gname}.${j + 1} 不是对象`, page); return; }
      for (const [key, def] of Object.entries(g.slots)) {
        const v = item[key];
        if (!str(v)) {
          err(`${where} ${gname}.${j + 1}.${key} 为空`, page);
          continue;
        }
        if (CJK(v) > def.maxCJK) err(`${where} ${gname}.${j + 1}.${key} 有 ${CJK(v)} 汉字，超过 ${def.maxCJK}`, page);
      }
      for (const key of Object.keys(item)) {
        if (!(key in g.slots) && key !== 'pct' && key !== 'px') warn(`${where} ${gname}.${j + 1} 未知字段 ${key}`, page);
      }
    });
  }

  // L11 数值预算
  if (s.layout === 'L11') {
    const maxV = parseFloat(slots.maxValue);
    if (!Number.isFinite(maxV) || maxV <= 0) err(`${where} maxValue 必须是正数`, page);
    const items = Array.isArray(groups.items) ? groups.items : [];
    for (let j = 0; j < items.length; j++) {
      const v = parseFloat(items[j].value);
      if (!Number.isFinite(v) || v < 0) err(`${where} items.${j + 1}.value 必须是 ≥0 的数字`, page);
      else if (Number.isFinite(maxV) && v > maxV) err(`${where} items.${j + 1}.value ${v} 超过 maxValue ${maxV}`, page);
    }
  }
});

/* ── 叙事顺序与版式轮换 ─────────────────────────────────────── */
if (n && slides[0].role !== 'cover') err('第 1 页必须是 cover（封面）', 1);
if (n && slides[n - 1].role !== 'closing') err(`第 ${n} 页必须是 closing（结尾）`, n);
if (n < 12 && slides.some((s) => s.role === 'section')) warn('少于 12 页时用章节幕会打断节奏');
for (let i = 1; i < layoutsSeen.length; i++) {
  if (layoutsSeen[i].id === layoutsSeen[i - 1].id) {
    let run = 1;
    for (let j = i; j > 0 && layoutsSeen[j].id === layoutsSeen[j - 1].id; j--) run++;
    if (run > P.maxSameLayoutRun) err(`第 ${i + 1} 页：版式 ${layoutsSeen[i].id} 连续 ${run} 页，超过 ${P.maxSameLayoutRun}`, i + 1);
  }
  if (layoutsSeen[i].family === layoutsSeen[i - 1].family
    && layoutsSeen[i].id !== layoutsSeen[i - 1].id) {
    warn(`第 ${i + 1} 页：与上一页同属 ${layoutsSeen[i].family} 家族，节奏可能偏平`, i + 1);
  }
}
if (n >= P.minSlides) {
  const count = new Map();
  for (const l of layoutsSeen) count.set(l.id, (count.get(l.id) || 0) + 1);
  for (const [id, c] of count) {
    if (c / n > P.maxShare) err(`版式 ${id} 占 ${Math.round((c / n) * 100)}%，超过 ${P.maxShare * 100}%`, 0);
  }
}

/* ── 时长预算 ───────────────────────────────────────────────── */
if (num(plan.durationMin) && totalMin > 0) {
  const diff = Math.abs(totalMin - plan.durationMin) / plan.durationMin;
  if (diff > P.minutesTolerance) {
    err(`逐页 minutes 合计 ${totalMin.toFixed(1)} 分钟，与 durationMin ${plan.durationMin} 相差 ${(diff * 100).toFixed(0)}%（允许 ${(P.minutesTolerance * 100)}%）`, 0);
  }
}

/* ── notes ──────────────────────────────────────────────────── */
slides.forEach((s, i) => {
  const notes = s.notes && typeof s.notes === 'object' ? s.notes : {};
  if (!str(notes.purpose)) err(`第 ${i + 1} 页缺 notes.purpose`, i + 1);
  if (!Array.isArray(notes.talk) || !notes.talk.filter(str).length) err(`第 ${i + 1} 页缺 notes.talk[]`, i + 1);
  if (notes.transition !== undefined && typeof notes.transition !== 'string') err(`第 ${i + 1} 页 notes.transition 必须是字符串`, i + 1);
});

/* ── plan ↔ deck 绑定 ───────────────────────────────────────── */
const deckPath = getArg('deck') ? path.resolve(getArg('deck')) : null;
if (deckPath) {
  if (!fs.existsSync(deckPath)) {
    err(`找不到 deck：${deckPath}`);
  } else {
    const html = fs.readFileSync(deckPath, 'utf8');
    const sections = [...html.matchAll(/<section\b([^>]*)>/g)]
      .map((m) => ({ attrs: m[1] }))
      .filter((s) => /\bclass\s*=\s*["'][^"']*\bslide\b[^"']*["']/.test(s.attrs));
    const attr = (attrs, name) => {
      const m = attrs.match(new RegExp(`\\bdata-${name}\\s*=\\s*["']([^"']*)["']`, 'i'));
      return m ? m[1].trim() : '';
    };
    if (sections.length !== n) err(`deck 有 ${sections.length} 页，plan 有 ${n} 页`, 0);
    const lim = Math.min(sections.length, n);
    for (let i = 0; i < lim; i++) {
      const a = sections[i].attrs;
      const sid = attr(a, 'plan-id');
      const role = attr(a, 'role');
      const layout = attr(a, 'layout');
      if (sid !== slides[i].id) err(`第 ${i + 1} 页 data-plan-id="${sid}"，plan 是 "${slides[i].id}"`, i + 1);
      if (role !== slides[i].role) err(`第 ${i + 1} 页 data-role="${role}"，plan 是 "${slides[i].role}"`, i + 1);
      if (layout !== slides[i].layout) err(`第 ${i + 1} 页 data-layout="${layout}"，plan 是 "${slides[i].layout}"`, i + 1);
    }
  }
}

/* ── 输出 ───────────────────────────────────────────────────── */
const errors = issues.filter((i) => i.level === 'error');
const warnings = issues.filter((i) => i.level === 'warn');
const ok = errors.length === 0 && !(STRICT && warnings.length);

if (JSON_OUT) {
  console.log(JSON.stringify({ ok, plan: planPath, deck: deckPath, slides: n, totalMinutes: totalMin, errors, warnings }, null, 2));
} else {
  console.log(`\nplan: ${path.basename(planPath)}  ${n} 页  ${totalMin.toFixed(1)} 分钟`);
  for (const i of [...errors, ...warnings]) {
    console.log(`  ${i.level === 'error' ? '✖' : '△'} ${i.page ? `P${String(i.page).padStart(2, '0')}` : '全局'} ${i.msg}`);
  }
  if (!issues.length) console.log('  结构、槽位、时长、版式轮换全部通过。');
  console.log('');
}
process.exit(ok ? 0 : 1);
