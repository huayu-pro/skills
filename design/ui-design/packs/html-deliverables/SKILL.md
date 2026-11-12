---
name: ui-html-deliverables
description: HTML 原生高保真原型、幻灯片、动画、信息图与导出流程。仅在用户点名原型/slides/信息图/导出时加载。
metadata: { version: "5.0.0", source: "alchaincyf/huashu-design", license: "MIT", parent: "ui-design" }
---

# HTML Deliverables Pack

来源：alchaincyf/huashu-design 3.0（MIT）。提炼工作流与评审结构，不复制 232MB
资产、原站图片/字体/视频，也不引入原生可编辑 PPTX 工程。

## 何时加载
用户说「高保真原型 / HTML slides / 动画演示 / 信息图 / 导出 MP4 或 GIF / 给老板演示」。
普通页面、设置页、表单、产品页不加载。

## 流程
1. 用 `ui-direction` 定 profile 与题材；deck/原型也不能跳过。
2. 用 `ui-tokens` 定视觉与 motion token；单文件 HTML 可从 `tokens.css` 内联。
3. 每个 screen/slide 写内容分级、主行动、进入/退出状态。
4. 五维专家评审：结构、叙事/信息、视觉、动效/节奏、交付完整性；证据写截图/录屏。
5. 导出按本文件 Reference 的 export 做 dry-run；无工具时写 `skipped`，不声称已导出。

## 边界
- 不做 guizang / PPTX 工程；不复制 AGPL 代码。
- 仍过 `ui-audit` 七镜与 motion budget；幻灯片不是动效豁免。
- 不把参考站的图片、字体、视频、品牌名带进交付物。

workflow/export 已并入本文件的 Reference 段；样例见 `sample.html`（单文件、无外部资产）。许可见 `NOTICE`。


---

## Reference: workflow

# HTML deliverables workflow（提炼）

输入：目标受众、主任务、页数/时长、交付格式、品牌/素材边界。

1. **Brief**：一句话目标 + 三个内容层级 + 一条主线。
2. **Storyboard**：每个 screen/slide 写「唯一主张 / 证据 / 主行动 / 终态」。
3. **Tokens**：颜色、字阶、间距、motion register 全部来自 `ui-tokens`。
4. **Build**：先灰度结构与真实内容，再表面/图像，最后动效；单文件可离线打开。
5. **Review**：结构 → 信息 → 视觉 → 节奏 → 收口，各给一条可指认证据。
6. **Deliver**：HTML + 1280/375 截图 + 3s 录屏（若有动效）+ `skipped` 清单。

## 五维评审表

| 维度 | 问法 | fail 线 |
|---|---|---|
| 结构 | 第一眼是否是唯一主张？ | 等权卡片堆叠 |
| 信息 | 每屏证据是否具体？ | 空泛形容词 |
| 视觉 | 换题材还成立吗？ | 默认模板 |
| 节奏 | attention/ambient/feedback 是否在预算内？ | 每屏淡入 |
| 收口 | 空/错/载、边缘、移动端、reduced 是否完整？ | 只做了首屏 |


---

## Reference: export

# Export dry-run

本 pack 不捆绑 232MB 资产或渲染器。按环境选择：

- HTML：交付单文件，所有资源内联或 data URI；零网络请求检查。
- PNG/JPEG：浏览器截图，分别输出 1280/375；长页用 fullPage，标注 crop。
- WebM/MP4/GIF：仅在有 Playwright/ffmpeg/录屏工具时执行；写命令、时长、帧率。
- 可编辑 PPTX：**不在 v5.0 核心范围**；需要时让用户选择外部工程化工具。

## 必须写进交付说明

`format / dimensions / duration / fps / tool / source / skipped / evidence`。
没有真实渲染就写 `skipped: no renderer`，不能把命令草案写成成品。
