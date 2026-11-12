#!/usr/bin/env node
/**
 * gen-layout-docs.mjs — 从 layouts.json + 模板生成 references/layout-specs.md
 *
 *   node scripts/gen-layout-docs.mjs
 *   node scripts/gen-layout-docs.mjs --check
 */
import fs from 'node:fs';
const existsSync = fs.existsSync;
import path from 'node:path';
import { loadLayouts, expandSlots, readTemplate, SKILL_ROOT } from './lib/layouts.mjs';

const CHECK = process.argv.includes('--check');
const OUT = path.join(SKILL_ROOT, 'references', 'layout-specs.md');
const cat = loadLayouts();

const roleRows = [...new Set(cat.layouts.flatMap((l) => l.roles))]
  .sort((a, b) => cat.roles.indexOf(a) - cat.roles.indexOf(b))
  .map((role) => {
    const ids = cat.layouts.filter((l) => l.roles.includes(role)).map((l) => l.id);
    return `| \`${role}\` | ${ids.join(' / ')} |`;
  });

function styleOf(tpl, name) {
  const re = new RegExp(`<[^>]*\\bdata-slot="${escapeRe(name)}"[^>]*\\bstyle="([^"]*)"`);
  const m = tpl.match(re);
  if (!m) return '';
  const style = m[1];
  const get = (k) => {
    const mm = style.match(new RegExp(`(?:^|;)\\s*${k}\\s*:\\s*([^;]+)`));
    return mm ? mm[1].trim() : '';
  };
  const parts = [];
  const left = get('left'); const top = get('top');
  const width = get('width'); const height = get('height');
  if (left && top) parts.push(`x ${left} / y ${top}`);
  else if (left) parts.push(`x ${left}`);
  if (width) parts.push(`w ${width}`);
  if (height) parts.push(`h ${height}`);
  if (!parts.length) return '随父级 / group 单元';
  return parts.join(' · ');
}

function escapeRe(s) {
  return s.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
}

const blocks = cat.layouts.map((l) => {
  const idx = cat.layouts.findIndex((x) => x.id === l.id) + 1;
  const tpl = readTemplate(l.id);
  const slots = [...expandSlots(l).entries()];
  const normal = slots.filter(([name]) => !name.includes('.'));
  const groups = Object.entries(l.groups || {});
  const rows = normal.map(([name, s]) => {
    const req = s.required ? '●' : '○';
    const lines = s.maxLines ? String(s.maxLines) : '—';
    return `| \`${name}\` | ${s.form} | ${req} | ${s.maxCJK ?? '—'} | ${lines} | ${styleOf(tpl, name)} |`;
  }).join('\n');
  const groupBlocks = groups.map(([gname, g]) => {
    const items = Object.entries(g.slots).map(([name, s]) => {
      const req = '●';
      const lines = s.maxLines ? String(s.maxLines) : '—';
      return `| \`${gname}.N.${name}\` | ${s.form} | ${req} | ${s.maxCJK ?? '—'} | ${lines} | 随 group 单元 |`;
    }).join('\n');
    const range = g.exact ? `固定 ${g.count}` : `${g.min || g.count}–${g.max || g.count}`;
    return `**${gname}**（${range} 项）\n\n| 槽位 | 形式 | 必填 | 字数上限 | 行数 | 坐标/说明 |\n|---|---|---|---|---|---|\n${items}`;
  }).join('\n\n');
  return `## ${l.id} · ${l.name}

- family：\`${l.family}\` · roles：${l.roles.map((r) => `\`${r}\``).join(' / ')} · motif：\`${l.motif}\`
- 骨架：\`assets/layouts/${l.id}.html\`（缩略图是生成物，见「画廊」一节的生成命令）

${existsSync(path.join(SKILL_ROOT, 'examples', 'layout-gallery', `slide-${String(idx).padStart(2, '0')}.png`))
  ? `![${l.id}](../examples/layout-gallery/slide-${String(idx).padStart(2, '0')}.png)`
  : '_缩略图未生成：生成物，发布包不含二进制。生成命令见下方「画廊」一节。'}

| 槽位 | 形式 | 必填 | 字数上限 | 行数 | 坐标/说明 |
|---|---|---|---|---|---|
${rows}
${groupBlocks ? `\n${groupBlocks}` : ''}
`;
});

const doc = `# 版式槽位表

> 本文件由 \`scripts/gen-layout-docs.mjs\` 从 \`assets/layouts.json\` 与 \`assets/layouts/L*.html\` 生成，勿手改。
> 坐标以骨架 HTML 为准；这里的 x/y/w/h 是从模板内联样式抽出的辅助值。

## 怎么用

1. 先写 \`deck.plan.json\`，用 \`role\` 选叙事位置，用 \`layout\` 选骨架。
2. 跑 \`node scripts/plan.mjs check plan.json\`；再跑 \`node scripts/scaffold.mjs plan.json -o deck.html\`。
3. 想改坐标就改骨架文件，然后重新生成这份表和画廊；不要只改一页导致全局漂移。

槽位写法：每个可填元素一个 \`data-slot="name"\`，内容写 \`{{slot:name}}\`；可选块用 \`data-slot-block="name"\` 包起来，scaffold 会整块删除空块。

## 角色 → 版式

| role | 候选版式 |
|---|---|
${roleRows.join('\n')}

## 画廊

缩略图与联系表是**生成物**：发布包不含二进制文件，需要看图时本地跑一次即可。

\`\`\`bash
node scripts/scaffold.mjs --gallery examples/layout-gallery --force
node scripts/render.mjs examples/layout-gallery/deck.html --out examples/layout-gallery --sheet
\`\`\`



${existsSync(path.join(SKILL_ROOT, 'examples', 'layout-gallery', 'contact-sheet.png'))
  ? '![layout gallery](../examples/layout-gallery/contact-sheet.png)'
  : '_联系表未生成，跑上面的命令即可。_'}

${blocks.join('\n---\n\n')}
`;

if (CHECK) {
  const old = fs.existsSync(OUT) ? fs.readFileSync(OUT, 'utf8') : '';
  if (old !== doc) {
    console.error('✖ references/layout-specs.md 与 layouts.json/模板不一致；运行 node scripts/gen-layout-docs.mjs');
    process.exit(1);
  }
  console.log('✓ layout-specs.md 已同步');
  process.exit(0);
}
fs.writeFileSync(OUT, doc);
console.log(`▸ 已更新 ${path.relative(SKILL_ROOT, OUT)}`);
