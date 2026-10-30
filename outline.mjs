#!/usr/bin/env node
/**
 * outline.mjs — 页级清单：把 deck 当成大纲审一遍
 *
 *   node scripts/outline.mjs deck.html [--json] [--strict]
 *
 * 输出每页的：id / role / layout / 标题 / 字数 / 图 / 意图 / 时长。
 * 不做 JSON 中间层——HTML 本身就是大纲，这里只是把它摊平成一张能一眼看完的表。
 * --strict：0 页、缺标题、缺 data-purpose 时 exit 1。
 */
import fs from 'node:fs';
import path from 'node:path';

const file = process.argv[2];
if (!file) {
  console.error('用法: node scripts/outline.mjs <deck.html> [--json] [--strict]');
  process.exit(1);
}
const asJson = process.argv.includes('--json');
const STRICT = process.argv.includes('--strict');

const html = fs.readFileSync(path.resolve(file), 'utf8');
const sections = [...html.matchAll(/<section\b([^>]*)>([\s\S]*?)<\/section>/g)]
  .map((m) => ({ attrs: m[1], body: m[2] }))
  .filter((s) => /\bclass\s*=\s*["'][^"']*\bslide\b[^"']*["']/.test(s.attrs));

const attrOf = (attrs, name) => {
  const m = attrs.match(new RegExp(`\\bdata-${name}\\s*=\\s*["']([^"']*)["']`, 'i'));
  return m ? m[1].trim() : '';
};
const textOf = (s) => s.replace(/<[^>]+>/g, '\n').split('\n').map((x) => x.trim()).filter(Boolean);
const strip = (s) => s.replace(/<[^>]+>/g, '').replace(/&nbsp;/g, ' ').trim();

const rows = sections.map((s, i) => {
  const lines = textOf(s.body);
  const tm = s.body.match(/<(?:div|span)[^>]*class=["'][^"']*\bt-(?:hero|h1|h2)\b[^"']*["'][^>]*>([\s\S]*?)<\/(?:div|span)>/);
  const title = tm ? strip(tm[1]).slice(0, 24) : (lines[0] || '').slice(0, 24);
  const text = lines.join('');
  const cjk = (text.match(/[\u4e00-\u9fa5]/g) || []).length;
  const words = (text.replace(/[\u4e00-\u9fa5]/g, ' ').match(/[A-Za-z0-9]+/g) || []).length;
  const hasImg = /<img\b/i.test(s.body);
  const purpose = attrOf(s.attrs, 'purpose');
  const notes = attrOf(s.attrs, 'notes');
  const layout = attrOf(s.attrs, 'layout');
  const role = attrOf(s.attrs, 'role');
  const planId = attrOf(s.attrs, 'plan-id');
  const theme = (s.attrs.match(/\btheme-[\w-]+/) || [''])[0].replace('theme-', '');
  const marks = [];
  if (/grid4--lead/.test(s.body)) marks.push('1大3小');
  else if (/class=["']grid4/.test(s.body)) marks.push('等宽四栏');
  if (/wedge/.test(s.body)) marks.push('楔形');
  if (/class=["']band/.test(s.body)) marks.push('斜带');
  if (/class=["']sun/.test(s.body)) marks.push('圆');
  return {
    page: i + 1,
    id: planId || `P${String(i + 1).padStart(2, '0')}`,
    role: role || '',
    layout: layout || '',
    title,
    cjk,
    words,
    hasImg,
    purpose,
    notes: notes ? notes.slice(0, 40) : '',
    minutes: parseFloat(attrOf(s.attrs, 'minutes')) || 0,
    theme,
    marks: marks.join('+'),
  };
});

const missing = rows.filter((r) => !r.purpose || !r.title);
const totalMin = rows.reduce((n, r) => n + r.minutes, 0);
const structured = /\bdata-structured\b/.test(html) || rows.some((r) => r.layout);

if (asJson) {
  console.log(JSON.stringify({
    file: path.basename(file),
    pages: rows.length,
    structured,
    totalMinutes: totalMin,
    totalCJK: rows.reduce((n, r) => n + r.cjk, 0),
    rows,
    missing: missing.map((r) => ({ page: r.page, title: !r.title, purpose: !r.purpose })),
  }, null, 2));
} else {
  console.log(`\n${rows.length} 页  ${rows.reduce((n, r) => n + r.cjk, 0)} 汉字  ${path.basename(file)}`);
  if (totalMin) console.log(`预计讲述 ${totalMin.toFixed(1)} 分钟`);
  console.log('');
  console.log('  页  ID    角色      版式   标题                     字数  图  骨架            意图');
  console.log('  ' + '─'.repeat(94));
  for (const r of rows) {
    const flag = r.purpose ? ' ' : '!';
    console.log(
      `  ${String(r.page).padStart(2)}${flag} ${r.id.padEnd(5)} ${(r.role || '—').padEnd(8)} ${(r.layout || '—').padEnd(5)} ${r.title.padEnd(24).slice(0, 24)} ${String(r.cjk).padStart(4)}  ${r.hasImg ? '●' : '·'}  ${(r.marks || '—').padEnd(15)} ${r.purpose.slice(0, 18)}`,
    );
  }
  if (missing.length) {
    console.log(`\n  ! ${missing.length} 页缺标题或意图（data-purpose）——先补一句"这页要让观众记住什么"`);
  }
  console.log('');
}

const fatal = rows.length === 0 || missing.some((r) => !r.title || !r.purpose);
process.exit(STRICT && fatal ? 1 : (rows.length === 0 ? 1 : 0));
