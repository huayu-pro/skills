---
name: constructivist-ppt
description: 当用户要做构成主义（Constructivist）风格的演示文稿、封面、路演 deck、作品集或海报式幻灯片时使用；触发词包括「构成主义 / 俄式构成主义 / 康定斯基式构成 / constructivist / 苏联海报风 / 红黑斜切 / 巨构海报风 / 大色块+粗黑字+斜切构图」。适用于 8–20 页、一页一个主张、需要压场的场合。不适用于大段表格、密集数据报表、逐条念的培训课件、多人协作的正式公文——这些场景直接说明不适合，并给替代方案。
metadata:
  version: "3.3.1"
  updated: "2026-10-25"
  agent_created: true
---

# 构成主义 PPT

一套**先规划、再排版、再编译**的流程：`deck.plan.json` → 1280×720 定尺 HTML → 原生可编辑 PPTX。

不是截图贴图。文字是文本框，色块是形状，斜带能用旋转手柄转，多边楔形是可拖锚点的自定义形状。

---

## 什么时候用 / 不用

| 适合 | 不适合 |
|---|---|
| 发布会、品牌/文化类分享 | 大段表格、密集数据报表 |
| 作品集、观点型路演 | 需要逐条念的培训课件 |
| 课程封面、章节幕 | 多人协作编辑的正式公文 |
| 8–20 页、一页一个主张、需要“压场” | 40 页以上的年报、尽调材料 |

遇到“不适合”的场景，**先说不适合，再给替代方案**（常规版式 + 数据页），不要硬套。

和邻近风格的分界：瑞士国际主义靠网格与留白、情绪克制；包豪斯靠几何与工艺感、色彩更轻；De Stijl 只有水平垂直。构成主义的关键是**斜线 + 面积差 + 两墨一纸**，三者缺一就不是这套语言。

---

## 交付物与完成判据

交付三件：`.pptx`、逐页预览图、一句说明“哪些可编辑、哪些是图”。

**没跑完 gate 不算交付。** 8 页以上的 deck 先有 `plan.json`，再谈下面的门禁：

| Gate | 命令 | 通过判据 |
|---|---|---|
| 规划 | `node scripts/plan.mjs check plan.json --strict` | 0 error；8 页以上必须 |
| 版式 | `node scripts/validate.mjs deck.html --strict` | 0 error；warn 逐条判断过 |
| 内容 | `node scripts/audit-text.mjs deck.html --strict` | 0 error（占位文案必须清零） |
| 观感 | `node scripts/render.mjs deck.html --out preview --sheet` | 联系表已生成并**实际看过** |
| 编译 | `node scripts/build-deck.mjs deck.html -o deck.pptx` | 退出码 0，无 `FORBID` 报错 |
| 反渲 | `node scripts/verify-pptx.mjs deck.pptx --out pptx-render --vs preview` | 每页差异在阈值内；每页讲者备注非空（notes 链路断裂会红，样张场景用 `--no-notes` 豁免） |
| 真渲染 | `node scripts/verify-render.mjs deck.pptx --out render --vs preview` | 有 LibreOffice 时跑；每页 ≤12%，无则标“未验证” |
| 总门禁 | `node scripts/gate.mjs deck.html --plan plan.json` | `gate.json` 全绿；一条命令串起以上步骤 |

最后一条不是可选项：`verify-pptx` 只能证明“我按 spec 画出来了”，`verify-render` 才能证明“PowerPoint 打得开”。

---

## 工作流

### 1 · 判断适配

先对照上面两张表。不适合就停，说明原因并给替代方案——这一步的产出是一句话，不是一个 deck。

### 2 · 澄清四件事

只问真正影响版式的：

| 问什么 | 为什么 |
|---|---|
| 受众与场景（内部评审 / 对外发布 / 课程） | 决定文字密度与语气 |
| 时长或页数 | 15 分钟 ≈ 10–12 页，30 分钟 ≈ 18–22 页 |
| 有没有原始素材（文档、旧 PPT、数据） | 有素材就以素材为准，不编数字 |
| 子风格：A 档案红黑 / B 重墨印刷（靛蓝 / 青墨）/ C 彩色巨构 | 见 `references/palettes.md`；要给用户看对照图就跑 `node scripts/style-preview.mjs <deck.html> --out examples/style-comparison`（生成物，不在包内） |

用户说不清就给推荐：文化/品牌/观点 → A；科技/产品/数据 → B；创意/活动/宣言 → C。

### 3 · 写 `deck.plan.json` 并过检查

8 页以上必须先写 plan；短稿可以直接写 HTML，但每页仍要有 `data-role` + `data-layout`。

