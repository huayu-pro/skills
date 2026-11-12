# 23 · 动效案例库（30 案）

从 302 个逆向站点里按 14 族各选 2–3 案：优先 shader source + 8 向手势双证据，
保留 10 个强惯性案。每案只保留**机制、实测读数、可迁移、不要照搬、证据缺口**；
截图与完整证据在 `reverse-302/cases/<id>/`，不随本包分发。

> 读数来自 `facts.json` / `probe-excerpt.json` / 运行时采样。
> `drag 8/8` 表示 8 个方向都观察到手势；`inertia 0/8` 表示释放后无惯性。

## F1 滚动叙事 / 分段揭示

### `155-127-deiterhaus`

**机制**：长滚动 + 24s Ken Burns 背景：视觉运动主要来自背景缓慢缩放，而不是大量 CSS 入场。

| 动画 | 唯一名 | 时长 (ms) | shader/uniform/texture/draw | 手势 | 惯性 | docH | libs |
|---:|---|---:|---|---:|---:|---:|---|
| 4 | `kenBurnsCycle` | 24000.0 | 0/0/0/0 | 8/8 | 1/8 | 12559 | gsap, Lenis, ScrollTrigger |

**可迁移**：24s 的 Ken Burns 适合做低干扰背景；把滚动距离先定成 14 屏，再反推每段内容。

**不要照搬**：4 条动画不代表页面只有 4 个动效；大部分变化发生在滚动位置而非 WAAPI。；8/8 gesture 只说明通道有变化，不说明惯性/吸附。

**证据缺口**：证据：observed：4 条动画、8/8 拖拽通道；GSAP + Lenis + ScrollTrigger 在 libs 中。

### `156-173-wist`

**机制**：批量 `fade-in-up` 入场 + 一条 8.6s 进度动画：产品页用短入场把长页切成段。

| 动画 | 唯一名 | 时长 (ms) | shader/uniform/texture/draw | 手势 | 惯性 | docH | libs |
|---:|---|---:|---|---:|---:|---:|---|
| 48 | `fade-in-up` | 300.0, 400.0, 8619.0 | 0/0/0/0 | 1/8 | 0/8 | 12038 | — |

**可迁移**：300ms + `fade-in-up` 是产品页最稳的批量入场；8.6s 的长条只用于进度，不用于入场。

**不要照搬**：48 条计数包含大量重复目标，不能当 48 种动效。；rAF p95 1016ms 是 headless 软件渲染读数，不能写成性能结论。

**证据缺口**：证据：observed：48 条动画；1/8 拖拽，0/8 惯性。

### `156-198-kontu`

**机制**：550/650/900ms 三层入场：标题、模型、标签各用不同时长，形成“舞台搭起来”的顺序。

| 动画 | 唯一名 | 时长 (ms) | shader/uniform/texture/draw | 手势 | 惯性 | docH | libs |
|---:|---|---:|---|---:|---:|---:|---|
| 52 | `hero-block-in`, `hero-fade`, `hero-mockup-in`, `hero-rise` | 146.25, 204.75, 450.0, 550.0, 585.0, 650.0, … (7 values) | 0/0/0/0 | 1/8 | 1/8 | 7515 | — |

**可迁移**：同一屏内用 450/550/650/900ms 四档建立层级；先让大块落位，再让小标签补细节。

**不要照搬**：rAF median 83.4ms / p95 1016ms 是 headless 读数，不要当真实帧率。；52 条动画是重复的段落入场，不是 52 种机制。

**证据缺口**：证据：observed：52 条动画；1/8 拖拽，1/8 惯性。

## F10 相机 / 缩放 / 多 canvas

### `300-015-the-content-architecture`

**机制**：Minimap 相机 + 25 个 canvas：把产品界面拆成可扫描的小地图，8/8 拖拽推进。

| 动画 | 唯一名 | 时长 (ms) | shader/uniform/texture/draw | 手势 | 惯性 | docH | libs |
|---:|---|---:|---|---:|---:|---:|---|
| 16 | `statusPing`, `marqyL`, `heroScrollCue`, `pulse` | 900.0, 1440.0, 1800.0, 2000.0, 5000.0, 14760.9375 | 14/200/6/6 | 8/8 | 0/8 | 21276 | — |

**可迁移**：`minimapScan` 900ms + `minimapScanCounter` 1800ms，是“扫描头 + 计数”的成对节奏。；25 个 canvas 可以拆成多个小场景，不要合成一个巨型 canvas。

