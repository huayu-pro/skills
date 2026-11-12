# 09 · 动效设计原则

> 从 302 个逆向站点、343 个站点 JS bundle、12 个零依赖复合组件与 89 份 DEEP2
> 里反推的可检查约束。每条尽量给反例与实测值。没有实测支撑的标 `inferred`。
> 实现细节在 `22-motion-implementation.md`；验收在 `24-motion-verification.md`；
> 案例在 `23-motion-cases.md`。

## 1. 先分清两种动效

| 用途 | 例子 | 时长 | 频率 | 失败的样子 |
|---|---|---|---|---|
| **解释变化** | 菜单展开、元素从 A 到 B、内容替换、状态切换 | 120–350ms | 用户触发，必须有 | 太慢，用户觉得卡 |
| **吸引注意** | 首屏入场、关键 CTA 呼吸、品牌氛围 | 400–1200ms | 非用户触发，一页最多一次 | 太多，用户无法阅读 |

「每个区块淡入上移」「每张卡片 hover 抬起」属于第二类，却被用在第一类的位置，并且重复几十次。
结果是页面一直在动，用户没有一处可以安静阅读。

**约束 P1**：非用户触发的主动效，一个页面最多一个。用户触发的动效必须有，而且要快。

> 反例：首屏 hero 入场 1.2s + 三列 feature 各 0.8s 淡入 + logo 墙 40s 跑马灯 + 每张卡片 hover 抬升。
> 五个「注意」同时抢，等于没有注意。

## 2. 先选一个物理关系，再谈排版

耐看的页面几乎都先有一个**物理关系**，布局是它的投影，动效是它的证据：

| 物理关系 | 案例 | 布局表现 | 动效证据 |
|---|---|---|---|
| 椭圆轨道 | `155-001` | 六颗项目球绕核心 | 深度同时改 scale/blur/z/opacity |
| 竖切片曲面 | `155-002` | 32 条竖片 | `rotateY(t*-17°) + translateZ(...)` |
| 物理传送带 | pilots case 04 | 11 张卡在 3300px 环上 | `BASE=62`、`MAX=900`、`friction=1.1` |
| 可拖时钟 | pilots case 03 | 指针 + 日期 | 指针角度映射时/分/秒/日/月/年 |
| 热感扫描头 | batch-15 Kelvin | 5,780px 舞台 + 0 宽扫描线 | 滚动 = 扫描位置 |
| 唱片架 | batch-15 Bob Moll | 9 张 21vw 封面 | 原生 `scroll-snap` |
| 幕布/合页 | batch-15 Eight Shot | 320vh runway | `h=(π/2)(1-ease(p))` |
| 剖面图 | `atelier-north` | 垂直切片 + 侧标注 | 滚动 = 剖切位置 |
| 档案柜 | 编辑型站点 | 索引 + 抽屉 | 展开从条目边缘长出来 |

**约束 P2**：首屏只允许一个主结构（轨道、传送带、仪表、剪贴簿、幕布、扫描头、剖面、档案柜）。
不要 hero + 三列 feature + logo 墙同时上场。主结构不是背景装饰，它要决定内容的组织方式。

> 反例：三列卡片网格，每列一个 icon + 标题 + 两行字。它没有物理关系，只有栅格。

## 3. 输入映射成「力」，不是「状态」

滚轮和拖拽优先映射成**速度或角度**，再加摩擦/弹簧；不要直接设 `scrollTop` 或
`transform: translateY(scrollY)`。直接映射让页面像一张没有重量的图。

| 做法 | 实测参数 | 案例 |
|---|---|---|
| 速度 + 指数摩擦 | `boost *= exp(-dt*1.1)`；`BASE=62`、`MAX=900` | pilots case 04 |
| 角度 + 惯性 | `angle += (target-angle)*0.08 + velocity`；`velocity *= 0.9` | pilots case 01 |
| lerp 追目标 | `lerp .15`；decay `.95/.92`；`velocity*(touch?12:8)`；边界 `*0.15` | batch-15 Tegra |
| Lenis + GSAP scrub | `lerp:0.1`；`scrub:1` / `0.6` | `155-007`、`155-006` |
| 拖动映射角度 | `angle = atan2(dy,dx)*180/π + 90`；`norm=(angle+360)%360` | pilots case 03 |

**约束 P3**：拖拽/滚轮必须有「释放之后还在动」的层（惯性、摩擦、弹簧）或「吸附/回中」的层。
只有即时位移的拖拽，手感像拖动一张没有重量的图。

> 反例：每帧 `el.style.transform = translateY(scrollY)`；或 `scroll-behavior:smooth` 一把梭。

## 4. 深度要同时改四件事

只改 `scale` 看起来像缩放，不像空间。真实的深度至少同时改：

