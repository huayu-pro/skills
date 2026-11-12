# Motion prompts — 10

> 每节用 `## <id>` 包住；`query_corpus.py --motion --kind prompts` 仍按 id 检索。

<a id="F1-magnet-lover-long-scroll.prompt"></a>
## F1-magnet-lover-long-scroll.prompt

# 强提示词：复刻「Magnet Lover」的 网格纸背景 + 巨型字 + 磁贴拼贴 + 长滚动论证

## 一、硬约束

- 单页、零外部依赖：不引 CDN、不复用原站图片/字体/视频；所有视觉用 CSS/SVG/Canvas 自造。
- 桌面 1440×900 与 390×844 都可运行；390px `scrollWidth <= innerWidth`。
- 核心机制可用鼠标完成：滚轮、点击、至少 8 方向拖拽；无键盘也可用。
- 有 `prefers-reduced-motion` 降级。

## 二、机制
- 网格纸背景 + 巨型字 + 磁贴拼贴 + 长滚动论证。
- 状态机：`pointer parallax`：每张磁贴按 data-depth 偏移；nav 锚点滚动；表单校验。

## 三、视觉规范
- 参考：工程网格 + 207px Doner Black 大字 + 漂浮磁贴；没有 WebGL，纯 DOM/CSS 也能做出强物件感。
- 颜色/字体/间距按 `DEEPEST-REVERSE.md` 的 F12 计算样式；不要用通用渐变按钮。

## 四、禁止项

- 不要 bento grid + 渐变 CTA + 通用 3D blob。
- 不要把“原站 shader 段数”当成自定义 shader；先看 `u*`。
- 不要把推断写成 observed；未知写 unknown。

## 五、验收

- `node deepest/test_site.mjs <site>` errors=0、mobile diff=0。
- 8 方向拖拽/滚轮/点击至少各 1 个状态变化，且截图可复核。

<a id="F1-scroll-narrative-angelo.prompt"></a>
## F1-scroll-narrative-angelo.prompt

# 强提示词：生成「玻璃球体轨道」型作品集

> 用法：整段作为系统提示或首条用户消息。要求模型输出可直接双击运行的单文件或三文件，零依赖、离线可用。

---

你是一位做空间界面与产品设计的创意开发者。请为 `{{工作室名}}` 做一个作品集，核心不是网格，而是**七颗悬浮的玻璃球围着一颗核心球公转**。每个项目是一颗球，球面里封着该项目的一个真实切片（一个界面、一个符号、一张图），点击它，它从自己的位置圆形展开成 case study。

## 一、空间构图（必须逐项满足）

1. 纯白背景 `#FFFFFF`，黑字 `#0B0B0C`，没有深色模式。
2. 中央一颗核心球：直径 `clamp(190px,21vw,330px)`，紫蓝渐变（`#B9A8FF → #7B6CFF → #4A3BD8`），左上强高光、右下内阴影、外投影 `0 50px 90px -40px rgba(70,50,180,.45)`。
3. 六颗项目球围成一圈椭圆轨道：
   - 球径 `clamp(132px,15vw,230px)`；
   - 水平半径 `min(34vw,520px)`，垂直半径 `min(25vh,230px)`，垂直再乘 0.72；
   - 每颗球的角度 = `angle + i*2π/6`。
4. 球体必须是真的"球"，不是圆角卡片：`border-radius:50%`，三层以上 `radial-gradient`（左上 96% 白高光、右下 28% 反光、主体色），加 `inset -18px -22px 38px rgba(20,16,60,.22)`、`inset 12px 14px 30px rgba(255,255,255,.5)`、外阴影。
5. 球内内容必须"被封住"：用 CSS 渐变/字母/卡片/剪影，允许 `mix-blend-mode:multiply`，但不要贴一张圆角图片了事；内容边缘要被球体的高光和阴影压住。

## 二、轨道与深度（本案的灵魂）

- 每帧计算：
  - `x = cos(a)*rx`，`y = sin(a)*ry*0.72`
  - `depth = sin(a)`（-1 = 最远，+1 = 最近）
  - `scale = 0.72 + (depth+1)/2 * 0.34`
  - `blur = depth < 0 ? (1-depth)*1.1 : 0`
  - `z-index = 60 + round(depth*40)`
  - `opacity = 0.62 + (depth+1)/2 * 0.38`
- 深度变化必须**同时**改大小、模糊、亮度、叠放顺序；只改 `scale` 会像缩放，不像空间。
- 核心球的 `z-index:50`，让球体可以从它前面/后面穿过。

## 三、输入状态机（必须实现）

| 输入 | 行为 |
|---|---|
| 滚轮 | `targetAngle += delta * 0.0014`，rAF 平滑，禁止直接跳角度 |
| 按住拖拽 | 水平位移 `dx * 0.004` 累加角度；松手保留速度，`velocity *= 0.9` 衰减 |
| 自动漂移 | 每 2.6s `targetAngle += 0.02`，页面隐藏或拖拽时暂停 |
| 点击球体 | 从**该球中心**圆形展开 case study；展开前区分"点击"与"拖拽"（位移 > 6px 不算点击） |
| 键盘 ←/→ | 等价于滚轮，步进 0.35rad |
| 键盘 Esc | 关闭 case study |

- 展开参数：读取球体 `getBoundingClientRect()`，球心换算成 `--cx/--cy` 百分比；detail 层 `clip-path: circle(0 at var(--cx) var(--cy))` → `circle(150vmax at ...)`，720ms `cubic-bezier(.22,.8,.2,1)`。
- 关闭时反向收回，不能瞬间消失。

## 四、Case study 面板