**不要照搬**：25 canvas ≠ 25 层同一场景；不要写“25 层 3D”。；8/8 drag 但 0 inertia；不要写惯性。

**证据缺口**：证据：observed：16 条动画、14 段 shader、25 个 canvas、8/8 拖拽。

### `155-028-tara`

**机制**：四个 Three.js 场景 + 18,080px 长滚动：CSS 只有 1 条 14s footer flow，主体在 canvas。

| 动画 | 唯一名 | 时长 (ms) | shader/uniform/texture/draw | 手势 | 惯性 | docH | libs |
|---:|---|---:|---|---:|---:|---:|---|
| 1 | `footer-flow` | 14000.0 | 0/0/0/0 | 7/8 | 4/8 | 18080 | gsap, ScrollTrigger |

**可迁移**：4 个 Three 场景 + 18k 滚动，适合“每个 section 一个 3D 舞台”。；14s footer flow 是长循环，不是入场。

**不要照搬**：archetype 与 shader 证据冲突；不要用 probe shader=0 判“没有 WebGL”。；4/8 inertia 只说明部分方向有惯性，不要写全向物理。

**证据缺口**：证据：observed：1 条动画、4 个 three.js canvas、7/8 拖拽、4/8 惯性；probe shader=0（冲突）。

## F11 传送带 / marquee / ticker

### `156-192-safestep`

**机制**：花粉/斑点/跑马灯的环境层 + 600ms 状态脉冲：8/8 拖拽但 0/8 惯性。

| 动画 | 唯一名 | 时长 (ms) | shader/uniform/texture/draw | 手势 | 惯性 | docH | libs |
|---:|---|---:|---|---:|---:|---:|---|
| 26 | `safestep-pollen-drift`, `marquee-slide`, `safestep-blob-drift-a`, `safestep-blob-drift-b` | 600.0, 2400.0, 11000.0, 12000.0, 13000.0, 16000.0, … (16 values) | 0/0/0/0 | 8/8 | 0/8 | 8610 | — |

**可迁移**：11–24s 的 blob 漂移 + 32s marquee，适合做“环境在呼吸”的产品页。；600ms 状态脉冲与 2.4s 入场分开，互不抢。

**不要照搬**：8/8 drag 但 0 inertia；不要写拖拽惯性。；长时间环境动画要考虑 reduced-motion 与暂停。

**证据缺口**：证据：observed：26 条动画、8/8 拖拽、0/8 惯性。

### `155-074-product-design-playbook-deck`

**机制**：Logo 跑马灯 + 证明条滑移 + AI 聊天微动效：47 条动画覆盖 200ms 到 60s。

| 动画 | 唯一名 | 时长 (ms) | shader/uniform/texture/draw | 手势 | 惯性 | docH | libs |
|---:|---|---:|---|---:|---:|---:|---|
| 47 | `logostrip-marquee-quad`, `proof-glide`, `sx-fade`, `rev-glide` | 200.0, 250.0, 300.0, 350.0, 450.0, 1100.0, … (12 values) | 0/0/0/0 | 6/8 | 0/8 | 13357 | — |

**可迁移**：24/36/52/60s 四档 marquee 适合不同长度的 logo 墙；200–450ms 给聊天/证明条微交互。；把 AI 聊天的 shimmer/caret 单独命名，避免和页面入场混在一起。

**不要照搬**：47 条包含重复目标；不要当 47 种动效。；6/8 drag 但 0 inertia；不要写惯性。

**证据缺口**：证据：observed：47 条动画、6/8 拖拽、0/8 惯性。

## F12 扫描 / VHS / 热感

### `156-191-smith-robinson`

**机制**：VHS/扫描线/颗粒的三层速度：200ms 扫描线、1000ms 噪声、8000ms 颗粒，0/8 拖拽。

| 动画 | 唯一名 | 时长 (ms) | shader/uniform/texture/draw | 手势 | 惯性 | docH | libs |
|---:|---|---:|---|---:|---:|---:|---|
| 16 | `animateGrain`, `arrow-blink`, `vhs-rotate-left`, `vhs-rotate-right` | 200.0, 1000.0, 1500.0, 2000.0, 3000.0, 8000.0, … (7 values) | 0/0/0/0 | 0/8 | 0/8 | 16833 | gsap, ScrollTrigger |

