---
name: ui-design
description: >-
  设计、构建、改造、评审专业网站 UI，以审美高度为第一标准：题材扎根、一个物理关系、
  排版人格、构图张力、克制、完成度、动效编排。用于新页面/落地页/作品集/产品页/设置页/
  表单/导航/定价/空状态，设计系统与 tokens，配色/字体/间距/深度，动效与交互手感，
  无障碍与文案，上线前审计，组件库选型与写法（shadcn/ui、HeroUI v3、Mantine 9）。
  Use when the user asks for a page, screen, landing page, layout, section, hero, nav,
  pricing block, form, modal, table, card, empty state, design system, design tokens,
  responsive behavior, accessibility review, motion pattern, or says 页面设计, 网站设计,
  界面设计, UI 设计, 样式调整, UI 太丑, 看起来像模板, 设计评审, 视觉层级, 配色,
  对比度, 间距, 排版, 阴影, 空状态, 设计规范, 设计系统, 组件库选型, 找组件, 组件检索,
  无障碍, 动效, 动画, 太花, 太土, 没质感. Exclude backend logic, data modelling,
  copy editing with no visual surface, native mobile apps, and video production.
license: "Mixed: MIT for original code; third-party and OPL-derived assets are not relicensed — see LICENSE, NOTICE, ATTRIBUTION.md"
metadata:
  version: "4.5.1"
  author: workspace
  category: design
  updated: "2026-11-12"
---

# UI Design 4.x

## 这是什么

一个把「网站是否好看」变成**可指认、可实现、可验收**的技能。四层，按需加载：

| 层 | 作用 | 位置 |
|---|---|---|
| **审美层** | 决定长什么样：题材扎根、物理关系、排版人格、构图、克制 | `01`、`assets/patterns/`、`assets/brands.json`、`assets/golden/` |
| **规则层** | 必须遵守什么，违规怎么诊断 | `02`–`08`、`10`–`13` |
| **动效层** | 动效为什么存在、怎么实现、怎么验 | `09`、`22`、`23`、`24`、`assets/motion/` |
| **执行层** | token、对比度、确定性审计、运行时探针 | `scripts/`、`evals/` |

它**不是**一个「风格生成器」，也不提供一套万能模板。它提供约束、诊断和可运行的机制库；
风格必须从**这个题材**里长出来。

### 签名方法：物性优先 Physical First

写布局之前，先选**一个物理关系**；布局是它的投影，动效是它的证据。

轨道 / 传送带 / 幕布 / 扫描头 / 镜头 / 剖面 / 折页 / 网格纸 / 转台 / 开关板 / 织机 / 档案柜。
一个页面一个主结构。选不出物理关系，说明还没理解题材；不要用「现代简洁」蒙混。

## 审美高度

七维 rubric（0–5）：**题材扎根 / 物理关系 / 排版人格 / 构图张力 / 克制 / 完成度 / 动效编排**。
通过线：平均 ≥4.0，无单项 ≤2。这是「工作室可交付」的门槛，不是「能用」。

三个基准页在 `assets/golden/`：`aperture`（编辑型技术产品）、`atelier-north`（建筑图纸）、
`studio`（12 机制动效实验室）。它们是质量地板，不是模板。逐页拆解见 `references/25-golden-pages.md`。

## Step 0 · 探测（任何判断之前）

先跑这一遍。它防止两个最坏的失败：跟已有系统打架，以及输出项目用不了的代码。

1. **框架** — React/Vue/Svelte/纯 HTML；SSR 还是 SPA。
2. **Tailwind 及版本** — v4 用 CSS 里 `@theme`；v3 用 `tailwind.config.js`。查 `package.json`，
   再看 `@import "tailwindcss"` vs `@tailwind base`。
3. **已有 token** — CSS 自定义属性、主题对象、`tokens.json`、`theme/` 目录。
4. **组件库** — shadcn/ui、HeroUI、Mantine、MUI、Ant Design、Radix、Base UI。
5. **深色模式** — 已有、计划中、还是不需要。
6. **动效基线** — 有没有 `prefers-reduced-motion`、动画库、滚动库、WebGL/canvas。