- 背景色由项目决定（浅青、炭黑、暖紫、粉、深绿等），文字色随之反转；对比度必须 ≥ 4.5:1。
- 内容：`01 / 06` 序号、项目名（`clamp(44px,9vw,140px)`、900 字重、行高 .86、字距 -.055em）、一段 40–60 词描述、底部一行 `BRAND · PRODUCT · 2025`。
- 右上角 `CLOSE ×`，1px 边框、999px 圆角、10px 等宽字。
- 面板里不允许出现卡片、阴影、圆角容器。

## 五、Chrome 与 Ask

- 顶部：`© 2026 {{工作室}}.study` 在左，`WORK / ABOUT` 在右，10px 等宽字、字距 .12em。
- 底部：`07 PROJECTS · 2024—26` 在左，`IG / IN` 在右，`Let's talk` 黑色药丸按钮。
- 右下角必须有 `Ask` 入口：打开一个对话面板，第一句是 "You're checking out {{当前项目}}. Ask me anything about how it came together."，下面给 3 个示例问题；不要接后端，纯前端演示。
- 首次交互后，底部提示 `wheel / drag the orbit · click a sphere` 淡出。

## 六、视觉规范

- 字体：`Inter / Helvetica Neue`，不引网络字体。
- 颜色：白底黑字；球体允许青 `#4CC9F0`、紫 `#7A5CFF`、玫红 `#FF7AB8`、绿 `#35C98F`、灰蓝 `#7B8494`、沙 `#E2A25B`。
- 阴影只允许"大而软"：`0 34px 70px -34px`，不要 0 4px 8px 这种 UI 阴影。
- 动效时长只允许 200ms（hover）、720ms（展开）、900ms（轨道平滑）。
- 移动端：球径降到 `clamp(92px,26vw,140px)`，核心球 `clamp(150px,46vw,220px)`；隐藏顶部导航。

## 七、禁止项（出现任意一条即不合格）

- 禁止卡片网格、feature 三列、导航栏、hero 标题、渐变按钮。
- 禁止紫色 SaaS 渐变铺满全屏；紫色只属于核心球。
- 禁止 `Unlock`、`Seamless`、`Elevate`、`Revolutionize`、`Supercharge`。
- 禁止只改 scale 做深度；禁止用 `box-shadow` 模拟玻璃高光。
- 禁止点击后面板从屏幕中心展开；圆心必须是球心。
- 禁止复制原站图片、字体、视频；球面内容必须用 CSS/SVG 自造。
- 禁止自动播放声音、自动轮播视频。

## 八、验收清单

- [ ] 双击 `index.html` 可运行，零网络请求。
- [ ] 六颗球在椭圆轨道上，前后有大小/模糊/叠放差异。
- [ ] 滚轮与拖拽都能转轨道，松手有惯性；停止后能自然静止。
- [ ] 点击任意球，面板从该球位置圆形展开；`CLOSE`/`Esc` 能收回。
- [ ] 球体在核心球前/后穿过时，叠放顺序正确。
- [ ] 1440×900 与 390×844 都不溢出；控制台 0 error。
- [ ] 页面里没有任何外部 URL、字体、图片、音频。

## 九、输出格式

先给 6 行设计决策（为什么用轨道、为什么深度要改四件事、为什么展开圆心必须来自球体），再给完整代码。不要伪代码，不要省略号。

## 附：深挖参数（来自原站 WebGL shader）

- 卡片是矩形纹理 + **48×48 顶点网格**，不是球体。
- 顶点：`t=(y-zone)/(viewH-zone)`，`x = cx + (x-cx)*(1+flare*t²)`，`y += sag*(viewH-zone)*t²`。
- 默认 `zone .34 / flare .42 / sag .16 / blur 4`。
- 入场：`stickerDelay .1s / itemDur .8s / headlineDelay .92s / bodyDelay 1.14s / bodyStep .12s / blur 12px / glitchDelay 1.35s`。
- 圆角用 SDF；底部模糊用 `lod = t² * maxLod * smoothstep(0,8,-d)`。

<a id="F11-conveyor-typographic.prompt"></a>
## F11-conveyor-typographic.prompt

# 强提示词：生成「工厂传送带」型排版作品集

> 用法：整段作为系统提示或首条用户消息。要求模型输出可直接双击运行的单文件或三文件，零依赖、离线可用。

---

你是一位在瑞士做平面设计与艺术指导的创意开发者。你不做"作品集模板"，你做一台**印刷车间的传送带**：字标是车间招牌，作品是零件，过滤器是工位开关。请为 `{{工作室名}}` 实现一个单页。

## 一、首屏排版（必须逐项满足）

1. 视口固定：`html,body{height:100%;overflow:hidden}`；首屏没有滚动条。
2. 三行字标，全部大写字：
   - 第一行 `STUDIO`，字号 `clamp(18px,3vw,44px)`，字距 `.38em`，居中；
   - 第二行 `{{主理人名}}`，字号 `clamp(92px,18.5vw,300px)`，900 字重，行高 `.82`，字距 `-.055em`；
   - 第三行 `{{工作室名}}`，字号 `clamp(80px,16vw,260px)`，同样 900 字重、行高 `.82`。
3. 字标上下各压一条虚线轨道：高 16px，`border:1px solid currentColor`，`border-radius:999px`，内部用 `repeating-linear-gradient(90deg,currentColor 0 2px,transparent 2px 7px)` 做虚线；上轨道在字标上方 8%，下轨道在底部 4%。
4. 背景不是纯白：`#F5F3EE` 奶油纸色；所有墨色 `#2E2E36`。

## 二、传送带（本案的灵魂）

