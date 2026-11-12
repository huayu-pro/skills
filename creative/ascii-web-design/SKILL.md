---
name: "ascii-web-design"
description: "Creates ASCII/character-based web visuals and animations: image/GIF/video-to-ASCII, SVG/vector-to-ASCII, matrix rain, terminal UI, CRT effects, ASCII charts, halftone portraits, animation patterns, audio-reactive visuals, scroll/pointer interactivity, and Remotion video export. 当用户提到 ASCII 艺术、终端 UI、CRT 复古、字符画、字符雨、网点印刷、把图片/视频/logo/SVG 转成字符、把字符动画导出成视频/MP4、用 Remotion 做字符动画、音乐可视化、滚动渐变、鼠标交互字符画、批量预生成字符帧、字符画里放中文时使用。不用于：常规数据可视化（用图表 skill）、非字符化的复古海报、纯 CSS 故障艺术。"
metadata:
  version: "1.4.0"
  last_verified: "2026-10-25"
---

# ASCII Web Design

```
     _    ____   ____ ___ ___   __        __   _       ____            _
    / \  / ___| / ___|_ _|_ _|  \ \      / /__| |__   |  _ \  ___  ___(_) __ _ _ __
   / _ \ \___ \| |    | | | |    \ \ /\ / / _ \ '_ \  | | | |/ _ \/ __| |/ _` | '_ \
  / ___ \ ___) | |___ | | | |     \ V  V /  __/ |_) | | |_| |  __/\__ \ | (_| | | | |
 /_/   \_\____/ \____|___|___|     \_/\_/ \___|_.__/  |____/ \___||___/_|\__, |_| |_|
                                                                         |___/
```

ASCII 设计的本质是**字符化**：用字符替代像素表达图像与动效，自带"数据流 / 终端 / 极客"科技感（代表案例：ghostty.org 首页的多灰度静态 ASCII 吉祥物、poolside.ai 的伪终端 UI、Awwwards 多个交互式 ASCII 作品）。2026 年它已并入 Cyberbrutalism 大潮——故意暴露技术底层（代码行、系统符号、故障噪声）成为主流设计语言。

## 0. 需求澄清（先问再做，禁止直接开写）

拿到用户的初步提示词后，先联想其场景（hero 背景 / logo / 全屏动画 / 装饰组件 / 数据图表 / 落地页），然后**分两档提问**——简单装饰件走快问档（§0.1），整站 / 图表 / 浮点数据 / 实时动效类项目必须走深度档（§0.2）。所有提问**给出预设选项 + "自定义"出口**，一轮问完，不要挤牙膏。

### 0.1 快问档（装饰性需求，4 问）

| 维度 | 预设选项 | 说明 |
|---|---|---|
| **场景** | hero 主视觉 / 章节分隔 / 全屏背景 / 伪终端窗口 / 加载动画 / 数据图表 | 决定网格尺寸与性能预算 |
| **风格预设** | 见下方风格表 | 决定配色、字符集、动效气质 |
| **底色** | 深底浅字（推荐） / 浅底深字 | 决定 ramp 方向与 `invert` |
| **动效** | 静态 / 循环播放 / 交互响应（鼠标、滚动） | 决定路线与降级策略 |

**冲突消解规则**：风格预设的"动效气质"是默认值；用户在第 4 问中显式选择的动效**覆盖**预设气质列；用户未显式选择时，以预设气质列为准。回显确认时须体现最终生效值（如"极简禅 + 用户指定 glitch"）。

**风格预设表**（用户选风格即锁定整套视觉参数，避免逐项纠结）：

| 风格 | 主色 | ramp / 字符集 | 边框 | 动效气质 |
|---|---|---|---|---|
| Matrix 黑客 | 绿 `#00FF41` | 半角片假名+数字 | 无 / 细线 | 字符雨、流式输出 |
| 琥珀终端 | 琥珀 `#FFB000` | 经典 10 级 | 双线 `╔═╗` | 打字机、光标闪烁 |
| Cyberpunk | 品红 `#FF00FF` + 青 `#00FFFF` | 方块 `░▒▓█` | 粗线 `┏━┓` | glitch 抖动 |
| 极简禅 | 白 / 灰阶 | 稀松 ramp ` .:'` | 细线 `┌─┐` | 几乎静止 |
| 粗野主义 | 纯白 on 纯黑 | 方块 `█` 为主 | 方块 `█▀▄` | 硬切，无过渡 |
| 复古大型机 | 青绿 + 蓝灰 | 70 级长 ramp | 双线 + 装饰角 `◆` | 扫描线、慢速 |
| Vaporwave | 粉蓝紫渐变 | 全角字符 + `ｱｲｳ` | 圆角 `╭─╮` | 慢速漂移 |
| 网点印刷 Halftone | 黑 `#000` on 白底 | `•∙·` 点阵（Bayer 抖动） | 无，大面积留白 | 静态为主 |

