# Web 实现路线详册（GIF / 视频 / 3D / GPU / 纯字符装饰 / 构建期管线）

> 本文小节编号 3.0–3.9 为**文件本地编号**，与 SKILL.md 章节无关；跨文件引用本文时请写 `web-implementation.md §3.x`。

### 3.0 资源加载：重试、超时与兜底（所有网络/本地素材的统一入口）

素材加载失败是线上最高频故障（弱网、跨域、路径手误）。**本文所有 fetch / 图片解码统一走本节封装**，不要裸调用。

```js
// 通用重试加载：指数退避（500ms→1s→2s）+ 超时 + 用户能看懂的中文报错
async function loadWithRetry(url, { retries = 3, timeout = 8000, backoff = 500 } = {}) {
  let lastErr;
  for (let attempt = 0; attempt <= retries; attempt++) {
    const ctrl = new AbortController();                       // 单次尝试的超时开关
    const timer = setTimeout(() => ctrl.abort(), timeout);
    try {
      const res = await fetch(url, { signal: ctrl.signal });
      if (res.status === 404) throw new Error(`素材路径写错了（404）：${url}，请核对文件名与大小写`);
      if (res.status === 403) throw new Error(`服务器不允许直接引用这个素材（403）：${url}，请下载到本地再引用`);
      if (!res.ok) throw new Error(`素材加载失败（HTTP ${res.status}）：${url}`);
      return await res.arrayBuffer();
    } catch (err) {
      lastErr = err;
      if (err.message.includes('404') || err.message.includes('403')) throw err;  // 明确错误不重试
      if (attempt < retries) {
        showStatus(`素材加载失败，正在自动重试（第 ${attempt + 1}/${retries} 次）…`);
        await new Promise(r => setTimeout(r, backoff * 2 ** attempt));             // 指数退避
      }
    } finally {
      clearTimeout(timer);
    }
  }
  throw new Error(`网络不通或素材服务器无响应，已自动重试 ${retries} 次仍失败：${url}`);
}

// 图片版：new Image + decode()，同一套重试策略
async function loadImageWithRetry(url, opts = {}) {
  let lastErr;
  for (let attempt = 0; attempt <= (opts.retries ?? 3); attempt++) {
    try {
      const img = new Image();
      img.crossOrigin = 'anonymous';                          // 远程素材防画布污染（SKILL.md §0.2）
      img.src = url;
      await img.decode();                                     // 解码失败会在这抛出
      return img;
    } catch (err) {
      lastErr = err;
      if (attempt < (opts.retries ?? 3)) {
        showStatus(`图片解码失败，正在自动重试（第 ${attempt + 1} 次）…`);
        await new Promise(r => setTimeout(r, (opts.backoff ?? 500) * 2 ** attempt));
      }
    }
  }
  throw new Error(`图片无法显示（文件损坏或格式不对）：${url}`);
}
```

**失败兜底三件套**（重试耗尽后不许白屏）：

```js
async function loadAsciiAsset(url, fallbackText) {
  try {
    return await loadWithRetry(url);
  } catch (err) {
    showFallback(fallbackText, err);                          // ① 内联静态首帧（管线 --inline-first 产物）
    throw err;                                                // ③ 错误照常上报控制台，便于排查
  }
}
function showFallback(text, err) {
  pre.textContent = text;                                     // 静态字符画先顶上
  retryBtn.hidden = false;                                    // ② 手动"重试"按钮（比自动循环更尊重用户）
  retryBtn.onclick = () => location.reload();
  liveRegion.textContent = `素材加载失败：${err.message}`;      // aria-live 播报给读屏用户
}
```

**「控制台原话 → 人话 → 处置」对照表**（给最终用户的排错指引，可直接抄进项目 README）：

