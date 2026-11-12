# 端到端实战：Matrix 字符雨首屏 + 导出 MP4（从需求到交付一步步走）

> 本文演示 skill 的完整工作流：需求澄清 → 路线决策 → 网页实现 → 验收 → 导出视频 → 排错。
> 用户口吻的原始需求：**"帮我做个黑客帝国那种字符雨当网站首屏，要有那味儿，最后我想发抖音，给我个视频文件。"**
> 跟着做一遍，就掌握了本 skill 的大半路线。

## 第 1 步：需求澄清（SKILL.md §0 快问档）

不要直接开写，先按四问回显确认（用户答"随便/你定"时用默认值）：

> **回显确认**：场景 = hero 全屏背景；风格 = Matrix 黑客（绿 `#00FF41`、半角片假名+数字）；底色 = 深底浅字；动效 = 循环播放；**交付 = 网页首屏 + MP4 视频**（新增：视频交付 → 触发 Remotion 路线，见第 8 步）。

冲突检查：无（Matrix 预设的动效气质"字符雨、流式输出"与用户要求一致）。

## 第 2 步：查表定路线（SKILL.md §1 速查表）

| 用户话语 | 命中路线 |
|---|---|
| "黑客帝国字符雨"（网页） | web-implementation.md §3.5 |
| "给我个视频文件"（MP4） | remotion-video.md |
| "要有那味儿"（CRT 质感） | web-implementation.md §3.7 |

结论：**网页端**用 §3.5 完整实现（零依赖）；**视频端**用 Remotion 独立实现（网页录屏不可取：帧率不精确、无音频轨）。

## 第 3 步：骨架 HTML（SKILL.md §3 排版三件套）

