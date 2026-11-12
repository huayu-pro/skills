/**
 * diff.mjs — 两张图的逐像素比对 + 热力图
 *
 * 在浏览器里用 canvas 做，不引第三方依赖（pixelmatch 那类库的思路，
 * 但我们只需要"差异百分比 + 一张红点热力图"）。
 * 两张图先各自缩放到 1280×720 再比，避免 2x 预览图和 1x 反渲图尺寸不一致。
 */
import fs from 'node:fs';

const THRESHOLD = 48; // 单通道差超过这个值才算"不同像素"

export async function diffPng(page, pathA, pathB, outPath, { width = 1280, height = 720 } = {}) {
  const a = fs.readFileSync(pathA).toString('base64');
  const b = fs.readFileSync(pathB).toString('base64');

  const res = await page.evaluate(
    async ({ a, b, W, H, TH }) => {
      const load = (src) =>
        new Promise((res, rej) => {
          const img = new Image();
          img.onload = () => res(img);
          img.onerror = rej;
          img.src = 'data:image/png;base64,' + src;
        });

      const [ia, ib] = await Promise.all([load(a), load(b)]);

      const draw = (img) => {
        const c = new OffscreenCanvas(W, H);
        const ctx = c.getContext('2d', { willReadFrequently: true });
        ctx.imageSmoothingQuality = 'high';
        ctx.drawImage(img, 0, 0, W, H);
        return ctx.getImageData(0, 0, W, H).data;
      };

      const da = draw(ia);
      const db = draw(ib);

      const heat = new OffscreenCanvas(W, H);
      const hctx = heat.getContext('2d');
      const hd = hctx.createImageData(W, H);

      let diff = 0;
      for (let i = 0; i < da.length; i += 4) {
        const dr = Math.abs(da[i] - db[i]);
        const dg = Math.abs(da[i + 1] - db[i + 1]);
        const dbl = Math.abs(da[i + 2] - db[i + 2]);
        const d = Math.max(dr, dg, dbl);
        const p = i / 4;
        const x = p % W;
        const y = (p / W) | 0;
        if (d > TH) {
          diff++;
          hd.data[i] = 220;
          hd.data[i + 1] = 30;
          hd.data[i + 2] = 30;
          hd.data[i + 3] = 255;
        } else {
          // 相同的部分画成浅灰底，方便看位置
          const g = 235;
          hd.data[i] = g;
          hd.data[i + 1] = g;
          hd.data[i + 2] = g;
          hd.data[i + 3] = 255;
        }
      }
      hctx.putImageData(hd, 0, 0);

      const blob = await heat.convertToBlob({ type: 'image/png' });
      const buf = await blob.arrayBuffer();
      let bin = '';
      const bytes = new Uint8Array(buf);
      for (let i = 0; i < bytes.length; i++) bin += String.fromCharCode(bytes[i]);

      return { ratio: diff / (W * H), heat: btoa(bin) };
    },
    { a, b, W: width, H: height, TH: THRESHOLD },
  );

  if (outPath) fs.writeFileSync(outPath, Buffer.from(res.heat, 'base64'));
  return { ratio: res.ratio };
}