1. **大小**：`scale` 随 depth 变化。
2. **模糊**：后景 `blur`，前景清晰。
3. **亮度/透明度**：后景更暗或更透明。
4. **叠放顺序**：`z-index` 随 depth 变化。

pilots case 01 的实测：

```js
scale   = 0.72 + ((depth + 1) / 2) * 0.34;   // 0.72–1.06
blur    = depth < 0 ? (1 - depth) * 1.1 : 0;
zIndex  = 60 + Math.round(depth * 40);
opacity = 0.62 + ((depth + 1) / 2) * 0.38;
```

**约束 P4**：深度四通道要么一起改，要么不要假装有深度。

> 反例：所有卡片 `transform: scale(0.95)`，`z-index` 不变，`filter` 不变，看起来只是变小。

## 5. 几何因果：动效必须从交互点长出来

| 交互 | 正确做法 | 反例 |
|---|---|---|
| 主题/皮肤切换 | 从点击点/指针进入点 `clip-path: circle(0 → 165vmax)` 扩散，680ms | 全屏 `opacity: 0 → 1` |
| 展开/详情 | 圆心/方向来自被点击的物体（球心 `--cx/--cy`；从底部拉起） | 所有 modal 从屏幕中心 `scale(0.95)` |
| 过滤/删除 | 卡片「被移走/放回」（`clawOut` +0.09s / `clawIn` +0.12s） | `display:none` 瞬间消失 |
| 拖拽控件 | 指针和数字/文字同时变（拖时钟 → 指针 + 日期） | 拖 slider 只动滑块，数值不变 |

**约束 P5**：动效的起点、方向、圆心必须能追溯到触发它的那个物体。做不到，就不要做「大转场」，用短过渡。

## 6. 编排：错峰，但别让人等

多个元素同时进入视口时，错开 20–50ms 会显得有生命；但：

- 错开总时长不超过 300ms，否则最后几个元素让人等。
- 只对**同时进入视口**的一组元素做错峰。
- 列表超过 8 项时，只对前 8 项错峰，其余直接出现。
- 错峰要按阅读顺序（左→右、上→下），不要随机。

实测：GSAP `stagger` 主流 0.05–0.1s（0.1s 17 站、0.05s 10 站、0.2s 8 站）；
CSS 场景里 20–50ms 更适合「同一组一起出现」。

**约束 P6**：错峰是「让顺序可读」，不是「让每个元素都表演一次」。

## 7. 时长：三簇 + 两个手调值

| 簇 | 范围 | 用途 |
|---|---|---|
| 微交互 | 120–300ms | 按钮、hover、状态层、按下 |
| 段落转场 | 400–900ms | 卡片进/出、标题揭示、curtain |
| 长循环 | 1.4–24s | 呼吸、粒子、玻璃转圈、波浪 |
| 超长 marquee | 42–148s | logo 墙、ticker |

- **`0.45s`**：343 站 JS bundle 里出现 76 次的手调值；这是观测众数，**不是进入的默认**。默认来自 `28` 的 motion token 与 register。
- **`0.7s`**：Angelo 21 条入场统一 700ms；`reveal` 也是 0.7s。
- 84% 的站点时长落在 0.2 / 0.3 / 0.4 / 0.45 / 0.5 / 0.8 / 1.0 秒。
- 长循环不是「越慢越高级」：24s 的 Ken Burns 是背景，16s 的 mono turn 是氛围；
  超过 60s 的循环用户几乎感知不到，除非它是进度/时钟。

## 8. 缓动

| 场景 | 曲线 | 说明 |
|---|---|---|
| 进入 | `ease-out` / `cubic-bezier(0,0,.2,1)` | 快起慢停，像物体落位 |
| 退出 | `ease-in` / `cubic-bezier(.4,0,1,1)` | 慢起快走，像被带走 |
| 移动 | `ease-in-out` | 两端都慢，适合位移 |
| 落位/磁性 | spring | 有回弹，但不要每个元素都弹 |
| 进度/循环 | `linear` | 匀速，避免呼吸感干扰读数 |
| 强调 | `cubic-bezier(.22,.8,.2,1)` | 强快起慢停，适合大转场 |

GSAP 实测高频：`expo`（49 站）、`power4`（46）、`power2.out`（35）。这些是观测区间，
不是推荐默认。用 motion casting 从三种 easing/重量里选一版；CSS token 见 `28`。
`cubic-bezier(.16,1,.3,1)` 只是候选之一，不要把高频曲线升格为全站默认值。

## 9. 只动 transform 和 opacity（默认）

