# 07-color-lab — Color Lab

> 6 档明度 + hue shift + 饱和衰减；WCAG relative luminance 对比度。
> 家族：F14 状态机 / 产品演示 · verified: `true`

## 机制

6 档明度 + hue shift + 饱和衰减；WCAG relative luminance 对比度。

## 合并来源

| 来源 ID | type | 层级 | 保留 |
|---|---|---|---|
| `ui3-form-contact-585e8164` | form-contact | molecule | 结构/语义参考；文案/资产/动效重写 |
| `ui3-form-contact-634765d0` | form-contact | block | 结构/语义参考；文案/资产/动效重写 |
| `ui3-form-contact-b3462718` | form-contact | block | 结构/语义参考；文案/资产/动效重写 |
| `ui3-form-contact-5c0a0677` | form-contact | block | 结构/语义参考；文案/资产/动效重写 |
| `ui3-form-contact-22b7248f` | form-contact | molecule | 结构/语义参考；文案/资产/动效重写 |

## 引擎

| 引擎 | 来源 | 证据 |
|---|---|---|
| ColorEngine | `reverse-250/repro/202-color-scales-i-o/site/script.js` | observed-repro |

## 参数

| 参数 | 值 | 来源 |
|---|---|---|
| bases | Graphite / Vermilion / Amber / Blue | Observed-repro |
| lightness | 94 / 82 / 68 / 54 / 38 / 22 | Observed-repro |
| hue shift | t × 10° + 用户 -30..30° | Observed-repro |
| saturation | s × (1 - |50-L|/180) × 1.05 × spread | Observed-repro |
| contrast | WCAG relative luminance | Observed-repro |
| reveal | 360ms / 20ms stagger | Authored |

## 交互

- 键盘：Tab, Arrow keys, Home, End。
- 指针/滚轮/触屏：见 `component.js`；移动端只保留核心手势。

## 降级

- `prefers-reduced-motion`：prefers-reduced-motion: 色阶直接出现，无 360ms/20ms stagger
- 移动端：390px 无横向溢出；触控目标 ≥44px。

## 验证

```bash
node ../../../../../scripts/verify_motion.mjs --component .
```

## 限制

- picker 用 HSL 映射，不是 OKLCH
- 对比度按 WCAG 2.1，不含 APCA
