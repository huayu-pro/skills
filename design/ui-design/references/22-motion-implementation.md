# 22 · 动效实现

> 这一章是「怎么写」。原则在 `09-motion-principles.md`，验收在 `24-motion-verification.md`。
> 所有骨架都遵守同一个契约：`mount(root, options) => dispose`、零外部资产、
> `prefers-reduced-motion` 终态、移动端保留核心手势、无全局监听泄漏。

## 1. 实现契约

```js
export function mount(root, options = {}) {
  if (!root) throw new Error("root required");
  const ac = new AbortController();
  const { signal } = ac;
  const rafIds = new Set();
  const timers = new Set();

  // setup...

  return function dispose() {
    ac.abort();
    for (const id of rafIds) cancelAnimationFrame(id);
    for (const id of timers) clearInterval(id);
    // remove created DOM, close AudioContext/GL, disconnect observers
  };
}
```

硬要求：

- 所有事件监听用 `{ signal }`，`dispose` 时 `ac.abort()`。
- 所有 `requestAnimationFrame` 存 id，`dispose` 时 cancel。
- 所有 `setTimeout/setInterval` 存 id，`dispose` 时 clear。
- 创建的 DOM 节点在 `dispose` 时移除；不往 `window/document` 留全局监听。
- 重复 `mount` 不叠加：`root.dataset.mounted` 检查或 dispose 清理。
- WebGL：`deleteProgram/deleteBuffer/deleteTexture`；Audio：`ctx.close()`。
- 每帧只读一次 `getBoundingClientRect()`，循环里不读布局。

## 2. 通用原语

### 2.1 rAF 循环

```js
let last = performance.now();
let raf = 0;
function frame(now) {
  const dt = Math.min((now - last) / 1000, 1 / 30); // 卡顿后不要跳一大步
  last = now;
  update(dt);
  raf = requestAnimationFrame(frame);
}
raf = requestAnimationFrame(frame);
```

- `dt` 上限 1/30，防止切 tab 回来时页面瞬移。
- 页面隐藏时停：`document.visibilitychange` → cancel/恢复。
- 只在需要时循环：静止后 cancel，交互时重启；不要常驻空转。

### 2.2 lerp / 弹簧 / 摩擦

```js
// v5.0：所有新代码统一用 dt（秒），dt 上限 1/30。
const alpha = 1 - Math.exp(-lambda * dt); // 追目标，lambda 8–14 s^-1
x += (target - x) * alpha;

// 指数摩擦（与帧率无关）
velocity *= Math.exp(-friction * dt); // friction 1.1–4

// 弹簧显式 ζ/ω；ζ=1 才叫临界（无回弹）
const omega = 2 * Math.PI * hz;
const accel = omega * omega * (target - x) - 2 * zeta * omega * v;
v += accel * dt; x += v * dt;
```

`k=120, damping=20` 对应 `ζ≈0.91`，是**欠阻尼**、有轻微回弹，不能写成
「临界弹簧（无回弹）」；`lerp .15` 是 60fps 的 frame-based 观测，只允许出现在
标为 `legacy/observed frame-based` 的旧案例。统一规范见 `28-motion-system.md`。

实测组 `decay .95/.92`、`velocity*(touch?12:8)`、边界 `*0.15`、
传送带 `BASE=62 / MAX=900 / friction=1.1` 是**起点**，不是宇宙常数；新代码先把它们
换算成 `--spring-* / --lambda-* / --dur-*` token，再写理由。

### 2.3 IO reveal

```js
const io = new IntersectionObserver((entries) => {
  for (const e of entries) {
    if (!e.isIntersecting) continue;
    e.target.classList.add("is-in");
    io.unobserve(e.target);
  }
}, { rootMargin: "200px", threshold: 0 });
```

实测：343 站里 `rootMargin: "200px"` 87 站、`threshold: 0` 97 站。
进入用 `var(--dur-long) / var(--dist-md) / var(--ease-enter)`；只对同组元素错峰 `var(--stagger-step)`。观测值 450ms / 16px 不是默认。

### 2.4 指针手势

