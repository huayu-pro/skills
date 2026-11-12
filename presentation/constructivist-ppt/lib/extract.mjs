/**
 * extract.mjs — 把 deck.html 的每一页读成 deck-spec
 *
 * 输出是纯数据（px 坐标、十六进制色、字号、旋转角），不含任何 DOM 句柄。
 * 这样 spec 可以单测、可以回渲、可以换后端；Node 侧永远不碰 DOM。
 *
 * spec 结构：
 * {
 *   canvas: {w,h},
 *   meta: {title, theme},
 *   slides: [{
 *     index, notes, bg, ink,
 *     shapes: [
 *       {kind:'rect'|'ellipse'|'poly', x,y,w,h, fill, rotate, points?, stroke?}
 *       {kind:'image', x,y,w,h, src, rotate}
 *       {kind:'text', x,y,w,h, align, wrap, vertical, size, lineHeight, color,
 *        family, weight, letterSpacing, paragraphs:[{align, runs:[{text,size,color,weight,family,italic,letterSpacing}]}]}
 *     ],
 *     warnings: []
 *   }]
 * }
 */
import path from 'node:path';

export async function extractDeck(page, htmlPath, { canvas = { w: 1280, h: 720 } } = {}) {
  const slideCount = await page.locator('section.slide').count();
  if (!slideCount) throw new Error('deck.html 里没有 section.slide');

  const slides = [];
  for (let i = 0; i < slideCount; i++) {
    const s = await page.evaluate(browserExtract, { index: i, W: canvas.w, H: canvas.h });
    s.shapes.forEach((sh) => {
      if (sh.kind === 'image' && sh.src && !/^https?:|^data:/.test(sh.src)) {
        if (sh.src.startsWith('file://')) {
          // getComputedStyle 会把 background-image 的 url 解析成绝对 file:// URL
          sh.src = decodeURIComponent(sh.src.replace(/^file:\/\//, ''));
        } else {
          sh.src = path.resolve(path.dirname(htmlPath), sh.src);
        }
      }
    });
    slides.push(s);
  }

  return {
    canvas,
    meta: {
      title: await page.title(),
      generatedAt: new Date().toISOString(),
      source: path.resolve(htmlPath),
    },
    slides,
  };
}

/* ------------------------------------------------------------------------ */
/* 以下函数整段被序列化进浏览器执行，不能引用外部变量。                         */
/* ------------------------------------------------------------------------ */
function browserExtract({ index, W, H }) {
  // 必须在这里重新声明：本函数会被整段序列化进浏览器，访问不到模块作用域
  const INLINE_TAGS = new Set([
    'SPAN', 'EM', 'B', 'I', 'STRONG', 'A', 'SUP', 'SUB', 'SMALL', 'CODE', 'U', 'MARK', 'S', 'BR',
  ]);
  const section = document.querySelectorAll('section.slide')[index];
  const warnings = [];

  // 白名单与 lib/anim.mjs 的 ALIASES 对齐；这里内联是因为本函数会被序列化进浏览器。
  const ANIM_OK = new Set(['fade', 'dissolve', 'wipe', 'wipe-up', 'wipe-down', 'wipe-left',
    'wipe-right', 'wedge', 'circle-in', 'circle-out']);
  // 禁止项清单与 assets/rules.json 的 forbid 一一对应。
  // selfcheck.mjs 的 FORBID_SYNC 会比对两边；改了这里必须同步那边。
  const FORBID = ['gradient', 'shadow', 'filter', 'blend', 'zindex',
    'fixed', 'pseudo', 'nested', 'overflow', 'svg', 'transform', 'translate',
    'clip', 'radius', 'remote'];
  const forbidWarn = (id, msg) => {
    if (!FORBID.includes(id)) {
      warnings.push(`内部错误：禁止项 ${id} 未登记到 FORBID`);
      return;
    }
    warnings.push(`FORBID:${id} ${msg}`);
  };

  const hex = (input) => {
    if (!input) return null;
    const s = String(input).trim();
    if (s === 'transparent' || s === 'none' || s === 'rgba(0, 0, 0, 0)') return null;
    if (s.startsWith('#')) {
      let h = s.slice(1);
      if (h.length === 3) h = h.split('').map((c) => c + c).join('');
      if (h.length !== 6) return null;
      return h.toUpperCase();
    }
    const m = s.match(/^rgba?\(([^)]+)\)$/i);
    if (m) {
      const p = m[1].split(/[,\s/]+/).filter(Boolean);
      const a = p[3] === undefined ? 1 : parseFloat(p[3]);
      if (a < 0.02) return null;
      const t = (v) => Math.max(0, Math.min(255, Math.round(parseFloat(v)))).toString(16).padStart(2, '0');
      return (t(p[0]) + t(p[1]) + t(p[2])).toUpperCase();
    }
    return null;
  };

  /** 布局盒（未旋转）相对 section 的坐标。绝不用 getBoundingClientRect。 */
  const absBox = (el) => {
    let x = 0;
    let y = 0;
    let n = el;
    let guard = 0;
    while (n && n !== section && guard++ < 80) {
      x += n.offsetLeft;
      y += n.offsetTop;
      n = n.offsetParent;
    }
    if (guard >= 80) {
      warnings.push(`${tag(el)} 的 offsetParent 链超过 80 层，坐标可能被截断`);
    }
    return { x, y, w: el.offsetWidth, h: el.offsetHeight };
  };

  /** 从 transform 矩阵里只取旋转角；平移/缩放/斜切/非中心原点都表达不了。 */
  const rotationOf = (el, cs) => {
    const t = cs.transform;
    if (!t || t === 'none') return 0;
    const m = new DOMMatrix(t);
    if (Math.abs(m.e) > 0.5 || Math.abs(m.f) > 0.5) {
      forbidWarn('translate', `${tag(el)} 使用了 translate()，布局盒与 PPT 坐标不一致`);
    }
    const scaleX = Math.hypot(m.a, m.b);
    if (Math.abs(scaleX - 1) > 0.02) {
      forbidWarn('transform', `${tag(el)} 使用了 scale()，PPTX 不支持`);
    }
    if (Math.abs(m.a - m.d) > 0.002 || Math.abs(m.b + m.c) > 0.002) {
      forbidWarn('transform', `${tag(el)} 使用了 skew()，PPTX 不支持`);
    }
    // 原点必须居中，否则 PPT 的旋转中心对不上
    const o = cs.transformOrigin.split(' ').map(parseFloat);
    const cx = el.offsetWidth / 2;
    const cy = el.offsetHeight / 2;
    if (Math.abs(o[0] - cx) > 0.6 || Math.abs(o[1] - cy) > 0.6) {
      forbidWarn('transform', `${tag(el)} 的 transform-origin 不在中心，旋转会错位`);
    }
    const deg = (Math.atan2(m.b, m.a) * 180) / Math.PI;
    return Math.abs(deg) < 0.05 ? 0 : Math.round(deg * 100) / 100;
  };

  const tag = (el) => {
    const raw = (el.getAttribute && el.getAttribute('class')) || (typeof el.className === 'string' ? el.className : '');
    const cls = raw.split(/\s+/).filter(Boolean)[0];
    return `<${el.tagName.toLowerCase()}${cls ? '.' + cls : ''}>`;
  };

  /** clip-path: polygon(...) → 局部 px 点集 */
  const parsePolygon = (clip, w, h) => {
    const m = clip.match(/polygon\(([^)]+)\)/i);
    if (!m) return null;
    const pts = [];
    for (const part of m[1].split(',')) {
      const bits = part.trim().split(/\s+/);
      if (bits.length < 2) return null;
      const conv = (v, base) => (v.endsWith('%') ? (parseFloat(v) / 100) * base : parseFloat(v));
      const px = conv(bits[0], w);
      const py = conv(bits[1], h);
      if (!Number.isFinite(px) || !Number.isFinite(py)) return null;
      pts.push({ x: Math.round(px * 100) / 100, y: Math.round(py * 100) / 100 });
    }
    return pts.length >= 3 ? pts : null;
  };

  /** 元素自身文本流（文本节点 + inline 后代）的联合包围盒。
   *  不把 block 子元素算进来——否则父容器会吞掉子块，生成一个覆盖整页的文本框。 */
  const inkBox = (el) => {
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
      if (!isInlineEl(node)) return;
      for (const c of node.childNodes) collect(c);
    };
    for (const c of el.childNodes) collect(c);
    if (!rects.length) return null;
    const sr = section.getBoundingClientRect();
    const left = Math.min(...rects.map((x) => x.left));
    const top = Math.min(...rects.map((x) => x.top));
    const right = Math.max(...rects.map((x) => x.right));
    const bottom = Math.max(...rects.map((x) => x.bottom));
    return {
      x: Math.round((left - sr.left) * 100) / 100,
      y: Math.round((top - sr.top) * 100) / 100,
      w: Math.round((right - left) * 100) / 100,
      h: Math.round((bottom - top) * 100) / 100,
      lines: new Set(rects.map((x) => Math.round(x.top))).size,
    };
  };

  const applyCase = (t, mode) => {
    if (mode === 'uppercase') return t.toUpperCase();
    if (mode === 'lowercase') return t.toLowerCase();
    return t;
  };

  const runOf = (node, inherited) => {
    const el = node.nodeType === 1 ? node : node.parentElement;
    const cs = getComputedStyle(el);
    return {
      text: applyCase(node.textContent.replace(/\s+/g, ' '), cs.textTransform),
      size: parseFloat(cs.fontSize),
      color: hex(cs.color) || inherited.color,
      weight: parseInt(cs.fontWeight, 10) || 400,
      family: cs.fontFamily.split(',')[0].replace(/["']/g, '').trim(),
      stack: cs.fontFamily,
      italic: cs.fontStyle === 'italic',
      letterSpacing: cs.letterSpacing === 'normal' ? 0 : parseFloat(cs.letterSpacing) || 0,
      transform: cs.textTransform,
    };
  };

  /** 只有 display:inline 的子元素才并进父元素的文本流。
   *  flex / grid 的子项会被 blockify（computed display 变成 block），
   *  所以它们各自成为独立文本框——否则 01 和 ONE DIAGONAL 会叠在一起。 */
  const isInlineEl = (n) => n.nodeType === 1 && getComputedStyle(n).display === 'inline';

  /** 把元素的内联内容拆成段落数组（<br> 分段，行内元素成 run） */
  const readParagraphs = (el) => {
    const paras = [[]];
    const walkInline = (node, inherited) => {
      if (node.nodeType === 3) {
        const t = node.textContent.replace(/\s+/g, ' ');
        if (t.trim() || t === ' ') paras[paras.length - 1].push(runOf(node, inherited));
        return;
      }
      if (node.nodeType !== 1) return;
      if (node.tagName === 'BR') {
        paras.push([]);
        return;
      }
      // 块级子元素不参与父元素的文本流，它会被单独递归发射
      if (!isInlineEl(node)) return;
      const cs = getComputedStyle(node);
      const inh = { color: hex(cs.color) || inherited.color };
      for (const c of node.childNodes) walkInline(c, inh);
    };
    const cs = getComputedStyle(el);
    for (const c of el.childNodes) walkInline(c, { color: hex(cs.color) });
    return paras
      .map((runs) => {
        const cleaned = runs.filter((r) => r.text !== '' || runs.length === 1);
        if (cleaned.length) {
          cleaned[0].text = cleaned[0].text.replace(/^ +/, '');
          cleaned[cleaned.length - 1].text = cleaned[cleaned.length - 1].text.replace(/ +$/, '');
        }
        return cleaned;
      })
      .filter((runs) => runs.some((r) => r.text.trim()));
  };

  const hasOwnText = (el) =>
    Array.from(el.childNodes).some(
      (n) => (n.nodeType === 3 && n.textContent.trim()) || (isInlineEl(n) && n.textContent.trim()),
    );

  // 字体的自然行高（ascent+descent）。用来给单行文本定行距：
  // 只要 lineSpacing 等于自然行高，"文字从盒顶开始"在 CSS 与 PPT 两种模型下都成立。
  const measureCtx = document.createElement('canvas').getContext('2d');
  const naturalHeight = (cs) => {
    const fs = parseFloat(cs.fontSize);
    try {
      measureCtx.font = `${cs.fontStyle} ${cs.fontWeight} ${fs}px ${cs.fontFamily}`;
      const m = measureCtx.measureText('国');
      const a = m.fontBoundingBoxAscent;
      const d = m.fontBoundingBoxDescent;
      if (a && d) return Math.round((a + d) * 100) / 100;
    } catch {}
    return Math.round(fs * 1.45 * 100) / 100;
  };

  const shapes = [];
  let rasterSeq = 0;

  const emitText = (el, cs) => {
    const paras = readParagraphs(el);
    if (!paras.length) return false;
    const ink = inkBox(el);
    if (!ink || ink.w < 1 || ink.h < 1) return false;

    const align = (cs.textAlign === 'start' ? 'left' : cs.textAlign) || 'left';
    const vertical = cs.writingMode && cs.writingMode.startsWith('vertical');
    const box = absBox(el);
    // wrap 是"这个文本框允许重排"的契约，不是"当前是否已经折行"。
    // 单行正文也必须输出 wrap=true，用户加字后 PowerPoint 才会自己重排。
    const wrap = !vertical && cs.whiteSpace !== 'nowrap';

    // 文本框宽度：
    //  · 会折行的正文（wrap=true）必须用元素的排版宽，否则 PPT 每行塞进更多字、
    //    最后一行会越过栏宽压到隔壁——这比"少一个字的余量"严重得多。
    //  · 单行展示字用 ink 宽并留 6% 余量，防止字体替换后提前折行。
    let bx = ink.x;
    let bw = ink.w;
    if (!vertical) {
      if (wrap) {
        bx = box.x;
        bw = Math.max(box.w, ink.w);
      } else if (align === 'center') {
        bw = Math.max(box.w, ink.w);
        bx = ink.x + ink.w / 2 - bw / 2;
      } else if (align === 'right') {
        bw = Math.max(box.w, ink.w);
        bx = ink.x + ink.w - bw;
      } else {
        bw = ink.w * 1.06 + 6;
      }
    }

    const size = parseFloat(cs.fontSize);
    const natH = naturalHeight(cs);
    const cssLh = cs.lineHeight === 'normal' ? natH : parseFloat(cs.lineHeight);

    // 显式 <br> 造的换行不是"意外折行"，只有超出段落数才算问题
    if (ink.lines > Math.max(1, paras.length) && cs.whiteSpace === 'nowrap') {
      warnings.push(`${tag(el)} 声明 nowrap 却折了 ${ink.lines} 行`);
    }
    if (ink.lines > 1 && /t-(hero|h1|h2)/.test(el.className)) {
      warnings.push(`${tag(el)} 是展示字却折了 ${ink.lines} 行，改成每行一个元素更准`);
    }

    // 单行：行距取字体自然行高，文字从盒顶开始——CSS 与 PPT 两种模型都对得上。
    // 多行：行距取 CSS line-height，盒顶按半行距（half-leading）上移。
    let boxY = ink.y;
    let lineHeight = natH;
    let boxH = natH;
    const nLines = Math.max(1, ink.lines || 1);
    if (nLines > 1) {
      lineHeight = cssLh;
      boxH = cssLh * nLines;
    }

    shapes.push({
      kind: 'text',
      x: Math.round(bx * 100) / 100,
      y: Math.round(boxY * 100) / 100,
      w: Math.round(bw * 100) / 100,
      h: Math.round((vertical ? ink.h : boxH) * 100) / 100,
      align,
      wrap,
      vertical,
      lines: nLines,
      size,
      lineHeight: Math.round(lineHeight * 100) / 100,
      color: hex(cs.color) || '000000',
      paragraphs: paras.map((runs) => ({ align, runs })),
    });
    return true;
  };

  const emitBorder = (el, cs, box, rotate = 0) => {
    const ecx = box.x + box.w / 2;
    const ecy = box.y + box.h / 2;
    const rad = (rotate * Math.PI) / 180;
    const cos = Math.cos(rad);
    const sin = Math.sin(rad);
    const sides = [
      ['Top', box.x, box.y, box.w, null],
      ['Right', box.x + box.w - parseFloat(cs.borderRightWidth || 0), box.y, null, box.h],
      ['Bottom', box.x, box.y + box.h - parseFloat(cs.borderBottomWidth || 0), box.w, null],
      ['Left', box.x, box.y, null, box.h],
    ];
    for (const [side, x0, y0, wOverride, hOverride] of sides) {
      const bw = parseFloat(cs[`border${side}Width`] || 0);
      const bs = cs[`border${side}Style`];
      if (!bw || bs === 'none' || bs === 'hidden') continue;
      const color = hex(cs[`border${side}Color`]);
      if (!color) continue;
      const vertical = side === 'Left' || side === 'Right';
      const w = vertical ? bw : wOverride;
      const h = vertical ? hOverride : bw;
      let x = x0;
      let y = y0;
      // 旋转元素的边框：每条边仍是细矩形，但中心要绕元素中心旋转。
      if (rotate) {
        const cx = x + w / 2;
        const cy = y + h / 2;
        const rx = ecx + (cx - ecx) * cos - (cy - ecy) * sin;
        const ry = ecy + (cx - ecx) * sin + (cy - ecy) * cos;
        x = rx - w / 2;
        y = ry - h / 2;
      }
      shapes.push({
        kind: 'rect',
        x: Math.round(x * 100) / 100,
        y: Math.round(y * 100) / 100,
        w: Math.round(w * 100) / 100,
        h: Math.round(h * 100) / 100,
        fill: color,
        rotate,
      });
    }
  };

  const visit = (el, depth, ancestorRotated = false) => {
    if (el.nodeType !== 1) return;
    if (el.classList.contains('ui')) return;
    const cs = getComputedStyle(el);
    if (cs.display === 'none' || cs.visibility === 'hidden') return;
    if (parseFloat(cs.opacity) === 0) return;

    const isSlide = el === section;
    const isImg = el.tagName === 'IMG';
    const box = isSlide ? { x: 0, y: 0, w: W, h: H } : absBox(el);
    // 零尺寸盒子不整棵剪掉：封面标题常常挂在高 0 的包裹器上（Slidev 的 walker 同样不剪枝）。
    // 只有"既没面积又没文字"才跳过。
    if (!isSlide && box.w < 0.5 && box.h < 0.5 && !el.textContent.trim()) return;

    const rotate = isSlide ? 0 : rotationOf(el, cs);
    const bg = hex(cs.backgroundColor);
    const shapeStart = shapes.length;
    const animAttr = el.getAttribute && el.getAttribute('data-anim');
    const bgImage = cs.backgroundImage && cs.backgroundImage !== 'none' ? cs.backgroundImage : null;
    const radius = cs.borderTopLeftRadius;
    const isCircle =
      radius && (radius === '50%' || parseFloat(radius) >= Math.min(box.w, box.h) / 2 - 0.75) && Math.abs(box.w - box.h) < 2;
    const clip = cs.clipPath && cs.clipPath !== 'none' ? cs.clipPath : null;
    const poly = clip ? parsePolygon(clip, box.w, box.h) : null;

    if (clip && !poly) forbidWarn('clip', `${tag(el)} 的 clip-path 不是 polygon()，PPTX 无法表达`);
    if (!isCircle && radius && parseFloat(radius) > 0) {
      forbidWarn('radius', `${tag(el)} 用了 border-radius:${radius}；只有 50% 正圆能转换`);
    }

    // ---- 形状层（section 自身的底色由 slide.background 承担，不重复发射）
    if (isSlide) {
      // nothing
    } else if (isImg) {
      const src = el.getAttribute('src') || '';
      if (/^https?:/i.test(src)) {
        forbidWarn('remote', `${tag(el)} 用了远程图片（${src.slice(0, 48)}），PPTX 不会自动下载`);
      }
      shapes.push({
        kind: 'image',
        x: Math.round(box.x * 100) / 100,
        y: Math.round(box.y * 100) / 100,
        w: Math.round(box.w * 100) / 100,
        h: Math.round(box.h * 100) / 100,
        src,
        rotate,
        fit: getComputedStyle(el).objectFit || 'cover',
      });
    } else if (bgImage) {
      const m = bgImage.match(/url\(["']?([^"')]+)["']?\)/);
      if (m) {
        if (/^https?:/i.test(m[1])) {
          forbidWarn('remote', `${tag(el)} 的背景图是远程地址，PPTX 不会自动下载`);
        }
        shapes.push({
          kind: 'image',
          x: Math.round(box.x * 100) / 100,
          y: Math.round(box.y * 100) / 100,
          w: Math.round(box.w * 100) / 100,
          h: Math.round(box.h * 100) / 100,
          src: m[1],
          rotate,
          fit: 'fill',
          texture: true,
        });
      }
    } else if (poly) {
      shapes.push({
        kind: 'poly',
        x: Math.round(box.x * 100) / 100,
        y: Math.round(box.y * 100) / 100,
        w: Math.round(box.w * 100) / 100,
        h: Math.round(box.h * 100) / 100,
        fill: bg || '000000',
        rotate,
        points: poly,
      });
    } else if (isCircle) {
      shapes.push({
        kind: 'ellipse',
        x: Math.round(box.x * 100) / 100,
        y: Math.round(box.y * 100) / 100,
        w: Math.round(box.w * 100) / 100,
        h: Math.round(box.h * 100) / 100,
        fill: bg,
        rotate,
        outline: bg ? null : { color: hex(cs.borderTopColor) || '000000', width: parseFloat(cs.borderTopWidth) || 1 },
      });
    } else if (bg) {
      shapes.push({
        kind: 'rect',
        x: Math.round(box.x * 100) / 100,
        y: Math.round(box.y * 100) / 100,
        w: Math.round(box.w * 100) / 100,
        h: Math.round(box.h * 100) / 100,
        fill: bg,
        rotate,
      });
    }

    // 圆（ellipse）与多边形（custGeom）的边框由 shape 自身的 outline 承担，
    // 不能再拆成四条边发出去——否则 .sun--outline 会变成一个方框。
    if (!isImg && !isSlide && !isCircle && !poly) emitBorder(el, cs, box, rotate);
    if (cs.boxShadow && cs.boxShadow !== 'none') forbidWarn('shadow', `${tag(el)} 用了 box-shadow，会被拍平`);
    if (cs.textShadow && cs.textShadow !== 'none') forbidWarn('shadow', `${tag(el)} 用了 text-shadow，会被拍平`);
    if (cs.filter && cs.filter !== 'none') forbidWarn('filter', `${tag(el)} 用了 filter，会被拍平`);
    if (cs.backgroundImage && /gradient/i.test(cs.backgroundImage)) {
      forbidWarn('gradient', `${tag(el)} 用了渐变背景，PPTX 无渐变填充，已跳过`);
    }
    if (cs.mixBlendMode && cs.mixBlendMode !== 'normal') {
      forbidWarn('blend', `${tag(el)} 用了 mix-blend-mode（${cs.mixBlendMode}），叠色会变`);
    }
    if (cs.zIndex && cs.zIndex !== 'auto') {
      forbidWarn('zindex', `${tag(el)} 用了 z-index（${cs.zIndex}），只认 DOM 顺序`);
    }
    if (cs.position === 'fixed') {
      forbidWarn('fixed', `${tag(el)} 用了 position:fixed，会串页`);
    }
    for (const pe of ['::before', '::after']) {
      const pcs = getComputedStyle(el, pe);
      if (pcs && pcs.content && pcs.content !== 'none' && pcs.content !== 'normal') {
        forbidWarn('pseudo', `${tag(el)} 用 ${pe} 画图形，没有 DOM 盒子，量不到`);
      }
    }
    const tagName = el.tagName.toLowerCase();
    if (tagName === 'svg' || tagName === 'canvas') {
      forbidWarn('svg', `${tag(el)} 是内联 <${tagName}>，转不成形状`);
    }
    if (ancestorRotated && cs.transform && cs.transform !== 'none') {
      forbidWarn('nested', `${tag(el)} 嵌套旋转：PPT 没有 group，父子旋转叠加必然错位`);
    }
    if (!isSlide && cs.overflow !== 'visible'
        && (el.scrollHeight > el.clientHeight + 1 || el.scrollWidth > el.clientWidth + 1)) {
      forbidWarn('overflow', `${tag(el)} 的 overflow:hidden 真的裁掉了内容，PPT 里会溢出框外`);
    }

    // ---- 关键标题可以标 data-fidelity="raster"：整块渲成透明 PNG，
    //      这样即使用户机器没有黑体，字重也不会走样。
    // 只认 raster；image 之类的值没有任何实现，写上也只是自我安慰
    const fidelity = el.getAttribute && el.getAttribute('data-fidelity');
    if (fidelity && fidelity !== 'raster') {
      warnings.push(`${tag(el)} 的 data-fidelity="${fidelity}" 不支持，只有 "raster"`);
    }
    const rasterMark = fidelity === 'raster';
    if (!isImg && rasterMark && hasOwnText(el)) {
      rasterSeq += 1;
      const rid = `cst-r${index}-${rasterSeq}`;
      el.setAttribute('data-cst-raster', rid);
      // 用字的 ink 盒而不是元素盒：CJK 的 inline box 比 line-height 高出 40%，
      // 按元素盒截会把字的上下切掉。
      const rink = inkBox(el) || box;
      shapes.push({
        kind: 'raster',
        rasterId: rid,
        x: Math.round(rink.x * 100) / 100,
        y: Math.round(rink.y * 100) / 100,
        w: Math.round(rink.w * 100) / 100,
        h: Math.round(rink.h * 100) / 100,
      });
    } else if (!isImg && hasOwnText(el)) {
      // ---- 文本层：只取本元素的内联内容，块级子元素交给递归
      emitText(el, cs);
    }

    // ---- 入场动画：挂在本元素发射出的第一个形状上（通常是它的主色块或文本）
    if (animAttr && shapes.length > shapeStart) {
      const eff = ANIM_OK.has(animAttr) ? animAttr : null;
      if (!eff) {
        warnings.push(`${tag(el)} 的 data-anim="${animAttr}" 不在支持范围（fade/dissolve/wipe-up/down/left/right）`);
      } else {
        const step = parseInt(el.getAttribute('data-anim-step') || '0', 10) || 0;
        shapes[shapeStart].anim = { effect: eff, step };
      }
    }

    // ---- 递归：行内子元素已被父元素的文本流吸收，不再单独发射
    for (const child of el.children) {
      if (getComputedStyle(child).display === 'inline') continue;
      visit(child, depth + 1, ancestorRotated || !!(cs.transform && cs.transform !== 'none'));
    }
  };

  visit(section, 0, false);

  const bg = hex(getComputedStyle(section).backgroundColor) || 'FFFFFF';

  // 演讲备注：结构化字段优先，data-notes 作为自由补充。
  // 一段"讲稿"和一张"提词卡"的区别，就是有没有把任务、内容、转场、时长分开。
  const np = [];
  const purpose = section.getAttribute('data-purpose');
  const talk = section.getAttribute('data-talk');
  const transition = section.getAttribute('data-transition');
  const minutes = section.getAttribute('data-minutes');
  const freeNotes = section.getAttribute('data-notes');
  if (purpose) np.push(`【任务】${purpose.trim()}`);
  if (talk) {
    const items = talk.split('|').map((t) => t.trim()).filter(Boolean);
    np.push('【讲】\n' + items.map((t) => `・${t}`).join('\n'));
  }
  if (transition) np.push(`【转场】${transition.trim()}`);
  if (minutes) np.push(`【时长】${minutes} 分钟`);
  if (freeNotes) np.push(freeNotes.trim());
  const notes = np.join('\n\n');

  // 页面级越界提示（旋转元素按四角判断）
  const EPS = 0.6;
  for (const sh of shapes) {
    if (sh.x < -EPS || sh.y < -EPS || sh.x + sh.w > W + EPS || sh.y + sh.h > H + EPS) {
      if (sh.kind !== 'text' && sh.kind !== 'image') continue; // 色块越界是刻意的出血
      warnings.push(`${sh.kind} 超出画布：${Math.round(sh.x)},${Math.round(sh.y)} ${Math.round(sh.w)}×${Math.round(sh.h)}`);
    }
  }

  return {
    index,
    notes: notes.trim(),
    bg,
    ink: getComputedStyle(section).color,
    shapes,
    warnings,
  };
}
