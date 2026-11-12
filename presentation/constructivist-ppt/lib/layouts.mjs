/**
 * layouts.mjs — assets/layouts.json + assets/layouts/L*.html 的唯一读取入口
 *
 * 契约在 JSON，几何在 HTML；本文件负责：
 *   · 校验目录本身（id/role/slot/form/group）
 *   · 展开 group 槽位（items.1.num …）
 *   · 检查模板里的 data-slot / data-slot-block / {{slot:…}} 与 JSON 一一对应
 *   · 给 plan/scaffold/validate/selfcheck 提供同一套数据
 */
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const HERE = path.dirname(fileURLToPath(import.meta.url));
export const SKILL_ROOT = path.resolve(HERE, '../..');
export const LAYOUTS_PATH = path.join(SKILL_ROOT, 'assets', 'layouts.json');
export const TEMPLATE_DIR = path.join(SKILL_ROOT, 'assets', 'layouts');

const FORMS = new Set(['T1', 'T2', 'T3', 'media']);
const ROLE_OK = new Set([
  'cover', 'context', 'thesis', 'method', 'evidence', 'data',
  'comparison', 'sequence', 'case', 'quote', 'section', 'closing',
]);

let cache = null;

export function loadLayouts(explicitPath) {
  if (cache && !explicitPath) return cache;
  const file = explicitPath || LAYOUTS_PATH;
  if (!fs.existsSync(file)) {
    throw new Error(`找不到 layouts.json：${file}。版式目录缺失时不做任何猜测。`);
  }
  const cat = JSON.parse(fs.readFileSync(file, 'utf8'));
  validateCatalog(cat, file);
  if (!explicitPath) cache = cat;
  return cat;
}

function validateCatalog(cat, file) {
  const fail = (msg) => { throw new Error(`layouts.json 无效（${file}）：${msg}`); };
  if (cat.version !== 1) fail('version 必须是 1');
  if (!Array.isArray(cat.layouts) || !cat.layouts.length) fail('layouts[] 为空');
  if (!Array.isArray(cat.roles) || !cat.roles.length) fail('roles[] 为空');
  const roles = new Set(cat.roles);
  for (const r of roles) if (!ROLE_OK.has(r)) fail(`未知 role：${r}`);
  const ids = new Set();
  for (const l of cat.layouts) {
    if (!/^L\d{2}$/.test(l.id || '')) fail(`版式 id 必须是 L01 形式：${l.id}`);
    if (ids.has(l.id)) fail(`版式 id 重复：${l.id}`);
    ids.add(l.id);
    if (!l.name || !l.family) fail(`${l.id} 缺 name/family`);
    if (!Array.isArray(l.roles) || !l.roles.length) fail(`${l.id} 缺 roles`);
    for (const r of l.roles) if (!roles.has(r)) fail(`${l.id} 引用了未登记的 role：${r}`);
    if (!l.slots || typeof l.slots !== 'object') fail(`${l.id} 缺 slots`);
    for (const [name, s] of Object.entries(l.slots)) {
      if (!/^[a-z][a-zA-Z0-9]*$/.test(name)) fail(`${l.id}.${name} 槽位名不合法`);
      if (!FORMS.has(s.form)) fail(`${l.id}.${name} form 非法：${s.form}`);
      if (s.form !== 'media' && (!Number.isInteger(s.maxCJK) || s.maxCJK < 1)) {
        fail(`${l.id}.${name} 缺 maxCJK`);
      }
    }
    if (l.groups) {
      for (const [gname, g] of Object.entries(l.groups)) {
        if (!/^[a-z][a-zA-Z0-9]*$/.test(gname)) fail(`${l.id}.${gname} group 名不合法`);
        if (!Number.isInteger(g.count) || g.count < 1) fail(`${l.id}.${gname} 缺 count`);
        if (g.min && g.min > g.count) fail(`${l.id}.${gname} min > count`);
        if (g.max && g.max < g.count) fail(`${l.id}.${gname} max < count`);
        if (!g.slots || typeof g.slots !== 'object') fail(`${l.id}.${gname} 缺 slots`);
        for (const [name, s] of Object.entries(g.slots)) {
          if (!FORMS.has(s.form)) fail(`${l.id}.${gname}.${name} form 非法`);
          if (s.form !== 'media' && (!Number.isInteger(s.maxCJK) || s.maxCJK < 1)) {
            fail(`${l.id}.${gname}.${name} 缺 maxCJK`);
          }
        }
      }
    }
  }
  // 模板 ↔ JSON 一一对应
  for (const l of cat.layouts) {
    const tpl = readTemplate(l.id);
    if (!tpl.includes('{{folio}}')) fail(`${l.id} 模板缺 {{folio}}`);
    if (!tpl.includes('{{texture}}')) fail(`${l.id} 模板缺 {{texture}}`);
    const expected = expandSlots(l);
    const slotAttrs = new Set([...tpl.matchAll(/data-slot="([^"]+)"/g)].map((m) => m[1]));
    const slotVars = new Set([...tpl.matchAll(/\{\{slot:([^}]+)\}\}/g)].map((m) => m[1]));
    for (const name of expected.keys()) {
      if (!slotAttrs.has(name)) fail(`${l.id} 模板缺 data-slot="${name}"`);
      if (!slotVars.has(name)) fail(`${l.id} 模板缺 {{slot:${name}}}`);
    }
    for (const name of slotAttrs) {
      if (!expected.has(name)) fail(`${l.id} 模板多出未登记槽位：${name}`);
    }
    for (const name of slotVars) {
      if (!expected.has(name)) fail(`${l.id} 模板多出未登记占位符：${name}`);
    }
    for (const m of tpl.matchAll(/data-slot-block="([^"]+)"/g)) {
      const name = m[1];
      if (!expected.has(name) && !Object.keys(l.groups || {}).some((g) => name.startsWith(`${g}.`))) {
        fail(`${l.id} 模板的 data-slot-block="${name}" 不是槽位或 group`);
      }
    }
  }
}

export function readTemplate(id) {
  const file = path.join(TEMPLATE_DIR, `${id}.html`);
  if (!fs.existsSync(file)) throw new Error(`找不到版式模板：${file}`);
  return fs.readFileSync(file, 'utf8');
}

/** 平铺槽位：普通槽位 + group 展开（items.1.num …） */
export function expandSlots(layout) {
  const out = new Map();
  for (const [name, s] of Object.entries(layout.slots || {})) out.set(name, { ...s, name });
  for (const [gname, g] of Object.entries(layout.groups || {})) {
    // 模板可能预展开到 max（如表格 4–6 行），count 只是默认填充数
    for (let i = 1; i <= (g.max || g.count); i++) {
      for (const [name, s] of Object.entries(g.slots)) {
        out.set(`${gname}.${i}.${name}`, {
          ...s, name: `${gname}.${i}.${name}`, group: gname, index: i,
        });
      }
    }
  }
  return out;
}

export function layoutById(cat, id) {
  return (cat.layouts || []).find((l) => l.id === id) || null;
}

export function roleCandidates(cat, role) {
  return (cat.layouts || []).filter((l) => (l.roles || []).includes(role));
}

export function planThresholds(cat) {
  return cat.plan || {};
}
