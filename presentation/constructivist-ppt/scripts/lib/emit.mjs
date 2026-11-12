/**
 * emit.mjs — deck-spec → pptxgenjs（纯函数，不碰文件系统以外的东西）
 *
 * 这里的每一条硬约束都来自对 pptxgenjs 4.0.1 源码的核验，写错会静默毁版面：
 *  · margin 必须传数组 [0,0,0,0]，传 0 会被 falsy 判断吞掉，回落成 PowerPoint 默认内边距
 *  · valign 默认是 middle，必须显式 'top'
 *  · 任何 >100 的数值会被当成"已经是 EMU"透传，所以几何一律先过 px2in
 *  · custGeom 的 points 是相对形状左上角的局部英寸，w/h 必须等于点集紧包围盒
 */
import fs from 'node:fs';
import { px2in, px2pt, normDeg } from './units.mjs';

export const FONT_PROFILES = {
  // 写给"用户那台机器"：Office 自带、不会掉字
  office: { cjk: '微软雅黑', narrow: 'Arial Narrow', mono: 'Consolas', latin: 'Arial' },
  // 写给装了思源的人：字重更狠，构成功更足
  source: { cjk: '思源黑体 CN', narrow: 'Arial Narrow', mono: 'Consolas', latin: 'Arial' },
  // 原样输出 CSS 里的第一个 family，只适合本机预览
  asis: null,
};

function familyKind(stack = '') {
  if (/Mono|Consolas|Courier/i.test(stack)) return 'mono';
  if (/Narrow/i.test(stack)) return 'narrow';
  if (/CJK|Han Sans|YaHei|PingFang|Heiti|黑体/i.test(stack)) return 'cjk';
  return 'latin';
}

function resolveFont(run, profile) {
  const map = FONT_PROFILES[profile];
  if (!map) return run.family;
  return map[familyKind(run.stack || run.family)] || run.family;
}

const ALIGN = new Map([
  ['left', 'left'],
  ['start', 'left'],
  ['right', 'right'],
  ['end', 'right'],
  ['center', 'center'],
  ['justify', 'justify'],
]);

export function emitDeck(pptxgen, spec, { fontProfile = 'office', title = 'Constructivist Deck' } = {}) {
  if (!FONT_PROFILES[fontProfile]) throw new Error(`未知 fontProfile: ${fontProfile}`);

  const p = new pptxgen();
  p.defineLayout({ name: 'CST_16x9', width: 13.333, height: 7.5 });
  p.layout = 'CST_16x9';
  p.title = title;
  p.subject = 'Constructivist deck';
  p.author = 'constructivist-ppt skill';

  const report = { slides: [], warnings: [], shapeCount: 0 };

  spec.slides.forEach((sl, i) => {
    const slide = p.addSlide();
    slide.background = { color: sl.bg || 'FFFFFF' };

    const counts = { shape: 0, text: 0, image: 0 };
    let emitIndex = 0;

    for (const sh of sl.shapes) {
      if (sh.kind === 'rect' || sh.kind === 'ellipse' || sh.kind === 'poly') {
        const opts = {
          x: px2in(sh.x),
          y: px2in(sh.y),
          w: Math.max(px2in(sh.w), 0.004),
          h: Math.max(px2in(sh.h), 0.004),
          fill: sh.fill ? { color: sh.fill } : { type: 'none' },
          line: { type: 'none' },
        };
        if (sh.rotate) opts.rotate = normDeg(sh.rotate);
        if (sh.outline) {
          opts.fill = { type: 'none' };
          opts.line = { color: sh.outline.color, width: px2pt(sh.outline.width) };
        }

        if (sh.kind === 'poly') {
          const pts = sh.points.map((pt) => ({
            x: px2in(Math.max(0, Math.min(pt.x, sh.w))),
            y: px2in(Math.max(0, Math.min(pt.y, sh.h))),
          }));
          opts.points = [...pts, { close: true }];
          // 类型定义里没有 custGeom，必须用字符串字面量
          slide.addShape('custGeom', opts);
        } else {
          slide.addShape(sh.kind === 'ellipse' ? 'ellipse' : 'rect', opts);
        }
        sh.emitIndex = emitIndex++;
        counts.shape++;
      } else if (sh.kind === 'image') {
        const isData = /^data:image\//i.test(sh.src || '');
        if (!sh.src || (!isData && !fs.existsSync(sh.src))) {
          report.warnings.push(`第 ${i + 1} 页：图片不存在 ${sh.src}`);
          continue;
        }
        if (/^https?:/i.test(sh.src)) {
          report.warnings.push(`第 ${i + 1} 页：远程图片不会自动下载 ${sh.src.slice(0, 48)}`);
          continue;
        }
        const opts = {
          x: px2in(sh.x),
          y: px2in(sh.y),
          w: Math.max(px2in(sh.w), 0.01),
          h: Math.max(px2in(sh.h), 0.01),
        };
        if (isData) opts.data = sh.src;
        else opts.path = sh.src;
        if (sh.rotate) opts.rotate = normDeg(sh.rotate);
        if (sh.fit === 'fill') opts.sizing = { type: 'cover', w: opts.w, h: opts.h };
        else if (sh.fit === 'contain') opts.sizing = { type: 'contain', w: opts.w, h: opts.h };
        else opts.sizing = { type: 'cover', w: opts.w, h: opts.h };
        slide.addImage(opts);
        sh.emitIndex = emitIndex++;
        counts.image++;
      } else if (sh.kind === 'text') {
        emitText(slide, sh, fontProfile);
        sh.emitIndex = emitIndex++;
        counts.text++;
      }
    }

    if (sl.notes) slide.addNotes(sl.notes);

    report.shapeCount += counts.shape + counts.text + counts.image;
    report.slides.push({ index: i + 1, ...counts, total: counts.shape + counts.text + counts.image });
    if (counts.shape + counts.text + counts.image > 160) {
      report.warnings.push(`第 ${i + 1} 页图元 ${counts.shape + counts.text + counts.image} 个，超过 160，PowerPoint 里编辑会卡`);
    }
  });

  return { pptx: p, report };
}

function emitText(slide, sh, fontProfile) {
  const align = ALIGN.get(sh.align) || 'left';
  const runs = [];
  const paras = sh.paragraphs;
  if (!paras.length) return;

  paras.forEach((para, pi) => {
    const isLastPara = pi === paras.length - 1;
    para.runs.forEach((r, ri) => {
      const isLastRun = ri === para.runs.length - 1;
      const opts = {
        fontFace: resolveFont(r, fontProfile),
        fontSize: px2pt(r.size),
        color: r.color,
        bold: r.weight >= 600,
        italic: !!r.italic,
        charSpacing: px2pt(r.letterSpacing || 0),
        align: ALIGN.get(para.align) || align,
        lineSpacing: px2pt(sh.lineHeight),
        breakLine: isLastRun && !isLastPara,
      };
      runs.push({ text: r.transform === 'uppercase' ? r.text.toUpperCase() : r.text, options: opts });
    });
  });

  const box = {
    x: px2in(sh.x),
    y: px2in(sh.y),
    w: Math.max(px2in(sh.w), 0.02),
    h: Math.max(px2in(sh.h), 0.02),
    margin: [0, 0, 0, 0],
    valign: 'top',
    wrap: !!sh.wrap,
    fit: 'none',
    isTextBox: true,
  };
  if (sh.vertical) box.vert = 'eaVert';
  if (sh.rotate) box.rotate = normDeg(sh.rotate);

  slide.addText(runs, box);
}
