#!/usr/bin/env node
/**
 * scaffold.mjs — plan.json → deck.html
 *
 *   node scripts/scaffold.mjs plan.json -o deck.html [--force] [--check] [--css path]
 *   node scripts/scaffold.mjs --gallery examples/layout-gallery
 *
 * 几何来自 assets/layouts/L*.html；本脚本只做确定性填充：
 *   · 展开 groups、计算 L11 条形宽度
 *   · 移除没有内容的 data-slot-block
 *   · 写 data-plan-id/data-role/data-layout/data-purpose/data-talk/data-minutes
 *   · 按 layout 的 folio/ink/texture 元数据生成页脚与纹理
 * 同一份 plan 两次输出必须字节一致。
 */
import fs from 'node:fs';
import path from 'node:path';
import { spawnSync } from 'node:child_process';
import { loadLayouts, expandSlots, layoutById, SKILL_ROOT, readTemplate } from './lib/layouts.mjs';

const argv = process.argv.slice(2);
const has = (n) => argv.includes(`--${n}`);
const getArg = (n, d = null) => {
  let i = argv.indexOf(`--${n}`);
  return i === -1 ? d : (argv[i + 1] && !argv[i + 1].startsWith('--') ? argv[++i] : true);
};

const galleryDir = getArg('gallery');
const planArg = argv.find((a, i) => !a.startsWith('-') && argv[i - 1] !== '--out' && argv[i - 1] !== '--css' && argv[i - 1] !== '--gallery' && argv[i - 1] !== '--plan' && argv[i - 1] !== '-o');
const oShort = argv.indexOf('-o');
const outArg = getArg('out') || (oShort >= 0 ? argv[oShort + 1] : null);
const CHECK = has('check');
const FORCE = has('force');
if (galleryDir === true || outArg === true) {
  console.error('✖ --gallery / --out 需要一个目录或文件路径');
  process.exit(2);
}

let cat;
try {
  cat = loadLayouts();
} catch (err) {
  console.error(`✖ ${err.message}`);
  process.exit(2);
}

/* ── 输出路径 ─────────────────────────────────────────────── */
const outPath = galleryDir
  ? path.resolve(galleryDir, 'deck.html')
  : outArg ? path.resolve(outArg) : null;
if (!outPath) {
  console.error('用法: node scripts/scaffold.mjs plan.json -o deck.html [--force] [--check]');
  console.error('      node scripts/scaffold.mjs --gallery examples/layout-gallery');
  process.exit(2);
}
if (fs.existsSync(outPath) && !FORCE && !CHECK) {
  console.error(`✖ 输出已存在：${outPath}。确认要覆盖就加 --force。`);
  process.exit(2);
}

/* ── 读 plan / gallery ────────────────────────────────────── */
let plan;
let planPath = null;
if (galleryDir) {
  plan = galleryPlan(cat);
} else {
  planPath = path.resolve(getArg('plan') || planArg || '');
  if (!planPath || !fs.existsSync(planPath)) {
    console.error(`✖ 找不到 plan：${planPath || '(未提供)'}`);
    process.exit(2);
  }
  // 先过 plan.mjs，结构不成立就不生成 HTML
  const chk = spawnSync(process.execPath, ['scripts/plan.mjs', 'check', planPath], {
    cwd: SKILL_ROOT, stdio: 'inherit',
  });
  if (chk.status !== 0) {
    console.error('\n✖ plan 未通过检查，scaffold 停止。');
    process.exit(1);
  }
  try {
    plan = JSON.parse(fs.readFileSync(planPath, 'utf8'));
  } catch (err) {
    console.error(`✖ plan 不是合法 JSON：${err.message}`);
    process.exit(2);
  }
}