**可迁移**：三层速度（200ms/1s/8s）是 VHS 质感的关键；不要所有噪点用同一速度。；`vhs-rotate-left/right` 做色差/抖动，比整屏 filter 更便宜。

**不要照搬**：0/8 drag；不要写交互结论。；40 个视频不等于 40 个 WebGL 纹理。

**证据缺口**：证据：observed：16 条动画、40 个视频；0/8 拖拽。

### `L0-rig`

**机制**：安全产品演示的队列/流水线状态机 + glitch：54 条动画覆盖 1.1s 到 18s，另有 166s 环境层。

| 动画 | 唯一名 | 时长 (ms) | shader/uniform/texture/draw | 手势 | 惯性 | docH | libs |
|---:|---|---:|---|---:|---:|---:|---|
| 54 | `watermark-glitch`, `ticker`, `queue-build`, `rework` | 1100.0, 1500.0, 3000.0, 4000.0, 4500.0, 5000.0, … (12 values) | 0/0/0/0 | 1/8 | 0/8 | 8585 | — |

**可迁移**：1.1/1.5/3/4/4.5/5/6s 的阶梯很适合“队列/检查/重做”的产品演示。；`thinking-dot` 这种小状态命名，让演示可读。

**不要照搬**：1/8 drag；不要写交互。；166s 是环境/装饰，不要当主叙事时长。

**证据缺口**：证据：observed：54 条动画；1/8 拖拽。

## F13 视频拼贴

### `155-067-flowjam-2`

**机制**：视频 + 方向点/飞机/落位的光标叙事：103 条动画里大量是同一组光标粒子。

| 动画 | 唯一名 | 时长 (ms) | shader/uniform/texture/draw | 手势 | 惯性 | docH | libs |
|---:|---|---:|---|---:|---:|---:|---|
| 103 | `fj-dot-down`, `fj-dot-up`, `fj-dot-left`, `fj-dot-right` | 500.0, 700.0, 3600.0, 4500.0, 8000.0, auto | 0/0/0/0 | 1/8 | 0/8 | 14954 | — |

**可迁移**：500ms 光标 + 700ms 落位，是“演示光标”的标准节奏。；用方向点/飞机/落位三种状态表达“操作—移动—到达”。

**不要照搬**：103 条计数膨胀；不要当 103 种动效。；1/8 drag；不要写交互结论。

**证据缺口**：证据：observed：103 条动画、16 个视频；1/8 拖拽。

### `156-159-shopify-editions-winter-2026`

**机制**：60 屏长滚动 + 12 视频 + 24 段 shader + 8/8 惯性：本 atlas 的综合信号最强案。

| 动画 | 唯一名 | 时长 (ms) | shader/uniform/texture/draw | 手势 | 惯性 | docH | libs |
|---:|---|---:|---|---:|---:|---:|---|
| 76 | `nav-item-in`, `fade-in`, `slide`, `load-lines` | 300.0, 400.0, 500.0, 520.0, 600.0, 1000.0, … (9 values) | 24/200/120/12 | 8/8 | 8/8 | 54042 | — |

**可迁移**：300–6000ms 的完整阶梯 + 60 屏预算，适合“年度发布/编辑特刊”。；8/8 惯性说明可以做大范围拖拽浏览，不只纵向滚动。

**不要照搬**：76 条动画包含重复；不要当 76 种机制。；60 屏不是内容自然长度，是显式买的滚动距离。

**证据缺口**：证据：observed：76 条动画、24 段 shader、12 个视频、8/8 拖拽/惯性。

## F14 状态机 / 产品演示

### `300-033-tori`

**机制**：产品演示状态机：44 个命名阶段，从 URL 输入、按钮按下到消息升起，全部是 300–9000ms 的短段。

| 动画 | 唯一名 | 时长 (ms) | shader/uniform/texture/draw | 手势 | 惯性 | docH | libs |
|---:|---|---:|---|---:|---:|---:|---|
| 44 | `tori-caret-blink`, `tori-msg-rise`, `tori-line-reveal`, `tori-setup-stage-active-first` | 300.0, 360.0, 460.0, 800.0, 1000.0, 1200.0, … (8 values) | 0/0/0/0 | 2/8 | 0/8 | 4283 | — |