| 控制台/网络面板原话 | 实际意思 | 用户怎么办 |
|---|---|---|
| `TypeError: Failed to fetch` | 网络不通，或目标服务器拒绝跨域访问 | 检查网络；把素材下载到项目里用相对路径 |
| `404 Not Found` | 素材路径写错了 | 核对文件名拼写与大小写、相对路径层级 |
| `403 Forbidden` | 服务器禁止外站直接引用（防盗链） | 把素材下载到本地再引用 |
| `CORS header 'Access-Control-Allow-Origin'` | 跨域被浏览器拦截 | 素材本地化，或让素材服务器补 CORS 头 |
| `EncodingError` / `decode failed` / 图片显示碎块 | 文件损坏或扩展名与内容不符 | 重新导出素材（别手改扩展名） |
| `net::ERR_INTERNET_DISCONNECTED` | 断网了 | 页面已自动重试 3 次；联网后点"重试"按钮 |

### 3.1 GIF → ASCII 动画（gifuct-js）

```js
import pkg from 'gifuct-js';
const { parseGIF, decompressFrames } = pkg;

const buf = await loadWithRetry('anim.gif');   // §3.0 封装：重试 + 超时 + 中文报错，勿裸 fetch
const frames = decompressFrames(parseGIF(buf), true);
// ParsedFrame 字段（gifuct-js v2）：{ pixels, dims:{top,left,width,height},
//   colorTable, delay, disposalType, transparentIndex, patch }
// 注意：delay 已是毫秒（库内 (gce.delay || 10) * 10），不要再乘 10。

// 画布逻辑尺寸 = 所有帧 rect 的并集
const W = Math.max(...frames.map(f => f.dims.left + f.dims.width));
const H = Math.max(...frames.map(f => f.dims.top + f.dims.height));

// 增量帧合成：把每个 patch 贴回全幅画布，采样始终针对完整帧
const full = new Uint8ClampedArray(W * H * 4);
const asciiFrames = frames.map(f => {
  if (f.disposalType === 2) full.fill(0);            // 恢复背景式清除
  const { left, top, width: w, height: h } = f.dims;
  for (let y = 0; y < h; y++) for (let x = 0; x < w; x++) {
    const s = (y * w + x) * 4, d = ((top + y) * W + left + x) * 4;
    full[d] = f.patch[s]; full[d+1] = f.patch[s+1];
    full[d+2] = f.patch[s+2]; full[d+3] = f.patch[s+3];
  }
  return { delay: f.delay, rgba: full.slice() };     // slice：存快照
});

// RGBA 数组 → ASCII（GIF patch / 合成帧共用；与 image-to-ascii.md §2.1 同一 RAMP 与映射）
function patchToAscii(rgba, dims, darkBg = true) {
  const RAMP = ' .:-=+*#%@';
  const { width: w, height: h } = dims;
  let out = '';
  for (let y = 0; y < h; y++) {
    for (let x = 0; x < w; x++) {
      const i = (y * w + x) * 4;
      const a = rgba[i + 3] / 255;
      const t = ((0.299 * rgba[i] + 0.587 * rgba[i + 1] + 0.114 * rgba[i + 2]) / 255) * a;
      out += RAMP[Math.floor((darkBg ? t : 1 - t) * (RAMP.length - 1))];   // 契约索引公式（SKILL.md §1.2）
    }
    out += '\n';
  }
  return out;
}

// 每帧按自身 delay 调度（累计误差修正），而非 setInterval 均摊
let i = 0, nextAt = performance.now();
function tick(now) {
  while (now >= nextAt) {
    const f = asciiFrames[i];
    pre.textContent = patchToAscii(f.rgba, { width: W, height: H });
    i = (i + 1) % asciiFrames.length;
    nextAt += f.delay;
  }
  requestAnimationFrame(tick);
}
requestAnimationFrame(tick);
```

**最大坑：GIF 增量帧压缩**。相邻帧只存差异，直接解出的帧缺背景、有破边。素材必须保证每帧完整：AE 用 GifGun 插件勾选"保留每帧完整像素"；PS/其他工具关闭帧优化。无法控制素材来源时，播放前做帧合成校验（上方代码已内置合成）。快速判定是否为增量帧：`frames.some(f => f.dims.left || f.dims.top || f.dims.width !== W || f.dims.height !== H)` 为 true 即含局部帧，必须走合成路径。素材站：gifer.com、tenor.com。单 GIF（约 2MB）远优于帧序列图（几十张约 5MB + 高频 HTTP 请求）。大 GIF 建议构建期离线转成 JSON 帧缓存。

### 3.2 视频 / 摄像头

