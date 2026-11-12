# 无障碍

> 教材仅零散涉及，本文件合并 WCAG 2.2 AA 的必需项与组件库实践。

## 定位

无障碍不是「额外工作」，它是**界面是否可用**的一部分。绝大多数无障碍缺陷同时也是普通用户的缺陷：对比度低的人在阳光下看不清、键盘用户是重度效率用户、目标太小在高 DPI 触屏上人人难按。

## §10.1 对比度（数值门槛）

> **扩展章节**：原书没有第 10 章。本文件的 §10.x 编号是本 skill 自建的，
> 便于审计时引用；对比度的原则出处是原书 §5.6。

| 内容 | AA 最低 | AAA |
|---|---|---|
| 正文 < 18.66px / 粗体 < 24px | 4.5:1 | 7:1 |
| 大文本 ≥ 18.66px / 粗体 ≥ 24px | 3:1 | 4.5:1 |
| 图标、边框、图形 | 3:1 | 4.5:1 |
| 焦点指示 | 3:1（对相邻色） | — |
| 禁用态 | 无要求，但应可辨识 | — |

**必须算复合后的颜色**：`opacity`、`rgba`、`backdrop-filter` 都会改变实际渲染色。RED 基线中一个 `opacity: 0.45` 的按钮实际对比度是 1.33:1，源码里写的是 `#111`。

用 `scripts/check_contrast.py` 批量算。

## §10.2 键盘可达

- 所有交互元素必须可达（`Tab`）且可操作（`Enter`/`Space`/方向键）。
- 焦点顺序必须与视觉顺序一致（不要用 `tabindex` 正数）。
- 焦点必须**可见**，见 §10.4。
- 模态必须**困住焦点**（focus trap），`Esc` 关闭，关闭后焦点回到触发元素。
- 不要用 `<div onclick>`。用 `<button>` / `<a>`，或补 `role` + `tabindex` + 键处理（三者缺一不可）。

**RED 基线中的 P0**：页面上可聚焦元素数量为 0。用户无法离开这个页面。

## §10.3 语义结构

- 一个页面一个 `<h1>`，标题层级不跳级。
- 用 `<nav>` `<main>` `<aside>` `<footer>` 划分区域，并给 `<nav>` 加 `aria-label`。
- 表格用 `<table>` + `<thead>` + `<th scope>`，不要用 div 拼。
- 表单每个输入必须有 `<label for>` 或 `aria-label`。
- 图像：内容图给 `alt`（描述信息，不是描述图像），装饰图给 `alt=""`。
- 图标按钮必须有 `aria-label`。
- 模态必须有标题（`DialogTitle`），视觉隐藏时用 `sr-only`。

## §10.4 焦点环

```css
:focus-visible {
  outline: 2px solid var(--focus-ring);
  outline-offset: 2px;
}
```

- 用 `:focus-visible` 而不是 `:focus`（避免鼠标点击时出现环）。
- 焦点环与相邻颜色的对比 ≥ 3:1。
- **不要 `outline: none` 而不提供替代**。
- 焦点环在深色和浅色背景上都要可见（可以用双层环：内白外深）。

## §10.5 目标尺寸

- 触控目标最小 **24×24 CSS px**（WCAG 2.2 AA），推荐 **44×44**。
- 相邻目标之间至少 8px 间距（或目标本身足够大）。
- 小图标按钮（如关闭 ×）必须扩大点击区：`padding` 或用伪元素扩展。

## §10.6 表单

- 错误信息必须**关联**到字段：`aria-describedby` 指向错误文本。
- 无效状态用 `aria-invalid="true"` + 视觉标记（不只是红边框）。
- 必填字段用 `required` + 视觉标记，并在说明里解释标记含义。
- 不要用 `placeholder` 代替 label（placeholder 会消失）。
- 自动填充要支持：`autocomplete` 属性写对。
- 错误提示在提交后**聚焦到第一个错误字段**。

## §10.7 动态内容

- 异步更新的区域用 `aria-live="polite"`（重要但不打断）或 `"assertive"`（紧急）。
- Toast 必须是 `role="status"` 或 `role="alert"`。
- 加载状态用 `aria-busy="true"`。
- 展开/收起用 `aria-expanded`。
- 选中态用 `aria-selected` / `aria-checked` / `aria-pressed`，与视觉状态同步。

## §10.8 动效与闪烁

- 见 `09-motion-principles.md`：必须尊重 `prefers-reduced-motion`。
- 不要有每秒闪烁超过 3 次的内容。
- 自动播放的轮播必须可暂停。

## §10.9 语言与方向

- `<html lang="zh-CN">`（或实际语言）。
- 混排段落用 `lang` 标注（如英文术语）。
- RTL 支持用逻辑属性：`margin-inline-start` 而不是 `margin-left`。

## 快速自检

用键盘走一遍，不看鼠标：

1. 能不能 Tab 到每个交互元素？
2. 焦点环看不看得见？
3. 模态打开后焦点是否进入、`Esc` 是否关闭、关闭后是否回到原处？
4. 每个输入有没有 label？错误有没有关联？
5. 所有文字对比度是否算过？
6. 触控目标是否 ≥ 24px（推荐 44px）？

## 与其他章节的接口

- 对比度计算：`05-color.md` §5.7
- 动效偏好：`09-motion-principles.md`
- 组件库的无障碍约定：`15-stack-shadcn.md`、`16-stack-heroui.md`、`17-stack-mantine.md`
- 审计中的无障碍检查项：`12-audit-rubric.md`