- 底部（或中部）一条横向轨道，放 11 张作品卡；卡片宽 `clamp(180px,20vw,286px)`，比例 3:4，**无圆角、无阴影、无边框**。
- 卡片颜色只允许 6 种：粉 `#FF78BC`、红 `#E2413E`、紫 `#6E61C9`、绿 `#2FB68F`、黄 `#F5C542`、蓝 `#4A7DFF`；每张卡只用一个底色 + 黑色 900 字重标题 + 9px 等宽分类小字。
- 滚轮和拖拽**不直接设位置**，而是给速度 `boost`：
  - `wheel`: `boost += deltaY * 0.55`
  - `pointermove`（按住拖动）: `boost += dx * 1.15`
  - 每帧：`offset += boost; boost *= 0.935`；`|boost| < 0.02` 归零。
- 卡片位置循环：`x = ((i*300 + offset) % (N*300) + N*300) % (N*300)`；超过半周回绕。
- 每帧根据 `|x|` 计算：`scale = max(0.42, 1 - |x|/(vw*1.05))`、`rotateY = x/vw * -26deg`、`opacity` 在 0.62vw 之外开始衰减、`z-index = 100 - round(|x|/10)`。
- 停止输入后必须还能惯性滑动 ≥ 1.5 秒，禁止松手即停。

## 三、控制件（必须裸）

- 左上：一个 34px 圆形 `+` 按钮，1px 边框，hover 旋转 90°。
- 旁边：`WORK` / `INFO` 两个 10px 等宽字按钮，选中项下方 3px 粉色横线。
- 中间：实时时钟 `HH:MM` + `· CLOSED`。
- 右侧：`MAIL` / `SOUND ON` / `NIGHT` 三个纯文字按钮，10px，`SOUND ON` 按下时变粉。
- 底部：11 个分类 chip，格式 `ALL 11` / `ART DIRECTION 02` / `BRANDING 01` / `WEB DESIGN 04`……数字用等宽字体、透明度 0.6；选中项用粉色下划线（`z-index:-1` 的 5px 色块），不要药丸背景。
- 所有控制件不加图标、不加底板、不加圆角容器。

## 四、过滤与详情

- 点击分类：不匹配的卡片必须"被移走"——`opacity:0; pointer-events:none`，并在 320ms 内完成；匹配的卡片从下方 40px 归位。禁止 `display:none`。
- 点击卡片：全屏详情层从底部 `clip-path: inset(100% 0 0 0)` 展开到 `inset(0)`，620ms `cubic-bezier(.3,0,.25,1)`；内容为 `FIG. 02`、项目名（900 字重、`clamp(54px,10vw,150px)`）、一句描述、三个色块。
- 详情层只能通过 `CLOSE ×` 或 `Escape` 关闭。

## 五、视觉与动效规范

- 字体：`Arial Black`/`Impact` 做展示字，`Helvetica Neue` 做正文，`SFMono-Regular`/`Menlo` 做控制件。不要引入任何网络字体。
- 只允许三档时长：180ms（hover）、320ms（过滤）、620–760ms（层展开）。
- 只允许两种缓动：`cubic-bezier(.3,0,.25,1)` 与 `ease-out`。
- 音效：Web Audio 正弦波，520→1040Hz，80ms 指数衰减，音量 ≤0.06；默认开启但必须可一键静音；禁止自动播放背景音乐。
- 移动端：字标降到 `clamp(70px,22vw,150px)`；隐藏右侧 MAIL/SOUND/NIGHT；分类 chip 可换行滚动。

## 六、禁止项（出现任意一条即不合格）

- 禁止 hero 大图、视频背景、玻璃卡片、圆角 16px 以上的容器。
- 禁止卡片阴影、渐变按钮、悬停放大 1.05、`transition: all`。
- 禁止 `Unlock`、`Elevate`、`Seamless`、`Revolutionize` 等 AI 文案。
- 禁止用 `display:none` 做过滤；禁止松手即停；禁止把字标做成静态装饰。
- 禁止复制原站图片、字体、视频；卡片视觉必须用 CSS 渐变/纯色自造。
- 禁止把控制件做成带图标的导航栏。

## 七、验收清单

- [ ] 双击 `index.html` 可运行，零网络请求。
- [ ] 滚轮后传送带能持续滑动 ≥1.5s 并自然停下。
- [ ] 拖拽后卡片有倾斜/缩放/前后层次，不是整体平移。
- [ ] 点击 `BRANDING` 后只剩匹配卡片，其余在 320ms 内消失且不可点。
- [ ] 点击卡片能打开详情层，`CLOSE` 与 `Escape` 都能关闭。
- [ ] 控制台 0 error；1440×900 与 390×844 都不溢出。
- [ ] 页面里没有任何外部 URL、字体、图片、音频。

## 八、输出格式

先给 6 行设计决策（为什么用速度而非位置、为什么控制件要裸、为什么卡片无阴影），再给完整代码。不要伪代码，不要省略号。

## 附：深挖参数（来自原站 app.js）

- `BASE = 62`（mobile 30）px/s、`MAX = 900`、`SPACING = .62`、`boost *= exp(-dt * 1.1)`。
- 滚轮 `boost += d * .9`；拖拽 `boost += |dx| * 3`。
- 过滤：`clawOut` 逐个 +0.09s 移走，`clawIn` +0.12s 放回。
- 音效是方波，40ms 指数包络：`blip(f1, f2, dur, type, vol)`。

<a id="F12-unholy-halftone-light.prompt"></a>
## F12-unholy-halftone-light.prompt

# 强提示词：复刻「The Unholy Project」的 半调网点纸 + 灯开关明暗 + 团队档案 + waitlist

## 一、硬约束

