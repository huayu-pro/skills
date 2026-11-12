---
name: ui-design-md
description: DESIGN.md 双层结构、lint/diff/export 与品牌设计语言路由。仅在用户点名 DESIGN.md 时加载。
metadata: { version: "5.0.0", source: "VoltAgent/awesome-design-md", license: "MIT", parent: "ui-design" }
---

# DESIGN.md Pack

来源：google-labs-code/design.md 工作流与 VoltAgent/awesome-design-md（MIT）。
已有 `assets/brands.json` 的 84 份品牌文档仍复用，不重复打包品牌目录。

## 结构
YAML front matter 给精确 token；Markdown body 给设计意图。
prose 比 token 更重要：一个具体参照自带负面约束，比「现代、简洁、高级」有效。

8 个标准 section：Overview / Colors / Typography / Layout / Elevation & Depth /
Shapes / Components / Do's and Don'ts。自定义 section 可保留，但要在 prose 解释。

## 接入
1. `ui-tokens` 生成 token → 写 YAML。
2. 写 prose：题材、反默认、surface profile、motion register、CJK 边界。
3. 可用外部 CLI 时跑 `lint` / `diff` / `export`；没有就把未执行项写 `skipped`。
4. 输出可作为 Tailwind v3/v4、W3C DTCG、CSS 的单一信源。

## 边界
Alpha 格式可能演进；锁定版本。品牌 DESIGN 文档是第三方观察，不是官方规范；
商标/品牌名归各自所有者。商业交付核对商标政策。

template / lint-export 已并入本文件的 Reference 段。许可见 `NOTICE`。


---

## Reference: template

# DESIGN.md minimal template

```md
---
name: <project>
colors:
  primary: "#1A1C1E"
  secondary: "#6C7278"
  tertiary: "#B8422E"
typography:
  body-md: { fontFamily: "Noto Sans CJK SC", fontSize: 16px }
motion:
  register: utility
  dur-short: 180ms
  attention: 0
---

## Overview
一个 <题材/受众/主任务> 的 <surface profile>。得体优先于独特。
参考 <具体参照>，不要 <明确负面约束>。

## Colors
- **Primary (#…):** <只写职责，不写情绪>
- **Surface:** <与中性色的关系>

## Typography / Layout / Elevation & Depth / Shapes
<每个选择写来自哪个题材事实；CJK 见 references/29>

## Components
<状态、空/错/载、键盘焦点，不复制品牌组件>

## Do's and Don'ts
- Do: <让设计属于本项目的做法>
- Don't: <本项目最常见的 AI 默认>
```

自定义 token 必须在 prose 解释；AI 看不懂的名字等于没有约束。


---

## Reference: lint-export

# lint / diff / export（外部 CLI 可选）

```bash
npx @google/design.md lint DESIGN.md
npx @google/design.md diff DESIGN.md DESIGN-v2.md
npx @google/design.md export --format json-tailwind DESIGN.md > tailwind.theme.json
npx @google/design.md export --format css-tailwind DESIGN.md > theme.css
npx @google/design.md export --format dtcg DESIGN.md > tokens.json
```

- 没有网络/CLI：用仓库内 `check_contrast.py` + 人工 prose 检查，并写
  `skipped: designmd CLI unavailable`。
- CI：lint + diff；新增 error/warning 时 fail。
- Windows PowerShell 用别名 `designmd` 规避 `.md` 包名冲突。
- Alpha 阶段锁版本；不保证向后兼容。
