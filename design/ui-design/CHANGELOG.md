# CHANGELOG

## 5.0.0 — 2026-11-12

从「可 lint 的合规」升级到「有手感、得体、可拆装」：Web UI 核心 + 可选 packs。

**核心**
- `SKILL.md` 456 → 路由版；新增 `subskills/direction|tokens|motion|audit` 与 `build_skills.py`。
- 新增 `references/28-motion-system.md`：dt-based 模型、ζ/ω 弹簧、motion token/register、
  attention/ambient/feedback 预算、casting、native-first、可打断、reduced identity。
- 新增 `references/29-cjk-mobile.md` 与五类 surface profile 加权 rubric；appropriate 高于 distinctive。
- 新增 utility golden `assets/golden/ledger.html`：0 attention/0 ambient、120–180ms feedback、空/错/载/键盘完整。
- `check_motion.py` 增至 M-001..M-016（12/12 self-test），旧 17 组件 grandfather。
- `verify_motion.mjs` 支持 `--url/--trace` 与 motionBudget；`detect_stack.mjs` 探测真实项目。
- `emit_tokens.py` 支持 `--motion-profile`；token 模板新增 motion primitives/semantic。
- compliance / quality / appropriateness 三层报告；`accepted` 不能由脚本单独给。

**可选 packs（用户点名才加载）**
- apple-motion (MIT)、apple-liquid-glass (MIT+ISC+MIT)、html-deliverables (MIT)、
  design-md (MIT)、refactoring-ui (MIT 原创部分)、code-animation-prompts (自定义许可)、
  remotion (Remotion License 外部依赖)。
- 排除 guizang-ppt-skill (AGPL-3.0)；不 vendor ppt-master/open-design 的大仓库。
- `NOTICE` / `ATTRIBUTION.md` 增加逐项来源、许可门槛与商业交付清单。
- 新增 `score_rubric.py` 与 `evals/reports/v5-evidence.json`；ledger 375/audit/utility rubric、
  三页 golden 复评、Apple pack 1280/375、HTML sample/dry-run、Refactoring UI 覆盖报告均留证。

**边界**
- 普通页面不加载 packs；Stack 降级为 references/18 可选分支。
- 200 源文件 / 无二进制上限：7 个 pack 压成单 SKILL（Apple/HTML 各保留一个文本样例），
  5 个 merged 演示移出（git 历史可查），4 张 golden PNG 不随包；验证读数保留在
  `evals/reports/v5-evidence.json`。
- 图里的质量判断仍是人工/LLM 评审；脚本只提供证据，不声称「证明好看」。

## 4.5.1 — 2026-11-12

包体压缩，内容不删：354 → 195 文件（≤200）。

- `assets/brands/` 84 份 DESIGN.md → `assets/brands.json`（`content` 字段保留全文）。
- `assets/patterns/` 14 张 arch 卡 + techniques/deep → `patterns.md` + `archetypes.json` + `methods.json`；`query_corpus.py --id` 从 ARCH 标记取卡。
- `assets/site-techniques/` 28 HTML → `site-techniques.html`（左侧列表 + iframe srcdoc）。
- `assets/site-studies/` 8 HTML → `site-studies.html`（同一 viewer 模式）。
- `assets/motion/prompts/` 10 MD → `prompts.md`；`code/snippets/` 8 JS → `snippets.js`。
- golden 10 PNG → 3 桌面 PNG；保留 3 个 HTML。
- `check_assets.py` 支持合并后的结构；`query_corpus.py` 支持 brands.json / patterns.md / anchor path。
- 验证：check_assets 0/0；check_motion 13/13 + evals 6/6；audit 35/35；17 组件 5 文件契约不变。

## 4.5.0 — 2026-11-12

R5（整包对抗审查）修复，最终交付。

**P1**
- `SELF-CHECK.md` 重写为 4.5.0：457 行 SKILL、44/44 触发、2 个组件 P2 / 8 个
  shipped HTML P2、19 个原站引擎未打包、5 轮报告与 TRACE-REPORT 指针。
- `assets/golden/studio.html` 45 个死链修复：`../SKILL.md`、`09-motion-principles.md`、
  `23-motion-cases.md`、`../motion/code/components/<id>/index.html`；「12 families」
  改「12 mechanisms」。
- 许可边界：新增 `NOTICE`；SKILL `license` 改混合许可；ATTRIBUTION 加
  VoltAgent/refactoring-ui 版权与「OPL 派生不重新授权」。
- Mantine 122+82 删除；HeroUI 73 与表内 79 个名称对账（删重复 Select）。
- `check_assets.py` 去掉源码里的绝对路径/OPL 字面量与自豁免；新增 SELF-CHECK
  版本检查。

