# 02-bend-carousel — Bend Carousel

> 32 条竖切片伪造圆柱面；进入曲线 1.55，落位 760ms。
> 家族：F9 3D 倾斜 / 剥皮 / 材质 · verified: `true`

## 机制

32 条竖切片伪造圆柱面；进入曲线 1.55，落位 760ms。

## 合并来源

| 来源 ID | type | 层级 | 保留 |
|---|---|---|---|
| `ui3-hero-centered-3ac99847` | hero-centered | molecule | 结构/语义参考；文案/资产/动效重写 |
| `ui3-hero-split-ba9e2048` | hero-split | block | 结构/语义参考；文案/资产/动效重写 |
| `ui3-feature-bento-9db5cf15` | feature-bento | page-section | 结构/语义参考；文案/资产/动效重写 |
| `ui3-feature-bento-0b2edec9` | feature-bento | page-section | 结构/语义参考；文案/资产/动效重写 |
| `ui3-card-grid-f09aff89` | card-grid | block | 结构/语义参考；文案/资产/动效重写 |

## 引擎

| 引擎 | 来源 | 证据 |
|---|---|---|
| BendPanel | `reverse-pilots/cases/02-webgl-3d-mathias/site/script.js` | observed |

## 参数

| 参数 | 值 | 来源 |
|---|---|---|
| slices | 32 | Observed（Mathias 复刻） |
| edge rotate | t × -17° | Observed |
| depth | -(1 - cos(|t|π/2)) × 92px | Observed |
| entry curve | 1.55 | Observed |
| transition | 760ms cubic-bezier(.22,.8,.2,1) | Observed |
| drag commit | ±40px / threshold 10px | Observed |

## 交互

- 键盘：Tab, ArrowLeft, ArrowRight, Enter, Escape。
- 指针/滚轮/触屏：见 `component.js`；移动端只保留核心手势。

## 降级

- `prefers-reduced-motion`：prefers-reduced-motion: 2×2 平面网格，切片不弯曲
- 移动端：390px 无横向溢出；触控目标 ≥44px。

## 验证

```bash
node ../../../../../scripts/verify_motion.mjs --component .
```

## 限制

- 切片之间有可见接缝；不是像素级曲面
- 原站 CSS 注释 26 片，JS 实际 32 片，本组件取 32
