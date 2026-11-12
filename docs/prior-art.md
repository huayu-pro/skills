# 这套 skill 从哪些方案借了什么

> 状态：已冻结。这里是**开发史与出处**，不是每次执行都要读的内容。
  文中标 `[已过期]` 的结论已被后续实现推翻，保留只为说明为什么走了这条路。

# 这套 skill 从哪来

工作区里躺了七套 PPT skill。逐套读过之后，结论是**没有一套能直接改**——要么依赖不存在的服务，要么输出的东西不可编辑。但每一套都有值得抄的结构。

记在这里，方便以后维护时知道自己承了什么债。

---

## 逐套评估

### guizang-ppt-skill（43KB，单文件 HTML deck）

**做法**：一份 HTML 装完整份 deck，WebGL 背景 + 横向翻页 + 演讲者模式 + 观众屏同步。CSS 类库 + `layouts.md` 骨架表 + `themes.md` 主题表。强制"写页之前先读完模板的 `<style>`"。

**借了什么**
- 双层结构：`SKILL.md` 只做路由和纪律，规范全部下沉到 `references/`。本 skill 的references 已按"写页面要读"与"开发史"分层，后者移到 docs/ 就是这个结构。
- **类名预检**：它明确要求"用之前先确认类在模板里存在"。本 skill 用更硬的方式解决——`deck.css` 是单一来源，`html-contract.md` 列全了允许的类。
- 一 deck 一主题不许换色的硬规则。
- 七问澄清清单。本 skill 砍到四个（只留真正影响版式的）。

**没借**
- 不做网页交付：没有翻页、没有演讲者模式、没有 WebGL。那是它的地盘。
- 类名体系太细（`grid-2-7-5`、`span-N` 之类），学起来成本高于收益。

### ppt-master v6.7.2（22MB）

**做法**：路由 → 工作流 → 执行器的三层结构，SVG 页面编译成原生 PPTX。有完整的 Plan → Do·Check·Act 阶段门和阻塞点。

**借了什么**
- 阶段门与"阻塞就是停"的纪律。
- **"在拥有该错误的层修复"**：页面错就改页面，规格错就改规格，不要在下游绕过。本 skill 的 `rerender.mjs` 就是这个原则的工具化——提取错了就去修提取，不许用截图糊过去。
- `semantic-svg` 的思路：结构先于视觉。

**没借**：22MB 的脚本和 98KB 的 SVG 规范。它解决的是"从零编译任意 SVG"，本 skill 只需要一个受约束的子集。

### pptx-skill（Anthropic 系，pptxgenjs 直写）

**做法**：一个 SKILL.md 加一堆脚本，核心是一份"踩坑清单"——每条一句话，只说后果和修法。

**借了什么**
- **踩坑清单的文体**：不写"注意对齐"，写"`margin:0` 会被 falsy 判断吞掉，文字整体右下移 7.2pt"。本 skill 的 `html-contract.md` 第五节整节都是这个写法。
- 三色角色模型（BACKGROUND / PRIMARY / ACCENT）。
- QA 分三级：内容 / 文件 / 视觉。

**没借**：它的"避免 AI 味"清单（禁止色条、禁止装饰线、避免米色背景）**与构成主义直接冲突**。这些规则是为了让通用 PPT 不显得像模板，但色带和满幅色块在这套语言里是结构本身。本 skill 在 `SKILL.md` 末尾显式豁免了它们。

### pptx-skill-2026-10-20（Z.AI，54KB 纯规范）

**做法**：不写代码，只写设计规范。配色、密度、字体、图表、CJK 处理。

**借了什么**
- **CJK 字体章节**：哪些字体目标机器一定有（微软雅黑 / 苹方），哪些只在本机有（Noto Sans SC / 思源黑体），避免 Light 字重。本 skill 的 `--font-profile` 直接来自这一节的教训。
- "字号阶梯绑定 13.33″ 画布"的写法。

**没借**：同样是反 AI 味规则（避免 cream 背景、避免卡片网格），与构成主义冲突。

### ppt-skill（Qoder Office，MCP 工具链）

**做法**：`begin_deck` → `set_plan` → 逐页 `put_page` → `check_deck` → `save_document`。

**借了什么**
- **PageSpec 的结构化页面描述**：把一页拆成结构化的形状/文字/图片数组，而不是直接写渲染代码。本 skill 的 `deck-spec.json` 就是这个思路——先出规格，再出渲染。
- "先 set_plan 持久化大纲，再逐页落地"的顺序。

