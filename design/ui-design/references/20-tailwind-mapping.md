# Tailwind 映射

> 把规则层的原则翻成 Tailwind v3 / v4 的具体类。默认刻度与教材一致，所以路径很短。

## 版本差异（先确认）

| | v3 | v4 |
|---|---|---|
| 声明主题 | `tailwind.config.js` | CSS 里 `@theme { }` |
| 引入 | `@tailwind base; @tailwind components; @tailwind utilities;` | `@import "tailwindcss";` |
| 自定义色 | `theme.extend.colors` | `@theme { --color-*: ... }` |
| 任意值 | `p-[13px]` | 同样支持，同样不推荐 |

探测方法：`package.json` 里的版本，再看全局 CSS 是 `@import "tailwindcss"` 还是 `@tailwind base`。

## 间距

教材刻度 = Tailwind 默认刻度（4px 基准）：

| px | 类 | 用途 |
|---|---|---|
| 4 | `1` | 图标与文字之间 |
| 8 | `2` | 紧凑元素内 |
| 12 | `3` | 小间隙 |
| 16 | `4` | 字段内、卡片内紧凑 |
| 24 | `6` | 卡片内边距、组内 |
| 32 | `8` | 卡片内边距（宽） |
| 48 | `12` | 组间（小） |
| 64 | `16` | 区块内边距（移动） |
| 96 | `24` | 区块内边距（桌面） |
| 128 | `32` | 大区块 |

**禁止** `p-[13px]`、`gap-[18px]` 这类任意值。需要非刻度值时先问「是不是刻度选错了」。

**用 `gap-*` 不用 `space-*`**：

```jsx
<div className="flex flex-col gap-4">   // 对
<div className="space-y-4">             // 错
```

`space-*` 用 margin 实现，会在最后一个子元素上留尾距，且与 `flex-wrap` 交互差。

## 排版

| 规则 | 类 |
|---|---|
| 行宽 45–75ch | `max-w-prose`（65ch）或 `max-w-[65ch]` |
| 正文行高 | `leading-relaxed`（1.625） |
| 标题行高 | `leading-tight`（1.25）/ `leading-none`（1） |
| 大标题负字距 | `tracking-tight` / `tracking-tighter` |
| 大写标签正字距 | `tracking-wide` / `tracking-wider` |
| 数字对齐 | `tabular-nums` |
| 截断 | `truncate` |

**字阶**：`text-xs/sm/base/lg/xl/2xl/3xl/4xl/5xl` 的默认比值约 1.125–1.2，偏密。需要更清晰层级时用 `text-sm` / `text-base` / `text-xl` / `text-3xl` 跳档，而不是全用。

## 颜色

**用语义 token，不用原始调色板**：

```jsx
<div className="bg-background text-foreground">        // 对
<div className="bg-gray-50 text-gray-900">             // 错（硬编码）
<div className="bg-primary text-primary-foreground">   // 对
<span className="text-emerald-600">+20%</span>         // 错
<Badge variant="secondary">+20%</Badge>                // 对
```

**不要手写 `dark:` 颜色覆盖**——语义 token 已经处理了深浅色：

```jsx
<div className="bg-background text-muted-foreground">  // 对
<div className="bg-white dark:bg-gray-900">            // 错
```

## 深度

| 意图 | 类 | 注意 |
|---|---|---|
| 卡片静止 | `shadow-sm` | 一层就够 |
| 卡片悬停 | `shadow-md` | 过渡 150ms |
| 下拉/浮层 | `shadow-lg` | |
| 模态 | `shadow-xl` 或 `2xl` | 配背景遮罩 |

**不要**给静态卡片用 `shadow-xl`。Tailwind 的 `shadow-xl` 是 `0 20px 25px -5px`，是模态级。

自定义阴影用 `@theme`（v4）或 config（v3）定义成具名 token，不要在组件里写任意 `shadow-[...]`。

## 圆角

| 类 | px | 用途 |
|---|---|---|
| `rounded-sm` | 2 | 徽章 |
| `rounded` | 4 | 输入、小按钮 |
| `rounded-md` | 6 | 按钮、卡片（紧凑） |
| `rounded-lg` | 8 | 卡片、面板 |
| `rounded-xl` | 12 | 大卡片、模态 |
| `rounded-2xl` | 16 | 营销卡片 |
| `rounded-full` | — | 头像、pill 按钮 |

**同一层级用同一个圆角**。卡片 16px 配按钮 4px 会失衡。

## 响应式

断点默认：`sm 640 / md 768 / lg 1024 / xl 1280 / 2xl 1536`。

**从内容出发设断点**：布局在哪个宽度坏掉，哪里就是断点。不要机械地用 `md:`。

```jsx
// 移动优先
<div className="grid grid-cols-1 gap-4 md:grid-cols-2 lg:grid-cols-3">
```

**必须验证**：320 / 375 / 768 / 1024 / 1280 / 1440 下 `document.documentElement.scrollWidth === window.innerWidth`。

## 容器

```jsx
<div className="mx-auto w-full max-w-6xl px-5 sm:px-8">
```

`max-w-6xl` = 72rem = 1152px，是常见的营销容器宽度。数据密集的界面用 `max-w-7xl` 或全宽 + 内边距。

## 常见反模式

| 反模式 | 为什么错 | 改成 |
|---|---|---|
| `space-y-*` | 尾距 + flex 交互差 | `flex flex-col gap-*` |
| `w-10 h-10` | 冗余 | `size-10` |
| `p-[13px]` | 破坏刻度 | `p-3` 或 `p-4` |
| `text-gray-500` | 硬编码 | `text-muted-foreground` |
| `dark:bg-gray-900` | 绕过 token | `bg-background` |
| `shadow-xl` 在静态卡 | 模态级阴影 | `shadow-sm` |
| 组件内 `w-4 h-4` 图标 | 组件自己管尺寸 | `data-icon` |
| `overflow-hidden text-ellipsis whitespace-nowrap` | 冗余 | `truncate` |
| 手写 `z-50` 给浮层 | 组件自己管 | 删掉 |

## 与组件库配合

用 shadcn/ui 时，`className` 只做**布局**，不改颜色和字体：

```jsx
<Card className="p-6">              // 对：布局
<Card className="bg-blue-500">      // 错：覆盖主题
```

改颜色走 `variant` 或改 `cva` 定义。详见 `15-stack-shadcn.md`。

## 与其他章节的接口

- 刻度来源：`03-layout-spacing.md` §3.2、`04-typography.md` §4.1
- 颜色系统：`05-color.md`
- shadcn 规则：`15-stack-shadcn.md`
