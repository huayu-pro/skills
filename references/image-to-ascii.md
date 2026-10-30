# 图像转 ASCII 完整技术手册

## 2.1 基础采样内核（像素 → 字符，图片/视频/GIF 共用）

```js
const RAMP = ' .:-=+*#%@';   // 亮 → 暗，视觉密度递增
const COLS = 120;            // 输出列数，甜点区间 80–160

function toAscii(ctx, src, srcW, srcH, darkBg = true) {
  // 字符格高约为宽的 2 倍，0.55 为纵横比修正系数（按字体微调 0.5–0.66）
  const rows = Math.max(1, Math.round(COLS * (srcH / srcW) * 0.55));
  // 注意：canvas 尺寸只在输入分辨率变化时重设，勿逐帧重分配（会触发 GPU buffer 重建掉帧）
  if (ctx.canvas.width !== COLS || ctx.canvas.height !== rows) {
    ctx.canvas.width = COLS;
    ctx.canvas.height = rows;
  }
  ctx.drawImage(src, 0, 0, COLS, rows);
  const { data } = ctx.getImageData(0, 0, COLS, rows);

  const lines = [];
  for (let y = 0; y < rows; y++) {
    const row = [];
    for (let x = 0; x < COLS; x++) {
      const i = (y * COLS + x) * 4;
      const a = data[i + 3] / 255;   // 预乘合成到页面底色（默认黑底 bgLum=0）
      const t = ((0.299 * data[i] + 0.587 * data[i + 1] + 0.114 * data[i + 2]) / 255) * a;
      const d = darkBg ? t : 1 - t;
      row.push(RAMP[Math.floor(d * (RAMP.length - 1))]);   // 契约索引公式（SKILL.md §1.2）
    }
    lines.push(row.join(''));
  }
  return lines.join('\n') + '\n';   // 行尾 \n 与原版逐字节一致
}
```

**ramp 设计**：
- 经典 10 级 `' .:-=+*#%@'` 够用；70 级长 ramp 仅在 160 列以上有收益，小图反而出噪点。
- **透明像素**：先按 alpha 合成到页面底色再取亮度（`t = lum * a`，黑底即 `bgLum=0`）；否则亮色透明区会输出最密字符形成亮斑。半块 `▀` 路线天然利用 alpha，不受此限。
- 海报化风格用方块 ramp `░▒▓█`（注意字体支持）。
- **ramp 可以是任意字符串**：品牌词、句子循环重复，可生成"文字构成图像"的效果。
- **彩色 ASCII**：不映射灰度，字符只承载明度；改用 Canvas 逐格 `fillText` + 原像素 `fillStyle`，避免海量 `<span>`。要精确色彩时取色源走 §2.3 浮点数据。
- **CJK 陷阱**：全角字符占两格宽，混入 ASCII 网格会错位。要么整个网格统一用全角字符（列数减半），要么避开；不要混排。确需混排时走 §2.6 的三条对齐方案。
- 映射到空格的格子注意行宽塌陷，必要时输出 `&nbsp;`。

## 2.2 精度档位表

| 档位 | 手段 | 适用 |
|---|---|---|
| 标准 | 10 级 ramp，80–120 列 | 装饰、背景、小图 |
| 高清 | 24 级 ramp `' .\'",:;Il!i><~+_-?][}{1)(|/tfjrxnuvczXYUJCLQ0OZmwqpdbkhao*#MW&8%B@$'`（暗→亮），160–240 列 | hero 主视觉、人像 |
| 超高清 | 70 级长 ramp + 有序抖动（Bayer 4×4 阈值矩阵，见 web-implementation.md §3.4 的 GPU 版与 §2.4 的 CPU 版） | 海报级静态作品 |
| 线稿 | **盲文点阵**：每字符格编码 2×4 子像素点，横纵分辨率 ×2/×4 | 轮廓、图标、矢量感图形 |