```js
const stream = await navigator.mediaDevices.getUserMedia({ video: true });
video.srcObject = stream; // video 元素隐藏，仅作帧源

// 优先 requestVideoFrameCallback：仅当新视频帧就绪才采样，与流帧率精确对齐
function onFrame() {
  ctx.drawImage(video, 0, 0, COLS, rows);
  pre.textContent = toAscii(ctx, video, video.videoWidth, video.videoHeight);
  video.requestVideoFrameCallback(onFrame);
}
if (video.requestVideoFrameCallback) video.requestVideoFrameCallback(onFrame);
// 不支持时回退 requestAnimationFrame 循环
```
注意：等待 `video.readyState >= 2` 再采样；页面不可见时停流省电。

### 3.3 Three.js 3D → ASCII

```js
import { AsciiEffect } from 'three/addons/effects/AsciiEffect.js';

const effect = new AsciiEffect(renderer, ' .:-=+*#%@', { invert: true, resolution: 0.15 });
effect.setSize(innerWidth, innerHeight);
document.body.appendChild(effect.domElement);
renderer.setAnimationLoop(() => effect.render(scene, camera)); // 替代 renderer.render
```
- `resolution`（默认 0.15）是主调参旋钮：直接决定字符密度与帧率。
- `invert` 按页面底色调整（深底用 true）。
- 内部是 CPU 回读（getImageData + DOM），适合中小 hero 区；全屏高分辨率实时需求走 §3.4，或直接用 `ascii-scene`（GLSL 字符图集，无 CPU 回读，自带鼠标跟随/自动旋转）与 `@ascii-fx/three`（WebGPU 后处理）。

### 3.4 GPU shader 后处理（性能上限）

场景渲到离屏纹理 → fragment shader 把屏幕切字符格 → 每格中心采样算亮度 → 从**预烘焙字符图集**选格贴出。全 GPU、无 CPU 回读。质量升级项：
- **有序抖动（Bayer 2×2/4×4/8×8）**：格内亮度与 Bayer 阈值比较再选字，消除色带，出复古颗粒感。
- **误差扩散（Floyd-Steinberg / Atkinson）**：Atkinson 只扩散 6/8 误差，对比更高、质感更"脆"，是 MacPaint 经典风味。参考 Codrops "Efecto: Real-Time ASCII and Dithering Effects with WebGL Shaders"（2026）。
- SPA 中组件卸载时必须完整清理 WebGL 资源（buffer/texture/program），最后调 `WEBGL_lose_context` 主动释放——浏览器并发上下文上限仅 8–16 个。

仅当 §3.1–3.3 达不到帧率目标时才上。

**降级链特性检测（SKILL.md §5 的四级回退可复制实现）**：

```js
function pickRenderer() {
  const c = document.createElement('canvas');
  const gl = c.getContext('webgl2') || c.getContext('webgl');
  if (gl) return 'webgl';                       // 全屏实时首选
  const ctx2d = c.getContext('2d');
  if (ctx2d && typeof ctx2d.fillText === 'function') return 'canvas';
  if (typeof document.createElement('pre').textContent === 'string') return 'pre';
  return 'static';                              // 预生成字符串内联
}
```

### 3.5 纯字符装饰（零采样）

**FIGlet 大字**：运行时用 `figlet.text('HI', { font: 'Slant' })`；更推荐构建期 `npx figlet -f Slant HI` 生成后内联为静态字符串，零运行时成本。

**box-drawing 风格表**（按气质选，全站统一）：

| 风格 | 样例 | 气质 |
|---|---|---|
| 细线 | `┌─┐│└┘` | 干净、现代 |
| 双线 | `╔═╗║╚═╝` | 正式、复古大型机 |
| 圆角 | `╭─╮│╰─╯` | 柔和、友好 |
| 粗线 | `┏━┓┃┗━┛` | 工业、力量感 |
| 纯 ASCII | `+-+|+-+` | 极复古、兼容一切 |
| 方块 | `█▀▀█ █ █▄▄█` | 粗野主义、块状 |

进阶：不对称边框（顶双线上侧细线）制造层次；装饰角符 `◆ ◈ ✦ ⬡ ● ◢ ◣` 做点睛；主容器用粗线、次级用细线建立视觉层级。

