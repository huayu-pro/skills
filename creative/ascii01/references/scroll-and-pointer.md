# 滚动叙事与指针交互：让字符画响应滚动和鼠标

> 本文小节编号 I.1–I.6 为**文件本地编号**；跨文件引用本文时写 `scroll-and-pointer.md §I.x`。
> 场景：落地页 hero 随滚动逐渐"聚焦"（精度渐变）、长页叙事（每章一屏 ASCII）、鼠标"手电筒"照亮字符画、hover 窥见原图。全部零依赖。

## I.1 滚动进度：一切的基础

```js
// 页面滚动进度 0–1；passive 监听不阻塞滚动，rAF 节流保证每帧最多算一次
let ticking = false;
function scrollProgress() {
  const doc = document.documentElement;
  const max = doc.scrollHeight - innerHeight;
  return max <= 0 ? 1 : Math.min(1, Math.max(0, scrollY / max));
}
addEventListener('scroll', () => {
  if (ticking) return;
  ticking = true;
  requestAnimationFrame(() => { render(scrollProgress()); ticking = false; });
}, { passive: true });                        // passive：承诺不调 preventDefault，滚动更顺滑
```

**容器级进度**（元素自身滚过视口的程度，长页叙事更常用）：

```js
function elementProgress(el) {
  const r = el.getBoundingClientRect();
  return Math.min(1, Math.max(0, (innerHeight - r.top) / (innerHeight + r.height)));  // 0 进入前 → 1 离开后
}
```

**步进检测**（精度档位切换这类离散需求，用 IntersectionObserver 而不是连续比较）：

```js
const io = new IntersectionObserver(entries => {
  for (const e of entries) {
    if (e.isIntersecting) renderScene(e.target.dataset.scene);   // 进入视口 → 触发该场景动画
  }
}, { threshold: 0.4 });                        // 40% 可见才算"到达"，防止边缘抖动
document.querySelectorAll('[data-scene]').forEach(el => io.observe(el));
```

## I.2 用法一：精度渐变（越滚越清晰）

滚动进度映射采样档位：进场模糊（10 级稀 ramp）→ 滚到主视觉时高清（24 级）→ 定格时超高清（70 级）。叙事感强且首屏渲染最便宜。

```js
const TIERS = [                                // 档位表：进度阈值 → ramp（档位定义见 image-to-ascii.md §2.2）
  { until: 0.15, ramp: ' .:-',     label: '模糊' },
  { until: 0.55, ramp: ' .:-=+*#%@', label: '标准' },
  { until: 1.01, ramp: ' .\'`^",:;Il!i><~+_-?][}{1)(|/tfjrxnuvczXYUJCLQ0OZmwqpdbkhao*#MW&8%B@$', label: '高清' },
];
function rampFor(p) { return TIERS.find(t => p < t.until); }

let lastRamp = null;
function render(p) {
  const tier = rampFor(p);
  if (tier.ramp === lastRamp) return;          // 档位没变不重采样——渐变是分档的，不是逐帧的
  lastRamp = tier.ramp;
  grid = sampleToGrid(sourceImage, COLS, tier.ramp);   // 复用 image-to-ascii.md §2.1 内核，仅 ramp 可变
  pre.textContent = grid.join('\n');
}
```

- **防抖红线**：档位切换发生在滚动中，重采样一次 24 级网格在 1–3ms 量级，但别在连续两帧间反复切（阈值区间不要重叠，上表 `until` 单调递增已保证）。
- 变体：反向渐变（进场高清、滚走时溶解成噪声——配 animation-patterns.md §P.4）。

## I.3 用法二：密度渐变（列数呼吸）

进度映射 COLS：80 → 160，网格由疏到密。视觉上像"信号增强"。

```js
function render(p) {
  const cols = Math.round(80 + p * 80);        // 80 → 160
  if (cols === lastCols) return;
  lastCols = cols;
  grid = sampleToGrid(sourceImage, cols, RAMP);
  pre.textContent = grid.join('\n');
  pre.style.fontSize = `${baseFont * 160 / cols}px`;   // 列变多字号变小，画布总宽不变
}
```

- 每次变 COLS 都是全量重采样：**步进 8 列一档**（`Math.round(cols / 8) * 8`）而不是逐列，滚动全程只重采样 ~10 次。
- 行数随纵横比联动（image-to-ascii.md §2.1 同款修正），不要锁死行数造成压扁。

## I.4 用法三：场景切换（长页叙事）

每章节一屏，sticky 定位 + 进入视口触发该屏的入场动效（动效本体用 animation-patterns.md 的模式，此处只管调度）：

```html
<section class="scene" data-scene="intro" style="position: sticky; top: 0; height: 100vh;">
  <pre class="ascii"></pre>
</section>
<section class="scene" data-scene="logo"   style="position: sticky; top: 0; height: 100vh;">
  <pre class="ascii"></pre>