const slides = plan.slides || [];
const total = slides.length;
const deckTitle = plan.title || 'constructivist deck';
const folioLabel = String(plan.folioLabel || deckTitle).slice(0, 18);
const theme = plan.theme || 'theme-archive';
const THEMES = JSON.parse(fs.readFileSync(path.join(SKILL_ROOT, 'assets', 'themes.json'), 'utf8')).themes;
const texture = THEMES[theme]?.texture || 'grain';
const axisDeg = Number.isFinite(plan.axisDeg) ? plan.axisDeg : -11;
const showcase = !!plan.showcase || !!galleryDir;
const cssRel = getArg('css') || path.relative(path.dirname(outPath), path.join(SKILL_ROOT, 'assets', 'deck.css')).split(path.sep).join('/');

const pages = [];
const errors = [];
slides.forEach((slide, i) => {
  const layout = layoutById(cat, slide.layout);
  if (!layout) {
    errors.push(`第 ${i + 1} 页 layout ${slide.layout} 不存在`);
    return;
  }
  let tpl;
  try {
    tpl = readTemplate(layout.id);
  } catch (err) {
    errors.push(err.message);
    return;
  }
  const slots = slide.slots || {};
  const groups = slide.groups || {};
  const flat = expandSlots(layout);
  const values = new Map();

  // 普通槽位
  for (const [name, def] of flat) {
    if (name.includes('.')) continue;
    if (def.form === 'media') {
      const media = slide.media || {};
      const src = media[name] || media.hero || '';
      values.set(name, src);
    } else {
      values.set(name, slots[name] == null ? '' : String(slots[name]));
    }
  }

  // group 槽位 + L11 计算宽度
  for (const [gname, g] of Object.entries(layout.groups || {})) {
    const items = Array.isArray(groups[gname]) ? groups[gname] : [];
    const maxV = gname === 'items' && slide.layout === 'L11' ? parseFloat(slots.maxValue) : NaN;
    items.slice(0, g.max || g.count).forEach((item, j) => {
      for (const key of Object.keys(g.slots)) {
        values.set(`${gname}.${j + 1}.${key}`, item[key] == null ? '' : String(item[key]));
      }
      if (Number.isFinite(maxV) && maxV > 0) {
        const v = parseFloat(item.value);
        const pct = Number.isFinite(v) ? Math.max(0, Math.min(100, (v / maxV) * 100)) : 0;
        values.set(`${gname}.${j + 1}.pct`, pct.toFixed(1));
        values.set(`${gname}.${j + 1}.px`, String(Math.max(2, Math.round(pct * 8))));
      }
    });
  }

  // 先填 slot，再删空块，最后补 computed：computed 占位符可能躺在会被整块
  // 删除的 data-slot-block 里（如 L11 只给 4 项时的 items.5），先删块再算，
  // 否则删掉的块里的 {{computed:}} 会先一步报"没有值"。
  let html = tpl.replace(/\{\{slot:([^}]+)\}\}/g, (m, name) => {
    if (!values.has(name)) {
      if (flat.has(name)) return '';
      errors.push(`第 ${i + 1} 页模板占位符 ${name} 没有对应槽位`);
      return '';
    }
    return escapeAttr(values.get(name));
  });
  html = removeEmptyBlocks(html, (name) => blockKeep(name, slide, layout));
  html = html.replace(/\{\{computed:([^}]+)\}\}/g, (m, name) => {
    if (!values.has(name)) {
      errors.push(`第 ${i + 1} 页计算占位符 ${name} 没有值`);
      return '0';
    }
    return values.get(name);
  });

  html = html.replace(/\{\{axisDeg\}\}/g, String(Number.isFinite(slide.axisDeg) ? slide.axisDeg : axisDeg));
  html = html.replace(/\{\{texture\}\}/g, textureFor(texture));
  html = html.replace(/\{\{folio\}\}/g, folioFor(layout, i + 1, total, folioLabel));

  if (/\{\{[^}]+\}\}/.test(html)) {
    errors.push(`第 ${i + 1} 页仍有未替换的占位符：${html.match(/\{\{[^}]+\}\}/)[0]}`);
  }

  const cls = ['slide', theme, layout.ink ? 'slide--ink' : ''].filter(Boolean).join(' ');
  const extraAttrs = [
    layout.balanceOk ? 'data-balance-ok' : '',
  ].filter(Boolean).join(' ');
  const attrs = [
    `data-plan-id="${escapeAttr(slide.id || `s${String(i + 1).padStart(2, '0')}`)}"`,
    `data-role="${escapeAttr(slide.role || '')}"`,
    `data-layout="${escapeAttr(layout.id)}"`,
    extraAttrs,
    `data-purpose="${escapeAttr(slide.notes?.purpose || slide.claim || '')}"`,
    `data-talk="${escapeAttr((slide.notes?.talk || []).join('|'))}"`,
    slide.notes?.transition ? `data-transition="${escapeAttr(slide.notes.transition)}"` : '',
    `data-minutes="${Number(slide.minutes) || 1}"`,
    // 讲稿只用 notes.cue。曾经用 purpose/claim 兜底，于是「讲稿只有一句标题」
    // 在 audit-text 与 verify-pptx 里都算非空，整条备注链路永绿——宁可留空让它红。
    `data-notes="${escapeAttr(slide.notes?.cue || '')}"`,
  ].filter(Boolean).join(' ');
  pages.push(`<section class="${cls}" ${attrs}>\n${html.trim()}\n</section>`);
});

