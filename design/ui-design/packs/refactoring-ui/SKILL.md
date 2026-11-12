---
name: ui-refactoring-ui
description: Refactoring UI 规则映射与审计补漏。仅在用户点名或需要规则溯源时加载。
metadata: { version: "5.0.0", source: "edisonmbli/refactoring-ui-skill", license: "MIT-original + book-copyright", parent: "ui-design" }
---

# Refactoring UI Pack

来源：edisonmbli/refactoring-ui-skill，MIT（原创脚本/参考/skill/打包），
Copyright (c) 2026 Edison Li。该仓库是 *Refactoring UI*（Adam Wathan &
Steve Schoger）原则的非官方独立再实现；书本身是独立版权作品，本 pack 不复制书正文、
不声称官方、不替代原书。

## 用法
已有 `references/02`–`08`、`12-audit-rubric.md`、SKILL 的「十二条法则」覆盖大部分规则。
本 pack 只做：

1. 151 条规则到现有 ID 的映射与缺口清单（`coverage-report.md`）。
2. 审计时的第二遍补漏：层级、间距、字阶、颜色、深度、收尾。
3. 发现重复规则时保留现有 ID，不新增平行编号。

冲突时以 `ui-audit` 的 surface profile / appropriateness 为准；书里的通用建议不压过
utility 的得体要求。
