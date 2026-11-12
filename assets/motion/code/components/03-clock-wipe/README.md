# 03-clock-wipe — Clock Wipe

> 可拖时钟 + 从点击点扩散的圆形换肤 + 滚轮抬升面板。
> 家族：F14 状态机 / 产品演示 · verified: `true`

## 机制

可拖时钟 + 从点击点扩散的圆形换肤 + 滚轮抬升面板。

## 合并来源

| 来源 ID | type | 层级 | 保留 |
|---|---|---|---|
| `ui3-menu-mega-f683afae` | menu-mega | page-section | 结构/语义参考；文案/资产/动效重写 |
| `ui3-menu-mega-34870e2a` | menu-mega | page-section | 结构/语义参考；文案/资产/动效重写 |
| `ui3-menu-mega-8214ed87` | menu-mega | page-section | 结构/语义参考；文案/资产/动效重写 |
| `ui3-section-split-b1a4821f` | section-split | page-section | 结构/语义参考；文案/资产/动效重写 |
| `ui3-testimonial-grid-b82795f6` | testimonial-grid | page-section | 结构/语义参考；文案/资产/动效重写 |

## 引擎

| 引擎 | 来源 | 证据 |
|---|---|---|
| ClockDial | `reverse-pilots/cases/03-cursor-petrillo/site/script.js` | observed |
| CircularWipe | `reverse-pilots/cases/03-cursor-petrillo/site/script.js` | observed |

## 参数

| 参数 | 值 | 来源 |
|---|---|---|
| wipe | circle(0 → 165vmax) / 680ms | Observed |
| clock drag | delta angle / 360 × 720min | Observed |
| lift | wheel / 1200 → 0..1 / 560ms | Observed |
| idle | 20s 下滑（原站） | Observed；本组件未启用 idle |
| hand easing | 880ms cubic-bezier(.65,0,.35,1) | Observed |

## 交互

- 键盘：Tab, ArrowUp, ArrowDown, Space, F, Escape。
- 指针/滚轮/触屏：见 `component.js`；移动端只保留核心手势。

## 降级

- `prefers-reduced-motion`：prefers-reduced-motion: 直接切换主题，无圆形擦除；面板直接抬起
- 移动端：390px 无横向溢出；触控目标 ≥44px。

## 验证

```bash
node ../../../../../scripts/verify_motion.mjs --component .
```

## 限制

- 日期是合成映射，不是真实日历
- 原站把交互内容放在 aria-hidden 容器，本组件已修正
