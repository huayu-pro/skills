#!/usr/bin/env node
/**
 * validate.mjs — 交付前的版式体检
 *
 *   node scripts/validate.mjs <deck.html> [--slide N] [--strict] [--allow-forbid]
 *
 * 阈值与规则码全部来自 assets/rules.json（唯一真相源）；本文件不硬编码任何数值。
 * 改了 rules.json 之后跑 `node scripts/gen-rules-doc.mjs` 重新生成文档表格。
 */
import fs from 'node:fs';
import path from 'node:path';
import { loadRules, codeOrder, codeRule } from './rules.mjs';
import { loadLayouts, expandSlots } from './lib/layouts.mjs';
import { launchBrowser, openDeck } from './lib/browser.mjs';

const RULES = loadRules();
const T = RULES.thresholds;
let LAYOUTS;
try {
  LAYOUTS = loadLayouts();
} catch (err) {
  console.error(`✖ ${err.message}`);
  process.exit(2);
}
const LAYOUT_CTX = {
  roles: LAYOUTS.roles,
  layouts: LAYOUTS.layouts.map((l) => ({
    id: l.id,
    name: l.name,
    family: l.family,
    roles: l.roles,
    slots: l.slots,
    groups: l.groups || {},
    _slots: Object.fromEntries(expandSlots(l)),
  })),
};

function parseArgs(argv) {
  const a = { _: [] };
  for (let i = 0; i < argv.length; i++) {
    const t = argv[i];
    if (t.startsWith('-') && t !== '-') {
      const v = argv[i + 1] && !argv[i + 1].startsWith('-') ? argv[++i] : true;
      a[t.replace(/^--?/, '')] = v;
    } else a._.push(t);
  }
  return a;
}

const args = parseArgs(process.argv.slice(2));
const html = args._[0];
if (!html) {
  console.error('用法: node scripts/validate.mjs <deck.html> [--slide N] [--strict] [--allow-forbid]');
  process.exit(1);
}
const only = args.slide ? parseInt(args.slide, 10) : 0;
const STRICT = !!args.strict;
const ALLOW_FORBID = !!args['allow-forbid'];
const COMPAT = args.compat === 'v2';
const JSON_OUT = !!args.json;
const COMPAT_CODES = new Set(RULES.compat?.v2?.downgrade || []);

const issues = [];
const downgraded = [];   // --compat v2 降级的项：可见、单独计数，但不计入 strict 的失败
const forbidLevel = ALLOW_FORBID ? 'warn' : 'error';

/** v3 新检查在 --compat v2 下降级；旧检查保持原级别。
    降级的项单独收进 downgraded，而不是混进普通 warn：混进去的话 --strict 会把它们
    当失败（compat 失去意义），不混又会被淹没、无从审计。 */
function applyCompat(issue) {
  if (COMPAT && (issue.compat || COMPAT_CODES.has(issue.code))) {
    const out = { ...issue, level: issue.level === 'error' ? 'warn' : issue.level, downgraded: true };
    downgraded.push(out);
    return out;
  }
  return issue;
}

/* ────────────────────────────────────────────────────────────────
   静态检查：类名存在性（不需要浏览器）
   deck.css 是唯一来源；用了没定义的类，浏览器会静默 fallback，
   版式会莫名其妙地塌，而且最难查。
   ──────────────────────────────────────────────────────────────── */
function checkClasses() {
  const raw = fs.readFileSync(path.resolve(html), 'utf8');
  const link = raw.match(/<link[^>]+href=["']([^"']+\.css)["']/i);
  if (!link) {
    const hasInline = /<style[\s\S]*?<\/style>/i.test(raw);
    issues.push({
      page: 0,
      level: hasInline ? 'warn' : 'error',
      code: 'CLASS',
      msg: hasInline ? '没找到样式表 <link>，只看到内联 <style>，类名检查不完整' : '没找到样式表 <link>，无法检查类名',
      fix: '补上 <link href="../assets/deck.css">；类名 fallback 会让版式静默塌掉',
    });
    return;
  }
  const cssPath = path.resolve(path.dirname(path.resolve(html)), link[1]);
  if (!fs.existsSync(cssPath)) {
    issues.push({ page: 0, level: 'error', code: 'CLASS', msg: `样式表不存在：${link[1]}` });
    return;
  }
  const css = fs.readFileSync(cssPath, 'utf8');
  const defined = new Set();
  for (const m of css.matchAll(/\.(-?[A-Za-z_][\w-]*)/g)) defined.add(m[1]);

  const used = new Map();
  const body = raw.replace(/<style[\s\S]*?<\/style>/gi, '');
  for (const m of body.matchAll(/class=["']([^"']+)["']/g)) {
    for (const c of m[1].trim().split(/\s+/)) {
      if (c) used.set(c, (used.get(c) || 0) + 1);
    }
  }
  const missing = [...used.keys()].filter((c) => !defined.has(c));
  for (const c of missing) {
    issues.push({
      page: 0,
      level: 'error',
      code: 'CLASS',
      msg: `class "${c}" 在 ${path.basename(cssPath)} 里没有定义（用了 ${used.get(c)} 次），浏览器会 fallback 成默认样式`,
      fix: '拼写错了就改；确实需要新类就加到 deck.css，不要靠 inline 样式临时补',
    });
  }
}
checkClasses();

/* ────────────────────────────────────────────────────────────────
   浏览器检查
   ──────────────────────────────────────────────────────────────── */