**可迁移**：把产品演示拆成命名阶段（type/press/pulse/travel/rise/reveal），比一条大时间轴可维护。；300–460ms 给输入，800–1200ms 给状态，2400–9000ms 给镜头/停顿。

**不要照搬**：2/8 drag；不要写手势。；44 条阶段不等于 44 个独立动效，很多是同一阶段的子目标。

**证据缺口**：证据：observed：44 条动画、2/8 拖拽；状态机命名清晰。

### `300-008-michael-kolesidis`

**机制**：角色/笑脸 + 音频 + 2 个 canvas 的固定视口状态机：9 条动画，8/8 拖拽/惯性。

| 动画 | 唯一名 | 时长 (ms) | shader/uniform/texture/draw | 手势 | 惯性 | docH | libs |
|---:|---|---:|---|---:|---:|---:|---|
| 9 | `ticker`, `moveSmiley`, `levitate`, `animate` | 1000.0, 2000.0, 3000.0, 20000.0, 180000.0, 1200000.0 | 4/200/13/3 | 8/8 | 8/8 | 12404 | — |

**可迁移**：1/2/3/20s 给角色状态，180s 给 ticker；短状态与长环境分开。；8/8 惯性适合“拖拽角色/场景”的玩法。

**不要照搬**：1,200,000ms（20 分钟）是极端循环，不要当 20 分钟主叙事。；audio 元素存在，但没有 analyser 数据；不要写频谱驱动。

**证据缺口**：证据：observed：9 条动画、4 段 shader、8/8 拖拽/惯性；audio 未分析。

## F2 横向轨道 / 惯性

### `156-193-onlook-cam`

**机制**：光标/菜单/浮层的微交互状态机：178 条里 170 条是同一条暂停的 ripple，真正活跃的只有 8 类。

| 动画 | 唯一名 | 时长 (ms) | shader/uniform/texture/draw | 手势 | 惯性 | docH | libs |
|---:|---|---:|---|---:|---:|---:|---|
| 178 | `menubarFadeIn`, `shimmerUp`, `cursorClick`, `dockFadeIn` | 200.0, 400.0, 800.0, 900.0, 1000.0, 1500.0 | 0/0/0/0 | 8/8 | 4/8 | 3679 | — |

**可迁移**：200/400/800/900/1000ms 五档正好对应点击、hover、菜单、dock、文字；照这个阶梯做 UI demo。；把 170 条暂停 ripple 当成状态池，而不是 170 个动画。

**不要照搬**：178 条动画是计数膨胀的典型；不能写“178 种动效”。；easing 大多未被捕获，不要编造曲线。

**证据缺口**：证据：observed：8 类活跃动画、8/8 拖拽、4/8 惯性；170 条 paused ripple。

### `155-006-tegra`

**机制**：GSAP ScrollTrigger 的横向/钉住叙事：WAAPI 采样为 0，但源码里 `scrub:1`、`power4.out`、`start/end` 都清楚。

| 动画 | 唯一名 | 时长 (ms) | shader/uniform/texture/draw | 手势 | 惯性 | docH | libs |
|---:|---|---:|---|---:|---:|---:|---|
| 0 | — | — | 0/0/0/0 | 1/8 | 1/8 | 4979 | gsap, ScrollTrigger |

**可迁移**：`scrub:1` + `power4.out` 是“滚动即时间轴”的保守配置；`top 85%` 比 `top 100%` 更早开始。；先把 section 的 start/end 写成百分比，再调位移。

**不要照搬**：不要因为 §4 写 0 animations 就判“没有动效”；这是 GSAP timeline 不在 WAAPI 里的典型。；1/8 drag 不能当横向轨道证据。

**证据缺口**：证据：observed（源码）：GSAP 3.12.2 + ScrollTrigger 3.12.2；WAAPI 时间线未捕获。

## F3 WebGL 全屏 shader / lens

### `155-052-textmode-overlay`

**机制**：Textmode 字形波 + 18–31s 熔岩环境：全屏 shader 做底，DOM 字形做波，拖拽有 8/8 惯性。

| 动画 | 唯一名 | 时长 (ms) | shader/uniform/texture/draw | 手势 | 惯性 | docH | libs |
|---:|---|---:|---|---:|---:|---:|---|
| 40 | `hero-glyph-wave`, `workflow-lava-primary`, `workflow-lava-ambient-a`, `workflow-lava-ambient-b` | 2400.0, 18000.0, 19000.0, 23000.0, 27000.0, 31000.0 | 54/200/120/9 | 8/8 | 8/8 | 8460 | — |

