# HTML 契约

转换器不是浏览器。它只认识下面的 CSS 子集，其余的一律降级或丢弃。
**改版式前先读这一页**，能省掉 80% 的返工。

---

## 一、坐标系统

| 项 | 值 |
|---|---|
| 画布 | 1280 × 720 px |
| 输出 | 13.333 × 7.5 in（LAYOUT_WIDE） |
| 换算 | 96 px = 1 in；1 px = 0.75 pt |
| 原点 | `.slide` 左上角 |
| 安全区 | `left/top: 56`，内容宽 1168 |

所有位置用 `position:absolute` + `left/top/width/height`。允许负值（出血），PowerPoint 放映时按页裁切。

---

## 二、映射表

| 你的写法 | 转换结果 | 备注 |
|---|---|---|
| `background-color` | 实色填充 | 支持 `#rgb` / `#rrggbb` / `rgb()` / `rgba()`（alpha<0.02 视作透明） |
| `border-radius: 50%` + 宽高相等 | 椭圆形状 | 宽高不等会被判成矩形 |
| `border-radius: 其他值` | **FORBID** | 只有 50% 正圆能转换；其他圆角用直角或 polygon |
| `clip-path: polygon(...)` | 自定义多边形（可拖锚点） | 坐标支持 `%` 与 `px`，相对元素盒 |
| `clip-path: 其他函数` | **FORBID** | `path()` / 非对称 `ellipse()` 不支持；只用 polygon |
| `transform: rotate(θ)` | 形状旋转 | 只允许单层，原点必须居中 |
| `transform: scale/skew/translate/matrix` | **FORBID** | 只支持单层 rotate；位移用 left/top，缩放用真实尺寸 |
| `border: Npx solid`（矩形/多边形） | 独立的细长矩形 | 比用描边更准，因为 PPT 描边居中在路径上 |
| `border: Npx solid`（圆 `.sun--outline`） | 椭圆描边 | 圆只走描边一条路，不会另发四条边（v2 修复） |
| `box-shadow` / `filter` / 渐变 / `mix-blend-mode` / `z-index` / `position:fixed` / 伪元素 / 内联 svg | **丢弃并报警** | `validate` 全部报 `FORBID`，见第七节 |
| `linear-gradient` / `radial-gradient` | **丢弃并报警** | 需要渐变就把那一块栅格化成 PNG |
| `<img>` + `object-fit: cover` | 图片，居中裁切 | `contain` 也支持；**永远不要拉伸** |
| `background-image: url(...)` | 图片层，`fill` 铺满 | 本地路径或 data URI；远程图 FORBID。只用于 `.grain` / `.halftone` 这类整幅叠层 |
| `writing-mode: vertical-rl` | 竖排文本框 | 元素必须是独立的绝对定位块 |
| `text-transform: uppercase` | 文本在提取时已转大写 | 写入 PPT 的是转换后的字符串 |
| `letter-spacing: 2px` | 字符间距 1.5pt | 会强制关掉 kerning |
| `opacity: 0` | 视作隐藏 | 文本透明度会 error，形状会 warn；PPTX 会拍平 |
| `display: none` / `visibility: hidden` | 跳过 | — |
| `z-index` | **丢弃** | 只认 DOM 顺序 |
| `overflow: hidden` | 只允许在 `.slide` 上用 | 内部裁切无法表达，见第四节 |

---

## 三、文本：两种模式

### T1 展示字（单行）

```html
<div class="t-h1" style="position:absolute; left:52px; top:196px;">赶出画室</div>
```

- `white-space: nowrap`。`.t-hero/.t-h1/.t-h2` 已内置；自己覆盖它会被 `WRAP` 判 error。
- **一行一个元素**。要两行就写两个 div，各自定位。
- 输出：一个文本框，`wrap="none"`（PowerPoint 物理上不会重排），行距 = 字体自然行高。

**为什么不能折行**：CSS 的 `line-height` 与 PowerPoint 的"固定行距"对首行基线的锚定方式不完全一致。单行时两者重合，多行且行距小于字高时会漂十来个像素。在 96px 的标题上，那就是肉眼可见的错位。

### T2 正文（折行）

```html
<div class="t-body" style="position:absolute; left:56px; top:362px; width:540px;">……</div>
```

- 必须给 `width`，让浏览器先折好行。
- 输出：一个文本框，`wrap="true"`，宽度 = **元素的排版宽**（不是文字的 ink 宽）。
- 用户改字后 PowerPoint 会自己重排——这是唯一"改字不散架"的形态。
- `wrap` 由 `white-space` 决定，与"当前是否已经折了行"无关（v2 修复：以前按是否折行判断，导致单行正文输出 `wrap=false`）。

### T3 竖排

```html
<div class="vlabel" style="left:1222px; top:120px; height:240px; color:var(--bg);">SERIAL EXPERIMENTS</div>
```

输出 `vert="eaVert"`。同理，一框一段。

### 行内混排

```html
<div class="t-h2">构成主义的<em class="fg-pop" style="font-style:normal;">四条法则</em></div>
```

`<span>/<em>/<b>/<i>` 会成为同一段里的多个 run，样式逐 run 保留。
**但 flex / grid 的子项不算行内**——它们会被各自 blockify，成为独立文本框。所以在 flex 行里写 `<span>01</span><span>FORM</span>` 是对的（两个框），在一个普通 div 里写才是合并的（一个框两个 run）。

---

## 四、表达不了的三件事

| 想要 | 现实 | 替代做法 |
|---|---|---|
| 标题被色块"咬掉一角" | PPT 没有容器裁切 | 只让元素**超出画布边缘**，放映时天然被裁；或在色块上盖一块与背景同色的矩形 |
| 半透明叠加 | 形状透明度不可靠 | 预先把颜色调成实色的混合结果 |
| 多层模糊/发光 | 无 filter | 用网点 PNG 叠层模拟 |

