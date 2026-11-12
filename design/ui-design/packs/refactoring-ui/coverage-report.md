# Refactoring UI — coverage report

> 上游：edisonmbli/refactoring-ui-skill（MIT 原创部分；*Refactoring UI* 书版权归 Wathan/Schoger）。
> 本报告只做映射与缺口审计，不复制书正文。

## 方法

- 从上游 `references/00-coverage-matrix.md` 解析 **151** 条：50 个 top-level + 101 个 sub-point（含 9 个 `n.n.a` 正文补充项）。
- 每条规则按章节映射到本 skill 的主题章节；本 skill 不使用上游的 `§n.n` 编号，因此不声称逐条原文覆盖。
- 状态：`covered` = 本 skill 有对应主题与可执行检查；`partial` = 只覆盖父规则/缺少具体做法；`gap` = 当前没有对应内容。
- 分数不是验收分数；缺口进入 pack 的 remediation，不假装 151/151 逐条同构。

## 总览

| 状态 | 数量 |
|---|---:|
| covered | 138 |
| partial | 7 |
| gap | 6 |
| **合计** | **151** |

## 按章节

| 章 | 上游条目 | 映射到 | covered | partial | gap |
|---|---:|---|---:|---:|---:|
| 1 | 17 | `subskills/direction + Workflow B` | 16 | 1 | 0 |
| 2 | 20 | `references/02-hierarchy` | 20 | 0 | 0 |
| 3 | 18 | `references/03-layout-spacing` | 18 | 0 | 0 |
| 4 | 28 | `references/04-typography` | 26 | 1 | 1 |
| 5 | 22 | `references/05-color` | 19 | 1 | 2 |
| 6 | 17 | `references/06-depth` | 14 | 1 | 2 |
| 7 | 14 | `references/07-imagery` | 13 | 0 | 1 |
| 8 | 12 | `references/08-finishing` | 11 | 1 | 0 |
| 9 | 3 | `subskills/direction self-eval + SKILL` | 1 | 2 | 0 |

## partial / gap 明细

| ID | 上游断言（摘要） | 状态 | 本 skill 现状 / 补救 |
|---|---|---|---|
| 1.5.3 | Systematize everything | partial | tokens/motion token 覆盖主要系统；opacity/border-width 未全部列。 |
| 4.4 | Baseline, not center | gap | 04 讲对齐，但未讲混排字号按基线对齐。 |
| 4.7.3 | Hyphenate justified text | partial | 04 提到两端对齐需连字符支持；未给完整规则。 |
| 5.1.1 | HSL vs. HSB | gap | 05 用 HSL，未解释 HSB 与 HSL 的 50% 亮度差异。 |
| 5.4.1 | Use perceived brightness to your advantage | gap | 05 讲饱和度补偿，未给感知亮度公式。 |
| 5.4.2 | Changing brightness by rotating hue | partial | 05 有 20–30° 上限；未给 60/180/300 与 0/120/240 的具体方向。 |
| 6.3.1 | Accounting for elevation | partial | 06 有双层阴影；未把环境阴影随高度衰减写成规则。 |
| 6.4.2 | Using solid shadows | gap | 06 讲阴影/边框替代，未讲零模糊实心阴影。 |
| 6.5 | Overlap elements to create layers | gap | 06 讲深度，未讲元素跨背景/父容器叠层。 |
| 7.4.2 | Prevent background bleed | gap | 07 讲裁切，未讲用户图与背景同色时的内阴影/半透明内边框。 |
| 8.1 | Supercharge the defaults | partial | 08 有重色强调；未覆盖列表符号/引号/自定义 checkbox。 |
| 9.1.1 | Look for decisions you wouldn't have made | partial | 01 自评有「换个品牌名」；未覆盖「别人做过而你不会的决定」。 |
| 9.1.2 | Rebuild your favorite interfaces | partial | 01 有截图自评；未覆盖「不看 devtools 重建」。 |

## 结论

- **151/151** 有章节级 home；按可执行深度是 **138 covered / 7 partial / 6 gap**。
- 缺口不阻塞 v5.0：它们都在上游有明确条目，使用时按需读取 `packs/refactoring-ui` 并回到原书核对。
- 新增规则时先查本报告，避免再造一套平行编号；重复的规则保留现有 ID。
- 商业交付仍按 `NOTICE` 的 Refactoring UI 条款：不复制书正文、不声称官方、不替代原书。
