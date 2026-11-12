---
name: ui-apple-motion
description: Apple/Fluid Interfaces 动效词汇、弹簧物理、可打断与 animation review。仅在用户点名苹果动效时加载。
metadata: { version: "5.0.0", source: "emilkowalski/skills", license: "MIT", parent: "ui-design" }
---

# Apple Motion Pack

来源：emilkowalski/skills（`apple-design`, `animation-vocabulary`, `improvements`, `review-animations`），
MIT，Copyright (c) 2026 Emil Kowalski。只提炼判断规则，不复制仓库。

## 核心输入

- 动画要解释变化、空间关系与连续性，不是装饰。
- 时间/重量/方向从交互出发；弹簧是 `ζ/ω` 的物理契约，不是 `damping=20` 的咒语。
- 手势应可打断、可反向；释放速度继续，取消从当前值续接。
- 先问「这个动画能不能删」，再问「参数对不对」；remove-animations 是一等能力。
- performance 是设计约束：transform/opacity、避免 layout、长任务与真机帧率。

## 与核心的关系

先读 `subskills/motion/SKILL.md` 和 `references/28-motion-system.md`；本 pack 只补
Apple 的词汇、审核问题与删除清单。冲突以核心 register/budget/quality 为准。

Review 用 `review.md`，词汇用 `vocabulary.md`。许可见 `NOTICE`。


---

## Reference: vocabulary.md

# Apple motion vocabulary（提炼）

| 术语 | 可指认问题 | 对应核心 |
|---|---|---|
| fluid interface | 手势是否从当前速度/位置续接？ | 28 §4 可打断 |
| spring settle | ζ 是 1 还是 <1？有没有不该有的回弹？ | 28 §1 |
| spatial continuity | enter/exit 是否共享物体/圆心/方向？ | 09 §5 几何因果 |
| interruption | 半途反向会不会跳回 0/1？ | 28 §4 |
| affordance feedback | 120ms 内是否让用户知道输入被接收？ | register=feedback |
| restraint | 删掉这条动画，信息是否更清楚？ | quality=克制/得体 |
| opportunity | 这个动效解释状态、空间，还是只是表演？ | MOTION MAP |

不把「苹果风」写成紫蓝渐变、玻璃滥用或全页弹性；那是 AI 默认，不是 Apple。


---

## Reference: review.md

# Animation review checklist

1. 列出每条动画的 role / trigger / token / area / stoppable；无 MOTION MAP 直接 fail。
2. 对 attention 和 feedback 各录 0/25/50/75/100% 五帧；只看首末帧记 `skipped`。
3. 半途反向、连续触发 5 次、切 tab 回来：无跳变、无叠加、终态正确。
4. 弹簧写 ζ/ω；ζ<1 不得标注「临界/无回弹」。
5. reduced-motion 保留页面身份，且状态变化可感知。
6. 删除测试：逐条关闭 ambient，若页面更清楚则 quality 的「克制」扣分。
7. 质量与合规分开写；`verified:true` 不等于 `accepted:true`。

来源保留：emilkowalski/skills MIT。本文件是独立提炼，不是原文复制。