- 长 ramp 仅在 160 列以上有收益，小图反而出噪点。ghostty.org 首页正是长 ramp 多灰度路线的范例。
- **盲文内核**：采样 2×4 像素块，阈值二值化后按盲文位序拼成 U+2800 起始的字符。`⠁⠂⠄⡀` 分别是 U+2801 / U+2802 / U+2804 / U+2840，即 bit 0 / 1 / 2 / 6。2×4 网格的正确映射：**左列（x=0）自上而下 bit 0,1,2,6，右列（x=1）自上而下 bit 3,4,5,7**；位运算公式 `bit(x,y) = y < 3 ? y + 3*x : 6 + x`，拼字即 `chr(0x2800 + bits)`。边缘检测（Sobel 或简单梯度）后接盲文，出线稿效果。

| 位 | 点 | 2×4 格内位置 | 字符 |
|---|---|---|---|
| 0 | dot1 | 左上 | ⠁ |
| 1 | dot2 | 左中 | ⠂ |
| 2 | dot3 | 左下偏上 | ⠄ |
| 3 | dot4 | 右上 | ⠈ |
| 4 | dot5 | 右中 | ⠐ |
| 5 | dot6 | 右下偏上 | ⠠ |
| 6 | dot7 | 左下 | ⡀ |
| 7 | dot8 | 右下 | ⢀ |
- **半块字符 `▀`**：前景色=上半像素、背景色=下半像素，纵向分辨率翻倍且保留彩色——彩色 ASCII 的性价比之王。

## 2.3 浮点彩色内核（静态图像 → 浮点数值，像素级彩色复刻）

**功能层级（L1 采集 → L2 精度 → L3 交换 → L4 消费）**：

**L1 采集内核**：

```js
async function imageToFloat(url, { maxW = 0, alpha = true } = {}) {
  const img = new Image();
  img.crossOrigin = 'anonymous';
  await (img.src = url, img.decode());
  const scale = maxW && img.width > maxW ? maxW / img.width : 1;
  const w = Math.round(img.width * scale), h = Math.round(img.height * scale);
  const ctx = Object.assign(document.createElement('canvas'), { width: w, height: h })
    .getContext('2d', { willReadFrequently: true });
  ctx.drawImage(img, 0, 0, w, h);
  const { data } = ctx.getImageData(0, 0, w, h);
  const C = alpha ? 4 : 3;
  const f32 = new Float32Array(w * h * C);
  for (let s = 0, d = 0; s < data.length; s += 4, d += C) {
    f32[d] = data[s] / 255; f32[d + 1] = data[s + 1] / 255; f32[d + 2] = data[s + 2] / 255;
    if (C === 4) f32[d + 3] = data[s + 3] / 255;
  }
  return { data: f32, width: w, height: h, channels: C,
           colorspace: 'srgb', premultiplied: false };
}
```

**L2 精度档位**：float32（通用）/ float16（显示级）/ uint16 量化（紧凑）/ toFixed(4)（调试）。

**L3 交换格式**：JSON（调试）、`.f32` 裸二进制（跨端直读）、PFM（Blender/OpenCV 生态原生认）。

> **PFM 行序陷阱**：PFM 规定行为**底向上**（与图像内存顶向上相反），Blender/OpenCV 读写时不提示。落盘前必须垂直翻转，并在元数据记录 `rowOrder: 'top-down'`：
> ```js
> function flipRows(data, w, h, C) {
>   const out = new Float32Array(data.length);
>   for (let y = 0; y < h; y++) {
>     const s = y * w * C, d = (h - 1 - y) * w * C;
>     out.set(data.subarray(s, s + w * C), d);
>   }
>   return out;
> }
> ```

**L4 消费**：彩色 ASCII（亮度→ramp，RGB→fillStyle）、WebGL2 `RGBA32F` 纹理、半块 `▀` 双色渲染。

**体积红线**：原图分辨率直接浮点化只适用于 ≤512px 的素材；更大图先按显示网格降采样。