**可迁移**：2400ms 字形波 + 18–31s 环境层，是“快波 + 慢底”的两层时间尺度。；`u_charsetDimensions [16,16]` 这种把字符集做成 uniform 的做法，适合 textmode 类效果。

**不要照搬**：uniform 只是某一帧的采样，不能据此写“鼠标实时驱动 fluid”。；easing 未被探针捕获；8/8 inertia 是 canvas 变化，不代表有物理弹簧。

**证据缺口**：证据：observed：54 段 shader、200 uniform（触顶）、8/8 拖拽/惯性。

### `155-001-scroll-narrative-angelo`

**机制**：Orb + lens 双层 shader：21 条 700ms 入场 + 1 条 16s mono turn，8/8 拖拽但没有 release 惯性。

| 动画 | 唯一名 | 时长 (ms) | shader/uniform/texture/draw | 手势 | 惯性 | docH | libs |
|---:|---|---:|---|---:|---:|---:|---|
| 22 | `askMonoTurn` | 700.0, 16000.0 | 22/200/120/4 | 8/8 | 0/8 | 900 | — |

**可迁移**：700ms 统一入场 + 16s 单条旋转，是“短互动 + 长氛围”的组合。；lens 的 `uHold/uStrength/uChroma` 命名可以直接借用为参数契约。

**不要照搬**：orb 的运行时 uniform 值没有被采样；不能编造 `uScroll` 的曲线。；8/8 拖拽但 0/8 惯性；它是即时映射，不是弹簧。

**证据缺口**：证据：observed：22 段 shader、8 个 canvas、8/8 拖拽；orb 运行时值 unknown。

## F4 WebGL 3D 物体 / 场景

### `155-007-pete-sena`

**机制**：Three.js 材质场景 + Lenis 平滑滚动 + GSAP scrub：视觉主体是 22 个视频和 3 个 canvas，不是自定义 shader。

| 动画 | 唯一名 | 时长 (ms) | shader/uniform/texture/draw | 手势 | 惯性 | docH | libs |
|---:|---|---:|---|---:|---:|---:|---|
| 3 | `ps-nudge-wheel`, `ps-marquee` | 1600.0, 48000.0 | 2/19/7/1 | 8/8 | 8/8 | 21195 | THREE, gsap, Lenis, ScrollTrigger |

**可迁移**：Lenis `lerp:0.1` + GSAP `scrub:0.6` 是“滚动追动画”的稳配置。；48s marquee 适合作为视频墙的底层节奏。

**不要照搬**：“2 段 shader”其实是 Three.js 内置 `MeshStandardMaterial`，不是定制 shader。；22 个视频不一定是 WebGL 纹理；不要写成“视频纹理驱动 3D”。

**证据缺口**：证据：observed：3 条动画、19 uniform、8/8 拖拽/惯性；Lenis/GSAP 源码可读。

### `155-081-ousmane-dembele`

**机制**：40,610px 长滚动 + 16 段 shader 的 3D 场景：WAAPI 为 0，但 8/8 拖拽/惯性证明交互层很重。

| 动画 | 唯一名 | 时长 (ms) | shader/uniform/texture/draw | 手势 | 惯性 | docH | libs |
|---:|---|---:|---|---:|---:|---:|---|
| 0 | — | — | 16/200/42/8 | 8/8 | 8/8 | 40610 | gsap, ScrollTrigger |

**可迁移**：45 屏的滚动预算 + 8/8 惯性，适合“体育/品牌大片”式长叙事。；把 shader 数量当渲染层预算，不要当动效数量。

**不要照搬**：0 animations 是采样盲区，不是没有动效。；8/8 惯性是 canvas/容器变化，不等于物理参数已知。

**证据缺口**：证据：observed：16 段 shader、8/8 拖拽/惯性；GSAP 时间线未捕获。

## F5 Canvas2D 像素 / 角色世界

### `155-032-when-you-wish-upon-a-starboy`

**机制**：逐字揭示 + 像素 canvas：28 条动画其实只有 2 类，`charReveal` 1200ms 与 `renderFadeIn` 500ms。

| 动画 | 唯一名 | 时长 (ms) | shader/uniform/texture/draw | 手势 | 惯性 | docH | libs |
|---:|---|---:|---|---:|---:|---:|---|
| 28 | `renderFadeIn`, `charReveal` | 500.0, 1200.0 | 0/0/0/0 | 2/8 | 0/8 | 8383 | — |