### 0.2 深度档（整站 / 图表 / 浮点 / 实时类，6 组问题）

在 §0.1 四问之上追加，按需裁剪（纯装饰静态图可跳过性能/安全组）：

| 组 | 维度 | 预设选项 / 探问点 |
|---|---|---|
| **技术精度** | 渲染精度档位 | 标准 10 级 ramp / 高清 24 级 / 超高清 70 级+抖动 / 盲文 2×4 亚像素（见 image-to-ascii.md §2.2）；彩色需求 → 是否启用 §2.3 浮点管线（float32/16/量化，见 image-to-ascii.md §2.3）；矢量素材 → 是否走 SVG 栅格化路线（见 image-to-ascii.md §2.5） |
| | **圆润度 / 浮点密度** | 曲线类图（饼/环/玫瑰/雷达）用 Canvas 弧线还是字符网格（前者边缘平滑、后者终端感强，见 ascii-charts.md §F.0）；浮点数值的显示密度（整数 / 1 位 / 2 位小数，按占比自适应） |
| | 数据精度 | 图表数值的有效位数；浮点模式的位深与色彩空间（sRGB 直用 / 线性化运算） |
| | 等宽网格语言 | 纯 ASCII-safe / 允许 Unicode 方块与制表符 / **含 CJK 全角文案**（后者必须走 image-to-ascii.md §2.6 的网格对齐方案，禁止与半角 ramp 混排） |
| **实现方式** | 路线与架构 | 自研内核（references/image-to-ascii.md）/ 成熟库（chartscii、termatplotlib、termaid，见 ascii-charts.md）/ 混合；构建期预生成（零运行时成本）/ 运行时实时采样 |
| | 技术栈偏好 | 原生 JS / React / Vue / Astro；是否允许引入依赖；三端交付范围（见 terminal-templates.md：HTML 必有，Python/C 是否都要） |
| **性能指标** | 帧率与规模 | 目标 fps（30/60）、网格规模（列数上限）、素材体积上限（经验参考：单 GIF 约 ≤2MB，换取帧序列方案）；并发：同屏动画实例数 |
| | 响应预算 | 首帧时间（预生成 ≈ 0ms / 运行时采样一次性开销）、交互响应延迟（目标：鼠标跟随约 ≤16ms，即一帧预算） |
| **兼容性** | 渲染环境 | 现代浏览器全量 / 需兼容旧浏览器（降级链见 §5）；终端能力：truecolor+Unicode / 仅 256 色 / **仅纯 ASCII**（决定 ASCII-safe 模式，见 ascii-charts.md） |
| | 设备与系统 | 桌面 / 移动（列宽收窄或静态回退）；终端版目标平台：Linux/macOS/原生 Windows（影响 C 模板的 VT 分支） |
| **安全考量** | 素材与数据 | 图片本地处理（默认，零上传）/ 允许远程 URL（需 CORS 与 `crossOrigin`）；用户上传素材的格式白名单与体积上限 |
| | 输出卫生 | 用户输入回显终端前**必须剥离控制字符**（防 ANSI 注入：`\x1b`、`\x07` 等，见 §1.1）；浮点数据文件是否含敏感信息 |
| **用户体验** | 交互流程 | 键盘快捷键映射（如 `T` 切换）、伪终端命令集设计、easter egg 策略 |
| | 操作反馈 | 加载态（打字机进度 / 光标闪烁）、错误提示风格（终端风 `command not found`）、`prefers-reduced-motion` 回退（§5 强制项，确认即可） |

