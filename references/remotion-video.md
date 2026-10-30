# Remotion 路线：把 ASCII 动画渲染成视频（MP4 / WebM / GIF）

> 本文小节编号 R.1–R.10 为**文件本地编号**；跨文件引用本文时写 `remotion-video.md §R.x`。
> API 事实来源：Remotion v4.0.538 源码（packages/core、packages/effects），以下签名均已对照源码核验。

**Remotion 是什么**：用 React 组件写视频的框架。每"帧"就是一次组件渲染，`useCurrentFrame()` 返回当前帧号，导出时逐帧截图合成 MP4。对 ASCII 动画而言它是**帧驱动画布的天然宿主**：字符网格本来就是"给定帧号 → 确定性输出一张网格"的纯函数。

## R.1 何时选 Remotion（决策表）

| 用户需求 | 选 Remotion？ | 理由 / 替代 |
|---|---|---|
| 把字符动画导出成 MP4 / WebM / GIF | ✅ 唯一正解 | 浏览器路线只能录屏，帧率不精确 |
| 多场景时间线（片头→正文→片尾、转场） | ✅ | `<Sequence>`/`<Series>` 精确到帧的编排 |
| 音画同步（音乐可视化视频、配音字符动画） | ✅ | `<Audio>` + 帧时间线天然同步 |
| 帧精确的可复现动画（同输入必出同片） | ✅ | `random(seed)` 确定性随机保证跨线程一致 |
| 批量渲染（模板 + 数据生成 N 条视频） | ✅ | 编程式渲染，参数化 Composition |
| 网页内实时交互（鼠标、滚动、摄像头） | ❌ | 走 web-implementation.md / scroll-and-pointer.md，Remotion 是离线渲染 |
| 单张静态字符画 | ❌ | 杀鸡用牛刀，image-to-ascii.md §2.1 即可 |

**一句话**：要"文件产物"（视频）选 Remotion，要"页面行为"（交互）选浏览器路线；两者共用同一套视觉契约（SKILL.md §1.2）与采样内核（image-to-ascii.md §2.1）。

## R.2 概念映射表（ASCII 思维 → Remotion 思维）

| 你熟悉的写法 | Remotion 等价物 | 说明 |
|---|---|---|
| `requestAnimationFrame` 帧循环 | `useCurrentFrame()` | 返回组件本地帧号（`<Sequence>` 内自动偏移），不写循环 |
| `setInterval` / 逐帧 delay 调度 | `<Composition fps>` 时间线 | fps 定死（常用 30），帧号即时间：`秒 = frame / fps` |
| `Math.random()` | `random(seed)` | **必须**换：多线程渲染时 `Math.random()` 各线程不一致，必出鬼影 |
| 亮度 ramp 映射 | `renderGrid(frame)` 纯函数 | 每帧重算整个网格字符串，喂给 `<pre>`；确定性是硬要求 |
| CSS `animation` / `transition` | `interpolate(frame, ...)` 内联 | CSS 动画在逐帧渲染下**不可用**，必须重构为帧驱动 |
| 弹簧回弹 | `spring({frame, fps, config})` | 返回 0→1；注意 SKILL.md §4 "机器不回弹"，字符动画用高 damping |
| 素材相对路径 | `staticFile('a.png')` | 引用项目根 `public/` 下的文件 |

## R.3 五分钟上手

```bash
# 空目录脚手架（--blank 空模板，--no-tailwind 避免多余依赖）
npx create-video@latest --yes --blank --no-tailwind .
npm i
npx remotion studio        # 立即开预览，先看空项目能跑再写代码
```

**等宽字体红线（国内网络）**：不要用 `@remotion/google-fonts`（依赖 Google Fonts CDN，国内不稳）。用系统等宽栈或本地字体文件：

