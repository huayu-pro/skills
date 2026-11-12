# 28 · 动效系统：模型、register、预算、质量

> 这是 v5.0 的动效单一规范。`09` 给原理与案例，`22` 给实现，`24` 给验收；冲突时以本章为准。

## 1. 统一模型

| 用途 | 公式 | 参数 | 证据 |
|---|---|---|---|
| 追目标 | `alpha = 1 - exp(-lambda*dt)` | lambda 8–14 s⁻¹ | 60/120/30fps 同收敛 |
| 弹簧 | `accel = omega²(target-x) - 2ζωv` | ζ=1 临界；ζ<1 回弹 | 记录 ζ/ω，不写裸 damping |
| 摩擦 | `v *= exp(-friction*dt)` | friction 1.1–4 | time-based |

`dt` 上限 1/30；页面隐藏暂停。`k=120, damping=20` 对应 ζ≈0.91，是欠阻尼，
有轻微回弹；不能同时写「临界」「无回弹」。旧 `lerp(.15)` 是 frame-based 观测，
在 shipped 资产里标 `legacy`，新代码不得复制。

## 2. Token 与 register

所有值来自 `--dur-* / --ease-* / --dist-* / --stagger-* / --spring-*`。
三套 register：

| register | duration | attention | ambient | feedback |
|---|---|---:|---:|---|
| expressive | 120–900ms | 1 | ≤2/page | 120–350ms |
| product | 120–480ms | ≤1 | ≤1/page | 120–350ms |
| utility | 0–240ms | 0 | 0 | 120–240ms |

观测值 0.45s / expo / power4 是语料频率，不是默认。选择必须通过 motion casting：
三种 easing/重量/方向，写清为什么这一版属于题材。

## 3. MOTION MAP 与三档预算

```text
role=attention trigger=load token=--dur-attention area=hero stoppable=visibility
role=ambient trigger=time token=--dur-ambient area=background stoppable=hover+visibility+reduce
role=feedback trigger=pointer token=--dur-short area=button stoppable=cancel+redirect
```

- attention：非用户触发，首屏可见或有因果线索；隐藏暂停；utility/catalog = 0。
- ambient：非用户触发，位移 ≤8px 或 opacity ≤.15；不压文字、不闪、不改布局；
  ≤1/viewport、≤2/page；hover/focus/visibility/reduced 可停。
- feedback：用户触发，必须存在；可取消、可重定向；不循环。
- `data-motion-role="catalog"`：demo 是内容，不是全页氛围；每个 demo 自带暂停，
  不共享 wheel/pointer 劫持，且只在 catalog profile 使用。

## 4. Native-first 与可打断

优先 CSS scroll-driven animations（`animation-timeline: view()/scroll()`）、
View Transitions、`@starting-style`、FLIP/shared-element；JS/rAF 用于需要力/惯性的机制。
所有状态机显式：`idle→entering→visible→exiting→hidden`；反向或连续输入从当前
computed value 重定向，取消旧动画，不排队；enter/exit 交接不用 `display:none`。

## 5. Reduced-motion identity

| 物理关系 | 静态身份 |
|---|---|
| 轨道 | 径向景深 + 前后标注 |
| 传送带 | 横向条 + 位置刻度 + scroll-snap |
| 幕布 | 分层表面 + 可见接缝 + 点击展开 |
| 扫描头 | 静态扫描线 + 标尺 |
| 剖面 | 静态切面 + 侧标注 |
| 档案柜 | 静态索引 + 开合状态 |

状态变化用 ≤120ms 的颜色/徽标提示；`prefers-reduced-transparency` 给不透明回退，
`prefers-contrast` 给高对比回退。不假造 `prefers-reduced-motion: less` 标准。

## 6. Compliance 与 Quality（两层）

Compliance（脚本）：M-001..M-016、运行时 `verified`、reduced 终态、375 无溢出、console 0。
Quality（人/LLM，0–5）：

| 维度 | expressive | product | utility |
|---|---:|---:|---:|
| 节奏 | 20 | 15 | 10 |
| 重量 | 15 | 10 | 5 |
| 缓动与题材人格 | 20 | 15 | 10 |
| 交接/打断 | 15 | 25 | 25 |
| 克制/得体 | 15 | 15 | 30 |
| 中帧工艺 | 15 | 20 | 20 |

加权 ≥4.0、无单项 ≤2 才过；utility 的克制/工艺 ≥3；product 的交接 ≥3。
每个分数写一条可指认观察。证据：attention 五帧或 3s 录屏 + `trace.json`
（16ms transform/opacity 采样）；交互三帧；`quality-bad-compliant` 必须 fail。

## 7. 裁决

`accepted` 需要 compliance + quality + appropriateness；优先级：用户指令 >
人工质量评审 > 运行时 > 静态。脚本不得单独写 `accepted:true`。