- 布局属性（`width/height/top/left/margin/padding`）每帧触发布局，移动端直接掉帧。
- `filter: blur()` 和 `box-shadow` 触发绘制，长循环里很贵；要动就动 `opacity` 或预先分层的 `transform`。
- 例外：`clip-path`（圆形揭示）、`grid-template-rows`（手风琴）可以动，但必须知道代价，
  并且只在小面积/短时长使用。手风琴用 `grid-template-rows: 0fr → 1fr`，不要量 `scrollHeight`。
- 无限动画要 `will-change` 谨慎：只在动画期间加，结束移除；常驻 `will-change` 会吃显存。

## 10. 可访问性

- `prefers-reduced-motion: reduce` 必须到**终态**，不是「动画没了但元素还在 opacity:0」。
  做法：JS 里 `matchMedia` 直接跳过 rAF/IO reveal，把目标状态写死；CSS 里
  `animation: none; transition: none; opacity: 1; transform: none;`。
- 非用户触发的动效要能停：轮播/视频/背景 shader 提供暂停，或至少不自动播放声音。
- 闪烁 ≤3 次/秒；大面积高对比闪烁会诱发光敏性癫痫。
- 滚动不能被劫持：`scroll-jacking` 只在明确叙事页、并提供键盘/跳转出口时使用。
- 键盘：Tab 可达、焦点可见、Esc 可关、Space/Enter 可触发。

## 11. 证据等级与假信号

每条动效声明标一个等级：

- `observed`：运行时采样到（rAF 帧、`document.getAnimations()`、F12 computed style、8 向拖拽）。
- `inferred`：从 CSS/JS 源码推断，但没有运行时读数。
- `authored`：本包自写，不是原站观察。

**六个最常见的假信号**：

1. 静态 dHash 通过 ≠ 动效通过。截图只能证明某一帧。
2. 302 复刻「有交互」≠「有动效」：共享 runtime 0 rAF / 0 shader，canvas 是快照水合。
3. 组件 `advanced: true` ≠ 真实动效：字段可能是注入的合成值。
4. 动画条数 ≠ 机制数：178 条可能是同一条 ripple 的 170 个实例。
5. headless rAF 83ms / 1016ms ≠ 真机性能：无 GPU、无 vsync。
6. 「用了 GSAP/Lenis」≠ 动效好：库只是运输工具，参数和编排才是设计。

## 12. 14 族速查

| 族 | 一句话 | canonical 代码 | 典型时长 |
|---|---|---|---|
| F1 滚动叙事 | 滚动位置决定段落/位移/透明度 | kit 01、component 10 | 300–900ms，pin 320vh |
| F2 横向轨道 | 滚轮/拖拽映射轨道位移 + 惯性 | kit 02、component 04 | lerp .15，decay .95 |
| F3 全屏 shader | 全屏片元做背景/液体/textmode | kit 03、component 05 | 700ms 入场，16s 环境 |
| F4 WebGL 3D | 物体/相机/场景 | kit 10（merged 14 已移出） | 6–24s 循环 |
| F5 像素 canvas | 低分辨率 + 整数放大 + 调色板 | kit 04 | 500–1200ms 逐字 |
| F6 排版动效 | 行/字/字重作为结构 | kit 07、component 12 | 20–50ms stagger |
| F7 光标/磁吸 | dot/ring/磁吸/多层视差 | kit 06、component 09 | 120–300ms |
| F8 音频/波形 | 音频是状态源，不是背景 | kit 09、component 11 | 1–7.2s 循环 |
| F9 3D 倾斜/材质 | 倾斜、卷动、箔材、玻璃 | kit 05、component 02 | 760ms 落位 |
| F10 相机/缩放 | 页面当可移动的地图/画布 | kit 10、component 06 | 900–1800ms |
| F11 传送带/marquee | 环形内容 + 速度/摩擦 | component 04 | BASE 62，42–148s |
| F12 扫描/VHS | 扫描线/噪点/色带/glitch | 24 keyframes | 200ms/1s/8s 三层 |
| F13 视频拼贴 | 多视频作为版面零件 | kit 08 | 镜头时长 2–6s |
| F14 状态机/演示 | 多步骤 UI 的命名状态 | kit 11、component 03/07/08 | 300–9000ms |

**选择规则**：一个页面只选 1 个主族 + 最多 2 个辅族。主族决定结构，辅族只做局部反馈。
不要为了「丰富」混 5 个族。

## 13. 与实现/验收的接口

- 写代码：`22-motion-implementation.md`（每族的 DOM/CSS/JS 骨架、参数、降级）。
- 选案例：`23-motion-cases.md`（30 案，按族，含实测读数与提示词指针）。
- 验收：`24-motion-verification.md`（静态扫描 + 运行时探针 + 必红用例）。
- 资产：`assets/motion/` 索引（kit/component/prompt/keyframes 映射）。
