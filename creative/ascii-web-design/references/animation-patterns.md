# 动效模式库：8 种字符网格动效（打字机 → morph）

> 本文小节编号 P.0–P.10 为**文件本地编号**；跨文件引用本文时写 `animation-patterns.md §P.x`。
> 定位：给**已有一张字符网格**（静态字符画、图片转出的 ASCII、FIGlet 大字）加动效的手法库。网格怎么来见 image-to-ascii.md / web-implementation.md §3.5；要导出视频配合 remotion-video.md。

## P.0 统一契约（先读这段，8 种模式全部遵守）

所有动效都是**帧驱动纯函数**：

```js
// 输入：grid = 行字符串数组（如 [' .#.', ' .@.', ...']），frame = 当前帧号，params = 模式参数
// 输出：新的 grid（或带样式标记的网格）。同输入必同输出，不依赖上一帧、不依赖 Math.random()。
const nextGrid = pattern(grid, frame, params);
```

为什么强制纯函数：

- **三端同构**：网页端在 rAF 循环里喂 `performance.now()` 换算的帧号；终端端在帧循环模板（terminal-templates.md）里喂循环计数；Remotion 端喂 `useCurrentFrame()`——同一份模式代码三端通用。
- **可降级**：`prefers-reduced-motion` 命中时直接喂终态帧号 `frame = Infinity`（或模式自带的总时长），一行业务代码得到静态成品。
- **可导出**：纯函数 = 可复现 = Remotion 能逐帧渲染成视频（remotion-video.md §R.2）。

需要随机性的模式（溶解、故障闪烁）用**种子化伪随机**：网页端 `seedRandom('溶解-3-7', salt)`（下方实现），Remotion 端直接 `random()`（remotion 模块，同语义）。

```js
// 网页端种子化伪随机（与 Remotion random(seed) 同思路：同种子恒同值）
function seedRandom(seed, salt = 0) {
  let h = 2166136261 ^ salt;
  for (const ch of String(seed)) { h ^= ch.codePointAt(0); h = Math.imul(h, 16777619); }
  h = Math.imul(h ^ (h >>> 15), h | 1);                 // murmur3 终局
  return ((h ^ (h >>> 13)) >>> 0) / 4294967296;
}
```

**渲染载体提醒**（SKILL.md §6）：160×60 以内网格每帧全量重算 `textContent` 没问题；更大网格用 canvas `fillText` 并只重算脏区。

## P.1 打字机（typewriter）

最"终端感"的动效。按字符序展示，配光标。

```js
function typewriter(lines, frame, { cps = 20 } = {}) {
  // cps：每秒字符数。visible = 已显示字符总数（跨行累计，换行占 1 个名额）
  const visible = Math.floor(frame / 60 * cps);
  let used = 0;
  return lines.map(line => {
    const take = Math.max(0, Math.min(line.length, visible - used));
    used += line.length + 1;
    return line.slice(0, take);
  });
}
// 光标（网页端贴在最后一行末尾；闪烁必须 steps(1)，见 web-implementation.md §3.7）：
// <span class="cursor"></span>  .cursor::after { content: '▊'; animation: blink 1s steps(1) infinite; }
```

| 参数 | 默认 | 说明 |
|---|---|---|
| `cps` | 20 | 每秒字符数；正文感 15–25，机械感 40+，命令行回显 80+ |

- **等价实现**：终端端逐帧 `printf` 增量打印即可（不需重绘）；Remotion 端 `useCurrentFrame()` 喂同一函数。
- **变体**：`take` 改为每行独立计数 → 多行并行走字；对 FIGlet 大字按**列**切 → "扫描书写"效果。

## P.2 逐字符揭示（per-char reveal）

打字机的并行版：全字符已就位，逐个从透明/占位变实体。

```js
function reveal(lines, frame, { stagger = 1, fade = 6, placeholder = '·' } = {}) {
  // 返回 {ch, o} 网格：o 为 0–1 透明度，网页端转 <span style="opacity:o">
  return lines.map((line, y) => line.split('').map((ch, x) => {
    const start = (x + y * 4) * stagger;        // 行间额外错峰（×4）
    const o = Math.max(0, Math.min(1, (frame - start) / fade));
    return { ch: o === 0 ? placeholder : ch, o };
  }));
}
```