```js
root.addEventListener("pointerdown", (e) => {
  root.setPointerCapture(e.pointerId);
  start = { x: e.clientX, y: e.clientY, t: performance.now() };
}, { signal });

root.addEventListener("pointermove", (e) => {
  if (!start) return;
  const dx = e.clientX - start.x;
  const dy = e.clientY - start.y;
  // 8 方向：|dx| vs |dy|，主通道决定是横向轨道还是纵向滚动
  if (Math.abs(dx) > Math.abs(dy)) targetAngle += dx * 0.004;
  else targetY += dy;
}, { signal });

root.addEventListener("pointerup", () => {
  velocity = (lastX - prevX) * 0.9; // 保留释放速度
  start = null;
}, { signal });
```

- `touch-action: pan-y` 或 `none` 按主族决定；横向轨道用 `pan-y`，canvas 拖拽用 `none`。
- 触屏没有 hover：核心信息必须在 pointerdown 前可见。
- 点击与拖拽区分：位移 >6px 不算 click。

### 2.5 DPR canvas

```js
const dpr = Math.min(devicePixelRatio || 1, 2);
canvas.width = Math.round(cssW * dpr);
canvas.height = Math.round(cssH * dpr);
ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
```

DPR 上限 2：3x 屏上 3 倍像素只增加成本，肉眼几乎无差。ResizeObserver 里重设，
不要每帧读 `clientWidth`。

### 2.6 WebGL2 最小骨架

```js
const gl = canvas.getContext("webgl2", {
  antialias: false,
  alpha: false,
  powerPreference: "high-performance",
});
if (!gl) { fallbackStaticImage(); } // then return from the mount function

const vert = `#version 300 es
in vec2 a_pos;
void main(){ gl_Position = vec4(a_pos, 0.0, 1.0); }`;

const frag = `#version 300 es
precision highp float;
uniform vec2 u_res; uniform float u_time; uniform vec2 u_mouse;
out vec4 outColor;
void main(){
  vec2 uv = gl_FragCoord.xy / u_res;
  outColor = vec4(uv, 0.5 + 0.5 * sin(u_time), 1.0);
}`;
```

- 全屏用一个覆盖三角形（3 顶点），不要两个三角形。
- 编译失败要捕获 `getShaderInfoLog`，降级到静态渐变/图片，不要留黑屏。
- `webglcontextlost` 监听，`preventDefault()`，恢复后重建资源。
- 暂停按钮 + `visibilitychange` 停 rAF。
- uniform 只传必要：`u_res`、`u_time`、`u_mouse`、`u_progress`。

## 3. 每族骨架

### F1 滚动叙事

- DOM：`section.reveal` 若干 + 一个 `position: sticky` 的 pin 容器。
- CSS：`.reveal{opacity:0;transform:translateY(var(--dist-md))} .reveal.is-in{opacity:1;transform:none;transition:var(--dur-long) var(--ease-enter)}`。
- JS：native-first 用 `animation-timeline: view()`；需要惯性时 IO + pin 容器高度 `320vh`，进度 `p = (scrollY - start) / (height - innerHeight)`。
- 降级：reduced-motion 直接 `is-in`，pin 改三段堆叠，并保留剖面/进度的静态刻度身份。
- 资产：`kits/01-scroll-narrative.js`、`components/10-scroll-narrative`。

### F2 横向轨道

- DOM：`track` + N 个 `panel`；容器 `overflow: hidden`。
- CSS：`track{display:flex;gap:24px;will-change:transform}`。
- JS：wheel/drag → `targetX`，`x = lerp(x, targetX, .15)`；边界 `if (x < min) x = min + (x-min)*.15`。
- 降级：reduced-motion 改为原生横向滚动（`overflow-x:auto; scroll-snap`）+ 静态位置刻度。
- 资产：`kits/02-horizontal.js`、`kits/02-horizontal-rail`。

### F3 全屏 shader

- DOM：`canvas` 全屏 + 一个 `pause` 按钮。
- JS：覆盖三角形 + fragment shader；`u_time` 来自 rAF；`u_mouse` lerp 平滑。
- 性能：DPR≤2；`precision highp float` 在移动端可能降为 mediump，先测。
- 降级：无 WebGL2 → 静态渐变 + 一个 CSS 动画层。
- 资产：`components/05-shader-plane`、`kits/03-webgl-shader.js`。

### F4 WebGL 3D 物体