用户回答后回显一句话确认（如"Matrix 风格 / 深底 / 循环动画 / hero 区 / 高清档 / 桌面优先"），再进入实现。**用户说"随便/你定"时，默认：Matrix 风格、深底、循环动效、120 列、标准精度档、现代浏览器、本地处理素材。**

## 1. 路线选择（先查这两张表）

### 1.0 用户话语 → 路线速查表（按用户原话直查）

| 用户会说的话 | 去读 | 交付物 |
|---|---|---|
| 把这张图转成字符画 / ASCII | image-to-ascii.md §2.1 | 静态字符画（HTML 内嵌） |
| 要更精细 / 像照片 / 盲文线稿 | image-to-ascii.md §2.2–2.3 | 高精度档字符画 |
| 黑客帝国字符雨 | web-implementation.md §3.5 | 网页 canvas 动画 |
| 这个 GIF 转成字符动画 | web-implementation.md §3.1 | 网页播放器 |
| 摄像头实时字符化 | web-implementation.md §3.2 | 网页实时画面 |
| 3D 模型转字符 | web-implementation.md §3.3–3.4 | 网页 WebGL |
| 做个终端风网站 / 命令行作品集 | terminal-ui.md | 伪终端整站 |
| 大字标题 LOGO | web-implementation.md §3.5 | FIGlet 静态字 |
| 复古显示器 / 老电视质感 | web-implementation.md §3.7 | CRT CSS 层 |
| 数据做成 ASCII 图表 | ascii-charts.md | HTML/终端图表 |
| 把字符动画导出成视频 / MP4 / GIF 文件 | remotion-video.md | MP4/WebM/PNG |
| 用 Remotion 做字符动画 | remotion-video.md | React 视频项目 |
| 标题动起来（打字机/渐变/溶解…） | animation-patterns.md | 网页动效/视频片段 |
| 音乐可视化 / 随节奏跳动的字符 | audio-visual.md | 网页实时 + 可导出视频 |
| 滚动时字符画变化 / 鼠标照亮 | scroll-and-pointer.md | 交互式长页 |
| 批量预生成 / 离线可用的字符帧 | web-implementation.md §3.9 | frames.json（scripts/ascii_pipeline.py） |
| 网点印刷 / 报纸肖像 | image-to-ascii.md §2.4 | 二值网点图 |
| SVG / 矢量 logo 转字符（细线要保住） | image-to-ascii.md §2.5 | 超采样栅格 + 覆盖率采样 |
| 字符画里要放中文 / 全角文案 | image-to-ascii.md §2.6 | CJK 感知网格 / 全角补位 |
| 完整案例跟着做一遍 | walkthrough.md | Matrix 字符雨全链路 |
| 遇到报错/画面不对 | faq.md | 排错答案 |

按需求类型查总表：

