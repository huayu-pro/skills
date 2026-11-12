/**
 * anim.mjs — 往生成的 pptx 里注入入场动画（<p:timing>）
 *
 * pptxgenjs 没有动画 API，所以这一步是"事后改包"：
 * 解 zip → 在每页 spTree 里找到第 N 个 <p:sp>/<p:pic> 的 id →
 * 生成 <p:timing> → 插到 </p:clrMapOvr> 之后 → 重新打包。
 *
 * 结构不是猜的，是照 BramAlkema/pptx-animation-skill 的实证模板
 * （oracle/entr/filter_effect.xml）来的。那份 oracle 是在 PowerPoint 里
 * 逐帧截图验证过的；而"看起来合法、播放时被静默丢弃"的写法有 7 种
 * （见其 references/dead_paths.md）。
 *
 * 三条最容易写错的：
 *   1. 入场必须有 <p:set style.visibility="visible"> 作为前置，
 *      否则没有"从不可见到可见"的过渡起点，animEffect 不触发；
 *   2. fade 的 presetID 是 9（10 是 dissolve）；
 *   3. wipe(up) 的 presetSubtype 是 1（4 是 wipe(down)，方向反的）。
 */

import fs from 'node:fs';
import { createRequire } from 'node:module';

const require = createRequire(import.meta.url);
const JSZip = require('jszip');

/**
 * 入口滤波器表 —— 逐条抄自 pptx-animation-skill 的
 * oracle/filter_vocabulary.xml（只收 verification=visually-verified 的条目）。
 * 抓取日期 2026-10-21。上游表变了要重新对一遍。
 */
export const FILTERS = {
  fade: { presetID: 9, presetSubtype: 0, filter: 'fade' },
  dissolve: { presetID: 10, presetSubtype: 0, filter: 'dissolve' },
  'wipe-up': { presetID: 22, presetSubtype: 1, filter: 'wipe(up)' },
  'wipe-down': { presetID: 22, presetSubtype: 4, filter: 'wipe(down)' },
  'wipe-left': { presetID: 22, presetSubtype: 8, filter: 'wipe(left)' },
  'wipe-right': { presetID: 22, presetSubtype: 2, filter: 'wipe(right)' },
  wedge: { presetID: 37, presetSubtype: 0, filter: 'wedge' },
  'circle-in': { presetID: 18, presetSubtype: 12, filter: 'circle(in)' },
  'circle-out': { presetID: 19, presetSubtype: 12, filter: 'circle(out)' },
  'wheel-1': { presetID: 21, presetSubtype: 1, filter: 'wheel(1)' },
  'wheel-2': { presetID: 21, presetSubtype: 2, filter: 'wheel(2)' },
  'strips-dl': { presetID: 25, presetSubtype: 0, filter: 'strips(downLeft)' },
  blinds: { presetID: 42, presetSubtype: 10, filter: 'blinds(horizontal)' },
  checker: { presetID: 43, presetSubtype: 0, filter: 'checkerboard(across)' },
  barn: { presetID: 45, presetSubtype: 0, filter: 'barn(inVertical)' },
  randombar: { presetID: 52, presetSubtype: 0, filter: 'randombar(horizontal)' },
};

/** 作者侧简写到规范名的别名 */
export const ALIASES = {
  fade: 'fade',
  wipe: 'wipe-up',
  'wipe-up': 'wipe-up',
  'wipe-down': 'wipe-down',
  'wipe-left': 'wipe-left',
  'wipe-right': 'wipe-right',
  dissolve: 'dissolve',
  wedge: 'wedge',
  'circle-in': 'circle-in',
  'circle-out': 'circle-out',
};

/** 作者侧可用的 data-anim 取值（给 extract 做白名单用） */
export const EFFECT_NAMES = Object.keys(ALIASES);

/** 收集一页里 sp/pic 的 spid，按文档顺序 */
function collectSpIds(xml) {
  const marks = [...xml.matchAll(/<p:(sp|pic)[ >]/g)].map((m) => m.index);
  const ids = [];
  for (let i = 0; i < marks.length; i++) {
    const seg = xml.slice(marks[i], i + 1 < marks.length ? marks[i + 1] : marks[i] + 4000);
    const m = seg.match(/<p:cNvPr id="(\d+)"/);
    ids.push(m ? m[1] : null);
  }
  return ids;
}

