# 12-editorial-motion — Editorial Motion

> 110% 行 mask + 逐字波 1.4s/0.07s + dt marquee + ±3° 速度 skew。
> 家族：F6 排版 / 动态字体 · verified: `true`

## 机制

110% 行 mask + 逐字波 1.4s/0.07s + dt marquee + ±3° 速度 skew。

## 合并来源

| 来源 ID | type | 层级 | 保留 |
|---|---|---|---|
| `ui3-footer-mega-6d9e4a93` | footer-mega | block | 结构/语义参考；文案/资产/动效重写 |
| `ui3-tabs-content-15c8d48c` | tabs-content | block | 结构/语义参考；文案/资产/动效重写 |
| `ui3-menu-mega-42a32747` | menu-mega | page-section | 结构/语义参考；文案/资产/动效重写 |
| `ui3-pricing-cards-d5b8fae0` | pricing-cards | block | 结构/语义参考；文案/资产/动效重写 |

## 引擎

| 引擎 | 来源 | 证据 |
|---|---|---|
| TypeMotion | `reverse-302/_kits/07-typography.js` | authored |
| EditorialChrome | `reverse-302/_kits/12-editorial-landing.js` | authored |

## 参数

| 参数 | 值 | 来源 |
|---|---|---|
| line mask | translateY(110%) → 0 / .8s | Observed（kit 07） |
| char wave | 1.4s / 0.07s delay | Observed（PP Neue Montreal） |
| marquee | 60 px/s，dt 基准 | Observed（kit 07 修正） |
| velocity skew | ±3° / lerp .12 | Observed（kit 07） |
| tab switch | 即时 | Authored |

## 交互

- 键盘：Tab, Enter。
- 指针/滚轮/触屏：见 `component.js`；移动端只保留核心手势。

## 降级

- `prefers-reduced-motion`：prefers-reduced-motion: 行直接显示，停止逐字波/marquee/skew
- 移动端：390px 无横向溢出；触控目标 ≥44px。

## 验证

```bash
node ../../../../../scripts/verify_motion.mjs --component .
```

## 限制

- 逐字波只用于短词 MOTION，不用于正文
- marquee 是装饰层，aria-hidden