**Matrix 字符雨**（完整可复制实现；列模型 + 半透明拖尾，深底页面直接可用）：

```html
<canvas id="rain" aria-hidden="true"></canvas>
```

```js
const rain = document.getElementById('rain');
const ctx = rain.getContext('2d');
const CHARS = 'ｱｲｳｴｵｶｷｸｹｺ0123456789';              // 半角片假名 + 数字（视觉契约同 SKILL.md §0.1 Matrix 预设）
const FONT = 16;                                          // 字号 = 格高；格宽按等宽体实测
const reduced = matchMedia('(prefers-reduced-motion: reduce)').matches;

function resize() {
  rain.width = innerWidth; rain.height = innerHeight;
  ctx.font = `${FONT}px monospace`;
}
resize(); addEventListener('resize', resize);

const charW = ctx.measureText('ｱ').width;                 // 实测单字符宽（别硬编码）
const COLS = Math.floor(rain.width / charW);
// 列模型：每列 {y 当前头位置, speed 每帧下落行数, tail 尾长}；随机只出现在初始化（一次性）
const drops = Array.from({ length: COLS }, () => ({
  y: Math.random() * -50,                                 // 负值错开起始相位（先在屏外）
  speed: 0.5 + Math.random(),                             // 0.5–1.5 行/帧
  tail: 8 + Math.random() * 16,                           // 尾长 8–24
}));

function draw() {
  // 半透明黑整屏覆盖 → 旧字符逐帧变淡，形成拖尾（0.05–0.10：越小尾越长）
  ctx.fillStyle = 'rgba(0,0,0,0.08)';
  ctx.fillRect(0, 0, rain.width, rain.height);
  for (let i = 0; i < COLS; i++) {
    const d = drops[i], x = i * charW;
    // 只画列头（亮）与尾内字符（暗）——列身靠拖尾残留自然形成，无需逐字符遍历整列
    ctx.fillStyle = '#e8ffe8';                            // 列头近白的亮绿
    ctx.fillText(CHARS[Math.floor(Math.random() * CHARS.length)], x, d.y * FONT);
    ctx.fillStyle = '#0a0';                               // 尾内补充字符（暗绿）
    ctx.fillText(CHARS[Math.floor(Math.random() * CHARS.length)], x, (d.y - d.tail) * FONT);
    d.y += d.speed;
    if (d.y * FONT - d.tail * FONT > rain.height + FONT) { // 整列走完屏 → 回到屏上方重生
      d.y = Math.random() * -20;
      d.speed = 0.5 + Math.random();
      d.tail = 8 + Math.random() * 16;
    }
  }
}

// reduced-motion：只画一帧快照（静态雨幕），不进循环——SKILL.md §5 硬性要求
if (reduced) { for (let k = 0; k < 60; k++) draw(); }
else {
  let visible = true;
  document.addEventListener('visibilitychange', () => { visible = !document.hidden; loop(); });
  (function loop() { if (visible) draw(); requestAnimationFrame(loop); })();
}
```

- **性能红线**：每帧成本 O(COLS)（每列只 fillText 两个字符），1920px 宽 ≈ 120 列，远低于 SKILL.md §6 预算；不要把列身逐字符全画（O(COLS×tail)，5 倍开销且被拖尾覆盖看不见）。
- `Math.random()` 在网页端合法（无需跨帧确定性）；**同样的雨要导出视频时**必须换成 `random(seed)` 纯函数列模型——完整视频版实现见 remotion-video.md §R.4。
- 页面底色非纯黑时：把拖尾的 `rgba(0,0,0,0.08)` 换成底色同值 `rgba(R,G,B,0.08)`，否则会逐渐"黑化"。

---

### 3.6 双视觉模式切换（彩蛋级手法）

标杆案例：Novoseltsev 作品集——正常现代页面，**按 `T` 整站切换 ASCII 终端模式**，图片实时转字符。实现：

```js
addEventListener('keydown', e => {
  if (e.key.toLowerCase() === 't' && !e.target.matches('input,textarea')) {
    document.body.classList.toggle('ascii-mode');
    if (document.body.classList.contains('ascii-mode')) startAscii(); else stopAscii();
  }
});
```