| 需求 | 路线 | 依赖 |
|---|---|---|
| 静态图片转 ASCII（logo / 海报 / hero 图） | Canvas 采样内核（→ image-to-ascii.md §2.1），或在线工具预生成 | 无 |
| GIF 动图 → ASCII 动画 | gifuct-js 解帧 + 采样内核（→ web-implementation.md §3.1） | `gifuct-js` |
| 视频 / 摄像头实时 ASCII | `<video>` 逐帧采样；优先 `requestVideoFrameCallback`（→ web-implementation.md §3.2） | 无 |
| Three.js 3D 场景 → ASCII | 官方 `AsciiEffect`；GPU 全速用 `ascii-scene` / `@ascii-fx/three`（→ web-implementation.md §3.3） | `three` |
| 全屏 60fps 实时 ASCII 背景 | WebGL shader 后处理（字符图集，→ web-implementation.md §3.4） | 自研 / OGL / `textmode.js` |
| 大字标题横幅 | figlet.js（200+ FIGfont，→ web-implementation.md §3.5） | `figlet` |
| 边框 / 分隔线 / 伪窗口 | box-drawing 字符全套风格表（→ web-implementation.md §3.5） | 无 |
| 黑客帝国字符雨 | Canvas 列下落 + 半透明拖尾（→ web-implementation.md §3.5） | 无 |
| 高精度线稿 / 矢量轮廓 | 盲文点阵 2×4 子像素（→ image-to-ascii.md §2.2），矢量源走 §2.5 | 无 |
| 彩色像素级复刻（保色不抽象） | 浮点彩色内核，数据层与显示层分离（→ image-to-ascii.md §2.3） | 无 |
| 网点肖像 / 报纸印刷质感 | Halftone 有序抖动内核，白底黑点（→ image-to-ascii.md §2.4） | 无 |
| 整站伪终端作品集（命令行浏览） | 伪终端站范式（→ terminal-ui.md） | 无 |
| 双视觉切换（现代页 ⇄ ASCII 模式） | 模式切换开关（→ web-implementation.md §3.6） | 无 |
| CRT 复古质感层 | 扫描线/暗角/辉光 CSS 包（→ web-implementation.md §3.7） | 无 |
| 数据图表（柱状/折线/饼图/甘特等） | ASCII 图表内核或成熟库（→ ascii-charts.md §A 终端引擎） | `chartscii` / `termatplotlib` |
| 结构图（流程图/时序图/树图） | Mermaid→ASCII 或手绘范式（→ ascii-charts.md §A） | `termaid` / `mermaid-ascii` |
| 交互图表 / 数据大屏 / 动态图（网页） | HTML 交互图表引擎（→ ascii-charts.md §B 架构，其下 §C 主题 / §D 交互 / §E 响应式 / §F 图表类型库〔含 §F.1 饼图族、§F.2 动态播放、§F.3 扩展图表〕/ §G 大屏 / §H 智能匹配） | 零依赖自研 / ECharts 主题包 |
| ASCII 动画导出视频 / MP4 / GIF 文件 | Remotion 帧驱动组件（→ remotion-video.md） | `remotion`（特殊许可证，见 §R.10） |
| 标题/网格动效（打字机、揭示、溶解、glitch、morph…） | 动效模式库纯函数，三端同构（→ animation-patterns.md） | 无 |
| 音频驱动可视化（频谱/波形/呼吸） | Web Audio AnalyserNode（→ audio-visual.md；导出视频见其 §M.5） | 无（视频导出需 `@remotion/media-utils`） |
| 滚动叙事 / 鼠标交互（照亮、显原像素、鱼眼） | 滚动进度 + 指针交互滤镜（→ scroll-and-pointer.md） | 无 |
| 批量预生成 / 离线兜底素材 | 构建期管线（→ web-implementation.md §3.9 + scripts/ascii_pipeline.py） | Pillow / ffmpeg（均可选，缺失有指引） |

**依赖红线**（快照日期：2026-10-25，复审时更新）：`jscii`、`asciify-image` 已停更/归档（npm 页面可查最后发布时间），只可读原理，不要引入项目。`gifuct-js` 仅 CommonJS 导出，Vite/ESM 中用默认导入：`import pkg from 'gifuct-js'`。不想自研渲染循环时，优先评估活跃新秀：`textmode.js`（创意编码向）、`ascii-scene`（.glb 模型直转 GPU ASCII，含鼠标跟随）——**引入前核对当次安装的版本与最后发布时间**。Remotion 采用特殊许可证（个人/非营利/≤3 人公司免费，更大需付费），引入前先确认使用主体性质（remotion-video.md §R.10）。

## 1.1 ASCII 编码基础（选用字符前必知）

标准 ASCII 共 128 个码位（0–127），只有 **32–126 是 95 个可打印字符**——这才是 ramp 与字符画的合法原料库：

