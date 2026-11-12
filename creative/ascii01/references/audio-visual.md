# 音频驱动可视化：让字符网格随音乐呼吸

> 本文小节编号 M.1–M.6 为**文件本地编号**；跨文件引用本文时写 `audio-visual.md §M.x`。
> 场景：音乐站首页、播客页、演出海报页的字符化频谱/波形。网页实时路线零依赖（Web Audio 浏览器内置）；导出成视频走 Remotion（§M.5）。

## M.1 基础链路（30 行跑起来）

```js
// 零依赖：AudioContext + AnalyserNode 全浏览器内置（含国产内核的现代版）
let audioCtx, analyser, sourceNode;
const FFT_SIZE = 2048;                       // 频率分辨率与实时性的平衡点
const freqData = new Uint8Array(FFT_SIZE / 2);   // 频谱：每 bin 0–255
const timeData = new Uint8Array(FFT_SIZE);       // 波形：每采样点 128 为中轴

function setupAudio(mediaEl) {               // mediaEl = <audio> 或 <video> 元素
  audioCtx = new AudioContext();
  analyser = audioCtx.createAnalyser();
  analyser.fftSize = FFT_SIZE;
  analyser.smoothingTimeConstant = 0.8;      // 0.8：自带平滑，跳变不扎眼（0=生跳，1=迟钝）
  sourceNode = audioCtx.createMediaElementSource(mediaEl);  // 一个元素只能接一次
  sourceNode.connect(analyser);
  analyser.connect(audioCtx.destination);    // analyser 必须再接到输出，否则没声音
}

function pollAudio() {
  analyser.getByteFrequencyData(freqData);   // 频谱（能量分布）
  analyser.getByteTimeDomainData(timeData);  // 波形（时域振荡）
  return { freqData, timeData };
}
```

**铁律：`createMediaElementSource` 对同一元素只能调用一次**——重复调用会静音且不报错；SPA 里组件重挂载时复用旧 sourceNode，不要重建。

## M.2 三种字符网格映射（各取所需）

### 映射 A：频谱列（最常用）

低频在左、高频在右，每列高度映射 ramp 字符——"均衡器"。

```js
const RAMP = ' .:-=+*#%@';                   // 视觉契约（SKILL.md §1.2）

function spectrumGrid(freqData, { cols = 32, rows = 12, logScale = true } = {}) {
  const grid = Array.from({length: rows}, () => ' '.repeat(cols));
  const nyquist = audioCtx.sampleRate / 2;   // FFT 覆盖 0–nyquist Hz
  for (let c = 0; c < cols; c++) {
    // 对数分频段：低频占更多列（符合听感），线性分会把低频挤成一列
    const fLo = 30 * Math.pow(nyquist / 30, c / cols);
    const fHi = 30 * Math.pow(nyquist / 30, (c + 1) / cols);
    let binLo = Math.floor(fLo / nyquist * freqData.length);
    let binHi = Math.max(binLo + 1, Math.floor(fHi / nyquist * freqData.length));
    let sum = 0;
    for (let b = binLo; b < binHi; b++) sum += freqData[b];
    const level = sum / (binHi - binLo) / 255;          // 0–1
    const h = Math.round(level * rows);
    for (let y = 0; y < h; y++) {                        // 自底向上生长
      const row = rows - 1 - y;
      grid[row] = grid[row].substring(0, c) + RAMP[Math.min(RAMP.length - 1, 2 + y)] + grid[row].substring(c + 1);
    }
  }
  return grid;
}
```

| 参数 | 默认 | 说明 |
|---|---|---|
| `cols` | 32 | 频段列数（8–32 推荐；再多列低频分不出段） |
| `rows` | 12 | 网格高度；柱高动态范围 |
| `logScale` | true | 对数分频（听感均匀）；false 线性（机器感） |

### 映射 B：波形行

时域采样值直接驱动一行字符的纵向振荡——"心电感"。

```js
function waveformLine(timeData, { cols = 80, amp = 3 } = {}) {
  const mid = 4;                              // 振荡中轴行号
  const grid = Array.from({length: mid + amp + 1}, () => ' '.repeat(cols));
  for (let c = 0; c < cols; c++) {
    const v = (timeData[Math.floor(c / cols * timeData.length)] - 128) / 128;  // -1–1
    const dy = Math.round(v * amp);           // 振幅压在 ±amp 行内
    const row = mid - dy;                     // 上正下负
    grid[row] = grid[row].substring(0, c) + (dy === 0 ? '-' : (v > 0 ? '^' : 'v')) + grid[row].substring(c + 1);
  }
  return grid;                                // 静音时是一根平直的 -----
}
```

### 映射 C：低频呼吸（叠加层）

不画独立图形，而是让**已有的字符画**（logo、标题、hero 图）随节拍明暗/缩放——侵入最小的方案。

```js
function bassPulse(freqData, { bins = 8 } = {}) {
  let sum = 0;
  for (let b = 0; b < bins; b++) sum += freqData[b];       // 前 8 bin ≈ 0–190Hz，鼓点区
  const intensity = sum / bins / 255;                       // 0–1
  return {
    brightness: 0.7 + intensity * 0.5,                      // 亮度 0.7–1.2（CSS filter: brightness）
    scale: 1 + intensity * 0.05,                            // 字号 ±5%：呼吸感，再多就晕
  };
}
// 用法：pre.style.filter = `brightness(${p.brightness})`;  pre.style.fontSize = `${base * p.scale}px`;
```