- ASCII 模式下：`<img>`/背景图用 §2 内核逐张转 `<pre>` 替换（或 `position:absolute` 覆盖，保原图在 DOM 里以便切回）；文本保持原样但换成等宽体 + 终端配色。
- 两套视觉共享 DOM 结构，只切渲染层——切换成本是一次全量采样，不要重建节点。
- 在页脚/关于里埋提示（`press [T]`），让彩蛋可被发现；切换时播一次 100ms 的 CRT 闪烁过渡，仪式感拉满。
- 变体：滚动深度触发（滚过 hero 后字符开始"溶解"为像素——完整实现见 scroll-and-pointer.md §I.2）、区域级切换（只有 hero 图可 ASCII 化）。

### 3.7 CRT / 复古层（CSS 质感包）

```css
.crt::before {              /* 扫描线：1px 渐变条纹平铺 */
  content: ''; position: fixed; inset: 0; pointer-events: none; z-index: 99;
  background: repeating-linear-gradient(0deg, rgba(0,0,0,.15) 0 1px, transparent 1px 3px);
  opacity: .5;              /* 克制：总强度换算后 ≤2% 等效 */
}
.crt::after {               /* 暗角：四边轻微压暗 */
  content: ''; position: fixed; inset: 0; pointer-events: none; z-index: 99;
  background: radial-gradient(ellipse at center, transparent 60%, rgba(0,0,0,.35) 100%);
}
.glow { text-shadow: 0 0 4px currentColor, 0 0 12px color-mix(in srgb, currentColor 40%, transparent); }
.flicker { animation: flick 4s infinite steps(1); }   /* 极低频随机亮度抖动 */
@keyframes flick { 0%,97%,100% {opacity:1} 98% {opacity:.86} 99% {opacity:.94} }
.cursor::after { content: '▊'; animation: blink 1s steps(1) infinite; }
@keyframes blink { 50% { opacity: 0 } }
```

- 扫描线 + 暗角 + 辉光三件套即可，**屏幕整幅滚动/弯曲变形（barrel distortion）只适合做全屏 hero 演示**，正文阅读区禁用。
- `flicker` 必须 `steps(1)` 离散跳变、占比 <3%，连续渐变会像劣质灯管。
- 所有这些层 `pointer-events: none` 且放 `::before/::after`，不污染 DOM。

### 3.8 等宽校准：把「字符格」量出来再采样

纵横比 0.55、`letter-spacing: -0.05em` 都是**起点值**，不是终点值——它们只对某一款字体在某一字号下成立。换字体/换字号后不重新量，图像必变形。本节是 §3.5 与 image-to-ascii.md §2.1 之间的校准环节。

```js
// 量出当前字体下「一个字符格」的实际像素尺寸，反推本项目的纵横比
function measureCell(pre) {
  const ctx = document.createElement('canvas').getContext('2d');
  const cs = getComputedStyle(pre);
  ctx.font = `${cs.fontSize} ${cs.fontFamily}`;      // 与 <pre> 完全同字体同字号
  const w = ctx.measureText('M'.repeat(10)).width / 10;   // 半角基准：10 个字符取均值，抗 hinting 抖动
  const h = parseFloat(cs.lineHeight) || parseFloat(cs.fontSize) * 1.2;
  return { w, h, aspect: w / h };
}

// 用实测 aspect 反算行数（替换写死的 0.55）
function rowsFor(srcW, srcH, cols, aspect) {
  return Math.max(1, Math.round(cols * (srcH / srcW) * aspect));
}
```