- 用裸 WebGL：一个立方体/平面，`mat4` 透视 + 相机 + 旋转；不用 Three.js 保持零依赖。
- 深度线索：大小、雾化（fog）、亮度、遮挡顺序。
- 降级：无 WebGL → CSS 3D `transform-style: preserve-3d` 的卡片。
- 资产：`kits/10-webgl-object`；Three.js 版本见提示词 `F4-tristan-rain-scene`。

### F5 像素 canvas

- 低分辨率离屏 canvas（如 160×120），`imageSmoothingEnabled=false`，整数倍放大。
- 调色板 ≤8 色；逐字/逐像素用整数索引，不用浮点采样。
- 降级：reduced-motion 只画终帧。
- 资产：`kits/04-canvas-2d.js`、`kits/04-pixel-canvas`。

### F6 排版动效

- 行 mask：外层 `overflow:hidden`，内层 `translateY(110%) → 0`，450–700ms。
- 逐字：`span` 包每个字，stagger 20–50ms，总时长 ≤300ms（短标题可 700ms）。
- 可变字体：先测 `font-stretch`/`font-variation-settings` 是否真的改变宽度；
  同串文本 50% 与 150% 宽度相同 = 无 `wdth` 轴，不要声称。
- 资产：`kits/07-typography.js`、`components/12-editorial-motion`。

### F7 光标/磁吸

- dot 跟随指针（lerp .2），ring 更慢（lerp .08）；hover 可点击元素时放大 ring。
- 磁吸：元素中心与指针距离 < radius 时 `translate` 部分跟随；离开回弹。
- 触屏/`prefers-reduced-motion`：隐藏自定义光标，恢复原生。
- 资产：`kits/06-cursor.js`、`components/09-cursor-field`。

### F8 音频/波形

- 必须用户手势解锁 `AudioContext`；不要自动播放。
- `AnalyserNode.fftSize=128`，64 根 bar；峰值衰减用 `bar *= .92`。
- 暂停时 `suspend()`，恢复时 `resume()`；页面隐藏时暂停。
- 降级：reduced-motion 用静态波形；无音频权限时显示占位。
- 资产：`kits/09-audio.js`、`components/11-audio-visualizer`。

### F9 3D 倾斜/ peeling

- `perspective: 900px` + `rotateX/rotateY` 由指针位置映射，clamp ±10–14°。
- sheen：`linear-gradient` 的 `background-position` 跟随指针；不要叠 `box-shadow` 模拟高光。
- 材质：箔材/玻璃用多层渐变 + `mix-blend-mode`，一层就够。
- 降级：触屏只保留 `:active` 的 1–2° 倾斜。
- 资产：`kits/05-orbit-3d.js`、`components/02-bend-carousel`。

### F10 相机/缩放

- 把页面当一张可移动的画布：`transform: translate(x,y) scale(z)`，`transform-origin: 0 0`。
- 拖拽 pan、滚轮 zoom、双击回中；边界用橡皮筋。
- minimap 用第二个 scale 的克隆或 canvas 缩略图；点击跳转。
- 降级：reduced-motion 取消惯性，直接定位。
- 资产：`kits/10-map.js`、`components/06-tunnel-scene`。

### F11 传送带/marquee

- 内容复制两份，`x = (x - speed*dt) % loopWidth`；速度由滚动/拖拽 boost。
- `boost *= exp(-dt*1.1)`，`BASE=62`、`MAX=900`；hover 减速，`prefers-reduced-motion` 停止。
- 无缝：复制内容的宽度必须等于 `loopWidth`，字体加载后重算。
- 资产：`components/04-belt-conveyor`、`kits/12-editorial-landing.js`。

### F12 扫描/VHS

- 三层速度：200ms 扫描线、1s 噪点、8s 颗粒；不要三层同速。
- 扫描线用 `repeating-linear-gradient`，噪点用 SVG `feTurbulence` 或 canvas 随机像素。
- glitch：`clip-path: inset()` 随机切片 + `translateX` 抖动，持续 80–160ms，不要常驻。
- 降级：reduced-motion 只保留静态纹理。
- 资产：`keyframes-scan-vhs`、`code/css/keyframes.css`。

### F13 视频拼贴

- 多 `<video muted playsinline preload="metadata">`，封面用 `poster`；用户手势后再 `play()`。
- 布局：绝对定位 + `object-fit: cover`，每块有不同延迟/视差。
- 网络差/离屏：`IntersectionObserver` 暂停；`prefers-reduced-motion` 只显示 poster。
- 资产：`kits/08-collage.js`、`kits/08-video-collage`。