```json
{
  "version": 1, "title": "…", "audience": "…", "durationMin": 15,
  "theme": "theme-archive", "substyle": "A", "axisDeg": -11,
  "slides": [{
    "id": "s01", "role": "cover", "layout": "L01",
    "claim": "一句主张", "minutes": 1.5,
    "slots": { "title1": "构成主义", "lead": "…" },
    "notes": { "purpose": "…", "talk": ["…"], "transition": "…", "cue": "…" }
  }]
}
```

- `role` 决定叙事位置，`layout` 决定骨架；角色 → 候选版式见 `references/layout-specs.md`。
- `slots` 是普通槽位；重复内容放 `groups`（`items` / `leftPoints` / `rows` 等）。
- `notes.purpose` 必填；`talk` 是讲述要点；`cue` 是备注栏里的提词。
- 检查：`node scripts/plan.mjs check plan.json --strict`。它会抓页数、时长、角色顺序、版式轮换、槽位预算、重复 claim、plan↔deck 漂移。

### 4 · scaffold，然后填内容

```bash
node scripts/scaffold.mjs plan.json -o deck.html --force
```

scaffold 从 `assets/layouts/L*.html` 生成带精确坐标的页面，写 `data-plan-id / data-role / data-layout / data-purpose / data-talk / data-minutes`，并按主题加纹理与页脚。**先填槽，不要先改坐标。** 要改结构就改骨架文件，再重新生成；只改一页会让整份漂移。

手写页面也可以，但必须声明 `data-role` 和 `data-layout`（自定义版式写 `custom`），并尽量给 `data-slot`，否则 `STRUCTURE / SLOTS` 会报。

### 5 · 逐页写 / 改，逐页看

每写完一页跑一次，不要攒：

```bash
node scripts/validate.mjs deck.html --slide 3
node scripts/render.mjs deck.html --out preview
```

`CLASS` 错误在写第一页时就已经产生，攒到最后只会一次冒出几十条。`render` 不报错——浏览器对未定义类是静默 fallback，所以看图不能替代 `validate`。

第一次写这套 HTML，先读 `references/start-here.md`；改任何“预览对、PPT 里不对”的东西之前，先读 `references/html-contract.md`。

### 6 · 体检与修

```bash
node scripts/validate.mjs deck.html --strict
node scripts/audit-text.mjs deck.html --strict
```

- `error` 必须修，不能靠豁免属性糊过去。
- `warn` 逐条判断；判完在回复里说清哪些是刻意的。
- 豁免属性共六个：`data-axis-ok` / `data-palette-ok` / `data-safe-ok` 挂在 `section` 上；`data-balance-ok` / `data-overlap-ok` 可挂祖先；`data-showcase` 挂 `.deck`，只给样张。另有一个内部属性 `data-structure-ok`，只给画廊/样张，正常 deck 不要用。
- 旧 deck 迁移用 `--compat v2`：新检查降为 warn，`DECK` 与 `FORBID` 仍是 error。降级的项会单独计数并在输出里标 `(compat 降级)`——**它们是真实缺陷，不是通过项**，交付说明里要逐条交代。

规则码的完整清单与修法见 `references/troubleshooting.md`。

### 7 · gate 与交付

```bash
node scripts/gate.mjs deck.html --plan plan.json
```

它会依次跑 doctor、plan check、plan↔deck、validate、audit-text、render `--sheet`、build、verify-pptx、verify-render（有 LO），并写 `gate.json`。任一步失败就停。

交付时三句话说完：哪些是原生对象、哪些是图片、字体怎么替换。不要写设计说明。

---

## 结构化契约

| 属性 | 作用 |
|---|---|
| `data-role` | 叙事角色：cover / context / thesis / method / evidence / data / comparison / sequence / case / quote / section / closing |
| `data-layout` | 版式 id（L01–L25，无 L08），自定义写 `custom` |
| `data-plan-id` | 与 plan 的 `slides[].id` 对齐；`plan.mjs check --deck` 用它抓漂移 |
| `data-purpose` | 这页要让观众记住什么 |
| `data-talk` | 讲述要点，用 `|` 分隔 |
| `data-transition` | 为什么翻到下一页 |
| `data-minutes` | 本页建议时长 |
| `data-notes` | 备注栏里的提词/讲稿 |
| `data-slot="name"` | 可填槽位；scaffold 按 `{{slot:name}}` 填充 |
| `data-slot-block="name"` | 可选块；内容为空时 scaffold 整块删除 |

版式目录、槽位表、缩略图：`references/layout-specs.md`。几何以 `assets/layouts/L*.html` 为准。

---

## 十二条硬规则

规范不可执行就只是建议。下表由 `scripts/gen-rules-doc.mjs` 从 `assets/rules.json` 生成，每条都挂在 `validate.mjs` 的规则码上：

