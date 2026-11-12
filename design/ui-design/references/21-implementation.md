# 实现层手法（代码怎么写）

> 这一章回答的是「代码怎么写」，而不是「用什么值」。数据来自对 **286 个站点样式表的直接读取**（CSSOM 逐条规则匹配），不是规范建议，也不是我的偏好。

## 先读这个：三档使用率意味着什么

| 档位 | 含义 | 怎么用 |
|---|---|---|
| **> 50%** | 默认栈。不写就是落后 | 直接采用，不需要理由 |
| **20–50%** | 有区分度。用不用是一种选择 | 按题材决定，不要默认全用 |
| **< 20%** | 少见。用了要么是真需要，要么是炫技 | 用之前问「这个项目真的需要吗」 |

**最大的反直觉发现**：`oklch()` 只有 **6%**、`CSS 嵌套` 只有 **3.5%**、`@container` 只有 **14%**。这三个在技术圈被讨论得最多，但精选站里几乎不用。**不要因为「新」而用。**

---

## 默认栈（过半站点在用）

| 手法 | 占比 | 实现要点 |
|---|---|---|
| `inset` 简写 | **76%** | `inset: 0` 代替 `top/right/bottom/left: 0` |
| `aspect-ratio` | **67%** | 图片、视频、骨架屏必须有，防 CLS |
| `min()` / `max()` | **58%** | 比 `clamp()` 更常用，常配合 `min(100%, 420px)` |
| `will-change` | **58%** | 只加在真正会动的元素上，用完移除 |
| 逻辑属性 | **54%** | `margin-inline` / `padding-block` / `inset-inline-start` |
| `position: sticky` | **54%** | 注意：**57% 的站点一个 sticky 元素都没有**，它不是必需品 |
| `font-variation-settings` | **53%** | 可变字体，`"wght" 400, "wdth" 80` 这种组合 |
| `:focus-visible` | **52%** | 用 `:focus-visible` 而非 `:focus`，避免鼠标点击出环 |
| `filter: blur/drop-shadow` | **52%** | 注意 `drop-shadow` 比 `box-shadow` 更贴合不规则形状 |
| 自定义滚动条 | **50%** | `::-webkit-scrollbar` 或 `scrollbar-width` + `scrollbar-color` |

### 一个真实的 sticky 用法

```css
/* 53% 的站点在用，但只在需要「保持上下文」时 */
.section-header {
  position: sticky;
  top: 0;
  z-index: 10;
  background: var(--surface-page-bg);
  /* 关键：sticky 元素必须有实底，否则滚动时文字压内容 */
}
```

### 逻辑属性的实际写法

```css
/* 53% 的站点在用。直接换掉 left/right 就能自动支持 RTL */
.card {
  padding-inline: 24px;
  padding-block: 16px;
  margin-inline-start: auto;
  inset-inline-end: 0;
}
```

---

## 区分度手法（20–50%）

### 毛玻璃 `backdrop-filter` — 49%

```css
.nav {
  background: color-mix(in oklab, var(--surface) 72%, transparent);
  backdrop-filter: blur(12px) saturate(140%);
  /* 必须有 @supports 兜底，Safari 老版本和部分安卓不支持 */
}
@supports not (backdrop-filter: blur(1px)) {
  .nav { background: var(--surface); }
}
```

### 流式尺寸 `clamp()` — 42%

```css
/* 42% 的站点在用。min()/max() 更常见（58%），因为更可控 */
h1 { font-size: clamp(2rem, 5vw, 4rem); }
.container { padding-inline: clamp(20px, 4vw, 40px); }

/* 更精确的写法：把视口项写成负斜率，让增长刚好在断点处停止 */
h1 { font-size: clamp(2rem, 1rem + 4vw, 4rem); }
```

### 排版细节 `text-wrap` — 40%

```css
h1, h2 { text-wrap: balance; }   /* 标题两行等长，避免孤字 */
p       { text-wrap: pretty; }   /* 正文避免行尾孤字 */
```