```tsx
import {loadFont} from '@remotion/fonts';   // v4 内置字体加载器
import {staticFile} from 'remotion';

// 方案 A（推荐）：系统等宽栈，零下载零风险
const MONO = '"JetBrains Mono", "IBM Plex Mono", "Courier New", monospace';

// 方案 B：本地字体文件放 public/，加载完成前自动阻塞渲染
loadFont({family: 'MyMono', url: staticFile('mono.woff2')});
```

**最小示例「AsciiReveal」**（字符逐个浮现——打字机的近亲）：

```tsx
// src/AsciiReveal.tsx
import {AbsoluteFill, interpolate, useCurrentFrame, useVideoConfig} from 'remotion';

const TEXT = 'HELLO ASCII';  // 待揭示的字符画第一行（多行同理按网格展开）

export const AsciiReveal: React.FC = () => {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();

  // 每个字符 opacity 由帧号插值驱动；内联在 style 里 Studio 才能编辑关键帧
  const chars = TEXT.split('').map((ch, i) => ({
    ch,
    opacity: interpolate(
      frame,
      [i, i + fps * 0.4],           // 第 i 帧开始浮现，约 0.4 秒完成
      [0, 1],
      {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'},
    ),
  }));

  return (
    <AbsoluteFill style={{backgroundColor: '#000', justifyContent: 'center', alignItems: 'center'}}>
      <div style={{fontFamily: MONO, fontSize: 64, color: '#00FF41', letterSpacing: '-0.05em'}}>
        {chars.map((c, i) => (
          <span key={i} style={{opacity: c.opacity}}>{c.ch === ' ' ? '\u00A0' : c.ch}</span>
        ))}
      </div>
    </AbsoluteFill>
  );
};
```

```tsx
// src/index.ts —— 注册（id 必须是字符串字面量；durationInFrames = 秒数 × fps）
import {Composition} from 'remotion';
import {AsciiReveal} from './AsciiReveal';

export const RemotionRoot: React.FC = () => (
  <Composition
    id="AsciiReveal"
    component={AsciiReveal}
    durationInFrames={150}   // 5 秒 × 30fps
    fps={30}
    width={1920}
    height={1080}
  />
);
```

## R.4 完整示例 A「AsciiRain」——字符雨导出 MP4

核心差异：网页版字符雨（web-implementation.md §3.5）用"每帧在上帧基础上叠加拖尾"；Remotion 里**每帧独立成图**，不能依赖上一帧的画布残留——拖尾改为**纯函数回看**：列头位置由帧号直接算出，尾迹画同帧内完成。

