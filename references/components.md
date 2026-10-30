# 组件库

`assets/deck.css` 里已定义好的东西。**直接抄代码片段，改数值，不要重写类**。

---

## 日轮 `.sun`

正圆。构成主义最重要的单一形状——它可以是太阳、镜头、靶心、一个句号的实体化。

```html
<!-- 实心：压住画面一角，被边缘裁掉 -->
<div class="sun" style="left:786px; top:168px; width:600px; height:600px;"></div>

<!-- 描边：需要穿透感、需要让后面的东西露出来 -->
<div class="sun sun--outline" style="left:900px; top:300px; width:280px; height:280px; border-color:var(--bg);"></div>
```

**规则**：宽高必须相等（差 >2px 就会被判成矩形）。直径至少 240，否则失重。

---

## 斜带 `.band`

一条长矩形 + 旋转。它决定整页的动势。

```html
<div class="band" style="left:-140px; top:486px; width:1560px; height:96px;
     background:var(--fg); transform:rotate(-11deg);"></div>
```

**规则**
- 长度要超过画布宽度 1.2 倍以上，两端必须出血。
- 角度 6°–20°。小于 6° 看起来像画歪了，大于 20° 会切断阅读。
- 一页只有一条。要第二条就让它严格平行（同一个 rotate 值）。
- `transform-origin` 保持默认（中心），不要改。

**斜带 vs 竖板**：`.band` 的长轴是横向，长度要超过画布宽；竖板的长轴是高度，同样要超过画布高。不要把“长度 ≥1.2× 画布宽”套在竖板上——判断标准是它在画面里有没有形成一条明确的边。

---

## 楔形 `.wedge`

用 `clip-path: polygon()` 画三角/斜切块。转换后是可拖锚点的自定义形状。

```html
<!-- 向右推进的箭头 -->
<div class="wedge" style="left:442px; top:170px; width:790px; height:440px;
     clip-path:polygon(0 22%, 100% 50%, 0 78%);"></div>

<!-- 一个斜切的直角三角，用来压角 -->
<div class="wedge" style="left:415px; top:508px; width:156px; height:84px;
     clip-path:polygon(0 100%, 100% 100%, 0 0);"></div>
```

**规则**：点的顺序会影响填充方向；用百分比而不是 px，方便改盒子大小。

---

## 规线 `.rule`

构成主义的线是有**重量**的，不是 hairline。

```html
<div class="rule" style="left:56px; top:452px; width:660px; height:3px;"></div>
<div class="rule rule--pop" style="left:56px; top:332px; width:96px;"></div>   <!-- 6px 爆点短线 -->
```

| 变体 | 高度 | 用在哪 |
|---|---|---|
| `.rule` | 2px | 分隔、页脚顶线 |
| `.rule--pop` | 6px | 标题下的小短线、强调 |

**没有 1px 的变体**。发丝线属于编辑设计，不属于这套语言；需要更轻的分隔就降低对比（用 `--alt`），不要减细。规则 4 由 `WEIGHT` 判定。

**禁止**用 `<hr>` 或 `border-bottom` 代替——它们的内边距和盒模型不好控制。

---

## 编号头 `.card-head`

```html
<div class="card-head">
  <span class="num fg-pop" style="font-size:34px;">01</span>
  <span class="meta fg-fg">ONE DIAGONAL</span>
</div>
```

4px 顶线 + 大数字 + 全大写小标。四栏页的标配。
**注意**：`card-head` 是 flex，两个 span 会各自成为独立文本框（不是合并的一段）——这是对的。

**不许手写 deck.css 里没有的类**：浏览器对未定义类是静默 fallback，`validate` 会报 `CLASS`，但预览可能已经先塌了一半。改版式前先在 `deck.css` 里找到那个类。

---

## 页脚 `.folio`

```html
<div class="folio">
  <div class="meta fg-fg">ART · PRODUCTION · SOCIETY</div>
  <div class="meta fg-fg">02 / 10</div>
</div>
```

默认只有 `left:56 / bottom:40` 和 `display:flex`，**没有顶线也没有固定宽度**；顶线是 `.folio--cut` / `.folio--end` 才加的。

| 变体 | 形态 | 用在哪 |
|---|---|---|
| `.folio` | 贴左，无装饰 | 默认，最不对称 |
| `.folio--cut` | 左侧一段 2px 顶线 | 需要"页码起点"的页 |
| `.folio--block` | 反白色块压角 | 墨底页或照片页 |
| `.folio--end` | 1168 宽 + 两端对齐 | 正式场合，别连续用 |