- `32` 空格（ramp 的起点，"最亮"）；`33–47 / 58–64 / 91–96 / 123–126` 共 33 个标点符号；`48–57` 数字；`65–90` 大写；`97–122` 小写。
- **0–31 与 127 是控制字符，永远不要放进 ramp**——它们不可见或会触发终端行为。唯一例外是渲染控制：`LF(10)` 换行、Web/终端渲染时的 `ESC(27)` ANSI 序列（着色、光标移动，见 terminal-templates.md）。
- 记忆锚点：大写 `A=65`、小写 `a=97`（大小写恒差 32）、数字 `0=48`——手写编码工具（hex⇄char）时天天用。
- 扩展 ASCII（128–255）**不是统一标准**，各代码页映射不同，跨平台作品禁用；需要更密字符时走 Unicode 明确码位：box-drawing（U+2500+）、方块渐变 `░▒▓█`（U+2591–2588）、盲文（U+2800+）、半角片假名（U+FF66–FF9D）。
- 经典 10 级 ramp `' .:-=+*#%@'` 全部落在可打印区间；自行扩充 ramp 时按"视觉墨量"排序，而非码值排序。
- **换行符陷阱**：Windows 工具生成的字符画带 `\r\n`，直接塞进 `<pre>` 或终端帧会多出空行/错位。入库前统一 `.replace(/\r\n?/g, '\n')`。

**素材库**：需要现成字符画（动物/logo/边框/表情）时先查 asciiart.eu（11,000+ 分类作品）与 getascii.com 的符号集（shrug、table-flip、lenny 等），不要从零手绘常见题材。

## 1.2 视觉契约（单一事实源）

以下常量为全部实现（JS / Python / C / 图表 / Remotion）的唯一定义处；各代码副本必须与此一致，改此处即改全站：

| 契约项 | 值 | 说明 |
|---|---|---|
| RAMP | `' .:-=+*#%@'` | 10 级，亮→暗；仅当用户选 24/70 级档时整体替换 |
| 亮度系数 | `0.299 / 0.587 / 0.114` | Rec.601，三端共用 |
| **亮度→字符索引** | `index = min(n−1, floor(lum × (n−1)))` | **明文公式**。`n = RAMP.length`，`lum ∈ [0,1]` 为 alpha 合成后的相对亮度。乘 `n−1` 而非 `n`：10 级 ramp 只有 9 个间隔，乘 `n` 会让 `lum ∈ [0.5,1)` 系统性偏密一档。整数等价式：`floor(v × (n−1) / 1000)`（v 为千分亮度） |
| 纵横比修正 | `0.55`（区间 0.5–0.66） | 随字体微调，改动需同步三端；行数 `rows = round(cols × 源高/源宽 × 0.55)` |
| COLS 甜点 | `80–160` | 超宽终端居中裁切；Halftone 默认取上沿 160（见 image-to-ascii.md §2.4），下限 80 不可破 |
| 帧率 / 帧间隔 | `12 fps` / `1/12 s ≈ 83.33 ms` | 三端同帧间隔：HTML `STEP = 1000/FPS`、Python `FPS_DELAY = 1/12`、C `FRAME_TS = {0, 83333333}`；管线 `--fps` 默认同为 12（GIF 按原 delay 推算）。改帧率即三端 + 管线同步改 |
| 强调色（24-bit ANSI） | `#00FF41` → `\033[38;2;0;255;65m` | 单强调色契约：网页 `color: #00FF41`，终端真彩色 `38;2;R;G;B` 与 `\033[m` 复位。风格预设换色时三端同步换（协议细节见 terminal-templates.md） |

> 引用规则：跨文件引用必须带文件名（`<file>.md §x.y`）；不带文件名的 `§x` 仅指 SKILL.md 自身章节。
> 契约的机器可读副本：`scripts/ascii_pipeline.py`（Python 采样内核）、`assets/templates/ascii.{html,py,c}`（三端骨架）。`scripts/selfcheck.sh` 断言三端 ramp / 纵横比 / 帧间隔 / 索引公式与上表逐字一致，`scripts/verify_deliverable.py three-ends` 断言三端同帧输出逐字节相同。

## 2. 实现手册（按需求跳转）

主文件只保留路由与原则；代码实现拆到 `references/`，按需读取：