**最高原则：既有系统永远优先。** 项目有系统时，把本书的原则翻译成它的词汇；
没有时，提出一个。不要覆盖、不要静默迁移、不要装用户没要求的依赖。

## 路由

| 用户要… | 工作流 | 先读 | 退出条件 |
|---|---|---|---|
| 配色、设计系统、token、字阶/间距 | **A · Tokens** | `05` → `03` → `04` | 五件套齐 + 每个前景/背景对算过对比度 |
| 新页面、屏幕、组件、落地页 | **B · Build** | `01` → 相关规则镜 → `21` | 首行有 DESIGN BRIEF；1280/375 看过；`audit.py` 无 P0 |
| 「弄好看点」「看着不对」 | **C · Refine** | `12` → `13` | D 的 P0 全清；P1 清到用户说够 |
| 评审、上线前检查 | **D · Audit** | `12` → `24` | 七镜 + 动效三层证据 + `skipped` 列全 |
| 找参考、这个风格怎么落地 | **E · Reference** | `14` → `19` → `25` | 找到可解释的匹配，或明确声明无匹配 |
| 动效设计、加交互、调手感 | **F · Motion** | `09` → `22` → `23` → `24` | 主族 + 一个注意瞬间 + 参数在簇内 + 运行时验证 |
| 组件库选型 / 某个库怎么写 | **G · Stack** | `18` → `15`/`16`/`17` | 决策树走到一个叶子并给出理由 |

**混合意图按顺序跑，并说明在跑哪几个**：
「没有设计系统的设置页」= A→B；「太丑，顺便加动效」= D→C→F；
「照这个风格做落地页」= E→B→F；「用 HeroUI 重做」= G→B→D。

**强度档位**：用户说「快速看一下」→ 只跑 D 的 P0；说「正式评审」→ 七镜 + 动效三层 + 报告；
说「从零做」→ A/B/F 全跑。不要对一句「看看这个按钮」启动完整设计系统流程。

---

## Workflow A · Tokens

项目没有设计系统，或系统有缺口。已有系统 → 跳过，直接翻译。

1. **访谈**（可选）— 最多四轮，批量问，每问可跳过。用户说「你定」就取默认值直接进第 2 步。
2. **生成色阶** — 每个色系跑一次：

   ```bash
   python3 -I scripts/generate_palette.py --base "#0f766e" --name brand --json
   ```

   算法：base(500) → 两端(900/100) → 中点(700/300) → 填充(800/600/400/200)；
   明度远离 50% 时饱和度上升，色相旋转上限 20–30°。**不要手挑 hex**——手挑的色阶会漂。

3. **验证对比度** —

   ```bash
   python3 -I scripts/check_contrast.py --pair "#0f766e" "#ffffff"
   python3 -I scripts/check_contrast.py --matrix tokens.json
   ```

   正文 4.5:1，大文本 3:1。半透明必须算**复合后**的颜色。

4. **产出五件套** — `design-tokens.json`、Tailwind 主题块（按探测到的版本）、`tokens.css`、
   人读的 `DESIGN` 文档、`preview.html`。

5. **间距与字阶** — 从 `references/03-layout-spacing.md` §3.2 和 `references/04-typography.md` §4.1 取刻度。
   相邻档比值 ≥1.2（字阶）/ 1.25（间距）。

**退出**：五个产物齐了，且每个前景/背景对都算过对比度。不需要生成 preview 页也能停。

---

## Workflow B · Build

**顺序就是方法。** 打乱顺序是界面变得「过度装饰而结构不足」的主因。

### B.0 物理关系 + 原型（强制，二选一）

先按 `references/01-aesthetic-direction.md` 的六步做题材考古，写出**一个物理关系**和**三个布局推论**。

然后选一个原型作为约束（不是答案）：