if (errors.length) {
  console.error('\n✖ scaffold 失败：');
  for (const e of errors) console.error('  · ' + e);
  process.exit(1);
}

const doc = `<!doctype html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<title>${escapeHtml(deckTitle)}</title>
<link rel="stylesheet" href="${escapeAttr(cssRel)}">
</head>
<body>
<div class="deck"${showcase ? ' data-showcase' : ''}${galleryDir ? ' data-structure-ok' : ''} data-structured>

${pages.join('\n\n')}

</div>
</body>
</html>
`;

if (CHECK) {
  console.log(`\n✔ scaffold check：${total} 页，模板与 plan 都能填充；未写盘。\n`);
  process.exit(0);
}
fs.mkdirSync(path.dirname(outPath), { recursive: true });
fs.writeFileSync(outPath, doc);
console.log(`\n✔ ${path.relative(process.cwd(), outPath)}  ${total} 页  ${plan.theme}  ${plan.substyle || '?'}`);
console.log('  下一步：node scripts/validate.mjs <deck.html> --strict');
console.log('          node scripts/render.mjs <deck.html> --out preview --sheet\n');

/* ── 工具 ─────────────────────────────────────────────────── */
function blockKeep(name, slide, layout) {
  const slots = slide.slots || {};
  const groups = slide.groups || {};
  if (name === 'counter1') return !!(slots.counter1 || slots.counter2);
  const gm = name.match(/^([a-zA-Z0-9]+)\.(\d+)$/);
  if (gm) {
    const arr = groups[gm[1]];
    const item = Array.isArray(arr) ? arr[Number(gm[2]) - 1] : null;
    if (!item) return false;
    return Object.values(item).some((v) => String(v == null ? '' : v).trim());
  }
  if (layout.slots && layout.slots[name]) {
    if (layout.slots[name].form === 'media') {
      const media = slide.media || {};
      return !!(media[name] || media.hero);
    }
    return String(slots[name] == null ? '' : slots[name]).trim().length > 0;
  }
  return true;
}

/** 只处理模板里由 <div data-slot-block="…"> 包起来的块；按 div 深度找闭合。 */
function removeEmptyBlocks(html, keep) {
  const findEnd = (openEnd) => {
    let depth = 1;
    const tag = /<\/?div\b[^>]*>/g;
    tag.lastIndex = openEnd;
    for (let t = tag.exec(html); t; t = tag.exec(html)) {
      if (t[0].startsWith('</')) depth--;
      else depth++;
      if (depth === 0) return t.index + t[0].length;
    }
    return -1;
  };
  let changed = true;
  while (changed) {
    changed = false;
    let pos = 0;
    while (true) {
      const re = /<div\b[^>]*\bdata-slot-block="([^"]+)"[^>]*>/g;
      re.lastIndex = pos;
      const m = re.exec(html);
      if (!m) break;
      const end = findEnd(m.index + m[0].length);
      if (end === -1) break;
      if (!keep(m[1])) {
        html = html.slice(0, m.index) + html.slice(end);
        changed = true;
        pos = m.index;
      } else {
        pos = end;
      }
    }
  }
  return html;
}

