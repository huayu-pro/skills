# CHANGELOG

## [3.3.1] — 2026-10-25

发布平台不接受二进制文件。本版把包内全部二进制（3 张 PNG + 2 张 PPTX）改为纯文本方案，包内不再含任何非文本文件。

### 新增：纯文本化

- **纹理与示例图改用 SVG**：`assets/textures/grain.svg`（520 B）/ `halftone.svg`（335 B）/ `assets/img/industry.svg`（纯文本、参数与原 PNG 配方一致：grain 用 feTurbulence 出颗粒，halftone 12px 网点，industry 10px 点阵剪影）。`deck.css` 改引 SVG；`gen-textures.mjs` 改产 SVG。
- **转换器加 SVG 栅格化**：PPTX 的图片槽只认 PNG/JPEG，直接塞 SVG 会产出"后缀 .png、内容是文本"的假媒体文件（PowerPoint 打不开，实测已证伪）。`build-deck.mjs` 现在在装配前用浏览器（既有硬依赖）把 SVG 栅格化成临时 PNG，用后即清，不落交付目录。实测 PPTX 媒体目录 100% 真 PNG、零 SVG 残留、文字仍是原生可编辑 run。

### 移出包：生成物

- **画廊缩略图与联系表**（26 张 PNG）、**主题对照图**（37 张 PNG）、**示例 PPTX**（2 张）：全部是生成物，不再随包发布。要看图时本地跑一条命令：
  - 缩略图：`node scripts/scaffold.mjs --gallery examples/layout-gallery --force && node scripts/render.mjs examples/layout-gallery/deck.html --out examples/layout-gallery --sheet`
  - 对照图：`node scripts/style-preview.mjs examples/demo-31.html --out examples/style-comparison`
- `references/layout-specs.md` 的图片引用改为「存在才嵌入」；SKILL.md / README / `references/palettes.md` 的硬引用同步改为生成命令。`selfcheck` 的 PATH_REF 会拦住任何写死不存在的二进制引用。

### 版本

- 版本 3.2.0 → **3.3.1**（改动以修复为主，配少量文档结构调整；3.3.0 未对外发布过，故直接递补 patch）。同步：frontmatter / `_meta.json` / `CHANGELOG` / `rules.json` / `package.json` / `layouts.json` / `themes.json` 的 skillVersion。

## [3.3.0] — 2026-10-25

门禁可信化 + 版式补全。本版主题是「让门禁说真话」：修掉会说谎的检查、补齐四个只有单一候选的叙事角色、补上三处「文档承诺但代码没实现」。

### 新增：版式

- **L22 体量对比 / L23 巨引语 / L24 斜切章节 / L25 横幅收束**（`layouts.json` 契约 + `assets/layouts/L*.html` 骨架 + 画廊示例 + `references/layout-specs.md` 生成文档）。
  起因：12 个叙事角色里 comparison / quote / section / closing **各只有 1 个候选版式**，而 `STRUCTURE` 门禁要求「连续同版式 ≤2 页、单版式占比 ≤40%」——任何含两次对比或多幕 section 的 deck 必然撞轮换门禁且无解。现在四个角色各有两个候选。
- 画廊从 20 页扩到 24 页，`examples/layout-gallery/` 的缩略图与联系表同步重出。

### 新增：主题

- **`theme-archive-ember` 档案焦墨 / `theme-archive-rust` 档案锈橙**（A 子风格）。此前 A 只有 `theme-archive` 一套，而 SKILL.md 推荐「文化/品牌/观点 → A」——最主要推荐项没有选择空间。
- `style-preview.mjs` 默认覆盖**全部主题**（此前硬编码 `archive,signal,c1,c4`，新增主题永远进不了对照图，而 SKILL.md 又让用户「先看对照图再选子风格」）。`themes.png` 已按 12 套重出。
- 两套新主题经 WCAG 全配对复核：`pop/bg` ≥4.4、`pop/fg` ≥3.3，均满足规则 8 的大字门槛。

### 新增：脚本