</section>
```

```js
// 场景表驱动：每屏 = 静态网格 + 入场模式 + 参数（模式代码直接引用 animation-patterns.md §P.x）
const SCENES = {
  intro: { grid: introGrid, pattern: 'typewriter', params: { cps: 30 } },
  logo:  { grid: logoGrid,  pattern: 'cascade',    params: { stagger: 2 } },
};
function renderScene(id) {
  const s = SCENES[id];  if (!s) return;
  startAnimation(s.grid, PATTERNS[s.pattern], s.params);   // 帧驱动循环，入场播完即停（§P.9 规则 4）
}
```

- 离开视口的场景必须停帧（IntersectionObserver 的 `!isIntersecting` 分支里 cancel），否则后台空转（SKILL.md §6）。
- sticky 场景的总高度 = 场景数 × 100vh，`scrollProgress` 按场景计数换算"第几屏"。

## I.5 指针照亮（手电筒）

鼠标位置半径 R 内的字符提亮一档——配深底暗字符画效果最佳（"暗房里的手电"）。

```js
const R = 6;                                   // 照亮半径（字符格）
const charW = pre.querySelector?.offsetWidth ?? 10;   // 实测单字符宽（取 pre 宽 / COLS）
const charH = fontSize * 1;                    // line-height:1 时字符高 = 字号

pre.addEventListener('pointermove', e => {
  const rect = pre.getBoundingClientRect();
  const px = Math.floor((e.clientX - rect.left) / charW);    // 指针所在格坐标
  const py = Math.floor((e.clientY - rect.top) / charH);
  // 只重算受影响的行（|y-py|<=R），其余行保持缓存——脏区思想（SKILL.md §6）
  pre.textContent = brighten(baseGrid, px, py, R).join('\n');
});
pre.addEventListener('pointerleave', () => { pre.textContent = baseGrid.join('\n'); });

function brighten(grid, px, py, r) {           // 半径内提亮一档（bump 见 animation-patterns.md §P.3）
  return grid.map((line, y) => {
    if (Math.abs(y - py) > r) return line;
    return line.split('').map((ch, x) => {
      const d2 = (x - px) ** 2 + ((y - py) * 0.55) ** 2;     // 0.55：纵横比修正，照亮区是圆不是椭圆
      return d2 <= r * r && ch !== ' ' ? bump(ch) : ch;
    }).join('');
  });
}
```

- 性能：`brighten` 只重映射受影响行，160 列网格单帧 <1ms；但仍要 rAF 合并连续 pointermove（一次移动事件流可能一帧触发多次）。
- **缓存基准网格**：`baseGrid` 是常量，永远从它生成亮化版——不要在亮化版上叠加亮化（会越来越亮）。

## I.6 hover 显原像素 + 鱼眼（进阶交互）

**hover 显原像素**：字符格与原图像素块一一对应，鼠标悬停区域露出原图——"双层视觉"（与 web-implementation.md §3.6 全局切换同源，这里是局部版）：

```html
<div class="reveal" style="position: relative;">
  <img src="logo.png" style="position: absolute; inset: 0; clip-path: circle(0 at 50% 50%);">  <!-- 原图层 -->
  <pre class="ascii"></pre>                                                                                  <!-- 字符层 -->
</div>
```

```js
// 悬停时把 clip-path 圆心跟着指针走：字符画上开一扇"看见原像素的圆窗"
wrapper.addEventListener('pointermove', e => {
  const r = wrapper.getBoundingClientRect();
  const x = ((e.clientX - r.left) / r.width * 100).toFixed(1);
  const y = ((e.clientY - r.top) / r.height * 100).toFixed(1);
  img.style.clipPath = `circle(60px at ${x}% ${y}%)`;       // 60px 窗口半径，按需调
});
wrapper.addEventListener('pointerleave', () => { img.style.clipPath = 'circle(0 at 50% 50%)'; });
```

- 两层必须像素级对齐：字符网格由该图该尺寸采样而来（同一 `wrapper` 尺寸），否则窗口里的原图与周围字符错位。
- **鱼眼放大**（网格重排版）：距指针 d 的列横向位移 `dx = k * Math.sin(π * d / (2R))`（k≈4），网格中心被"推开"、指针处内容相对放大——与 animation-patterns.md §P.6 波浪同构（把正弦相位换成指针距离），实现时复用其行长恒定位移写法。

**触屏与无障碍回退**（硬性要求，SKILL.md §5/§7）：

| 场景 | 回退方案 |
|---|---|
| 触屏（无 hover） | 指针照亮 → 点击切换开关（tap 开/关手电筒，照亮区固定在屏幕中偏上）；显原像素 → 长按预览 |
| `prefers-reduced-motion` | 精度/密度渐变直接呈现终态最高档；动效场景切换只做淡入（或直接静态切换）；照亮/鱼眼保留（属响应式反馈非动效） |
| 键盘用户 | 场景切换支持 `Tab` 聚焦 + 方向键翻屏；照亮交互提供等价按钮（"开启高亮模式"） |