const { browser, page } = await launchBrowser({ scale: 1 });
let result;
try {
  await openDeck(page, html);
  // elementsFromPoint 只看视口内，长 deck 必须先把视口拉到全高
  const deckHeight = await page.evaluate(() => document.documentElement.scrollHeight);
  await page.setViewportSize({ width: 1280, height: Math.min(deckHeight, 16000) });

  result = await page.evaluate((ctx) => {
    const { onlyPage, R, L } = ctx;
    const T = R.thresholds;
    const out = [];
    const W = R.canvas.w;
    const H = R.canvas.h;
    const CANVAS = W * H;
    const SAFE = R.canvas.safe;
    const LABEL_RE = /micro|meta|vlabel|barcode|folio/;
    const CJK_RE = /[\u4e00-\u9fa5]/g;

    const HEX = (s) => {
      if (!s) return null;
      const m = String(s).match(/rgba?\(([^)]+)\)/);
      if (!m) return null;
      const p = m[1].split(/[,\s/]+/).filter(Boolean);
      if (p[3] !== undefined && parseFloat(p[3]) < 0.05) return null;
      const t = (v) => Math.max(0, Math.min(255, Math.round(+v))).toString(16).padStart(2, '0');
      return (t(p[0]) + t(p[1]) + t(p[2])).toUpperCase();
    };
    /** 把 " #F2EDE3" / "#F2EDE3" 归一成 F2EDE3 */
    const TOK = (s) => (s ? String(s).trim().replace(/^#/, '').toUpperCase() : '');
    const LUM = (h) => {
      const c = [0, 2, 4].map((i) => parseInt(h.slice(i, i + 2), 16) / 255);
      const l = c.map((v) => (v <= 0.03928 ? v / 12.92 : ((v + 0.055) / 1.055) ** 2.4));
      return 0.2126 * l[0] + 0.7152 * l[1] + 0.0722 * l[2];
    };
    const CONTRAST = (a, b) => {
      const la = LUM(a);
      const lb = LUM(b);
      return (Math.max(la, lb) + 0.05) / (Math.min(la, lb) + 0.05);
    };
    const rotOf = (el) => {
      const t = getComputedStyle(el).transform;
      if (!t || t === 'none') return 0;
      try {
        const m = new DOMMatrix(t);
        return (Math.atan2(m.b, m.a) * 180) / Math.PI;
      } catch {
        return 0;
      }
    };
    /** 把角度折到 0–90，-11° 与 169° 是同一条轴线 */
    const axisOf = (deg) => {
      let a = ((deg % 180) + 180) % 180;
      if (a > 90) a -= 180;
      return Math.round(Math.abs(a) * 10) / 10;
    };
    const r1 = (v) => Math.round(v * 10) / 10;
    const CJK = (s) => (s.match(CJK_RE) || []).length;
    const isTexture = (el) => el.classList
      && (el.classList.contains('grain') || el.classList.contains('halftone'));

    /** 只收集自身文本流 + inline 后代，避免父容器把 block 子元素吞进文本框。 */
    const flowInk = (el) => {
      const rects = [];
      const collect = (node) => {
        if (node.nodeType === 3) {
          if (!node.textContent.trim()) return;
          const r = document.createRange();
          r.selectNodeContents(node);
          rects.push(...Array.from(r.getClientRects()).filter((x) => x.width > 0.5 && x.height > 0.5));
          return;
        }
        if (node.nodeType !== 1) return;
        if (node.tagName === 'BR') return;
        if (getComputedStyle(node).display !== 'inline') return;
        for (const c of node.childNodes) collect(c);
      };
      for (const c of el.childNodes) collect(c);
      if (!rects.length) return null;
      return {
        x: Math.min(...rects.map((x) => x.left)),
        y: Math.min(...rects.map((x) => x.top)),
        r: Math.max(...rects.map((x) => x.right)),
        b: Math.max(...rects.map((x) => x.bottom)),
        lineArea: rects.reduce((n, x) => n + x.width * x.height, 0),
        lines: new Set(rects.map((x) => Math.round(x.top))).size,
      };
    };

    const effOpacity = (el) => {
      let o = 1;
      let n = el;
      while (n && n !== document.documentElement) {
        const v = parseFloat(getComputedStyle(n).opacity);
        if (Number.isFinite(v)) o *= v;
        n = n.parentElement;
      }
      return o;
    };

    /** 单点背景：跳过透明纹理；图片/渐变返回 unknown，不拿 slide 底色冒充。 */
    const bgAtPoint = (x, y, sr, slideBg, textEl) => {
      const stack = document.elementsFromPoint(sr.left + x, sr.top + y);
      for (const node of stack) {
        if (node === textEl || (textEl.contains && textEl.contains(node))) continue;
        if (isTexture(node)) continue;
        const cs = getComputedStyle(node);
        const hasImg = node.tagName === 'IMG'
          || (cs.backgroundImage && cs.backgroundImage !== 'none' && !/gradient/i.test(cs.backgroundImage));
        if (hasImg) return { backdrop: null, unknown: true, cover: node };
        const bgc = HEX(cs.backgroundColor);
        if (bgc) return { backdrop: bgc, unknown: false, cover: null };
      }
      return { backdrop: slideBg, unknown: false, cover: null };
    };

    /** 采样点覆盖率：后序不透明元素盖住文字的比例。
        采样网格来自 rules.json 的 occlude.samples（3 → 3×3 九点）。 */
    const occlusionAt = (text, sr) => {
      const b = text.box;
      const n = Math.max(1, T.occlude.samples || 9);
      const k = Math.max(2, Math.round(Math.sqrt(n)));
      const axis = Array.from({ length: k }, (_, i) => 0.12 + (0.76 * i) / (k - 1));
      let hit = 0;
      for (const fx of axis) {
        for (const fy of axis) {
          const px = b.x + (b.r - b.x) * fx;
          const py = b.y + (b.b - b.y) * fy;
          const stack = document.elementsFromPoint(sr.left + px, sr.top + py);
          let above = true;
          for (const node of stack) {
            if (node === text.el || (text.el.contains && text.el.contains(node))) { above = false; break; }
            if (isTexture(node)) continue;
            const cs = getComputedStyle(node);
            const bgc = HEX(cs.backgroundColor);
            if (bgc && above) {
              // 只算 DOM 后序的覆盖物；祖先背景在栈里位于文字之后，不算遮挡
              const pos = text.el.compareDocumentPosition(node);
              if (pos & Node.DOCUMENT_POSITION_FOLLOWING) { hit++; break; }
            }
          }
        }
      }
      return hit;
    };

    const sections = Array.from(document.querySelectorAll('section.slide'));
    const structured = !!document.querySelector('.deck[data-structured]')
      || sections.some((s) => s.hasAttribute('data-layout'));
    const structureOk = !!document.querySelector('.deck[data-structure-ok]');
    const stats = [];
    const sigs = [];
    const folioSigs = [];
    const themeSeen = new Set();
    let firstThemePage = 0;

    sections.forEach((sec, idx) => {
      const pageNo = idx + 1;
      if (onlyPage && pageNo !== onlyPage) return;

      // 必须先滚进视口：elementsFromPoint 对视口外的点一律返回空栈，
      // 采样就会静默回落到 slide 底色——白字压黑块被判成"纸底白字"（假红），
      // 深字压墨底被判成"纸底深字"（假绿）。两种都是错的。
      sec.scrollIntoView({ block: 'start', inline: 'start' });
      const sr = sec.getBoundingClientRect();
      const slideBg = HEX(getComputedStyle(sec).backgroundColor) || 'FFFFFF';
      // 主题令牌：所有允许出现的颜色都必须出自这里
      const token = new Set([slideBg]);
      for (const role of R.palette.roles) {
        const v = TOK(getComputedStyle(sec).getPropertyValue(`--${role}`));
        if (v) token.add(v);
      }
      const labelOnly = TOK(getComputedStyle(sec).getPropertyValue(`--${R.palette.labelOnly}`));
      if (labelOnly) token.add(labelOnly);

      const theme = [...sec.classList].find((c) => c.startsWith('theme-')) || '';
      if (theme) {
        themeSeen.add(theme);
        if (!firstThemePage) firstThemePage = pageNo;
      }

      const texts = [];
      const blocks = [];
      const colors = new Set([slideBg]);
      const diagonals = [];
      let thinLines = 0;
      let textInkArea = 0;
      let forbidCount = 0;
      let forbiddenColor = null;
      const forbiddenColors = [];

      /* ---- 遍历：收集文本、色块、旋转、线条、禁止项 */
      const walk = (el, rotatedAncestor) => {
        if (el.classList.contains('ui')) return;
        const cs = getComputedStyle(el);
        if (cs.display === 'none' || cs.visibility === 'hidden') return;

        if (el !== sec) {
          /* ---- FORBID：转换器表达不了的 CSS，一律报错，不做静默降级 */
          const rawCls = (el.getAttribute && el.getAttribute('class')) || (typeof el.className === 'string' ? el.className : '');
          const tag = el.tagName.toLowerCase() + (el.id ? `#${el.id}` : '') + (rawCls ? `.${rawCls.split(/\s+/).slice(0, 2).join('.')}` : '');
          const rect0 = el.getBoundingClientRect();
          if (cs.backgroundImage && /gradient/i.test(cs.backgroundImage)) {
            forbidCount++;
            out.push({ page: pageNo, level: ctx.forbidLevel, code: 'FORBID', msg: `${tag} 用了渐变（gradient）——PPTX 无渐变填充，背景会被跳过`, fix: '删掉渐变；需要过渡就用实色块切分' });
          }
          if (cs.boxShadow && cs.boxShadow !== 'none') {
            forbidCount++;
            out.push({ page: pageNo, level: ctx.forbidLevel, code: 'FORBID', msg: `${tag} 用了 box-shadow`, fix: '删掉阴影；层级靠面积与字重' });
          }
          if (cs.textShadow && cs.textShadow !== 'none') {
            forbidCount++;
            out.push({ page: pageNo, level: ctx.forbidLevel, code: 'FORBID', msg: `${tag} 用了 text-shadow`, fix: '删掉文字阴影；重点靠字号与颜色' });
          }
          if (cs.transform && cs.transform !== 'none') {
            try {
              const m = new DOMMatrix(cs.transform);
              if (Math.abs(m.e) > 0.5 || Math.abs(m.f) > 0.5) {
                out.push({ page: pageNo, level: 'error', code: 'TRANSFORM', compat: true, msg: `${tag} 用了 translate()`, fix: '用 left/top 定位；translate 会让布局盒与 PPT 坐标脱节' });
              }
              const sc = Math.hypot(m.a, m.b);
              if (Math.abs(sc - 1) > 0.02 || Math.abs(m.a - m.d) > 0.002 || Math.abs(m.b + m.c) > 0.002) {
                out.push({ page: pageNo, level: 'error', code: 'TRANSFORM', compat: true, msg: `${tag} 用了 scale/skew`, fix: '只允许 rotate；缩放/斜切用真实尺寸与 polygon 重做' });
              }
              const o = cs.transformOrigin.split(' ').map(parseFloat);
              const cx = el.offsetWidth / 2;
              const cy = el.offsetHeight / 2;
              if (Math.abs(o[0] - cx) > 0.6 || Math.abs(o[1] - cy) > 0.6) {
                out.push({ page: pageNo, level: 'error', code: 'TRANSFORM', compat: true, msg: `${tag} 的 transform-origin 不在中心`, fix: '旋转原点必须是中心，否则 PPT 里会错位' });
              }
            } catch {}
          }
          if (cs.clipPath && cs.clipPath !== 'none' && !/^polygon\(/i.test(cs.clipPath)) {
            forbidCount++;
            out.push({ page: pageNo, level: ctx.forbidLevel, code: 'FORBID', msg: `${tag} 的 clip-path 不是 polygon()`, fix: '只支持 polygon()；其他裁切用 polygon 近似' });
          }
          const br = cs.borderTopLeftRadius;
          if (br && parseFloat(br) > 0) {
            const pct = String(br).trim().endsWith('%');
            const brPx = pct
              ? (parseFloat(br) / 100) * Math.min(rect0.width, rect0.height)
              : parseFloat(br);
            const isCircle = Math.abs(rect0.width - rect0.height) < 2
              && brPx >= Math.min(rect0.width, rect0.height) / 2 - 0.75;
            if (!isCircle) {
              forbidCount++;
              out.push({ page: pageNo, level: ctx.forbidLevel, code: 'FORBID', msg: `${tag} 用了 border-radius:${br}`, fix: '只有 50% 正圆能转换；其他圆角改成直角或 polygon' });
            }
          }
          if (el.tagName === 'IMG' && /^https?:/i.test(el.getAttribute('src') || '')) {
            forbidCount++;
            out.push({ page: pageNo, level: ctx.forbidLevel, code: 'FORBID', msg: `${tag} 用了远程图片`, fix: '先把图片下载到本地；PPTX 不会自动下载远程图' });
          }
          if (cs.backgroundImage && /url\(/i.test(cs.backgroundImage) && /https?:/i.test(cs.backgroundImage)) {
            forbidCount++;
            out.push({ page: pageNo, level: ctx.forbidLevel, code: 'FORBID', msg: `${tag} 的背景图是远程地址`, fix: '先把图片下载到本地，再引用相对路径' });
          }
          if (cs.filter && cs.filter !== 'none') {
            forbidCount++;
            out.push({ page: pageNo, level: ctx.forbidLevel, code: 'FORBID', msg: `${tag} 用了 filter`, fix: '删掉滤镜；颗粒用 .grain 纹理层' });
          }
          if (cs.mixBlendMode && cs.mixBlendMode !== 'normal') {
            forbidCount++;
            out.push({ page: pageNo, level: ctx.forbidLevel, code: 'FORBID', msg: `${tag} 用了 mix-blend-mode（${cs.mixBlendMode}）`, fix: '叠色预先把结果调成实色' });
          }
          if (cs.zIndex && cs.zIndex !== 'auto') {
            forbidCount++;
            out.push({ page: pageNo, level: ctx.forbidLevel, code: 'FORBID', msg: `${tag} 用了 z-index（${cs.zIndex}）`, fix: '只认 DOM 顺序；把元素挪到正确的先后' });
          }
          if (cs.position === 'fixed') {
            forbidCount++;
            out.push({ page: pageNo, level: ctx.forbidLevel, code: 'FORBID', msg: `${tag} 用了 position:fixed`, fix: '改成 absolute，坐标基于 .slide' });
          }
          for (const pe of ['::before', '::after']) {
            const pcs = getComputedStyle(el, pe);
            if (pcs && pcs.content && pcs.content !== 'none' && pcs.content !== 'normal') {
              forbidCount++;
              out.push({ page: pageNo, level: ctx.forbidLevel, code: 'FORBID', msg: `${tag} 用 ${pe} 画图形`, fix: '伪元素没有 DOM 盒子，转换器量不到；改成真实元素' });
            }
          }
          const lowerTag = el.tagName.toLowerCase();
          if (lowerTag === 'svg' || lowerTag === 'canvas') {
            forbidCount++;
            out.push({ page: pageNo, level: ctx.forbidLevel, code: 'FORBID', msg: `${tag} 是内联 <${lowerTag}>`, fix: 'SVG/Canvas 转不成形状；改成 .wedge / .sun / .band' });
          }
          if (rotatedAncestor && cs.transform && cs.transform !== 'none') {
            forbidCount++;
            out.push({ page: pageNo, level: ctx.forbidLevel, code: 'FORBID', msg: `${tag} 嵌套旋转（祖先与自身都转了）`, fix: 'PPT 没有 group；只保留一层旋转，子元素单独定位' });
          }
          if (el !== sec && cs.overflow !== 'visible'
              && (el.scrollHeight > el.clientHeight + 1 || el.scrollWidth > el.clientWidth + 1)) {
            forbidCount++;
            out.push({ page: pageNo, level: ctx.forbidLevel, code: 'FORBID', msg: `${tag} 的 overflow:hidden 真的裁掉了内容`, fix: '只有 .slide 允许裁切；删掉裁切，或让内容不超框' });
          }

          const rect = rect0;
          const area = rect.width * rect.height;
          const bg = HEX(cs.backgroundColor);
          const effOp = effOpacity(el);
          if (bg && effOp > 0 && effOp < T.opacity.shape) {
            out.push({
              page: pageNo, level: 'warn', code: 'OPACITY',
              msg: `${tag} 的有效 opacity ${effOp.toFixed(2)} 会被拍平成实色`,
              fix: '换成预混实色；PPTX 没有组透明度',
            });
          }

          // 色块（用于 BALANCE / INK）
          // 用布局盒面积，不用旋转后的 AABB：一条 120×900 的斜带转 18°
          // AABB 会膨胀到 350k，把细长结构误判成"第二大块"。
          const blockArea = (el.offsetWidth || rect0.width) * (el.offsetHeight || rect0.height);
          if (bg && blockArea > CANVAS * T.balance.minBlockAreaPct) {
            blocks.push({ area: blockArea, color: bg, cls: (el.className || '').toString().slice(0, 24) });
            if (!token.has(bg)) {
              forbiddenColor = bg;
            }
            colors.add(bg);
          }

          // 斜线（AXIS）
          const deg = rotOf(el);
          const clipped = cs.clipPath && cs.clipPath !== 'none';
          if ((Math.abs(deg) >= T.axis.minDeg || clipped) && area > T.classes.scanMinAreaPx) {
            // 楔形（clip-path）只有方向，没有可比较的角度，不参与"竞争角度"判定
            diagonals.push({
              deg: Math.abs(deg) >= T.axis.minDeg ? r1(deg) : null,
              axis: Math.abs(deg) >= T.axis.minDeg ? axisOf(deg) : null,
              clipped,
              area,
              w: rect.width,
              h: rect.height,
            });
          }

          // 细线（WEIGHT）
          const thin = ['Top', 'Right', 'Bottom', 'Left'].some((s) => {
            const w = parseFloat(cs[`border${s}Width`]);
            return w > 0 && w < T.weight.minLinePx && cs[`border${s}Style`] === 'solid';
          });
          const box1 = ((Math.round(rect.height) === 1 || Math.round(rect.width) === 1)
            || ((rect.height < T.weight.minLinePx || rect.width < T.weight.minLinePx) && !!bg)) && !!bg;
          if (thin || box1) thinLines++;
        }

        const hasOwn = Array.from(el.childNodes).some((n) => (
          (n.nodeType === 3 && n.textContent.trim())
          || (n.nodeType === 1 && getComputedStyle(n).display === 'inline' && n.textContent.trim())
        ));
        if (hasOwn && !['SCRIPT', 'STYLE'].includes(el.tagName)) {
          const size = parseFloat(cs.fontSize);
          const fi = flowInk(el);
          if (fi) {
            const ink = {
              x: fi.x - sr.left,
              y: fi.y - sr.top,
              r: fi.r - sr.left,
              b: fi.b - sr.top,
            };
            const isDisplay = size >= T.textArea.displayPx;
            // 只统计正文与标签；展示字本来就该占大，不能算"字多"
            if (!isDisplay) textInkArea += fi.lineArea;
            const eb = el.getBoundingClientRect();
            const box = {
              x: ink.x, y: ink.y, r: ink.r, b: ink.b,
              ex: eb.left - sr.left, ey: eb.top - sr.top, er: eb.right - sr.left, ebb: eb.bottom - sr.top,
            };
            const txt = el.textContent.trim();
            const cls = (el.className || '').toString();
            const isLabel = LABEL_RE.test(cls);
            const fg = HEX(cs.color);
            const isMute = !!(fg && labelOnly && fg === labelOnly);
            const effOp = effOpacity(el);
            texts.push({ el, cs, size, box, txt, cls, lines: fi.lines });
            if (effOp > 0 && effOp < T.opacity.text) {
              out.push({
                page: pageNo, level: 'error', code: 'OPACITY', compat: true,
                msg: `文字有效 opacity ${effOp.toFixed(2)}，PPTX 会拍平，与预览不一致：「${txt.slice(0, 14)}」`,
                fix: '文字必须不透明；需要弱化就用更浅的实色',
              });
            }
            if (fg && !isMute) {
              colors.add(fg);
              if (size >= T.ink.infoTextPx && !token.has(fg)) forbiddenColors.push(fg);
            }

            /* ---- MUTE：次墨只给非信息微字 */
            if (isMute && (size > T.font.labelPx || CJK(txt) > T.font.labelMaxCJK)) {
              out.push({
                page: pageNo, level: 'error', code: 'MUTE', compat: true,
                msg: `--mute 被用在 ${size}px / ${CJK(txt)} 汉字的文本上：「${txt.slice(0, 14)}」——次墨只给 ≤${T.font.labelPx}px 的页码/标签`,
                fix: '信息文本改用 --fg 或 --alt；--mute 不能做副标',
              });
            }

            /* ---- WRAP：展示字必须 nowrap，一行一个元素 */
            if (!isLabel && T.wrap.classes.some((c) => cls.split(/\s+/).includes(c))) {
              if (cs.whiteSpace !== 'nowrap') {
                out.push({
                  page: pageNo, level: 'error', code: 'WRAP',
                  msg: `展示字 ${cls.trim().split(/\s+/)[0]} 的 white-space 不是 nowrap（实际 ${cs.whiteSpace}），会自动折行`,
                  fix: '一行一个元素；要两行写两个 div 各自定位',
                });
              }
            }

            // 字号地板
            if (size < T.font.microPx) {
              out.push({ page: pageNo, level: 'error', code: 'FONT', msg: `${size}px 小于微字地板 ${T.font.microPx}px：「${txt.slice(0, 14)}」`, fix: '升一档字号阶梯；承载不了信息就删掉' });
            } else if (!isLabel && size < T.font.bodyPx) {
              const need = size < T.font.labelPx ? T.font.labelPx : T.font.bodyPx;
              out.push({
                page: pageNo, level: 'error', code: 'FONT',
                msg: `信息文本 ${size}px 低于正文地板 ${need}px：「${txt.slice(0, 14)}」`,
                fix: `升到 ${need}px 以上；只想做标签就用 .meta（${T.font.labelPx}px）并保持无汉字`,
              });
            }
            // 标签里塞内容：标签不该承载句子
            if (isLabel && CJK(txt) > T.font.labelMaxCJK) {
              out.push({
                page: pageNo, level: 'error', code: 'FONT',
                msg: `标签 ${cls.trim().split(/\s+/)[0]} 里有 ${CJK(txt)} 个汉字——标签只放编号与英文，不放句子：「${txt.slice(0, 14)}」`,
                fix: `搬到正文阶梯（≥${T.font.bodyPx}px），或把内容减到 ${T.font.labelMaxCJK} 字以内`,
              });
            }

            // 越界
            if (ink.x < -T.bounds.tolerancePx || ink.y < -T.bounds.tolerancePx || ink.r > W + T.bounds.tolerancePx || ink.b > H + T.bounds.tolerancePx) {
              const over = Math.max(-ink.x, -ink.y, ink.r - W, ink.b - H);
              out.push({
                page: pageNo,
                level: 'error',
                code: 'BOUNDS',
                msg: `文字越出画布 ${Math.round(over)}px：「${txt.slice(0, 14)}」`,
                fix: over < 40
                  ? `只超 ${Math.round(over)}px：把 left/top 挪回来，或把 width 收窄一点，不要删内容`
                  : `超出 ${Math.round(over)}px：缩字号或改窄栏宽；再不行就拆页`,
              });
            }

            // 安全区：只查正文，不误伤页脚/出血标题
            const bodyish = !isLabel
              && size >= T.font.bodyPx
              && size < T.textArea.displayPx
              && CJK(txt) >= 8;
            const safeOk = el.closest('[data-safe-ok]') || sec.hasAttribute('data-safe-ok');
            if (bodyish && !safeOk) {
              const over = Math.max(
                SAFE - ink.x,
                SAFE - ink.y,
                ink.r - (W - SAFE),
                ink.b - (H - SAFE),
              );
              if (over > T.safe.warnPx) {
                out.push({
                  page: pageNo,
                  level: over > T.safe.errorPx ? 'error' : 'warn',
                  code: 'SAFE', compat: true,
                  msg: `正文越出 ${SAFE}px 安全区 ${Math.round(over)}px：「${txt.slice(0, 14)}」`,
                  fix: '正文收回安全区；展示字可以出血，但正文不出',
                });
              }
            }

            // 没有真正给宽度的单行正文
            if (bodyish && fi.lines === 1 && !el.style.width
                && cs.position === 'absolute' && el.offsetWidth - (fi.r - fi.x) < T.width.minGapPx) {
              out.push({
                page: pageNo, level: 'warn', code: 'WIDTH', compat: true,
                msg: `单行正文没有显式 width，文本框贴着墨迹：「${txt.slice(0, 14)}」`,
                fix: '给 T2 正文写 width；否则用户在 PPT 里加字不会重排',
              });
            }

            // 溢出容器
            if (el.scrollHeight > el.clientHeight + T.overflow.tolerancePx && el.clientHeight > 0 && cs.overflow !== 'visible') {
              const over = el.scrollHeight - el.clientHeight;
              out.push({
                page: pageNo,
                level: 'error',
                code: 'OVERFLOW',
                msg: `内容被容器裁掉 ${over}px：「${txt.slice(0, 14)}」`,
                fix: over < 40 ? '加高容器或收紧行距' : '换更高容量的版式，或把这段拆到下一页',
              });
            }

            // 遮挡：后序不透明色块盖住文字
            if (!el.closest('[data-overlap-ok]')) {
              const hit = occlusionAt({ el, box }, sr);
              const warnHits = T.occlude.warnHits;
              const errorHits = T.occlude.errorHits;
              if (hit >= warnHits) {
                out.push({
                  page: pageNo,
                  level: hit >= errorHits ? 'error' : 'warn',
                  code: 'OCCLUDE', compat: true,
                  msg: `${hit}/${T.occlude.samples} 个采样点被后序色块盖住：「${txt.slice(0, 14)}」`,
                  fix: '把文字移到色块之上（DOM 后序），或挪开色块；故意的叠压加 data-overlap-ok',
                });
              }
            }

            // 对比度：5 点取最差；图片/纹理背景标需人工
            const fg2 = HEX(cs.color);
            const isLarge = size >= T.contrast.largePx || parseInt(cs.fontWeight, 10) >= T.contrast.largeWeight;
            const floor = isLarge ? T.contrast.large : T.contrast.body;
            if (fg2) {
              let worst = Infinity;
              let unknown = false;
              for (const fx of [0.5, 0.25, 0.75]) {
                for (const fy of [0.5, 0.25, 0.75]) {
                  if (fx === 0.5 && fy === 0.5) continue;
                  const px = ink.x + (ink.r - ink.x) * fx;
                  const py = ink.y + (ink.b - ink.y) * fy;
                  const b = bgAtPoint(px, py, sr, slideBg, el);
                  if (b.unknown) { unknown = true; continue; }
                  worst = Math.min(worst, CONTRAST(fg2, b.backdrop));
                }
              }
              if (unknown) {
                out.push({
                  page: pageNo, level: 'warn', code: 'CONTRAST', compat: true,
                  msg: `背景含图片/纹理，对比度需人工确认：「${txt.slice(0, 14)}」`,
                  fix: '把字放在实色区，或给字垫一块实色；图片上的字必须人工看',
                });
              }
              if (Number.isFinite(worst)) {
                if (worst < floor - T.contrast.tolerance) {
                  out.push({ page: pageNo, level: 'error', code: 'CONTRAST', msg: `最差采样对比度 ${worst.toFixed(1)}（需 ${floor}）：「${txt.slice(0, 14)}」`, fix: '换色，或给文字底下垫一块实色' });
                } else if (worst < floor) {
                  out.push({ page: pageNo, level: 'warn', code: 'CONTRAST', msg: `最差采样对比度 ${worst.toFixed(1)} 略低：「${txt.slice(0, 14)}」`, fix: '加深文字或提亮底色' });
                }
              }
            }
          }
        }
        Array.from(el.children)
          .filter((c) => getComputedStyle(c).display !== 'inline')
          .forEach((c) => walk(c, rotatedAncestor || (cs.transform && cs.transform !== 'none')));
      };

      walk(sec, false);

      /* ---- STRUCTURE / LAYOUT / SLOTS：结构化 deck 的页级契约 */
      const role = sec.getAttribute('data-role') || '';
      const layoutId = sec.getAttribute('data-layout') || '';
      const isCustom = layoutId === 'custom';
      const layout = layoutId && !isCustom
        ? L.layouts.find((l) => l.id === layoutId)
        : null;
      if (!onlyPage) stats.push({ page: pageNo, role, layoutId, family: layout ? layout.family : (isCustom ? 'custom' : '') });

      if (structured && !structureOk) {
        if (!role) out.push({ page: pageNo, level: 'error', code: 'STRUCTURE', compat: true, msg: '缺 data-role：这页在叙事里承担什么？', fix: '补 cover/context/thesis/method/evidence/data/comparison/sequence/case/quote/section/closing' });
        if (!layoutId) out.push({ page: pageNo, level: 'error', code: 'STRUCTURE', compat: true, msg: '缺 data-layout：这页用哪个骨架？', fix: '补 L01–L21；自定义版式写 custom' });
        if (layoutId && !isCustom && !layout) {
          out.push({ page: pageNo, level: 'error', code: 'LAYOUT', compat: true, msg: `data-layout="${layoutId}" 不在 layouts.json 里`, fix: '改用 L01–L21 或 custom' });
        } else if (layout && role && !layout.roles.includes(role)) {
          out.push({ page: pageNo, level: 'error', code: 'LAYOUT', compat: true, msg: `layout ${layoutId} 不支持 role "${role}"（支持：${layout.roles.join('/')}）`, fix: '换一个支持该角色的版式，或改 data-role' });
        } else if (isCustom && role && !L.roles.includes(role)) {
          out.push({ page: pageNo, level: 'error', code: 'LAYOUT', compat: true, msg: `custom 版式的 role "${role}" 不在角色表里`, fix: `用 ${L.roles.join('/')} 之一` });
        }
      }

      if (layout && structured) {
        const slotEls = [...sec.querySelectorAll('[data-slot]')];
        const known = new Set(Object.keys(layout._slots || {}));
        for (const el of slotEls) {
          const name = el.getAttribute('data-slot');
          if (!known.has(name)) {
            out.push({ page: pageNo, level: 'warn', code: 'SLOTS', compat: true, msg: `版式 ${layoutId} 没有登记槽位 "${name}"`, fix: '删掉该 data-slot，或在 layouts.json 里登记' });
          }
        }
        if (!slotEls.length) {
          out.push({ page: pageNo, level: 'warn', code: 'SLOTS', compat: true, msg: `版式 ${layoutId} 没使用 data-slot，无法检查结构`, fix: '按 references/layout-specs.md 的槽位表写' });
        }
        for (const [name, def] of Object.entries(layout._slots || {})) {
          const el = slotEls.find((x) => x.getAttribute('data-slot') === name);
          const gd = def.group ? layout.groups[def.group] : null;
          const blockExists = def.group
            ? !!(gd && (gd.exact || sec.querySelector(`[data-slot-block="${def.group}.${def.index}"]`)))
            : false;
          if (!el) {
            if (def.required || blockExists) {
              out.push({ page: pageNo, level: 'error', code: 'SLOTS', compat: true, msg: `版式 ${layoutId} 缺槽位 "${name}"`, fix: '按 references/layout-specs.md 补齐；slot 元素要有 data-slot 与内容' });
            }
            continue;
          }
          if (def.form === 'media') {
            const src = (el.getAttribute('src') || '').trim();
            if (!src) out.push({ page: pageNo, level: 'error', code: 'SLOTS', compat: true, msg: `媒体槽位 "${name}" 没有 src`, fix: '给图片本地路径' });
            continue;
          }
          const text = (el.textContent || '').trim();
          if (!text && (def.required || blockExists)) {
            out.push({ page: pageNo, level: 'error', code: 'SLOTS', compat: true, msg: `槽位 "${name}" 为空`, fix: '补内容；不需要就删掉整页的该槽位' });
            continue;
          }
          if (!text) continue;
          if (def.maxCJK && CJK(text) > def.maxCJK) {
            out.push({ page: pageNo, level: 'error', code: 'SLOTS', compat: true, msg: `槽位 "${name}" 有 ${CJK(text)} 汉字，超过 ${def.maxCJK}`, fix: '先删内容，再调坐标；不要靠缩字号硬塞' });
          }
          if (def.maxLines) {
            const r = document.createRange();
            r.selectNodeContents(el);
            const lines = new Set([...r.getClientRects()].filter((x) => x.width > 0.5).map((x) => Math.round(x.top))).size;
            if (lines > def.maxLines) {
              out.push({ page: pageNo, level: 'error', code: 'SLOTS', compat: true, msg: `槽位 "${name}" 折了 ${lines} 行，超过 ${def.maxLines} 行`, fix: '删减文字或换更高容量的版式' });
            }
          }
        }
      }

      for (const bad of new Set([forbiddenColor, ...forbiddenColors].filter(Boolean))) {
        out.push({
          page: pageNo, level: 'error', code: 'INK',
          msg: `颜色 ${bad} 不在本页主题的令牌里（${[...token].join(' ')}）`,
          fix: `改用 var(--bg)/var(--fg)/var(--pop)/var(--alt)；反白不要写 #FFFFFF`,
        });
      }

      // 规则 12「交付前跑完验证链」不在这里实现：本脚本只能证明自己跑过，
      // 证明不了 audit-text / build / verify-pptx 跑过。那件事由 gate.mjs 负责——
      // 它读 gate.json 的 steps 判定整条链，并在缺步时失败（见 gate.mjs 的 gate-chain 检查）。

      /* ---- AXIS：一页一条主斜线，而且必须是"主"的 */
      if (!sec.hasAttribute('data-axis-ok')) {
        if (!diagonals.length) {
          out.push({
            page: pageNo,
            level: 'error',
            code: 'AXIS',
            msg: '整页没有斜线或楔形——这是正交版面，不是构成主义',
            fix: `加一条 ${T.axis.bandMinDeg}°–${T.axis.bandMaxDeg}° 的贯穿斜带，或一个 clip-path 楔形；让标题与它咬合`,
          });
        } else {
          const principal = [...diagonals].sort((a, b) => b.area - a.area)[0];
          const areaPct = principal.area / CANVAS;
          const longPct = Math.max(principal.w, principal.h) / W;
          if (areaPct < T.axis.dominantMinAreaPct) {
            out.push({
              page: pageNo, level: 'error', code: 'AXIS', compat: true,
              msg: `最大斜元素只占 ${(areaPct * 100).toFixed(1)}% 画布，低于主斜线下限 ${(T.axis.dominantMinAreaPct * 100).toFixed(1)}%——这是装饰，不是结构`,
              fix: '把一条斜带/楔形放大到贯穿画面；小角度装饰删掉或改成水平/垂直',
            });
          } else if (principal.deg !== null
            && (Math.abs(principal.deg) < T.axis.bandMinDeg || Math.abs(principal.deg) > T.axis.bandMaxDeg)) {
            out.push({
              page: pageNo, level: 'warn', code: 'AXIS', compat: true,
              msg: `主斜线 ${principal.deg}°，不在推荐区间 ${T.axis.bandMinDeg}°–${T.axis.bandMaxDeg}°`,
              fix: `把主角度调到 ${T.axis.bandMinDeg}°–${T.axis.bandMaxDeg}°；推荐 ${T.axis.recommendMinDeg}°–${T.axis.recommendMaxDeg}°`,
            });
          }
          if (longPct < T.axis.longSidePct) {
            out.push({
              page: pageNo, level: 'warn', code: 'AXIS', compat: true,
              msg: `主斜线长边只有画布宽的 ${(longPct * 100).toFixed(0)}%，不够贯穿`,
              fix: '让斜带两端出血；短斜线读起来像贴纸',
            });
          }
          const rivals = diagonals.filter((d) => d !== principal
            && d.area >= principal.area * T.axis.rivalAreaPct
            && d.axis !== null && principal.axis !== null
            && Math.abs(d.axis - principal.axis) > 3);
          if (rivals.length) {
            const strong = rivals.some((d) => d.area >= principal.area * 0.5);
            out.push({
              page: pageNo,
              level: strong ? 'error' : 'warn',
              code: 'AXIS', compat: true,
              msg: `主斜线之外还有 ${rivals.length} 条竞争角度（${rivals.map((d) => d.axis).join('° / ')}°）`,
              fix: '其余元素改成与主斜线平行，或严格水平/垂直；确需正交版面加 data-axis-ok',
            });
          }
        }
      }

      /* ---- BALANCE：面积不均，禁止等价并列 */
      const exemptBalance = sec.closest('[data-balance-ok]');
      if (!exemptBalance && blocks.length >= T.balance.minBlocks) {
        const sorted = [...blocks].sort((a, b) => b.area - a.area);
        const top1 = sorted[0];
        const top2 = sorted[1];
        if (top2.area >= CANVAS * T.balance.minRunnerUpPct) {
          const ratio = top1.area / top2.area;
          if (ratio < T.balance.minRatio) {
            out.push({
              page: pageNo,
              level: 'error',
              code: 'BALANCE',
              msg: `最大块 ${Math.round((top1.area / CANVAS) * 100)}% 只有次大块 ${Math.round((top2.area / CANVAS) * 100)}% 的 ${r1(ratio)} 倍，低于下限 ${T.balance.minRatio}——读者判断不出主次`,
              fix: `把首栏放大到 ${T.balance.minRatio} 倍以上（骨架配方 ${T.balance.recipeFr}fr，理想 ${T.balance.idealRatio} 倍）；确实需要等价并列加 data-balance-ok`,
            });
          }
        }
      }

      /* ---- INK：两墨一纸，四色含纸 */
      const inkOk = sec.closest('[data-palette-ok]');
      if (colors.size > R.palette.inkMaxColors && !inkOk) {
        out.push({
          page: pageNo,
          level: 'error',
          code: 'INK',
          msg: `本页出现 ${colors.size} 种颜色（${[...colors].slice(0, 8).join(' ')}），超过 ${R.palette.inkMaxColors} 色（含纸色）`,
          fix: '收敛到 纸 + 墨 + 爆点色 + 一个次墨；展示色板的页加 data-palette-ok 豁免',
        });
      }

      /* ---- WEIGHT：构成主义的线有重量，不是 hairline */
      if (thinLines > 0) {
        out.push({
          page: pageNo,
          level: 'error',
          code: 'WEIGHT',
          msg: `有 ${thinLines} 处细于 ${T.weight.minLinePx}px 的线——这是编辑设计的发丝线，不是构成主义的规则线`,
          fix: `线改成 ${T.weight.minLinePx}px 起；要用细线的地方改用留白或色块边界`,
        });
      }

      /* ---- TEXTAREA：正文面积受限 */
      // 这里量的是正文"行盒"面积（含行距），比真实墨迹大，展示字不计入。
      const areaRatio = textInkArea / CANVAS;
      if (areaRatio > T.textArea.max) {
        out.push({
          page: pageNo,
          level: 'error',
          code: 'TEXTAREA',
          msg: `正文行盒面积 ${(areaRatio * 100).toFixed(1)}%，超过上限 ${T.textArea.maxPercent}%`,
          fix: '删掉一半的正文，或把这一页拆成两页；构成主义靠面积差说话，不靠字数',
        });
      }

      /* ---- 文本互压：用 ink 盒，不用元素行盒 */
      for (let i = 0; i < texts.length; i++) {
        for (let j = i + 1; j < texts.length; j++) {
          const A = texts[i].box;
          const B = texts[j].box;
          const ox = Math.min(A.r, B.r) - Math.max(A.x, B.x);
          const oy = Math.min(A.b, B.b) - Math.max(A.y, B.y);
          if (ox > T.overlap.minPx && oy > T.overlap.minPx) {
            const exempt = texts[i].el.closest('[data-overlap-ok]') || texts[j].el.closest('[data-overlap-ok]');
            if (exempt) continue;
            // 展示字的 getClientRects 带字体上下伸，容易与相邻小字误报；
            // 展示字之间的压叠是设计决定，交给人工看联系表。
            if (texts[i].size >= T.textArea.displayPx || texts[j].size >= T.textArea.displayPx) continue;
            const minArea = Math.min(
              (A.r - A.x) * (A.b - A.y),
              (B.r - B.x) * (B.b - B.y),
            );
            const ratio = (ox * oy) / Math.max(1, minArea);
            if (ratio < T.overlap.minRatio) continue;
            out.push({
              page: pageNo,
              level: ratio > T.overlap.errorRatio ? 'error' : 'warn',
              code: 'OVERLAP', compat: ratio > T.overlap.errorRatio,
              msg: `文字相压 ${Math.round(ox)}×${Math.round(oy)}px（占小者 ${(ratio * 100).toFixed(0)}%）：「${texts[i].txt.slice(0, 10)}」×「${texts[j].txt.slice(0, 10)}」`,
              fix: '故意的压字给祖先加 data-overlap-ok；不是故意的就拉开位置',
            });
          }
        }
      }

      /* ---- 字数密度 */
      const total = texts.map((t) => t.txt).join('');
      const cjk = (total.match(/[\u4e00-\u9fa5]/g) || []).length;
      const words = (total.replace(/[\u4e00-\u9fa5]/g, ' ').match(/[A-Za-z0-9]+/g) || []).length;
      if (cjk + words > T.density.maxChars) {
        out.push({ page: pageNo, level: 'warn', code: 'DENSITY', msg: `单页 ${cjk + words} 字，超过 ${T.density.maxChars} 字`, fix: '删减或拆页' });
      }

      /* ---- 版式指纹 + 页脚形态 */
      const sig = layoutId && layoutId !== 'custom'
        ? `L:${layoutId}`
        : blocks.map((b) => `${Math.round(b.area / T.rhythm.bucketPx)}`).sort().join('|');
      sigs.push({ page: pageNo, sig });

      const folio = sec.querySelector('.folio');
      const f = folio
        ? (['folio--cut', 'folio--block', 'folio--end'].find((m) => folio.classList.contains(m)) || 'folio')
          + (folio.style.color ? ':ink' : '')
        : 'none';
      folioSigs.push({ page: pageNo, f });
    });

    for (let i = 1; i < sigs.length; i++) {
      if (sigs[i].sig && sigs[i].sig === sigs[i - 1].sig) {
        out.push({
          page: sigs[i].page,
          level: 'warn',
          code: 'RHYTHM',
          msg: '与上一页的色块结构几乎相同，翻页没有节奏变化',
          fix: '换骨架（见 layouts.md），不要只换文字',
        });
      }
    }

    /* ---- THEME：一份 deck 一套主题 */
    if (themeSeen.size > 1 && !document.querySelector('.deck[data-showcase]')) {
      out.push({
        page: firstThemePage,
        level: 'error',
        code: 'THEME',
        msg: `一份 deck 用了 ${themeSeen.size} 套主题（${[...themeSeen].join(' / ')}）`,
        fix: '全篇统一到一套 theme-*；风格对照交给 style-preview.mjs；样张文件加 data-showcase',
      });
    }

    /* ---- FOOTER：页脚不许连续三页同一种形态 */
    // 样张/画廊是版式目录，不是叙事 deck：它本来就要连续展示同类版式，
    // 页脚跟着重复是预期行为，不构成"翻页失去标点"。
    const folioRotationApplies = !structureOk
      && !document.querySelector('.deck[data-showcase]');
    if (folioRotationApplies) {
      for (let i = 2; i < folioSigs.length; i++) {
        const a = folioSigs[i - 2].f;
        const b = folioSigs[i - 1].f;
        const c = folioSigs[i].f;
        if (a === b && b === c && a !== 'none') {
          out.push({
            page: folioSigs[i].page,
            level: 'warn',
            code: 'FOOTER',
            msg: `页脚连续三页都是 ${a}，翻页失去标点`,
            fix: '在默认贴左 / .folio--cut / .folio--block / .folio--end 之间轮换',
          });
        }
      }
    }

    /* ---- STRUCTURE：整份 deck 的叙事顺序与版式轮换 */
    if (structured && !structureOk && !onlyPage && stats.length) {
      const last = stats[stats.length - 1];
      if (stats[0].role !== 'cover') {
        out.push({ page: 1, level: 'error', code: 'STRUCTURE', compat: true, msg: '第 1 页不是 cover', fix: '封面用 cover + L01/L02' });
      }
      if (last.role !== 'closing') {
        out.push({ page: last.page, level: 'error', code: 'STRUCTURE', compat: true, msg: `最后 1 页是 ${last.role || '空'}，不是 closing`, fix: '结尾用 closing + L16' });
      }
      const maxRun = T.structure.maxSameRun;
      let run = 1;
      for (let i = 1; i < stats.length; i++) {
        // custom 是手写版式，不是同一骨架的重复；不参与轮换统计
        if (stats[i].layoutId === 'custom' || stats[i - 1].layoutId === 'custom') { run = 1; continue; }
        if (stats[i].layoutId && stats[i].layoutId === stats[i - 1].layoutId) run++;
        else run = 1;
        if (run > maxRun) {
          out.push({ page: stats[i].page, level: 'error', code: 'STRUCTURE', compat: true, msg: `版式 ${stats[i].layoutId} 连续 ${run} 页，超过 ${maxRun}`, fix: '换骨架；连续同版式会让翻页失去节奏' });
          break;
        }
      }
      for (let i = 1; i < stats.length; i++) {
        if (stats[i].family && stats[i].family !== 'custom' && stats[i].family === stats[i - 1].family && stats[i].layoutId !== stats[i - 1].layoutId) {
          out.push({ page: stats[i].page, level: 'warn', code: 'STRUCTURE', compat: true, msg: `与上一页同属 ${stats[i].family} 家族，节奏可能偏平`, fix: '换一个 family 的骨架' });
        }
      }
      if (stats.length >= T.structure.minSlides) {
        const count = new Map();
        for (const s of stats) {
          if (s.layoutId === 'custom') continue;
          count.set(s.layoutId || '(none)', (count.get(s.layoutId || '(none)') || 0) + 1);
        }
        const counted = stats.filter((s) => s.layoutId !== 'custom').length;
        for (const [id, n] of count) {
          if (!counted) break;
          if (n / counted > T.structure.maxShare) {
            out.push({ page: 0, level: 'error', code: 'STRUCTURE', compat: true, msg: `版式 ${id} 占 ${Math.round((n / stats.length) * 100)}%，超过 ${T.structure.maxShare * 100}%`, fix: '增加版式种类，或把内容拆到别的叙事角色' });
          }
        }
      }
      if (stats.length < 12 && stats.some((s) => s.role === 'section')) {
        out.push({ page: 0, level: 'warn', code: 'STRUCTURE', compat: true, msg: '少于 12 页时用章节幕会打断节奏', fix: '短 deck 去掉 section，直接进内容' });
      }
    }

    return { pages: sections.length, issues: out };
  }, { onlyPage: only, R: RULES, L: LAYOUT_CTX, forbidLevel, allowForbid: ALLOW_FORBID });
} finally {
  await browser.close();
}

/* ────────────────────────────── 汇总 ────────────────────────────── */
const all = [...issues, ...result.issues].map(applyCompat);

// 空 deck / --slide 越界：以前会打印"0 页 0 问题"并 exit 0，这是最危险的假绿。
if (result.pages === 0) {
  all.push({ page: 0, level: 'error', code: 'DECK', msg: '整份 deck 没有 section.slide', fix: '每页一个 <section class="slide theme-*">；空文件不是"通过"' });
}
if (only && (!Number.isInteger(only) || only < 1 || only > result.pages)) {
  all.push({ page: 0, level: 'error', code: 'DECK', msg: `--slide ${args.slide} 越界（共 ${result.pages} 页）`, fix: `--slide 取 1–${result.pages}` });
}

const errs = all.filter((i) => i.level === 'error');
const compatDown = all.filter((i) => i.level === 'warn' && i.downgraded);
const warns = all.filter((i) => i.level === 'warn' && !i.downgraded);
const icon = { error: '✖', warn: '△' };
const order = codeOrder(RULES);
const rank = (c) => (order.indexOf(c) === -1 ? 99 : order.indexOf(c));
const sorted = [...errs, ...warns, ...compatDown].sort((a, b) => rank(a.code) - rank(b.code) || a.page - b.page);
// compat 降级项不算失败，但必须显式计数：静默放行正是这一版要堵的洞。
const compatNote = COMPAT ? `  兼容降级 ${compatDown.length}` : '';

if (JSON_OUT) {
  console.log(JSON.stringify({
    pages: result.pages,
    only: only || null,
    compat: COMPAT ? 'v2' : null,
    summary: { errors: errs.length, warns: warns.length, compatDowngraded: compatDown.length },
    issues: sorted,
  }, null, 2));
  process.exit(errs.length ? 1 : (STRICT && warns.length ? 1 : 0));
}

console.log(only
  ? `\n第 ${only} 页 / 共 ${result.pages} 页  错误 ${errs.length}  提示 ${warns.length}${compatNote}\n`
  : `\n${result.pages} 页  错误 ${errs.length}  提示 ${warns.length}${compatNote}\n`);

sorted.forEach((i) => {
  const p = i.page ? `P${String(i.page).padStart(2, '0')}` : '全局';
  const r = codeRule(RULES, i.code);
  const rule = r ? `·规则${r}` : '';
  console.log(`  ${icon[i.level]} ${p} [${i.code}${rule}]${i.downgraded ? ' (compat 降级)' : ''} ${i.msg}`);
  if (i.fix) console.log(`      → ${i.fix}`);
});
if (!all.length) console.log('  全部通过。\n');

if (!errs.length && warns.length) {
  console.log('  △ 有提示项不是失败，但逐条判断：说不出理由的请改掉，别一条条糊过去。\n');
}
if (compatDown.length) {
  console.log(`  △ ${compatDown.length} 项因 --compat v2 降级放行——它们是真实缺陷，不是通过项。\n`);
}

process.exit(errs.length ? 1 : (STRICT && warns.length ? 1 : 0));
