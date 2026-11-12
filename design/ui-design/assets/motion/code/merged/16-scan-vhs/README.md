# 16-scan-vhs — Scan / VHS

> F12 扫描 / VHS · `verified: true`

## 机制

三层独立速度，叠在同一个 monitor 里：

| 层 | 速度 | 实现 |
|---|---|---|
| 扫描线 | 8s linear infinite | `repeating-linear-gradient` + `translateY` |
| 噪点 | 1s steps(2) infinite | SVG `feTurbulence` data URI + `background-position` |
| glitch | 4.2s steps(1) | `clip-path: inset()` 切片 + 微小 `translateX` |

再加一条 `animationiteration` 计数，readout 显示 glitch 次数。
Pause 用 `animation-play-state`，不销毁 DOM。

## 参数

| 参数 | 值 | 来源 |
|---|---|---|
| scanline | 8s linear | Observed（三层速度） |
| noise | 1s steps(2) | Observed |
| glitch | 4.2s steps(1)，120ms 切片 | Authored |
| noise opacity | .08 / reduced .05 | Authored |

## 交互

- Scan / Noise / Glitch：三个 toggle，`aria-pressed` 同步。
- Pause/Play：暂停/恢复 CSS 动画。
- 页面隐藏：只加 `is-hidden-tab`，动画由浏览器节流。
- `prefers-reduced-motion`：三层动画 none，glitch 隐藏。

## 降级

- reduced-motion：静态扫描线 + 低透明噪点，无 glitch。
- 无 SVG filter 支持：噪点层透明，其余两层仍工作。

## 验证

```bash
node ../../../../../scripts/verify_motion.mjs --component .
```

期望：`__rfStats.scan` 存在；glitch 次数随时间增长；reduced 模式不再增长；
375 无溢出；console 0 error。

## 限制

- 噪点是背景图，不是逐帧噪声；大面积高频率可能掉帧。
- glitch 是切片模拟，不是真实 VHS 色带/磁迹。