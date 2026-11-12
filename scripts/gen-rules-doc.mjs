#!/usr/bin/env node
/**
 * gen-rules-doc.mjs — 从 assets/rules.json 渲染文档里的规则表
 *
 *   node scripts/gen-rules-doc.mjs            # 写入所有带标记块的文件
 *   node scripts/gen-rules-doc.mjs --check    # 只比对，不写盘（selfcheck 用）
 *
 * 文档里只有标记块之间的内容是生成的：
 *   <!-- RULES:BEGIN 由 scripts/gen-rules-doc.mjs 生成，勿手改 --> … <!-- RULES:END -->
 *
 * 这样「十二条硬规则」只有一份定义；改阈值只改 rules.json，表格不会漂移。
 */
import fs from 'node:fs';
import path from 'node:path';
import { loadRules, interpolate, SKILL_ROOT } from './rules.mjs';

const args = new Set(process.argv.slice(2));
const CHECK = args.has('--check');
const rules = loadRules();

const LEVEL_LABEL = { error: 'error', warn: 'warn', gate: 'gate' };

function tableRules() {
  const head = [
    '| # | 规则 | 判据 | 码 | 豁免 |',
    '|---|---|---|---|---|',
  ];
  const rows = rules.rules.map((r) => {
    const codes = r.codes.map((c) => `\`${c}\``).join(' ');
    const exempt = r.exempt.length ? r.exempt.map((e) => `\`${e}\``).join(' ') : '—';
    const criterion = interpolate(r.criterion, rules).replace(/\|/g, '\\|');
    return `| ${r.id} | **${r.title}** | ${criterion} | ${codes} | ${exempt} |`;
  });
  return [...head, ...rows].join('\n');
}

function tableCodes() {
  const head = ['| 码 | 级别 | 判据 | 典型修法 |', '|---|---|---|---|'];
  const rows = Object.entries(rules.codes).map(([code, def]) => {
    const rule = def.rule ? `规则 ${def.rule}` : '支撑检查';
    const summary = interpolate(def.summary, rules).replace(/\|/g, '\\|');
    return `| \`${code}\`<br><sub>${rule}</sub> | ${LEVEL_LABEL[def.level] || def.level} | ${summary} | ${def.fix} |`;
  });
  return [...head, ...rows].join('\n');
}

const RENDERERS = { RULES: tableRules, CODES: tableCodes };

function marker(kind) {
  return {
    begin: `<!-- ${kind}:BEGIN 由 scripts/gen-rules-doc.mjs 生成，勿手改 -->`,
    end: `<!-- ${kind}:END -->`,
  };
}

function replaceBlock(text, kind, body) {
  const { begin, end } = marker(kind);
  const b = text.indexOf(begin);
  if (b === -1) return { text, changed: false, found: false };
  const e = text.indexOf(end, b);
  if (e === -1) return { text, changed: false, found: false };
  const next = `${begin}\n${body}\n${end}`;
  const current = text.slice(b, e + end.length);
  return { text: text.slice(0, b) + next + text.slice(e + end.length), changed: current !== next, found: true };
}

let stale = 0;
let written = 0;
let missing = 0;

for (const [rel, kinds] of Object.entries(rules.generatedBlocks)) {
  const file = path.join(SKILL_ROOT, rel);
  if (!fs.existsSync(file)) {
    console.error(`✖ 生成块目标不存在：${rel}`);
    missing++;
    continue;
  }
  let text = fs.readFileSync(file, 'utf8');
  let dirty = false;

  for (const kind of kinds) {
    const body = RENDERERS[kind]?.();
    if (!body) {
      console.error(`✖ 未知生成块类型：${kind}`);
      missing++;
      continue;
    }
    const r = replaceBlock(text, kind, body);
    if (!r.found) {
      console.error(`✖ ${rel} 缺少 ${kind} 标记块`);
      missing++;
      continue;
    }
    text = r.text;
    if (r.changed) dirty = true;
  }

  if (dirty) {
    stale++;
    if (CHECK) {
      console.error(`✖ ${rel} 的生成块与 rules.json 不一致`);
    } else {
      fs.writeFileSync(file, text);
      written++;
      console.log(`▸ 已更新 ${rel}`);
    }
  }
}

if (CHECK) {
  if (stale || missing) {
    console.error(`\n生成块检查未通过：${stale} 处过期，${missing} 处缺失`);
    process.exit(1);
  }
  console.log(`✓ 生成块与 rules.json 一致（${rules.rules.length} 条规则 / ${Object.keys(rules.codes).length} 个码）`);
} else {
  console.log(`\n${written} 个文件已更新；${stale - written} 处无变化`);
}