```bash
python3 -I scripts/query_corpus.py --style minimal --genre saas
python3 -I scripts/query_corpus.py --color dark --limit 5
python3 -I scripts/query_corpus.py --list
```

读 `assets/patterns/<id>.md`。**如果没有任何原型匹配简报，明确说「无匹配原型，走自由方向」**，
并在下一步写出你自己的 token 系统。不允许跳过这一步直接写代码。

### B.1 约束简报（强制，写在产出文件首行）

```js
/* DESIGN BRIEF
 * Subject: <产品/受众/主任务，一句话>
 * Materials: <3 个具体名词 / 2 种材料 / 1 个动词>
 * Physical: <一个物理关系> → <3 个布局推论>
 * Archetype: arch-xxxxxx（或 FREE）
 * Content rank: primary=<…> / secondary=<…> / tertiary=<…>
 * Primary action: <唯一实心>
 * Tokens: --canvas #…, --surface #…, --ink #…, --muted #…, --accent #…
 * Type: <families + roles>; scale <a/b/c/d> (ratio 1.25); heading <weight/tracking>
 * Motion: <一个注意瞬间> + <参数簇> + <reduced-motion 终态>
 * Forbidden: <本页禁止的 3 个默认>
 */
```

这段不是形式主义：评审者能看出分级**确实做过**，而不是假定做过。
`Subject / Physical / Forbidden` 三项缺一，Build 不算完成。

### B.2 构建顺序

1. **从一个功能开始，不是一个外壳。** 先设计实际功能，再导航、容器、logo。
2. **先灰度。** 强制用间距、尺寸、对比承担层级，然后才上色。
3. **内容分级** 主要 / 次要 / 三级；行动分一个主 / 少数次 / 若干三级。
4. **从刻度布局。** 间距、尺寸、字号全部来自系统；组间距 ≥ 组内 1.5–2 倍。
5. **定行宽与节奏。** 45–75 字符；行高随行长和字号变化。
6. **上色 → 深度 → 收尾**，按这个顺序。
7. **空状态是功能的一部分。** 零数据时隐藏无用的 tab/筛选器。
8. **视觉验证。** 见 B.3。

### B.3 视觉验证（强制）

- 1280×900 与 390×844 各截一次；只看过代码的发现标 `verified: false`。
- **动效证据**：注意瞬间至少两帧（起点/终点）或 3 秒录屏；只有静态首屏、
  没有起点/终点对比 → `verified: false`。
- **390 微尺度五项**：数字与地名/标签不碰撞；端点标签不越界；无孤立单字；
  触控目标 ≥44×44；最后一行不是压扁的桌面版。
- 与 `assets/golden/` 的三页并排：问「缺的是结构、字、色、还是收口？」
- 用 `01` 的 7 维 rubric 打分；平均 <4.0 或任一 ≤2 → 回到 B。
- 用 `audit.py` 扫一遍：P0 清零；P1 逐条解释（可留，但不能沉默）。

**退出**：首行有完整 DESIGN BRIEF；1280/375 看过；动效两帧/录屏；390 五项过；
`audit.py` 无 P0。

---

## Workflow C · Refine

改造现有页面，不重写。

1. **先审计**（D），拿到 P0/P1/P2 清单；不要凭感觉改。
2. **结构优先于外观**：层级、分组、间距、行宽、对齐 → 再字/色/深度 → 最后动效。
3. **每条规则一个可评审 diff**：说明改前/改后/依据的规则 ID；不要一次提交 40 个改动。
4. **不改变用户没要求的东西**：不改品牌色、不改信息架构、不换组件库。
5. **复验**：重跑 `audit.py` + 1280/375 截图 + reduced-motion。
6. 其他发现写进报告，不擅自修。

**退出**：P0 全清；P1 清到用户说够；没有为了清零而重写组件。

---

## Workflow D · Audit

七面固定镜头，按顺序走；每面都要有可指认的位置与规则 ID。