- 单页、零外部依赖：不引 CDN、不复用原站图片/字体/视频；所有视觉用 CSS/SVG/Canvas 自造。
- 桌面 1440×900 与 390×844 都可运行；390px `scrollWidth <= innerWidth`。
- 核心机制可用鼠标完成：滚轮、点击、至少 8 方向拖拽；无键盘也可用。
- 有 `prefers-reduced-motion` 降级。

## 二、机制
- 半调网点纸 + 灯开关明暗 + 团队档案 + waitlist。
- 状态机：`lights-on/off`：按钮 click 切 body class、aria-pressed；表单校验；锚点滚动。

## 三、视觉规范
- 参考：半调网点 + 窄纸栏 + 灯开关 + 恐怖档案；8 个 canvas、18 段 shader、`routeChange` 事件，气氛和状态机都很完整。
- 颜色/字体/间距按 `DEEPEST-REVERSE.md` 的 F12 计算样式；不要用通用渐变按钮。

## 四、禁止项

- 不要 bento grid + 渐变 CTA + 通用 3D blob。
- 不要把“原站 shader 段数”当成自定义 shader；先看 `u*`。
- 不要把推断写成 observed；未知写 unknown。

## 五、验收

- `node deepest/test_site.mjs <site>` errors=0、mobile diff=0。
- 8 方向拖拽/滚轮/点击至少各 1 个状态变化，且截图可复核。

<a id="F13-scrapbook-collage.prompt"></a>
## F13-scrapbook-collage.prompt

# 强提示词：生成「手作剪贴簿」型个人主页

> 用法：整段作为系统提示或首条用户消息。要求模型输出可直接双击运行的单文件或三文件，零依赖、离线可用。

---

你是一位做独立杂志与剪贴簿的平面设计师，不是 SaaS 落地页设计师。请为 `{{姓名}}` 做一个个人主页，媒介是一张**被翻旧、被手写、被贴过胶带的纸**。页面上每一处"不整齐"都必须有物理理由：旋转是因为纸贴歪了，阴影是因为纸叠起来了，手写是因为有人真的在旁边写了字。

## 一、纸与便签（必须逐项满足）

1. 页面背景 `#F4F1EA`，内容纸 `#FFFFFF`，纸宽 `min(820px, calc(100% - 40px))`，居中，1px 边框 `#E8E6E1`，阴影 `0 30px 70px -50px rgba(0,0,0,.45)`。
2. 顶部一条黄色便签跑马灯：背景 `#FFE86B`，整体 `rotate(-.6deg) scale(1.02)`，文字用手写体，内容重复两句自嘲（例如"i haven't updated this in a while" / "42 days since i last touched this"），中间用一个小笔尖图形分隔。
3. 跑马灯必须无缝循环：内容复制一份，`width:max-content`，`@keyframes { to { transform: translateX(-50%) } }`，周期 26s，线性。
4. 主纸内边距 `34px clamp(20px,5vw,56px) 60px`。

## 二、打印体 + 钢笔批注

- 正文用 `Inter/Helvetica Neue`，字号 `clamp(16px,1.9vw,19px)`，行高 1.7。
- 重点只用"马克笔高亮"：`background: linear-gradient(transparent 52%, rgba(35,70,214,.28) 52%)`，不要背景色块、不要加粗变色。
- 全页手写批注不超过 6 处；每处必须是 `#2346D6` 蓝色、手写体、轻微旋转（-3deg ~ +2deg），并带一个手写箭头或圈。
- 一处批注指向"被高亮的那句话"，制造"有人读过"的因果。

## 三、三只文件夹（项目卡）

- 三列网格，每列一只文件夹：黄 `#FFE86B`、粉 `#FFB3D1`、蓝 `#B7D0FF`。
- 文件夹不是卡片：`border-radius: 8px 8px 10px 10px`，顶部左侧有一个 tab 标签（`position:absolute; top:-10px`），整体轻微旋转（-0.7deg / +0.8deg / -0.3deg），`box-shadow: 0 10px 24px -18px rgba(0,0,0,.6)`。
- hover 时旋转归零、上移 4px，过渡 240ms。
- 文件夹里只放：tab 名、一句 16px 粗标题、一句 12px 描述、右下角年份。不要按钮、不要图标、不要进度条。

## 四、拍立得与胶带

- `scrapbook` 区放 4 张拍立得：白底、8px 边、底部 12px、1px 灰边、旋转 -4deg / +3deg / -2deg / +5deg。
- 每张顶部贴一条半透明黄色胶带（`::before`，54×18px，`rgba(255,240,160,.75)`），不要用阴影模拟胶带。
- 照片内容用 CSS 渐变占位，禁止引用外部图片。

## 五、可戳的小人 + 滚动积分

- 页脚放一个 54×74px 的 SVG 线条小人（圆头 + 5 条线），`stroke-width:2.4`，`stroke-linecap:round`；hover 抖动 ±9deg，点击触发一次 620ms 的"被戳"摆动。
- 点击同时在鼠标位置喷 26 个 7×11px 彩纸方块，颜色只允许 `#2346D6 / #FFE86B / #FFB3D1 / #B7D0FF / #2FBF71`，900–1800ms 内落下并淡出。
- 页脚实时显示 `your scroll points: N (okay)`：`scroll` 事件累计 `|Δy|/40`，四舍五入；不要持久化。

## 六、Boring mode（必须实现）

- 右上角一个开关，标签 `Boring mode`，下方一行手写小字 `← too much going on?`。
- 打开后：便签跑马灯、所有手写批注、箭头、胶带、旋转全部 `display:none`；文件夹去彩色去阴影去旋转、变成 1px 灰边；按钮圆角降到 4px；整体变成一份干净、灰、平的简历。
- 关闭后必须完全恢复，不允许刷新页面。
- 这个开关是"手作层的逃生门"，不是主题切换。