### 混合模式 `mix-blend-mode` — 39%

```css
/* 常用于：文字压在图片上、渐变叠加、噪点纹理 */
.overlay-text { mix-blend-mode: difference; color: #fff; }
```

### `mask-image` — 37%

```css
/* 比 overflow 更灵活：渐变淡出、形状裁切 */
.fade-bottom {
  mask-image: linear-gradient(to bottom, #000 70%, transparent 100%);
}
```

### `color-mix()` — 33%

```css
/* 33% 的站点在用。比手动算半透明更好，因为它作用于已解析的颜色 */
.hover-surface { background: color-mix(in oklab, var(--surface), var(--ink) 6%); }
.disabled { color: color-mix(in oklab, var(--ink), transparent 55%); }
```

### `:has()` — 31%

```css
/* 父选择器。常见于表单校验和卡片状态 */
.field:has(input:invalid) { --border-color: var(--danger); }
.card:has(img) { grid-template-rows: 200px 1fr; }
```

### `@layer` — 23%

```css
/* 级联层。只在样式来源复杂（第三方库 + 自己的）时值得 */
@layer reset, base, components, utilities;
@layer components { .btn { ... } }
```

### 计数器 `counter-reset` — 23%

```css
/* 编号列表、目录、步骤。比手写数字更可靠 */
.steps { counter-reset: step; }
.step::before { counter-increment: step; content: counter(step, decimal-leading-zero); }
```

### 描边文字 `-webkit-text-stroke` — 21%

```css
/* 常见于大标题描边风格。注意它只描边不填充 */
.outline-type { -webkit-text-stroke: 1px var(--ink); color: transparent; }
```

---

## 少见但值得知道（< 20%）

| 手法 | 占比 | 什么时候真需要 |
|---|---|---|
| 文字渐变 | 19% | 只有一个强调标题时；不要全站用 |
| `scroll-snap` | 19% | 横向卡片轮播、全屏分页 |
| `env()` 安全区 | 17% | 有刘海/圆角屏的移动端全屏布局 |
| `subgrid` | 16% | 卡片网格需要跨卡片对齐标题/正文 |
| 滚动时间线动画 | 15% | 纯 CSS 滚动驱动，不需要 JS |
| `@container` | 14% | 组件需要在不同容器宽度下变形（**被高估最多**） |
| `interpolate-size` | 11% | `height: auto` 可动画，替代 `grid-template-rows` 技巧 |
| `lab()` / `lch()` | 10% | 需要感知均匀的色彩时 |
| `view-transition` | 9% | 页面间转场，需要 SPA/MPA 支持 |
| CSS 锚点定位 | 8% | 浮层跟随触发元素，不用 JS 算位置 |
| `oklch()` | **6%** | 几乎没人用。**别为了「现代」而用** |
| `grid-template-areas` | 5% | 复杂页面布局可读性更好 |
| CSS 嵌套 `&` | **3.5%** | 最少人用。构建工具已处理，收益低 |

---

## 实测的排版基线

| 指标 | 实测中位 | 我的技能原先写的 | 说明 |
|---|---|---|---|
| 正文计算字号 | **16px** | 16px | 一致 |
| 正文行高比 | **1.50** | 1.5–1.6 | 一致 |
| 首个 h1 计算字号 | **60px** | 未规定 | 新增基线 |
| 每站 CSS 变量数 | **16.5**（IQR 1–92） | 未规定 | 新增基线 |
| grid 容器数 | 中位 4 | 未规定 | 布局以 flex 为主（中位 64） |
| sticky 元素数 | 中位 **0** | 未规定 | 57% 站点完全没有 |

---

## 组件级的实现约定

### 按钮的 slot 与变体（来自 269 个站点的 Component Anatomy）

**Slot 构成**：`label`（248 站）+ `icon`（111 站）+ `badge`（3 站）

**变体命名**（按使用频率）：

