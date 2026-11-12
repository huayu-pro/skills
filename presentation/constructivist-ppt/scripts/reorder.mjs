#!/usr/bin/env node
/**
 * reorder.mjs — 增删页、重排页序，同时保持 plan 与 deck 同步
 *
 *   node scripts/reorder.mjs plan.json --move 5:2            # 把第 5 页挪到第 2 位
 *   node scripts/reorder.mjs plan.json --drop 7              # 删掉第 7 页
 *   node scripts/reorder.mjs plan.json --duplicate 3 --after 3   # 复制第 3 页
 *   node scripts/reorder.mjs plan.json --list                # 只看当前页序
 *
 * 为什么需要它：早先改结构只能改骨架文件再整份重新生成（SKILL.md 原话），
 * 单页的插、删、换位没有脚本支持，只能手改 plan.json 再全量 scaffold——
 * 手改数组最容易把 id 与页序弄错，而 plan.mjs 只查重复 id，查不出错位。
 *
 * 本脚本只改 plan.json；改完必须重跑 scaffold 重新出 deck：
 *   node scripts/scaffold.mjs plan.json -o deck.html --force
 */
import fs from 'node:fs';
import path from 'node:path';

const argv = process.argv.slice(2);
const has = (n) => argv.includes(`--${n}`);
const getArg = (n, d = null) => {
  const i = argv.findIndex((a) => a === `--${n}`);
  if (i === -1) return d;
  const v = argv[i + 1];
  return v && !v.startsWith('-') ? v : true;
};
const WITH_VALUE = new Set(['--move', '--drop', '--duplicate', '--after', '--to', '-o', '--out']);
const positional = [];
for (let i = 0; i < argv.length; i++) {
  if (WITH_VALUE.has(argv[i])) { i++; continue; }
  if (argv[i].startsWith('-')) continue;
  positional.push(argv[i]);
}

const planPath = path.resolve(positional[0] || '');
if (!planPath || !fs.existsSync(planPath)) {
  console.error('用法: node scripts/reorder.mjs <plan.json> --move 5:2 | --drop 7 | --duplicate 3 --after 3 | --list');
  process.exit(2);
}
const plan = JSON.parse(fs.readFileSync(planPath, 'utf8'));
const slides = plan.slides || [];

if (has('list')) {
  slides.forEach((s, i) => console.log(`${String(i + 1).padStart(2, '0')}  ${s.id}  ${s.layout}  ${s.role}  ${s.claim || ''}`));
  process.exit(0);
}

const fail = (msg) => { console.error('✖ ' + msg); process.exit(1); };
const inRange = (n) => Number.isInteger(n) && n >= 1 && n <= slides.length;

let changed = false;

const move = getArg('move');
if (move && move !== true) {
  const [from, to] = String(move).split(':').map(Number);
  if (!inRange(from) || !inRange(to)) fail(`--move ${move}：页号必须在 1–${slides.length} 之间`);
  const [item] = slides.splice(from - 1, 1);
  slides.splice(to - 1, 0, item);
  changed = true;
  console.error(`✔ 第 ${from} 页挪到第 ${to} 位`);
}

const drop = getArg('drop');
if (drop && drop !== true) {
  const n = Number(drop);
  if (!inRange(n)) fail(`--drop ${drop}：页号必须在 1–${slides.length} 之间`);
  const [gone] = slides.splice(n - 1, 1);
  changed = true;
  console.error(`✔ 删除第 ${n} 页（${gone.id}）`);
}

const dup = getArg('duplicate');
if (dup && dup !== true) {
  const n = Number(dup);
  if (!inRange(n)) fail(`--duplicate ${dup}：页号必须在 1–${slides.length} 之间`);
  const after = Number(getArg('after', n));
  if (!inRange(after) && after !== n) fail(`--after ${after}：页号必须在 1–${slides.length} 之间`);
  const copy = JSON.parse(JSON.stringify(slides[n - 1]));
  // 复制页必须换新 id：plan.mjs 查重复 id，同 id 会直接报错
  const ids = new Set(slides.map((s) => s.id));
  let k = 2;
  while (ids.has(`${copy.id}c${k}`)) k++;
  copy.id = `${copy.id}c${k}`;
  slides.splice(after, 0, copy);
  changed = true;
  console.error(`✔ 复制第 ${n} 页 → 插在第 ${after} 页之后（新 id ${copy.id}）`);
}

if (!changed) {
  console.error('没有指定任何改动。可用：--move 5:2 / --drop 7 / --duplicate 3 --after 3 / --list');
  process.exit(2);
}

plan.slides = slides;
plan.durationMin = slides.reduce((n, s) => n + (Number(s.minutes) || 0), 0);
fs.writeFileSync(planPath, JSON.stringify(plan, null, 2) + '\n');

console.error(`\n当前页序（${slides.length} 页，合计 ${plan.durationMin.toFixed(1)} 分钟）：`);
slides.forEach((s, i) => console.error(`  ${String(i + 1).padStart(2, '0')}  ${s.id}  ${s.layout}  ${s.role}`));
console.error('\n下一步：node scripts/scaffold.mjs <plan.json> -o deck.html --force');
console.error('        node scripts/plan.mjs check <plan.json>');
process.exit(0);