- **`scripts/plan-from-deck.mjs`** —— deck → plan 反向提取。此前流程是 plan→scaffold→deck 单向的，接手别人做的 deck 只能人眼一页页抄回 plan，而 8 页以上又必须过 plan check。读不出来的字段（`audience`、图表数值）如实留空并列出缺口，不编造。
- **`scripts/reorder.mjs`** —— 页序重排 / 删页 / 复制页。此前「改结构要改骨架文件再整份重新生成」，单页插删换位没有脚本支持。复制页自动换新 id（否则 plan check 报重复）。
- **`scripts/prepare-image.mjs`** —— 图片一键网点化，封装 `references/image-prompts.md` 里原本 7 条手敲 ImageMagick 命令。参数自检（网点半径必须小于半格，否则糊成一片）。

### 修复：会说谎的门禁

- **对比度采样对第 N 页一律误判**（`validate.mjs`）。`elementsFromPoint` 对视口外的点返回空栈，采样就静默回落到 slide 底色：白字压黑块被判成「纸底白字」（假红 1.0），深字压墨底被判成「纸底深字」（**假绿**）。修法：逐页 `scrollIntoView` 后再采样。实测第 24 页从误报 1.0 变为真实 3.9。
- **`gate.mjs` 默认非 strict**，与 SKILL.md「总门禁、全绿」的声称不符：不传 `--strict` 时 validate/audit-text 的 warn 全部放行。现默认 strict，放宽须显式 `--no-strict`。
- **`--compat v2` 静默关闭 8 类结构检查**：只把 error 降 warn，而退出码依赖 `--strict`，默认非 strict 时降级项完全不影响退出码。现在降级项进独立桶、单独计数、输出标 `(compat 降级)`，并明说「它们是真实缺陷，不是通过项」。
- **`verify-pptx` 不传 `--vs` 时 exit 0**：只出图 + 查备注就报「全部正常」，伪绿。现在未传参照即失败，只需出图请显式 `--no-compare`。
- **`verify-pptx --write-baseline` 先写基线后判红**：一次坏运行会被固化成新基线，之后所有比对都对着错的参照跑。现在判红即拒绝写入。
- **`scaffold.mjs` 用 `claim` 兜底填 `data-notes`**：plan 缺 `notes.cue` 时拿主张冒充讲稿，audit-text 与 verify-pptx 都判「非空」，备注链路永绿。现在只用 `notes.cue`，缺了就留空让它红。
- **`gate.mjs` 版本号硬编码 `3.0.0`**（第六处版本不同步，`examples/gate.json` 连带）。现在读 `scripts/package.json`。
- **规则 12 `GATE` 无独立实现**：唯一发射点是 FORBID 的伴生计数，不是「验证链是否跑过」。现在如实交还 `gate.mjs`，代码里写明职责边界。
- **`rules.json` 四个阈值无人读取**：`occlude.samples/warnHits/errorHits`、`ink.minFillAreaPct` 改了不生效，validate 硬编码 3/6/9。现在 occlude 三项改读 rules.json（采样网格按 `samples` 推导），四项全部纳入 `rules.mjs` 的必填校验，拼错即 exit 2。
- **`compat.v2.downgrade` 从未被读取**（与 `validate.mjs` 的 `COMPAT_CODES` 双真相源）。现在读 rules.json。
- **`selfcheck.mjs` 三处盲区**：RULES_SYNC 只扫 `validate.mjs`（audit-text 的 7 个码永远查不出）、PATH_RE 不认裸文件名、ANIM_SYNC 三重循环恒不报错（第一组遍历自身）。三处已修；扩扫后立刻抓出 audit-text 的 7 个未登记码。

### 修复：一致性

