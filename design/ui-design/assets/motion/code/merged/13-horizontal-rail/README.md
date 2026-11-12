# 13-horizontal-rail — Horizontal Rail

> F2 横向轨道 / 惯性 · `verified: true`

## 机制

滚轮和拖拽都映射成轨道目标 `targetX`；每帧 `x = lerp(x, targetX, .15)`。
释放时把最近速度加到目标上（`velocity * 10`），自然衰减；边界用 clamp，
越界时按 `.15` 回弹。进度条用 `scaleX`，不动宽度。

## 参数

| 参数 | 值 | 来源 |
|---|---|---|
| follow | `lerp .15` | Observed（Tegra 组） |
| release | `velocity * 10`，随后 `*.92` | Authored |
| boundary | clamp + rubber `.15` | Observed/Authored |
| panel | `clamp(250px, 40vw, 520px)` | Authored |

## 交互

- 滚轮：纵向 delta 映射水平位移；`preventDefault` 只在纵向为主时。
- 拖拽：pointerdown/move/up；释放保留速度。
- 键盘：← →、Home、End。
- 触屏：`touch-action: pan-y`，水平通道由 JS 接管。

## 降级

- `prefers-reduced-motion: reduce`：取消 JS 位移，`overflow-x:auto` + `scroll-snap`。
- 无 JS：track 仍是 flex，viewport 可横向滚动（CSS 兜底）。

## 验证

```bash
node ../../../../../scripts/verify_motion.mjs --component .
```

期望：`__rfStats.horizontal.frames > 0`；375 无溢出；reduced 模式 `transform: none`。

## 限制

- 没有 snap-to-panel；需要吸附时用 reduced 路径的原生 scroll-snap，或自行加索引目标。
- 速度是在 pointermove 里估的，不是高精度采样；够用，不适合物理仿真。