| 需求 | 去读 | 覆盖内容 |
|---|---|---|
| 图片/GIF/视频/摄像头 → ASCII | [references/image-to-ascii.md](references/image-to-ascii.md) | 采样内核、ramp 设计、精度档位（10级→24级→70级→盲文）、浮点彩色内核（L1采集→L2精度→L3交换→L4消费）、Halftone 网点内核、SVG/矢量栅格化（§2.5）、CJK 全角网格对齐（§2.6） |
| GIF 解帧、视频流、Three.js、GPU shader、FIGlet/box-drawing/字符雨 | [references/web-implementation.md](references/web-implementation.md) | 各路线代码模板与坑点、等宽校准（§3.8）、CRT 质感 CSS 包、双视觉模式切换、构建期管线（§3.9） |
| 整站伪终端（命令行浏览的作品集站） | [references/terminal-ui.md](references/terminal-ui.md) | 命令表驱动骨架、历史/补全、打字机输出、easter egg |
| 数据图表（柱状/折线/饼图/甘特/流程图等） | [references/ascii-charts.md](references/ascii-charts.md) | 终端引擎（§A）+ HTML 交互引擎（§B 架构 → §C 主题 / §D 交互 / §E 响应式 / §F 图表类型库〔§F.1 饼图族、§F.2 动态播放、§F.3 扩展图表、§F.4 注册接口〕/ §G 大屏 / §H 智能匹配） |
| 三端交付（HTML+Python+C 同 slug） | [references/terminal-templates.md](references/terminal-templates.md) + [assets/templates/](assets/templates/) | Python stdlib 模板、C99 模板、ANSI 控制字符协议、三端分工；`assets/templates/ascii.{html,py,c}` 为可直接复制运行的三端骨架 |
| 导出视频 / Remotion 字符动画 | [references/remotion-video.md](references/remotion-video.md) | 决策表、概念映射、AsciiRain/AsciiImage 完整示例、帧序列、特效、导出命令、许可证 |
| 字符网格动效（8 种模式） | [references/animation-patterns.md](references/animation-patterns.md) | 打字机/揭示/扫描/溶解/glitch/波浪/级联/morph + 组合规则与性能红线 |
| 音频驱动可视化 | [references/audio-visual.md](references/audio-visual.md) | Web Audio 链路、频谱/波形/呼吸三映射、Autoplay 红线、Remotion 音画同步 |
| 滚动叙事 / 鼠标交互 | [references/scroll-and-pointer.md](references/scroll-and-pointer.md) | 滚动进度、精度/密度渐变、场景切换、指针照亮、显原像素、触屏回退 |
| 端到端完整案例 / 排错 | [references/walkthrough.md](references/walkthrough.md)、[references/faq.md](references/faq.md) | Matrix 字符雨全链路十步（可直接运行的 HTML）；27 条常见问题集中答疑 |

构建期批量预生成用 `scripts/ascii_pipeline.py`（用法与 JSON 契约见 web-implementation.md §3.9；调参迭代时 `serve` 子命令起本地实时预览，产物变更自动重载）。两个校验脚本分工明确：`scripts/selfcheck.sh` 查**包自身**完整性（章节/引用/契约常量/红线扫描），`scripts/verify_deliverable.py` 查**用户交付物**是否满足 §7 的【自动】项（`<子命令> <项目目录>`，`self-test` 为它自己的必红用例自测）。三端骨架直接从 `assets/templates/ascii.{html,py,c}` 复制改名即可开工。

## 3. 排版 CSS（质感关键）

```css
.ascii {
  font-family: "JetBrains Mono", "IBM Plex Mono", "Courier New", monospace; /* 必须等宽 */
  font-variant-ligatures: none;  /* 防连字破坏网格 */
  white-space: pre;
  margin: 0;
  line-height: 1;                /* 消除行缝 */
  letter-spacing: -0.05em;       /* 可负值压实，逼近"方形像素" */
}
```
换字体必须重新调校 line-height / letter-spacing / 纵横比系数（实测方法见 web-implementation.md §3.8 `measureCell`），否则图像变形。

## 4. 美学原则（从好看到专业）

