# constructivist-ppt

用 HTML 排版，编译成**原生可编辑**的构成主义风格 PPTX。

```
deck.plan.json  →  scaffold  →  deck.html  →  Chromium 读几何  →  PPTX
```

不是截图贴图。文字是文本框，色块是形状，斜带能用旋转手柄转，楔形是能拖锚点的自定义形状，正文双击就能改字。

---

## 安装

```bash
cp -r constructivist-ppt ~/.workbuddy/skills/
cd ~/.workbuddy/skills/constructivist-ppt/scripts
npm install
npx playwright install chromium
```

依赖：

| 组件 | 用途 | 怎么来 |
|---|---|---|
| `pptxgenjs` | 生成 pptx | `npm install` |
| `playwright-core` | 驱动 Chromium | `npm install` |
| `jszip` | 读 pptx XML | `npm install` |
| Chromium | 渲染与量尺寸 | `npx playwright install chromium` |
| ImageMagick | 联系表 / 像素对比 | 系统包（`montage` / `convert`） |
| poppler-utils | PDF → PNG | 系统包（`pdftoppm`） |
| unzip | 读 pptx 内容 | 系统包 |
| LibreOffice | `verify-render` 真渲染 | 可选；没有就标 skipped |

环境体检：

```bash
node scripts/doctor.mjs
```

找不到 Chromium 时用环境变量指定：

```bash
export CST_CHROME=/path/to/chrome
```

---

## 快速开始

```bash
# 1. 写 plan，过结构检查
node scripts/plan.mjs check examples/plan.json --strict

# 2. 从 plan 生成带精确坐标的 HTML
node scripts/scaffold.mjs examples/plan.json -o my-deck.html --force

# 3. 填内容后，一条命令跑完验证链
node scripts/gate.mjs my-deck.html --plan examples/plan.json
```

想先看效果：

```bash
node scripts/render.mjs examples/structured.html --out /tmp/prev --sheet
```

---

## 命令

| 命令 | 作用 |
|---|---|
| `plan.mjs check plan.json` | 检查页数、时长、角色顺序、版式轮换、槽位预算、claim 重复；`--deck` 比对 plan↔HTML |
| `scaffold.mjs plan.json -o deck.html` | 从 `assets/layouts/L*.html` 确定性填充；`--check` 只检查；`--gallery` 生成版式画廊 |
| `validate.mjs deck.html` | 版式、构图、结构、槽位体检；`--strict` / `--compat v2` / `--json` |
| `audit-text.mjs deck.html` | 占位、重复、空页、字数、中文排版、purpose/notes |
| `outline.mjs deck.html` | 页级清单：role / layout / 标题 / 字数 / 时长 |
| `render.mjs deck.html --out preview --sheet` | 逐页 PNG + 联系表 |
| `build-deck.mjs deck.html -o deck.pptx` | 编译；`--check` 只提取并检查 FORBID，不写盘 |
| `verify-pptx.mjs deck.pptx --out dir --vs preview` | 读 XML 重画，与预览逐像素比 |
| `verify-render.mjs deck.pptx --out dir --vs preview` | LibreOffice 真渲染；`--compare-width` 做布局级降采样比对 |
| `gate.mjs deck.html --plan plan.json` | 串起 doctor → plan → validate → audit → render → build → verify，写 `gate.json` |
| `doctor.mjs` | 检查 Node、依赖、Chromium、ImageMagick、poppler、字体、LibreOffice |
| `style-preview.mjs` | 同一批页面套不同主题，出对照图 |
| `gen-themes.mjs` | 从 `assets/themes.json` 生成 CSS 主题块与 `palettes.md` 表；`--check` 比对 |
| `gen-textures.mjs` | 确定性生成 `assets/textures/` 纹理与 `assets/img/industry.svg` 示例图（ImageMagick） |
| `gen-layout-docs.mjs` | 从 `assets/layouts.json` + 骨架生成 `references/layout-specs.md`；`--check` 比对 |
| `pack-html.mjs` | 内联 CSS/图片，便于单文件归档 |
| `rerender.mjs` | 从 spec 重画 PNG，调试提取用 |
| `font-map.mjs` | 改写 pptx 里的字体名 |
| `plan-from-deck.mjs deck.html -o plan.json` | 从既有 deck 反提 plan（接手没有 plan 的 deck；读不出的字段列成缺口） |
| `reorder.mjs plan.json --move 5:2` | 插页 / 删页 / 复制页；改完重跑 scaffold |
| `prepare-image.mjs src.jpg -o out.png` | 图片一键网点化，封装 image-prompts.md 的四步工序 |
| `evals/run.mjs --pipeline` | 确定性回归；`--agent` 对真实产物下判据；含 `08-pack-security` |
| `selfcheck.mjs` | 文档 ↔ 代码 ↔ 资产一致性自检 |

