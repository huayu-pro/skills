# 04 失败恢复

`fixture.html` 是一份埋了四个已知错的 deck：

1. 1px 规线（违反规则 4）
2. `.quote-mark` —— deck.css 里不存在的幽灵类
3. 一个内联 `<svg>` 三角形（转换器表达不了）
4. 一段越出画布的正文

## 两种模式

- **pipeline（自动）**：只验**检测**——`validate` 必须 exit 1，并报出 `CLASS` / `WEIGHT` / `FORBID` / `BOUNDS`；不允许 0 页假绿。
- **agent（人工跑）**：agent 把 `fixed.html` 修到 `validate` exit 0，且四类问题真的从源文件里消失，汉字保留率 ≥90%。

## 为什么不自动修

以前用正则自己修一遍再验，测的是“修理工”，不是 agent。v3 把两种模式分开：自动只验检测，修复由 agent 模式验。