**没借**：依赖特定 MCP 工具，本机没有。

### ppt-skill2（飞书 Slides，lark-cli + XML）

**做法**：逐页写 XML → 服务端 lint → 通过才写下一页。有严格的"三种完成状态"区分（已落本地 / 已写入 / 已通过校验）。

**借了什么**
- **逐页闭环**：每页校验通过再下一页，不攒着。本 skill 的"每写完一页跑一次 render"来自这里。
- 状态区分：写了 ≠ 对了。本 skill 里对应"build 成功 ≠ 打开好看"。

**没借**：依赖飞书服务。

### jingmei-ppt（只做视觉总监）

**做法**：不产出文件，只给审美判断和设计系统：风格简报 → 配方 → 渲染验证。

**借了什么**
- **风格简报的字段**：三个形容词 / 一个设计张力 / 密度 / 配色逻辑 / 字体逻辑 / 图片行为 / 空间节奏。本 skill 的第 2 步直接用它。
- "配方是提示，不是牢笼"：骨架可以破，前提是知道为什么。

**没借**：它不落地。本 skill 必须端到端出文件。

### lieflat-charts（图表与报告）

**做法**：模板驱动的图表库，强制从 gallery 里选型而不是自由发挥。

**借了什么**
- **"先锁模板再组织内容"**的顺序：不要先想好一页要讲六件事再找版式，先选骨架再填。
- 数据图的诚实性约束（不编数字、缺数据要标注）。

**没借**：它的图表体系与构成主义视觉冲突（细网格、渐变、图例）。本 skill 在 `layouts.md` 的 L11 里明确说"只用条形和数字，不用原生图表"。

---

## 承下来的债

1. **[已解决 2026-10] 没有 PPTX 渲染器**。`scripts/verify-render.mjs` 用 LibreOffice 完成了真渲染验收（阈值 12%，LO 的字体替换带来的系统性偏差要人工判读）。此前的缓解手段 `rerender.mjs` 仍保留，用于"提取是否忠实"这一层。
2. **文本基线靠推理，不是靠实测**。CSS 的 line-height 与 OOXML 的 `lnSpc` 对首行基线的锚定方式没有权威文档，本 skill 用"单行取自然行高、多行取 CSS 行高"来规避分歧，但 1–3px 的误差可能存在。
3. **custGeom 是 pptxgenjs 4.x 的新特性**。在 WPS 或较老的 PowerPoint 上可能渲染异常。降级方案（三角形拼接）没实现。
4. **不支持容器裁切**。"标题被色块咬掉一角"这个构成主义招牌手法只能近似。


---

## 2026-10 审计后：看过但没采用的做法

这一轮把七套 skill 又过了一遍，逐条评估后**决定不做**的：

| 做法 | 出处 | 为什么不做 |
|---|---|---|
| 风格的可视化确认页（起本地服务给缩略图点选） | ppt-master `confirm_ui` | 收益真实，但要维护一个 web server + 生命周期，对"一次生成 10 页"的场景太重。用文字描述三套风格 + 示例图足够 |
| 动画 / Morph 配置（scaffold / list-groups / validate） | ppt-master `animation_config.py` | 构成主义确实适合"斜带先入、字后压"，但 pptx 动画在 WPS/Keynote 上表现不稳。等有真实需求再做，别先造一个没人调的配置层 |
| 图表的原生对象校验 | ppt-master `verify-charts` | 本 skill 的 L11 明确不用原生图表（默认主题会破坏配色）。没有对象可校 |
| 结构化演讲备注（purpose / talk[] / transition / minutes） | guizang `presenter-mode.md` | 概念好，但要求作者写 7 个字段，实际会退化成"填两行"。暂时只保留 `data-notes` 自由文本 |
| 大纲持久化成 `outline.json` 再逐页生成 | ppt-skill `set_plan` | 对 20 页以上的长稿有价值；10 页以内的稿子，直接在 HTML 里改更快。等支持 30 页时再加 |
| 逐页 lint 闭环（`--slide N`） | ppt-skill2 | **已实现**。但只在长稿里有用，短稿跑全量更省事 |
| 同层并列必须等宽均分 | ppt-skill2 通用规则 §8 | **明确拒绝**——与构成主义直接冲突。已写进 `visual-system.md` 的"冲突"一节 |
| 禁止色条 / 满幅色块 / 米色背景 | pptx-skill、pptx-skill-2026-10-20 | **明确拒绝**，同上 |

