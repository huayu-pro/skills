# Motion assets — 17 components · 12 kits · 10 prompts

一个入口：按族查代码/提示词/参数，不要按文件名猜。

```bash
python3 -I scripts/query_corpus.py --motion --family F3
python3 -I scripts/query_corpus.py --motion --kind components
```

| 资产 | 数量 | 位置 |
|---|---:|---|
| kits | 12 | `code/kits/` |
| components | 12 | `code/components/` |
| prompts | 10 | `prompts/` |
| keyframes | 24 | `code/css/keyframes.css` |
| snippets | 8 | `code/snippets/` |

## F1 滚动叙事 / 分段揭示

| 类型 | ID | 路径 | 说明 |
|---|---|---|---|
| kit | `01-scroll-narrative` | `assets/motion/code/kits/01-scroll-narrative.js` | 滚动叙事、分段 reveal、进度条 |
| kit | `12-editorial-landing` | `assets/motion/code/kits/12-editorial-landing.js` | 编辑落地页、sticky/nav/accordion |
| component | `10-scroll-narrative` | `assets/motion/code/components/10-scroll-narrative/index.html` | IO reveal 200px/450ms/16px + sticky pin 三段 + accordion + modal。 |
| prompt | `F1-magnet-lover-long-scroll.prompt` | `assets/motion/prompts.md#F1-magnet-lover-long-scroll.prompt` | 强提示词：复刻「Magnet Lover」的 网格纸背景 + 巨型字 + 磁贴拼贴 + 长滚动论证 |
| prompt | `F1-scroll-narrative-angelo.prompt` | `assets/motion/prompts.md#F1-scroll-narrative-angelo.prompt` | 强提示词：生成「玻璃球体轨道」型作品集 |
| keyframes | `kf-fade-up` | `assets/motion/code/css/keyframes.css` | canonical keyframes recipe |
| keyframes | `kf-fade-in` | `assets/motion/code/css/keyframes.css` | canonical keyframes recipe |
| keyframes | `kf-mask-reveal` | `assets/motion/code/css/keyframes.css` | canonical keyframes recipe |
| keyframes | `kf-wipe-circle` | `assets/motion/code/css/keyframes.css` | canonical keyframes recipe |
| keyframes | `kf-scale-in` | `assets/motion/code/css/keyframes.css` | canonical keyframes recipe |
| keyframes | `kf-drop-in` | `assets/motion/code/css/keyframes.css` | canonical keyframes recipe |
| snippet | `io-reveal` | `assets/motion/code/snippets.js#io-reveal` | IO reveal 200px/threshold 0/终态 |
| snippet | `sticky-pin` | `assets/motion/code/snippets.js#sticky-pin` | pin 进度 0..1，不劫持滚动 |

## F2 横向轨道 / 惯性

| 类型 | ID | 路径 | 说明 |
|---|---|---|---|
| kit | `02-horizontal` | `assets/motion/code/kits/02-horizontal.js` | 横向轨道、wheel/drag、边界 clamp |
| keyframes | `kf-slide-in-left` | `assets/motion/code/css/keyframes.css` | canonical keyframes recipe |
| keyframes | `kf-slide-in-right` | `assets/motion/code/css/keyframes.css` | canonical keyframes recipe |
| snippet | `lerp` | `assets/motion/code/snippets.js#lerp` | clamp / lerp / damp / wrap / rubber |
| snippet | `pointer-gestures` | `assets/motion/code/snippets.js#pointer-gestures` | 8 方向拖拽 + wheel 归一化 |

## F3 全屏 shader / lens

| 类型 | ID | 路径 | 说明 |
|---|---|---|---|
| kit | `03-webgl-shader` | `assets/motion/code/kits/03-webgl-shader.js` | 全屏 WebGL fragment shader |
| component | `01-orbit-gallery` | `assets/motion/code/components/01-orbit-gallery/index.html` | 六张卡片绕一个核心轨道；深度同时驱动 scale/blur/z-index/opacity。 |
| component | `05-shader-plane` | `assets/motion/code/components/05-shader-plane/index.html` | 覆盖三角形 + 单 fragment shader：时间/分辨率/指针/进度四个 uniform。 |
| snippet | `webgl-boilerplate` | `assets/motion/code/snippets.js#webgl-boilerplate` | WebGL2 全屏三角形/编译守卫 |

## F4 WebGL 3D 物体 / 场景

