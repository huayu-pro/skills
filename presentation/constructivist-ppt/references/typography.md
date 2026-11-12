# 字体与排字

## 字体栈

`deck.css` 里四组，**不要改成别的**：

```css
--f-display: "Noto Sans CJK SC", "Source Han Sans SC", "Microsoft YaHei", sans-serif;
--f-body:    同 --f-display;
--f-latin:   "Liberation Sans Narrow", "Arial Narrow", "Helvetica Neue", Arial, sans-serif;
--f-mono:    "DejaVu Sans Mono", Consolas, "Courier New", monospace;
```

中文展示字靠 `font-weight: 900` 取到黑体（Noto Sans CJK SC 家族内含 Black 字重，不需要另设 font-family）。
西文展示字靠**窄体**（condensed）—— 这是构成主义区别于瑞士风格的关键：瑞士用常规宽度的 Helvetica，构成主义用被压扁的工业字体。

| 本机渲染 | 写入 PPTX（office） | 写入 PPTX（source） |
|---|---|---|
| Noto Sans CJK SC Black | 微软雅黑 Bold | 思源黑体 CN Heavy |
| Liberation Sans Narrow Bold | Arial Narrow Bold | Arial Narrow Bold |
| DejaVu Sans Mono | Consolas | Consolas |

**注意**：`Noto Sans CJK SC Black` 是独立 family，`font-family: "Noto Sans CJK SC"; font-weight: 900` 在 Chromium 里能取到 Black，但在别的渲染器里未必。要绝对保险就用 `data-fidelity="raster"` 把关键标题栅格化——注意转换器会连底色一起截，所以这个标题必须落在纯色区（纸底或墨底）。

---

## 字号阶梯

画布 1280×720，下列 px 值直接对应 `deck.css` 的类：

| 类 | px | pt | 用途 |
|---|---|---|---|
| `.t-hero` | 158 | 118.5 | 封面主标题，一行不超过 5 个汉字 |
| `.t-h1` | 96 | 72 | 内页大标题 |
| `.t-h2` | 64 | 48 | 常规标题 |
| `.t-h3` | 42 | 31.5 | 小节标题 |
| `.t-h4` | 28 | 21 | 卡片标题 |
| `.t-lead` | 26 | 19.5 | 导语 |
| `.t-body` | 19 | 14.25 | 正文 |
| `.t-small` | 18 | 13.5 | 卡片正文、注释 |
| `.meta` | 15 | 11.25 | 元数据、页脚 |
| `.micro` | 13 | 9.75 | 装饰性微字，不承载信息 |

字号地板由规则 9 判定：信息文本不低于 `.t-small`，标签不低于 `.meta`，微字只能是装饰。

**标签档最多 12 个汉字**（`FONT` 会判）。超过就不是标签，搬到正文档；不要把句子塞进 `.meta`。

**展示字一行一个元素**：`.t-hero` / `.t-h1` / `.t-h2` 内置 `nowrap`；要两行就写两个 div，各自定位（`WRAP` 会判）。

**比例原则**：`.t-h1`/`.t-hero` 与正文的比值应 ≥ 3.5，`.t-h2` 与正文 ≥ 3.0。`.t-h1` 配正文 = 5.05，是对的；`.t-h2` 配正文 ≈ 3.4，合格；再往下的标题与正文拉不开差距，那种情况应该把标题换成 `.t-h2`，或者把正文压到两三行。

---

## 行距

| 场景 | line-height | 说明 |
|---|---|---|
| 展示字单行 | 0.86–1.00 | 大字收得紧一些；字面框比行高大，视觉上会轻微咬合 |
| 两行标题（两个独立元素） | 第二行 top 差 = 字号 × 1.0–1.15 | 例：64px 标题，第二行 top 比第一行大 64–74；不要靠自动折行 |
| 正文 | 1.55–1.62 | 低于 1.5 会挤，高于 1.7 会散 |
| 元数据 | 1.3–1.4 | |

**关键**：展示字不要靠 `line-height` 做紧排，要靠**元素的 top 差**。因为 PowerPoint 的固定行距对首行基线的锚定方式与 CSS 不完全一致，单行元素没有这个问题。

---

## 字距

| 场景 | letter-spacing |
|---|---|
| 中文展示字 | `-0.02em` ~ `-0.035em`（越大的字收紧越多） |
| 中文正文 | `0` ~ `0.01em` |
| 西文展示字 | `0.01em` ~ `0.05em` |
| 元数据（全大写） | `0.14em` ~ `0.26em` |
| 竖排标签 | `0.24em` |

字距在 PPT 里会被转成 `charSpacing`（pt），并强制关闭 kerning。所以 HTML 里要显式写 `font-kerning: none`（`deck.css` 已在 `.slide` 上设好），让两边一致。

---

## 七种排字技法

参考海报里反复出现的处理，按可移植性排序（前面的转换后最稳）。

1. **巨型放大**——一个字占半个画面。最稳，纯字号。
2. **局部反白**——标题压在深色块上，或其中一个词换成爆点色。用 `<em>` 做 run 级换色，转换后仍是同一段。
3. **双行错位**——两行标题左边界不同，第二行缩进 40–80px。用两个元素。
4. **与几何咬合**——标题压在色块边缘，一半在块上一半在纸面。靠图层顺序，转换后仍是两个对象。
5. **沿斜带排**——把文字元素和色带设成同一个 `rotate`，文字元素叠在色带之上。转换后是两个独立对象，都能拖。
6. **纵向排列**——`writing-mode: vertical-rl`。转换后是 `vert="eaVert"`，可编辑。
7. **局部裁切**——标题被色块咬掉一角。**转换不了**，只能用"超出画布边缘"或"盖一块与底色相同的矩形"近似。

---

## 中英混排

- 中文用黑体，西文用窄体，两者混排时**西文视觉重量要接近中文**。中文 900 配西文 Bold 是安全的。
- 中英同一行时，字号不要一样大：西文略小（×0.85）并加字距，看起来才齐。
- 全大写的西文不要超过 40 个字符，否则失去"标签感"变成一团灰。
- 标点：中文用全角，西文用半角；`·` 和 `—` 两侧留半角空格。

---

## 字体授权

| 字体 | 授权 | 说明 |
|---|---|---|
| Noto Sans CJK / Source Han Sans | SIL OFL | 商用免费，可嵌入 |
| Liberation Sans Narrow | SIL OFL | 与 Arial Narrow 度量兼容 |
| DejaVu Sans Mono | 自由 | |
| Arial Narrow | 随 Office 授权 | 交付时用这个，对方一定有 |
| 微软雅黑 | 随 Windows 授权 | 交付默认 |
| 思源黑体 | SIL OFL | 需自行安装 |

**不要把字体文件打进 PPTX**——授权和体积都有问题。用 `--font-profile` 控制写入的字体名，让对方机器自己去找最接近的。
