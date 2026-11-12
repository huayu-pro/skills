/**
 * rules.mjs — assets/rules.json 的唯一读取入口
 *
 * 为什么要有这个文件：阈值一旦在 validate.mjs 里硬编码，它就会变成"第 5 个真相源"，
 * 文档、脚本、示例又会各自漂移。所以：
 *   · 只有这里能读 rules.json；
 *   · 找不到就退出码 2，绝不静默用默认值；
 *   · 文档表格由 gen-rules-doc.mjs 从同一份数据渲染。
 */
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const HERE = path.dirname(fileURLToPath(import.meta.url));
export const SKILL_ROOT = path.resolve(HERE, '..');
export const RULES_PATH = path.join(SKILL_ROOT, 'assets', 'rules.json');

const REQUIRED = ['canvas', 'palette', 'thresholds', 'codes', 'rules', 'forbid'];

// 阈值拼错（如 minratio）会让比较式静默变成 false，规则永远不触发。
// 这里逐个点名，缺一个就 exit 2，绝不回落默认值。
const REQUIRED_THRESHOLDS = [
  ['balance.minRatio', 'number'],
  ['balance.recipeFr', 'number'],
  ['weight.minLinePx', 'number'],
  ['font.bodyPx', 'number'],
  ['font.labelPx', 'number'],
  ['font.microPx', 'number'],
  ['font.labelMaxCJK', 'number'],
  ['textArea.max', 'number'],
  ['density.maxChars', 'number'],
  ['contrast.body', 'number'],
  ['contrast.large', 'number'],
  ['axis.minDeg', 'number'],
  ['axis.dominantMinAreaPct', 'number'],
  ['axis.longSidePct', 'number'],
  ['overlap.minPx', 'number'],
  ['overlap.minRatio', 'number'],
  ['opacity.text', 'number'],
  ['safe.warnPx', 'number'],
  ['width.minGapPx', 'number'],
  ['occlude.samples', 'number'],
  ['occlude.warnHits', 'number'],
  ['occlude.errorHits', 'number'],
  ['ink.minFillAreaPct', 'number'],
];

export function loadRules(explicitPath) {
  const candidates = [
    explicitPath,
    process.env.CST_RULES,
    RULES_PATH,
  ].filter(Boolean);

  const found = candidates.find((p) => {
    try { return fs.existsSync(p); } catch { return false; }
  });

  if (!found) {
    console.error('✖ 找不到 rules.json。它是阈值与规则码的唯一真相源，缺失时不做任何猜测。');
    console.error(`  期望位置：${RULES_PATH}`);
    console.error('  修复：确认 skill 目录完整，或设置 CST_RULES 指向 rules.json');
    process.exit(2);
  }

  let rules;
  try {
    rules = JSON.parse(fs.readFileSync(found, 'utf8'));
  } catch (err) {
    console.error(`✖ rules.json 不是合法 JSON：${found}\n  ${err.message}`);
    process.exit(2);
  }

  const missing = REQUIRED.filter((k) => !(k in rules));
  if (missing.length) {
    console.error(`✖ rules.json 缺少必需字段：${missing.join(', ')}`);
    process.exit(2);
  }

  for (const [pathName, type] of REQUIRED_THRESHOLDS) {
    const v = pick(rules.thresholds, pathName);
    if (typeof v !== type || !Number.isFinite(v)) {
      console.error(`✖ rules.json thresholds.${pathName} 缺失或不是 ${type}（实际 ${v}）`);
      process.exit(2);
    }
  }

  const codeIds = new Set();
  for (const [code, def] of Object.entries(rules.codes)) {
    if (!def.level) {
      console.error(`✖ rules.json codes.${code} 缺少 level`);
      process.exit(2);
    }
    if (!def.summary) {
      console.error(`✖ rules.json codes.${code} 缺少 summary`);
      process.exit(2);
    }
    codeIds.add(code);
  }

  for (const rule of rules.rules) {
    if (!Number.isInteger(rule.id) || !rule.title) {
      console.error(`✖ rules.json rules[] 有缺 id/title 的条目：${JSON.stringify(rule).slice(0, 80)}`);
      process.exit(2);
    }
    for (const code of rule.codes || []) {
      if (!codeIds.has(code)) {
        console.error(`✖ 规则 ${rule.id} 引用了不存在的规则码 ${code}`);
        process.exit(2);
      }
    }
  }

  const forbidIds = new Set();
  for (const f of rules.forbid) {
    if (!f.id || !f.msg) {
      console.error(`✖ rules.json forbid[] 有缺 id/msg 的条目`);
      process.exit(2);
    }
    if (forbidIds.has(f.id)) {
      console.error(`✖ rules.json forbid id 重复：${f.id}`);
      process.exit(2);
    }
    forbidIds.add(f.id);
  }

  rules.__path = found;
  return rules;
}

/** 取 "a.b.c" 形式的嵌套值；拿不到返回 undefined */
export function pick(obj, dotted) {
  return dotted.split('.').reduce((acc, k) => (acc == null ? undefined : acc[k]), obj);
}

/** 把 "≥{balance.minRatio}×" 渲染成 "≥1.7×"；未知占位符原样保留，方便 selfcheck 抓出来 */
export function interpolate(template, rules) {
  const ctx = { ...rules.thresholds, palette: rules.palette, canvas: rules.canvas };
  return String(template).replace(/\{([\w.]+)\}/g, (m, key) => {
    const v = pick(ctx, key);
    return v === undefined ? m : String(v);
  });
}

/** 规则码的稳定顺序：文档表格与 issue 排序都用它，避免各处手写数组漏项 */
export function codeOrder(rules) {
  return Object.keys(rules.codes);
}

export function codeLevel(rules, code) {
  return rules.codes[code]?.level || 'warn';
}

export function codeRule(rules, code) {
  return rules.codes[code]?.rule ?? null;
}
