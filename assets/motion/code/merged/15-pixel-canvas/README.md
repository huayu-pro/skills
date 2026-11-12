# 15-pixel-canvas — Pixel Canvas

> F5 Canvas2D 像素 / 角色 · `verified: true`

## 机制

画布固定 160×120，所有绘制用整数坐标；CSS 用 `image-rendering: pixelated`
放大到 `min(100%, 640px)`，不做平滑。6 色 palette；场景分五层：
天空色带、太阳、云、山、海、角色。`phase = time % 1` 驱动太阳呼吸、
云漂移、海浪位移、角色上下 1px。

## 参数

| 参数 | 值 | 来源 |
|---|---|---|
| canvas | 160 × 120 | Authored |
| palette | 6 colors | Authored |
| scale | `min(100%, 640px)` + pixelated | Authored |
| speed | 0–2× slider | Authored |

## 交互

- Speed：0–2×，直接改 `time += dt * speed`。
- Pause/Play：停/启 rAF。
- 页面隐藏：停 rAF；恢复继续。
- `prefers-reduced-motion`：只画 phase .3 的静止帧。

## 降级

- 无 Canvas2D：抛错，页面保留背景色；生产环境应显示静态图。
- reduced-motion：静止帧，不启动 rAF。

## 验证

```bash
node ../../../../../scripts/verify_motion.mjs --component .
```

期望：`__rfStats.pixel.frames` 增长；reduced 模式不再增长；375 无溢出。

## 限制

- 角色是 7×10 手写 sprite，不是多帧动画；要更丰富需扩展 `HERO`。
- 固定 160×120；更高分辨率要同比放大所有坐标，不是简单改 canvas 宽高。