| 类型 | ID | 路径 | 说明 |
|---|---|---|---|
| prompt | `F4-tristan-rain-scene.prompt` | `assets/motion/prompts.md#F4-tristan-rain-scene.prompt` | 强提示词：复刻「Tristan Haquenne × Anthony Bayet」的 7 章状态机 + 全屏 Three.js 雨景/水滴 + 章节 overlay |

## F5 Canvas2D 像素 / 角色

| 类型 | ID | 路径 | 说明 |
|---|---|---|---|
| kit | `04-canvas-2d` | `assets/motion/code/kits/04-canvas-2d.js` | Canvas 2D 粒子/像素隧道 |
| snippet | `dpr-canvas` | `assets/motion/code/snippets.js#dpr-canvas` | DPR≤2 的 canvas 尺寸管理 |

## F6 排版 / 动态字体

| 类型 | ID | 路径 | 说明 |
|---|---|---|---|
| kit | `07-typography` | `assets/motion/code/kits/07-typography.js` | 动态字体、marquee、行 reveal |
| component | `12-editorial-motion` | `assets/motion/code/components/12-editorial-motion/index.html` | 110% 行 mask + 逐字波 1.4s/0.07s + dt marquee + ±3° 速度 skew。 |
| keyframes | `kf-line-mask` | `assets/motion/code/css/keyframes.css` | canonical keyframes recipe |
| keyframes | `kf-dash` | `assets/motion/code/css/keyframes.css` | canonical keyframes recipe |
| keyframes | `kf-caret` | `assets/motion/code/css/keyframes.css` | canonical keyframes recipe |

## F7 光标 / 磁吸 / 角色

| 类型 | ID | 路径 | 说明 |
|---|---|---|---|
| kit | `06-cursor` | `assets/motion/code/kits/06-cursor.js` | 自定义光标、磁吸、拖尾 |
| component | `09-cursor-field` | `assets/motion/code/components/09-cursor-field/index.html` | dot + ring 光标、磁吸按钮、多层视差、30° 倾斜卡片。 |

## F8 音频 / 波形

| 类型 | ID | 路径 | 说明 |
|---|---|---|---|
| kit | `09-audio` | `assets/motion/code/kits/09-audio.js` | WebAudio 解锁、频谱条 |
| component | `11-audio-visualizer` | `assets/motion/code/components/11-audio-visualizer/index.html` | 五个 oscillator 的 pad + analyser 64 bars；手势解锁、状态机、mute。 |

## F9 3D 倾斜 / 剥皮 / 材质

| 类型 | ID | 路径 | 说明 |
|---|---|---|---|
| kit | `05-orbit-3d` | `assets/motion/code/kits/05-orbit-3d.js` | CSS 3D 轨道/卡片 |
| component | `02-bend-carousel` | `assets/motion/code/components/02-bend-carousel/index.html` | 32 条竖切片伪造圆柱面；进入曲线 1.55，落位 760ms。 |
| prompt | `F9-bend-panel-mathias.prompt` | `assets/motion/prompts.md#F9-bend-panel-mathias.prompt` | 强提示词：生成「弯曲 3D 面板」型作品集 |
| prompt | `F9-janna-deloume-peel-tilt.prompt` | `assets/motion/prompts.md#F9-janna-deloume-peel-tilt.prompt` | 强提示词：复刻「Janna Deloume」的 插画 hero + 蓝色横幅 + 痛点卡片 + peel/tilt/sheen 卡片 |
| keyframes | `kf-float` | `assets/motion/code/css/keyframes.css` | canonical keyframes recipe |
| keyframes | `kf-orbit` | `assets/motion/code/css/keyframes.css` | canonical keyframes recipe |
| keyframes | `kf-shimmer` | `assets/motion/code/css/keyframes.css` | canonical keyframes recipe |
| snippet | `spring` | `assets/motion/code/snippets.js#spring` | 临界阻尼弹簧 + 落位进度 |

## F10 相机 / 缩放 / 多 canvas

| 类型 | ID | 路径 | 说明 |
|---|---|---|---|
| kit | `10-map` | `assets/motion/code/kits/10-map.js` | 地图 pan/zoom、pin |
| component | `06-tunnel-scene` | `assets/motion/code/components/06-tunnel-scene/index.html` | 26 层圆角矩形 + 46 粒子；滚动推进相位，拖拽横向旋转。 |

## F11 传送带 / marquee / ticker