## 七、视觉规范

- 颜色只允许：墨 `#101114`、纸 `#FFFFFF`/`#F4F1EA`、钢笔蓝 `#2346D6`、便签黄 `#FFE86B`、粉 `#FFB3D1`、浅蓝 `#B7D0FF`、绿点 `#2FBF71`。
- 字体：正文 `Inter/Helvetica Neue`；手写 `Comic Sans MS / Bradley Hand / Segoe Print / cursive`；等宽 `SFMono-Regular/Menlo`。不要引网络字体。
- 圆角只允许 6–10px（文件夹/拍立得）与 999px（按钮/头像）；不要 16px 以上的大圆角。
- 动效时长只允许 180ms（hover）、240ms（文件夹归位）、620ms（小人摆动/彩纸）。

## 八、禁止项（出现任意一条即不合格）

- 禁止 SaaS 三列 feature grid、渐变按钮、玻璃卡片、紫色渐变、统一 12 栏网格。
- 禁止 emoji 当图标；禁止 iconfont；图标只能是 SVG 线条或 CSS 图形。
- 禁止 `Unlock`、`Elevate`、`Seamless`、`Revolutionize`、`Supercharge`。
- 禁止把每个区块都做成卡片；禁止每个标题都加英文小标签。
- 禁止复制原站照片、头像、字体；所有视觉用 CSS/SVG 自造。
- 禁止手写批注超过 6 处；禁止把整页都旋转。

## 九、验收清单

- [ ] 双击 `index.html` 可运行，零网络请求。
- [ ] 跑马灯无缝循环，无跳帧；窄屏不溢出。
- [ ] 三只文件夹有 tab、旋转、纸张阴影；hover 归零。
- [ ] Boring mode 一开一关，页面完全恢复且不刷新。
- [ ] 戳小人能触发摆动 + 彩纸，连续点击不卡死。
- [ ] scroll points 随滚动增长，停止后不再变化。
- [ ] 1440×900 与 390×844 都不横向溢出；控制台 0 error。
- [ ] 页面里没有任何外部 URL、字体、图片、音频。

## 十、输出格式

先给 6 行设计决策（为什么是纸、为什么手写只占 5%、为什么 Boring mode 是必要的），再给完整代码。不要伪代码，不要省略号。

## 附：深挖参数（来自原站 Next.js chunk）

- Boring 是 **feature flags**：关闭 `tape / buddy / night / doodles / aura / wall`，**保留** `polaroids / live`；`localStorage` key = `rd-boring`。
- poke 三组文案：`day / sleepy / late`，按小时选组；`rd-buddy-intro / rd-buddy-poked` 记录状态。
- London 时间：`Intl.DateTimeFormat('en-GB', { timeZone: 'Europe/London' })`，每 30s 刷新。

<a id="F14-app-flow-console.prompt"></a>
## F14-app-flow-console.prompt

# 强提示词：复刻「App & Flow」的 旋钮/调音台隐喻 + 服务卡片 + 大面积留白 + 主题切换

## 一、硬约束

- 单页、零外部依赖：不引 CDN、不复用原站图片/字体/视频；所有视觉用 CSS/SVG/Canvas 自造。
- 桌面 1440×900 与 390×844 都可运行；390px `scrollWidth <= innerWidth`。
- 核心机制可用鼠标完成：滚轮、点击、至少 8 方向拖拽；无键盘也可用。
- 有 `prefers-reduced-motion` 降级。

## 二、机制
- 旋钮/调音台隐喻 + 服务卡片 + 大面积留白 + 主题切换。
- 状态机：`knob value 0–100`：pointerdown 记起始角，pointermove 按角度差映射；wheel ±4；键盘 ±4；主题 `lights`。

## 三、视觉规范
- 参考：把服务选择做成一台硬件调音台：4 个旋钮、8 方向拖拽全部改变读数；这是本批唯一 8 方向拖拽全部被页面观察到的站。
- 颜色/字体/间距按 `DEEPEST-REVERSE.md` 的 F12 计算样式；不要用通用渐变按钮。

## 四、禁止项

- 不要 bento grid + 渐变 CTA + 通用 3D blob。
- 不要把“原站 shader 段数”当成自定义 shader；先看 `u*`。
- 不要把推断写成 observed；未知写 unknown。

## 五、验收

- `node deepest/test_site.mjs <site>` errors=0、mobile diff=0。
- 8 方向拖拽/滚轮/点击至少各 1 个状态变化，且截图可复核。

<a id="F14-clock-dial-petrillo.prompt"></a>
## F14-clock-dial-petrillo.prompt

# 强提示词：生成「可拖拽日历仪表」型单页

> 用法：把下面整段作为系统提示或首条用户消息，替换 `{{品牌名}}`、`{{三个项目}}`。要求模型输出**一个可直接双击运行的 index.html**（内联 CSS/JS），或 HTML/CSS/JS 三文件。

---

你是一位做过实体产品界面（仪器、控制台、印刷品）的交互设计师，不是 SaaS 落地页设计师。请为 `{{品牌名}}` 做一个单页作品集，核心是一台**可操作的日历仪表**，而不是一张带标题的 hero。

## 一、核心构图（必须逐项满足）

