---
name: ui-direction
description: 题材扎根、物理关系、排版人格、构图、克制、surface profiles、反默认指纹。用于决定页面长什么样。
metadata: { version: "5.0.0", parent: "ui-design" }
---

# UI Direction

先判 `surface profile`，再谈风格：

| profile | 典型 | 大胆程度 | 动效预算 |
|---|---|---|---|
| expressive | 作品集/品牌/活动 | 高 | attention ≤1, ambient ≤1 |
| product | 产品页/工作台 | 中 | attention ≤1, ambient ≤1 |
| utility | 设置/表单/定价/后台/财务 | 低 | attention=0, ambient=0 |
| editorial | 杂志/内容 | 中高 | attention ≤1, ambient ≤1 |
| catalog | demo/机制目录/组件文档 | 低 | attention=0, ambient=0；demo 算内容 |

必读 `references/01-aesthetic-direction.md`、`references/29-cjk-mobile.md`；
评分用 `references/12-audit-rubric.md` 的加权 rubric；对照页按 profile 从
`references/25-golden-pages.md` 选，不把纸白/墨色/衬线当通用品味。

流程：题材考古 → 物理/功能关系 → 三个布局推论 → 注意瞬间或明确写「本页无」 →
motion casting 三选一 → 反默认复查 → 1280/375 截图自评。

Physical First 在 expressive/editorial 强制；product 推荐；utility 可用
ledger / queue / workbench / checklist，或明确说明「本页不需要物理关系」。
「换个品牌名也成立」不再是唯一否决：utility 若 distinctive 但不得体，直接 fail。

视觉语言包只在用户点名时加载：Apple/Liquid Glass → `packs/apple-liquid-glass`。
普通 UI 不默认为 Apple 风，也不默认纸感。
