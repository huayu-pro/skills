# 04-belt-conveyor — Belt Conveyor

> 速度驱动的无限带：BASE 62、MAX 900、exp(-dt×1.1) 摩擦。
> 家族：F11 传送带 / marquee / ticker · verified: `true`

## 机制

速度驱动的无限带：BASE 62、MAX 900、exp(-dt×1.1) 摩擦。

## 合并来源

| 来源 ID | type | 层级 | 保留 |
|---|---|---|---|
| `ui3-section-split-155f4926` | section-split | page-section | 结构/语义参考；文案/资产/动效重写 |
| `ui3-section-split-cd4b2b1f` | section-split | page-section | 结构/语义参考；文案/资产/动效重写 |
| `ui3-section-grid-2051e484` | section-grid | block | 结构/语义参考；文案/资产/动效重写 |
| `ui3-section-content-d279510f` | section-content | block | 结构/语义参考；文案/资产/动效重写 |
| `ui3-faq-grid-e3329526` | faq-grid | page-section | 结构/语义参考；文案/资产/动效重写 |

## 引擎

| 引擎 | 来源 | 证据 |
|---|---|---|
| BeltEngine | `reverse-pilots/cases/04-typographic-jungle/site/script.js` | observed |

## 参数

| 参数 | 值 | 来源 |
|---|---|---|
| cards / spacing | 11 / 300px | Observed（JUNGLE 复刻） |
| belt | 3300px 环 | Observed |
| BASE / MAX | 62 / 900 px/s | Observed |
| friction | exp(-dt × 1.1) | Observed |
| wrap | mod(i × SPACING + offset, TOTAL) | Observed |
| distance channels | scale / rotate / rise / opacity / z | Observed |

## 交互

- 键盘：Tab, ArrowLeft, ArrowRight, Enter, Escape。
- 指针/滚轮/触屏：见 `component.js`；移动端只保留核心手势。

## 降级

- `prefers-reduced-motion`：prefers-reduced-motion: 4×3 静态卡片网格，无传送带
- 移动端：390px 无横向溢出；触控目标 ≥44px。

## 验证

```bash
node ../../../../../scripts/verify_motion.mjs --component .
```

## 限制

- 原站 REPORT 写每帧 .935，代码用 exp(-dt×1.1)；本组件按代码实现
- 卡片是自绘渐变，不是原站图片