1. 视口就是全部舞台：`html,body{height:100%;overflow:hidden}`，首屏不出现纵向滚动条。
2. 画面四角各放一个巨大数字/月份：左上日期（如 `22`）、右上月份（如 `11`）、左下月份名（如 `NOV`）、右下年份后两位（如 `08`）。字号 `clamp(110px, 20vw, 288px)`，字重 900，行高 `.78`，字距 `-.06em`，贴边但保留 34–37px 内边距。
3. 正中放一个 SVG 模拟时钟：60 个刻度（每 5 个加粗）、时针/分针/秒针、中心圆点。时钟直径 `min(44vw, 400px)`。
4. 顶部中央只放一个 3–4 字母的模式词（`WORK` / `PLAY`），字距 `.28em`，12px。
5. 左右两侧各一条竖排小字（`W. / NOMINEE`、`IG / IN`），10px 等宽字体，贴边 18px。
6. 底部中央一个 `↓` 和一行 10px 提示，5 秒后自动淡出，不要常驻。

## 二、双皮肤与负片墨水（本案的灵魂）

- 两套皮肤叠放：皮肤 A 红底 `#FF0000`、皮肤 B 黑底 `#000000`。
- 所有文字/线条统一写 `color:#FF0000; mix-blend-mode:difference`，**不要**为黑底单独写一套颜色。红底会自动读成黑，黑底会保持红。
- 给每个皮肤容器 `isolation:isolate`；墨色层与背景层之间不得出现 `transform/opacity/z-index`，否则混合会被隔离。
- 皮肤 B 初始 `clip-path: circle(0px at var(--px) var(--py)); filter: blur(14px)`；切换时改为 `circle(165vmax at var(--px) var(--py))`、`blur(0)`，过渡 `680ms cubic-bezier(.3,.85,.15,1)`。
- 点击位置写入 `--px/--py`（百分比），擦除圆心必须是**用户实际点击的位置**，不能固定在中心。

## 三、交互状态机（必须实现）

| 输入 | 行为 |
|---|---|
| 鼠标左键点击画面空白处 | 从点击点圆形擦除，切换 A/B 皮肤；再次点击从新位置擦回 |
| 按住时钟指针拖动 | 指针跟随 `atan2` 角度旋转；四角日期/月份数字同步滚动；拖动中指针加粗 1px |
| 滚轮向下 | 仪表整体上移，下层黑色作品间从底部滑入；滚轮向上回到仪表 |
| 键盘 `f` | 等价于点击翻转（无障碍备用） |
| 键盘 `↑/↓` | 等价于滚轮推拉 |

- 拖动与点击必须区分：`pointerdown` 记录起点，`pointerup` 时位移 < 8px 且按住 < 420ms 才算点击。
- 拖拽必须 `setPointerCapture`，松手后保留当前角度，不回弹。
- 所有状态变化都要有可见的过渡，禁止瞬间跳变。

## 四、下层作品间

- 背景 `#000`，文字 `#F2F0EC`，红色 `#FF0000` 只做标题与强调。
- 标题 `SELECTED WORK` 用 900 字重、`clamp(42px, 8vw, 128px)`、行高 `.82`。
- 作品列表四行，每行：两位序号（等宽 10px 灰）、项目名（`clamp(18px,2.6vw,34px)` 粗体）、右侧分类小字。
- hover 时项目名变红并右移 8px，过渡 180ms / 260ms。
- 列表上下用 1px `#2A2A2A` 分隔，不要卡片、不要圆角、不要阴影。

## 五、视觉规范

- 字体：标题用系统里最重的 grotesque（`Arial Black`/`Impact`/`Helvetica Neue` 900），正文用 `Helvetica Neue`，等宽小字用 `SFMono-Regular/Menlo`。不要引入 Google Fonts。
- 点阵纹理：`radial-gradient(circle, currentColor 1.1px, transparent 1.3px)`，`background-size:26px 26px`，透明度 0.16–0.35。
- 缓动：`cubic-bezier(.3,.85,.15,1)` 用于擦除；`cubic-bezier(.32,.72,.16,1)` 用于位移；时长只允许 120/560/680ms 三档。
- 移动端：日期字号降到 `clamp(86px,30vw,150px)`，时钟 `min(70vw,320px)`，作品列表隐藏分类列。

## 六、禁止项（出现任意一条即不合格）

- 禁止紫色渐变、玻璃拟态卡片、圆角 24px 的 SaaS 面板、三列 feature grid、`Lorem ipsum`。
- 禁止用 emoji 当图标；禁止用 iconfont；图标只能是 SVG 线条。
- 禁止"AI 味"文案：`Unlock`、`Seamless`、`Elevate`、`Revolutionize`、`Supercharge`、`effortlessly`。
- 禁止淡入淡出代替几何擦除；禁止用 `transition: all`。
- 禁止把日期数字做成静态装饰——它必须随拖拽变化。
- 禁止自动播放声音；声音只能是用户操作后的短反馈。
- 禁止复制原站图片、字体、视频；所有视觉用 CSS/SVG 自造。

## 七、验收清单（交付前逐条自检）

- [ ] 双击 `index.html` 可直接运行，零网络请求、零依赖。
- [ ] 初始皮肤、点击后皮肤、拖拽后、滚轮后四种状态都能用鼠标完成。
- [ ] 点击擦除的圆心与点击坐标误差 < 2px。
- [ ] 时钟拖拽后，四角数字确实变化（不是只转指针）。
- [ ] 控制台 0 error；`prefers-reduced-motion` 下仍可用（至少保留状态切换）。
- [ ] 1440×900 与 390×844 两个视口都不溢出、不遮挡。
- [ ] 页面里没有任何外部 URL、字体、图片、音频。

## 八、输出格式

先输出 6 行设计决策（为什么是日历仪表、为什么用 difference、擦除的参数），再输出完整代码。代码必须是可运行的单文件或三文件，不要伪代码，不要省略号。

## 附：深挖参数（来自原站完整脚本）

