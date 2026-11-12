# ASCII 图表模块（终端字符图 + HTML 交互图表双引擎）

图表模块分两个引擎，**共用同一份数据 JSON**：
- **终端引擎**：纯字符输出（柱/线/饼/甘特/流程图等），见 §A。用于终端、日志、文档。
- **HTML 交互引擎**：Canvas/DOM 渲染的完整交互图表系统，见 §B–§H。用于网页、大屏、报告。

用户说"图表/可视化/大屏"默认走 HTML 引擎；说"终端/纯文本/markdown 里嵌"走终端引擎。不确定时在 §0 提问环节确认。

---

## §A 终端字符图引擎（纯文本输出）

**模式选择**：
- **ASCII-safe**（默认）：只用 32–126——`+ - | [ ] < > v ^ * #`。聊天/README/窄屏必须走这档。
- **Unicode**（受控环境）：box-drawing `┌─┐├┤` + 方块 `█▁▂▃▄▅▆▇` + 箭头 `→←▲▼`。

**缩放内核**（所有统计图共用）：

```js
// tick 取"整数友好"值（1/2/5×10^n 序列），避免 3.7 这种丑刻度
function niceCeil(v) {
  if (v <= 0) return 0;
  const pow = Math.pow(10, Math.floor(Math.log10(v)));
  const n = v / pow;
  return (n <= 1 ? 1 : n <= 2 ? 2 : n <= 5 ? 5 : 10) * pow;
}
function scale(values, rows) {
  const max = Math.max(...values), min = Math.min(0, ...values);
  const niceMax = niceCeil(max);
  return values.map(v => Math.round((v - min) / (niceMax - min) * rows * 8) / 8); // 1/8 精度给尾块
}
function bar(len) {                       // 垂直条形图；水平用 ▏▎▍▌▋▊▉
  const EIGHTHS = ' ▁▂▃▄▅▆▇';
  return '█'.repeat(Math.floor(len)) + EIGHTHS[Math.round((len % 1) * 8)];
}
```

**流程图手绘范式**：主线垂直走到底；分支 `+-->` 侧出；节点文字短而动词化；回环线非必要不画。

**成熟库速查**：`chartscii`（npm，柱/线/K线/动画）、`termatplotlib`（PyPI，28 种含甘特/雷达/词云）、`termplotx`（PyPI，盲文折线）、`termaid`（PyPI，Mermaid 18 类图）。

**终端质量红线**：轴有刻度单位；关键数值直接标注；多序列有图例；饼图 <5% 扇区标数字；目标环境实看一眼，对齐崩了退回 ASCII-safe。

---

## §B HTML 图表引擎架构

三层分离，任何一层可独立替换：

```
┌─────────────────────────────────────────┐
│  交互层  悬停/点击/播放条/图例联动/提示框   │  §D
├─────────────────────────────────────────┤
│  渲染层  Canvas 2D 逐帧绘制（默认）        │  §C 各图表内核
│         （字符美学：等宽字体 + §4 排版 CSS）│
├─────────────────────────────────────────┤
│  数据层  统一数据契约 + 变换管道           │  本节
└─────────────────────────────────────────┘
```

**统一数据契约**（所有图表、所有引擎的输入）：

```jsonc
// data.json —— 三端（HTML/Python/C）共用同一份
{
  "title": "月度营收",
  "series": [
    { "name": "产品A", "values": [120, 200, 150, 80], "color": null },  // color null = 走主题色带
    { "name": "产品B", "values": [60, 110, 90, 140] }
  ],
  "labels": ["Q1", "Q2", "Q3", "Q4"],   // 类目轴
  "unit": "万元",
  "frames": null                         // 动态图表：按时间帧的 series 数组，见 §F
}
```

**变换管道**（数据进渲染前必经，顺序固定）：

```js
const pipeline = [
  normalize,      // 缺省补 0、负值保留、剔除 NaN
  sortIfNeeded,   // 排名图/饼图降序
  aggregateTail,  // 饼图尾部 <2% 合并为"其他"（可关）
  scaleToViewport // 值域 → 像素/字符格（复用 niceCeil）
];
```

---

## §C 主题与背景系统

**三层配色模型**——背景层 / 数据色层 / 文本层，各自独立切换：

### C.1 背景预设