---

## 五、会静默出错的行为

这几条不会报错，只会让成品悄悄变丑。转换器已在 `lib/emit.mjs` 里做了断言，你自己写脚本时也要注意。

1. **`margin: 0` 会被 falsy 判断吞掉。** pptxgenjs 只认数组，必须传 `margin:[0,0,0,0]`，否则回落成 PowerPoint 默认内边距（左 0.1″、上 0.05″），整页文字集体右下移。
2. **`valign` 默认是 `middle`**，不是 top。必须显式写 `'top'`。
3. **任何 >100 的数值会被当成 EMU 直接透传。** 1280 会变成 1280 EMU ≈ 0.0014 英寸。几何一律先 `px2in()`。
4. **`rotate` 的基准是未旋转的包围盒**，所以位置只能取布局盒（`offsetLeft/Top`），不能取 `getBoundingClientRect()`（那是旋转后的外接框，会把斜带放大）。
5. **`custGeom` 的 `points` 是相对形状左上角的局部英寸**，且 `w/h` 必须等于点集的紧包围盒。
6. **`fontFace` 会同时写 latin / ea / cs 三个字段**，无法中西分设。所以全篇使用同一族字体（Noto Sans CJK 覆盖拉丁）。
7. **8 位 hex 或非法颜色不会报错，会静默变成黑色。**

---

## 六、命名约定

| 前缀/类名 | 用途 |
|---|---|
| `theme-*` | 色板，加在 `.slide` 上，一页一个 |
| `slide--ink` | 墨底反白页，会同时翻转 `--mute`/`--alt` |
| `t-*` | 字号阶梯：`t-hero/t-h1/t-h2/t-h3/t-h4/t-lead/t-body/t-small` |
| `meta` / `micro` / `latin` / `num` | 元数据 / 微字 / 窄体拉丁 / 数字 |
| `fg-*` | 文字颜色：`fg-fg/fg-bg/fg-pop/fg-alt/fg-mute` |
| `rect--*` | 色块变体：`--pop/--alt/--bg`，没有第五个 pale 角色 |
| `sun` / `band` / `wedge` / `rule` | 圆 / 斜带 / 楔形 / 规线 |
| `data-notes` | 演讲者备注（自由文本，会写进 PPT 备注栏） |
| `data-showcase` | 挂在 `.deck` 上；样张文件才用，豁免"一份 deck 一套主题" |
| `data-overlap-ok` / `data-balance-ok` | 告诉体检工具"这里的压字 / 等价并列是故意的"；可挂在祖先或 section |
| `data-axis-ok` / `data-palette-ok` | 豁免正交版面 / 色板展示页；**必须挂在 section 上** |
| `data-fidelity="raster"` | 把这一块连底色截成 PNG 压回原位；只用在落在纯色区的关键标题上 |
| `data-anim="fade\|wipe\|wipe-up\|dissolve\|wedge\|circle-in"` | 入场动画（默认关闭）；`data-anim-step` 控制先后 |
| `data-role` / `data-layout` | 叙事角色 / 版式 id；结构化 deck 必填 |
| `data-plan-id` | 与 plan 的 slide id 对齐，`plan.mjs check --deck` 用它抓漂移 |
| `data-slot="name"` | 版式槽位；scaffold 按 `{{slot:name}}` 填充 |
| `data-slot-block="name"` | 可选块；内容为空时 scaffold 整块删除 |
| `data-purpose` | 这页的任务，写进 PPT 备注的【任务】栏 |
| `data-talk` | 讲述要点，用 `\|` 分隔，写进【讲】栏 |
| `data-transition` | 为什么翻到下一页，写进【转场】栏 |
| `data-minutes` | 本页建议时长，写进【时长】栏 |

---

## 七、禁止项（`validate` 真检测，不是口头警告）

`validate` 会把下面每一条报成 `FORBID`，`build` 遇到会以退出码 1 结束（文件仍会写出，便于排查）。

| id | 写法 | 后果 |
|---|---|---|
| `gradient` | `linear-gradient` / `radial-gradient` | 背景被跳过 |
| `shadow` | `box-shadow` | 阴影消失 |
| `filter` | `filter` | 滤镜消失 |
| `blend` | `mix-blend-mode` | 叠色结果与预览不同 |
| `zindex` | `z-index` | 层级按 DOM 序，与预期不符 |
| `fixed` | `position: fixed` | 元素串页 |
| `pseudo` | `::before` / `::after` 画图形 | 没有 DOM 盒子，直接被忽略 |
| `nested` | 父子元素同时旋转 | 必然错位 |
| `overflow` | 非 `.slide` 上的 `overflow:hidden` 且真的裁切了内容 | 内容溢出到框外 |
| `svg` | 内联 `<svg>` / `<canvas>` | 不产生任何形状 |
| `transform` | `scale` / `skew` / 非中心 `transform-origin` | 只支持单层 rotate；否则错位 |
| `translate` | `translate()` | 布局盒与 PPT 坐标脱节 |
| `clip` | 非 `polygon()` 的 `clip-path` | 只有 polygon 能转 |
| `radius` | 非 50% 正圆 `border-radius` | 其他圆角被丢弃 |
| `remote` | 远程图片（`http(s):`） | PPTX 不会自动下载 |

`extract.mjs` 的 `FORBID` 数组与 `assets/rules.json` 的 `forbid` 一一对应，`selfcheck.mjs` 会校验两边没有脱节。`data:` URI 图片可以直接嵌入；`http(s):` 先下载到本地。