- `rules.json.codes` 登记 audit-text 的 7 个码：`PLACEHOLDER` `DUPLICATE` `SPACING` `PUNCT` `QUOTE` `EMPTY` `TERM`（此前只在脚本里发射，从未登记，而 `references/checklist.md` 又引用它们）。
- 清掉 `rules.json.staleClaims` 里「豁免属性只有四个」的过期断言；SKILL.md 豁免属性从「五个」更正为**六个**（补 `data-safe-ok`），并注明内部属性 `data-structure-ok`。
- SKILL.md「做不到什么」表补「报什么码」列：3 条实际报 `TRANSFORM` 而非 `FORBID`（`translate`/`scale`/`skew`、`transform-origin` 非中心），此前按表查 FORBID 会漏检。
- 参数表补 `--no-strict` / `--no-notes` / `--no-compare` / `--write-baseline` / `--allow-forbid`（后者是全局降级后门，此前未文档化，却被 `build-deck.mjs` 的错误提示主动教给使用者）。
- 参考索引补三行：`references/layouts.md`、`references/visual-system.md`（此前是索引孤儿，rules.json 的 `doc` 字段却指向它们）、`docs/libreoffice-setup.md`（此前完全无引用）。
- `SKILL.md` 裸文件名 `visual-system.md` 改为 `references/visual-system.md`（裸名会绕过 PATH_REF 检查）。
- 版本同步：`SKILL.md` frontmatter / `_meta.json` / `CHANGELOG` / `assets/rules.json` / `scripts/package.json`；`assets/layouts.json` 与 `assets/themes.json` 新增 `skillVersion`；`_meta.json.publishedAt` 与 `metadata.updated` 同步到 2026-10-25。
- `references/troubleshooting.md`、`references/palettes.md`、`references/layout-specs.md` 按新的 rules/themes/layouts 重新生成。

### 修复：检查行为

- `FOOTER` 页脚轮换检查对样张/画廊豁免：画廊是版式目录，本来就要连续展示同类版式，页脚跟着重复是预期行为。

### 验证

```
node scripts/selfcheck.mjs --strict                                         16/16 通过，error 0 warn 0
node scripts/gate.mjs examples/demo-31.html --plan examples/demo-31.json    全绿（含 LibreOffice 真渲染）
node scripts/validate.mjs examples/layout-gallery/deck.html --strict        24 页 0 error 0 warn
node scripts/plan-from-deck.mjs examples/demo-31.html                       12/12 页 layout+role 一致
node scripts/prepare-image.mjs <photo> -o out.png                           四步工序跑通，透明底网点图
node scripts/reorder.mjs <plan> --move 5:2                                  页序正确；越界 exit 1
```

必红用例（证明新门禁会失败）：`verify-pptx` 不传 `--vs` → exit 1；`--write-baseline` 遇差异 → 拒绝写入 exit 1；scaffold 缺 `cue` → `data-notes=""` 触发 NOTES 错误；`--compat v2` → 显式打印「兼容降级 N」；`reorder --drop 99` → exit 1；`prepare-image --radius ≥ --dot/2` → exit 2。

## [3.2.0] — 2026-10-24

交付门禁补强 + 包规范达标。

### 新增

- **讲者备注交付验证**：`verify-pptx.mjs` 现在逐页检查 notesSlide 存在且文本非空——plan 契约要求每页 `notes.purpose/talk` 必填，但此前 PPTX 侧无人验证讲稿是否真的写进了备注页（extract→emit→pptxgenjs 任一环断裂都会静默绿）。样张/特殊 deck 用 `--no-notes` 豁免。实测 demo-31 十二页全非空；构造删备注副本必红（exit 1）。
- **触发回归用例**：新增 `evals/trigger_cases.json`（正 4 / 负 2 / 近邻 3，覆盖中英文风格触发语与"普通商务 PPT/改表格/找模板"近邻边界），接入 skill-creator-cn 词法冒烟评测。

### 修复

- frontmatter：`agent_created` 从顶层未知字段挪入 `metadata` 嵌套（过字段白名单校验）；补 `metadata.version` 与 `updated`——此前版本号只在 `_meta.json`/`CHANGELOG`，frontmatter 无从比对。
- 版本四处同步：frontmatter / `_meta.json` / `assets/rules.json` / `scripts/package.json` 统一 3.2.0。

## [3.1.0] — 2026-10-24

版式扩充 + 图片可选化 + 去"AI 生成味"专项。用户反馈三件事：版式太单一、图可以不加但设计里要有它、AI 味太重。本版全部落地，另修复一批从未被发现的潜在缺陷。

### 新增：版式

- `L17 大圆聚焦 / L18 台阶进程 / L19 拼贴档案 / L20 横向时间轴 / L21 图文对切`（layouts.json 契约 + 手写骨架 + 画廊示例），补齐 case/method/sequence/context 角色的空缺。
- `layouts.md` 新增"镜像方向"节奏指导：`axisDeg` 逐页正负交替，零成本翻转斜线方向。