/** 单个入场 par，结构照 oracle/entr/filter_effect.xml */
function parXml({ spid, spec, par, delay, duration, nodeType }) {
  const setBid = par + 1;
  const effBid = par * 10 + 1;
  return (
    `<p:par><p:cTn id="${par}" dur="${duration}" fill="hold" nodeType="${nodeType}" grpId="${par}" ` +
    `presetID="${spec.presetID}" presetClass="entr" presetSubtype="${spec.presetSubtype}">` +
    `<p:stCondLst><p:cond delay="${delay}"/></p:stCondLst>` +
    `<p:childTnLst>` +
    // ① 先置可见 —— 少了这个，入场没有过渡起点
    `<p:set><p:cBhvr><p:cTn id="${setBid}" dur="1" fill="hold">` +
    `<p:stCondLst><p:cond delay="0"/></p:stCondLst></p:cTn>` +
    `<p:tgtEl><p:spTgt spid="${spid}"/></p:tgtEl>` +
    `<p:attrNameLst><p:attrName>style.visibility</p:attrName></p:attrNameLst>` +
    `</p:cBhvr><p:to><p:strVal val="visible"/></p:to></p:set>` +
    // ② 再做光学过渡
    `<p:animEffect transition="in" filter="${spec.filter}"><p:cBhvr>` +
    `<p:cTn id="${effBid}" dur="${duration}"/>` +
    `<p:tgtEl><p:spTgt spid="${spid}"/></p:tgtEl>` +
    `</p:cBhvr></p:animEffect>` +
    `</p:childTnLst></p:cTn></p:par>`
  );
}

/**
 * 整棵 timing 树。
 * nodeType：首个 clickEffect（与 oracle 一致），同页后续 withEffect + 递增 delay，
 * 这样一次点击就能把整组依次揭示。mode='click' 时全部 clickEffect（完全对齐 oracle）。
 */
function buildTiming(targets, mode) {
  let parId = 5; // 1=tmRoot, 2=mainSeq, 3/4 留给结构
  const pars = targets
    .map((t, i) => {
      const nodeType = i === 0 || mode === 'click' ? 'clickEffect' : 'withEffect';
      const xml = parXml({ ...t, par: parId, nodeType });
      parId += 2; // 奇数给 par，偶数留给 set（par+1），不会撞
      return xml;
    })
    .join('');

  return (
    `<p:timing><p:tnLst><p:par><p:cTn id="1" dur="indefinite" restart="never" nodeType="tmRoot">` +
    `<p:childTnLst><p:seq concurrent="1" nextAc="seek">` +
    `<p:cTn id="2" dur="indefinite" nodeType="mainSeq"><p:childTnLst>` +
    pars +
    `</p:childTnLst></p:cTn></p:seq></p:childTnLst>` +
    `</p:cTn></p:par></p:tnLst></p:timing>`
  );
}

/**
 * 注入后自检。五条硬断言——动画写错在 PowerPoint 里只是"没反应"，
 * 用户不会报错，只会觉得这个 skill 坏了。所以宁可直接判失败。
 */
export function verifyTiming(timingXml, slideXml, expected) {
  const errs = [];
  const pars = [...timingXml.matchAll(/<p:par>([\s\S]*?)<\/p:cTn><\/p:par>/g)].map((m) => m[1]);
  if (pars.length !== expected) errs.push(`par 数量 ${pars.length} ≠ 期望 ${expected}`);

  const ctIds = [...timingXml.matchAll(/<p:cTn id="(\d+)"/g)].map((m) => m[1]);
  if (new Set(ctIds).size !== ctIds.length) errs.push('p:cTn id 有重复');

  const spIds = new Set(collectSpIds(slideXml).filter(Boolean));

  pars.forEach((p, i) => {
    const sets = (p.match(/<p:set>/g) || []).length;
    const effs = (p.match(/<p:animEffect/g) || []).length;
    if (sets !== 1) errs.push(`第 ${i + 1} 个 par 的 p:set 数量是 ${sets}（应为 1）`);
    if (effs !== 1) errs.push(`第 ${i + 1} 个 par 的 p:animEffect 数量是 ${effs}（应为 1）`);
    if (!/<p:attrName>style\.visibility<\/p:attrName>/.test(p)) errs.push(`第 ${i + 1} 个 par 缺 style.visibility`);
    if (!/<p:strVal val="visible"\/>/.test(p)) errs.push(`第 ${i + 1} 个 par 的 to 不是 visible`);
    if (!/grpId="\d+"/.test(p)) errs.push(`第 ${i + 1} 个 par 缺 grpId`);
    if (!/<p:spTgt spid="\d+"\/>/.test(p)) errs.push(`第 ${i + 1} 个 par 没有指向任何形状（缺 spTgt）`);

    const filter = (p.match(/<p:animEffect[^>]*filter="([^"]+)"/) || [])[1];
    const pid = (p.match(/presetID="(\d+)"/) || [])[1];
    const psub = (p.match(/presetSubtype="(\d+)"/) || [])[1];
    const known = Object.values(FILTERS).find((f) => f.filter === filter);
    if (!known) {
      errs.push(`第 ${i + 1} 个 par 的 filter「${filter}」不在实证表里`);
    } else if (String(known.presetID) !== pid || String(known.presetSubtype) !== psub) {
      errs.push(
        `第 ${i + 1} 个 par 的 preset ${pid}/${psub} 与「${filter}」不匹配（应为 ${known.presetID}/${known.presetSubtype}）`,
      );
    }

    for (const m of p.matchAll(/<p:spTgt spid="(\d+)"\/>/g)) {
      if (!spIds.has(m[1])) errs.push(`第 ${i + 1} 个 par 指向的 spid ${m[1]} 在 spTree 里不存在`);
    }
  });
  return errs;
}