**P2**
- workflow cases F-1/F-2 → G-1/G-2；README 覆盖 A/B/E/G。
- CHANGELOG 4.0.0 的 28 demo → 26+2。
- `query_corpus.py --stats` 标「目录 550 / 抽取 412」。
- `assets/patterns/deep.md` 与 `techniques.md` 在 `14-pattern-library.md` 建索引。
- 12 个组件 meta `schema_version` 统一为 `ui-design/motion-component@1`。

**交付**
- 354 文件 / 7.3 MB；`ui-design-4.5.0.zip` + sha256。

## 4.4.0 — 2026-11-12

R4（三库路由）修复，来自 CLI/已安装技能/registry 的实测核对。

**实测版本（2026-11-12）**
- `@heroui/react` **3.2.7**、`@heroui/react-mcp` **1.1.4**、`@heroui/styles` 3.2.7。
- `@mantine/core` **9.8.0**、`@mantine/mcp-server` **9.8.0**。
- `shadcn` **4.23.0**。

**修正**
- shadcn 命令：删掉不存在的 `add --preset <code>`；改为
  `init --preset <code>`（新项目）/ `apply <code>`（已有项目）；补 `view`、
  `add --diff`、`info --json`、`docs <components>`。
- HeroUI 组件数：87 → **73**（`list_components.mjs` 实测 v3.2.7）；
  保留 no Provider / compound / onPress / Tailwind v4 / `@heroui/styles` / oklch。
- Mantine 版本 9.7.5 → **9.8.0**；包数/组件数改为“以 `list_items` 为准”，
  不再写死 122 + 82。
- `heroui-migration` 未装在 `~/.zcode/skills`：补“若未安装，按 16 的 v2→v3 表手工迁移”。
- 三库矩阵的组件数改为 registry/list 口径，避免版本腐化。

**验证**
- `npx shadcn@latest --help / add --help / apply --help / view --help / info --help`
  全部通过；`docs <components>` 存在。
- `node scripts/list_components.mjs` → 73 components (v3.2.7)；
  `get_component_docs.mjs Button`、`get_theme.mjs` 正常返回。
- `npm view` 四个包版本与上表一致。
- 仍未建真实 React 项目跑 runtime；标注 docs-verified。

## 4.3.0 — 2026-11-12

R3（动效验收）修复，来自独立动效对抗审查。

**P1**
- `verify_motion.mjs`：不再用绝对 `frames>0` 或任意 duration>0 判定运动；
  必须 `frameDelta>0 || animationDelta>0 || statsChanged`，且加载时的动画必须
  `playState === "running"`。假 stats / paused 动画现在 FAIL。
- reduced 模式：任何 running 且 duration>0 的动画都算失败（不再只看 infinite）。
- `check_motion.py`：`transition:` 纳入 M-002；query-string 与 `@import` CSS 会被跟随；
  JS 直接写布局属性改为人工复核项，WAAPI `.animate([{width…}])` 仍自动检测。
- 12 个 kit 中的 10 个补上 `prefers-reduced-motion` reset；kit 09 改 `scaleY`、
  kit 08 改 `translate3d`、kit 01/02 进度条改 `scaleX`、kit 06 ring 改 `scale`、
  kit 10 pin 改 CSS 变量；component 10 进度条改 `scaleX`；component 06 补 reduce 块。

**P2**
- `24-motion-verification.md` 改成**实际实现**：1280/768/375、交互探针、reduced
  双采样、schema 字段；未自动化的 Esc/手势/WebGL/meta 对账列为人工项。
- 17 个 README 的 verifier 路径改为 `../../../../../scripts/...`；5 个 merged
  README 的 `verified: false` 改为 true。
- 元数据：01 删除不存在的 reveal 参数；12 改 `1400ms / mixed`；17 改 `trigger: pointer`。
- `PARAMETERS.md`：cursor ring `.16`、dot 直接设置、audio fftSize `256（128 bins）`、
  bar mapping 修正、rAF dt cap 出处 §2.1。
- `INDEX.md` kit 02 摘要改为「边界 clamp」；`09` 的 F11 canonical 改为 component 04。
- `check_motion` M-007 识别 pause/hidden；M-009 只在 `pointer:fine` 块内包含
  `cursor:none` 时放行。

**证据**
- 12/12 运行时通过（1280/768/375；strict reduced）；假 stats、paused、query-string、
  `@import`、comment-only reduce 全部按预期失败或命中。
- 所有 shipped HTML 0 P1；`check_motion --self-test` 13/13；`--expect` 6/6。

## 4.2.0 — 2026-11-12

R2（审美高度）修复，来自同题 RED/GREEN 盲评。

