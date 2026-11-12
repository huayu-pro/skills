#!/usr/bin/env node
/**
 * prepare-image.mjs — 图片一键网点化（封装 references/image-prompts.md 的四步工序）
 *
 *   node scripts/prepare-image.mjs src.jpg -o out.png [--width 600] [--dot 10] [--radius 3]
 *                                  [--level 12%,88%] [--threshold 45%] [--invert]
 *
 * 四步：高反差单色 → 生成网点瓦片 → 平铺 → 用剪影当遮罩求交，输出「黑点 + 透明底」PNG。
 * 抠图不在本脚本内：纯色背景可先自行 convert -fuzz 去底，复杂背景请用专门的分割工具。
 *
 * 为什么需要它：references/image-prompts.md 里是 7 条手敲 ImageMagick 命令，
 * 顺序、文件名、中间产物都得自己对上；漏一步就得到一张不是网点的图。
 */
import fs from 'node:fs';
import path from 'node:path';
import os from 'node:os';
import { spawnSync } from 'node:child_process';

const argv = process.argv.slice(2);
const getArg = (n, d = null) => {
  // 同时接受 --name 与 -name：getArg('o') 要能命中 -o
  const i = argv.findIndex((a) => a === `--${n}` || a === `-${n}`);
  if (i === -1) return d;
  const v = argv[i + 1];
  return v && !v.startsWith('-') ? v : true;
};
const has = (n) => argv.includes(`--${n}`);
const WITH_VALUE = new Set(['-o', '--out', '--width', '--dot', '--radius', '--level', '--threshold']);
const positional = [];
for (let i = 0; i < argv.length; i++) {
  if (WITH_VALUE.has(argv[i])) { i++; continue; }
  if (argv[i].startsWith('-')) continue;
  positional.push(argv[i]);
}

const src = path.resolve(positional[0] || '');
if (!src || !fs.existsSync(src)) {
  console.error('用法: node scripts/prepare-image.mjs <src.jpg|png> -o out.png [--width 600] [--dot 10] [--radius 3]');
  console.error('  把照片压成「两色油墨能印」的网点图：高反差 → 网点瓦片 → 平铺 → 遮罩求交。');
  console.error('  抠图不在本脚本内（复杂背景请先用专门的分割工具出 alpha）。');
  process.exit(2);
}
const outArg = getArg('o') || getArg('out');
if (!outArg || outArg === true) {
  console.error('✖ 需要 -o <输出.png>');
  process.exit(2);
}
const out = path.resolve(outArg);

const width = Number(getArg('width', 600));
const dot = Number(getArg('dot', 10));
const radius = Number(getArg('radius', 3));
const level = String(getArg('level', '12%,88%'));
const threshold = getArg('threshold', null);
const invert = has('invert');

for (const [name, v] of [['--width', width], ['--dot', dot], ['--radius', radius]]) {
  if (!Number.isFinite(v) || v <= 0) {
    console.error(`✖ ${name} 必须是正数，收到 ${v}`);
    process.exit(2);
  }
}
if (radius >= dot / 2) {
  console.error(`✖ --radius ${radius} 必须小于 --dot/2（${dot / 2}）：点比格子还大就糊成一片，不是网点。`);
  process.exit(2);
}

// magick 7 优先，convert 6 兜底；两者参数语法一致
const IM = ['magick', 'convert'].find((c) => {
  const r = spawnSync(c, ['-version'], { encoding: 'utf8' });
  return r.status === 0;
});
if (!IM) {
  console.error('✖ 找不到 ImageMagick。安装：sudo apt install imagemagick（或 brew install imagemagick）');
  process.exit(2);
}

const tmp = fs.mkdtempSync(path.join(os.tmpdir(), 'prep-img-'));
const step = (label, args) => {
  const r = spawnSync(IM, args, { encoding: 'utf8' });
  if (r.status !== 0) {
    console.error(`✖ 第 ${label} 步失败：${IM} ${args.join(' ')}`);
    if (r.stderr) console.error('  ' + r.stderr.trim().split('\n').slice(0, 3).join('\n  '));
    fs.rmSync(tmp, { recursive: true, force: true });
    process.exit(1);
  }
};

try {
  const duo = path.join(tmp, 'duo.png');
  const mask = path.join(tmp, 'mask.png');
  const tile = path.join(tmp, 'tile.png');
  const dots = path.join(tmp, 'dots.png');

  // 1. 高反差单色：暗部压死、亮部提纯，中间调只剩一条窄带
  const duoArgs = [src, '-colorspace', 'Gray', '-level', level, '-modulate', '100,0'];
  if (threshold && threshold !== true) duoArgs.push('-threshold', String(threshold));
  if (invert) duoArgs.push('-negate');
  duoArgs.push(duo);
  step('1 高反差单色', duoArgs);

  // 2. 剪影：白主体、黑底（网点只留在主体里）
  step('2 剪影', [duo, '-threshold', '50%', '-negate', mask]);

  // 3. 网点瓦片：黑底上一个白点
  step('3 网点瓦片', ['-size', `${dot}x${dot}`, 'xc:black', '-fill', 'white',
    '-draw', `circle ${dot / 2},${dot / 2} ${dot / 2},${dot / 2 + radius}`, tile]);

  // 4. 平铺到输出尺寸
  step('4 平铺', ['-size', `${width}x${width}`, `tile:${tile}`, dots]);

  // 5. 求交：白点只留在剪影里
  const alpha = path.join(tmp, 'alpha.png');
  step('5 求交', [dots, mask, '-compose', 'Multiply', '-composite', alpha]);

  // 6. 输出「黑点 + 透明底」（分两步：CopyOpacity 需要独立的一次合成）
  step('6 成品', ['-size', `${width}x${width}`, 'xc:black', alpha,
    '-alpha', 'off', '-compose', 'CopyOpacity', '-composite',
    '-depth', '8', '-define', 'png:color-type=6', out]);

  const stat = fs.statSync(out);
  console.log(`✔ ${path.basename(out)}  ${width}×${width}  ${(stat.size / 1024).toFixed(1)} KB`);
  console.log(`  网点 ${dot}px / 半径 ${radius}px / 反差 ${level}${threshold ? ` / 二值 ${threshold}` : ''}${invert ? ' / 反相' : ''}`);
  console.log('  中间产物：', tmp);
} finally {
  if (!has('keep')) fs.rmSync(tmp, { recursive: true, force: true });
}
process.exit(0);