```tsx
// src/AsciiRain.tsx
import {AbsoluteFill, random, useCurrentFrame, useVideoConfig} from 'remotion';

const CHARS = 'ｱｲｳｴｵｶｷｸｹｺ0123456789';              // 半角片假名 + 数字（视觉契约同 §3.5）
const COLS = 120;
const ASPECT = 0.55;                                   // 视觉契约（SKILL.md §1.2）
const ROWS = Math.round(COLS * (9 / 16) * ASPECT);     // = 37：1920×1080 幅面按 16:9 与 0.55 修正
// 别把 ROWS 写死成 40：40 对应 16:9 × 0.625，字符会被纵向拉长 8%（列头落点与尾长全部偏移）。
// 竖屏交付（1080×1920）时改成 Math.round(COLS * (16 / 9) * ASPECT) = 117，并同步 composition 尺寸。

// 列模型：random(字符串种子) 保证任意线程/任意次渲染结果一致
// 种子不含帧号 → 列参数全程稳定（速度/相位/尾长开片即定，永不漂移）
const columns = new Array(COLS).fill(0).map((_, i) => ({
  speed: 0.6 + random(`speed-${i}`) * 1.2,        // 每帧下落 0.6–1.8 行
  offset: random(`offset-${i}`) * ROWS * 2,       // 错开各列起始相位
  tail: 8 + Math.floor(random(`tail-${i}`) * 16), // 尾长 8–24
}));

export const AsciiRain: React.FC = () => {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();
  const t = frame / fps;

  // 每帧从列模型纯函数生成两张网格（身体 + 列头），不读上一帧
  const body: string[] = [], heads: string[] = [];
  for (let y = 0; y < ROWS; y++) { body.push(' '.repeat(COLS)); heads.push(' '.repeat(COLS)); }
  const put = (g: string[], x: number, y: number, ch: string) => {
    if (y >= 0 && y < ROWS) g[y] = g[y].substring(0, x) + ch + g[y].substring(x + 1);
  };
  for (let x = 0; x < COLS; x++) {
    const c = columns[x];
    const head = Math.floor((c.offset + t * c.speed * fps) % (ROWS + c.tail));
    put(heads, x, head, CHARS[Math.floor(random(`ch-${x}-${head}-${Math.floor(frame / 6)}`) * CHARS.length)]);
    for (let k = 1; k < c.tail; k++) {
      // 字符每 6 帧换一次（闪烁感），同帧内恒定；15% 概率留空造"断尾"
      if (random(`c-${x}-${head - k}-${Math.floor(frame / 6)}`) > 0.15) {
        put(body, x, head - k, CHARS[Math.floor(random(`ch-${x}-${head - k}-${Math.floor(frame / 6)}`) * CHARS.length)]);
      }
    }
  }

  const preStyle: React.CSSProperties = {
    fontFamily: MONO, fontSize: 24, lineHeight: 1, margin: 0,
    whiteSpace: 'pre', position: 'absolute', inset: 0,
    display: 'flex', alignItems: 'center', justifyContent: 'center',
  } as const;

  return (
    <AbsoluteFill style={{backgroundColor: '#000'}}>
      {/* 两层同尺寸 pre 叠放：身体暗绿打底，列头亮绿覆盖（替代网页版"上帧残留"拖尾） */}
      <pre style={{...preStyle, color: '#0a0'}}><code>{body.join('\n')}</code></pre>
      <pre style={{...preStyle, color: '#e8ffe8'}}><code>{heads.join('\n')}</code></pre>
    </AbsoluteFill>
  );
};
```

> 演示要点：`random(`speed-${i}`)` 的种子**不含帧号** → 列参数全程稳定；`random(`ch-...-${floor(frame/6)}`)` 的种子**含 floor(frame/6)** → 字符每 6 帧换一次（闪烁感），同帧内恒定。这个"种子分层"技巧是 Remotion 字符动画的核心心法：**结构性参数用稳定种子，闪烁性细节用带帧号的种子**。

## R.5 完整示例 B：图片 → ASCII 动画（异步采样）

图片解码是异步的，必须用 `delayRender()` 挡住渲染，就绪后 `continueRender()`：