| 镜 | 看什么 | 规则 |
|---|---|---|
| 1 层级 | 第一眼、第二眼、主行动、竞争行动 | `02` |
| 2 布局/间距 | 组间距、容器宽、节奏、响应式 | `03` |
| 3 排版 | 字阶、行宽、行高、字重、中文 | `04` |
| 4 颜色 | 对比度、色阶、语义、暗色 | `05` |
| 5 深度 | 光源、层级、阴影、边框 | `06` |
| 6 图像 | 裁切、比例、图文关系、图标 | `07` |
| 7 收尾 | 空/错/载、最后 5%、边缘 | `08`、`13` |

**动效另走三层**（`references/24-motion-verification.md`）：静态扫描 `check_motion.py` → 运行时探针
`verify_motion.mjs` → 人工截图/录屏。三层缺一，不能写 `verified: true`。

### 报告格式

```markdown
# UI Audit — <file/screen>
**结论**：P0 <n> / P1 <n> / P2 <n>；是否可上线：<是/否/有条件>

## P0（阻断）
- [R-02-3] <位置> — <现状> → <建议>（<effort>）

## P1（明显）
...

## P2（打磨）
...

## Skipped
- <检查项> — <原因>（无浏览器/跨域 iframe/…）
```

**退出**：七镜走完 + 动效三层 + `skipped:` 列全。不要为了「完整」编造发现。

---

## Workflow E · Reference

```bash
python3 -I scripts/query_corpus.py --list
python3 -I scripts/query_corpus.py --style editorial --genre portfolio
python3 -I scripts/query_corpus.py --id arch-1a1b08
python3 -I scripts/query_corpus.py --brands
python3 -I scripts/query_corpus.py --brand linear.app --section colors
```

读 `assets/patterns/<id>.md`。用法：

1. **取区间，不取点。** 中位数是统计产物，不是设计目标。
2. **原型给约束，品牌给语言。** 先原型收窄方向，再 2–3 个品牌看具体值怎么落。
3. **解释匹配。** 写「因为这个原型的字阶 1.12–1.23 与题材的紧凑感一致」，
   不是「因为它是 minimal」。
4. **无匹配就说无匹配。** 不要硬套；走自由方向并写出自己的 token。

**退出**：一个可解释的匹配，或明确声明无匹配。不要穷举语料。

---

## Workflow F · Motion

**先决定动效为什么存在，再决定它长什么样。**

### F.1 目的

| 目的 | 时长 | 频率 | 例子 |
|---|---|---|---|
| 解释变化 | 120–350ms | 用户触发，必须有 | 菜单展开、状态切换、内容替换 |
| 吸引注意 | 400–1200ms | 非用户触发，一页最多一次 | 首屏入场、品牌氛围、关键 CTA |

一页只允许**一个**非用户触发的注意瞬间。其余动效只解释变化。

### F.2 选一个主族（F1–F14）

| 族 | 一句话 | 代码资产 |
|---|---|---|
| F1 滚动叙事 | 滚动位置决定段落/位移/透明度 | `kits/01`、`components/10` |
| F2 横向轨道 | 滚轮/拖拽映射轨道 + 惯性 | `kits/02`、`merged/13` |
| F3 全屏 shader | 全屏片元做背景/液体/textmode | `kits/03`、`components/05` |
| F4 WebGL 3D | 物体/相机/场景 | `merged/14` |
| F5 像素 canvas | 低分辨率 + 整数放大 + 调色板 | `kits/04`、`merged/15` |
| F6 排版动效 | 行/字/字重作为结构 | `kits/07`、`components/12` |
| F7 光标/磁吸 | dot/ring/磁吸/多层视差 | `kits/06`、`components/09` |
| F8 音频/波形 | 音频是状态源 | `kits/09`、`components/11` |
| F9 3D 倾斜/材质 | 倾斜/卷动/箔材/玻璃 | `kits/05`、`components/02` |
| F10 相机/缩放 | 页面是可移动地图 | `kits/10`、`components/06` |
| F11 传送带 | 环形内容 + 速度/摩擦 | `kits/02`/`12`、`components/04` |
| F12 扫描/VHS | 扫描线/噪点/色带/glitch | `merged/16`、`code/css` |
| F13 视频拼贴 | 多视频作为版面零件 | `kits/08`、`merged/17` |
| F14 状态机/演示 | 多步骤 UI 的命名状态 | `kits/11`、`components/03/07/08` |

