---
name: ui-motion
description: 动效为什么存在、统一运动模型、motion token/register/budget、native-first、可打断、reduced identity、质量验收。
metadata: { version: "5.0.0", parent: "ui-design" }
---

# UI Motion

先读 `references/28-motion-system.md`，再按需读 `09` / `22` / `24`。

## 1. 统一时间模型

所有新代码 time-based：

```js
const alpha = 1 - Math.exp(-lambda * dt);     // 追目标，lambda 8–14 s^-1
const accel = omega*omega*(target-x) - 2*zeta*omega*v; // semi-implicit spring
```

`zeta=1` 才是临界无回弹；`k=120, damping=20` 是 `zeta≈0.91` 的欠阻尼。
`lerp(.15)` 只允许出现在标为 `legacy/observed frame-based` 的旧案例。

## 2. Register + MOTION MAP

| 档 | expressive | product | utility/catalog |
|---|---|---|---|
| attention（非用户） | ≤1 | ≤1 | 0 |
| ambient（非用户） | ≤1/viewport, ≤2/page | ≤1 | 0 |
| feedback（用户） | 120–350ms，必须有 | 同左 | 120–240ms，必须有 |

在 DESIGN BRIEF 写 `MOTION MAP`：每条动效的 role / trigger / token / area / stoppable。
catalog demo 用 `data-motion-role="catalog"`，每个 demo 自带暂停，不得共享滚动劫持。

## 3. Casting, native, interruption, reduced

主 attention 做三种 easing/重量/入场处理，选「换题材就不成立」的那个。
优先 View Transitions、`@starting-style`、scroll-driven animations、FLIP；
rAF/IO 是 fallback。状态 `idle→entering→visible→exiting→hidden`：反向/连续输入
从当前值重定向，不回到 0/1、不排队、不 `display:none`。

reduced-motion 到终态并保留身份：轨道=静态径向景深，传送带=静态横向条+刻度，
剖面=静态切面+标注；状态变化给 ≤120ms 的颜色/徽标提示。详见 `28` 的 identity matrix。

## 4. 验收：Compliance ≠ Quality

```bash
python3 -I scripts/check_motion.py <file> --json
node scripts/verify_motion.mjs --component <dir> --trace
```

Compliance 是静态 0 P1、运行时 `verified:true`、reduced 终态、375 无溢出、console 0。
Quality 是 6 维人工/LLM rubric（节奏/重量/题材人格/交接/克制/中帧工艺），
要有 0/25/50/75/100% 五帧或 3s 录屏 + `trace.json`。`accepted` 不能由脚本单独给。

可选输入：苹果动效读 `packs/apple-motion`；代码动画分类读
`packs/code-animation-prompts`；程序化视频读 `packs/remotion`（先过许可）。
普通页面不加载 packs。