| 参数 | 默认 | 说明 |
|---|---|---|
| `stagger` | 1 | 相邻字符起步间隔（帧）；0 = 整体淡入 |
| `fade` | 6 | 单字符过渡时长（帧） |
| `placeholder` | `'·'` | 揭示前的占位符；用空格则像"逐渐聚焦"，用低密度字符则像"数据流入" |

- **等价实现**：终端端无透明度，`o` 降级为二值阈值（o ≥ 0.5 显示）近似；Remotion 端同函数，`o` 直接内联 `opacity` style（remotion-video.md §R.3 示例即此模式）。

## P.3 扫描线扫过（scan sweep）

一条亮带从上到下（或左到右）扫过网格，扫过处字符"提亮一档"。

```js
function scanSweep(lines, frame, { speed = 0.02, band = 3, duration = null } = {}) {
  // p：0→1 扫过进度；duration 给定则按总时长匀速，否则按 speed（每帧进度增量）
  const total = lines.length + band;
  const p = duration ? frame / duration : frame * speed;
  const center = p * total;
  return lines.map((line, y) => {
    const d = Math.abs(y - center);
    if (d <= band && p <= 1) {
      // 带内：字符向 ramp 高端平移一档（提亮）；需配合原始图像网格使用时按 (x,y) 查亮度索引
      return line.replace(/[^\s]/g, ch => bump(ch));
    }
    return line;
  });
}
function bump(ch) {                              // 提亮一档：沿视觉契约 RAMP 向密端走一格
  const RAMP = ' .:-=+*#%@';
  const i = RAMP.indexOf(ch);
  return i === -1 ? ch : RAMP[Math.max(0, i - 1)];
}
```

| 参数 | 默认 | 说明 |
|---|---|---|
| `speed` | 0.02 | 每帧进度增量（0.02 ≈ 50 帧扫完 40 行）；给了 `duration` 则忽略 |
| `band` | 3 | 亮带半宽（行）；大网格可到 6–8 |

- **变体**：横向扫（`x` 维度同构改写）；扫过处**反向**降一档 → "读取完毕归档"感；带内字符替换为 `▓` 高密度块。
- **等价实现**：终端端可用 ANSI 背景/前景色着色带内行（terminal-templates.md 控制字符协议）；Remotion 端把 `d <= band` 行套亮色 `color`。

## P.4 字符溶解（dissolve in / out）

整体以噪声阈值逐格显隐——入场像"信号接收"，离场像"信号丢失"。

```js
function dissolve(lines, frame, { duration = 60, out = false, salt = 0 } = {}) {
  const p = Math.max(0, Math.min(1, frame / duration));       // 进度 0→1
  return lines.map((line, y) => line.split('').map((ch, x) => {
    const r = seedRandom(`dis-${x}-${y}`, salt);               // 每格固定噪声值
    const show = out ? r > p : r < p;                          // out=true 离场（反向）
    return show ? ch : ' ';
  }).join(''));
}
```

| 参数 | 默认 | 说明 |
|---|---|---|
| `duration` | 60 | 总过渡帧数（60 帧 @30fps = 2 秒） |
| `out` | false | true 为离场溶解 |
| `salt` | 0 | 换盐值换一批噪声分布；Remotion 端注意 `salt` 要写死成常量 |

- **变体**：噪声值换成 `x + y` 的对角线阈值 → "斜向溶解"；按亮度排序溶解（暗部先出现）→ "显影"感。
- **等价实现**：Remotion 端把 `seedRandom` 换成 `random(\`dis-${x}-${y}\`)` 即可（remotion-video.md §R.10 种子分层）。

## P.5 故障闪烁（glitch flicker）

短周期、离散的行偏移与双色差——Cyberpunk 预设的标配（SKILL.md §0.1 风格表）。