### 新增：可选图位（缺图有兜底）

- `L02 / L06 / L12 / L16 / L19 / L21` 增加可选 media 槽位；骨架在图位下层放几何兜底（次墨窗 + 圆/楔剪影），缺图时露出"有意的空窗"，配图时整块覆盖、坐标不变。
- `image-prompts.md` 新增"缺图怎么办（几何兜底）"一节；`checklist.md` 新增兜底观感人工检查项。

### 新增：主题

- `theme-press 报纸青墨`（B 子风格第二套，报刊档案向，带颗粒）。
- `theme-c7 炭黑 × 工业绿`（C 子风格，工业/制造/能源向）。
- B 子风格更名"重墨印刷"（靛蓝 / 青墨两套）。

### 修复：主题对比度的潜在 bug（WCAG 全配对复核）

旧主题从未与全部版式组合验证过。逐套计算 fg/bg、pop/bg、pop/fg 后发现并修复：

| 主题 | 缺陷 | 修复 |
|---|---|---|
| `theme-signal` | pop #1E3E86 压在自家墨底上只有 1.91:1，`L16/L03` 墨底页的 `fg-pop` 标题必报 CONTRAST；冷灰白底是"默认 AI 蓝"观感 | 重调为暖纸底 + 印刷蓝 #3464C4（pop/fg 3.25，pop/bg 4.89） |
| `theme-c1` | pop #C9D24B 在纸底 1.36:1，任何带 `fg-pop` 纸底标题的版式必炸 | pop 改焦橙 #C4612F，橄榄黄绿降为 alt；更名"暗紫 × 焦橙" |
| `theme-c2` | fg #1B3FA0 太浅，任何 pop 都无法同时过纸底与墨底两关 | fg 加深至 #122663，pop 微调 #DC4E86 |
| `theme-c3` | pop 芥末黄纸底 2.01:1 | 压深为 #AD7908 |
| `theme-c6` | pop 珊瑚纸底 2.48:1 | 压深为 #D6543F |

### 修复：数据驱动与发布残缺

- `plan.mjs` / `gen-themes.mjs` 不再硬编码主题清单，改读 `themes.json`（单一真相源）——新增主题无需改代码。
- 新增 `scripts/gen-textures.mjs`：确定性生成 `assets/textures/grain.png / halftone.png`。旧发布包里 deck.css 引用的这两个文件根本不存在，A 子风格（强制颗粒）在裸包上渲染必缺层。
- 按文档配方补生成 `assets/img/industry.png`（画廊 L13 示例引用，旧包同样缺失）。
- `scaffold --gallery` 产出挂 `data-structure-ok`：画廊是样张，不是叙事 deck，不判"首 cover 尾 closing"。
- 版本号统一 3.1.0（旧 zip 名为 3.0.0、内含 3.0.1 的不一致一并消除）。

### 修复：去 AI 味文档化

- `visual-system.md` 新增"去 AI 生成味对照表"（症状 → 处方），核心论点：AI 味是"无立场的整齐"，构成主义每条法则都在制造不均。
- `checklist.md` 新增"模板味走查"人工项（同构换字/标题同角/全部端正三问）。

### 验证

```
node scripts/scaffold.mjs --gallery /tmp/gallery-test && \
node scripts/validate.mjs /tmp/gallery-test/deck.html --strict   20 页 0 error 0 warn
node scripts/audit-text.mjs /tmp/gallery-test/deck.html          无占位/重复/空页
node scripts/gen-themes.mjs --check / gen-layout-docs.mjs --check / gen-rules-doc.mjs --check  同步
node scripts/selfcheck.mjs --strict                              16/16
node scripts/gate.mjs demo-31.html --plan demo-31.json           全绿（详见交付报告）
```

## [3.0.1] — 2026-10-21

安全补丁。外部静态扫描指出 `pack-html.mjs` 中出现敏感凭据路径/私钥文件名的字面量。它原本是**拒绝读取**的黑名单，不是读取逻辑；但黑名单字面量会触发误报，防护强度也不如正白名单。现改为正白名单。

### 修复

