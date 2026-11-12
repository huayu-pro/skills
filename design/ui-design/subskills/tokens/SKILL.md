---
name: ui-tokens
description: 设计系统、色阶、对比度、字阶、间距、motion token、DESIGN.md 与既有系统适配。
metadata: { version: "5.0.0", parent: "ui-design" }
---

# UI Tokens

既有设计系统优先。没有系统时产出五件套：`design-tokens.json`、Tailwind 主题块、
`tokens.css`、人读 `DESIGN`、`preview.html`；色阶用 `generate_palette.py`，
每个前景/背景对用 `check_contrast.py` 算复合对比度。

```bash
python3 -I scripts/generate_palette.py --base "#0f766e" --name brand --json
python3 -I scripts/check_contrast.py --matrix tokens.json
python3 -I scripts/emit_tokens.py --motion-profile utility --format css
```

动效与视觉同属 token：时长、缓动、位移、stagger、spring 参数都在
`assets/tokens/tokens.template.json` / `theme.template.css`。三套 register：
`expressive` / `product` / `utility`。不得在组件里裸写 450ms、16px、
`cubic-bezier(0,0,.2,1)`；它们是观测值，不是默认值。

`DESIGN.md` 是可选输出，不是新体系：YAML token + prose，读
`packs/design-md/SKILL.md`；lint/export 无 CLI 时写 `skipped`。
Refactoring UI 规则映射只在补漏时读 `packs/refactoring-ui/SKILL.md`。
三库（shadcn/HeroUI/Mantine）按用户点名读 `references/18` → `15/16/17`；
不进入审美/动效默认路径。