## M.3 两种音源

| 音源 | 接法 | 适用 |
|---|---|---|
| `<audio>` / `<video>` 元素 | `createMediaElementSource(el)` | 页面配乐可视化（素材本地化，见 SKILL.md §0.2 安全组） |
| 麦克风 | `getUserMedia({audio: true})` → `createMediaStreamSource(stream)` | 互动装置、KTV 效果；**必须用户主动授权**，且不要 connect 到 destination（否则啸叫） |

```js
// 麦克风版（注意：stream 源不接 destination）
const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
audioCtx = new AudioContext();
analyser = audioCtx.createAnalyser();
analyser.fftSize = FFT_SIZE;
audioCtx.createMediaStreamSource(stream).connect(analyser);   // 只进 analyser，不进扬声器
```

## M.4 Autoplay 红线（最常见的"没反应"原因）

浏览器策略：**页面加载后 `AudioContext` 处于 `suspended` 状态，必须用户手势后 `resume()`**——没有点击就调 `getByteFrequencyData` 只会得到全 0，画面死平。这不是 bug，是所有浏览器（含国产内核）的强制策略。

标准解法——把"开启声音"做成显式交互，而不是自动播放：

```html
<button id="enable">▶ 点击开启可视化</button>
<audio id="player" src="track.mp3" loop></audio>
```

```js
enable.addEventListener('click', async () => {
  if (!audioCtx) setupAudio(player);
  await audioCtx.resume();                   // 手势上下文里 resume，必成功
  await player.play();
  enable.remove();                           // 开启后按钮退场
  requestAnimationFrame(loop);               // 可视化循环此刻才启动
}, { once: true });
```

- 想要"无按钮"页面：监听**任意**首次交互（`pointerdown` / `keydown`，`{once: true}`）统一解锁。
- 静音兜底：用户始终不交互时，展示一条静态频谱快照（预生成字符画），别留一片死黑。
- 麦克风源同样受此策略约束（授权弹窗本身就是手势，可顺带 resume）。

## M.5 Remotion 对照：导出音画同步的视频

网页实时分析在渲染期不可复现（麦克风/实时流没有"第二次一模一样"），导出视频改用**渲染期预抽取**：`@remotion/media-utils` 的 `getAudioData(src)` 一次性解码整个音频文件，返回 `{channelWaveforms: Float32Array[], sampleRate, durationInSeconds}`（签名对照 Remotion v4.0.538 源码 `packages/media-utils/src/get-audio-data.ts`）。

```tsx
import {getAudioData} from '@remotion/media-utils';
import {AbsoluteFill, Audio, interpolate, useCurrentFrame, useVideoConfig, staticFile} from 'remotion';
import {useEffect, useState} from 'react';

// 帧号 → 该时刻的瞬时振幅：直接从预抽取波形采样，无需 FFT、无需实时
function amplitudeAt(audioData, seconds) {
  const wave = audioData.channelWaveforms[0];
  const i = Math.floor(seconds * audioData.sampleRate) % wave.length;
  return Math.abs(wave[i]);                                  // 0–1
}

export const AudioPulse: React.FC = () => {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();
  const [data, setData] = useState(null);
  useEffect(() => { getAudioData(staticFile('track.mp3')).then(setData); }, []);

  const amp = data ? amplitudeAt(data, frame / fps) : 0;
  const scale = interpolate(amp, [0, 1], [1, 1.08]);         // 呼吸幅度 8%

  return (
    <AbsoluteFill style={{backgroundColor: '#000', alignItems: 'center', justifyContent: 'center'}}>
      {data && (
        <Audio src={staticFile('track.mp3')} />              {/* 音轨与帧时间线自动同步 */}
      )}
      <pre style={{fontFamily: 'monospace', fontSize: 64, color: '#00FF41', lineHeight: 1,
                   transform: `scale(${scale})`}}>
        {'▁▂▃▄▅▆▇█'.slice(0, Math.round(amp * 8) + 1)}
      </pre>
    </AbsoluteFill>
  );
};
```

- 频谱柱（网页映射 A）的视频版：离线跑一次 FFT（渲染前 Node 脚本或网页里预计算）存成 JSON，按帧索引取值——把"实时分析"变成"查表"，确定性达标（remotion-video.md §R.10）。
- 瞬时振幅采的是原始波形不是频谱：要"鼓点呼吸"请先做低通/分频预计算，别在组件里逐帧 FFT。

## M.6 无障碍与性能红线

- **音频必须有可见替代**：屏幕阅读器用户得不到任何信息——频谱旁放 `.visually-hidden` 文本摘要（"正在播放：曲名，节奏快"），或直接复用播放器的可访问字幕轨。
- `prefers-reduced-motion`：可视化降为**静态快照 + 播放进度条**（动画停，音乐不停——减弱的是动效不是功能）。
- 光敏安全：频谱闪变幅度限制在相邻帧 ±30% 以内（`smoothingTimeConstant ≥ 0.8` 已能兜住）；不要逐帧随机配色。
- 性能：`pollAudio()` 每帧最多调一次；网格渲染遵守 SKILL.md §6（`textContent`/canvas，勿逐字符 DOM）。移动端 `fftSize` 可降到 1024。
- 帧循环里 `getByteFrequencyData` 的数组**复用不重建**（预分配，见上方写法），逐帧 `new Uint8Array` 是常见无谓开销。