```js
function glitch(lines, frame, { every = 24, bursts = 3, maxShift = 3, salt = 0 } = {}) {
  const cycle = Math.floor(frame / every);                     // 每 every 帧换一次故障布局
  const active = seedRandom(`on-${cycle}`, salt) < 0.35;        // 35% 的周期有故障
  if (!active) return lines;
  return lines.map((line, y) => {
    const r = seedRandom(`row-${cycle}-${y}`, salt);
    if (r > 0.2) return line;                                  // 80% 行保持
    const shift = Math.floor(seedRandom(`shift-${cycle}-${y}`, salt) * (maxShift * 2 + 1)) - maxShift;
    if (shift === 0) return line;
    // 行内环形位移：正右负左
    const s = ((shift % line.length) + line.length) % line.length;
    return line.slice(line.length - s) + line.slice(0, line.length - s);
  });
}
// 网页端双色差：故障行同时渲染两份，分别偏移 ±1px、着 #FF00FF / #00FFFF（品红/青），mix-blend-mode: screen
```

| 参数 | 默认 | 说明 |
|---|---|---|
| `every` | 24 | 故障布局保持帧数；越短越癫痫，**≤8 慎用** |
| `bursts` | 3 | （配色层用）连续故障周期数 |
| `maxShift` | 3 | 行最大偏移列数 |

- **红线**：故障必须**离散跳变**（周期内恒定），连续渐变的偏移会像"果冻抖动"；无障碍上全程可被 `prefers-reduced-motion` 关闭（SKILL.md §5）。
- **等价实现**：Remotion 端 `every`/周期种子完全同构（`Math.floor(frame/every)` 进种子）；终端端偏移用行首空格实现，双色差用 ANSI 前景色。

## P.6 波浪呼吸（wave breathing）

网格随时间做正弦起伏——"活着的数据"感，适合背景层与分离线。

```js
function wave(lines, frame, { amp = 1, wavelength = 16, speed = 0.08 } = {}) {
  // 每行按相位平移；amp=1 时字符只在 ±1 列内摇摆，网格不被撕裂
  return lines.map((line, y) => {
    const dx = Math.round(Math.sin(y / wavelength * Math.PI * 2 + frame * speed) * amp);
    if (dx === 0) return line;
    // 行长恒定：右移补左空格，左移补右空格（网格一致性，SKILL.md §4 第 7 条）
    if (dx > 0) return ' '.repeat(dx) + line.slice(0, line.length - dx);
    return line.slice(-dx).padEnd(line.length);
  });
}
```

| 参数 | 默认 | 说明 |
|---|---|---|
| `amp` | 1 | 摆幅（列）；>2 开始撕图，配 placeholder 模式使用 |
| `wavelength` | 16 | 一个完整波的行数 |
| `speed` | 0.08 | 相位推进速度（弧度/帧） |

- **变体**：纵向波（列内 `y` 平移，用换行实现较贵，改用字符上下替换近似）；双波叠加（两 sin 相加）更有机。
- **注意**：`amp > 1` 时行首/行尾会露空隙，成对出现 `padStart`/`slice` 保持行长恒定（网格一致性，SKILL.md §4 第 7 条）。

## P.7 级联翻转（cascade）

按行错峰的整体动效——行入场/离场的"骨牌"感，remotion-video.md §R.5 的逐行揭示就是它 + P.2。

```js
function cascade(lines, frame, { stagger = 2, hold = 0, dir = 'top' } = {}) {
  // 每行的"局部帧号"= 全局帧 − 行延迟；dir 决定哪一行先动
  const order = dir === 'top' ? (y => y) : (y => lines.length - 1 - y);
  return lines.map((line, y) => {
    const local = frame - order(y) * stagger - hold;
    if (local < 0) return ' '.repeat(line.length);             // 还没轮到：空白
    return line;                                                // 轮到后直接到位（硬切）
    // 想要渐变：接 P.2 —— const o = Math.min(1, local / fade) 逐字符透明度
  });
}
```

| 参数 | 默认 | 说明 |
|---|---|---|
| `stagger` | 2 | 相邻行动作间隔（帧） |
| `dir` | `'top'` | `'top'` 自上而下；`'bottom'` 反向；`'center'` 从中间向两端（`Math.abs(y - mid)`） |

