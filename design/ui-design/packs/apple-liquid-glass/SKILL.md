---
name: ui-apple-liquid-glass
description: Apple Liquid Glass 视觉语言：统一表面、受控玻璃、灰度层级、单一强调色。仅在用户点名 Apple/Liquid Glass 时加载。
metadata: { version: "5.0.0", source: "naplesblue/apple-design-skill", license: "MIT + Lucide ISC + emilkowalski MIT", parent: "ui-design" }
---

# Apple Liquid Glass Pack

来源：naplesblue/apple-design-skill，MIT，Copyright (c) 2026 naplesblue；
`motion.md` 改编自 emilkowalski/skills（MIT，Copyright (c) 2026 Emil Kowalski）；
line-icon SVG 来源于 Lucide（ISC，Copyright (c) 2022 Lucide Contributors）。
只提炼规则，不复制 examples 截图、品牌图标或整仓文件。

## 规则

1. **统一表面 > 碎片卡片**：兄弟项放同一白色面板，用 hairline 分隔；碎片化是首敌。
2. **玻璃只用于真正重叠层**：sticky nav / modal / 彩色 CTA；普通内容用实色表面。
3. **层级靠 weight + size + grayscale**：正文黑白灰，颜色只留给一个强调蓝。
4. **克制即奢华**：留白与层级先于边框/填充/图标；一个页面一个「yes」。
5. **细节**：标题负字距、hairline、`tabular-nums`、轻微 hover lift、滚动边缘 nav。

## 边界

- 这是可选风格包，不是 ui-design 默认审美；先通过 `surface profile`。
- 玻璃/低对比表面必须给 `prefers-reduced-transparency` 与 `prefers-contrast` 回退。
- 文字对比度按 `check_contrast.py`；不能为了「像苹果」牺牲 WCAG AA。
- 动效仍走核心 motion register/budget，不把 Apple 当豁免。

tokens/patterns/checklist 已并入本文件的 Reference 段；可直接打开 `reference.html`（自包含，含内联 token）。许可见 `NOTICE`。


---

## Reference: patterns

# Patterns（提炼，不复制资产）

## 统一表面
一个页面一个主面板；列表项用 hairline 分隔，不各带边框/阴影/左色条。
例外必须有重叠关系（sticky nav、modal、toolbar）。

## 玻璃
只在背景确实会滚动/透出时使用；`backdrop-filter` 不铺满内容区。
玻璃层必须有不透明回退；文字不直接压在高光/图片上。

## 三种字角色
大标题（负字距、高字重）/ 正文（中性灰阶）/ 标签或数值（tabular-nums）。
颜色不承担层级；一个强调蓝只用于主行动/链接/选中态。

## 页面配方
Account / Settings：统一表面 + 分段列表 + 一个主行动。
Product detail：大标题 + 一张真实图/自绘对象 + 单一强调 CTA。
Nav：滚动到边缘才显 hairline；不在每屏都用毛玻璃。

这些是配方，不是模板；换题材要重新做 `ui-direction` 六步。


---

## Reference: checklist

# Apple Liquid Glass self-review

- [ ] 是用户明确要 Apple/Liquid Glass 吗？不是则不要加载本 pack。
- [ ] surface profile / 对比度 / 动效预算先过了吗？
- [ ] 兄弟项是否在同一表面？有无碎片卡片？
- [ ] 玻璃是否只出现在真实重叠层？reduced-transparency 有回退吗？
- [ ] 正文是否全灰度？强调色是否唯一？
- [ ] 标题负字距、数字 tabular-nums、hairline 是否一致？
- [ ] 删掉一层玻璃/一个边框后是否更好？
- [ ] quality 的「克制/得体」是否有五帧或录屏证据？

fail 不是「不像 Apple」，而是「为了像 Apple 破坏了可读性/得体/克制」。


---

## Reference: tokens

/* Apple Liquid Glass — distilled tokens. Do not apply as global default.
 * Source: naplesblue/apple-design-skill (MIT); adapted, not copied verbatim. */
:root[data-style="apple-liquid-glass"] {
  --al-ground: #f5f5f7;
  --al-surface: #ffffff;
  --al-ink: #1d1d1f;
  --al-muted: #6e6e73;
  --al-hairline: rgba(0, 0, 0, 0.10);
  --al-accent: #0066cc;
  --al-radius-surface: 18px;
  --al-radius-control: 999px;
  --al-shadow-surface: 0 1px 2px rgba(0,0,0,.04), 0 8px 30px rgba(0,0,0,.06);
  --al-glass-bg: rgba(255,255,255,.72);
  --al-glass-blur: saturate(180%) blur(18px);
  --al-title-tracking: -.035em;
  --al-dur-feedback: var(--dur-short, 180ms);
  --al-ease-feedback: var(--ease-move, cubic-bezier(.4,0,.2,1));
}
@media (prefers-reduced-transparency: reduce) {
  :root[data-style="apple-liquid-glass"] {
    --al-glass-bg: var(--al-surface);
    --al-glass-blur: none;
  }
}
@media (prefers-contrast: more) {
  :root[data-style="apple-liquid-glass"] {
    --al-hairline: rgba(0,0,0,.42);
    --al-muted: #3a3a3c;
  }
}