```js
const BACKGROUNDS = {
  dark:     { bg: '#0a0a0a', grid: '#1a1a1a', text: '#e0e0e0' },   // 深色（默认，终端美学）
  light:    { bg: '#fafafa', grid: '#e5e5e5', text: '#1a1a1a' },   // 浅色
  morandi:  { bg: '#d8cfc4', grid: '#c4b8ac', text: '#4a4440' },   // 莫兰迪（低饱和暖灰）
  blueprint:{ bg: '#1b3a5c', grid: '#2a4a6c', text: '#d0e4f5' },   // 蓝图
  custom:   null                                                    // 用户三色自定
};
function applyBackground(chart, name, custom) {
  const t = name === 'custom' ? custom : BACKGROUNDS[name];
  chart.style.background = t.bg;
  chart.dataset.gridColor = t.grid;   // 渲染层读 dataset，不读全局
  chart.dataset.textColor = t.text;
}
```

莫兰迪的要点是**低饱和 + 灰调打底**：若用户给自定义色，校验饱和度（HSL 的 s > 40% 时提示"这不像莫兰迪"但允许继续）。

### C.2 数据色块系统

```js
const COLOR_SYSTEM = {
  // 1) 预设色带（循环取用）
  palettes: {
    terminal: ['#00FF41', '#00D9FF', '#FFB000', '#FF5555', '#BC93FF'],
    morandi:  ['#a8b5a0', '#c4a69b', '#9ba8b5', '#b5a89b', '#a09bb5'],
    mono:     ['#ffffff', '#aaaaaa', '#777777', '#444444']
  },
  // 2) 渐变色带：两锚点间插值
  gradient(from, to, steps) {
    return Array.from({length: steps}, (_, i) => lerpColor(from, to, i / (steps - 1)));
  },
  // 3) 区间映射：值域分段着色（热力/状态墙用）
  thresholds: [[0, '#00FF41'], [60, '#FFB000'], [85, '#FF5555']],  // [下限, 色]
  colorFor(v) { return this.thresholds.findLast(([min]) => v >= min)[1]; }
};
```

- **主题色切换**：运行时可换 palette，图表用 `requestAnimationFrame` 做 300ms 颜色过渡（lerp 当前色→目标色），不要硬切。
- 色带长度不足时循环取色，但同屏相邻系列禁止同色（取色前先查已用集合）。

---

## §D 交互系统

### D.1 加载与更新动效

- **加载**：图表元素从 0 生长（柱从底部长高、线从左扫到右、饼从 0° 展开），时长 400–600ms，ease-out。终端美学下可用**逐行打印**替代（每 30ms 出一行）。
- **数据更新**：旧值→新值做 200ms 插值动画（`requestAnimationFrame` + lerp），禁止闪现。系列数量变化时，新增元素淡入、移除元素淡出。

### D.2 悬停呼吸 + 数据提示

```js
// 悬停元素：透明度呼吸（0.75 ↔ 1.0，周期 800ms）+ 其余元素降到 0.3
canvas.addEventListener('mousemove', e => {
  const hit = hitTest(e.offsetX, e.offsetY);        // 各图表内核提供 hitTest
  state.hover = hit;                                // 渲染循环里按 state.hover 呼吸
  tooltip.show(hit && {
    title: hit.seriesName,
    rows: [[`${hit.label}`, `${hit.value}${unit}`]],
    x: e.offsetX, y: e.offsetY
  });
});
```

- **提示框**：等宽字体、单像素边框（呼应 box-drawing）、跟随光标 12px 偏移、含系列名+数值+单位+占比。
- 呼吸幅度 ≤25% 透明度——再大就成闪烁，违反 §4 美学第 3 条。

### D.3 数据显示控制

- **图例联动**：点击图例项切换该系列显示/隐藏，隐藏时图例文字划线+降透明度；再次点击恢复。状态存 `state.hiddenSeries = Set`。
- **数据标签开关**：全局 `labels: on/off/auto`——auto 模式只在元素够宽时显示（柱宽 <30px 不标）。
- 所有控制状态变更后走 D.1 的插值动画重排，不跳变。

---

## §E 响应式布局

```js
const ro = new ResizeObserver(([entry]) => {
  const w = entry.contentRect.width;
  const tier = w < 480 ? 'phone' : w < 900 ? 'tablet' : 'desktop';
  if (tier !== state.tier) { state.tier = tier; relayout(); }
  else resizeCanvas();   // 同档只改尺寸
});
ro.observe(chartContainer);
```

**各档策略**：