一个页面只选 **1 个主族 + 最多 2 个辅族**。主族决定结构，辅族只做局部反馈。

### F.3 写 beat sheet

```text
状态：hidden → entering → visible → exiting → reduced
触发：scroll / pointer / time / state
时长：<簇内值，写理由>
缓动：<enter ease-out / exit ease-in / move ease-in-out / spring>
错峰：<20–50ms，总 ≤300ms，仅同组>
终态：<reduced 时直接到哪里>
```

### F.4 实现

- 默认只动 `transform` / `opacity`；`clip-path` / `grid-template-rows` 属例外，要写代价。
- 输入映射成**力**：速度/角度 + 摩擦/弹簧；不要直接设 `scrollTop`。
- 深度四通道一起改：scale/blur/z/opacity。
- 几何因果：展开的圆心/方向来自触发物。
- 无限动画必须能停：hover 减速 + `prefers-reduced-motion` 终态 + 页面隐藏暂停。
- 音频/视频必须用户手势解锁；视频 `muted playsinline`。

### F.5 验证

```bash
python3 -I scripts/check_motion.py <file> --json
node scripts/verify_motion.mjs --component <dir>   # Playwright 可选
```

**退出**：静态 0 个 P1；运行时 `verified: true`；reduced-motion 到终态；
375 无溢出；console 0 error；主族 + 注意瞬间 ≤1。缺浏览器就写 `skipped: no browser`，不算通过。

---

## Workflow G · Stack（三库）

| 库 | 什么时候 | 先读 | 关键规则 |
|---|---|---|---|
| **shadcn/ui** | 要完全掌控源码、做独特视觉、团队熟悉 Tailwind | `15` | 先 `npx shadcn@latest info --json`；`docs <c>`；`add`；presets；`components.json`；源码归项目 |
| **HeroUI v3** | 要开箱即用、React Aria 无障碍、接受组件是依赖 | `16` | Tailwind v4 必须；无 Provider；复合组件；`onPress`；`@heroui/styles` 导入顺序；oklch |
| **Mantine 9.x** | 表单/日期/图表/排程重、要组件数量 | `17` | Provider + `createTheme`；Styles API；`factory`；非受控表单；`useCombobox` |

- 选型决策树：`references/18-stack-selection.md`。走到一个叶子，给出理由。
- **默认不混用**：三库主题系统会打架（Mantine 10 档色阶 vs Tailwind 变量）。混合只在有明确边界时。
- **不 vendored 组件源码**：技能只给路由、适配规则和 MCP/离线文档配置；组件由库/CLI 提供。
- **HeroUI v2 → v3**：走 `heroui-migration`（无 Provider、复合组件、`onPress`、去 framer-motion）。
- **MCP**：shadcn 7 工具（需 `components.json`）、HeroUI 6 工具（Node ≥22.22）、Mantine 5 工具（无状态）。
  配置见 `assets/mcp.json`；无 MCP 时用离线文档回退。
- 版本以项目 `package.json` 和已安装技能为准；本文写的版本只是校准点。API 不确定时先查源码/文档，不凭记忆写。

---

## 十二条法则

