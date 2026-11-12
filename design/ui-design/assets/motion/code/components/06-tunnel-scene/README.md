# 06-tunnel-scene — Tunnel Scene

> 26 层圆角矩形 + 46 粒子；滚动推进相位，拖拽横向旋转。
> 家族：F10 相机 / 缩放 / 多 canvas · verified: `true`

## 机制

26 层圆角矩形 + 46 粒子；滚动推进相位，拖拽横向旋转。

## 合并来源

| 来源 ID | type | 层级 | 保留 |
|---|---|---|---|
| `ui3-accordion-faq-1302c874` | accordion-faq | molecule | 结构/语义参考；文案/资产/动效重写 |
| `ui3-accordion-faq-728a4bf3` | accordion-faq | block | 结构/语义参考；文案/资产/动效重写 |
| `ui3-faq-grid-72d3021d` | faq-grid | page-section | 结构/语义参考；文案/资产/动效重写 |
| `ui3-timeline-steps-62e5d6ba` | timeline-steps | molecule | 结构/语义参考；文案/资产/动效重写 |
| `ui3-section-split-7d45cf44` | section-split | page-section | 结构/语义参考；文案/资产/动效重写 |

## 引擎

| 引擎 | 来源 | 证据 |
|---|---|---|
| TunnelScene | `reverse-250/repro/164-spatial/site/script.js` | observed-repro |

## 参数

| 参数 | 值 | 来源 |
|---|---|---|
| layers | 26 | Observed-repro（164-spatial） |
| phase | pow(phase, 1.8) | Observed-repro |
| scroll gain | scrollN × 1.35 | Observed-repro |
| lerp | scroll .14 / drag .12 | Observed-repro |
| clamp | ±220 / ±180 | Observed-repro |
| release | 500ms 后 ×0.94 / 40ms | Observed-repro |

## 交互

- 键盘：Tab, ArrowUp, ArrowDown, Home, End。
- 指针/滚轮/触屏：见 `component.js`；移动端只保留核心手势。

## 降级

- `prefers-reduced-motion`：prefers-reduced-motion: 停 rAF，画一帧静态隧道
- 移动端：390px 无横向溢出；触控目标 ≥44px。

## 验证

```bash
node ../../../../../scripts/verify_motion.mjs --component .
```

## 限制

- Canvas2D 隧道是复刻近似，不是原站同帧
- 原站 interval 生命周期 bug 已改为逐帧衰减