function textureFor(kind) {
  if (kind === 'halftone') return '<div class="halftone"></div>';
  if (kind === 'grain') return '<div class="grain"></div>';
  return '';
}

function folioFor(layout, page, total, label) {
  const f = layout.folio || { variant: 'plain', tone: 'paper' };
  const cls = ['folio'];
  let style = '';
  if (f.variant === 'cut') { cls.push('folio--cut'); style = 'width:420px;'; }
  else if (f.variant === 'block') cls.push('folio--block');
  else if (f.variant === 'end') { cls.push('folio--end'); }
  if (f.tone === 'ink' && f.variant !== 'block') style += 'color:var(--bg);';
  const attrs = style ? ` style="${style}"` : '';
  return `<div class="${cls.join(' ')}"${attrs}><div class="meta">${escapeHtml(label)}</div><div class="meta">${String(page).padStart(2, '0')} / ${String(total).padStart(2, '0')}</div></div>`;
}

function escapeHtml(s) {
  return String(s == null ? '' : s)
    .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;').replace(/'/g, '&#39;');
}
function escapeAttr(s) {
  return escapeHtml(s).replace(/\n/g, ' ');
}

/* ── 画廊：每个版式一页，检查骨架本身 ───────────────────── */
function galleryPlan(cat) {
  const sample = {
    L01: { slots: { kicker: 'CONSTRUCTIVISM · LAYOUT 01', latin: 'Constructivism', title1: '构成主义', lead: '用最少的元素，制造最大的尺度、张力与记忆点。', meta: '1920 / USSR' }, notes: n('巨构封面') },
    L02: { slots: { masthead: 'ARCHIVE / LAYOUT 02', title1: '档案封面', subtitle: '比封面克制，用编号和留白压住。', counter1: '09', counter2: '01', lead: '适合内部汇报的首页。', meta: 'ARCHIVE COVER' }, notes: n('档案封面') },
    L03: { slots: { number: '02', chapter: '第二章 · 语法', title1: '从艺术', title2: '走向生活' }, notes: n('章节幕') },
    L04: { slots: { kicker: 'METHOD / LAYOUT 04', title: '四条法则，第一条压倒其余', lead: '一页只讲一个方法：首栏吃掉份额，其余三栏支撑。' }, groups: { items: [
      { num: '01', label: 'ONE DIAGONAL', head: '一条主斜线', body: '整张图只有一个动势方向。' },
      { num: '02', label: 'TYPE', head: '字是结构', body: '粗、窄、压缩，和形状咬合。' },
      { num: '03', label: 'TWO INKS', head: '两墨一纸', body: '面积严重不均，主次一眼可见。' },
      { num: '04', label: 'SCALE', head: '极端尺度差', body: '巨物与微字并置。' },
    ] }, notes: n('1+3 方法页') },
    L05: { slots: { kicker: 'TIMELINE / LAYOUT 05', title: '四个年份', lead: '一场运动从宣言到被禁，只用了十五年。', meta: '1917 — 1932' }, groups: { items: [
      { num: '1917', label: 'OCTOBER', text: '十月革命，先锋派进入生产。' },
      { num: '1919', label: 'RED WEDGE', text: '李西茨基用一块三角形画完内战。' },
      { num: '1922', label: 'PRODUCTIVISM', text: '艺术进入工厂与印刷所。' },
      { num: '1932', label: 'BANNED', text: '运动被禁，语法散进现代设计。' },
    ] }, notes: n('巨号时间轴') },
    L06: { slots: { kicker: 'SPLIT / LAYOUT 06', title1: '一条线', title2: '两个圆', body: '左右硬切，一侧纸底、一侧墨底。切边是硬的，不要圆角、不要阴影。', bigNumber: '1917', caption: '深色侧放数字与说明，浅色侧放论点。', meta: 'HARD SPLIT' }, notes: n('左右硬切') },
    L07: { slots: { title1: '把艺术', title2: '赶出画室', body: '楔形的左边缘是竖直的，文字放在它左边之外。', meta: 'WEDGE / MANIFESTO' }, notes: n('斜切宣言') },
    L09: { slots: { title: '两种做法，只能选一个', leftHead: '档案红黑', rightHead: '靛蓝重墨', meta: 'COMPARE' }, groups: {
      leftPoints: [{ text: '两色油墨 + 粗纸。' }, { text: '红承载立场，黑提供结构。' }, { text: '适合文化、品牌、观点。' }],
      rightPoints: [{ text: '高纯度靛蓝 + 冷白。' }, { text: '克制来自纯度，不来自空。' }, { text: '适合科技、产品、数据。' }],
    }, notes: n('双栏对比') },
    L10: { slots: { kicker: 'QUOTE / LAYOUT 10', quote1: '艺术不是生活的装饰，', quote2: '而是改变生活的力。', attribution: '— 罗德琴柯', meta: '1922' }, notes: n('引语') },
    L11: { slots: { title: '条形图：只留必要的东西', lead: '条形长度按数据等比，不加坐标轴和网格线。', maxValue: '100', meta: 'BARS' }, groups: { items: [
      { label: '档案', value: '62', display: '62' },
      { label: '靛蓝', value: '48', display: '48' },
      { label: '巨构', value: '31', display: '31' },
      { label: '引语', value: '18', display: '18' },
      { label: '结尾', value: '9', display: '9' },
    ] }, notes: n('条形图') },
    L12: { slots: { title: '用字母做肖像', meta: 'FOUR FIGURES' }, groups: { items: [
      { letter: 'T', name: '塔特林', meta: '1885 — 1953', text: '把艺术接到材料与结构上。' },
      { letter: 'L', name: '李西茨基', meta: '1890 — 1941', text: '把字变成图形。' },
      { letter: 'R', name: '罗德琴柯', meta: '1891 — 1956', text: '仰角、对角线、极端裁切。' },
      { letter: 'S', name: '斯捷潘诺娃', meta: '1894 — 1958', text: '把几何放进织物与服装。' },
    ] }, notes: n('人物卡') },
    L13: { slots: { kicker: 'IMAGE / LAYOUT 13', title1: '全图压字', caption: '图片和几何的对抗，正是构成主义的核心。', meta: 'FULL IMAGE' }, media: { image: '../../assets/img/industry.svg' }, notes: n('全图压字') },
    L14: { slots: { title: '目录', meta: 'CONTENTS' }, groups: { items: [
      { num: '01', name: '起源', date: '1917 — 1919' },
      { num: '02', name: '语法', date: '1919 — 1922' },
      { num: '03', name: '生产', date: '1922 — 1928' },
      { num: '04', name: '遗产', date: '1928 — 现在' },
    ] }, notes: n('目录索引') },
    L15: { slots: { title: '清单：只留横线', meta: 'TABLE' }, groups: {
      headers: [{ text: '阶段' }, { text: '年代' }, { text: '关键词' }, { text: '代表' }],
      rows: [
        { c1: '起源', c2: '1917', c3: '宣言与街头', c4: 'L' },
        { c1: '语法', c2: '1919', c3: '楔形与斜线', c4: 'R' },
        { c1: '生产', c2: '1922', c3: '织物与印刷', c4: 'S' },
        { c1: '遗产', c2: '1932', c3: '散进现代设计', c4: '—' },
      ],
    }, notes: n('清单表') },
    L16: { slots: { title1: '把你的内容', title2: '压进这个结构', action: '先写一句主张，再选一个版式。', meta: 'START NOW' }, notes: n('行动结尾') },
    L17: { slots: { kicker: 'FOCUS / LAYOUT 17', title1: '大圆聚焦', title2: '一个主张', body: '巨圆被边缘裁掉一角，斜带从它背后穿出。圆是尺度，带是方向，文字在左侧压住画布。', stat: '1908', statNote: 'DIAMETER 540 PX', meta: 'SUN + ORBIT' }, notes: n('大圆聚焦') },
    L18: { slots: { kicker: 'STEPS / LAYOUT 18', title: '四级台阶', meta: 'ASCENDING' }, groups: { steps: [
      { num: '01', label: 'CLAIM', text: '从一句主张出发。' },
      { num: '02', label: 'PROVE', text: '补证据与数据。' },
      { num: '03', label: 'IMAGE', text: '有巨物就上图。' },
      { num: '04', label: 'ACT', text: '落到一个动作。' },
    ] }, notes: n('台阶进程') },
    L19: { slots: { kicker: 'COLLAGE / LAYOUT 19', title: '拼贴档案', bigLabel: 'FIG. 01 / ARCHIVE', cellBHead: '两张墨', cellBText: '左格放证据：照片或几何剪影，缺图时露出底块。', cellCHead: '一条注释', cellCText: '右下格放旁注，用规则线分隔。', meta: 'COLLAGE CELLS' }, notes: n('拼贴档案') },
    L20: { slots: { kicker: 'TIMELINE / LAYOUT 20', title: '横排年份', lead: '节点沿脊线交替上下，读的顺序由位置给出。' }, groups: { nodes: [
      { date: '1917', label: 'START', text: '起点最重。' },
      { date: '1919', label: 'WEDGE', text: '红楔子打进白军。' },
      { date: '1922', label: 'PRESS', text: '艺术进印刷所。' },
      { date: '1932', label: 'END', text: '被禁，语法散开。' },
    ] }, notes: n('横向时间轴') },
    L21: { slots: { kicker: 'SPLIT / LAYOUT 21', title1: '图文', title2: '对切', body: '右半张给图片，缺图时露出几何兜底；左半张放主张。切边是硬的，一条斜带咬住分界。', caption: 'PHOTO / GEOMETRY', meta: 'HALF SPLIT' }, notes: n('图文对切') },
    L22: { slots: { kicker: 'COMPARE / LAYOUT 22', title: '用体量说主次，不用措辞', leftLabel: '现状', leftNum: '12%', leftNote: '两栏一样高时，读者读不出哪个更重要。', rightLabel: '目标', rightNum: '38%', rightNote: '数字本身承担了面积差。', takeaway: '结论写在最下面一行：先给判断，再给依据。' }, notes: n('体量对比') },
    L23: { slots: { kicker: 'QUOTE / LAYOUT 23', quote1: '版面不是容器，', quote2: '是论点本身。', attribution: '— 李西茨基，1923', meta: 'INK SLAB / LEFT' }, notes: n('巨引语') },
    L24: { slots: { number: '03', chapter: '第三章 · 生产', title1: '从画室', title2: '走进印刷所', lead: '楔形从右上压下来，编号在左下角给一个硬坐标。' }, notes: n('斜切章节') },
    L25: { slots: { title1: '现在就开始', title2: '写下第一句', action: '先写一句主张，再选版式，最后跑 gate。', contact: '问题与反馈走仓库 issue，不要发邮件。', meta: 'END / 2026' }, notes: n('横幅收束') },
  };
  const slides = cat.layouts.map((l) => {
    const s = sample[l.id] || { slots: {}, notes: n(l.name) };
    const mins = 1;
    const role = l.id === 'L02' ? 'context' : l.roles[0];
    return {
      id: `G${l.id}`,
      role,
      layout: l.id,
      claim: `版式 ${l.id} · ${l.name}`,
      minutes: mins,
      slots: s.slots || {},
      groups: s.groups || undefined,
      media: s.media || undefined,
      notes: { purpose: s.notes.purpose, talk: s.notes.talk, transition: s.notes.transition },
    };
  });
  return {
    version: 1,
    title: '版式画廊',
    audience: '维护者',
    durationMin: slides.length,
    theme: 'theme-archive',
    substyle: 'A',
    axisDeg: -11,
    folioLabel: 'LAYOUT GALLERY',
    showcase: true,
    slides,
  };
}
function n(name) {
  return { purpose: `展示 ${name}`, talk: [`这是 ${name} 的骨架示例。`], transition: '' };
}