- **`aspect` 就是契约里的 0.55 的实测值**：`w / h` 落在 0.5–0.66 区间内时，直接把实测值传给 `rowsFor`；落在区间外说明字体/字号组合不合适（过窄或过扁），换字体而不是硬调系数。
- `letter-spacing` 会改变 `measureText` 的结果吗？**不会**——Canvas 的 `measureText` 不应用 CSS 字距。若 `<pre>` 用了负字距，实测宽度要乘 `(1 + letterSpacing/fontSize)`；简单做法是把 `letter-spacing` 设为 0 再采样，采样完在 CSS 里加回去（缩放后的网格整体等比变化，不影响字符映射）。
- **CJK 字体必须量全角**：`measureText('中')` 与 `measureText('M')` 的比值应为 2.0；不是 2.0 就说明字体回退链不对（见 image-to-ascii.md §2.6 方案 2）。
- **字体加载竞态**：Web Font 未就绪时 `measureText` 拿到的是回退字体的宽度，采样会按错的 aspect 走。用 `await document.fonts.ready` 再量，或 `document.fonts.load('16px MyMono')` 后量。
- 校准结果**记进视觉契约副本**：项目里把实测 `aspect`、`fontFamily`、`fontSize`、`letterSpacing` 写成一个 `VISUAL` 常量对象，三端（HTML/Python/C）都从这里取——这与 SKILL.md §1.2 的「单一事实源」同一逻辑，只是粒度到项目。

### 3.9 构建期资产管线（预生成字符帧：离线可用 / 秒开 / 天然兜底）

**运行时采样 vs 构建期预生成的选择**：

| 场景 | 选哪条 | 理由 |
|---|---|---|
| 素材固定、追求秒开与离线可用 | 构建期（本节） | 首帧 ≈ 0ms；无解码失败风险；弱网零依赖 |
| 素材来自用户上传 / 摄像头实时流 | 运行时（§3.1–§3.2） | 构建期不存在"未来"的素材 |
| 大 GIF（>2MB）或视频片段 | 构建期 | 产物 JSON 通常比原素材小一个量级，且免 gifuct-js 运行时开销 |
| 要导出 Remotion 视频 | 构建期 | 帧序列是渲染期最稳的喂数方式（remotion-video.md §R.6） |

**用法**（脚本自带零依赖自检，首次使用先跑 `self-test` 确认环境）：

```bash
python3 scripts/ascii_pipeline.py self-test                    # 环境自检（不需要任何依赖）
python3 scripts/ascii_pipeline.py hero.png --cols 120 --out public/hero.json --inline-first
python3 scripts/ascii_pipeline.py loop.gif  --cols 100 --out public/loop.json
python3 scripts/ascii_pipeline.py clip.mp4   --cols 140 --fps 12 --out public/clip.json
python3 scripts/ascii_pipeline.py serve --out public/loop.json # 本地实时预览（改参数重跑 convert，页面自动重载）
```

**实时预览（serve）**：调参迭代时省去"转一次开一次文件"的往返——起一个仅监听 `127.0.0.1` 的零依赖服务（默认端口 8765，`--port` 改），页面按 `meta.fps` 循环播放、每 1.5 秒探测一次产物时间戳，`frames.json` 变了就自动重载；Ctrl+C 停止。

依赖均可选：图片/GIF 用 Pillow（`pip install Pillow`），视频用 ffmpeg 抽帧（PPM 中转，后续纯标准库）；缺失时脚本给中文安装指引（国内镜像含在提示里）。

**输出契约**（`frames.json`）：

```json
{
  "meta": { "cols": 120, "rows": 44, "fps": 12, "ramp": " .:-=+*#%@",
            "aspect": 0.55, "source": "hero.png", "width": 1024, "height": 768, "frameCount": 1 },
  "frames": [" .-:=+#@ …\n…", "…"]
}
```

`meta` 与 SKILL.md §1.2 视觉契约同源（同 ramp / 纵横比 / COLS 甜点），三端与 Remotion 端共用同一份产物。

**网页端消费**（配合 §3.0 重试封装与首帧兜底）：

```js
// 首帧兜底：把 --inline-first 产出的 hero.first-frame.txt 内容直接写死在 HTML 里
const FALLBACK = ' .-:=+#@…（首帧字符串，服务端渲染时内联）';
try {
  const doc = await (await loadWithRetry('hero.json')).json();
  pre.textContent = doc.frames[0];                         // 静态：直接第一帧
  // 动画：按 meta.fps 调度（同 §3.1 的累计误差修正写法）
} catch {
  pre.textContent = FALLBACK;                              // 加载失败也不白屏（§3.0 三件套）
}
```

**喂 Remotion**：`import frames from '../public/frames.json'` 按帧取串——完整代码见 remotion-video.md §R.6。

