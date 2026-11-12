#!/usr/bin/env node
/**
 * selfcheck.mjs — 文档 ↔ 代码 ↔ 资产 的一致性自检（静态，无浏览器）
 *
 *   node scripts/selfcheck.mjs [--json] [--strict]
 *
 * 它回答的问题只有一个：**文档承诺的东西，代码和资产真的给了吗？**
 * 现有 skill 最贵的 bug 不是转换器写错，而是文档推荐了不存在的类、
 * 写了脚本不认的参数、声明了与实际不符的条数。
 *
 * 退出码：0 全过 / 1 有 error（--strict 时含 warn）/ 2 读不到文件
 */
import fs from 'node:fs';
import path from 'node:path';
import { spawnSync } from 'node:child_process';
import { loadRules, SKILL_ROOT } from './rules.mjs';

const argv = new Set(process.argv.slice(2));
const JSON_OUT = argv.has('--json');
const STRICT = argv.has('--strict');

const rules = loadRules();
const issues = [];

const CSS_PATH = path.join(SKILL_ROOT, 'assets', 'deck.css');
const css = fs.readFileSync(CSS_PATH, 'utf8');

/* ────────────────────────────── 文件集合 ────────────────────────────── */
function listMd(dir) {
  const abs = path.join(SKILL_ROOT, dir);
  if (!fs.existsSync(abs)) return [];
  return fs.readdirSync(abs)
    .filter((f) => f.endsWith('.md'))
    .map((f) => path.join(dir, f));
}

const DOC_FILES = [
  'SKILL.md',
  'README.md',
  ...listMd('references'),
  ...listMd('docs'),
].filter((rel) => fs.existsSync(path.join(SKILL_ROOT, rel)));

const SCRIPTS = fs.readdirSync(path.join(SKILL_ROOT, 'scripts'))
  .filter((f) => f.endsWith('.mjs'))
  .map((f) => `scripts/${f}`);

/* ────────────────────────────── 文本工具 ────────────────────────────── */
/** 返回 [{ line, text, inFence }]，保留行号，方便报 path:line */
function scan(rel) {
  const raw = fs.readFileSync(path.join(SKILL_ROOT, rel), 'utf8').split('\n');
  const out = [];
  let fence = null;
  let inBlock = false;
  for (let i = 0; i < raw.length; i++) {
    const text = raw[i];
    const fenceMatch = text.match(/^\s*(```|~~~)/);
    if (fenceMatch) {
      fence = fence ? null : fenceMatch[1];
      out.push({ line: i + 1, text, inFence: true });
      continue;
    }
    if (/<!--\s*(RULES|CODES):BEGIN/.test(text)) inBlock = true;
    out.push({ line: i + 1, text, inFence: !!fence, inBlock });
    if (/<!--\s*(RULES|CODES):END/.test(text)) inBlock = false;
  }
  return out;
}

const SCANNED = new Map(DOC_FILES.map((rel) => [rel, scan(rel)]));

function add(code, level, file, line, message, fix) {
  issues.push({ code, level, file, line, message, fix });
}

/* ─────────────────────── 1. 类名是否真实存在 ─────────────────────── */
const definedClasses = new Set();
for (const m of css.matchAll(/\.(-?[A-Za-z_][\w-]*)/g)) definedClasses.add(m[1]);
const deprecated = rules.classes.deprecated || {};
const ignoreExt = new Set(rules.classes.ignoreInDocs || []);

function checkClassToken(token, file, line, raw) {
  if (!token) return;
  if (ignoreExt.has(token)) return;
  if (definedClasses.has(token)) return;
  if (token in deprecated) {
    add('CLASS_REF', 'error', file, line, `\`.${token}\` 在 deck.css 里不存在（文档推荐了幽灵类）`, `改用 ${deprecated[token]}`);
    return;
  }
  if (token.length <= 2) return; // .md .js 这类扩展名残留
  add('CLASS_REF', 'error', file, line, `\`.${token}\` 未在 deck.css 定义`, '删掉该用法，或先在 deck.css 里实现它');
}

for (const [rel, lines] of SCANNED) {
  for (const { line, text, inFence } of lines) {
    if (inFence) {
      // 代码块里的 class="..." 也必须是真的
      for (const m of text.matchAll(/class="([^"]+)"/g)) {
        for (const cls of m[1].split(/\s+/).filter(Boolean)) checkClassToken(cls, rel, line, text);
      }
    } else {
      for (const span of text.matchAll(/`([^`]+)`/g)) {
        const content = span[1];
        if (content.startsWith('.')) {
          for (const m of content.matchAll(/\.([a-z][a-z0-9_-]*)/g)) checkClassToken(m[1], rel, line, text);
        }
      }
    }
  }
}

/* ─────────────────────── 2. CSS 变量 vs CLI 参数 ─────────────────────── */
const cssVars = new Set([...css.matchAll(/(--[a-z0-9-]+)\s*:/g)].map((m) => m[1]));
const cliFlags = new Set();
for (const rel of [...SCRIPTS, 'evals/run.mjs']) {
  if (!fs.existsSync(path.join(SKILL_ROOT, rel))) continue;
  const src = fs.readFileSync(path.join(SKILL_ROOT, rel), 'utf8');
  for (const m of src.matchAll(/['"](--[a-z][\w-]*)['"]/g)) cliFlags.add(m[1]);
  for (const m of src.matchAll(/args\.([a-z][\w-]*)/g)) cliFlags.add(`--${m[1]}`);
  for (const m of src.matchAll(/args\['([a-z][\w-]*)'\]/g)) cliFlags.add(`--${m[1]}`);
  if (rel === 'evals/run.mjs') {
    for (const f of ['--pipeline', '--agent', '--score', '--update-baseline', '--require-complete', '--repeats', '--reason', '--dir', '--list']) cliFlags.add(f);
  }
}
cliFlags.add('--help');

for (const [rel, lines] of SCANNED) {
  for (const { line, text, inFence } of lines) {
    if (inFence) continue; // 代码块里的 --flag 是外部命令参数
    for (const m of text.matchAll(/(?<![\w-])--([a-z][a-z0-9-]+)/g)) {
      const v = `--${m[1]}`;
      if (cssVars.has(v) || cliFlags.has(v)) continue;
      add('CSS_VAR', 'error', rel, line, `\`${v}\` 既不是 deck.css 里的变量，也不是任何脚本认识的参数`, '检查拼写，或删掉该引用');
    }
  }
}

