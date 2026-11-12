# 29 · CJK 排版与移动端动效人格

> 现有语料 302 个 One Page Love 站点与 84 份品牌 DESIGN 文档高度偏向拉丁语、
> 桌面鼠标与作品集，不足以代表 CJK、utility 或移动端。本章补的是边界，不是新普适风格。

## CJK

- 回退栈按平台显式写：PingFang SC / Noto Sans CJK SC / Source Han Sans SC /
  Microsoft YaHei；衬线同理。`font-display` 与中文子集要避免 FOIT。
- 中西混排：基线、标点、空隙用 `text-spacing-trim` / `text-autospace` 渐进增强；
  不把英文负字距套到汉字。
- 行高 1.7–1.9；正文 30–45 汉字/行；标点挤压、避头尾、字重降一档。
- `font-variation-settings` 的中文 `wdth` 轴先测再声称；同串 50%/150% 宽度相同即无该轴。
- 数字、金额、日期用 `tabular-nums`；竖排 `writing-mode` 只在真实编辑场景启用。

## 移动端

- 375 不是缩小版桌面：重新定列、触控目标 ≥44×44、safe-area、无孤立单字。
- iOS 边缘返回、长按、触觉反馈、系统滚动惯性优先；自定义摩擦只在明确叙事机制里叠加。
- Android predictive back 与系统返回不能劫持；横向轨道用 `overflow-x: clip`。
- 120Hz / 30fps 低端机都要看；headless 帧率不是真机性能。
- 触屏无 hover：核心信息 pointerdown 前可见；自定义光标只在 `pointer:fine` 启用。

## 证据边界

在报告里写 `corpus: latin-desktop-portfolio-biased`。CJK 与移动端的结论若来自
实测标 `observed`；来自规范推断标 `inferred`；不要借用 302 站点替它们背书。
