# 05 交付验收

给一份**已经合规**的 deck.html，只要求“编译并交付”。

## 要验什么

- `render --sheet` 真的生成了逐页 PNG + **新鲜**联系表（mtime 不早于 deck）。
- 预览张数 **等于** pptx 页数，不是“≥10 张”。
- pptx 体积合理（≤1.5MB，防止全页截图蒙混）；文字仍是原生 `<a:t>`。
- `verify-render` 每页 ≤12%；没装 LibreOffice 标 `skipped`，**不标 pass**。
- 回复里说清三件事：哪些可编辑、哪些是图、字体提示。

## 判据

见 `run.mjs` 的 `CASES['05-delivery']`。预览目录在 case 自己的 `runs/05-delivery/preview`，不覆盖仓库资产。