/* ─────────────────────── 3. 文件路径是否存在 ─────────────────────── */
// 两种写法都要认：带目录前缀的 `references/x.md`，和正文里常见的裸文件名 `visual-system.md`。
// 早先只认前者，裸名引用（SKILL.md 里就有一处）完全绕过检查。
const PATH_RE = /\b(scripts|references|docs|assets|examples)\/([\w./-]+\.(?:mjs|md|html|css|json|png|jpg|svg))\b/g;
const BARE_RE = /(?<![\w/.-])([\w-]+\.(?:mjs|md|css|json|png|jpg|svg))(?![\w/.-])/g;
const KNOWN_DIRS = ['references', 'docs', 'assets', 'scripts', 'examples'];
const JUNK = new Set(['node_modules', '.git', '__pycache__', '.venv']);
const bareIndex = new Map();
for (const d of KNOWN_DIRS) {
  const dir = path.join(SKILL_ROOT, d);
  if (!fs.existsSync(dir)) continue;
  for (const e of fs.readdirSync(dir, { recursive: true })) {
    if (String(e).split(path.sep).some((part) => JUNK.has(part))) continue;
    const full = path.join(dir, e);
    if (!fs.statSync(full).isFile()) continue;
    const rel = path.relative(SKILL_ROOT, full);
    const base = path.basename(rel);
    bareIndex.set(base, [...(bareIndex.get(base) || []), rel]);
  }
}
for (const [rel, lines] of SCANNED) {
  for (const { line, text, inFence } of lines) {
    // 代码块里的路径是「命令要生成/要操作的目标」，不是对现存文件的引用——
    // 生成物（画廊缩略图、对照图）本来就不在包内，不该判成断链。
    if (inFence) continue;
    for (const m of text.matchAll(PATH_RE)) {
      const p = path.join(m[1], m[2]);
      if (p.includes('..')) continue;
      if (!fs.existsSync(path.join(SKILL_ROOT, p))) {
        add('PATH_REF', 'error', rel, line, `引用了不存在的文件 \`${p}\``, '删除该引用，或补齐文件');
      }
    }
    for (const m of text.matchAll(BARE_RE)) {
      const base = m[1];
      const hits = bareIndex.get(base);
      // 包内没有同名文件 → 视为对外部项目文档的引用（prior-art 里引别的仓库很正常），不判
      if (!hits) continue;
      // 裸名有歧义时要求写成完整路径：同名文件出现在多个目录，读者无从判断指哪个
      if (hits.length > 1) {
        add('PATH_REF', 'warn', rel, line, `裸文件名 \`${base}\` 有 ${hits.length} 处同名（${hits.join('、')}）`, `写成完整路径，如 ${hits[0]}`);
      }
    }
  }
}