- **hover** `.see-work` 触发翻转，指针进入点写 `--px/--py`；`circle(0 → 165vmax)`，680ms `cubic-bezier(.3,.85,.15,1)`，`blur(14px → 0)`。
- shuffle：4 套 `PRESETS`，指针 **880ms `quintInOut`**，旧圆 **340ms `quintOut`**，新圆再长出。
- 20s 空闲触发重力彩蛋；长按圆点每 450ms +0.5 pitch，最多 4×；抓针尖是 jog wheel，松手回弹。

<a id="F4-tristan-rain-scene.prompt"></a>
## F4-tristan-rain-scene.prompt

# 强提示词：复刻「Tristan Haquenne × Anthony Bayet」的 7 章状态机 + 全屏 Three.js 雨景/水滴 + 章节 overlay

## 一、硬约束

- 单页、零外部依赖：不引 CDN、不复用原站图片/字体/视频；所有视觉用 CSS/SVG/Canvas 自造。
- 桌面 1440×900 与 390×844 都可运行；390px `scrollWidth <= innerWidth`。
- 核心机制可用鼠标完成：滚轮、点击、至少 8 方向拖拽；无键盘也可用。
- 有 `prefers-reduced-motion` 降级。

## 二、机制
- 7 章状态机 + 全屏 Three.js 雨景/水滴 + 章节 overlay。
- 状态机：`progress → chapter`：wheel 0.35/格、click +1、drag 改水滴位置与 mix；`MORE` 面板可直接跳章。

## 三、视觉规范
- 参考：固定视口里的 7 章雨景，唯一主角是一颗黑色水滴；参数 uProgress/uAmplitude/uFrequency/uMix 把章节、雨、涟漪、折射绑在一起。
- 颜色/字体/间距按 `DEEPEST-REVERSE.md` 的 F12 计算样式；不要用通用渐变按钮。

## 四、禁止项

- 不要 bento grid + 渐变 CTA + 通用 3D blob。
- 不要把“原站 shader 段数”当成自定义 shader；先看 `u*`。
- 不要把推断写成 observed；未知写 unknown。

## 五、验收

- `node deepest/test_site.mjs <site>` errors=0、mobile diff=0。
- 8 方向拖拽/滚轮/点击至少各 1 个状态变化，且截图可复核。

<a id="F9-bend-panel-mathias.prompt"></a>
## F9-bend-panel-mathias.prompt

# 强提示词：生成「弯曲 3D 面板」型作品集

> 用法：整段作为系统提示或首条用户消息。要求模型输出可直接双击运行的单文件或三文件，零依赖、离线可用。

---

你是一位做创意开发（WebGL / 交互 / 前端）的设计工程师。请为 `{{姓名}}` 做一个作品集：三块网页作品被弯成圆柱面，悬在黑色空间里，像影院里三块弧面银幕；滚轮或拖拽让它们水平滑过，进入中心的那块由弯变正、由暗变亮。

## 一、舞台（必须逐项满足）

1. 背景 `#080808`，文字 `#F7F7F7`，没有其他大面积颜色。
2. 全屏固定：`html,body{height:100%;overflow:hidden}`；`perspective:1900px`，`perspective-origin:50% 46%`。
3. 三块面板横排，面板宽 `min(74vw,1080px)`，比例 16:9.4，间距 `3vw`，整体垂直居中。
4. 面板必须真的弯：每块切成 **26 条竖片**，每条：
   - `t = (i/(N-1))*2 - 1`（-1..1）
   - `rotateY(t * -17deg)`
   - `translateZ(-|t|² * 52px)`
   - `background-position: -x 0`，`background-size: 面板宽 100%`
   - 相邻切片重叠 0.7px，避免缝。
5. 面板内容只能是 CSS 渐变 + 大字 + 一行按钮；禁止使用真实图片。三块面板三个 art direction（雪景/黄昏/暖色），用 3–4 层 `radial-gradient` 叠出来。
6. 每块面板加一层颗粒 + 暗角：`radial-gradient(ellipse at 50% 45%, transparent 40%, rgba(0,0,0,.42))` + `repeating-radial-gradient` 细噪点，`mix-blend-mode:overlay`。

## 二、工位状态（本案的灵魂）

| 位置 | transform | filter | opacity |
|---|---|---|---|
| 中心 | `rotateY(0) scale(1)` | `brightness(1)` | 1 |
| 左右相邻 | 朝中心转 34deg，`translateX(±2vw)`，`scale(.86)` | `brightness(.52) saturate(.9)` | .9 |
| 更远 | 转 46deg，`translateX(±4vw)`，`scale(.7)` | `brightness(.32)` | .55 |

- 切换必须同时改旋转、缩放、亮度、透明度、叠放；只改一项不算"进入工位"。
- 过渡 760ms `cubic-bezier(.22,.8,.2,1)`。
- 中心面板的文案（kicker / 大标题 / 描述 / 按钮）必须清晰可读；两侧面板的文字要被压暗到几乎不可读，形成焦点。

## 三、输入状态机（必须实现）

| 输入 | 行为 |
|---|---|
| 滚轮 | 一次滚动切换一格，节流 620ms；`deltaY` 为主，`deltaX` 优先 |
| 按住拖拽 | 面板实时跟手（`dx*0.35`）；松手位移 < -40 切下一格，> 40 切上一格，否则回弹 |
| ← / → | 切换上一格/下一格 |
| 点击中心面板 | 从底部拉开 case study |
| 点击 About | 右侧滑出履历面板 |
| Esc | 关闭 case study 与 About |

- 切换用"吸附"而不是自由滚动：三块面板只有三个合法位置。
- 拖拽阈值 10px；低于阈值视为点击，不能误触切换。

## 四、Case study 与 About