```html
<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>字符雨首屏</title>
  <style>
    body { margin: 0; background: #000; color: #00FF41; overflow-x: hidden; }
    .ascii {
      font-family: "JetBrains Mono", "IBM Plex Mono", "Courier New", monospace; /* 必须等宽 */
      font-variant-ligatures: none;   /* 防连字破坏网格 */
      white-space: pre;
      line-height: 1;
    }
    .hero { position: relative; height: 100vh; }           /* 全屏首屏容器 */
    #rain { position: absolute; inset: 0; width: 100%; height: 100%; }  /* canvas 铺满 hero，不撑高页面 */
    .hero-title {
      position: absolute; inset: 0; display: grid; place-content: center;
      z-index: 2; text-align: center;                      /* 标题压在雨幕上 */
    }
    /* CRT 三件套中最轻的两件（第 5 步），默认注释掉；启用时给 <body> 加 class="crt" */
    .crt::before {
      content: ''; position: fixed; inset: 0; pointer-events: none; z-index: 3;
      background: repeating-linear-gradient(0deg, rgba(0,0,0,.15) 0 1px, transparent 1px 3px);
      opacity: .5;
    }
    .crt::after {
      content: ''; position: fixed; inset: 0; pointer-events: none; z-index: 3;
      background: radial-gradient(ellipse at center, transparent 60%, rgba(0,0,0,.35) 100%);
    }
    .cursor::after { content: '▊'; animation: blink 1s steps(1) infinite; }
    @keyframes blink { 50% { opacity: 0 } }
  </style>
</head>
<body>
  <section class="hero">
    <canvas id="rain" aria-hidden="true"></canvas>          <!-- 装饰性：读屏隐藏 -->
    <div class="hero-title">
      <h1 class="ascii">WAKE UP...</h1>
      <p style="color:#888; font-size:14px">滚动进入矩阵 ↓</p>
    </div>
  </section>

  <script>
  // 第 4 步：字符雨本体（完整版见 web-implementation.md §3.5，此处为可直接运行的最小实现）
  const rain = document.getElementById('rain');
  const ctx = rain.getContext('2d');
  const CHARS = 'ｱｲｳｴｵｶｷｸｹｺ0123456789';   // 半角片假名 + 数字（Matrix 预设）
  const FONT = 16;                              // 字号 = 格高
  const reduced = matchMedia('(prefers-reduced-motion: reduce)').matches;
  let charW = 10, COLS = 1, drops = [];

  function resize() {
    rain.width = rain.clientWidth;              // 用布局尺寸，别用 innerWidth（hero 可能不满屏）
    rain.height = rain.clientHeight;
    ctx.font = `${FONT}px monospace`;
    charW = ctx.measureText('ｱ').width;         // 实测单字符宽（别硬编码）
    COLS = Math.max(1, Math.floor(rain.width / charW));
    // 列模型只在这里初始化一次：速度/尾长入场即定，帧循环里只推进 y
    drops = Array.from({ length: COLS }, () => ({
      y: Math.random() * -50,                   // 负值错开起始相位（先在屏外）
      speed: 0.5 + Math.random(),               // 0.5–1.5 行/帧
      tail: 8 + Math.random() * 16,             // 尾长 8–24
    }));
  }

  function draw() {
    ctx.fillStyle = 'rgba(0,0,0,0.08)';         // 半透明覆盖 → 旧字符逐帧变淡，形成拖尾
    ctx.fillRect(0, 0, rain.width, rain.height);
    for (let i = 0; i < COLS; i++) {
      const d = drops[i], x = i * charW;
      ctx.fillStyle = '#e8ffe8';                // 列头近白亮绿
      ctx.fillText(CHARS[Math.floor(Math.random() * CHARS.length)], x, d.y * FONT);
      ctx.fillStyle = '#0a0';                   // 尾内字符暗绿
      ctx.fillText(CHARS[Math.floor(Math.random() * CHARS.length)], x, (d.y - d.tail) * FONT);
      d.y += d.speed;
      if (d.y * FONT - d.tail * FONT > rain.height + FONT) {
        d.y = Math.random() * -20;
        d.speed = 0.5 + Math.random();
        d.tail = 8 + Math.random() * 16;
      }
    }
  }

  resize();
  addEventListener('resize', resize);
  if (reduced) {
    for (let k = 0; k < 60; k++) draw();        // reduced-motion：只画一帧静态雨幕（SKILL.md §5）
  } else {
    let visible = true;
    document.addEventListener('visibilitychange', () => {   // 后台标签页停转（SKILL.md §6）
      visible = !document.hidden;
      if (visible) requestAnimationFrame(loop);
    });
    (function loop() { if (visible) draw(); requestAnimationFrame(loop); })();
  }
  </script>
</body>
</html>
```

## 第 4 步：字符雨本体（web-implementation.md §3.5 完整代码，此处讲解要点）

整段代码直接从 web-implementation.md §3.5 复制，三个关键决策回顾：

1. **canvas 而不是 `<pre>`**：字符雨每帧字符都换（片假名随机换字），`<pre>` 全量重排成本高；canvas 天生适合"覆盖式"绘制。
2. **拖尾靠半透明黑整屏覆盖**（`rgba(0,0,0,0.08)`）：上一帧的字符逐帧变淡形成尾迹——这是网页端技巧，**视频端不能这么干**（见第 8 步）。
3. **列模型只初始化一次**：每列的速度/尾长在入场时定死，帧循环里只推进 `y`。若每帧重新随机，雨会"集体瞬移"。

## 第 5 步：CRT 质感（web-implementation.md §3.7，克制剂量）

```css
/* 只加三件套中最轻的两件：扫描线 + 暗角；flicker 不加（首屏要稳） */
.crt::before {
  content: ''; position: fixed; inset: 0; pointer-events: none; z-index: 3;
  background: repeating-linear-gradient(0deg, rgba(0,0,0,.15) 0 1px, transparent 1px 3px);
  opacity: .5;
}
.crt::after {
  content: ''; position: fixed; inset: 0; pointer-events: none; z-index: 3;
  background: radial-gradient(ellipse at center, transparent 60%, rgba(0,0,0,.35) 100%);
}
```

