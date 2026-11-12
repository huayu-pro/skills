# 01-orbit-gallery — Orbit Gallery

> 六张卡片绕一个核心轨道；深度同时驱动 scale/blur/z-index/opacity。
> 家族：F3 WebGL 全屏 shader / lens · verified: `true`

## 机制

六张卡片绕一个核心轨道；深度同时驱动 scale/blur/z-index/opacity。

## 合并来源

| 来源 ID | type | 层级 | 保留 |
|---|---|---|---|
| `ui3-carousel-cards-0611d180` | carousel-cards | molecule | 结构/语义参考；文案/资产/动效重写 |
| `ui3-carousel-cards-9c165069` | carousel-cards | block | 结构/语义参考；文案/资产/动效重写 |
| `ui3-carousel-cards-a0c34418` | carousel-cards | block | 结构/语义参考；文案/资产/动效重写 |
| `ui3-carousel-cards-8fa18225` | carousel-cards | block | 结构/语义参考；文案/资产/动效重写 |
| `ui3-carousel-cards-2e561db1` | carousel-cards | block | 结构/语义参考；文案/资产/动效重写 |
| `ui3-gallery-grid-a60a4f72` | gallery-grid | atom | 结构/语义参考；文案/资产/动效重写 |

## 引擎

| 引擎 | 来源 | 证据 |
|---|---|---|
| OrbitEngine | `reverse-pilots/cases/01-scroll-narrative-angelo/site/script.js` | observed |
| LensGallery | `reverse-pilots/cases/01-scroll-narrative-angelo/site/script.js` | observed |

## 参数

| 参数 | 值 | 来源 |
|---|---|---|
| lerp | 0.08 | Observed（Angelo） |
| velocity damping | 0.9 / 帧 | Observed |
| wheel | deltaY × 0.0014 | Observed |
| drag | dx × 0.004 | Observed |
| depth 通道 | scale .72–1.06 / blur / z 60±40 / opacity .62–1 | Observed |

## 交互

- 键盘：Tab, ArrowLeft, ArrowRight, Enter, Escape。
- 指针/滚轮/触屏：见 `component.js`；移动端只保留核心手势。

## 降级

- `prefers-reduced-motion`：prefers-reduced-motion: 静态 3×2 网格，无轨道旋转/模糊
- 移动端：390px 无横向溢出；触控目标 ≥44px。

## 验证

```bash
node ../../../../../scripts/verify_motion.mjs --component .
```

## 限制

- 轨道不是原站同帧；lens shader 的运行时参数未采样
- 8/8 拖拽但原站 0/8 inertia