```tsx
// src/AsciiImage.tsx
import {AbsoluteFill, Img, delayRender, continueRender, cancelRender,
        interpolate, staticFile, useCurrentFrame, useVideoConfig} from 'remotion';
import {useState} from 'react';

const RAMP = ' .:-=+*#%@';                       // 视觉契约（SKILL.md §1.2）
const COLS = 160, ASPECT = 0.55;                 // 纵横比修正：字符格高瘦

function sampleToGrid(img: HTMLImageElement, cols: number): string[] {
  const rows = Math.floor(img.naturalHeight / img.naturalWidth * cols * ASPECT);
  const c = document.createElement('canvas');
  c.width = cols; c.height = rows;
  const ctx = c.getContext('2d')!;
  ctx.drawImage(img, 0, 0, cols, rows);          // 降采样一步到位
  const d = ctx.getImageData(0, 0, cols, rows).data;
  const grid: string[] = [];
  for (let y = 0; y < rows; y++) {
    let line = '';
    for (let x = 0; x < cols; x++) {
      const i = (y * cols + x) * 4;
      const a = d[i + 3] / 255;                  // alpha 预乘合成黑底
      const lum = (0.299 * d[i] + 0.587 * d[i + 1] + 0.114 * d[i + 2]) / 255 * a;
      line += RAMP[Math.floor(lum * (RAMP.length - 1))];   // 契约索引公式（SKILL.md §1.2）
    }
    grid.push(line);
  }
  return grid;
}

export const AsciiImage: React.FC = () => {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();
  // 挡住渲染直到图片就绪；handle 用 useState 只创建一次
  const [handle] = useState(() => delayRender('等待 ASCII 源图解码'));
  const [grid, setGrid] = useState<string[] | null>(null);

  // 图片解码（自带失败分支：cancelRender 传入中文错误，渲染日志直接可读）
  const source = (
    <Img
      src={staticFile('logo.png')}
      style={{position: 'absolute', width: 1, height: 1, opacity: 0}}  // 只作帧源，不显示
      onLoad={async (e) => { setGrid(sampleToGrid(e.currentTarget, COLS)); continueRender(handle); }}
      onError={(e) => cancelRender(new Error(`源图加载失败：${staticFile('logo.png')}，请检查 public/ 目录与文件名（当前错误：${e.type}）`))}
    />
  );
  if (!grid) return <AbsoluteFill style={{backgroundColor: '#000'}}>{source}</AbsoluteFill>;

  // 入场：逐行揭示（行 opacity 按帧插值，衔接 animation-patterns.md §P.7 级联）
  return (
    <AbsoluteFill style={{backgroundColor: '#000', justifyContent: 'center', alignItems: 'center'}}>
      {source}
      <pre style={{fontFamily: MONO, fontSize: 12, lineHeight: 1, color: '#00FF41', margin: 0}}>
        {grid.map((row, i) => (
          <div key={i} style={{opacity: interpolate(frame, [i * 1.5, i * 1.5 + fps * 0.5], [0, 1],
            {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'})}}>
            {row}
          </div>
        ))}
      </pre>
    </AbsoluteFill>
  );
};
```

> 采样内核与 image-to-ascii.md §2.1 **同一算法同一 RAMP**——这是"网页版与视频版同一视觉语言"的保证（三端一致性契约同样适用于视频端）。

## R.6 帧序列模式（大素材首选）

GIF / 视频这类多帧素材，与其在渲染期解码（慢、易错），不如**构建期预转**：用 `scripts/ascii_pipeline.py`（见 web-implementation.md §3.9）生成 `frames.json`，运行时按帧取串：

```tsx
import frames from '../public/frames.json';   // 构建期产物，直接 import 零 IO
// frames.meta = {cols, rows, fps, ramp, aspect, source, width, height}

export const AsciiFromPipeline: React.FC = () => {
  const frame = useCurrentFrame();
  const idx = frame % frames.frames.length;   // 循环
  return <pre style={{fontFamily: MONO, lineHeight: 1}}>{frames.frames[idx]}</pre>;
};
```

- 管线已按视觉契约统一 ramp / 列数 / 纵横比，视频端不再二次采样。
- `calculateMetadata` 可按素材定 composition 时长（见 §R.8）。

## R.7 特效叠加：@remotion/effects 的 CRT / 网点

`@remotion/effects` 提供 canvas 基组件（`<CanvasImage>` / `<Video>` 等）的 `effects` 数组，其中多个效果天生适配 ASCII 美学（参数已对照 v4.0.538 源码）：

| 效果工厂 | 关键参数（默认值） | 用途 |
|---|---|---|
| `scanlines({strength, lineDistance, thickness, offset})` | 0.15 / 4px / 1px / 0 | CRT 扫描线（等价 web-implementation.md §3.7 的 CSS 版） |
| `whiteNoise({...})` | — | 静态噪声，胶片颗粒 |
| `pixelate({...})` | blockSize | 像素化（马赛克入场） |
| `dotGrid({...})` | dotSize, gridSize | 网点网格（halftone 近亲） |
| `halftone({...})` | dotSize, shape: circle/square/line | 报纸网点质感 |
| `pixelDissolve({...})` | — | 像素溶解转场（衔接 animation-patterns.md §P.4） |