## 2.4 Halftone 有序抖动内核（网点肖像 / 报纸印刷质感）

白底 + 黑点，暗部聚点成面、亮部散点稀疏——打印机的二值化美学。

```js
const BAYER4 = [0,8,2,10,12,4,14,6,3,11,1,9,15,7,13,5];
function halftone(ctx, src, srcW, srcH, COLS = 160) {   // 默认取契约甜点上沿（SKILL.md §1.2）
  const rows = Math.round(COLS * (srcH / srcW) * 0.55);
  if (ctx.canvas.width !== COLS || ctx.canvas.height !== rows) {
    ctx.canvas.width = COLS; ctx.canvas.height = rows;
  }
  ctx.drawImage(src, 0, 0, COLS, rows);
  const { data } = ctx.getImageData(0, 0, COLS, rows);
  let out = '';
  for (let y = 0; y < rows; y++) {
    for (let x = 0; x < COLS; x++) {
      const i = (y * COLS + x) * 4;
      const lum = ((0.299 * data[i] + 0.587 * data[i+1] + 0.114 * data[i+2]) / 255) * (data[i+3] / 255);
      const threshold = BAYER4[(y % 4) * 4 + (x % 4)] / 16;
      out += (lum < threshold) ? '•' : ' ';
    }
    out += '\n';
  }
  return out;
}
```

要点：输出严格二值（空格+点），不要混入 ramp；**列数口径**（三处统一，SKILL.md §7 第 15 条同此）：默认 **160**（契约甜点 80–160 的上沿，4×4 Bayer 一个周期 = 4 列，160 恰好整除，网点不出现半周期断带），细粒肖像可上探 **240**（此时 Bayer 周期会在行尾截断，需按 `x % 4` 对齐起始相位），**任何情况不得低于 80**；`font-family: "Courier New", monospace; font-size: 6px–10px`。反相：黑底白点阈值取反 + 换 `○`。

## 2.5 SVG / 矢量 → ASCII（path 栅格化路线）

矢量素材（logo、图标、地图轮廓、图表导出）不要当普通位图直接采样——位图采样在细线处会因降采样直接丢线。正确做法是**先栅格化到足够高的分辨率，再降采样**，或用**覆盖率采样**替代点采样。

### 路线 A：SVG → 高分辨率栅格 → 采样（最省事，浏览器端）

```js
// 1) 把 SVG 当图片加载，按「目标网格 × 超采样倍数」设定栅格尺寸
async function svgToAscii(svgUrl, { cols = 120, supersample = 4, ramp = ' .:-=+*#%@' } = {}) {
  const img = new Image();
  img.crossOrigin = 'anonymous';
  img.src = svgUrl;
  await img.decode();                        // SVG 必须有内联 width/height 或 viewBox，否则尺寸为 0

  const rows = Math.max(1, Math.round(cols * (img.naturalHeight / img.naturalWidth) * 0.55));
  const c = document.createElement('canvas');
  c.width = cols * supersample;              // 超采样：每字符格 4×4 像素
  c.height = rows * supersample;
  const ctx = c.getContext('2d', { willReadFrequently: true });
  ctx.fillStyle = '#000';                    // 深底：先把底色铺满，矢量透明区才不会被当作「黑线」
  ctx.fillRect(0, 0, c.width, c.height);
  ctx.drawImage(img, 0, 0, c.width, c.height);   // 浏览器矢量渲染，边缘抗锯齿
  const { data } = ctx.getImageData(0, 0, c.width, c.height);

  // 2) 覆盖率采样：每格取 supersample² 个像素的亮度均值，细线不再随机丢失
  const lines = [];
  for (let y = 0; y < rows; y++) {
    let line = '';
    for (let x = 0; x < cols; x++) {
      let sum = 0;
      for (let sy = 0; sy < supersample; sy++) {
        for (let sx = 0; sx < supersample; sx++) {
          const i = (((y * supersample + sy) * c.width) + (x * supersample + sx)) * 4;
          sum += (0.299 * data[i] + 0.587 * data[i + 1] + 0.114 * data[i + 2]) / 255;
        }
      }
      const lum = sum / (supersample * supersample);
      line += ramp[Math.min(ramp.length - 1, Math.floor(lum * (ramp.length - 1)))];  // 契约索引公式
    }
    lines.push(line);
  }
  return lines;
}
```