规则 11 要求三种形态轮换，连续三页同形 `validate` 会 warn。

**墨底页**用 `.folio--block`，不要给 `.folio--cut` 改 `border-top-color`——基础 `.folio` 没有边框，改了也不生效。

---

## 编号表格 `.counter`

参考海报右上角那种 `09 / 100`。

```html
<div class="counter">
  <div class="counter__cell">
    <div class="num fg-fg" style="font-size:56px;">09</div>
    <div class="micro fg-mute" style="margin-top:2px;">/ 100</div>
  </div>
  <div class="counter__cell">…</div>
</div>
```

单元格之间是 2px 竖线（`.counter__cell` 的 `border-left`），首格没有。数值用 `.num`（窄体等宽），单位用 `.micro`。

---

## 竖排标签 `.vlabel`

```html
<div class="vlabel" style="left:1222px; top:120px; height:240px; color:var(--bg);">
  SERIAL EXPERIMENTS 04
</div>
```

`writing-mode: vertical-rl`，从下往上读。**只用于装饰性标签**，不要放需要读的内容。
放在深色块上时要改 `color`。

---

## 条形码 `.barcode`

```html
<div class="barcode">
  <i></i><i></i><i></i><i></i><i></i><i></i><i></i><i></i>
</div>
```

一排细竖条：基础 2px，每 3 根变宽（5px）、每 5 根回到 2px、每 7 根最宽（7px）。纯装饰，用来填充角落的空。

---

## 颗粒 `.grain` / 网点 `.halftone`

```html
<div class="grain"></div>      <!-- 放在 DOM 第一个子元素位置 -->
```

整幅透明 PNG，1280×720。**必须放在所有内容的第一个**（当底层），否则会盖住文字，在 PowerPoint 里还会挡住点击。

- `.grain`：纸张颗粒，透明度已烘焙在 PNG 里（约 10–12%），浅底可见。**不要写 CSS `opacity`**，转换器会拍平。
- `.halftone`：10px 网点，更明显的丝网印刷感，用于 C 组风格。

墨底页也可以加，但几乎看不见——那种情况删掉，省一个图元。

---

## 引号（没有专用类）

引号用**真文本 + 展示字**，不要伪元素（`FORBID:pseudo` 会报错）。

```html
<div class="t-h2 fg-pop" style="position:absolute; left:96px; top:96px;">「</div>
```

用中文引号「」，字号取 `.t-h1` 或 `.t-h2`，颜色用 `fg-pop`。`.num` 的窄体不适合引号——它没有中文标点。

---

## 栅格

```html
<div class="grid4" style="position:absolute; left:56px; top:262px; width:1168px;">…</div>
```

| 类 | 列数 | 列宽（1168 内容宽） | 间距 |
|---|---|---|---|
| `.grid4` | 4 | 275.5 | 22 |
| `.grid3` | 3 | 372 | 26 |
| `.grid2` | 2 | 568 | 32 |
| `.split` | 2 等分 | 584 | 0 |

**栅格单元里要放绝对定位元素时，单元必须 `position:relative`**，否则会定位到页面左上角。

等宽 `.grid4` 只适合“时间/数据等权项”（L05 时间轴）；内容页用 `.grid4--lead`，否则会触发 `BALANCE`。

---

## 组合示例：一个完整的四栏块

```html
<div class="grid4" style="position:absolute; left:56px; top:262px; width:1168px;">
  <div>
    <div class="card-head">
      <span class="num fg-pop" style="font-size:34px;">01</span>
      <span class="meta fg-fg">ONE DIAGONAL</span>
    </div>
    <div class="t-h4 fg-fg" style="margin-top:10px;">一条主斜线</div>
    <div class="t-small fg-fg" style="margin-top:6px;">整张图只有一个动势方向。</div>
  </div>
  <!-- 重复 3 次 -->
</div>
```


---

## 没入册但已定义的类

这些类在 `deck.css` 里存在，按需用；没有写进上面的组件表，不等于不能用：

| 类 | 用途 |
|---|---|
| `.masthead` | 顶部档头：左侧标题块 + 右侧编号格 |
| `.rays` / `.ray` | 放射线组；每条是一根细长矩形 |
| `.rule--v` | 竖向规线（配合 `.rule` 使用） |
| `.safe` | 安全区盒子，仅作布局参考 |
| `.abs` | `position:absolute` 的快捷类 |

未定义类会让浏览器静默 fallback，`validate` 会报 `CLASS`。新增类先加进 `deck.css`，不要在页面里写 inline 临时补。
