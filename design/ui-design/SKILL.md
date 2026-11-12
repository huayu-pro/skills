---
name: ui-design
description: >-
  设计、构建、改造、评审专业网站 UI，以审美得体为第一标准：题材扎根、物理关系、
  排版人格、构图张力、克制、完成度、动效编排。按需加载 direction / tokens / motion /
  audit 四个核心入口，以及 Apple、HTML 交付、DESIGN.md、Refactoring UI、代码动画、
  Remotion 可选 packs。用于新页面、落地页、设置页、表单、定价、空状态、设计系统、
  tokens、响应式、无障碍、动效手感、上线前审计。Use when the user asks for a page,
  landing page, UI design, design tokens, motion pattern, accessibility review,
  design audit, Apple/Liquid Glass style, HTML prototype/slides, DESIGN.md,
  Refactoring UI, code animation prompts, Remotion, or says 页面设计, UI 太丑,
  看起来像模板, 动效, 动画, 设计评审, 组件库选型. Exclude backend, native apps,
  commercial PPTX engineering, and video production unless a pack is selected.
license: "Mixed: MIT for original code; third-party and OPL-derived assets are not relicensed — see LICENSE, NOTICE, ATTRIBUTION.md"
metadata:
  version: "5.0.0"
  author: workspace
  category: design
  updated: "2026-11-12"
---

# UI Design 5.0 — 路由器

把「网站是否好看」变成**可指认、可实现、可验收**，同时把最不可 lint 的两件事——
**手感与得体**——保留为有证据的人工/LLM 判断。核心做深，扩展能力放在 packs。

## 两条 gate

1. **Appropriateness**：UI 第一美德是 appropriate，不是 distinctive。先判
   `surface profile`，再决定能不能大胆。设置页、表单、定价、后台、财务以克制和完成度为主。
2. **Acceptance**：`accepted = compliance + quality + appropriateness`。脚本证明「没坏」，
   不能单独证明「好看」。静态/运行时/人工证据分开写，未测写 `skipped`。

## 核心入口（按需加载，不整包读）

| 用户要… | 只读 | 说明 |
|---|---|---|
| 风格、题材、构图、反模板 | `subskills/direction/SKILL.md` | Physical First；expressive/editorial 强制，utility 可豁免 |
| 配色、字阶、间距、设计系统、DESIGN.md | `subskills/tokens/SKILL.md` | 五件套、对比度、motion token、既有系统优先 |
| 动效、交互、手感、reduced-motion | `subskills/motion/SKILL.md` | 统一时间模型、register、budget、quality review |
| 评审、上线前检查、报告 | `subskills/audit/SKILL.md` | 七镜、加权 rubric、provenance、self-review |

混合意图按顺序：无系统的设置页 = tokens → direction；太丑且要加动效 = audit → direction → motion；
正式评审 = audit + motion 的质量层。不要对「看看这个按钮」启动完整流程。

## 可选 packs（用户点名才读，一次最多 2 个）

| 触发 | Pack | 来源/许可 |
|---|---|---|
| Apple、弹簧、流体界面、苹果动效 | `packs/apple-motion/SKILL.md` | emilkowalski/skills · MIT |
| Apple、Liquid Glass、macOS 视觉 | `packs/apple-liquid-glass/SKILL.md` | naplesblue · MIT + Lucide ISC + emilkowalski MIT |
| 高保真 HTML 原型、幻灯片、信息图、导出 | `packs/html-deliverables/SKILL.md` | alchaincyf/huashu-design · MIT |
| DESIGN.md、lint/diff/export、品牌设计语言 | `packs/design-md/SKILL.md` | VoltAgent/awesome-design-md · MIT |
| Refactoring UI、151 条规则映射 | `packs/refactoring-ui/SKILL.md` | edisonmbli · MIT（原创部分）+ 书版权声明 |
| 代码动画风格提示词、动画分类 | `packs/code-animation-prompts/SKILL.md` | XiaoyeCodes · 自定义免费/保留来源/禁止付费打包 |
| 程序化视频、React 时间轴、Remotion | `packs/remotion/SKILL.md` | remotion-dev · Remotion License，外部依赖 |

Pack 是输入，不是豁免：Apple 风格仍要过对比度与 surface profile；HTML deck 仍要过七镜；
代码动画提示词仍要过 motion budget；Remotion 必须先过许可门槛。来源明细见 `NOTICE`、`ATTRIBUTION.md`。

## Step 0 · 探测（判断之前）

先查框架、Tailwind v3/v4、已有 token、组件库、深色模式、动效基线、SSR/hydration、
monorepo/CSS-in-JS/RSC 边界。有浏览器/真实页面时优先：

```bash
node scripts/detect_stack.mjs --url http://localhost:3000/settings --json
```

无浏览器时做文本扫描并把未探测项写 `skipped`。**既有系统永远优先**：翻译成它的词汇，
不覆盖、不静默迁移、不装依赖。

## 硬纪律

- 一页一个主结构；非用户动效按 register 分 attention / ambient / feedback 三档。
- 所有时间值来自 motion token；`0.45s + expo.out` 是观测众数，不是默认。
- reduced-motion 到终态，并保留物理/功能身份；不把页面删成普通栅格。
- 每次交付写 `profile / compliance / quality / appropriateness / accepted / skipped`。
- 普通页面不加载 packs；Stack（shadcn/HeroUI/Mantine）只在用户点名时读 `references/18`。
- 商业交付先跑 provenance：OPL 派生只保留区间；品牌文档是第三方观察；第三方 pack 按许可使用。

## 边界

不复制 AGPL 内容；不做 guizang / 原生 PPTX 工程；不 vendor Remotion 或 232MB 原型资产；
不声称脚本证明了好看；不把未测的 `verified` 写成 `true`。

正文详见 `references/00-routing.md`。版本分发用 `scripts/build_skills.py`。