- **为什么必须超采样**：SVG 的笔画常是 1–2 个单位宽。直接 `drawImage(img, 0, 0, cols, rows)` 时，浏览器先按目标尺寸抗锯齿，细线被抹成 10% 灰——再乘 ramp 就只剩空格。4×4 超采样后取均值，1px 线在 16 个采样点里仍占 4 个，覆盖率 25% 稳稳落在中段字符。
- `supersample = 4` 是性价比点（每格 16 次读取）；`cols ≥ 200` 的大图降到 2，否则 `getImageData` 本身成为瓶颈。
- **SVG 尺寸陷阱**：没有 `width`/`height` 属性只有 `viewBox` 的 SVG，部分浏览器 `naturalWidth` 为 0。加载前用 `fetch` 读文本，补上 `width`/`height` 或用 `img.width = viewBox 宽`。
- **CSS 变量 / 外部字体**：`<img>` 方式加载的 SVG 不执行脚本、不加载外部字体（安全，但也意味着 `<text>` 元素的字形可能退化成默认字体）。要精确控制字形，先在编辑器里把文字转曲（outline）。

### 路线 B：Path2D 覆盖率采样（无抗锯齿干扰，精度最高）

只关心「图形占了多少面积」时，直接遍历 path 做点内测试，完全绕开抗锯齿：

```js
function pathCoverage(path2d, cols, rows, samples = 4) {
  const lines = [];
  for (let y = 0; y < rows; y++) {
    let line = '';
    for (let x = 0; x < cols; x++) {
      let hit = 0;
      for (let sy = 0; sy < samples; sy++) {
        for (let sx = 0; sx < samples; sx++) {
          const px = x + (sx + 0.5) / samples, py = y + (sy + 0.5) / samples;
          if (ctx.isPointInPath(path2d, px, py)) hit++;
        }
      }
      const cov = hit / (samples * samples);          // 0–1 覆盖率
      line += ' .:-=+*#%@'[Math.min(9, Math.floor(cov * 9))];
    }
    lines.push(line);
  }
  return lines;
}
```

- `ctx.isPointInPath` 需要 `ctx` 的当前变换矩阵把 path 坐标映射到采样坐标系；先把 `ctx.setTransform(cols / vbW, 0, 0, rows / vbH, 0, 0)` 设好。
- 只适用于 `Path2D` / 内联 `<path>`；对外部 SVG 文件，先 `fetch` 文本、`DOMParser` 解析、取出 `d` 属性再 `new Path2D(d)`。
- 覆盖率天然是 0–1，与亮度同为线性量，可直接喂契约索引公式——**这是矢量路线里唯一不依赖渲染器抗锯齿行为的实现**。

### 路线 C：构建期栅格化（离线 / 三端 / 视频）

Node 侧用 `resvg-js` 或 `sharp`（libvips 内置 librsvg）把 SVG 转成高分辨率 PNG，再交给 `scripts/ascii_pipeline.py`：

```bash
npx @resvg/resvg-js-cli logo.svg -w 960 logo@4x.png   # 4× 目标列数栅格化
python3 scripts/ascii_pipeline.py logo@4x.png --cols 120 --out public/logo.json
```