| 档位 | 列宽 | 布局调整 |
|---|---|---|
| phone <480px | 图表全宽 | 图例从侧边移到底部、横屏柱状图转垂直条形图、标签 auto 关、tooltip 改点击触发 |
| tablet 480–900 | 全宽 | 保留图例侧边、标签 auto |
| desktop >900 | 按容器 | 全功能 |

- **横竖屏切换**：监听 `matchMedia('(orientation: landscape)')`，竖屏时横向长图（甘特/排名）提示"旋转屏幕查看更佳"并允许双指缩放。
- **比例锁定**：图表容器用 `aspect-ratio`（默认 16/9，大屏组件自定），防 reflow 时变形。
- Canvas 高分屏：`canvas.width = cssW * devicePixelRatio` 后 `ctx.scale(dpr, dpr)`，否则 Retina 上字符发虚。

---

## §F 图表类型库

### F.0 精度增强（对应 SKILL.md §0.2 技术精度组的"圆润度/浮点密度"探问点）

字符图的分辨率瓶颈在 HTML 引擎里不存在——Canvas 直接画弧形。**饼图/环图默认走 Canvas 弧线**，不走字符网格：

```js
function drawArc(ctx, cx, cy, r, startAngle, endAngle, color) {
  ctx.beginPath();
  ctx.moveTo(cx, cy);
  ctx.arc(cx, cy, r, startAngle, endAngle);
  ctx.closePath();
  ctx.fillStyle = color;
  ctx.fill();
}
// 数据浮点显示密度：标签默认 "值 (xx.x%)"，小数位按占比自适应：
// >=10% 显示整数百分比；1–10% 显示 1 位小数；<1% 显示 2 位小数
```

### F.1 饼图家族

| 类型 | 实现要点 | 适用 |
|---|---|---|
| 饼图 | 单环，从 12 点顺时针，扇区间 1px 分隔缝 | 3–7 个占比项 |
| 环图（donut） | 内半径 = 外半径 × 0.6，中心放总计/标题 | 同上，中心信息加分 |
| **双层环图** | 外环子类、内环父类，角度严格对齐（父类角度=子类之和） | 层级占比 |
| **旭日图** | 多层环，每层一级层级，半径均分 | 3 层以内层级数据 |
| **玫瑰图** | 扇区角度均分，**半径**表示数值（南丁格尔图） | 各类目数值差异大且要强调对比 |

玫瑰图红线：半径用 `r = rMax * sqrt(v / vMax)`——**面积正比于数值**才是诚实可视化，半径线性正比会夸大差异。

### F.2 动态图表引擎

带播放控制条的时序图表，三类共用同一个播放引擎：

```js
// frames: [{ t: '2020', series: [...] }, { t: '2021', ... }, ...]
const player = {
  i: 0, playing: false, speed: 1,   // 播放条：⏮ ◀ ▶ ⏭ + 进度 slider + 速度 1x/2x/4x
  tick() {
    renderFrame(frames[this.i], /* interpolate to */ frames[this.i + 1], this.progress);
    if (this.playing && ++this.progress >= 60) {   // 每帧间 60 步插值
      this.progress = 0;
      this.i = (this.i + 1) % frames.length;
    }
    requestAnimationFrame(() => this.tick());
  }
};
```

- **动态条形图**：每帧重排序，条位置 lerp 移动（排名交换时两条交叉滑过），值标签跟随。
- **动态排名图**：同上但垂直列表布局，榜首高亮。
- **百分比堆叠柱状图**：每帧重算占比，段高 lerp；悬停某段显示该帧绝对值+百分比。
- 播放条 UI：底部全宽，左侧播放/暂停，中间进度 slider（可拖拽 seek），右侧帧时间戳 + 速度切换。拖拽时暂停，松手续播。

### F.3 扩展图表

| 类型 | 内核 | 关键参数 |
|---|---|---|
| **词云** | 词按频次定字号（log 缩放防爆），螺旋放置 + 碰撞检测；**形状**：矩形/圆形/心形/星形——用形状遮罩的离屏 canvas 采样判定可放置区 | `shape`, `maxWords: 80` |
| **漏斗图** | 居中梯形条，层间转化率标注在右侧（`85% ↓`），顶层宽=100% | 层级单调递减校验，非递减时警告 |
| **河流图** | 时间轴堆叠面积沿中心线上下对称展开，段间 1px 缝 | 系列 ≥3 才有意义 |
| **堆叠面积图** | 折线下方填充，逐层堆叠；层序按总量降序（大的在底部） | 可切"绝对值/百分比"模式 |
| **雷达图** | N 轴等角辐射，每轴归一化后连多边形，顶点可悬停读值；多系列用半透明叠加 | 轴数 3–8，超出建议换条形图 |

