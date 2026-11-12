#!/usr/bin/env node
/**
 * audit-text.mjs — 内容体检（不看版式，只看字）
 *
 *   node scripts/audit-text.mjs deck.html [--json]
 *
 * 查四件事：
 *   1. 占位文案（xxx / TODO / lorem / 待补 / 占位）
 *   2. 成段重复（同一段话出现在两页）
 *   3. 空页 / 只有标题没有内容的页
 *   4. 每页字数（给节奏参考）
 *
 * 这一步借自 pptx-skill 的"导出全文 + grep 占位符"，但直接读 HTML，
 * 不依赖 LibreOffice 或 markitdown。
 */
import fs from 'node:fs';
import path from 'node:path';
import { loadRules } from './rules.mjs';

const file = process.argv[2];
if (!file) {
  console.error('用法: node scripts/audit-text.mjs <deck.html> [--json] [--strict]');
  process.exit(1);
}
const asJson = process.argv.includes('--json');
const STRICT = process.argv.includes('--strict');
const R = loadRules();
const MAX_CHARS = R.thresholds.density.maxChars;

const html = fs.readFileSync(path.resolve(file), 'utf8');
// 属性顺序无关，单/双引号都认；先抓完整 opening tag，再筛 slide
const sections = [...html.matchAll(/<section\b([^>]*)>([\s\S]*?)<\/section>/g)]
  .map((m) => ({ attrs: m[1], body: m[2] }))
  .filter((s) => /\bclass\s*=\s*["'][^"']*\bslide\b[^"']*["']/.test(s.attrs));
const structured = /\bdata-structured\b/.test(html) || /\bdata-layout\s*=/.test(html);

const attrOf = (attrs, name) => {
  const m = attrs.match(new RegExp(`\\bdata-${name}\\s*=\\s*["']([^"']*)["']`, 'i'));
  return m ? m[1].trim() : '';
};

const clean = (s) =>
  s
    .replace(/<!--[\s\S]*?-->/g, '')
    .replace(/<script[\s\S]*?<\/script>/gi, '')
    .replace(/<style[\s\S]*?<\/style>/gi, '')
    .replace(/<br\s*\/?>/gi, '\n')
    .replace(/<[^>]+>/g, '\n')
    .replace(/&nbsp;/g, ' ')
    .replace(/&amp;/g, '&')
    .replace(/&lt;/g, '<')
    .replace(/&gt;/g, '>')
    .replace(/[ \t]+/g, ' ')
    .split('\n')
    .map((l) => l.trim())
    .filter(Boolean);

const PLACEHOLDER = /\b(x{3,}|todos?|lorem|ipsum|foo|bar|待补|待定|占位|示例文本|填主题|填写)\b/i;

/* ── 中文排版规则（借 textlint 的 ja-space-between-half-and-full-width
   与 Tech-Doc-Style-Chinese 的规范）。全部只报警，不自动改。 ── */
const CJK = '\u4e00-\u9fa5';
// 中文紧贴英文（不含数字：数字前后不加空格在幻灯片里是常见且可接受的）
const RULE_SPACING = new RegExp(`([${CJK}])([A-Za-z])|([A-Za-z])([${CJK}])`);
// 全角标点连用、或中文语境里用半角逗号/句号
const RULE_PUNCT = new RegExp(`([，。、；：])\\1+|([${CJK}]),|([${CJK}])\\.(?![0-9])`);
// 中文里用了弯引号
const RULE_QUOTE = new RegExp(`[“”][^“”]{0,40}[${CJK}]|[${CJK}][^“”]{0,40}[“”]`);

const isDisplayish = (line) => {
  const cjk = (line.match(new RegExp(`[${CJK}]`, 'g')) || []).length;
  // 展示字通常短、且允许贴排；正文才检查
  return cjk > 0 && cjk <= 6;
};

const pages = sections.map((s, i) => {
  const lines = clean(s.body);
  const text = lines.join('');
  const cjk = (text.match(/[\u4e00-\u9fa5]/g) || []).length;
  return {
    page: i + 1,
    lines,
    text,
    cjk,
    chars: text.length,
    purpose: attrOf(s.attrs, 'purpose'),
    notes: attrOf(s.attrs, 'notes'),
  };
});

const issues = [];
const seen = new Map();

for (const p of pages) {
  for (const line of p.lines) {
    if (PLACEHOLDER.test(line)) {
      issues.push({ page: p.page, level: 'error', code: 'PLACEHOLDER', msg: `占位文案：「${line.slice(0, 30)}」` });
    }
    // 成段重复：≥12 个汉字的行
    const cjk = (line.match(/[\u4e00-\u9fa5]/g) || []).length;
    if (cjk >= 12) {
      const key = line.replace(/[\s，。、；：「」（）·—]/g, '');
      if (seen.has(key)) {
        issues.push({
          page: p.page,
          level: 'warn',
          code: 'DUPLICATE',
          msg: `与第 ${seen.get(key)} 页重复：「${line.slice(0, 24)}」`,
        });
      } else {
        seen.set(key, p.page);
      }
    }
  }
  for (const line of p.lines) {
    // 标题类短句不查排版：构成主义标题本来就允许贴排、断行
    if (isDisplayish(line)) continue;

    if (RULE_SPACING.test(line)) {
      issues.push({ page: p.page, level: 'warn', code: 'SPACING', msg: `中文与英文之间缺空格：「${line.slice(0, 26)}」` });
    }
    if (RULE_PUNCT.test(line)) {
      issues.push({ page: p.page, level: 'warn', code: 'PUNCT', msg: `标点不规范（连用/半角混用）：「${line.slice(0, 26)}」` });
    }
    if (RULE_QUOTE.test(line)) {
      issues.push({ page: p.page, level: 'warn', code: 'QUOTE', msg: `中文里用了弯引号，建议「」：「${line.slice(0, 26)}」` });
    }
  }

  if (p.cjk + p.chars < 12) {
    issues.push({ page: p.page, level: 'warn', code: 'EMPTY', msg: `几乎空页（${p.cjk} 字）` });
  }
  // 口径与 validate.mjs 一致：汉字 + 拉丁词数。两个工具对同一页必须给出同一结论。
  const words = (p.text.replace(/[\u4e00-\u9fa5]/g, ' ').match(/[A-Za-z0-9]+/g) || []).length;
  if (p.cjk + words > MAX_CHARS) {
    issues.push({ page: p.page, level: 'warn', code: 'DENSITY', msg: `${p.cjk + words} 字（汉字 ${p.cjk}），超过 ${MAX_CHARS} 字上限` });
  }

  if (!p.purpose) {
    issues.push({
      page: p.page,
      level: structured ? 'error' : 'warn',
      code: 'PURPOSE',
      msg: '缺 data-purpose：这页要让观众记住什么？',
    });
  }
  if (!p.notes) {
    issues.push({ page: p.page, level: 'error', code: 'NOTES', msg: '缺 data-notes 讲稿' });
  }
}

// 同一个英文词在同一份 deck 里大小写不一致（Constructivism / constructivism）
const wordForms = new Map();
for (const p of pages) {
  for (const line of p.lines) {
    for (const w of line.match(/[A-Za-z][A-Za-z-]{3,}/g) || []) {
      const key = w.toLowerCase();
      if (!wordForms.has(key)) wordForms.set(key, new Map());
      wordForms.get(key).set(w, p.page);
    }
  }
}
for (const [key, forms] of wordForms) {
  if (forms.size <= 1) continue;
  // 全大写 vs 首字母大写是刻意的层级区分（展示字 vs 标题字），不算不一致
  const vals = [...forms.keys()];
  const hasUpper = vals.some((w) => w === w.toUpperCase());
  const hasTitle = vals.some((w) => w !== w.toUpperCase());
  if (hasUpper && hasTitle) continue;
  {
    const detail = [...forms.entries()].map(([w, pg]) => `「${w}」(P${pg})`).join(' / ');
    issues.push({ page: [...forms.values()][0], level: 'warn', code: 'TERM', msg: `同一词大小写不一致：${detail}` });
  }
}

const total = pages.reduce((n, p) => n + p.cjk, 0);

if (asJson) {
  console.log(JSON.stringify({ pages: pages.map(({ page, cjk, chars }) => ({ page, cjk, chars })), total, issues }, null, 2));
} else {
  console.log(`\n${pages.length} 页  共 ${total} 汉字  ${path.basename(file)}\n`);
  pages.forEach((p) => {
    const bar = '█'.repeat(Math.round(p.cjk / 8));
    console.log(`  P${String(p.page).padStart(2, '0')}  ${String(p.cjk).padStart(3)} 字  ${bar}`);
  });
  if (issues.length) {
    console.log('');
    for (const i of issues) {
      console.log(`  ${i.level === 'error' ? '✖' : '△'} P${String(i.page).padStart(2, '0')} [${i.code}] ${i.msg}`);
    }
  } else {
    console.log('\n  没有占位文案、没有重复段落、没有空页。');
  }
  console.log('');
}

process.exit(issues.some((i) => i.level === 'error') ? 1 : (STRICT && issues.length ? 1 : 0));