<!-- RULES:BEGIN 由 scripts/gen-rules-doc.mjs 生成，勿手改 -->
| # | 规则 | 判据 | 码 | 豁免 |
|---|---|---|---|---|
| 1 | **一页只有一条主斜线** | 主斜线面积 ≥0.03 画布、长边 ≥0.3 画布宽；其余元素要么与它平行，要么严格水平/垂直 | `AXIS` | `data-axis-ok` |
| 2 | **面积必须不均** | 首栏 ≥1.7× 第二栏；理想 2×；骨架配方 1.9fr | `BALANCE` | `data-balance-ok` |
| 3 | **一页最多四色** | 纸 + 主墨 + 爆点 + 次墨；全部取自当前主题 token | `INK` `THEME` | `data-palette-ok` `data-showcase` |
| 4 | **线有重量** | ≥2px；1px 发丝线不属于这套语言 | `WEIGHT` | — |
| 5 | **展示字一行一个元素** | .t-hero/.t-h1/.t-h2 必须 nowrap；要两行写两个 div 各自定位 | `WRAP` | — |
| 6 | **正文面积受限** | ≤15% 画布 | `TEXTAREA` | — |
| 7 | **只用 deck.css 已有的类** | 未定义类会让浏览器静默 fallback，版式莫名其妙地塌 | `CLASS` | — |
| 8 | **对比度** | 正文 ≥4.5；≥28px 或 ≥700 字重时 ≥3 | `CONTRAST` | — |
| 9 | **字号地板** | 正文 18px / 标签 15px / 微字 13px | `FONT` | — |
| 10 | **一页一个主张** | ≤240 字（汉字 + 拉丁词） | `DENSITY` | — |
| 11 | **页脚形态轮换** | 不许连续三页同一种形态 | `FOOTER` | — |
| 12 | **交付前跑完验证链** | validate 零 error / audit-text 零占位 / 看过联系表 / build 成功 / verify-pptx 无异常 | `GATE` | — |
<!-- RULES:END -->

`error` 必须修；`warn` 逐条判断。页脚轮换与交付 gate 都是自动检查，不靠人工记。

---

## 支持边界

**能吃什么**：纯色块、旋转矩形/椭圆/多边形、边框、图片（本地路径或 data URI）、文本段落、`<br>` 断行、竖排。够了——这套语言本来就只有这些。

**做不到什么**（每一条都会被 `validate` 拦下；注意报的是 `FORBID` 还是 `TRANSFORM`——两者修法不同，前者删写法，后者换成单层 `rotate`）：

| 属性 | 报什么码 | 为什么不行 |
|---|---|---|
| 渐变 | `FORBID` | OOXML 无渐变填充映射 |
| `box-shadow` / `text-shadow` | `FORBID` | 阴影无法表达，会被拍平 |
| `filter` | `FORBID` | 同上 |
| `mix-blend-mode` | `FORBID` | 叠色结果与预览不同 |
| `z-index` | `FORBID` | 只认 DOM 顺序，层级会乱 |
| `position:fixed` | `FORBID` | 坐标链断裂，元素会串页 |
| 伪元素画图形 | `FORBID` | 没有 DOM 盒子，量不到也转不出 |
| 嵌套 `transform` | `TRANSFORM` | PPT 没有 group，父子旋转叠加必然错位 |
| `translate` / `scale` / `skew` | `TRANSFORM` | 布局盒与 PPT 坐标不一致；只支持单层 `rotate` |
| `transform-origin` 非中心 | `TRANSFORM` | 绕非中心旋转，PPT 里无法等价表达 |
| 非 `polygon()` 的 `clip-path` | `FORBID` | 只有 polygon 能转成自定义形状 |
| 非 50% 正圆的 `border-radius` | `FORBID` | 其他圆角会被丢弃 |
| 容器级 `overflow` 裁切 | `FORBID` | 只有 `.slide` 允许裁切 |
| 内联 `<svg>` / `<canvas>` | `FORBID` | 没有形状也没有文字，转换后消失 |
| 远程图片 | `FORBID` | PPTX 不会自动下载；先下载到本地 |

**旋转只能一层，`transform-origin` 必须是中心。** 父元素带旋转、子元素再旋转，PPT 里没有 group，必然错位。

---

## 关键参数