词云放置算法（够用的简化版）：按字号降序，从中心沿阿基米德螺旋 `r = aθ` 逐点尝试，用离屏 canvas 的 `getImageData` 判碰撞，成功即绘制并标记占用。80 词以内性能无压力。

### F.4 全部图表的交互一致性

每个新图表类型注册时必须实现四个接口，否则不予入库：

```js
registerChartType('radar', {
  render(ctx, data, geom, theme) {},   // 绘制
  hitTest(x, y) {},                    // 悬停命中 → {seriesName, label, value}
  update(data, animate) {},            // 数据更新（走 §D.1 插值）
  legendItems() {}                     // 图例项（供 §D.3 联动）
});
```

---

## §G 数据大屏

```html
<div class="dash" style="--cols: 12">
  <div class="panel" style="grid-area: span 4 / span 4">...</div>  <!-- CSS Grid 12 列 -->
</div>
```

- **组合布局**：CSS Grid 12 列网格，面板声明 `span`；phone 档自动塌缩为单列纵向滚动。
- **实时更新**：每个面板独立 `setInterval`/`EventSource` 拉数，更新走 §D.1 插值动画；**全局帧率对齐**——所有面板共用一个 rAF 循环，各自只在数据脏时重绘。
- **全屏优化**：`document.documentElement.requestFullscreen()`；全屏时面板间距 -25%、字号 +20%、隐藏浏览器 UI 提示条。轮播模式：多页大屏按 `interval` 自动翻页，URL 参数 `?autoplay=30s`。
- **大屏交互控制**：右上角控制条——播放/暂停轮播、主题切换（§C）、全屏开关、刷新频率选择。30 秒无操作自动隐藏控制条（鼠标移动唤回）。
- 性能红线：单屏面板 ≤12 个，每个面板数据点 ≤2000；超出走降采样（LTTB 算法）。

---

## §H 图表类型智能匹配

需求澄清阶段（SKILL.md §0）用户说不清图表类型时，按数据特征推荐：

```js
function recommendChart(data, intent) {
  const { seriesCount, pointCount, hasTime, isProportion, hasHierarchy } = analyze(data);
  if (intent === '排名') return hasTime ? '动态排名图' : '条形图(降序)';
  if (isProportion) {
    if (hasHierarchy) return '旭日图';
    if (hasTime) return '百分比堆叠柱状图';
    return seriesCount <= 7 ? '环图' : '堆叠柱状图';
  }
  if (hasTime) {
    if (seriesCount >= 3 && intent === '趋势构成') return '河流图';
    if (pointCount > 20) return '折线图';
    return '柱状图';
  }
  if (intent === '转化') return '漏斗图';
  if (intent === '多维对比' && seriesCount <= 3) return '雷达图';
  if (intent === '词频') return '词云';
  if (pointCount <= 2 && seriesCount === 1) return '大数字卡片';  // 别为两个数画图
  return '条形图';  // 兜底：条形图是最不易误读的字符图表
}
```

推荐后**必须给用户看理由**（"3 个时间序列 + 看趋势构成 → 河流图"）并给 1 个备选，用户可推翻。

---

## §I 质量红线（HTML 引擎）

1. 所有动画可降级：`prefers-reduced-motion` 时全部动效跳至终态。
2. 图表必须有无 Canvas 的文本摘要（`<details>` 里放终端引擎的 ASCII 版）——SEO + 读屏双收。
3. 颜色对比度：文字/背景 ≥ 4.5:1（WCAG AA），莫兰迪色系最容易踩线，切换后自动校验并警告。
4. 同一图表的配色、字号、间距从 §C 主题系统取，禁止散落的魔法数字。
5. 性能：单图表 60fps 预算内；数据点 >500 自动降采样；离屏面板（IntersectionObserver）停止重绘。
6. 三端联动保持：HTML 引擎的数据 JSON 与终端引擎同源（§B 契约），三端交付规则见 terminal-templates.md。

**成熟库速查（HTML 侧，不想自研时）**：ECharts（全覆盖含大屏/动态图，定制主题成本高）、D3.js（完全自由，工作量大）、Chart.js（轻量标准图）。本模块的价值在**终端美学皮肤 + 轻量零依赖**——若项目已用 ECharts，只做主题包（§C 配色 + 等宽字体 + box-drawing 边框装饰），不要重复造图表内核。