### F14 状态机/产品演示

- 先命名状态：`idle → focus → typing → sending → done → error`；每个转移有事件与时长。
- 一个 `state` 对象 + `transition(event)`；不要用散落的 `classList.toggle`。
- 键盘：Tab/Enter/Space/Escape；`aria-pressed`/`aria-live` 同步。
- 降级：reduced-motion 直接跳到终态，不播中间步骤。
- 资产：`kits/11-game.js`、`components/03-clock-wipe`、`07-color-lab`、`08-rotary-controls`。

## 4. 性能预算

| 项 | 预算 | 说明 |
|---|---|---|
| 每帧 JS | <8ms | 60fps 的 16.7ms 里留一半给渲染 |
| rAF 常驻 | 只在该动时 | 静止后 cancel，交互重启 |
| DPR | ≤2 | 3x 屏不追 3 倍像素 |
| 粒子/图层 | ≤300 / ≤40 | 超过就降采样或分层 |
| 布局读取 | 每帧 ≤1 次 | `getBoundingClientRect` 缓存，不在循环里读 |
| WebGL draw | ≤8/帧 | 全屏 shader 1 个 draw 足够 |
| 视频同时播放 | ≤3 | 其余 poster/暂停 |

## 5. 移动端与降级

- 390px 宽必须 `scrollWidth <= innerWidth`；横向轨道用 `overflow-x: clip` 不要 `hidden`（会破坏 sticky）。
- 触控目标 ≥44×44px；核心手势不超过 1 个。
- hover-only 的信息在触屏不存在：默认可见或点击展开。
- `prefers-reduced-motion`：到终态并保留物理/功能身份；见 `28` 的 identity matrix。状态变化给 ≤120ms 的颜色/徽标提示。
- `prefers-reduced-transparency` / `prefers-contrast`：玻璃/低对比表面要给不透明/高对比回退。
- 无 JS：F1 的 reveal 默认可见（`no-js` class 或 `<noscript>` 样式），不要空白。

## 6. 资产映射

| 想做什么 | 先读 | 再抄 |
|---|---|---|
| 滚动揭示/长页 | `09` §7 + `kits/01` | `components/10` |
| 横向作品集 | `09` §3 + `kits/02` | `kits/02` |
| 全屏背景 | `09` §12 + `kits/03` | `components/05` |
| 3D 物体 | `kits/10` 的相机数学 | `kits/10` |
| 像素/字符 | `kits/04` | `kits/04` |
| 动态标题 | `kits/07` | `components/12` |
| 自定义光标 | `kits/06` | `components/09` |
| 音频可视化 | `kits/09` | `components/11` |
| 卡片倾斜/材质 | `kits/05` | `components/02` |
| 地图/相机 | `kits/10` | `components/06` |
| 无限跑马灯 | `kits/12` | `components/04` |
| 扫描/glitch | `keyframes.css` | `keyframes` |
| 视频拼贴 | `kits/08` | `kits/08` |
| 产品演示状态机 | `kits/11` | `components/03/07/08` |

## 7. 常见错误

| 错误 | 症状 | 修法 |
|---|---|---|
| 直接映射 `scrollTop` | 页面像没有重量 | 加速度/角度 + 摩擦/弹簧 |
| 只改 `scale` 做深度 | 像缩放，不像空间 | 同时改 scale/blur/z/opacity |
| modal 从屏幕中心 scale | 与触发物无关 | 从被点元素的位置/方向展开 |
| 每个 section fade-in-up | 一直在动，无法阅读 | 只保留一个注意瞬间；其余 IO 只做一次 |
| 无限 marquee 无暂停 | 无法阅读，晕动 | hover 减速 + reduced-motion 停止 |
| `transition: all` | 意外属性也在动，卡 | 明确列 `transform, opacity` |
| 手风琴量 `scrollHeight` | 每帧布局，卡 | `grid-template-rows: 0fr → 1fr` |
| 自定义光标不降级 | 触屏没有光标 | `pointer: fine` 才启用 |
| 音频自动播放 | 被浏览器拦截/扰民 | 用户手势解锁 |
| 只做桌面 | 390px 溢出 | `min-width:0` + `overflow-x:clip` |