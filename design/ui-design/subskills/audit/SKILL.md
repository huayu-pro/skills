---
name: ui-audit
description: 七镜、加权 rubric、compliance/quality/appropriateness 三层报告、provenance、self-review 闭环。
metadata: { version: "5.0.0", parent: "ui-design" }
---

# UI Audit

七镜顺序固定：层级 → 布局/间距 → 排版 → 配色 → 深度 → 图像 → 收尾。
先按 `surface profile` 选权重（`references/12-audit-rubric.md`），再评分。
utility 里「克制 25 + 完成度 35」优先于「题材扎根/物理关系」；不要把得体的安静判低分。

报告：

```markdown
Profile: <expressive|product|utility|editorial|catalog>
Compliance: static / runtime / a11y / skipped
Quality: 6 dimensions, weighted score, evidence frames/trace
Appropriateness: why this level of boldness fits this surface
Provenance: MIT / OPL-derived / brand docs / third-party packs
Accepted: <yes|no|conditional>
Skipped: <item> — <reason>
```

裁决顺序：用户指令 > 人工质量评审 > 运行时 > 静态。`audit.py` 全绿不能压过
quality fail；`quality-bad-compliant.html` 就是必红的反例。

```bash
python3 -I scripts/audit.py <file> --json
python3 -I scripts/check_motion.py <file> --json
node scripts/verify_motion.mjs --url <real-page> --trace
```

补漏时读 `packs/refactoring-ui`；生成/验收 DESIGN.md 时读 `packs/design-md`。
商业交付逐项核对 `NOTICE` / `ATTRIBUTION.md`，尤其 OPL 派生、品牌文档与自定义许可 packs。
