# 02 边界场景

`fixture.html` 覆盖四个边界：

- 色板展示页（合法突破四色上限，`data-palette-ok` 豁免）；
- `.sun--outline`（v1 会多出一个方框）；
- 1.9fr 首栏（`BALANCE` 下限）；
- 真正单行的正文 + 竖排标签（v2 的 `wrap` 与竖排高度缺陷）。

## 要验什么

- `.sun--outline` 编译后**不再**派生 4 条 10px 直条。
- `data-test="single-line-body"` 的正文：`wrap=true`、`lines=1`、宽度是排版宽。
- `data-test="vlabel"` 的竖排：`vertical=true` 且 `h > w`（v2 取 `ink.w`，会变成小方块）。
- `data-palette-ok` 真的能豁免 `INK`；1.9fr 首栏不触发 `BALANCE`；validate exit 0。

## 判据

见 `run.mjs` 的 `CASES['02-edge']`。断言绑定到 `data-test` 元素，不是“某处存在”。