| 参数 | 取值 | 用途 |
|---|---|---|
| `--mode` | `native` / `hybrid` / `image` | 原生 / 部分栅格化 / 全截图 |
| `--raster-slides` | `3,7` | hybrid 的栅格化页号 |
| `--font-profile` | `office` / `source` / `asis` | 字体回退策略 |
| `--no-anim` | flag | 关闭动画，出静态稿 |
| `--anim-mode` | `chain` / `click` | 一次点击整组揭示 / 每元素各点一次 |
| `--strict` | flag | warn 也算失败，CI 用 |
| `--no-strict` | `gate` | 显式放宽总门禁（gate 默认已 strict） |
| `--compat v2` | `validate` / `gate` | 新检查降级并单独计数；`DECK`/`FORBID` 仍 error |
| `--check` | `build-deck` / `scaffold` | 只检查不写盘 |
| `--compare-width` | `verify-render` | 布局级比对宽度，默认 1280；gate 用 640 |
| `--no-notes` | `verify-pptx` | 跳过讲者备注检查，只给样张/特殊 deck 用 |
| `--no-compare` | `verify-pptx` | 明确表示「只出图不比图」；不传 `--vs` 又不用它 = 失败 |
| `--write-baseline` | `verify-pptx` | 记录每页正常差异；**只在全绿时写入**，坏运行不会被固化成参照 |
| `--allow-forbid` | `validate` / `build-deck` / `gate` | **降级后门**：把 `FORBID` 降为 warn。只在确认某写法必须保留时用，并在交付说明里写理由 |
| `data-fidelity="raster"` | 元素属性 | 该元素连底色截图，只用于纯色区的大字 |
| `data-showcase` | `.deck` 属性 | 样张豁免“一份 deck 一套主题” |

其余豁免属性（`data-axis-ok` / `data-palette-ok` / `data-safe-ok` / `data-balance-ok` / `data-overlap-ok`）的挂载位置与判定见上一节。

动画默认关闭：不写 `data-anim` 就没有动画，输出与静态稿完全一致。实现细节见 `references/animation.md`。

---

## 反合理化

| 借口 | 现实 |
|---|---|
| “加条粗斜线就有构成主义味” | 斜线是论点；说不出它在分隔/推进什么就是噪音 |
| “四栏并列更整齐” | 等宽 = 等价；首栏必须明显大于其余 |
| “内容多放一点信息量大” | 一页一个主张；超字数就拆页 |
| “半透明叠一下更高级” | PPTX 会拍平；预混实色或烘焙进图片 |
| “先出图再补结构” | 结构错在页面层修不好；先 plan 再 scaffold |
| “这版挺干净工整的” | 无立场的整齐就是 AI 味；面积差、尺度差、方向差做足了吗（见 `references/visual-system.md` 对照表） |

更完整的构图判据见 `references/composition.md`。

---

## 参考索引（按什么时候读）

| 时机 | 读哪份 |
|---|---|
| 第一次写这套 HTML | `references/start-here.md` |
| 选角色、版式、查槽位坐标 | `references/layout-specs.md` |
| 判断构图是否成立 | `references/composition.md` |
| 用组件（日轮/斜带/编号/页脚/竖标） | `references/components.md` |
| **改“预览对、PPT 里不对”的东西** | `references/html-contract.md` |
| 选配色、看子风格 | `references/palettes.md` |
| 排字号、字距、行距 | `references/typography.md` |
| 配图、生图、网点化 | `references/image-prompts.md` |
| 交付前逐项过一遍 | `references/checklist.md` |
| 出问题、查规则码 | `references/troubleshooting.md` |
| 改转换器或动画 | `references/animation.md` |
| 想知道某条规则为什么这么定、面积与尺度怎么算 | `references/layouts.md` |
| 判断“这版是不是 AI 味”、看视觉系统对照表 | `references/visual-system.md` |
| 装 LibreOffice 跑真渲染比对 | `docs/libreoffice-setup.md` |
| 这套 skill 从哪些方案借了什么 | `docs/prior-art.md` |

工具脚本（反提 plan、增删页、网点化、主题对照图）的用法见 `references/start-here.md` 末节。

---

## 常见故障

| 症状 | 原因 | 改法 |
|---|---|---|
| 文字整体偏右下 | 绕过 `lib/emit.mjs` 自己拼 margin | 用官方脚本，别手改 emit |
| 斜带在 PPT 里变大变歪 | 用了 `translate/scale`，或拿 `getBoundingClientRect` 当盒子 | 只用单层 rotate；转换器只读布局盒 |
| 字体全变宋体 | 目标机器没有输出字体 | 换 `--font-profile office`，或关键标题标 `raster` |

其余症状（含中文竖排、PPT 提示“需要修复”、页面显空）与每个规则码的判定与修法见 `references/troubleshooting.md`。

---

## 与通用 PPT 规范冲突时

网上多数 PPT 规范会写“不要用色条”“不要用满幅色块”“不要用密集编号”“避免米色背景”——**这些是反 AI 味的规则，在构成主义里恰恰相反**：色带就是结构，满幅色块就是论点，编号网格就是信息组织，米白纸底是这套语言的物理来源。

本 skill 显式豁免这些规则。但它们背后的原则仍然成立：**每加一个元素，都要能说出它在分隔什么、强调什么、把视线推向哪里。** 说不出来就删掉。