- Case study：`clip-path: inset(100% 0 0 0)` → `inset(0)`，760ms `cubic-bezier(.22,.8,.2,1)`；背景用该面板的 art 渐变；内容为 kicker、项目名（`clamp(48px,9vw,150px)`、900 字重、行高 .86）、一段描述；右上 `CLOSE ×`。
- About：右侧 520px 面板，`translateX(101%)` → `0`，620ms；内容为 `Creative Engineer` 大标题、两段自我介绍、三行 `dl`（WEBGL / FRONTEND / MOTION）。
- 两个层都不能用卡片、圆角容器、阴影盒子。

## 五、HUD（必须极简）

- 左上：姓名 13px + `Independent Creative Engineer` 11px 灰。
- 右上：`About` 文字按钮，下方 1px 线，hover 时线从 30% 拉到 100%。
- 底部：`01 / 03` 计数、当前项目名、1px 进度条（当前格白色，其余 18% 白）、两个 34px 圆形箭头。
- 底部中央一行 9px 提示 `wheel / drag · click the centre panel`，首次交互后淡出。
- 除此之外不允许有任何导航、标签、社交图标。

## 六、视觉规范

- 字体：`Inter / Helvetica Neue`，不引网络字体；标题 600 字重、负字距 `-.045em`。
- 颜色：背景 `#080808`、文字 `#F7F7F7`、灰 `#8A8A8A`；项目 art 允许雪蓝、粉紫、暖橙，但都必须压暗、加暗角。
- 圆角：面板 8px，按钮 999px；不要 16px 以上的卡片圆角。
- 阴影：只允许 `0 60px 100px -60px rgba(0,0,0,.9)` 这种大而软的舞台阴影。
- 移动端：面板宽 84vw；隐藏项目名；HUD 边距降到 14px。

## 七、禁止项（出现任意一条即不合格）

- 禁止给平面加 `skew` 假装弯曲；必须切片 + rotateY + translateZ。
- 禁止卡片网格、三列 feature、导航栏、渐变按钮、玻璃拟态。
- 禁止 `Unlock`、`Seamless`、`Elevate`、`Revolutionize`、`Supercharge`。
- 禁止自由滚动 + 无吸附；三块面板必须只有三个合法位置。
- 禁止用真实图片/视频；所有 art direction 用 CSS 渐变自造。
- 禁止把 About 做成新页面；必须是右侧滑层。
- 禁止自动轮播；切换必须由用户输入触发。

## 八、验收清单

- [ ] 双击 `index.html` 可运行，零网络请求。
- [ ] 面板边缘确实向后弯（切片可见但无缝）。
- [ ] 滚轮/拖拽/箭头三种方式都能切换，且只有三个合法位置。
- [ ] 中心面板最亮最大，两侧压暗缩小；切换有 760ms 过渡。
- [ ] 点击中心面板，case study 从底部拉开；`CLOSE`/`Esc` 收回。
- [ ] About 从右侧滑出，`CLOSE`/`Esc` 收回。
- [ ] 1440×900 与 390×844 都不溢出；控制台 0 error。
- [ ] 页面里没有任何外部 URL、字体、图片、音频。

## 九、输出格式

先给 6 行设计决策（为什么切片而不是 skew、为什么三块而不是无限轮播、为什么用吸附），再给完整代码。不要伪代码，不要省略号。

## 附：深挖参数（来自原站 TSL shader）

- `new THREE.PlaneGeometry(w, h, 32, 16)` + TSL 节点材质（`MeshBasicNodeMaterial`），不是切片 mesh。
- `radiusX = loopWidth / totalArcRad`，`radiusZ = radiusX * JS`，`ovalRatio = radiusZ/radiusX`。
- 弯曲：`z += (1-cos(y/uPanelRadius)) * uPanelRadius * uOvalFlatness * uCurveAmount`；入场再加 `uEntryCurveAmount`。
- 复现用 32 片：`translateZ(-(1-cos(|t|π/2)) * 92px)`，`--curve` 从 1.55 → 1，760ms。

<a id="F9-janna-deloume-peel-tilt.prompt"></a>
## F9-janna-deloume-peel-tilt.prompt

# 强提示词：复刻「Janna Deloume」的 插画 hero + 蓝色横幅 + 痛点卡片 + peel/tilt/sheen 卡片

## 一、硬约束

- 单页、零外部依赖：不引 CDN、不复用原站图片/字体/视频；所有视觉用 CSS/SVG/Canvas 自造。
- 桌面 1440×900 与 390×844 都可运行；390px `scrollWidth <= innerWidth`。
- 核心机制可用鼠标完成：滚轮、点击、至少 8 方向拖拽；无键盘也可用。
- 有 `prefers-reduced-motion` 降级。

## 二、机制
- 插画 hero + 蓝色横幅 + 痛点卡片 + peel/tilt/sheen 卡片。
- 状态机：`tilt(rx, ry, mx, my)`：pointer 在卡片内归一化，deadzone 0.035，最大 30°；离开复位。

## 三、视觉规范
- 参考：手绘巴黎人像 + 奶油底 + 蓝带；卡片有完整的 peel/tilt/sheen 参数（13 个 u*），是“触感”最好的站。
- 颜色/字体/间距按 `DEEPEST-REVERSE.md` 的 F12 计算样式；不要用通用渐变按钮。

## 四、禁止项

- 不要 bento grid + 渐变 CTA + 通用 3D blob。
- 不要把“原站 shader 段数”当成自定义 shader；先看 `u*`。
- 不要把推断写成 observed；未知写 unknown。

## 五、验收

- `node deepest/test_site.mjs <site>` errors=0、mobile diff=0。
- 8 方向拖拽/滚轮/点击至少各 1 个状态变化，且截图可复核。
