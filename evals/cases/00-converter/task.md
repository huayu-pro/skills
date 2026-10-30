# 00 转换器契约

`fixture.html` 集齐了转换器表达不了的写法，以及两个曾经修过的缺陷：

- 渐变、阴影、滤镜、混合、z-index、fixed、伪元素、嵌套旋转、裁切、内联 SVG、远程图；
- `translate` / `scale` / 偏心 `transform-origin`、非 polygon 裁切、非正圆圆角；
- 竖排标签、真正单行的正文、带旋转的边框、data URI 图片。

## 要验什么

- `build-deck --check` 必须 **exit 1**，在写盘前停住，不留下 `.pptx`。
- 输出逐条列出每个 `FORBID:<id>`；不能只报一部分。
- 不能再出现旧的 `ReferenceError`（`forbidWarn` 作用域 bug）。

## 判据

见 `run.mjs` 的 `CASES['00-converter']`。竖排/单行正文的 spec 断言在 `02-edge`。