- `pack-html.mjs` 只内联图片/字体/样式扩展名；其他扩展名、无扩展名文件一律拒绝。
- 路径必须经 `realpathSync` 后仍在围栏内；相对围栏根包含隐藏段的路径拒绝读取。
- 输入必须是存在的 `.html` / `.htm` 普通文件；不再接受其他类型。
- SVG/CSS 文本额外扫密钥特征串；拒绝时不写盘，错误信息不打印文件内容。
- 移除源码/文档中的敏感路径字面量；新增 `SECURITY.md` 说明读取面、打包策略与报告方式。
- 新增 `evals/cases/08-pack-security`：非资源扩展名、隐藏路径、非 HTML 输入、正常 deck 正例。

### 验证

```
node evals/run.mjs --pipeline 08-pack-security     7/7
node scripts/pack-html.mjs examples/structured.html --dry-run   exit 0
node scripts/selfcheck.mjs --strict                16/16
```

交付 zip 仍排除 `scripts/node_modules`、`evals/runs`、baseline 预览图；包内不含密钥或凭据文件。若旧版曾从包含私钥的目录打包过 HTML，建议预防性轮换相关凭据。

## [3.0.0] — 2026-10-21

v3 的主题是**把“输入结构”和“验收结构”变成数据**，同时修掉 v2 里“文档说修了、代码没修”的缺陷。能力层（emit）不做重写，只做列出的针对性修复。

### 新增：结构化生成

- `assets/plan.json` 之外的 `assets/layouts.json`：角色、槽位契约、group 计数、family、页脚/纹理元数据。
- `assets/layouts/L01.html … L16.html`：15 个手写骨架（**L08 并入 L05**），坐标只在 HTML 里。
- `scripts/plan.mjs`：页数/时长、角色顺序、版式轮换、槽位预算、claim 重复、plan↔deck 绑定。
- `scripts/scaffold.mjs`：plan → HTML，确定性填充；同一 plan 两次输出字节一致。
- `scripts/gate.mjs`：doctor → plan → validate → audit → render → build → verify → `gate.json`。
- `references/layout-specs.md`：从 layouts.json + 骨架生成的槽位表与缩略图。
- `examples/plan.json` / `examples/structured.html` / `examples/layout-gallery/`。

### 新增：单一真相源

- `assets/themes.json` → `scripts/gen-themes.mjs` 生成 `deck.css` 主题块与 `palettes.md` 表。
- `scripts/gen-layout-docs.mjs` 生成 `layout-specs.md`。
- `selfcheck` 增加到 16 类不变量：生成文档同步、SKILL 行数、动画白名单三处同步、布局模板 parity。

### 修复：转换器与验证链

| 缺陷 | 位置（改前） | 后果 |
|---|---|---|
| `forbidWarn` 作用域 | `lib/extract.mjs:443-471` vs `:511` | 任何带阴影/渐变/z-index/svg 的页面 build 时抛 `ReferenceError` |
| `wrap` 仍按 `ink.lines` | `lib/extract.mjs:260` | v2 声称已修，实际单行正文仍 `wrap=false` |
| 竖排高度取 `ink.w` | `lib/extract.mjs:311` | `.vlabel` 变成小方块 |
| 内联 SVG 大小写 | `lib/extract.mjs:464` | `tagName === 'SVG'` 对 HTML SVG 永远为假，svg 静默漏检 |
| 旋转元素边框 | `lib/extract.mjs:324-348` | 边框不随元素旋转，PPT 里错位 |
| data URI 图片 | `lib/emit.mjs:93` | pack-html 后的图片被当“不存在”丢掉 |
| build 先写盘后 gate | `build-deck.mjs:160-232` | FORBID 失败仍留下成品 |
| 空 deck / `--slide` 越界 exit 0 | `validate.mjs` | 最危险的假绿 |
| `--mute` 计入四色 | `validate.mjs` | 合法标签色误报 5 色 |
| 安全区 / 遮挡 / 主斜线支配度 | `validate.mjs` | 只有代理指标，1° 小装饰也算主斜线 |
| verify 缺参照图静默跳过 | `verify-*.mjs` | `--vs` 给错目录也 exit 0 |
| `outline.mjs` attrs 硬编码为空 | `outline.mjs:25` | 10 页全部标“缺意图”，仍 exit 0 |