1. **等宽不可妥协**——比例字体瞬间破功。选有个性的等宽体：JetBrains Mono / Berkeley Mono / IBM Plex Mono。
2. **单强调色**——黑底 + 一个主色（经典绿 `#00FF41` / 琥珀 `#FFB000` / 青 `#00FFFF`）。每多一个颜色都要像 CLI flag 一样"挣得"自己的位置。
3. **CRT 质感只能耳语**——扫描线/暗角/辉光按 web-implementation.md §3.7 的克制剂量；整屏弯曲变形只放 hero 演示区。
4. **动效像真终端**——逐字渲染、光标闪烁、stdout 流式输出。禁止 ease-in-out、禁止回弹——机器不回弹。
5. **信息密度是特性**——紧行距、可见数据、密集排版。这个美学犒赏会解析信息的人。
6. **有意的粗糙**——Cyberbrutalism 信条：数字噪声、像素化、glitch 不是 bug，是视觉表达。但不要过度打磨到失去实验感。
7. **网格一致性**——同一作品内字符格必须全局对齐：混用全角/半角、混入 emoji（宽度不确定）都会撕裂网格。emoji 只放 `<pre>` 之外的 UI 层。

## 5. 无障碍与工程兜底

- **屏幕阅读器**：装饰性 ASCII 容器加 `aria-hidden="true"`；若承载信息，旁边放 `.visually-hidden` 的文本等价物。`<pre>` 里的字符画对读屏是纯噪声。
- **音频可视化**：音频内容必须有可见/可读替代（文本摘要或字幕轨）；开启入口必须是显式交互（Autoplay 手势策略，audio-visual.md §M.4）。
- **`prefers-reduced-motion`**：媒体查询命中时动画回退为静态帧。
- **SEO/内容**：ASCII 字符画不参与文案语义，标题正文仍用正常 HTML 标签。
- **降级链**：WebGL shader → Canvas fillText → `<pre>` textContent → 静态预生成字符串，按设备能力逐级回退。

## 6. 性能红线

- 渲染载体：`<pre>` + `textContent` 首选（经验参考：约 150×60 网格可在典型桌面维持 60fps，未标注测量条件，项目以实测为准）；彩色/大网格用 Canvas `fillText`；不要手写 `<table>` 方案；全屏实时才上 WebGL。
- 动画用 `requestAnimationFrame`（视频源优先 `requestVideoFrameCallback`），支持降帧；`IntersectionObserver` 离屏暂停；后台标签页停转。
- 纵向采样可跳行（`y += 2`），字符本身高瘦，观感损失小。
- canvas 尺寸只在输入分辨率变化时重设，逐帧重分配会触发 GPU buffer 重建。
- 配色：黑底 + 单色字符最稳（经典绿 `#00FF41` / 白 / 琥珀色）。

## 7. 验收清单

> 图例：【自动】= 可脚本断言；【人工】= 需走查/实机。
> 【自动】项分两组：**包自身完整性** → `bash scripts/selfcheck.sh`；**用户交付物** → `python3 scripts/verify_deliverable.py <子命令> <项目目录>`。每条【自动】项末尾括注兑现它的命令，别凭记忆手敲 grep。