// 反向：每个 CLI 脚本都应该在 README 里出现
const readme = fs.readFileSync(path.join(SKILL_ROOT, 'README.md'), 'utf8');
for (const rel of SCRIPTS) {
  const base = path.basename(rel);
  if (['selfcheck.mjs', 'rules.mjs', 'gen-rules-doc.mjs'].includes(base)) continue;
  if (!readme.includes(base)) {
    add('PATH_REF', 'warn', 'README.md', 0, `${base} 没有出现在 README 的命令表里`, '补一行用法，或说明它是内部脚本');
  }
}

/* ─────────────────────── 4. 命令参数是否被脚本接受 ─────────────────────── */
function stripComments(src) {
  return src.replace(/\/\*[\s\S]*?\*\//g, '').replace(/^\s*\/\/.*$/gm, '');
}
for (const [rel, lines] of SCANNED) {
  for (const { line, text, inFence } of lines) {
    if (!inFence) continue;
    for (const m of text.matchAll(/node\s+(scripts\/[\w-]+\.mjs)([^\n]*)/g)) {
      const script = m[1];
      const abs = path.join(SKILL_ROOT, script);
      if (!fs.existsSync(abs)) continue;
      const src = stripComments(fs.readFileSync(abs, 'utf8'));
      for (const fm of m[2].matchAll(/(--[a-z][\w-]*)/g)) {
        const flag = fm[1];
        const name = flag.replace(/^--/, '');
        if (new RegExp(`\\b${name}\\b`).test(src)) continue;
        add('CMD_REF', 'error', rel, line, `\`${script}\` 不认识参数 \`${flag}\``, '实现该参数，或从文档里删掉');
      }
    }
  }
}

/* ─────────────────────── 5. 生成块与 rules.json 同步 ─────────────────────── */
const gen = spawnSync(process.execPath, [path.join(SKILL_ROOT, 'scripts', 'gen-rules-doc.mjs'), '--check'], {
  cwd: SKILL_ROOT, encoding: 'utf8',
});
if (gen.status !== 0) {
  const msg = (gen.stderr || gen.stdout || '').trim().split('\n').filter(Boolean)[0] || '生成块过期';
  add('RULES_SYNC', 'error', 'assets/rules.json', 0, msg, '运行 node scripts/gen-rules-doc.mjs 重新生成');
}

// validate.mjs 里的规则码集合必须与 rules.json 双向相等
const RULE_SRC = ['validate.mjs', 'audit-text.mjs'];
const declared = new Set(Object.keys(rules.codes));
const used = new Set();
for (const f of RULE_SRC) {
  const src = fs.readFileSync(path.join(SKILL_ROOT, 'scripts', f), 'utf8');
  for (const m of src.matchAll(/(?:code:\s*|push\()['"]([A-Z]{3,12})['"]/g)) used.add(m[1]);
}
const auditOnly = new Set(rules.auditOnlyCodes || []);
for (const code of declared) {
  if (code === 'GATE' || auditOnly.has(code)) continue; // 流程项/内容审计码不需要版式检查器
  if (!used.has(code)) add('RULES_SYNC', 'error', 'scripts/validate.mjs', 0, `rules.json 声明的 \`${code}\` 在 validate.mjs 里没有实现`, `补实现，或从 rules.json 删除该码`);
}
for (const code of used) {
  if (!declared.has(code)) add('RULES_SYNC', 'error', RULE_SRC.join(' / '), 0, `脚本输出了未登记的规则码 \`${code}\``, '在 rules.json 的 codes 里登记');
}

/* ─────────────────────── 5b. 生成文档同步 ─────────────────────── */
for (const [script, label] of [['gen-themes.mjs', 'themes.json'], ['gen-layout-docs.mjs', 'layouts.json']]) {
  const r = spawnSync(process.execPath, [path.join(SKILL_ROOT, 'scripts', script), '--check'], {
    cwd: SKILL_ROOT, encoding: 'utf8',
  });
  if (r.status !== 0) {
    add('GEN_SYNC', 'error', `scripts/${script}`, 0,
      `${label} 的生成文档不一致：${(r.stderr || r.stdout || '').trim().split('\n')[0]}`,
      `运行 node scripts/${script} 重新生成`);
  }
}

const skillText = fs.readFileSync(path.join(SKILL_ROOT, 'SKILL.md'), 'utf8');
if (skillText.split('\n').length > 300) {
  add('SKILL_LENGTH', 'error', 'SKILL.md', 0, `SKILL.md ${skillText.split('\n').length} 行，超过 300`, '把实现细节下沉到 references');
}

/* ─────────────────────── 6. FORBID 清单与探测实现一致 ─────────────────────── */
const extractSrc = fs.readFileSync(path.join(SKILL_ROOT, 'scripts', 'lib', 'extract.mjs'), 'utf8');
const forbidIds = rules.forbid.map((f) => f.id);
const extractForbid = new Set([...extractSrc.matchAll(/FORBID\s*=\s*\[([\s\S]*?)\]/g)]
  .flatMap((m) => [...m[1].matchAll(/'([\w-]+)'/g)].map((x) => x[1])));
for (const id of forbidIds) {
  if (!extractForbid.has(id)) add('FORBID_SYNC', 'error', 'scripts/lib/extract.mjs', 0, `禁止项 \`${id}\` 没有探测实现`, '在 FORBID 数组与 visit() 里补检测');
}
for (const id of extractForbid) {
  if (!forbidIds.includes(id)) add('FORBID_SYNC', 'error', 'scripts/lib/extract.mjs', 0, `探测了未登记的禁止项 \`${id}\``, '在 rules.json 的 forbid 里登记');
}

/* ─────────────────────── 6b. 动画白名单三处同步 ─────────────────────── */
const animSrc = fs.readFileSync(path.join(SKILL_ROOT, 'scripts', 'lib', 'anim.mjs'), 'utf8');
const animOk = new Set([...extractSrc.matchAll(/ANIM_OK\s*=\s*new Set\(\[([\s\S]*?)\]\)/g)]
  .flatMap((m) => [...m[1].matchAll(/'([\w-]+)'/g)].map((x) => x[1])));
const aliasBlock = animSrc.match(/export const ALIASES\s*=\s*\{([\s\S]*?)\};/);
const aliases = new Set(aliasBlock
  ? [...aliasBlock[1].matchAll(/(?:'([\w-]+)'|([a-z][\w-]*))\s*:/g)].map((m) => m[1] || m[2])
  : []);
const animDoc = fs.readFileSync(path.join(SKILL_ROOT, 'references', 'animation.md'), 'utf8');
const docLine = animDoc.split('\n').find((l) => l.includes('`fade`') && l.includes('`wedge`')) || '';
const docAnim = new Set([...docLine.matchAll(/`([\w-]+)`/g)].map((m) => m[1]));
// 三方比对：extract.mjs 的 ANIM_OK 是源头，anim.mjs 的别名表与 animation.md 的文档行都要对齐它。
// 早先内层循环误写成了遍历 animOk 自身，导致第一组恒不报错（等于没查）。
const ANIM_SETS = [['anim.mjs ALIASES', aliases], ['animation.md', docAnim]];
for (const [label, set] of ANIM_SETS) {
  for (const v of animOk) {
    if (!set.has(v)) add('ANIM_SYNC', 'error', label, 0, `动画取值 \`${v}\` 未在三处同步`, '同步 extract.mjs / anim.mjs / animation.md');
  }
}
for (const v of docAnim) {
  if (!animOk.has(v)) add('ANIM_SYNC', 'error', 'references/animation.md', 0, `文档列了未实现的动画 \`${v}\``, '删掉，或在 ANIM_OK 里实现');
}

/* ─────────────────────── 7. 手写计数声明 ─────────────────────── */
// "一"开头的单数表述（一套 deck、一个骨架）不是会漂移的计数，不拦。
// 真正会漂的是"九套配色""十份 references"这类总数声明。
const COUNT_RE = /[二三四五六七八九十两\d]+\s*(?:套|份|个|条)\s*(?:配色|主题|子风格|骨架|版式|脚本|检查|references|命令)/g;
const COUNT_RE2 = /(?:九|十|余|十余)\s*(?:套|份|个|条)\s*(?:配色|主题|子风格|骨架|版式|脚本|检查|references|命令|规范)/g;
for (const [rel, lines] of SCANNED) {
  for (const { line, text, inFence, inBlock } of lines) {
    if (inFence || inBlock) continue;
    for (const m of text.matchAll(new RegExp(`${COUNT_RE.source}|${COUNT_RE2.source}`, 'g'))) {
      add('COUNT_CLAIM', 'error', rel, line, `手写计数「${m[0]}」会随文件增删漂移`, '删掉数字，或把该表放进生成块');
    }
  }
}

/* ─────────────────────── 8. 正文里手写的阈值 ─────────────────────── */
// 只盯"历史上真的漂移过"的那几个字面量。不做通用数字扫描——设计论述里的
// 面积区间、坐标、字号阶梯本来就需要具体数字，全都拦掉只会逼人写废话。
const THRESHOLD_RES = [
  /\b1\.12\b/g,
  /\b16px\b/g,
  /\b18px\b/g,
  /\b15px\b/g,
  /\b240\s*字/g,
  /(?:大一|两|三)倍/g,
  /\d+(?:\.\d+)?\s*倍宽/g,
  /[≤>]\s*4\s*色/g,
];
const FONT_TABLE_ROW = /^\|\s*`?\.[a-z]/;
for (const [rel, lines] of SCANNED) {
  for (const { line, text, inFence, inBlock } of lines) {
    if (inFence || inBlock) continue;
    if (FONT_TABLE_ROW.test(text.trim())) continue;
    for (const re of THRESHOLD_RES) {
      for (const m of text.matchAll(re)) {
        add('THRESHOLD_DRIFT', 'error', rel, line, `手写阈值「${m[0]}」与 rules.json 可能不一致`, '改成"见规则 N"，或写进生成块');
      }
    }
  }
}

/* ─────────────────────── 9. typography 字号表 ↔ deck.css ─────────────────────── */
const FONT_CLASSES = ['t-hero', 't-h1', 't-h2', 't-h3', 't-h4', 't-lead', 't-body', 't-small', 'meta', 'micro'];
const cssFont = new Map();
for (const cls of FONT_CLASSES) {
  const m = css.match(new RegExp(`\\.${cls}\\s*\\{[^}]*font-size:\\s*(\\d+)px`));
  if (m) cssFont.set(cls, Number(m[1]));
}
const typoRel = 'references/typography.md';
if (fs.existsSync(path.join(SKILL_ROOT, typoRel))) {
  const typo = fs.readFileSync(path.join(SKILL_ROOT, typoRel), 'utf8');
  for (const cls of FONT_CLASSES) {
    const m = typo.match(new RegExp(`\\|\\s*\`?\\.${cls}\`?\\s*\\|\\s*(\\d+)`));
    if (!m) continue;
    const docSize = Number(m[1]);
    const cssSize = cssFont.get(cls);
    if (cssSize && docSize !== cssSize) {
      add('CSS_FONT_SYNC', 'error', typoRel, 0, `文档写 \`.${cls}\` ${docSize}px，deck.css 是 ${cssSize}px`, '两边对齐（以 deck.css 为准）');
    }
  }
}

/* ─────────────────────── 10. deck.css 引用的资产 ─────────────────────── */
for (const m of css.matchAll(/url\(["']?([^"')]+)["']?\)/g)) {
  const p = m[1];
  if (/^(data:|https?:)/.test(p)) continue;
  if (!fs.existsSync(path.join(SKILL_ROOT, 'assets', p))) {
    add('ASSET_REF', 'error', 'assets/deck.css', 0, `纹理所指的 \`${p}\` 不存在`, '补齐文件或删掉该声明');
  }
}

/* ─────────────────────── 11. frontmatter ─────────────────────── */
const skillRaw = fs.readFileSync(path.join(SKILL_ROOT, 'SKILL.md'), 'utf8');
const fm = skillRaw.match(/^---\n([\s\S]*?)\n---/);
if (!fm) {
  add('FRONTMATTER', 'error', 'SKILL.md', 1, '缺少 YAML frontmatter', '补 name / description');
} else {
  const nameM = fm[1].match(/^name:\s*(.+)$/m);
  const descM = fm[1].match(/^description:\s*([\s\S]*?)(?=\n[a-z-]+:|$)/m);
  if (!nameM) add('FRONTMATTER', 'error', 'SKILL.md', 1, 'frontmatter 缺 name', '补 name，且与目录名一致');
  else if (nameM[1].trim() !== path.basename(SKILL_ROOT)) {
    add('FRONTMATTER', 'error', 'SKILL.md', 1, `name「${nameM[1].trim()}」与目录名「${path.basename(SKILL_ROOT)}」不一致`, '改成同名');
  }
  if (!descM) add('FRONTMATTER', 'error', 'SKILL.md', 1, 'frontmatter 缺 description', '补触发词与能力边界');
  else {
    const d = descM[1].replace(/\s+/g, ' ').trim();
    if (d.length > 1024) add('FRONTMATTER', 'error', 'SKILL.md', 1, `description ${d.length} 字，超过 1024`, '压缩到一句话');
    if (/[<>]/.test(d)) add('FRONTMATTER', 'error', 'SKILL.md', 1, 'description 含尖括号', '删掉 XML 风格标记');
    if (COUNT_RE.test(d)) add('FRONTMATTER', 'error', 'SKILL.md', 1, 'description 里写死了数量', '删掉数量，改描述能力');
  }
}

/* ─────────────────────── 12. 相对链接 ─────────────────────── */
for (const rel of DOC_FILES) {
  const lines = SCANNED.get(rel);
  for (const { line, text } of lines) {
    for (const m of text.matchAll(/\]\(([^)#][^)]*\.md)(?:#[^)]*)?\)/g)) {
      const target = m[1];
      if (/^(https?:|\/)/.test(target)) continue;
      const p = path.resolve(path.dirname(path.join(SKILL_ROOT, rel)), target);
      if (!fs.existsSync(p)) add('DEAD_LINK', 'error', rel, line, `链接指向不存在的 \`${target}\``, '改链接或补文件');
    }
  }
}

/* ─────────────────────── 13. 已知过期陈述 ─────────────────────── */
for (const claim of rules.staleClaims || []) {
  for (const [rel, lines] of SCANNED) {
    for (const { line, text } of lines) {
      if (text.includes(claim)) {
        add('STALE_CLAIM', 'error', rel, line, `过期陈述「${claim}」已被代码推翻`, '删除，或标注 [已解决 日期]');
      }
    }
  }
}

/* ────────────────────────────── 输出 ────────────────────────────── */
const ORDER = ['CLASS_REF', 'CSS_VAR', 'PATH_REF', 'CMD_REF', 'RULES_SYNC', 'GEN_SYNC', 'FORBID_SYNC',
  'SKILL_LENGTH', 'ANIM_SYNC', 'COUNT_CLAIM', 'THRESHOLD_DRIFT', 'CSS_FONT_SYNC', 'ASSET_REF', 'FRONTMATTER', 'DEAD_LINK', 'STALE_CLAIM'];
issues.sort((a, b) => {
  const d = ORDER.indexOf(a.code) - ORDER.indexOf(b.code);
  if (d) return d;
  if (a.file !== b.file) return a.file < b.file ? -1 : 1;
  return a.line - b.line;
});

const errors = issues.filter((i) => i.level === 'error');
const warns = issues.filter((i) => i.level === 'warn');

if (JSON_OUT) {
  console.log(JSON.stringify({ ok: errors.length === 0, errors: errors.length, warnings: warns.length, issues }, null, 2));
} else {
  for (const i of issues) {
    const mark = i.level === 'error' ? '✖' : '△';
    const where = i.line ? `${i.file}:${i.line}` : i.file;
    console.log(`${mark} [${i.code}] ${where}  ${i.message}`);
    if (i.fix) console.log(`            fix: ${i.fix}`);
  }
  const total = ORDER.length;
  const failed = new Set(issues.map((i) => i.code)).size;
  console.log(`\n${total - failed}/${total} 项检查通过  error ${errors.length}  warn ${warns.length}`);
}

process.exit(errors.length ? 1 : (STRICT && warns.length ? 1 : 0));