| 变体 | 站点数 |
|---|---|
| outline | 43 |
| primary | 31 |
| secondary | 18 |
| link | 17 |
| ghost | 8 |
| tertiary | 3 |
| solid | 2 |

**尺寸档位命名**：`sm`(50) · `medium`(29) · `lg`(29) · `md`(26) · `xs`(11) · `small`(11) · `xl`(9)

> **注意**：`sm/md/lg` 和 `small/medium/large` 并存。选一套，不要混用。`md` 比 `medium` 更常见（26 vs 29 接近，但 Tailwind 生态倾向 `md`）。

### 实测的组件圆角

| 组件 | 圆角中位 | pill 占比 |
|---|---|---|
| button | 3.6px | **20%** |
| card | 4.0px | 7% |
| input | 0px | 7% |
| badge | 0px | 11% |
| switch | 0px | 14% |

**反直觉**：卡片圆角中位只有 **4px**，不是 16px。营销页的 16–24px 圆角是少数派。

### 实测的布局系统

| 指标 | 中位 | IQR |
|---|---|---|
| 内容列宽 | 1024px | 868–1200 |
| 边距 | 29px | 24–35 |
| 区块垂直内边距 | 60px | 38–112 |
| 每站 clamp 声明数 | 4 | 2–12 |

**真实 grid 模板**（数值归一为 1fr 后）：

| 模板 | gap | 出现 |
|---|---|---|
| `1fr 1fr` | 64px | 25 |
| `1fr 1fr` | 20px | 21 |
| `1fr 1fr` | 40px | 19 |
| `1fr 1fr 1fr` | 24px | 16 |
| `1fr 1fr 1fr` | 20px | 16 |
| 12×`1fr` | 24px | 16 |

**两列是主流**，不是三列或四列。gap 用 20–64px，不是统一的 16px。

---

## CSS 变量的命名约定

前缀使用频次（19001 次 `--color-` 等）：

| 前缀 | 次数 | 用法 |
|---|---|---|
| `--color-` | 19001 | 颜色，最常见 |
| `--font-` | 5796 | 字体族 |
| `--spacing-` | 4022 | 间距 |
| `--text-` | 1940 | 字号 |
| `--radius-` | 1878 | 圆角 |
| `--surface-` | 1424 | 表面（语义层） |
| `--action-` | 1256 | 动作（语义层） |
| `--container-` | 867 | 容器宽度 |
| `--shadow-` | 614 | 阴影 |

**最常出现的具体变量名**：

```
--color-neutral-50 … --color-neutral-900   （完整 10 档灰阶，最普遍）
--radius-full                               （605 次，pill 圆角）
--color-text / --color-bg                   （语义层，非数字）
--surface-page-bg / --surface-page-fg       （page 级语义对）
--color-text-1 / --color-text-2             （文字分级）
--color-primary / --color-primary-50        （主色 + 色阶）
--font-sans
```

**可直接采用的命名模式**：

```css
:root {
  /* 1. 原始色阶：完整 10 档，命名固定 */
  --color-neutral-50: …;  … --color-neutral-900: …;
  --color-primary-50: …;  … --color-primary-900: …;

  /* 2. 语义层：引用原始色阶，不写死 hex */
  --color-text: var(--color-neutral-900);
  --color-text-1: var(--color-neutral-900);
  --color-text-2: var(--color-neutral-600);
  --color-bg: var(--color-neutral-50);

  /* 3. page 级语义对：成对定义，便于整体换肤 */
  --surface-page-bg: var(--color-neutral-50);
  --surface-page-fg: var(--color-neutral-900);

  /* 4. 动作层 */
  --action-primary: var(--color-primary-600);
  --action-primary-hover: var(--color-primary-700);

  /* 5. 形状与阴影 */
  --radius-sm: 4px;  --radius-md: 8px;  --radius-full: 9999px;
  --shadow-sm: …;    --shadow-lg: …;
}
```

---

## 动效的实现

