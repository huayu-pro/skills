#!/usr/bin/env node
/**
 * gen-textures.mjs — 确定性生成 assets/textures/ 下的整幅纹理 PNG
 *
 *   node scripts/gen-textures.mjs
 *
 * deck.css 引用 textures/grain.png 与 textures/halftone.png（.grain / .halftone
 * 的背景图）。这两个文件必须存在，否则 ASSET_REF 报错、A 子风格渲染缺层。
 * 用 ImageMagick 生成，固定 seed，同一环境两次输出逐字节一致；透明度直接
 * 烘焙进 alpha（约一成上下的墨量），转换器原样搬进 PPTX，不要写 CSS opacity。
 */
import fs from 'node:fs';
import path from 'node:path';
import { spawnSync } from 'node:child_process';
import { fileURLToPath } from 'node:url';

const HERE = path.dirname(fileURLToPath(import.meta.url));
const ROOT = path.resolve(HERE, '..');
const OUT_DIR = path.join(ROOT, 'assets', 'textures');

const IM = (() => {
  for (const bin of ['magick', 'convert']) {
    const r = spawnSync(bin, ['-version'], { encoding: 'utf8' });
    if (r.status === 0) return { bin, v7: bin === 'magick' && !/Q16 .* 6\./.test(r.stdout || '') };
  }
  console.error('✖ 找不到 ImageMagick（magick / convert 都不行）');
  process.exit(1);
})();

function im(args) {
  const cmd = IM.v7 ? [IM.bin, ...args] : [IM.bin, ...args];
  const r = spawnSync(cmd[0], cmd.slice(1), { encoding: 'utf8' });
  if (r.status !== 0) {
    console.error(`✖ ${cmd.join(' ')}\n${r.stderr}`);
    process.exit(1);
  }
}

fs.mkdirSync(OUT_DIR, { recursive: true });

/* 为什么产 SVG 而不是 PNG：发布平台不接受二进制文件，而 deck.css 又必须引用到
   真实存在的纹理（ASSET_REF 会校验，A 子风格渲染必须带颗粒）。SVG 是纯文本，
   几百字节，能满足两者。PPTX 侧由 build-deck.mjs 在装配前用浏览器栅格化成
   临时 PNG——PPTX 的图片槽只认 PNG/JPEG，直接塞 SVG 会产出打不开的文件。 */

/* grain：纸颗粒。feTurbulence 出均匀噪声，feColorMatrix 去色，
   feComponentTransfer 把 alpha 离散成有限档位——对应 PNG 配方的 -posterize 4。 */
const grain = `<svg xmlns="http://www.w3.org/2000/svg" width="1280" height="720" viewBox="0 0 1280 720">
  <filter id="grain-noise" x="0" y="0" width="100%" height="100%">
    <feTurbulence type="fractalNoise" baseFrequency="0.9" numOctaves="1" seed="42" stitchTiles="stitch"/>
    <feColorMatrix type="saturate" values="0"/>
    <feComponentTransfer><feFuncA type="discrete" tableValues="0 0 0 0 0.28"/></feComponentTransfer>
  </filter>
  <rect width="1280" height="720" fill="#000" filter="url(#grain-noise)" opacity="0.5"/>
</svg>
`;
fs.writeFileSync(path.join(OUT_DIR, 'grain.svg'), grain);

/* halftone：12px 间距、半径 3.4px 的规则网点屏，严格对齐网格。 */
const halftone = `<svg xmlns="http://www.w3.org/2000/svg" width="1280" height="720" viewBox="0 0 1280 720">
  <defs>
    <pattern id="ht-dot" width="12" height="12" patternUnits="userSpaceOnUse">
      <circle cx="6" cy="6" r="3.4" fill="#000" fill-opacity="0.5"/>
    </pattern>
  </defs>
  <rect width="1280" height="720" fill="url(#ht-dot)"/>
</svg>
`;
fs.writeFileSync(path.join(OUT_DIR, 'halftone.svg'), halftone);

for (const f of ['grain.svg', 'halftone.svg']) {
  const p = path.join(OUT_DIR, f);
  const size = fs.statSync(p).size;
  console.log(`▸ ${path.relative(ROOT, p)}  ${size} B`);
}