/**
 * @param {string} pptxPath
 * @param {object} spec  deck-spec（shapes 上带 emitIndex 与 anim）
 */
export async function applyAnimations(pptxPath, spec, { defaultDuration = 500, stepDelay = 120, mode = 'chain' } = {}) {
  const warnings = [];
  const errors = [];
  const buf = fs.readFileSync(pptxPath);
  const zip = await JSZip.loadAsync(buf);

  let totalTargets = 0;
  let touchedSlides = 0;

  for (let i = 0; i < spec.slides.length; i++) {
    const sl = spec.slides[i];
    const animated = sl.shapes.filter((s) => s.anim && Number.isInteger(s.emitIndex));
    if (!animated.length) continue;

    const name = `ppt/slides/slide${i + 1}.xml`;
    const f = zip.file(name);
    if (!f) {
      warnings.push(`第 ${i + 1} 页：pptx 里找不到 ${name}`);
      continue;
    }
    let xml = await f.async('string');

    if (xml.includes('<p:timing')) {
      warnings.push(`第 ${i + 1} 页：已有 timing，跳过`);
      continue;
    }

    const ids = collectSpIds(xml);
    const targets = [];
    const ordered = [...animated].sort((a, b) => a.emitIndex - b.emitIndex);

    for (const sh of ordered) {
      const spid = ids[sh.emitIndex];
      const specEntry = FILTERS[ALIASES[sh.anim.effect] || sh.anim.effect];
      if (!specEntry) {
        warnings.push(`第 ${i + 1} 页：未知效果「${sh.anim.effect}」，已跳过`);
        continue;
      }
      if (!spid) {
        warnings.push(`第 ${i + 1} 页：第 ${sh.emitIndex} 个形状找不到 spid，已跳过`);
        continue;
      }
      targets.push({
        spid,
        spec: specEntry,
        delay: (sh.anim.step || 0) * stepDelay,
        duration: sh.anim.duration || defaultDuration,
      });
    }
    if (!targets.length) continue;

    const seen = new Set();
    for (const t of targets) {
      if (seen.has(t.spid)) warnings.push(`第 ${i + 1} 页：spid ${t.spid} 重复，动画可能错位`);
      seen.add(t.spid);
    }

    const timing = buildTiming(targets, mode);
    const check = verifyTiming(timing, xml, targets.length);
    if (check.length) {
      // 自检不过就不写进去 —— 宁可没有动画，也不要一个"看起来有、播不出来"的
      errors.push(...check.map((e) => `第 ${i + 1} 页：${e}`));
      continue;
    }

    // <p:sld> 子元素顺序：cSld → clrMapOvr → transition → timing → extLst
    if (xml.includes('</p:clrMapOvr>')) {
      xml = xml.replace('</p:clrMapOvr>', `</p:clrMapOvr>${timing}`);
    } else {
      xml = xml.replace('</p:cSld>', `</p:cSld>${timing}`);
    }

    zip.file(name, xml);
    touchedSlides++;
    totalTargets += targets.length;
  }

  if (touchedSlides) {
    const out = await zip.generateAsync({ type: 'nodebuffer', compression: 'DEFLATE' });
    fs.writeFileSync(pptxPath, out);
  }

  return { slides: touchedSlides, targets: totalTargets, warnings, errors };
}

/** 注入后复核：每个 slide 的 XML 是否良构（用浏览器 DOMParser） */
export async function verifyXml(page, pptxPath) {
  const buf = fs.readFileSync(pptxPath);
  const zip = await JSZip.loadAsync(buf);
  const bad = [];
  for (const name of Object.keys(zip.files)) {
    if (!/^ppt\/slides\/slide\d+\.xml$/.test(name)) continue;
    const xml = await zip.file(name).async('string');
    const err = await page.evaluate((s) => {
      const doc = new DOMParser().parseFromString(s, 'application/xml');
      const e = doc.querySelector('parsererror');
      return e ? e.textContent.slice(0, 160) : null;
    }, xml);
    if (err) bad.push(`${name}: ${err}`);
  }
  return bad;
}