- 构建期路线天然可复现（同 SVG 同版本 → 同 PNG → 同 ASCII），适合 Remotion 与三端交付。
- **不要**用 `--cols` 直接等于 SVG 宽度：先 4× 栅格化再由管线降采样，等价于路线 A 的超采样。
- 栅格化器差异：librsvg 与 Chrome 对渐变/滤镜的渲染有细微差别，跨端一致要求三端用同一份 PNG（管线产物），不要让 Python 和 C 各自栅格化。

### 矢量路线的验收补充

| 检查 | 判据 |
|---|---|
| 细线存活 | 原 SVG 里最细的笔画，在输出网格里至少有一处非空格字符 |
| 无意外实心 | 闭合图形的内部不应整片是 `@`——除非原图确实实心 |
| 尺寸正确 | `naturalWidth/naturalHeight` 非 0；`rows = round(cols × h/w × 0.55)` 与契约一致 |
| 跨端一致 | 矢量路线**先出 PNG 再进管线**；三端只消费管线产物，不各自栅格化 |

## 2.6 CJK / 全角网格的等宽替代方案

`image-to-ascii.md §2.1` 与 SKILL.md §4 第 7 条都说「不要混排全角与半角」——但中文产品几乎必然要在字符画里放中文标题。以下是三条可行路线，按侵入性从低到高。

### 先搞清楚宽度契约

| 字符类 | 终端宽度 | 浏览器 `<pre>` 宽度 | 备注 |
|---|---|---|---|
| ASCII 32–126 | 1 格 | 1 个 `ch` 单位（等宽字体） | ramp 的原料 |
| 全角 CJK（U+4E00–9FFF 等） | **2 格** | 通常 2×，但**取决于字体** | JetBrains Mono 无 CJK 字形，会回退到系统中文字体 → 宽度不再受控 |
| 半角片假名 `ｱｲｳ`（U+FF66–FF9D） | 1 格 | 1× | Matrix 预设安全区 |
| emoji | **不确定**（多数 2 格，部分 1 格） | 不确定 | 永远不要进网格 |
| 组合字符 / 变体选择符 | 0 格（叠加） | 0 | 不要进网格 |

**关键结论**：全角宽度在**终端里是硬契约（2 格）**，在**浏览器里是软契约（看字体）**。所以 CJK 方案必须按渲染载体分。

### 方案 1：全角补位（终端优先，零依赖）

把网格里的每一格都当成「2 个半角宽」，非 CJK 字符后面补一个空格。这样终端与浏览器都稳定。

```js
// 判断是否需要补位：CJK / 全角标点 / 全角片假名 视为 2 格
const WIDE = /[\u1100-\u115F\u2E80-\uA4CF\uAC00-\uD7A3\uF900-\uFAFF\uFE30-\uFE6F\uFF00-\uFF60\uFFE0-\uFFE6]/;
function padWide(ch) { return WIDE.test(ch) ? ch : ch + ' '; }

function renderWideGrid(grid) {                  // grid: string[]
  return grid.map(line => Array.from(line).map(padWide).join(''));
}
```

- 代价：网格横向物理宽度翻倍，等效列数减半。所以用这方案时 `cols` 取目标视觉宽度的 **1/2**（120 列的视觉密度 → 传 60）。
- 适合：**终端版**（Python/C）、需要与终端输出对齐的网页（例如网页里嵌一个 `<pre>` 模拟终端）。
- 不适合：纯网页作品——空格补位会让字距看起来松散，且无法用 CSS 修正。

### 方案 2：CJK 感知的列宽计算（网页优先）

不补位，而是让**采样网格**与**显示网格**使用不同的坐标：采样时按视觉格算，渲染时按实际字符宽度排。