- **美学对齐**：硬切版本最"机器"（粗野主义预设）；接 P.2 渐变版最"现代"。禁止对 stagger 做 ease-in-out（SKILL.md §4 第 4 条）。

## P.8 字形渐变（morph）

网格 A 渐变成网格 B——标题换词、图片"显影"成文字的招牌手法。

**文本 ⇄ 文本**（两张同尺寸网格，按格噪声切换，保序变体更顺滑）：

```js
function morphText(from, to, frame, { duration = 45, ordered = true, salt = 0 } = {}) {
  const p = Math.max(0, Math.min(1, frame / duration));
  return from.map((line, y) => line.split('').map((ch, x) => {
    if (ch === to[y][x]) return ch;                            // 相同字符不动（大幅减少闪烁）
    if (ordered) {
      // 保序：按列前缀阈值切——从左到右逐列"换血"，无随机闪烁
      return x / line.length < p ? to[y][x] : ch;
    }
    // 噪声版：每格独立、随进度概率切换（更"数字噪声"）
    return seedRandom(`m-${x}-${y}`, salt) < p ? to[y][x] : ch;
  }).join(''));
}
```

**图片 ⇄ 文字**（两张网格来自同一采样内核，字符索引做线性插值）：

```js
function morphImage(gridA, gridB, frame, { duration = 60 } = {}) {
  // gridA/gridB 的每个字符都映射到统一 RAMP 索引；索引插值 = 视觉墨量插值
  const RAMP = ' .:-=+*#%@';
  const p = Math.max(0, Math.min(1, frame / duration));
  return gridA.map((line, y) => line.split('').map((chA, x) => {
    const iA = RAMP.indexOf(chA), iB = RAMP.indexOf(gridB[y][x]);
    if (iA < 0 || iB < 0) return chA;
    return RAMP[Math.round(iA + (iB - iA) * p)];
  }).join(''));
}
```

| 参数 | 默认 | 说明 |
|---|---|---|
| `duration` | 45–60 | 过渡帧数；morph 比其他模式慢一档更优雅 |
| `ordered` | true | true=列前缀保序（顺滑），false=噪声切换（碎 glitch 感） |

- **前置条件**：两张网格**必须同尺寸同 COLS**（都按 SKILL.md §1.2 视觉契约采样），不同尺寸先统一重采样。
- **等价实现**：Remotion 端完全同构，`frame` 来自 `useCurrentFrame()`——morph 是视频端最出彩的转场（remotion-video.md §R.1 多场景时间线）。

## P.9 组合规则

模式可串可叠，但有秩序：

1. **先内容后位移**：morph / dissolve / reveal（决定"每个格是什么字符"）先算，wave / glitch（决定"格怎么摆"）后算。顺序反了会让字符身份每帧跳变。
2. **同类不叠**：wave 与 glitch 都是位移类，叠加等于随机平移；pick 一个。
3. **一次一个主旋律**：主视觉区同一时刻只跑一个"大动效"（morph 或 scanSweep），其余用低幅度辅助（P.6 波浪背景、光标闪烁）。全屏同时打字机 + glitch + 波浪 = 噪声墙。
4. **入场与常驻分开**：入场模式（typewriter/reveal/cascade/dissolve-in）跑完即停（`frame` 封顶），常驻模式（wave/glitch/呼吸）才无限循环——省掉终态判断错误导致的"死动画"。

## P.10 性能与无障碍红线

- 每帧全量重算适用 ≤160×60 网格（SKILL.md §6 经验值）；超过用 canvas `fillText` + 脏区（只重算 P.5 位移行 / P.3 亮带附近行）。
- `seedRandom` 的种子字符串每帧拼接有 GC 压力：高频模式预计算种子表（`seeds[y][x]` 初始化一次）。
- 所有模式在 `prefers-reduced-motion` 命中时喂终态帧（入场模式喂 `duration`、循环模式喂 0）→ 静态成品，这是硬性验收项（SKILL.md §7 第 6 条）。
- P.5 glitch 的 `every ≥ 16` 且提供关闭开关，防光敏不适。