**可迁移**：1200ms 的强 ease-out 逐字入场 + 500ms/300ms delay 的场景淡入，适合像素/角色页。；把 canvas 的 bitmap 分辨率压到 300×150，再用 CSS 放大，是低成本的像素质感。

**不要照搬**：28 条 = 24+4，不是 28 种动效。；canvas 内部 draw 未被 probe 捕获；像素角色怎么动仍是 unknown。

**证据缺口**：证据：observed：28 条动画、CSS easing 可读；2/8 拖拽、0/8 惯性。

### `155-129-rene-coignard`

**机制**：Matter.js 物理画布 + 800ms SVG：8/8 拖拽/惯性，但 probe 为空，物理参数不可见。

| 动画 | 唯一名 | 时长 (ms) | shader/uniform/texture/draw | 手势 | 惯性 | docH | libs |
|---:|---|---:|---|---:|---:|---:|---|
| 6 | `venenta-c1`, `venenta-c2`, `venenta-c3` | 800.0 | 0/0/0/0 | 8/8 | 8/8 | 900 | Matter |

**可迁移**：8/8 惯性 + Matter 的组合，适合做“可拖拽物理画布”的交互原型。；800ms 是 SVG 装饰层的统一时长，不抢物理层的注意力。

**不要照搬**：不要写 Matter 的质量/弹簧/阻尼参数；probe 为空，全部 unknown。；canvas 内部 draw 未被采样，不能写“物理对象实时碰撞”的细节。

**证据缺口**：证据：observed（gesture only）：8/8 拖拽/惯性；probe 为空。

## F6 排版 / 动态字体

### `156-175-typer`

**机制**：排版微动效的完整时长阶梯：260 条重复目标，约 11 类命名，从 120ms 的按键到 2000ms 的光晕。

| 动画 | 唯一名 | 时长 (ms) | shader/uniform/texture/draw | 手势 | 惯性 | docH | libs |
|---:|---|---:|---|---:|---:|---:|---|
| 260 | `hero-word-in`, `usp-enter`, `usp-glow`, `usp-draw` | 120.0, 200.0, 400.0, 600.0, 700.0, 750.0, … (9 values) | 0/0/0/0 | 1/8 | 0/8 | 4741 | — |

**可迁移**：按语义命名动画：keycap、token、usp、newsletter 各有自己的入场，不共用 `fade-up`。；120ms 给按键、200–400ms 给 hover/状态、600–1000ms 给段落、2000ms 给光晕。

**不要照搬**：260 条是重复目标计数；不要写“260 种动效”。；horizontal archetype 但 1/8 drag；不要当横向轨道案例。

**证据缺口**：证据：observed：260 条动画、约 11 类命名；1/8 拖拽。

### `155-141-heaven-in-color`

**机制**：大圆揭示 + 色彩时间轴：2000ms 的 `circle-reveal` 与日期颜色变化，滚动叙事为主。

| 动画 | 唯一名 | 时长 (ms) | shader/uniform/texture/draw | 手势 | 惯性 | docH | libs |
|---:|---|---:|---|---:|---:|---:|---|
| 61 | `circle-reveal`, `archiveDateFadeColor` | 2000.0 | 0/0/0/0 | 0/8 | 0/8 | 8799 | — |

**可迁移**：2000ms 的圆形揭示适合“换场景/换时间”而不是小控件。；日期颜色随滚动变化，是把数据绑定到色彩的轻量做法。

**不要照搬**：61 条计数包含重复目标；不要当 61 种动效。；0/8 drag；不要写手势结论。

**证据缺口**：证据：observed：61 条动画；0/8 拖拽。

## F7 光标 / 磁吸 / 角色

### `L0-alcove`

**机制**：固定视口 + Canvas2D 角色/光标 + 8/8 惯性：70 条动画集中在 2800ms 的环境层。

| 动画 | 唯一名 | 时长 (ms) | shader/uniform/texture/draw | 手势 | 惯性 | docH | libs |
|---:|---|---:|---|---:|---:|---:|---|
| 70 | — | 2800.0 | 0/0/0/0 | 8/8 | 8/8 | 900 | — |

**可迁移**：固定视口 + 8/8 惯性适合做“角色/光标即界面”的产品页。；2800ms 的环境循环比 300ms 微交互更适合角色呼吸。

