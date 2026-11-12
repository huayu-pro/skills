#!/usr/bin/env node
/**
 * plan-from-deck.mjs — 从既有 deck.html 反向提取 plan.json
 *
 *   node scripts/plan-from-deck.mjs deck.html -o plan.json [--force]
 *   node scripts/plan-from-deck.mjs deck.html                 # 打印到 stdout
 *
 * 为什么需要它：整套流程是 plan → scaffold → deck 单向的。接手一份别人做的
 * deck，或早先手写、没有 plan 的 deck，就只能一页页人眼抄回 plan——而
 * plan.mjs check 又要求 8 页以上必须有 plan。这个脚本把那条回头路补上。
 *
 * 提取范围：能机械读出来的都读（data-plan-id / data-role / data-layout /
 * data-purpose / data-talk / data-transition / data-minutes / 槽位文本）；
 * 读不出来的如实留空并在 stderr 列出，不编造。
 */
import fs from 'node:fs';
import path from 'node:path';
import { loadLayouts, expandSlots, layoutById, SKILL_ROOT } from './lib/layouts.mjs';

const argv = process.argv.slice(2);
const has = (n) => argv.includes(`--${n}`);
const getArg = (n, d = null) => {
  // 同时接受 --name 与 -name 两种写法：getArg('o') 要能命中 -o
  const i = argv.findIndex((a) => a === `--${n}` || a === `-${n}`);
  if (i === -1) return d;
  const v = argv[i + 1];
  return v && !v.startsWith('-') ? v : true;
};

const WITH_VALUE = new Set(['-o', '--out', '--plan']);
const positional = [];
for (let i = 0; i < argv.length; i++) {
  if (WITH_VALUE.has(argv[i])) { i++; continue; }
  if (argv[i].startsWith('-')) continue;
  positional.push(argv[i]);
}

const deckPath = path.resolve(positional[0] || '');
if (!deckPath || !fs.existsSync(deckPath)) {
  console.error('用法: node scripts/plan-from-deck.mjs <deck.html> [-o plan.json] [--force]');
  console.error('  从既有 deck 反提出 plan.json（用于接手没有 plan 的 deck）');
  process.exit(2);
}

const cat = loadLayouts();
const html = fs.readFileSync(deckPath, 'utf8');