```tsx
import {CanvasImage} from 'remotion';
import {scanlines, whiteNoise} from '@remotion/effects';

<CanvasImage src={staticFile('cover.png')} effects={[scanlines({strength: 0.25}), whiteNoise()]} />
```

- effects 走 WebGL2，**渲染命令需加 `--gl=angle`**（Linux 尤其）。
- 纯字符层（`<pre>` 文本）不走 effects；要 CRT 质感叠在字符画上，用 CSS 等价物（背景条纹 + 暗角）或把字符画绘进 `<CanvasImage>`。

## R.8 calculateMetadata：按素材定尺寸与时长

源图宽高比各不相同时，写死 width/height 会变形。用 `calculateMetadata` 动态返回：

```tsx
import {getImageDimensions} from '@remotion/media-utils';   // 读图尺寸（异步）

<Composition
  id="AsciiImage"
  component={AsciiImage}
  durationInFrames={300}
  fps={30}
  width={1920}
  height={1080}
  calculateMetadata={async ({props}) => {
    const {width, height} = await getImageDimensions(staticFile(props.src));
    return {width: 1920, height: Math.round(1920 * height / width)};  // 按源图比例
  }}
  defaultProps={{src: 'logo.png'}}
/>
```

## R.9 命令表

| 目的 | 命令 |
|---|---|
| 预览（带时间轴 scrub） | `npx remotion studio`（已启动则打印 URL；指定组合 `http://localhost:3000/<id>`） |
| 导出 MP4 | `npx remotion render src/index.ts <CompositionId> out.mp4` |
| 导出封面静图 | `npx remotion still src/index.ts <CompositionId> cover.png` |
| 抽帧检查 | `npx remotion render <id> out/frames --frames=0,30,90 --image-format=png` |
| 透明背景（WebM） | `npx remotion render <id> out.webm --codec=vp9 --pixel-format=yuva420p --image-format=png` |
| 透明背景（ProRes） | `npx remotion render <id> out.mov --codec=prores --prores-profile=4444 --image-format=png --pixel-format=yuva444p10le` |
| WebGL/effects 渲染 | 追加 `--gl=angle`（或在 remotion.config.ts 设 `Config.setChromiumOpenGlRenderer('angle')`） |

## R.10 红线与坑（违反必翻车）

1. **禁用 `Math.random()`**：Remotion 多线程逐帧渲染，各线程随机序列不一致，输出必出鬼影/闪烁。一律 `random(seed)`（字符串种子会被哈希，同种子恒同值）。
2. **禁用 CSS `transition` / `animation` / Tailwind 动画类**：逐帧截图捕捉不到时间推进，动画"不动"。全部重构为 `interpolate(frame, ...)` 内联 style。
3. **许可证**：Remotion 采用特殊许可证——个人、非营利组织、**≤3 人的营利公司**免费；超过 3 人的营利公司商用需购买 Company License（remotion.pro）。**交付前必须向用户确认使用主体性质**。
4. **国内网络**：npm 安装慢用镜像（`npm config set registry https://registry.npmmirror.com`）；首次渲染需下载 Chrome Headless Shell，失败时按官方文档配置镜像变量后重试；**不要**依赖 Google Fonts（见 §R.3 字体红线）。
5. **`useCurrentFrame()` 在 `<Sequence>` 内会自动偏移**：组件读到的是 Sequence 本地帧。跨层传帧号时显式传 `frame` prop，避免双重偏移。
6. **`defaultProps` 必须内联字面量**且 JSON 可序列化；Composition `id` 必须字符串字面量（运行时拼接的 id 不可渲染）。
7. **视频画布是像素不是字符格**：纵横比修正 0.55 发生在**采样阶段**（源图 → 网格），composition 尺寸只管最终画布比例，两者别混。