1. **层级就是工作本身。** 不是配色，不是阴影；是用户先看什么、再看什么。
2. **靠削弱竞争者来强调。** 想让 A 突出，先让 B/C 退后；不是把 A 加大加亮。
3. **每个值都来自系统。** 间距、字号、圆角、阴影、颜色；一次性值就是漂移的开始。
4. **从「太多留白」开始。** 觉得刚好时再加一档；拥挤是默认失败。
5. **组间距 > 组内间距。** 至少 1.5–2 倍；否则关系读不出来。
6. **尺寸不是唯一的杠杆。** 字重、颜色、对比、位置、留白、动效都能分级。
7. **不要在彩色背景上用灰字。** 用同色相的深/浅，或加透明度；灰会脏。
8. **一屏一个主行动。** 多个实心按钮 = 没有主行动；危险操作不因危险而变大。
9. **语义标签与视觉层级分开。** `h2` 不必比 `h3` 大；用 class 控制视觉。
10. **光从上方来。** 阴影向下、内阴影上亮下暗；暗色模式阴影失效，用表面亮度。
11. **行宽 45–75 字符。** 超过 80 字符，眼睛回行会丢；中文约 30–45 字。
12. **永远不要只靠颜色编码。** 加图标、文字、下划线、形状；色盲用户存在。

> 规则编号出处：`§1.x`–`§8.x` 来自 *Refactoring UI*；`§2.9`、`§5.9` 是扩展；
> `§9.x`–`§11.x` 是动效/无障碍/文案新章。审计报告引用时写「扩展 §x.y」或原书 §x.y。

## 动效十条铁律

1. **两种目的**：解释变化（120–350ms，必须有）与吸引注意（400–1200ms，一页一次）。
2. **一个物理关系**：布局是投影，动效是证据；不要用「现代简洁」代替。
3. **输入映射成力**：速度/角度 + 摩擦/弹簧；不要直接设 `scrollTop`。
4. **深度四通道**：scale + blur + 亮度/透明度 + 叠放；只改 scale 是缩放，不是空间。
5. **几何因果**：展开的圆心/方向来自触发物；不是屏幕中心。
6. **错峰可读**：20–50ms，总 ≤300ms；超过 8 项只错前 8 项。
7. **只动 transform/opacity**：布局属性、`box-shadow`、`filter: blur` 默认不动；例外要写代价。
8. **reduced-motion 到终态**：不是「没有动画」，是「直接到结果」。
9. **不自动播放声音**：视频 `muted playsinline`，音频用户手势解锁；离屏暂停。
10. **三层验收**：静态 + 运行时 + 人工；`verified: true` 只在运行时通过后写。

---

## 资产索引

| 资产 | 内容 |
|---|---|
| `references/00-routing.md` | 七工作流、混合意图、强度档位 |
| `references/01-aesthetic-direction.md` | 物性优先六步、四个杠杆、7 维 rubric、反默认指纹 |
| `references/02`–`08` | 层级 / 布局间距 / 排版 / 颜色 / 深度 / 图像 / 收尾 |
| `references/09-motion-principles.md` | 两种目的、14 族、时长/缓动/编排、假信号 |
| `references/10`–`13` | 无障碍 / 文案 / 审计 / 反模式 |
| `references/14-pattern-library.md` | 14 原型怎么读、怎么取区间 |
| `references/15`–`18` | shadcn / HeroUI / Mantine / 选型决策树 |
| `references/19-brand-index.md` | 84 品牌语言索引与用法 |
| `references/20`–`21` | Tailwind 映射 / 实测 CSS 基线 |
| `references/22-motion-implementation.md` | 每族骨架、契约、性能预算、降级 |
| `references/23-motion-cases.md` | 30 案实测读数、可迁移、不要照搬 |
| `references/24-motion-verification.md` | 静态检查 ID、运行时 schema、假绿清单 |
| `references/25-golden-pages.md` | 3 个 golden 页的逐页拆解 |
| `references/26-site-techniques.md` | 26 个 demo + 2 个索引页 |
| `references/27-site-studies.md` | 一份内容 × 六种设计语言 |
| `assets/patterns/` | 14 张原型卡 + archetypes.json（区间，不含 URL） |
| `assets/brands.json` | 84 份品牌 DESIGN 文档合为一个 JSON（MIT） |
| `assets/motion/code/kits/` | 12 个紧凑机制 kit（零依赖） |
| `assets/motion/code/components/` | 12 个复合组件（5 文件/个，`mount/dispose`） |
| `assets/motion/code/merged/` | 5 个补缺组件：F2/F4/F5/F12/F13 |
| `assets/motion/code/css/keyframes.css` | 24 条 canonical keyframes（从 1,537 块归并） |
| `assets/motion/code/snippets.js` | 8 个原语：lerp/spring/friction/IO/pin/DPR/WebGL/pointer |
| `assets/motion/prompts.md` | 10 份强提示词（整页生成用） |
| `assets/motion/` 索引 `index.json` | 族 → 代码/提示词/案例/参数 的唯一入口 |
| `assets/site-techniques.html` | 26 个单手法 demo + 2 个索引页（单文件 viewer） |
| `assets/site-studies.html` | 一份内容 × 六种设计语言 + 索引（单文件 viewer） |
| `assets/golden/` | aperture / atelier-north / studio + 截图 |
| `assets/tokens/` | `tokens.template.json`、`theme.template.css` |
| `scripts/` | audit / check_motion / check_assets / palette / contrast / emit / query / verify_motion |