```js
// 一行字符 → 视觉宽度（以半角格为单位）
function visualWidth(s) {
  let w = 0;
  for (const ch of s) w += WIDE.test(ch) ? 2 : 1;
  return w;
}

// 用 CSS Grid 而不是 <pre> 的等宽排版：每个字符一个格子，跨列数由宽度决定
function renderGridDom(grid) {
  const frag = document.createDocumentFragment();
  for (const line of grid) {
    const row = document.createElement('div');
    row.className = 'ascii-row';                 // display: grid; grid-auto-flow: column;
    for (const ch of line) {
      const cell = document.createElement('span');
      cell.textContent = ch === ' ' ? '\u00A0' : ch;   // 空格必须用 nbsp，否则格子塌陷
      if (WIDE.test(ch)) cell.style.gridColumn = 'span 2';
      row.appendChild(cell);
    }
    frag.appendChild(row);
  }
  return frag;
}
```

配合 CSS：

```css
.ascii-row {
  display: grid;
  grid-auto-flow: column;
  grid-auto-columns: 1ch;        /* 1ch = 当前字体下 "0" 的宽度，半角基准 */
  line-height: 1;
  font-family: "JetBrains Mono", "Sarasa Mono SC", "Noto Sans Mono CJK SC", monospace;
}
```

- **字体选择是关键**：用**同时含 CJK 与半角的等宽字体**（Sarasa Mono SC / Noto Sans Mono CJK SC / IBM Plex Mono + Noto Sans CJK 回退），保证 2:1 宽度比是字体自带的，不靠浏览器回退猜测。
- `grid-auto-columns: 1ch` 让半角格宽恒等于 `1ch`；全角格 `span 2` 后宽 = `2ch`，与字体内部宽度一致（Sarasa 系列保证这个比例）。
- 代价：DOM 节点数 = 网格格数（160×60 = 9600 个 span）。**只适合静态或低频更新的 CJK 标题区**，动画网格仍用纯半角 + `<pre>`。

### 方案 3：混排时的网格对齐（最小侵入，推荐默认）

不改变渲染方式，只保证**每一行的视觉宽度一致**——这是最容易漏、也最容易做对的一条。

```js
// 把一行按视觉宽度补到 targetWidth（半角格单位），补空格在行尾
function alignRow(line, targetWidth) {
  const pad = targetWidth - visualWidth(line);
  return pad > 0 ? line + ' '.repeat(pad) : line;   // pad < 0 说明该行超宽，需截断
}

// 采样阶段：CJK 文案不参与亮度映射，作为「固定覆盖层」单独排版
// 1) 采样得到纯 ASCII 网格（cols 按视觉宽度算）
// 2) CJK 标题放独立元素（绝对定位 / 单独一行），不进网格
// 3) 必须进网格时（如字符画里嵌中文），把 CJK 字符视为「占 2 格的固定字符」，
//    在网格里占位、其后一格强制为空格，再走 alignRow
```

- **默认推荐这条**：CJK 标题用正常 HTML 层（`<h1>`）叠在字符画上，网格内保持纯 ASCII。视觉上完全成立（标题本来就是前景层），工程上零风险。
- 必须嵌入网格时，按「CJK 占 2 格 + 后一格留空」的规则处理，并用 `alignRow` 兜底行宽。

### 反模式（会翻车的写法）

| 写法 | 后果 |
|---|---|
| 中文文案直接拼进 ramp 字符串 | 每个中文字符吃掉 2 格，整行右移，网格逐行错位 |
| 用 `length` 计算 CJK 字符串宽度 | `'中文'.length === 2` 但视觉宽度是 4 |
| 用 `font-family: monospace` 指望中文也等宽 | 多数系统 monospace 不含 CJK，回退到比例中文字体 |
| emoji 放进字符画 | 宽度在 1–2 格之间随平台漂移，无法对齐 |
| 用 `<pre>` + 全角补位做网页作品 | 字距松散，且无法用 `letter-spacing` 修正（会同时影响半角） |

### 验收补充

- 抽查任意三行的**视觉宽度**相同（`visualWidth` 一致），不是 `line.length` 相同。
- 终端版跑一次 `wc -L`（最长行视觉宽度）与目标 `cols` 对照。
- 混排页面截图后，用肉眼确认中文与字符画的左边界对齐。