| 类型 | ID | 路径 | 说明 |
|---|---|---|---|
| component | `04-belt-conveyor` | `assets/motion/code/components/04-belt-conveyor/index.html` | 速度驱动的无限带：BASE 62、MAX 900、exp(-dt×1.1) 摩擦。 |
| prompt | `F11-conveyor-typographic.prompt` | `assets/motion/prompts.md#F11-conveyor-typographic.prompt` | 强提示词：生成「工厂传送带」型排版作品集 |
| keyframes | `kf-marquee` | `assets/motion/code/css/keyframes.css` | canonical keyframes recipe |
| keyframes | `kf-ticker` | `assets/motion/code/css/keyframes.css` | canonical keyframes recipe |
| snippet | `friction` | `assets/motion/code/snippets.js#friction` | 速度 + 指数摩擦 + wheel 归一化 |

## F12 扫描 / VHS / 热感

| 类型 | ID | 路径 | 说明 |
|---|---|---|---|
| prompt | `F12-unholy-halftone-light.prompt` | `assets/motion/prompts.md#F12-unholy-halftone-light.prompt` | 强提示词：复刻「The Unholy Project」的 半调网点纸 + 灯开关明暗 + 团队档案 + waitlist |
| keyframes | `kf-scanline` | `assets/motion/code/css/keyframes.css` | canonical keyframes recipe |
| keyframes | `kf-grain` | `assets/motion/code/css/keyframes.css` | canonical keyframes recipe |
| keyframes | `kf-glitch-slice` | `assets/motion/code/css/keyframes.css` | canonical keyframes recipe |
| keyframes | `kf-flicker` | `assets/motion/code/css/keyframes.css` | canonical keyframes recipe |

## F13 视频拼贴

| 类型 | ID | 路径 | 说明 |
|---|---|---|---|
| kit | `08-collage` | `assets/motion/code/kits/08-collage.js` | 可拖拽拼贴卡片、吸附 |
| prompt | `F13-scrapbook-collage.prompt` | `assets/motion/prompts.md#F13-scrapbook-collage.prompt` | 强提示词：生成「手作剪贴簿」型个人主页 |

## F14 状态机 / 产品演示

| 类型 | ID | 路径 | 说明 |
|---|---|---|---|
| kit | `11-game` | `assets/motion/code/kits/11-game.js` | Canvas 小游戏循环、输入 |
| component | `03-clock-wipe` | `assets/motion/code/components/03-clock-wipe/index.html` | 可拖时钟 + 从点击点扩散的圆形换肤 + 滚轮抬升面板。 |
| component | `07-color-lab` | `assets/motion/code/components/07-color-lab/index.html` | 6 档明度 + hue shift + 饱和衰减；WCAG relative luminance 对比度。 |
| component | `08-rotary-controls` | `assets/motion/code/components/08-rotary-controls/index.html` | 三个 270° 旋钮 + 物理灯开关；中心 12px 退化，键盘 ±4。 |
| prompt | `F14-app-flow-console.prompt` | `assets/motion/prompts.md#F14-app-flow-console.prompt` | 强提示词：复刻「App & Flow」的 旋钮/调音台隐喻 + 服务卡片 + 大面积留白 + 主题切换 |
| prompt | `F14-clock-dial-petrillo.prompt` | `assets/motion/prompts.md#F14-clock-dial-petrillo.prompt` | 强提示词：生成「可拖拽日历仪表」型单页 |
| keyframes | `kf-spin` | `assets/motion/code/css/keyframes.css` | canonical keyframes recipe |
| keyframes | `kf-pulse-soft` | `assets/motion/code/css/keyframes.css` | canonical keyframes recipe |
| keyframes | `kf-ping` | `assets/motion/code/css/keyframes.css` | canonical keyframes recipe |
| keyframes | `kf-progress` | `assets/motion/code/css/keyframes.css` | canonical keyframes recipe |

## 选择规则

- 先按 `09-motion-principles.md` 选 **1 个主族**，再来这里找该族的 canonical 代码。
- 优先 `components/`（完整、已验证）→ `kits/`（最小机制）。
- 需要整页生成时用 `prompts/`；需要单个曲线/原语时用 `snippets/`。
- `keyframes/` 是 CSS 起手式，不绑定时长；时长从 `PARAMETERS.md` 取。
- 一个页面不要混超过 1 主族 + 2 辅族。