**时长预设**（跨 405 个站点的 WAAPI 生成文件统计）：

| 值 | 出现 |
|---|---|
| 300ms | 173 |
| 200ms | 145 |
| 500ms | 91 |
| 150ms | 81 |
| 100ms | 73 |
| 800ms | 38 |
| 160ms | 36 |

**结论**：`100/150/200/300/500` 是实际在用的五个值。`300ms` 是最常见的单值。

**缓动曲线**（按使用频次）：

| 曲线 | 出现 |
|---|---|
| `cubic-bezier(0.25, 0.1, 0.25, 1)` | 132 |
| `cubic-bezier(0.4, 0, 0.2, 1)` | 110 |
| `cubic-bezier(0, 0, 0.2, 1)` | 28 |
| `cubic-bezier(0.16, 1, 0.3, 1)` | 23 |
| `cubic-bezier(0.22, 1, 0.36, 1)` | 23 |
| `cubic-bezier(0.34, 1.56, 0.64, 1)` | 14 |

**可直接采用**：

```css
:root {
  --duration-xs: 100ms;
  --duration-sm: 150ms;
  --duration-md: 200ms;
  --duration-lg: 300ms;
  --duration-xl: 500ms;

  --ease-out: cubic-bezier(0, 0, 0.2, 1);        /* 进入 */
  --ease-in-out: cubic-bezier(0.4, 0, 0.2, 1);   /* 位移 */
  --ease-spring: cubic-bezier(0.34, 1.56, 0.64, 1); /* 落地感 */
}
```

**五个基础动画原语**（405 个站点的生成文件里，每一个都出现了 405 次）：

```js
// 只动 transform 和 opacity，不触发重排
fadeIn    : [{ opacity: 0 }, { opacity: 1 }]
fadeOut   : [{ opacity: 1 }, { opacity: 0 }]
slideUp   : [{ opacity: 0, transform: 'translateY(16px)' }, { opacity: 1, transform: 'translateY(0)' }]
slideDown : [{ opacity: 0, transform: 'translateY(-16px)' }, { opacity: 1, transform: 'translateY(0)' }]
scaleIn   : [{ opacity: 0, transform: 'scale(0.96)' }, { opacity: 1, transform: 'scale(1)' }]
```

位移距离统一是 **16px**，缩放统一是 **0.96**——这是真实站点里最普遍的进入参数。

**必须的处理**：

```js
const prefersReducedMotion = () =>
  matchMedia('(prefers-reduced-motion: reduce)').matches;
// 命中时把 duration 设为 0，而不是不执行动画
if (prefersReducedMotion()) timing.duration = 0;
```

---

## 怎么用这一章

1. **写之前**：`> 50%` 的那一列是默认栈，直接照做。`< 20%` 的那一列不要主动引入。
2. **布局**：先两列（主流），gap 从 20/24/40/64 里选，不要一律 16px。
3. **组件**：按钮圆角 4–8px 是主流，pill 只占 20%。卡片圆角中位 4px，不是 16px。
4. **变量**：照上面的五层命名写，`--color-*` 用完整 10 档。
5. **动效**：五个时长值 + 三条缓动曲线 + 五个原语，够用。位移 16px，缩放 0.96。

## 数据来源与限制

- 使用率：`corpus/css_techniques.json`，286 个站点成功读取 CSSOM（343 个有 URL 的站点中 83%）。
- 组件/布局/动效：`corpus/techniques.json`，405 个站点的 designlang 报告。
- **限制**：这版数据来自 CSSOM（同源）。跨域 CDN 样式读不到会让使用率偏低——后续用网络层补测了 **119/343 个站点有跨域 CSS**，完整数据见 `22-motion-implementation.md` 和 `corpus/deep.json`。`@layer` 内的规则已递归展开，`@media`/`@supports` 的 prelude 单独收集。
- **样本偏向**：One Page Love 是单页营销站策展，后台/数据密集界面的实现手法不在这个分布里。