---

## 工作流

1. **判断适配**：适合发布会、品牌/文化分享、观点型路演、课程封面；不适合密集表格、培训课件、正式公文。
2. **澄清**：受众、时长/页数、素材、子风格（A 档案红黑 / B 靛蓝重墨 / C 彩色巨构）。
3. **写 plan**：`role` 定叙事位置，`layout` 选骨架，`claim` 一句主张，`notes` 写讲稿。
4. **scaffold**：生成带精确坐标的 HTML；填槽位，不先改坐标。
5. **逐页看**：`validate --slide N` + `render`。
6. **全量体检**：`validate --strict` + `audit-text --strict` + 联系表。
7. **gate**：`gate.mjs` 一条命令跑完，`gate.json` 全绿再交付。

8 页以上必须先有 plan；短稿可以直接写 HTML，但每页仍要 `data-role` + `data-layout`。

---

## 主题与版式

- 主题：`assets/themes.json` 是单一真相源，生成 `assets/deck.css` 的主题块与 `references/palettes.md` 的表。子风格 A/B/C 的差异见 `references/palettes.md`，对照图由 `scripts/style-preview.mjs` 现生成（生成物不在包内）：`node scripts/style-preview.mjs examples/demo-31.html --out examples/style-comparison`，默认覆盖 themes.json 全部主题。
- 纹理：`.grain` / `.halftone` 引用 `assets/textures/*.svg`，示例图是 `assets/img/industry.svg`——**都是纯文本 SVG**，发布平台不接受二进制。PPTX 装配时由 `build-deck.mjs` 用浏览器栅格化成临时 PNG。
- 版式：`assets/layouts.json` 管角色与槽位契约，`assets/layouts/L*.html` 管几何；两者由 `selfcheck` 做一一对应。槽位表与缩略图见 `references/layout-specs.md`。
- 画廊：`examples/layout-gallery/` 每个版式一页，用于看骨架本身。

---

## 支持边界

转换器只认识一个受约束的 HTML 子集：纯色块、旋转矩形/椭圆/多边形、边框、图片（本地或 data URI）、文本段落、`<br>`、竖排。

**不支持**：渐变、阴影、滤镜、混合模式、`z-index`、`position:fixed`、伪元素画图形、嵌套旋转、`translate/scale/skew`、非 polygon 的 `clip-path`、非 50% 正圆的圆角、容器级裁切、内联 SVG/Canvas、远程图片。每一条都会报 `FORBID`，build 在写盘前停止。

旋转只能一层，`transform-origin` 必须是中心。

## 安全边界

`pack-html.mjs` 只接受 `.html` 输入，只内联图片/字体/样式扩展名；隐藏路径段、非白名单扩展名、围栏外路径一律拒绝。它不联网、不执行 shell、不读取凭据。详见 [SECURITY.md](SECURITY.md)。

---

## 目录

```
assets/
  deck.css              画布、字号、组件、主题块
  themes.json           主题单一真相源
  layouts.json          角色 / 槽位契约
  layouts/L*.html       精确坐标骨架
  rules.json            阈值 / 规则码 / forbid / compat
  template.html         手写模板（三页示例）
references/             按需读的规范（start-here / layout-specs / composition / …）
scripts/                plan / scaffold / validate / gate / build / verify / doctor / 生成器
evals/                  cases、baselines、TRACE 记分卡
examples/
  plan.json             完整 plan 示例
  structured.html       scaffold 产物
  layout-gallery/       版式画廊
  style-comparison/     子风格对照
docs/                   开发史与环境搭建
```

---

## 评测

```bash
node evals/run.mjs --pipeline          # 确定性回归
node evals/run.mjs --agent <case> --dir <产物目录>
node evals/run.mjs --score             # TRACE 四态汇总
```

Case 覆盖转换器契约、结构化生成、边界、负面触发、失败恢复、交付。`INCOMPLETE` 不等于通过；人工视觉评分卡见 `evals/TRACE.md`。

---

## 文档

- 第一次写：`references/start-here.md`
- 选版式/查槽位：`references/layout-specs.md`
- 构图判据：`references/composition.md`
- 预览对但 PPT 不对：`references/html-contract.md`
- 交付检查：`references/checklist.md`
- 出问题：`references/troubleshooting.md`
- 开发史：`docs/prior-art.md`