### 已经落地的

- 联系表（`render.mjs --sheet`）← pptx-skill `thumbnail.py`
- 内容体检（`audit-text.mjs`）← pptx-skill 的 markitdown + grep
- 类名预检（`validate.mjs` 的 `CLASS`）← guizang `validate-swiss-deck.mjs`
- 分级修法文案（每条 error 后面跟一句"该怎么改"）← guizang `overflowFix()`
- 逐页模式（`--slide N`）← ppt-skill2 的逐页闭环

---

## 2026-10 第二轮：外部项目调研

按环节扫了 GitHub / SkillHub / ClawHub / WorkBuddy 市场，记下看过的东西。

| 项目 | 在哪一环 | 结论 |
|---|---|---|
| **kwikwag/svg-to-drawingml** | 编译 | SVG path → `a:custGeom`，弧线转贝塞尔、transform 烘焙进坐标。**印证我们 custGeom 路线正确**；其 path 命令覆盖可作"WPS 不认曲线时退化为折线"的参考 |
| **svg2ooxml**（PyPI） | 编译 / 校验 | SMIL 动画 → PowerPoint timing，说明动画 XML 可编程生成；配套 `openxml-audit` 用"受控样本 + 差异证据"做回归 → **采纳为基线比对** |
| **BramAlkema/svg2pptx** | 校验 | PIL 视觉比对 + diff/heatmap → **采纳思路**，自己用 canvas 实现 |
| **slidevjs/slidev** | 预览导出 | **上一版写错了。** 读到源码：`packages/slidev/node/commands/pptx/` 下是 `capture → walker → ir → normalize → build` 的完整原生管线，不是截图贴图。它的 `walker.ts` 与我们的 `extract.mjs` 同构（递归 DOM + `getComputedStyle` + `Range.getClientRects()`）。已抄其字体探针与"零尺寸盒子不剪枝" |
| **pandoc `-t pptx`** | 大纲→版式 | 仅 README 级，未核实源码。据文档是把结构映射到 PowerPoint 版式，与我们的绝对定位冲突，不采纳 |
| **Satori** | 字→路径 | 仅 README 级，未核实源码。能做"不依赖字体的矢量标题"，但工程量大，现有 raster 方案够用，暂不采纳 |
| **SkillHub `spellbook-slides`** | 版式 | 6 主题 × 4 页面类型 + **视觉四层结构** → 采纳四层模型写进 `visual-system.md` |
| **SkillHub `presentation-architect`** | 大纲 | 每页九要素清单 → 裁成五项做 `outline.mjs` |
| **Marketplace `ppt-generator`** | 版式 | 11 种标准版式，与我们 这些骨架互补，未逐条吸收 |
| **Marketplace `cyber-ppt`** | 大纲 | SCR 叙事 + 证据溯源。溯源部分我们只在 checklist 里写了"数字要有来源"，没做工具 |
| **textlint `ja-space-between-half-and-full-width`** | 校验 | 中英之间空格规则 → 采纳进 `audit-text.mjs` 的 `SPACING` |
| **Tech-Doc-Style-Chinese** | 校验 | 中文标点、直角引号规范 → 采纳为 `PUNCT` / `QUOTE` |
| **html-plan `pack.mjs`** | 交付 | CSS/图片内联成单文件 → 采纳为 `pack-html.mjs` |
| **KitchenSink4PPT** | 交付 | `export_slide_image` 让 agent 看到产出再修。我们用 `verify-pptx.mjs` 做了更强的版本（读 XML 而不是读图） |

**没做成的**：本机装了 WPS（`/usr/bin/wpp`）但没有 CLI 转换入口，又没有 sudo 装 LibreOffice，所以 **pptx 仍然不能直接渲成图**。`verify-pptx.mjs` 是绕过去的办法：它验证的是"我们写进 pptx 的几何"，不是"PowerPoint 渲染出来的样子"。

---

## 2026-10 第三轮：读源码后的修正

前两轮的判断有一部分是读 README 得出的。这一轮直读源码（GitHub API tree + raw 文件，不 clone），推翻了三条。

### 读到的文件

