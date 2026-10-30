# 第一页：最小知识集

读完这一页就能写出第一张合规的构成主义幻灯片。其余 references 按需读。

## 先走结构化路径

8 页以上：`deck.plan.json` → `plan.mjs check` → `scaffold.mjs` → 填槽。坐标、主题、页脚、纹理由骨架给，不要从零手写。

短稿可以直接写 HTML，但每页仍要：

```html
<section class="slide theme-archive"
         data-role="cover" data-layout="L01"
         data-purpose="这页要让观众记住什么"
         data-minutes="1.5"
         data-notes="讲稿/提词">
```

版式与槽位见 `layout-specs.md`；自定义版式写 `data-layout="custom"`。

## 骨架

```html
<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8">
  <link rel="stylesheet" href="../assets/deck.css">
</head>
<body>
  <div class="deck" data-structured>
    <section class="slide theme-archive" data-role="cover" data-layout="L01">
      <div class="grain"></div>
      <!-- 内容 -->
    </section>
  </div>
</body>
</html>
```

`<link>` 不能省：`validate` 靠它定位 deck.css，才查得出类名是否真实存在。

## 坐标与角度

- 画布 1280×720，原点左上角，单位一律 px。
- 安全区 `left/top 56`，内容宽 1168；正文不出安全区，展示字可以出血。
- 定位用 `position:absolute` + `left/top`，不用 flex 做页面级布局。flex/grid 只用于列内分配。
- 页面上任何元素都会被读成形状，所以**不要用包裹 div 做装饰**——包裹层的背景色也会被发成一个矩形。
- **角度符号**：CSS 正角 = 左上到右下（╲）；负角 = 左下到右上（╱）。`transform-origin` 必须是中心。

## 三个必记的类

| 类 | 作用 | 注意 |
|---|---|---|
| `.slide` | 1280×720 画布 | 必须有，且每页一个 `section` |
| 主题类 `theme-*` | 五个颜色令牌 | 一套 deck 只用一套；样张加 `data-showcase` |
| `.grain` / `.halftone` | 纸张颗粒 / 网点 | 必须是 `.slide` 的第一个子元素，否则会盖住文字 |

文字类按阶梯选：`.t-hero`(158) `.t-h1`(96) `.t-h2`(64) `.t-h3`(42) `.t-h4`(28) `.t-lead`(26) `.t-body`(19) `.t-small`(18) `.meta`(15) `.micro`(13)。标签档最多 12 个汉字。

## 三种文本形态

| 形态 | 怎么写 | PPT 里的行为 |
|---|---|---|
| T1 展示字 | `.t-hero/.t-h1/.t-h2` + 绝对定位，一行一个 div | 不折行；要两行写两个 div 各自定位 |
| T2 正文 | 给容器显式 `width`，用 `.t-body/.t-lead/.t-small` | 可换行，改字会重排 |
| T3 标签 | `.meta/.micro/.num/.latin`，短、全大写或编号 | 不换行，只有一行 |

T2 的关键是**给宽度**。不给宽度的正文，转换器只能按当前墨迹宽度出框，用户在 PPT 里加字就会溢出（`WIDTH` 会 warn）。

## 颜色

只用主题令牌，不写 hex：

```html
<div class="rect rect--pop"></div>              <!-- 爆点色块 -->
<div class="t-h1 fg-fg">黑字</div>              <!-- 主墨 -->
<div class="slide--ink"><div class="t-h1 fg-bg">反白</div></div>
```

需要“纸色字”时用 `var(--bg)`，不要写 `#FFFFFF`——后者不在主题里，`INK` 会报 off-palette。`--mute` 只给标签档，不能做副标（`MUTE` 会判）。

## 第一页最常见的五个错

1. **用了没定义的类**：浏览器静默 fallback，预览就塌了。`validate` 会报 `CLASS`。
2. **展示字没 nowrap**：`.t-h2` 已内置 nowrap；自己覆盖 `white-space` 会报 `WRAP`。
3. **正文没给宽度**：输出 `wrap=false`，PPT 里改字不重排。`WIDTH` 会提醒。
4. **一页超过一个主张**：`DENSITY` 会 warn，读者也记不住。
5. **没写 data-role / data-layout / data-purpose**：结构化检查会报 `STRUCTURE`，大纲也读不出这页的任务。

## 工具脚本（不读文档也能跑）

| 想做什么 | 命令 |
|---|---|
| 接手一份没有 plan 的 deck | `node scripts/plan-from-deck.mjs deck.html -o plan.json`（读不出的字段会列成缺口，不编造） |
| 插页 / 删页 / 换页序 | `node scripts/reorder.mjs plan.json --move 5:2`（改完必须重跑 scaffold） |
| 把照片做成网点图 | `node scripts/prepare-image.mjs src.jpg -o out.png --width 600 --dot 10 --radius 3` |
| 看全部主题的对照图 | `node scripts/style-preview.mjs deck.html --out style-comparison`（默认覆盖 themes.json 里全部主题） |
| 反查某个规则码的修法 | `references/troubleshooting.md` |

## 下一步

- 选版式、查槽位 → `layout-specs.md`
- 判断构图 → `composition.md`
- 用组件 → `components.md`
- 预览对但 PPT 里不对 → `html-contract.md`