**不要照搬**：没有唯一动画名，不能编造具体机制。；canvas 内部状态未知；只能写可见的光标/角色层。

**证据缺口**：证据：observed：70 条动画、8/8 拖拽/惯性；动画名缺失。

### `156-168-magnet-lover`

**机制**：磁吸商品页：600–1500ms 的漂浮/磁吸节奏，但拖拽证据只有 1/8 方向。

| 动画 | 唯一名 | 时长 (ms) | shader/uniform/texture/draw | 手势 | 惯性 | docH | libs |
|---:|---|---:|---|---:|---:|---:|---|
| 13 | — | 600.0, 1000.0, 1200.0, 1500.0 | 0/0/0/0 | 1/8 | 0/8 | 12165 | — |

**可迁移**：600/1000/1200/1500ms 四档适合商品卡的漂浮/吸附层。；把磁吸做成 hover/pointer 反馈，不要承诺拖拽物理。

**不要照搬**：1/8 drag + 0/8 inertia；不要写“已验证磁吸拖拽”。；动画名缺失，机制只能从时长与站点类型推断。

**证据缺口**：证据：observed（有限）：13 条动画；1/8 拖拽、0/8 惯性；机制 inferred。

## F8 音频 / 波形 / 可视化

### `155-013-voice-tag-gods`

**机制**：音频状态 + WebGL 玻璃字/粒子：27 条动画围绕 progress/live 状态，7.2s 是最大循环。

| 动画 | 唯一名 | 时长 (ms) | shader/uniform/texture/draw | 手势 | 惯性 | docH | libs |
|---:|---|---:|---|---:|---:|---:|---|
| 27 | `vtg-progress-linear-rotate`, `vtg-progress-rotate-arc`, `vtg-progress-expand-arc`, `hero-ai-float` | 1000.0, 1333.0, 1568.2352941176, 1800.0, 2700.0, 3000.0, … (11 values) | 22/200/37/11 | 1/8 | 1/8 | 6555 | gsap, ScrollTrigger |

**可迁移**：把音频状态拆成 progress/live/float 三组动画，而不是一条大时间轴。；1568ms 这种非整数值来自节拍/采样，适合音频可视化。

**不要照搬**：没有 audio analyser 数据；不要写“频谱驱动”。；1/8 drag；交互结论很弱。

**证据缺口**：证据：observed：27 条动画、1 个 audio、22 段 shader；1/8 拖拽。

### `155-062-midnight-2`

**机制**：沉浸式 WebGL 背景 + 文字入场：只有 3 条动画，但 64 段 shader 和 8/8 惯性才是主体。

| 动画 | 唯一名 | 时长 (ms) | shader/uniform/texture/draw | 手势 | 惯性 | docH | libs |
|---:|---|---:|---|---:|---:|---:|---|
| 3 | `hero-text-in`, `t-shimmer` | 500.0, 2000.0 | 64/200/120/32 | 8/8 | 8/8 | 7739 | — |

**可迁移**：500ms 文字 + 2000ms shimmer，把 DOM 动效压到最低，把预算给 WebGL。；8/8 惯性适合“拖动背景/相机”的沉浸式产品页。

**不要照搬**：3 条动画不代表简单；不要用动画计数判断 WebGL 站。；64 段 shader 的内部时间线未知。

**证据缺口**：证据：observed：3 条动画、64 段 shader、8/8 拖拽/惯性。

### `156-161-deeo-studio-2`

**机制**：视频 + 离屏 shader + 10.8s 长循环：Canvas 数显示 0，但 probe 抓到 6 段 shader。

| 动画 | 唯一名 | 时长 (ms) | shader/uniform/texture/draw | 手势 | 惯性 | docH | libs |
|---:|---|---:|---|---:|---:|---:|---|
| 17 | — | 600.0, 1000.0, 2000.0, 4000.0, 10800.0, 10950.0 | 6/200/21/3 | 8/8 | 0/8 | 12423 | — |

**可迁移**：10.8s/10.95s 的长循环适合视频/环境层，不抢 600ms 的 UI 入场。；不要用 DOM canvas 数量判断是否有 WebGL。

**不要照搬**：0 canvas + 6 shader 是数据冲突；不要写“无 WebGL”。；8/8 drag 但 0 inertia；不要写惯性。

