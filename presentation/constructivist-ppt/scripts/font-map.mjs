#!/usr/bin/env node
/**
 * font-map.mjs — 事后批量换字体
 *
 *   node scripts/font-map.mjs deck.pptx --map "微软雅黑=思源黑体 CN" --map "Consolas=JetBrains Mono" -o out.pptx
 *   node scripts/font-map.mjs deck.pptx --list          # 看看里面用了哪些字体
 *
 * 用途：客户机器上没某个字体时，把整份 deck 一次性换掉，不用重新编译。
 * 直接改 ppt/slides/*.xml 与 ppt/notesSlides/*.xml 里的 typeface 属性。
 */
import fs from 'node:fs';
import path from 'node:path';
import { createRequire } from 'node:module';

const require = createRequire(import.meta.url);
const JSZip = require('jszip');

function parseArgs(argv) {
  const a = { _: [], map: [] };
  for (let i = 0; i < argv.length; i++) {
    const t = argv[i];
    if (t.startsWith('-') && t !== '-') {
      const k = t.replace(/^--?/, '');
      const v = argv[i + 1] && !argv[i + 1].startsWith('-') ? argv[++i] : true;
      if (k === 'map') a.map.push(v);
      else a[k] = v;
    } else a._.push(t);
  }
  return a;
}

const args = parseArgs(process.argv.slice(2));
const input = args._[0];
if (!input) {
  console.error('用法: node scripts/font-map.mjs <deck.pptx> [--map "A=B"] [--list] [-o out.pptx]');
  process.exit(1);
}
const out = path.resolve(args.o || input.replace(/\.pptx$/i, '') + '_fontmap.pptx');

const buf = fs.readFileSync(path.resolve(input));
const zip = await JSZip.loadAsync(buf);

const targets = Object.keys(zip.files).filter((n) => /^ppt\/(slides|notesSlides|slideMasters|slideLayouts)\/.*\.xml$/.test(n));

const fonts = new Map();
for (const name of targets) {
  const xml = await zip.file(name).async('string');
  for (const m of xml.matchAll(/typeface="([^"]+)"/g)) {
    fonts.set(m[1], (fonts.get(m[1]) || 0) + 1);
  }
}

if (args.list || !args.map.length) {
  console.log(`\n${input} 里用到的字体：\n`);
  [...fonts.entries()].sort((a, b) => b[1] - a[1]).forEach(([f, n]) => console.log(`  ${String(n).padStart(4)}  ${f}`));
  if (!args.map.length) {
    console.log('\n加 --map "旧=新" 才会改写。');
    process.exit(0);
  }
}

const mapping = new Map();
for (const pair of args.map) {
  const [from, to] = String(pair).split('=');
  if (!from || !to) {
    console.error(`--map 格式错误: ${pair}（应为 "旧字体=新字体"）`);
    process.exit(1);
  }
  mapping.set(from.trim(), to.trim());
}

let changed = 0;
for (const name of targets) {
  let xml = await zip.file(name).async('string');
  const before = xml;
  for (const [from, to] of mapping) {
    xml = xml.split(`typeface="${from}"`).join(`typeface="${to}"`);
  }
  if (xml !== before) {
    zip.file(name, xml);
    changed++;
  }
}

const outBuf = await zip.generateAsync({ type: 'nodebuffer', compression: 'DEFLATE' });
fs.writeFileSync(out, outBuf);
console.log(`\n✔ 改写 ${changed} 个部件 → ${path.basename(out)}`);
for (const [from, to] of mapping) console.log(`  ${from} → ${to}`);
if (![...fonts.keys()].some((f) => mapping.has(f))) {
  console.log('\n⚠ 注意：map 里的旧字体在原文件里没有出现，可能写错了。');
}
