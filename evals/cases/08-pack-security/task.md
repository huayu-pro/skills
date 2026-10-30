# 08 打包安全

`pack-html.mjs` 把 deck 引用的 CSS/图片内联成自包含 HTML。它必须只读“资源类文件”，不能因为路径被引用就去读凭据目录或任意文件。

## 要验什么

- 非图片/字体/样式扩展名（如 `asset.xyz`）被拒绝，dry-run exit 1，不写盘。
- 隐藏路径段（如 `.hidden/asset.png`）被拒绝。
- 输入不是 `.html/.htm` 时 exit 2，不读取其他类型文件。
- 正常 deck（`examples/structured.html`）的 dry-run 通过。
- 失败时错误信息说明白名单/隐藏路径原因，不输出被引用文件的内容。

## 判据

见 `run.mjs` 的 `CASES['08-pack-security']`。测试文件在运行时生成，不进仓库。