**证据缺口**：证据：observed：17 条动画、6 段 shader、8/8 拖拽；canvas 计数冲突。

## F9 3D 倾斜 / 剥皮 / 材质

### `155-068-plastic`

**机制**：唱片/卷动/扫描的 3D 物体语法：6/12/14s 的长循环 + 8/8 拖拽，但惯性只有 1/8。

| 动画 | 唯一名 | 时长 (ms) | shader/uniform/texture/draw | 手势 | 惯性 | docH | libs |
|---:|---|---:|---|---:|---:|---:|---|
| 12 | `media-swap`, `vinyl-spin`, `roll-travel`, `roll-turn` | 6000.0, 12000.0, 14000.0, auto | 0/0/0/0 | 8/8 | 1/8 | 11469 | gsap |

**可迁移**：6/12/14s 三档长循环适合“实体物件”而不是 UI 控件。；`roll-turn`/`vinyl-spin` 的命名把物体运动语义化。

**不要照搬**：1/8 inertia；不要写“拖拽唱片有惯性”。；GSAP 时间线未被 WAAPI 捕获；时长来自 CSS/动画样本，可能不是完整时间轴。

**证据缺口**：证据：observed：12 条动画、8/8 拖拽、1/8 惯性；GSAP。

### `155-072-materials`

**机制**：视频纹理 + 箔材/颗粒材质：46 条动画覆盖 350ms 到 160s，21 个视频是主角。

| 动画 | 唯一名 | 时长 (ms) | shader/uniform/texture/draw | 手势 | 惯性 | docH | libs |
|---:|---|---:|---|---:|---:|---:|---|
| 46 | `rise-blur`, `foil-soft`, `foil`, `rise` | 350.0, 450.0, 800.0, 900.0, 1100.0, 2400.0, … (12 values) | 2/200/0/1 | 1/8 | 0/8 | 4426 | — |

**可迁移**：把 350–2400ms 给 UI，把 62–160s 给材质漂移，是两个完全不同的时间尺度。；`foil`/`grain-fizz` 这类材质命名可以直接作为视觉层参数。

**不要照搬**：2 段 shader / 1 draw 很薄；不要当 WebGL 重度案例。；1/8 drag；交互结论弱。

**证据缺口**：证据：observed：46 条动画、21 个视频、2 段 shader；1/8 拖拽。

## 提示词索引

| 主族 | 源案 | 提示词 |
|---|---|---|
| F1 | `155-001-scroll-narrative-angelo` | `assets/motion/prompts.md#F1-scroll-narrative-angelo.prompt` |
| F9 | `155-002-webgl-3d-mathias` | `assets/motion/prompts.md#F9-bend-panel-mathias.prompt` |
| F14 | `155-003-cursor-petrillo` | `assets/motion/prompts.md#F14-clock-dial-petrillo.prompt` |
| F11 | `155-004-typographic-jungle` | `assets/motion/prompts.md#F11-conveyor-typographic.prompt` |
| F13 | `155-005-collage-oluwatobi` | `assets/motion/prompts.md#F13-scrapbook-collage.prompt` |
| F1 | `156-168-magnet-lover` | `assets/motion/prompts.md#F1-magnet-lover-long-scroll.prompt` |
| F9 | `156-186-janna-deloume` | `assets/motion/prompts.md#F9-janna-deloume-peel-tilt.prompt` |
| F12 | `156-188-the-unholy-project` | `assets/motion/prompts.md#F12-unholy-halftone-light.prompt` |
| F4 | `156-160-tristan-haquenne-x-anthony-bayet` | `assets/motion/prompts.md#F4-tristan-rain-scene.prompt` |
| F14 | `156-163-app-flow` | `assets/motion/prompts.md#F14-app-flow-console.prompt` |

> 10 份提示词覆盖 5 个 pilot + 5 个 deepest 案例；其余 20 案只有机制卡，
> 没有对应提示词。不要为了凑数给每案编一份提示词。

## 用法

1. 先按 `09-motion-principles.md` 选 1 个主族。
2. 在本章找 2–3 个同族案例，取**区间与关系**，不要抄具体值。
3. 需要实现时跳到 `22-motion-implementation.md` 或对应 kit/component。
4. 需要生成整页时用提示词索引里的文件，先读它的禁止项与验收清单。
5. 验收按 `24-motion-verification.md`；证据缺口必须写进交付说明。