| 项目 | 文件 | 结论 |
|---|---|---|
| **BramAlkema/pptx-animation-skill** | `oracle/entr/filter_effect.xml`、`oracle/filter_vocabulary.xml`、`scripts/emit_entrance.py`、`scripts/validate.py`、`README.md` | 实证过的动画 XML 模板 + 死路清单 |
| **kwikwag/svg-to-drawingml** | `src/emit.ts` 全文 | custGeom 的坐标/文本约定 |
| **slidevjs/slidev** | `commands/pptx/` 目录 + `walker.ts` 全文 | 原生管线，非截图 |
| **anthropics/skills** | `skills/pptx/scripts/` 目录 | **没有 html2pptx**，只有 pptxgenjs 路线 + OOXML 编辑工具 |
| **html-plan** | `runtime/pack.mjs` | 打包器的读取围栏与密钥扫描 |

### 动画：五条修正

1. 入场必须有 `<p:set style.visibility="visible">` 作前置，否则 `animEffect` 没有过渡起点——**这条不做，动画等于没写**。
2. `fade` 的 `presetID` 是 **9**（10 是 dissolve）。
3. `wipe(up)` 的 `presetSubtype` 是 **1**（4 是 wipe(down)）。
4. preset 元数据挂在 `par` 自己的 `cTn` 上，不要多套两层。
5. 必须带 `grpId`，否则效果面板认不出预设。

### 七条死路（解析通过、播放静默丢弃）

`p:anim` 打在 `fill.opacity` / `stroke.opacity` / `stroke.weight` / `line.weight` / 带 `tavLst` 的 `style.opacity` 上全部无效；`style.fontSize` 单独用也不触发，必须凑齐 preset 28 的复合体。**结论：不要试图用 `p:anim` 做透明度或线宽动画。**

### custGeom：我们是对的

`svg-to-drawingml` 用 `emu(v) - e.x` 把点算成相对形状盒的 EMU，`path w/h` = 形状 extent，`bodyPr` 与我们逐字一致。差异只有两处，而且都是我们更好：它把旋转烘焙进坐标（不可再编辑），我们用 `rot` 属性；它用"字符数 × 0.6em"估文本宽度，我们实测 ink 盒。

### 从 html-plan 抄的打包围栏

它的 `pack.mjs` 在读任何文件前做三件事：`realpathSync` 解析符号链接后判断是否在 `--root` 内、只允许资源类扩展名并拒绝隐藏路径段、对文本内容扫密钥特征串。任何一条不过就**不写盘**。我们的 `pack-html.mjs` 原来会把任何被引用路径直接 base64 进去——这是真实的安全缺口，已照抄。

---

## 2026-10 v2 系统性优化时新增的参考来源

| 来源 | 借了什么 |
|---|---|
| SkillHub TRACE 严选框架（T/R/A/C/E） | 用五维给改动归因；"no-skill 对照 + 证据包审计"的思路落到 `evals/`；E 维度要求把 token/耗时代价一并考虑，SKILL.md 因此加了交付 gate 与"没跑完不算交付" |
| skill-refinement（niits/ds-skills） | 提案/实施两阶段分离；findings 必须带 `path:line`、行为影响、最小修法与验证方式；severity 只挂可观察行为 |
| Skill Forge（ClawHub cjg-skill-forge） | 导航式 SKILL.md（只留路由+红线+锚点）；"删掉这段 agent 照样能干 → 它不该在技能里" |
| skill-official-evaluation / reviewing-skills（Anthropic 最佳实践衍生） | SKILL.md <500 行、reference 一层深、degrees of freedom 与任务脆弱度匹配、必须有 validate→fix→repeat 反馈环 |
| Anthropic Agent Skills 渐进式披露 | 启动只加载 name+description；按需读 references；新增 `references/start-here.md` 降低首读成本 |

## v2 引入的新机制

- `assets/rules.json`：阈值、规则码、禁止项、幽灵类的唯一真相源。
- `scripts/rules.mjs`：唯一读取入口，缺文件直接退出码 2，不允许静默默认值。
- `scripts/gen-rules-doc.mjs`：把规则表渲染进 SKILL.md 的标记块，`--check` 供自检调用。
- `scripts/selfcheck.mjs`：文档↔代码↔资产一致性自检，抓幽灵类、幽灵变量、过期陈述、手写计数与阈值。
- `evals/`：五个任务包（正常/边界/负面/恢复/交付），可复现的改前/改后对照。