1.【人工】§0 四问已确认（场景/风格/底色/动效），或用户明确说"你定"；预设×动效冲突已按消解规则处理。
2.【人工】等宽字体 + 禁连字；纵横比已修正，图像不拉伸变形。
3.【人工】ramp 明暗方向与页面底色匹配（深底→亮部密字符；浅底→反转）。
4.【人工】空格字符不塌陷（`<pre>` 或 `&nbsp;`）；无全角/emoji 混入网格（确需 CJK 见 image-to-ascii.md §2.6）。
5.【自动】GIF 完整帧：`frames.some(f => f.dims.left || f.dims.top || f.dims.width !== W || f.dims.height !== H) === false`，为 true 时已走合成路径（web-implementation.md §3.1）。→ `verify_deliverable.py gif-frames`（数据层逐帧同尺寸 + 源码层合成守卫）
6.【人工】动画可暂停/降帧，离屏与后台不空转；`prefers-reduced-motion` 有静态回退。
7.【人工】装饰性 ASCII 已 `aria-hidden`；承载信息的有文本等价物。
8.【人工】移动端降级：收窄列宽或回退静态 ASCII 图。
9.【自动】三端齐套：同目录 `<slug>.html` / `<slug>.py` / `<slug>.c` 三件并存；三端 ramp 字符串相同；`gcc -O2 -std=c99 <slug>.c -o <slug>` 与 `python3 -m py_compile <slug>.py` 退出码 0；三端同帧输出**逐字节一致**。→ `verify_deliverable.py three-ends <目录> [--slug X]`（可直接拿包内 `assets/templates/` 当绿例）
10.【人工】美学走查：单强调色、CRT 质感克制、动效无缓动回弹、box-drawing 风格全站统一。
11.【自动】ASCII-safe 档：`/^[\x20-\x7E\n]*$/.test(ramp) === true`；Unicode 档码位在白名单内（box-drawing / 方块 / 盲文 / 半角片假名 / 几何图形 / 箭头）；素材换行符已统一为 `\n`。→ `verify_deliverable.py ascii-safe <目录> [--mode unicode]`
12.【人工】伪终端站（如适用）：`help` 列出全部命令、↑↓ 历史不越界且草稿可恢复、Tab 补全生效、`clear` 生效、有至少一个 easter egg；移动端有命令快捷按钮。
13.【自动】浮点元数据四件套（`width` / `height` / `channels` / `colorspace`）+ `premultiplied` + `rowOrder: 'top-down'` 随数据落盘；PFM 头尺寸与元数据一致；源图 >512px 已降采样。→ `verify_deliverable.py float-meta <目录>`
14.【自动】图表数据 JSON 三端同源（各份 `data.json` md5 一致）；刻度 1-2-5 友好值由 `niceCeil` 生成（校验器抽函数实跑 13 个探针）。→ `verify_deliverable.py chart-data <目录>`
15.【人工】Halftone：严格二值输出（只允许空格 + 点字符）；Bayer 4×4 周期确认；列数按 image-to-ascii.md §2.4 口径（默认 160，细粒肖像可到 240，**不得低于契约甜点下限 80**）；反相需求已确认。
16.【自动】回显消毒断言 `/[\u0000-\u0008\u000B\u000C\u000E-\u001F\u007F]/.test(echoed) === false`（抽源码 sanitize 实跑 + 回显样本扫描）；深度档六组问题已确认或明确豁免。→ `verify_deliverable.py sanitize <目录> [--echo-file X]`
17.【自动】`grep '^## ' SKILL.md` 章节编号连续无洞（0,1,1.1,1.2,2,3,4,5,6,7）。→ `selfcheck.sh` 第 1 项
18.【自动】frontmatter 版本字段齐套：`grep -c '^ *version:\|^ *last_verified:' SKILL.md` 为 2（生态快照可溯源；`version` 在 `metadata` 嵌套下，故用 `^ *version:` 而非 `^version:`；`^` 锚定避免本断言行自匹配）。→ `selfcheck.sh` 第 2 项
19.【自动】Remotion 项目交付：`out/*.mp4` 存在且时长 > 0（`ffprobe -v error -show_entries format=duration`）；`src/` 内无 `Math.random` 调用（确定性红线，remotion-video.md §R.10）。→ `verify_deliverable.py remotion <项目目录>`
20.【自动】网络加载卫生：源码内除 `loadWithRetry` 自身外无裸 `await fetch(`（全部经重试封装，web-implementation.md §3.0）；管线脚本 `python3 scripts/ascii_pipeline.py self-test` 退出码 0（含 ramp 索引公式断言）。→ `verify_deliverable.py network <目录>` + 管线 self-test
21.【人工】音频页（如适用）：有"点击开启"显式入口；静音状态有静态频谱兜底；`smoothingTimeConstant ≥ 0.8`（audio-visual.md §M.4/§M.6）。
22.【人工】滚动/指针页（如适用）：触屏有点击等价交互；`prefers-reduced-motion` 呈现终态静态档（scroll-and-pointer.md §I.6）。
23.【人工】动效组合（如适用）：入场动效播完即停、常驻动效唯一，遵守 animation-patterns.md §P.9 组合规则。
24.【自动】包内自检：`bash scripts/selfcheck.sh` 退出码 0 —— 覆盖范围：章节编号连续、frontmatter 版本字段、引用文件存在、**三端 ramp 字符串逐字一致**、契约常量（纵横比 / 帧率 / 索引公式）、ASCII-safe 与换行符、Remotion 示例代码块内 Math.random 红线（全 references 扫描，网页端合法用法按围栏语言区分）、触发用例可解析、管线 self-test。