/** 粗粒度属性读取：本脚本只服务「结构可读」的 deck，不追求完整 HTML 解析。 */
const attr = (tag, name) => {
  const m = tag.match(new RegExp(`\\b${name}="([^"]*)"`));
  return m ? m[1] : '';
};
const decode = (s) => String(s)
  .replace(/&lt;/g, '<').replace(/&gt;/g, '>')
  .replace(/&quot;/g, '"').replace(/&#39;/g, "'").replace(/&amp;/g, '&');

const sections = html.match(/<section\b[^>]*>[\s\S]*?<\/section>/g) || [];
if (!sections.length) {
  console.error('✖ 这个 HTML 里没有 <section> 页。不是本套版式的 deck，无法反提。');
  process.exit(1);
}

const deckTag = html.match(/<div[^>]*class="[^"]*\bdeck\b[^"]*"[^>]*>/)?.[0] || '';
const themeMatch = html.match(/class="[^"]*\b(theme-[a-z0-9-]+)\b/);
const theme = themeMatch ? themeMatch[1] : 'theme-archive';
const THEMES = JSON.parse(fs.readFileSync(path.join(SKILL_ROOT, 'assets', 'themes.json'), 'utf8'));
const substyle = THEMES.themes[theme]?.substyle || 'A';
const axisDeg = Number((html.match(/rotate\(\s*(-?\d+(?:\.\d+)?)deg/) || [])[1]);
const title = decode((html.match(/<title>([\s\S]*?)<\/title>/) || [])[1] || path.basename(deckPath, '.html'));

const gaps = [];
const slides = [];

sections.forEach((sec, i) => {
  const open = sec.match(/<section\b[^>]*>/)[0];
  const layoutId = attr(open, 'data-layout') || '';
  const layout = layoutId && layoutId !== 'custom' ? layoutById(cat, layoutId) : null;

  const role = attr(open, 'data-role') || (layout ? layout.roles[0] : '');
  const purpose = decode(attr(open, 'data-purpose'));
  const talkRaw = decode(attr(open, 'data-talk'));
  const talk = talkRaw ? talkRaw.split('|').map((s) => s.trim()).filter(Boolean) : [];
  const transition = decode(attr(open, 'data-transition'));
  const minutes = Number(attr(open, 'data-minutes')) || 1;

  // 槽位：按 data-slot 取纯文本（去标签、压空白）
  const slots = {};
  const groups = {};
  for (const m of sec.matchAll(/<([a-z0-9]+)\b[^>]*\bdata-slot="([^"]+)"[^>]*>([\s\S]*?)<\/\1>/g)) {
    const name = m[2];
    const text = decode(m[3].replace(/<[^>]+>/g, ' ').replace(/\s+/g, ' ').trim());
    if (!text) continue;
    if (name.includes('.')) {
      const [g, idx, key] = name.split('.');
      groups[g] = groups[g] || [];
      const at = Number(idx) - 1;
      groups[g][at] = groups[g][at] || {};
      groups[g][at][key || 'text'] = text;
    } else {
      slots[name] = text;
    }
  }

  // 必填槽位缺失：如实记缺口，不填占位符
  if (layout) {
    for (const [name, spec] of expandSlots(layout)) {
      if (!spec.required) continue;
      if (name.includes('.')) {
        const [g, idx, key] = name.split('.');
        const got = groups[g]?.[Number(idx) - 1]?.[key || 'text'];
        if (!got) gaps.push(`P${String(i + 1).padStart(2, '0')} 必填槽位 ${name} 在 HTML 里读不到`);
      } else if (!slots[name]) {
        gaps.push(`P${String(i + 1).padStart(2, '0')} 必填槽位 ${name} 在 HTML 里读不到`);
      }
    }
  }

  if (!purpose) gaps.push(`P${String(i + 1).padStart(2, '0')} 缺 data-purpose`);
  if (!talk.length) gaps.push(`P${String(i + 1).padStart(2, '0')} 缺 data-talk`);
  if (!layoutId) gaps.push(`P${String(i + 1).padStart(2, '0')} 缺 data-layout（plan 检查会要求补）`);

  slides.push({
    id: attr(open, 'data-plan-id') || `s${String(i + 1).padStart(2, '0')}`,
    role,
    layout: layoutId || 'custom',
    claim: slots.title1 || slots.title || slots.quote1 || '',
    minutes,
    slots,
    ...(Object.keys(groups).length ? { groups } : {}),
    notes: { purpose, talk, transition },
  });
});

const plan = {
  version: 1,
  title,
  audience: '',
  durationMin: slides.reduce((n, s) => n + s.minutes, 0),
  theme,
  substyle,
  ...(Number.isFinite(axisDeg) ? { axisDeg } : {}),
  slides,
};

const outArg = getArg('o') || getArg('out');
if (outArg && outArg !== true) {
  const out = path.resolve(outArg);
  if (fs.existsSync(out) && !has('force')) {
    console.error(`✖ ${out} 已存在。要覆盖加 --force（反提的 plan 通常需要人工补 audience 与 claim）。`);
    process.exit(1);
  }
  fs.writeFileSync(out, JSON.stringify(plan, null, 2) + '\n');
  console.error(`✔ ${slides.length} 页 → ${out}`);
} else {
  console.log(JSON.stringify(plan, null, 2));
}

if (gaps.length) {
  console.error('\n以下内容在 HTML 里读不到，plan 里如实留空，需人工补：');
  for (const g of gaps) console.error('  · ' + g);
  console.error('\n补完后跑 node scripts/plan.mjs check <plan.json> 验证。');
}
process.exit(0);