## 自证

所有读数以 `SELF-CHECK.md` 与 `ui-design-v4/reports/` 为准；本文件只写口径。

| 项 | 口径 |
|---|---|
| 逆向语料 | **302** 个唯一站点（155 legacy + 50 `156-*` + 50 `300-*` + 47 `L0-*`） |
| 动效案例 | **30** 案（302 的 10%，14 族各 2–3 案） |
| 动效代码 | **1,310** 份盘中文件扫描；**870** 个唯一内容哈希；**1,537** 个唯一 `@keyframes` 块（351 个库默认） |
| canonical 代码 | **12** 复合组件 + **5** 补缺 merged = **17** 个可运行组件（另有 **12** 个机制 kit）；**24** 条 keyframes；**8** 个原语；**10** 份提示词 |
| 运行时 | **17/17** 组件通过 `verify_motion.mjs`：console 0、375 无溢出、reduced-motion 无无限动画 |
| 静态动效 | **0** 个 P1；P2 逐条可解释（无限循环/降级 cube） |
| 原型语料 | 目录 **550** → 抽取成功 **412** → 有 ≥3 色 token 可聚类 **379** → **14** 原型 |
| 品牌语料 | **84** 份 `DESIGN` 文档（74 YAML + 10 散文，MIT） |
| 审计金标准 | **8/8** 带 `--brand "#0f766e"`；不带 **7/8**（`05-landing` 漏品牌漂移）；`audit.py --self-test` **35/35** |
| 动效夹具 | **6/6** 通过 `check_motion.py --expect`；`--self-test` **13/13** |
| 资产门禁 | `check_assets.py` **0 errors**（索引/文件/URL/版本一致） |
| golden 页 | **3** 页；aperture/atelier 桌面与移动全页 + 视口，studio 桌面/移动视口 |

> 302 复刻是**静态种子**（0 rAF / 0 shader）；它们不是动效证据。
> 动效只认 12 个重写组件、5 个补缺组件与运行时探针。

## 作用域守则

- 只改用户要求的东西；其他发现写进报告，不擅自修。
- 不装依赖、不迁移样式体系、不改构建配置，除非用户明确要求。
- 不改品牌色/信息架构；不把「重做」当「优化」。
- 项目约定优先于本技能。
- 不声称未测的事：`verified` / `skipped` / `inferred` 三选一，写清。

## 输出语言

参考文件中文；规则 ID、类名、命令、文件路径保持英文/原文。
交付物语言跟随用户：用户中文就中文，用户英文就英文。

## Attribution

规则源自 *Refactoring UI*（Wathan & Schoger）；品牌文档来自
[awesome-design-md](https://github.com/VoltAgent/awesome-design-md)（MIT）；
逆向语料来自 One Page Love 公开目录，只做区间蒸馏，不再分发原始语料。
详见 `ATTRIBUTION.md`。