**新增规则**
- `01`：材质取色（反奶油默认）；首屏必须是题材最有特征的东西；**图表不是英雄**
  （全屏灰色图表会变仪表盘，首屏需要排版陈述 + 人性细节 + 图表支撑）；
  字体试衣（标题至少三种处理）；390 微尺度五项；注意瞬间必须在首屏可见/可感知。
- `SKILL.md` B.3：动效证据要求两帧（起点/终点）或 3s 录屏；390 五项。
- `12-audit-rubric.md`：动效证据、390 微尺度加入镜 7。
- `24-motion-verification.md`：人工复核必须有两帧/录屏，否则 `skipped`。
- `25-golden-pages.md`：补「图表/示意图不独占首屏」。

**盲评证据**
- Acoustic：GREEN 4.6 vs RED 4.1（+0.5）。
- Journal：GREEN 4.4 vs RED 4.1（+0.3）。
- 反例：把 journal 首屏改成整屏高程图后，盲评 3.4（低于 RED 4.1）——
  证明「图表不是英雄」，该版本被拒绝，规则写回。

## 4.1.0 — 2026-11-12

R1（结构/可靠性）修复，来自对抗审查的实证问题。

**P0**
- `verify_motion.mjs` 不再给「没有运动」的页面写 `verified: true`：加入交互探针
  （wheel/drag/scroll/click/keyboard）、帧/动画/状态变化判定、body visibility/opacity
  检查、reduced 模式双采样、reduced 页 console 监听、favicon 204、空目录 exit 2。

**P1**
- `check_motion.py`：P1 现在返回非零；目标不存在/无 HTML 返回 2；reduced-motion
  必须有真正禁用动画的块（注释不算）；跟随 `@import` 与 query-string CSS。
- `check_assets.py`：motion index 的每个 path 必须存在；组件/merged 目录与索引双向
  一致；`meta.motion.verified` 必须为 true；运行时 JS/CSS 的外部 URL 与 `.py/.mjs`
  的工作区绝对路径都会报错。
- 触发负例去掉裸 `"video"`，改为 `video editing/production/render/mp4`；新增
  video-collage 正例；44/44 通过。
- 文档对账：12 个组件的算术、26 demo + 2 索引、studio 截图范围、eval F→G、
  6 个品牌用例、`mkdir -p`、`--kind components`、`15-beyond-the-book`、
  brand 文档里的上游 helper、site-studies manifest。

**P2**
- `audit.py` 新增 `--fail-on-p0`（CI 用）与 `--out` 父目录自动创建。
- `check_contrast.py` 支持 rgb()/rgba() 并做 alpha 合成；文件缺失/JSON 错误给一行错误。
- `generate_palette.py` / `emit_tokens.py` / `query_corpus.py` 的坏输入改为一行错误。
- `check_motion.py` 的 M-012 不再误报 canonical reduced-motion reset。

## 4.0.0 — 2026-11-12

初始 4.x 交付。

**审美层**
- 新增 `01-aesthetic-direction.md`：物性优先六步、四个杠杆、7 维 rubric、反默认指纹。
- 3 个 golden 页：aperture（编辑型技术产品）、atelier-north（建筑图纸）、studio（12 机制）。
- 84 个品牌 DESIGN.md + 索引；14 张原型卡（去 URL）。
- 8 个站点研究（一份内容 × 六种设计语言）；26 个 CSS 手法 demo + 2 个索引页。

**动效层**
- 全量盘点 1,310 份逆向代码文件；870 个唯一哈希；1,537 个唯一 keyframes（351 个库默认）。
- 12 个机制 kit + 12 个复合组件 + 5 个补缺 merged；其中 **12 个组件**（12 复合 + 5 merged）可运行并已验证。
- 24 条 canonical keyframes；8 个原语 snippet；10 份强提示词；30 案实测索引。
- 12/12 组件运行时通过（console 0、375 无溢出、reduced-motion 无无限动画）。
- 6/6 动效夹具通过；`check_motion.py --self-test` 13/13。
- 修复 golden 页与 09-cursor-field 的布局属性过渡/重复 reveal。

**规则层**
- 02–21 章沿用 v2 的成熟规则并更新引用；新增 00/09/22/23/24/25/26/27。
- 三组件库路由：shadcn/ui、HeroUI v3、Mantine 9.x；MCP + 离线回退。
- 8/8 审计金标准（带 `--brand`；不带 7/8）；`audit.py --self-test` 35/35。
- 新增 `check_assets.py` 资产/索引/URL/版本一致性门禁。

**边界**
- 不打包 302 复刻/截图/报告、4,055 组件语料、57 结构来源、19 原站引擎。
- 不安装全局、不改 MCP 配置。