### 新增检查与参数

- 新码：`DECK` / `SAFE` / `OCCLUDE` / `MUTE` / `STRUCTURE` / `LAYOUT` / `SLOTS` / `WIDTH` / `TRANSFORM`。
- `AXIS` 增加支配度、长边、竞争轴；`OVERLAP` 改用 ink 盒；`CONTRAST` 多点采样；`INK` 排除 `--mute`。
- `build-deck --check`：只提取/检查，不写盘；FORBID 在写盘前失败。
- `--compat v2`：新检查降为 warn；`DECK`/`FORBID` 仍 error。
- `verify-render --compare-width/--compare-height`：布局级降采样，避免网点重采样假差异。
- `doctor.mjs`：依赖/Chromium/ImageMagick/poppler/字体/LO 体检。

### 评测

- evals 重组为 `00-converter` / `01-normal` / `02-edge` / `03-negative` / `04-recovery` / `05-delivery` / `06-structure` / `07-trigger`。
- `run.mjs` 支持 `--score`（TRACE 四态）、`--update-baseline`（必须带 reason）、`--repeats`、`--require-complete`。
- 04 不再自动修 fixture：pipeline 只验检测，agent 模式验修复。
- 02 的断言绑定 `data-test`；05 校验“预览数 == 页数”和联系表新鲜度。
- `evals/TRACE.md`：五维定义、三层证据链、人工视觉评分卡。

### 验证记录

```
node scripts/selfcheck.mjs --strict                         16/16，0 error
node scripts/validate.mjs examples/structured.html --strict 10 页 0 error 0 warn
node scripts/audit-text.mjs examples/structured.html --strict 0 占位
node scripts/gate.mjs examples/structured.html --plan examples/plan.json
                                                            gate.json 全绿
verify-pptx                                                 1.31%–3.36%（阈值 4%）
verify-render                                               1.19%–5.52%（阈值 12%）
node evals/run.mjs --pipeline --score                       T/R PASS；A/C/E INCOMPLETE（人工项）
```

### 破坏性/行为变更

- 8 页以上必须有 `plan.json`；短稿可手写，但每页要 `data-role` + `data-layout`。
- 手写样张用 `data-layout="custom"`：跳过槽位检查，也不参与版式轮换统计。
- 旧的 `data-fidelity="image"` 已废弃；用 `"raster"` 或 `--raster-slides`。
- 旧的 1px 线、`#FFFFFF` 反白、半透明叠层、`translate/scale/skew` 会报 error；用 `--compat v2` 逐步迁移。

### 已知残留

- `verify-render` 依赖 LibreOffice 与字体替换；全幅高频网点图仍有重采样差异，示例改用平滑图片。
- 动画 spid 仍按“第 N 个 shape ↔ 第 N 个 sp”；改 `emit.mjs` 后需人工验一次。
- 视觉评分卡的 6 项仍为人工；`--score` 只汇总自动证据，不替代人看联系表。

## [2.0.0] — 2026-10-21

一次**系统性**优化：能力层（HTML → 原生 PPTX 的转换器）不变，契约层全部重建。
起因是同一条规则在 SKILL.md、`references/workflow.md`、`README.md`、`references/checklist.md`
里各写一遍，且四个版本互相矛盾；工具只兑现了其中一部分。

### 破坏性变更（老 deck 需要三步迁移）

1. **`.t-small` 16px → 18px**。卡片正文必须达到正文地板，否则 `FONT` 报 error。
   只改 `.t-small` 的容器宽度，通常不用改内容；如首栏多出一行，删修饰字或把色块改矮。
2. **反白不许写 `#FFFFFF`**，改用 `var(--bg)`。`INK` 现在会做主题成员校验。
3. **1px 线全部作废**，`WEIGHT` 的判定从"恰好 1px"改成"细于 2px"。

### 新增机制

- `assets/rules.json`：阈值、规则码、禁止项、幽灵类的**唯一真相源**。
- `scripts/rules.mjs`：唯一读取入口；找不到直接退出码 2，绝不用默认值兜底。
- `scripts/gen-rules-doc.mjs`：把规则表渲染进 SKILL.md 与 `references/troubleshooting.md`
  的标记块。**规则表只有这两处，且不是手写的。**
