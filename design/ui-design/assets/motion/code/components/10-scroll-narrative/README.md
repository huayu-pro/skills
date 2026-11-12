# 10-scroll-narrative — Scroll Narrative

> IO reveal 200px/450ms/16px + sticky pin 三段 + accordion + modal。
> 家族：F1 滚动叙事 / 分段揭示 · verified: `true`

## 机制

IO reveal 200px/450ms/16px + sticky pin 三段 + accordion + modal。

## 合并来源

| 来源 ID | type | 层级 | 保留 |
|---|---|---|---|
| `ui3-navigation-bar-06c7a80c` | navigation-bar | block | 结构/语义参考；文案/资产/动效重写 |
| `ui3-navigation-bar-d0c95c6c` | navigation-bar | page-section | 结构/语义参考；文案/资产/动效重写 |
| `ui3-footer-mega-4bab00da` | footer-mega | page-section | 结构/语义参考；文案/资产/动效重写 |
| `ui3-footer-mega-c5f68b11` | footer-mega | page-section | 结构/语义参考；文案/资产/动效重写 |

## 引擎

| 引擎 | 来源 | 证据 |
|---|---|---|
| ScrollNarrative | `reverse-302/_kits/01-scroll-narrative.js` | authored |
| EditorialChrome | `reverse-302/_kits/12-editorial-landing.js` | authored |

## 参数

| 参数 | 值 | 来源 |
|---|---|---|
| IO | rootMargin 200px / threshold 0 | Observed（343 站） |
| reveal | 450ms / 16px / cubic-bezier(0,0,0.2,1) | Observed |
| pin budget | 320vh | Authored |
| pin end | innerHeight × duration × .78 | Observed（mappy） |
| accordion | grid-template-rows 0fr→1fr / .35s | Observed（v2 ch09） |
| nav hide | scroll down > 160px | Observed（kit 12） |

## 交互

- 键盘：Tab, Enter, Space, Escape。
- 指针/滚轮/触屏：见 `component.js`；移动端只保留核心手势。

## 降级

- `prefers-reduced-motion`：prefers-reduced-motion: reveal 直接终态，pin 改为三段堆叠，导航不隐藏
- 移动端：390px 无横向溢出；触控目标 ≥44px。

## 验证

```bash
node ../../../../../scripts/verify_motion.mjs --component .
```

## 限制

- pin 段落只有 3 个 beat，不是完整叙事
- accordion 用 button + grid rows，不是原生 details
