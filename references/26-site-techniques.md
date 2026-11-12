# 26 · 手法演示索引（26 demo + 2 索引页）

> 26 个单手法 demo + 2 个索引页已收进 `assets/site-techniques.html`：左侧选 demo，右侧 iframe 运行；下表文件名就是 viewer 里的 demo id。
> 它们不是模板，是「这个效果到底怎么实现、什么时候会失败」的对照件。
> 打开页面看源码；每页顶部有机制说明与来源注记。

## 布局 / 比例

| 页 | 证明什么 | 什么时候用 | 失败模式 |
|---|---|---|---|
| `02-ratio-lock.html` | 按原始比例锁高，且不超过视口 | 图片/视频 hero、作品集 | 只写 `aspect-ratio` 不写 `max-height`，长图把首屏顶走 |
| `08-contain.html` | `contain` 隔离固定背景层 | 长页里的固定纹理/背景 | 用 `background-attachment: fixed`，移动端直接失效/卡 |
| `09-curve-tail.html` | 页脚弧线收尾 | 想要「结束感」的长页 | 弧线用图片/SVG 贴上去，宽度不随视口 |
| `12-page-horizontal.html` | 整页横向布局 + 移动端回退 | 横向叙事、作品集 | 只做横向，390px 直接溢出；无键盘/滚轮回退 |
| `21-subgrid-timeline.html` | `subgrid` 对齐时间轴 | 时间线、步骤、日程 | 用 flex 手工对齐，列一多就漂 |

## 滚动 / 动效

| 页 | 证明什么 | 什么时候用 | 失败模式 |
|---|---|---|---|
| `03-scroll-driven.html` | 纯 CSS 滚动驱动动画 | 进度条、视差、reveal | 用 JS 每帧写 `scrollTop`；无 reduced-motion |
| `14-stacked-panels.html` | sticky 叠层 | 分段叙事、卡片堆 | 每层都 sticky，滚动长度失控 |
| `17-shimmer-text.html` | 文字扫光 | 加载/强调（一次） | 常驻扫光，抢阅读 |
| `19-view-transitions.html` | 同页视图过渡 | 列表→详情、主题切换 | 跨页滥用；无 `prefers-reduced-motion` |
| `23-marquee.html` | 无缝跑马灯 | logo 墙、ticker | 内容不复制两份，接缝跳；无 hover 暂停 |
| `24-conic-gradient.html` | 旋转描边 | 加载环、状态环 | 用 `border` + rotate 假描边，形状会抖 |

## 字体

| 页 | 证明什么 | 什么时候用 | 失败模式 |
|---|---|---|---|
| `10-variable-width.html` | 宽度轴先探测再决定 | 可变字体的窄/宽标题 | 字体没有 `wdth` 轴，`font-stretch` 是 no-op；页面内置探测（50/75/100/150% 宽度相同即无轴） |
| `13-nav-oversized.html` | 整屏大字导航 | 工作室/作品集 | 大字导航挡住内容；键盘不可达 |
| `15-outline-text.html` | `text-stroke` 镂空大字 | 海报式标题 | 细字重 + 描边 = 糊；打印不可读 |
| `16-gradient-text.html` | `background-clip:text` 渐变字 | 一个强调标题 | 对比度不足；每个标题都用 |
| `25-fluid-clamp.html` | `clamp()` 流式字/距 | 全站响应式 | 每个值都 clamp，失去节奏；相邻档 <1.2 |

## 表面 / 图像

| 页 | 证明什么 | 什么时候用 | 失败模式 |
|---|---|---|---|
| `01-mask-fade.html` | 底部渐隐遮罩 | 图片隧道、长列表 | 遮罩盖住可点击元素；对比度不足 |
| `04-fixed-gradient.html` | 固定渐变（不用 `background-attachment`） | 全屏背景 | 移动端 fixed 失效；渐变跨色相太多 |
| `06-glass.html` | 毛玻璃导航 + 降级 | 浮层导航 | 无 `backdrop-filter` 回退；文字对比度不足 |
| `11-blend-cursor.html` | `mix-blend-mode` 自绘光标 | 创意站点 | 触屏无光标；对比度随背景翻转失效 |
| `18-feed-fade.html` | 列表两端渐隐且按需 | 横向列表、feed | 两端都盖，首尾内容不可读 |
| `26-pixel-art.html` | 像素图整数放大不糊 | 像素/复古题材 | `image-rendering` 缺失；非整数缩放 |

## 交互 / 组件

| 页 | 证明什么 | 什么时候用 | 失败模式 |
|---|---|---|---|
| `05-horizontal-reel.html` | 可访问的横向轨道 | 卡片轨道、作品集 | 只支持拖拽，无键盘/滚轮 |
| `07-doppelganger.html` | `clip-path` 展开的重影按钮 | 一个主 CTA | 每个按钮都用；展开方向与点击点无关 |
| `20-container-queries.html` | 组件按容器宽度自己排 | 卡片/侧栏组件 | 用 viewport 媒体查询写组件，复用即坏 |
| `22-has-states.html` | `:has()` 三段用法 | 表单/列表状态 | 依赖 JS 加 class；浏览器不支持时无回退 |

## 索引页

- `index-batch1.html`、`index-batch2.html`：按批次列出全部 demo，带一句说明。

## 怎么用

1. 先确定你要的是**布局/动效/字体/表面/交互**中的哪一类。
2. 只打开 1–2 个相关 demo，读源码，不要整包浏览。
3. 抄的是**机制**（选择器、属性组合、降级），不是具体色值/文案。
4. 每个 demo 都有失败模式；先读那一列，再决定用不用。
5. 用了哪个 demo，在交付说明里写页码与改动点。

> 这些 demo 来自对真实站点的观察与重写，不包含原站图片/字体/视频。
> 统一去掉了来源 URL；需要追溯时看 构建记录 `SOURCE-LEDGER` 与 `ATTRIBUTION.md`。