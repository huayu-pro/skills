#!/usr/bin/env node
/**
 * gen-themes.mjs — assets/themes.json → deck.css 主题块 + palettes.md 表
 *
 *   node scripts/gen-themes.mjs
 *   node scripts/gen-themes.mjs --check
 */
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const HERE = path.dirname(fileURLToPath(import.meta.url));
const ROOT = path.resolve(HERE, '..');
const CHECK = process.argv.includes('--check');
const themesPath = path.join(ROOT, 'assets', 'themes.json');
const cssPath = path.join(ROOT, 'assets', 'deck.css');
const palettesPath = path.join(ROOT, 'references', 'palettes.md');

const data = JSON.parse(fs.readFileSync(themesPath, 'utf8'));
const required = ['bg', 'fg', 'pop', 'alt', 'mute'];
for (const [id, t] of Object.entries(data.themes)) {
  // id 只管格式；合不合法由 substyles 登记表决定（单一真相源，不在脚本里点名主题）
  if (!/^theme-[a-z][a-z0-9-]*$/.test(id)) throw new Error(`主题 id 非法：${id}`);
  if (!data.substyles[t.substyle]) throw new Error(`${id} 的 substyle ${t.substyle} 未登记`);
  for (const k of required) {
    if (!/^#[0-9A-Fa-f]{6}$/.test(t.tokens[k] || '')) throw new Error(`${id}.${k} 不是 6 位 hex`);
  }
}

const cssBlock = Object.entries(data.themes).map(([id, t]) => {
  const p = t.tokens;
  return `.${id} {\n  --bg:   ${p.bg};\n  --fg:   ${p.fg};\n  --pop:  ${p.pop};\n  --alt:  ${p.alt};\n  --mute: ${p.mute};\n}`;
}).join('\n');

const rows = Object.entries(data.themes).map(([id, t]) => {
  const p = t.tokens;
  return `| \`${id}\` | ${t.substyle} · ${t.name} | \`${p.bg}\` | \`${p.fg}\` | \`${p.pop}\` | \`${p.alt}\` | \`${p.mute}\` | ${t.texture} | ${t.use} |`;
}).join('\n');

const substyleBlocks = Object.entries(data.substyles).map(([key, s]) => {
  const rows2 = s.themes.map((id) => {
    const t = data.themes[id];
    return `| \`${id}\` | ${t.name} | ${t.area} | ${t.rules.join('；')} |`;
  }).join('\n');
  return `### ${key} · ${s.name}

${s.summary}

**气质**：${s.mood}　**适合**：${s.use}

| 主题 | 名称 | 面积配方（bg/fg/pop/alt） | 硬规则 |
|---|---|---|---|
${rows2}`;
}).join('\n\n');

const paletteBlock = `### 速查表

| 主题 | 子风格 | bg 纸 | fg 主墨 | pop 爆点 | alt 次墨 | mute 微字 | 纹理 | 适合 |
|---|---|---|---|---|---|---|---|---|
${rows}

${substyleBlocks}`;

function replaceBlock(text, begin, end, body, file) {
  const start = text.indexOf(begin);
  const stop = text.indexOf(end, start + begin.length);
  if (start === -1 || stop === -1) throw new Error(`${file} 缺生成块标记 ${begin} / ${end}`);
  return text.slice(0, start) + begin + '\n' + body + '\n' + end + text.slice(stop + end.length);
}

const THEMES_BEGIN = '/* THEMES:BEGIN 由 scripts/gen-themes.mjs 生成，勿手改 */';
const THEMES_END = '/* THEMES:END */';
const PAL_BEGIN = '<!-- PALETTES:BEGIN 由 scripts/gen-themes.mjs 生成，勿手改 -->';
const PAL_END = '<!-- PALETTES:END -->';

const css = fs.readFileSync(cssPath, 'utf8');
const nextCss = replaceBlock(css, THEMES_BEGIN, THEMES_END, cssBlock, 'assets/deck.css');
const pal = fs.readFileSync(palettesPath, 'utf8');
const nextPal = replaceBlock(pal, PAL_BEGIN, PAL_END, paletteBlock, 'references/palettes.md');

if (CHECK) {
  let bad = false;
  if (css !== nextCss) { console.error('✖ deck.css 主题块与 themes.json 不一致'); bad = true; }
  if (pal !== nextPal) { console.error('✖ palettes.md 与 themes.json 不一致'); bad = true; }
  if (bad) process.exit(1);
  console.log('✓ themes 已同步');
  process.exit(0);
}
fs.writeFileSync(cssPath, nextCss);
fs.writeFileSync(palettesPath, nextPal);
console.log('▸ 已更新 assets/deck.css 与 references/palettes.md');