- `scripts/selfcheck.mjs`：13 类不变量静态自检（幽灵类 / 幽灵变量 / 死路径 /
  脚本不认的参数 / 过期陈述 / 手写计数 / 生成块不同步 / 字号表与 CSS 不一致…）。
  改过文档之后必跑。
- `evals/`：五个任务包（正常 / 边界 / 负面触发 / 失败恢复 / 交付验收）+ 可复现基线。
- `references/start-here.md`：第一页最小知识集，不必先读 1800 行。
- `references/troubleshooting.md`：18 个规则码的判定与修法（表格由生成器产出）。
- `references/animation.md`：动画实现细节从 SKILL.md 下沉，改转换器的人才读。

### 修掉的缺陷

| 缺陷 | 位置（改前） | 后果 |
|---|---|---|
| `.sun--outline` 编译成方框 | `lib/extract.mjs:440` | 成品肉眼可见多一个正方形描边（示例 P4 已中招） |
| `.t-h2` 缺 `white-space:nowrap` | `assets/deck.css:92` | 64px 标题会静默折行，而 SKILL 声称已内置 |
| 单行正文输出 `wrap=false` | `lib/extract.mjs:260` | 用户在 PPT 里加字不会重排，直接越过栏宽 |
| 12 条规则 ↔ 14 个码不对应 | `SKILL.md` vs `validate.mjs` | 规则 5、11 从未被执行 |
| 7 类禁止项静默丢弃 | `SKILL.md:34` 措辞失实 | 混合模式 / z-index / fixed / 伪元素 / svg / 嵌套旋转 / 裁切，成品会残但不报警 |
| `--strict`、`--sheet` 失败静默 | `validate.mjs`、`render.mjs` | 自动化验收拿到退出码 0 |
| `data-fidelity="image"` 悬空 | `build-deck.mjs:12` | 注释承诺了一个不存在的开关 |
| 幽灵类 `.quote-mark` / `.rule--hair` / `rect--pale`、幽灵变量 `--pale` | 3 份 references + `deck.css:6` 注释 | 照文档写立刻报错或静默塌版 |
| 示例用了 4 套主题 | `examples/constructivism.html` | few-shot 会学到违规做法；现以 `data-showcase` 显式豁免并说明这是样张 |
| checklist 编号重复、计数虚报 | `references/checklist.md` | agent 会漏检 4 项 |

### 阈值统一（以设计意图为准）

| 项 | v1 | v2 |
|---|---|---|
| 面积不均 | 1.12（warn，top1/top3） | 1.7（error，top1/top2）；骨架配方 1.9fr |
| 正文字号 | 15px warn | 18px error；标签 15px；微字 13px 且只做装饰 |
| 色数 | 4 色但不含纸底（有效 5 色） | 4 色含纸 + 主题成员校验 |
| 线重 | 判"恰好 1px" | 判"细于 2px" |
| 页脚 | 只靠人工 | `FOOTER` warn |
| 展示字折行 | 无实现 | `WRAP` error |

### 结构

`references/workflow.md` 删除（过期的第二真相源）；`prior-art.md` 与
`libreoffice-setup.md` 移入 `docs/`（不属"写页面要读"）；SKILL.md 252 → 242 行，
但制造者细节全部下沉，实际执行上下文减少约四成；`examples/preview/` 补齐为 10 页 + 联系表。

### 验证记录

改前：`validate` 0 error / 0 warn（但含未实现的规则、P4 方框缺陷）。
改后：

```
node scripts/selfcheck.mjs                                  12/13 通过，0 error
node scripts/validate.mjs examples/constructivism.html       10 页  错误 0  提示 0
node scripts/audit-text.mjs examples/constructivism.html     无占位/重复/空页
node scripts/build-deck.mjs examples/… -o deck.pptx          exit 0，无 FORBID
node scripts/verify-pptx.mjs …                               10 页 1.46%–3.44%（阈值 4%）
node scripts/verify-render.mjs …                             10 页 3.45%–5.85%（阈值 12%）
```

P4 细矩形由 5 条（方框）降到 1 条；P05 单行正文由 3 个可重排文本框增到 4 个。