给 `<body class="crt">`。剂量红线：总强度换算 ≤2% 等效，超过就"劣质灯管"（SKILL.md §4 第 3 条）。

## 第 6 步：无障碍兜底（SKILL.md §5）

- canvas 已 `aria-hidden="true"`（第 3 步写好）。
- `prefers-reduced-motion`：§3.5 代码已内置——只画 60 帧快照成静态雨幕，不进循环。
- 后台标签页：`visibilitychange` 停帧（§3.5 已内置）。
- 光标闪烁标题可选：`.cursor::after { content:'▊'; animation: blink 1s steps(1) infinite; }`。

## 第 7 步：验收（SKILL.md §7 清单，本案例命中的条目）

- 【人工】等宽字体 + 禁连字 ✓（第 3 步三件套）
- 【人工】动画可暂停/降帧、离屏不空转 ✓（§3.5 visibilitychange）
- 【人工】reduced-motion 静态回退 ✓（第 6 步）
- 【人工】装饰性 ASCII 已 aria-hidden ✓
- 【人工】美学走查：单强调色（只有绿系）、动效无缓动回弹 ✓
- 【自动】断言脚本：`scripts/selfcheck.sh`（包内自检）；线上素材路径如走了网络加载，确认接入了 `loadWithRetry`（web-implementation.md §3.0）

浏览器实测：开 DevTools Performance 面板录 5 秒，确认帧率稳定 60fps、无长任务（列数在 120 内通常无压力）。

## 第 8 步：导出 MP4（remotion-video.md 路线）

网页录屏不可取（帧率/分辨率不可控），用 Remotion 独立实现：

```bash
mkdir matrix-video && cd matrix-video
npx create-video@latest --yes --blank --no-tailwind .
npm i
npx remotion studio      # 先开预览再写代码
```

把 remotion-video.md §R.4 的 `AsciiRain.tsx` 整个复制进 `src/`，在 `src/index.ts` 注册（`id="AsciiRain"`、`fps=30`、`durationInFrames=300`（10 秒）、1920×1080 竖屏改 1080×1920）。

**与网页版的核心差异**（这就是第 4 步埋的伏笔）：视频端每帧独立成图，不能靠"上帧残留"做拖尾——§R.4 用**纯函数回看**：列头位置由帧号直接算出，尾迹在同帧内画完；`Math.random()` 全部换成 `random(seed)`。

```bash
npx remotion render src/index.ts AsciiRain out/matrix.mp4     # 导出
npx remotion still src/index.ts AsciiRain out/cover.png --frame=60   # 顺手出封面帧
```

发布前确认 Remotion 许可证（个人/≤3 人公司免费，详见 remotion-video.md §R.10）。

## 第 9 步：排错演示（真会遇到的三个）

1. **雨幕全黑不动** → 控制台多半有 `Failed to fetch` 或 canvas 尺寸为 0：先查 `resize()` 是否在 DOM ready 后调用；素材类问题对照 web-implementation.md §3.0 表。FAQ Q1。
2. **视频里雨"忽浓忽淡"像鬼影** → 代码里混进了 `Math.random()`（多线程不一致），全局搜索替换成 `random(seed)`。FAQ Q14。
3. **渲染出的视频字符变宋体** → 渲染机器缺等宽字体，本地字体文件 `loadFont` 加载。FAQ Q16。

## 第 10 步：延伸（同框架换玩法）

- **换动效**：把入场换成"字符雨淡入 + 标题打字机"→ animation-patterns.md §P.1；标题从旧词 morph 到新词 → §P.8。
- **加音频**：配一首电子乐，让雨速随低频呼吸 → audio-visual.md §M.2 映射 C；导出音画同步版视频 → §M.5。
- **滚动叙事**：首屏雨幕滚走时溶解成产品图 → scroll-and-pointer.md §I.2 + animation-patterns.md §P.4。
- **批量交付**：多条素材要预生成/离线可用的雨幕底图 → web-implementation.md §3.9 构建期管线。
