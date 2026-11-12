/**
 * units.mjs — 单一单位入口
 *
 * 画布 1280×720 px = 13.333×7.5 in @96dpi。
 * pptxgenjs 有一条致命启发式：数值 >100 会被当作"已经是 EMU"直接透传，
 * 1280 会变成 1280 EMU ≈ 0.0014 英寸，形状缩成一个点且不报错。
 * 所以所有几何必须过这个文件，绝不把 px 直接交给 add*()。
 */

export const DPI = 96;
export const CANVAS = { w: 1280, h: 720, in: { w: 1280 / 96, h: 720 / 96 } };
export const EMU_PER_IN = 914400;
export const PX_PER_PT = 96 / 72;

/** px → 英寸。这是唯一允许把 px 交给 pptxgenjs 的通道。 */
export function px2in(px) {
  const v = px / DPI;
  if (!Number.isFinite(v)) throw new Error(`px2in: 非法数值 ${px}`);
  if (Math.abs(v) > 20) throw new Error(`px2in: ${px}px → ${v}in 超出画布量级，检查是否误传了别的东西`);
  return round(v, 4);
}

/** px → pt（字号、行距、字距）。 */
export function px2pt(px) {
  const v = px * 0.75;
  if (!Number.isFinite(v)) throw new Error(`px2pt: 非法数值 ${px}`);
  return round(v, 2);
}

/** pt → px，回渲时用。 */
export function pt2px(pt) {
  return round(pt / 0.75, 2);
}

/** px → EMU，回渲与自检用。 */
export function px2emu(px) {
  return Math.round(px * (EMU_PER_IN / DPI));
}

export function round(v, digits = 3) {
  const f = 10 ** digits;
  return Math.round(v * f) / f;
}

/** 旋转角归一化到 [0,360)，pptxgenjs 只减一次 360，不归一化会写出 720。 */
export function normDeg(d) {
  const v = ((d % 360) + 360) % 360;
  return round(v, 2);
}

/** 颜色：#RRGGBB / #RGB / rgb() → RRGGBB。返回 null 表示透明。 */
export function toHex(input) {
  if (!input) return null;
  const s = String(input).trim();
  if (s === 'transparent' || s === 'none') return null;
  if (s.startsWith('#')) {
    let h = s.slice(1);
    if (h.length === 3) h = h.split('').map((c) => c + c).join('');
    if (h.length === 4) h = h.slice(0, 3).split('').map((c) => c + c).join('');
    if (h.length !== 6) return null;
    return h.toUpperCase();
  }
  const m = s.match(/^rgba?\(([^)]+)\)$/i);
  if (m) {
    const parts = m[1].split(/[,\s/]+/).filter(Boolean);
    const a = parts[3] === undefined ? 1 : parseFloat(parts[3]);
    if (a === 0) return null;
    const to2 = (v) => Math.max(0, Math.min(255, Math.round(parseFloat(v)))).toString(16).padStart(2, '0');
    return (to2(parts[0]) + to2(parts[1]) + to2(parts[2])).toUpperCase();
  }
  return null;
}

/** 相对亮度与对比度（WCAG）。 */
export function relLuminance(hex) {
  const h = String(hex).replace('#', '');
  const rgb = [0, 2, 4].map((i) => parseInt(h.slice(i, i + 2), 16) / 255);
  const lin = rgb.map((c) => (c <= 0.03928 ? c / 12.92 : ((c + 0.055) / 1.055) ** 2.4));
  return 0.2126 * lin[0] + 0.7152 * lin[1] + 0.0722 * lin[2];
}

export function contrast(a, b) {
  if (!a || !b) return 21;
  const la = relLuminance(a);
  const lb = relLuminance(b);
  const hi = Math.max(la, lb);
  const lo = Math.min(la, lb);
  return round((hi + 0.05) / (lo + 0.05), 2);
}
