# 版式槽位表

> 本文件由 `scripts/gen-layout-docs.mjs` 从 `assets/layouts.json` 与 `assets/layouts/L*.html` 生成，勿手改。
> 坐标以骨架 HTML 为准；这里的 x/y/w/h 是从模板内联样式抽出的辅助值。

## 怎么用

1. 先写 `deck.plan.json`，用 `role` 选叙事位置，用 `layout` 选骨架。
2. 跑 `node scripts/plan.mjs check plan.json`；再跑 `node scripts/scaffold.mjs plan.json -o deck.html`。
3. 想改坐标就改骨架文件，然后重新生成这份表和画廊；不要只改一页导致全局漂移。

槽位写法：每个可填元素一个 `data-slot="name"`，内容写 `{{slot:name}}`；可选块用 `data-slot-block="name"` 包起来，scaffold 会整块删除空块。

## 角色 → 版式

| role | 候选版式 |
|---|---|
| `cover` | L01 / L02 |
| `context` | L02 / L06 / L07 / L14 / L19 / L21 |
| `thesis` | L06 / L07 / L17 |
| `method` | L04 / L18 |
| `evidence` | L06 / L11 / L12 / L13 / L15 / L17 / L19 / L21 |
| `data` | L05 / L11 / L15 / L20 |
| `comparison` | L09 / L22 |
| `sequence` | L05 / L14 / L18 / L20 |
| `case` | L12 / L13 / L17 / L19 / L21 |
| `quote` | L10 / L23 |
| `section` | L03 / L24 |
| `closing` | L16 / L25 |

## 画廊

缩略图与联系表是**生成物**：发布包不含二进制文件，需要看图时本地跑一次即可。

```bash
node scripts/scaffold.mjs --gallery examples/layout-gallery --force
node scripts/render.mjs examples/layout-gallery/deck.html --out examples/layout-gallery --sheet
```



_联系表未生成，跑上面的命令即可。_

## L01 · 巨构封面

- family：`hero` · roles：`cover` · motif：`sun+band`
- 骨架：`assets/layouts/L01.html`（缩略图是生成物，见「画廊」一节的生成命令）

_缩略图未生成：生成物，发布包不含二进制。生成命令见下方「画廊」一节。

| 槽位 | 形式 | 必填 | 字数上限 | 行数 | 坐标/说明 |
|---|---|---|---|---|---|
| `kicker` | T3 | ○ | 16 | — | x 56px / y 56px |
| `latin` | T3 | ○ | 24 | — | x 58px / y 250px |
| `title1` | T1 | ● | 6 | — | x 52px / y 292px |
| `title2` | T1 | ○ | 6 | — | x 52px / y 430px |
| `lead` | T2 | ● | 60 | 2 | x 56px / y 588px · w 640px |
| `meta` | T3 | ○ | 30 | — | x 600px / y 56px · w 624px |


---

## L02 · 档案封面

- family：`archive` · roles：`cover` / `context` · motif：`masthead+counter`
- 骨架：`assets/layouts/L02.html`（缩略图是生成物，见「画廊」一节的生成命令）

_缩略图未生成：生成物，发布包不含二进制。生成命令见下方「画廊」一节。

| 槽位 | 形式 | 必填 | 字数上限 | 行数 | 坐标/说明 |
|---|---|---|---|---|---|
| `masthead` | T3 | ○ | 20 | — | x 56px / y 48px |
| `title1` | T1 | ● | 6 | — | x 56px / y 140px |
| `title2` | T1 | ○ | 6 | — | x 56px / y 244px |
| `subtitle` | T2 | ○ | 40 | 2 | x 56px / y 392px · w 720px |
| `counter1` | T3 | ○ | 4 | — | 随父级 / group 单元 |
| `counter2` | T3 | ○ | 4 | — | 随父级 / group 单元 |
| `lead` | T2 | ○ | 90 | 4 | x 56px / y 500px · w 740px |
| `photo` | media | ○ | — | — | x 880px / y 100px · w 340px · h 340px |
| `meta` | T3 | ○ | 30 | — | x 56px / y 620px |


---

## L03 · 章节幕

- family：`section` · roles：`section` · motif：`number+circle`
- 骨架：`assets/layouts/L03.html`（缩略图是生成物，见「画廊」一节的生成命令）

_缩略图未生成：生成物，发布包不含二进制。生成命令见下方「画廊」一节。

| 槽位 | 形式 | 必填 | 字数上限 | 行数 | 坐标/说明 |
|---|---|---|---|---|---|
| `number` | T3 | ● | 3 | — | x 56px / y 80px |
| `chapter` | T3 | ● | 10 | — | x 56px / y 380px |
| `title1` | T1 | ● | 8 | — | x 56px / y 440px |
| `title2` | T1 | ○ | 8 | — | x 56px / y 540px |


---

## L04 · 1+3 方法页

- family：`grid` · roles：`method` · motif：`lead+three`
- 骨架：`assets/layouts/L04.html`（缩略图是生成物，见「画廊」一节的生成命令）

_缩略图未生成：生成物，发布包不含二进制。生成命令见下方「画廊」一节。

| 槽位 | 形式 | 必填 | 字数上限 | 行数 | 坐标/说明 |
|---|---|---|---|---|---|
| `kicker` | T3 | ○ | 16 | — | x 56px / y 48px |
| `title` | T1 | ● | 12 | — | x 56px / y 96px · w 900px |
| `lead` | T2 | ○ | 70 | 2 | x 56px / y 210px · w 820px |

**items**（固定 4 项）

| 槽位 | 形式 | 必填 | 字数上限 | 行数 | 坐标/说明 |
|---|---|---|---|---|---|
| `items.N.num` | T3 | ● | 3 | — | 随 group 单元 |
| `items.N.label` | T3 | ● | 8 | — | 随 group 单元 |
| `items.N.head` | T1 | ● | 6 | — | 随 group 单元 |
| `items.N.body` | T2 | ● | 45 | 3 | 随 group 单元 |

---

## L05 · 巨号数据 / 时间轴

- family：`timeline` · roles：`data` / `sequence` · motif：`big-numbers`
- 骨架：`assets/layouts/L05.html`（缩略图是生成物，见「画廊」一节的生成命令）

_缩略图未生成：生成物，发布包不含二进制。生成命令见下方「画廊」一节。

| 槽位 | 形式 | 必填 | 字数上限 | 行数 | 坐标/说明 |
|---|---|---|---|---|---|
| `kicker` | T3 | ○ | 16 | — | x 56px / y 56px |
| `title` | T1 | ● | 10 | — | x 56px / y 100px |
| `lead` | T2 | ○ | 70 | 2 | x 56px / y 190px · w 620px |
| `meta` | T3 | ○ | 30 | — | x 900px / y 56px · w 324px |

**items**（3–4 项）

| 槽位 | 形式 | 必填 | 字数上限 | 行数 | 坐标/说明 |
|---|---|---|---|---|---|
| `items.N.num` | T3 | ● | 4 | — | 随 group 单元 |
| `items.N.label` | T3 | ● | 8 | — | 随 group 单元 |
| `items.N.text` | T2 | ● | 30 | 2 | 随 group 单元 |

---

## L06 · 左右硬切

- family：`split` · roles：`context` / `thesis` / `evidence` · motif：`hard-split`
- 骨架：`assets/layouts/L06.html`（缩略图是生成物，见「画廊」一节的生成命令）

_缩略图未生成：生成物，发布包不含二进制。生成命令见下方「画廊」一节。

| 槽位 | 形式 | 必填 | 字数上限 | 行数 | 坐标/说明 |
|---|---|---|---|---|---|
| `kicker` | T3 | ○ | 16 | — | x 56px / y 56px |
| `title1` | T1 | ● | 6 | — | x 56px / y 120px |
| `title2` | T1 | ○ | 6 | — | x 56px / y 220px |
| `body` | T2 | ● | 80 | 4 | x 56px / y 360px · w 520px |
| `bigNumber` | T3 | ○ | 4 | — | x 700px / y 120px |
| `caption` | T2 | ○ | 30 | 2 | x 706px / y 390px · w 480px |
| `meta` | T3 | ○ | 30 | — | x 56px / y 620px |
| `photo` | media | ○ | — | — | x 690px / y 460px · w 530px · h 204px |


---

## L07 · 斜切宣言

- family：`wedge` · roles：`thesis` / `context` · motif：`wedge`
- 骨架：`assets/layouts/L07.html`（缩略图是生成物，见「画廊」一节的生成命令）

_缩略图未生成：生成物，发布包不含二进制。生成命令见下方「画廊」一节。

| 槽位 | 形式 | 必填 | 字数上限 | 行数 | 坐标/说明 |
|---|---|---|---|---|---|
| `title1` | T1 | ● | 7 | — | x 56px / y 120px |
| `title2` | T1 | ○ | 7 | — | x 56px / y 220px |
| `body` | T2 | ● | 70 | 4 | x 56px / y 380px · w 340px |
| `meta` | T3 | ○ | 30 | — | x 56px / y 600px |


---

## L09 · 双栏对比

- family：`compare` · roles：`comparison` · motif：`two-columns`
- 骨架：`assets/layouts/L09.html`（缩略图是生成物，见「画廊」一节的生成命令）

_缩略图未生成：生成物，发布包不含二进制。生成命令见下方「画廊」一节。

| 槽位 | 形式 | 必填 | 字数上限 | 行数 | 坐标/说明 |
|---|---|---|---|---|---|
| `title` | T1 | ● | 12 | — | x 56px / y 80px |
| `leftHead` | T1 | ● | 6 | — | x 56px / y 220px |
| `rightHead` | T1 | ● | 6 | — | x 660px / y 220px |
| `meta` | T3 | ○ | 30 | — | x 56px / y 620px |

**leftPoints**（固定 3 项）

| 槽位 | 形式 | 必填 | 字数上限 | 行数 | 坐标/说明 |
|---|---|---|---|---|---|
| `leftPoints.N.text` | T2 | ● | 30 | 2 | 随 group 单元 |

**rightPoints**（固定 3 项）

| 槽位 | 形式 | 必填 | 字数上限 | 行数 | 坐标/说明 |
|---|---|---|---|---|---|
| `rightPoints.N.text` | T2 | ● | 30 | 2 | 随 group 单元 |

---

## L10 · 引语

- family：`quote` · roles：`quote` · motif：`quote-bar`
- 骨架：`assets/layouts/L10.html`（缩略图是生成物，见「画廊」一节的生成命令）

_缩略图未生成：生成物，发布包不含二进制。生成命令见下方「画廊」一节。

| 槽位 | 形式 | 必填 | 字数上限 | 行数 | 坐标/说明 |
|---|---|---|---|---|---|
| `kicker` | T3 | ○ | 16 | — | x 100px / y 180px |
| `quote1` | T1 | ● | 14 | — | x 100px / y 200px |
| `quote2` | T1 | ○ | 14 | — | x 100px / y 280px |
| `attribution` | T3 | ● | 12 | — | x 104px / y 448px · w 640px |
| `meta` | T3 | ○ | 30 | — | x 104px / y 600px |


---

## L11 · 条形图

- family：`chart` · roles：`data` / `evidence` · motif：`bars`
- 骨架：`assets/layouts/L11.html`（缩略图是生成物，见「画廊」一节的生成命令）

_缩略图未生成：生成物，发布包不含二进制。生成命令见下方「画廊」一节。

| 槽位 | 形式 | 必填 | 字数上限 | 行数 | 坐标/说明 |
|---|---|---|---|---|---|
| `title` | T1 | ● | 10 | — | x 56px / y 56px |
| `lead` | T2 | ○ | 50 | 2 | x 56px / y 150px · w 700px |
| `maxValue` | T3 | ● | 6 | — | x 1000px / y 150px |
| `meta` | T3 | ○ | 30 | — | x 56px / y 620px |

**items**（3–5 项）

| 槽位 | 形式 | 必填 | 字数上限 | 行数 | 坐标/说明 |
|---|---|---|---|---|---|
| `items.N.label` | T3 | ● | 8 | — | 随 group 单元 |
| `items.N.value` | T3 | ● | 6 | — | 随 group 单元 |
| `items.N.display` | T3 | ● | 6 | — | 随 group 单元 |

---

## L12 · 人物 / 作品卡

- family：`cards` · roles：`case` / `evidence` · motif：`stair-cards`
- 骨架：`assets/layouts/L12.html`（缩略图是生成物，见「画廊」一节的生成命令）

_缩略图未生成：生成物，发布包不含二进制。生成命令见下方「画廊」一节。

| 槽位 | 形式 | 必填 | 字数上限 | 行数 | 坐标/说明 |
|---|---|---|---|---|---|
| `title` | T1 | ● | 12 | — | x 56px / y 56px |
| `meta` | T3 | ○ | 30 | — | x 900px / y 56px · w 324px |
| `portrait` | media | ○ | — | — | x 56px / y 190px · w 430px · h 300px |

**items**（固定 4 项）

| 槽位 | 形式 | 必填 | 字数上限 | 行数 | 坐标/说明 |
|---|---|---|---|---|---|
| `items.N.letter` | T3 | ● | 2 | — | 随 group 单元 |
| `items.N.name` | T1 | ● | 6 | — | 随 group 单元 |
| `items.N.meta` | T3 | ● | 10 | — | 随 group 单元 |
| `items.N.text` | T2 | ● | 30 | 2 | 随 group 单元 |

---

## L13 · 全图压字

- family：`image` · roles：`case` / `evidence` · motif：`full-image`
- 骨架：`assets/layouts/L13.html`（缩略图是生成物，见「画廊」一节的生成命令）

_缩略图未生成：生成物，发布包不含二进制。生成命令见下方「画廊」一节。

| 槽位 | 形式 | 必填 | 字数上限 | 行数 | 坐标/说明 |
|---|---|---|---|---|---|
| `image` | media | ● | — | — | x 0 / y 0 · w 1280px · h 720px |
| `kicker` | T3 | ○ | 16 | — | x 56px / y 410px |
| `title1` | T1 | ● | 7 | — | x 56px / y 440px |
| `title2` | T1 | ○ | 7 | — | x 56px / y 540px |
| `caption` | T2 | ○ | 40 | 2 | x 56px / y 610px · w 700px |
| `meta` | T3 | ○ | 30 | — | x 640px / y 410px · w 150px |


---

## L14 · 目录索引

- family：`contents` · roles：`context` / `sequence` · motif：`index-rows`
- 骨架：`assets/layouts/L14.html`（缩略图是生成物，见「画廊」一节的生成命令）

_缩略图未生成：生成物，发布包不含二进制。生成命令见下方「画廊」一节。

| 槽位 | 形式 | 必填 | 字数上限 | 行数 | 坐标/说明 |
|---|---|---|---|---|---|
| `title` | T1 | ● | 10 | — | x 56px / y 56px |
| `meta` | T3 | ○ | 30 | — | x 56px / y 620px |

**items**（固定 4 项）

| 槽位 | 形式 | 必填 | 字数上限 | 行数 | 坐标/说明 |
|---|---|---|---|---|---|
| `items.N.num` | T3 | ● | 4 | — | 随 group 单元 |
| `items.N.name` | T2 | ● | 20 | 1 | 随 group 单元 |
| `items.N.date` | T3 | ● | 12 | — | 随 group 单元 |

---

## L15 · 清单 / 表

- family：`table` · roles：`data` / `evidence` · motif：`rules-only-table`
- 骨架：`assets/layouts/L15.html`（缩略图是生成物，见「画廊」一节的生成命令）

_缩略图未生成：生成物，发布包不含二进制。生成命令见下方「画廊」一节。

| 槽位 | 形式 | 必填 | 字数上限 | 行数 | 坐标/说明 |
|---|---|---|---|---|---|
| `title` | T1 | ● | 12 | — | x 56px / y 56px |
| `meta` | T3 | ○ | 30 | — | x 56px / y 620px |

**headers**（固定 4 项）

| 槽位 | 形式 | 必填 | 字数上限 | 行数 | 坐标/说明 |
|---|---|---|---|---|---|
| `headers.N.text` | T3 | ● | 10 | — | 随 group 单元 |

**rows**（3–6 项）

| 槽位 | 形式 | 必填 | 字数上限 | 行数 | 坐标/说明 |
|---|---|---|---|---|---|
| `rows.N.c1` | T2 | ● | 20 | 1 | 随 group 单元 |
| `rows.N.c2` | T3 | ● | 10 | — | 随 group 单元 |
| `rows.N.c3` | T2 | ● | 20 | 1 | 随 group 单元 |
| `rows.N.c4` | T3 | ● | 10 | — | 随 group 单元 |

---

## L16 · 行动结尾

- family：`closing` · roles：`closing` · motif：`action`
- 骨架：`assets/layouts/L16.html`（缩略图是生成物，见「画廊」一节的生成命令）

_缩略图未生成：生成物，发布包不含二进制。生成命令见下方「画廊」一节。

| 槽位 | 形式 | 必填 | 字数上限 | 行数 | 坐标/说明 |
|---|---|---|---|---|---|
| `title1` | T1 | ● | 7 | — | x 56px / y 196px |
| `title2` | T1 | ○ | 7 | — | x 56px / y 314px |
| `action` | T2 | ● | 40 | 2 | x 56px / y 500px · w 620px |
| `photo` | media | ○ | — | — | x 856px / y 56px · w 368px · h 368px |
| `meta` | T3 | ○ | 30 | — | x 56px / y 56px |


---

## L17 · 大圆聚焦

- family：`focus` · roles：`case` / `thesis` / `evidence` · motif：`sun-orbit`
- 骨架：`assets/layouts/L17.html`（缩略图是生成物，见「画廊」一节的生成命令）

_缩略图未生成：生成物，发布包不含二进制。生成命令见下方「画廊」一节。

| 槽位 | 形式 | 必填 | 字数上限 | 行数 | 坐标/说明 |
|---|---|---|---|---|---|
| `kicker` | T3 | ○ | 16 | — | x 56px / y 56px |
| `title1` | T1 | ● | 6 | — | x 56px / y 110px |
| `title2` | T1 | ○ | 6 | — | x 56px / y 214px |
| `body` | T2 | ● | 70 | 4 | x 56px / y 360px · w 420px |
| `stat` | T3 | ○ | 4 | — | x 980px / y 190px |
| `statNote` | T3 | ○ | 10 | — | x 56px / y 560px |
| `meta` | T3 | ○ | 30 | — | x 56px / y 620px |


---

## L18 · 台阶进程

- family：`stair` · roles：`method` / `sequence` · motif：`ascending-steps`
- 骨架：`assets/layouts/L18.html`（缩略图是生成物，见「画廊」一节的生成命令）

_缩略图未生成：生成物，发布包不含二进制。生成命令见下方「画廊」一节。

| 槽位 | 形式 | 必填 | 字数上限 | 行数 | 坐标/说明 |
|---|---|---|---|---|---|
| `kicker` | T3 | ○ | 16 | — | x 56px / y 56px |
| `title` | T1 | ● | 8 | — | x 56px / y 90px |
| `meta` | T3 | ○ | 30 | — | x 450px / y 56px |

**steps**（3–4 项）

| 槽位 | 形式 | 必填 | 字数上限 | 行数 | 坐标/说明 |
|---|---|---|---|---|---|
| `steps.N.num` | T3 | ● | 4 | — | 随 group 单元 |
| `steps.N.label` | T3 | ● | 8 | — | 随 group 单元 |
| `steps.N.text` | T2 | ● | 22 | 2 | 随 group 单元 |

---

## L19 · 拼贴档案

- family：`collage` · roles：`context` / `evidence` / `case` · motif：`collage-cells`
- 骨架：`assets/layouts/L19.html`（缩略图是生成物，见「画廊」一节的生成命令）

_缩略图未生成：生成物，发布包不含二进制。生成命令见下方「画廊」一节。

| 槽位 | 形式 | 必填 | 字数上限 | 行数 | 坐标/说明 |
|---|---|---|---|---|---|
| `kicker` | T3 | ○ | 16 | — | x 56px / y 56px |
| `title` | T1 | ● | 12 | — | x 56px / y 90px |
| `bigImage` | media | ○ | — | — | x 56px / y 190px · w 600px · h 474px |
| `bigLabel` | T3 | ○ | 10 | — | x 76px / y 624px |
| `cellBHead` | T1 | ● | 6 | — | x 726px / y 222px |
| `cellBText` | T2 | ○ | 22 | 2 | x 726px / y 290px · w 468px |
| `cellCHead` | T1 | ● | 6 | — | x 696px / y 528px |
| `cellCText` | T2 | ○ | 20 | 2 | x 696px / y 588px · w 400px |
| `meta` | T3 | ○ | 30 | — | x 660px / y 56px · w 384px |


---

## L20 · 横向时间轴

- family：`timeline` · roles：`sequence` / `data` · motif：`spine-nodes`
- 骨架：`assets/layouts/L20.html`（缩略图是生成物，见「画廊」一节的生成命令）

_缩略图未生成：生成物，发布包不含二进制。生成命令见下方「画廊」一节。

| 槽位 | 形式 | 必填 | 字数上限 | 行数 | 坐标/说明 |
|---|---|---|---|---|---|
| `kicker` | T3 | ○ | 16 | — | x 56px / y 56px |
| `title` | T1 | ● | 10 | — | x 56px / y 90px |
| `lead` | T2 | ○ | 46 | 2 | x 56px / y 174px · w 560px |

**nodes**（3–4 项）

| 槽位 | 形式 | 必填 | 字数上限 | 行数 | 坐标/说明 |
|---|---|---|---|---|---|
| `nodes.N.date` | T3 | ● | 6 | — | 随 group 单元 |
| `nodes.N.label` | T3 | ● | 8 | — | 随 group 单元 |
| `nodes.N.text` | T2 | ● | 16 | 2 | 随 group 单元 |

---

## L21 · 图文对切

- family：`image-split` · roles：`case` / `evidence` / `context` · motif：`image-half`
- 骨架：`assets/layouts/L21.html`（缩略图是生成物，见「画廊」一节的生成命令）

_缩略图未生成：生成物，发布包不含二进制。生成命令见下方「画廊」一节。

| 槽位 | 形式 | 必填 | 字数上限 | 行数 | 坐标/说明 |
|---|---|---|---|---|---|
| `kicker` | T3 | ○ | 16 | — | x 56px / y 56px |
| `title1` | T1 | ● | 6 | — | x 56px / y 110px |
| `title2` | T1 | ○ | 6 | — | x 56px / y 214px |
| `body` | T2 | ● | 80 | 4 | x 56px / y 360px · w 520px |
| `image` | media | ○ | — | — | x 720px / y 0 · w 560px · h 720px |
| `caption` | T2 | ○ | 22 | 1 | x 744px / y 636px · w 512px |
| `meta` | T3 | ○ | 30 | — | x 56px / y 620px |


---

## L22 · 体量对比

- family：`contrast` · roles：`comparison` · motif：`two-scale`
- 骨架：`assets/layouts/L22.html`（缩略图是生成物，见「画廊」一节的生成命令）

_缩略图未生成：生成物，发布包不含二进制。生成命令见下方「画廊」一节。

| 槽位 | 形式 | 必填 | 字数上限 | 行数 | 坐标/说明 |
|---|---|---|---|---|---|
| `kicker` | T3 | ○ | 16 | — | x 56px / y 56px |
| `title` | T2 | ● | 12 | — | x 56px / y 90px · w 1000px |
| `leftLabel` | T3 | ● | 8 | — | x 56px / y 250px |
| `leftNum` | T1 | ● | 6 | — | x 56px / y 280px |
| `leftNote` | T3 | ○ | 40 | 2 | x 56px / y 440px · w 400px |
| `rightLabel` | T3 | ● | 8 | — | x 660px / y 250px |
| `rightNum` | T1 | ● | 6 | — | x 660px / y 280px |
| `rightNote` | T3 | ○ | 40 | 2 | x 660px / y 500px · w 480px |
| `takeaway` | T2 | ● | 40 | 2 | x 56px / y 576px · w 560px |


---

## L23 · 巨引语

- family：`quote` · roles：`quote` · motif：`ink-slab`
- 骨架：`assets/layouts/L23.html`（缩略图是生成物，见「画廊」一节的生成命令）

_缩略图未生成：生成物，发布包不含二进制。生成命令见下方「画廊」一节。

| 槽位 | 形式 | 必填 | 字数上限 | 行数 | 坐标/说明 |
|---|---|---|---|---|---|
| `kicker` | T3 | ○ | 16 | — | x 780px / y 520px |
| `quote1` | T1 | ● | 10 | — | x 56px / y 150px · w 420px |
| `quote2` | T1 | ○ | 10 | — | x 56px / y 270px · w 420px |
| `attribution` | T3 | ● | 16 | — | x 56px / y 448px · w 400px |
| `meta` | T3 | ○ | 40 | — | x 780px / y 556px · w 420px |


---

## L24 · 斜切章节

- family：`divider` · roles：`section` · motif：`wedge-number`
- 骨架：`assets/layouts/L24.html`（缩略图是生成物，见「画廊」一节的生成命令）

_缩略图未生成：生成物，发布包不含二进制。生成命令见下方「画廊」一节。

| 槽位 | 形式 | 必填 | 字数上限 | 行数 | 坐标/说明 |
|---|---|---|---|---|---|
| `number` | T3 | ● | 3 | — | x 56px / y 64px |
| `chapter` | T3 | ● | 10 | — | x 56px / y 180px |
| `title1` | T1 | ● | 8 | — | x 56px / y 250px · w 620px |
| `title2` | T1 | ○ | 8 | — | x 56px / y 370px · w 620px |
| `lead` | T2 | ○ | 40 | 2 | x 56px / y 500px · w 560px |


---

## L25 · 横幅收束

- family：`closing` · roles：`closing` · motif：`banner-action`
- 骨架：`assets/layouts/L25.html`（缩略图是生成物，见「画廊」一节的生成命令）

_缩略图未生成：生成物，发布包不含二进制。生成命令见下方「画廊」一节。

| 槽位 | 形式 | 必填 | 字数上限 | 行数 | 坐标/说明 |
|---|---|---|---|---|---|
| `title1` | T1 | ● | 7 | — | x 56px / y 56px · w 900px |
| `title2` | T1 | ○ | 7 | — | x 56px / y 158px · w 900px |
| `action` | T2 | ● | 30 | 2 | x 56px / y 360px · w 820px |
| `contact` | T3 | ○ | 60 | 2 | x 56px / y 500px · w 700px |
| `meta` | T3 | ○ | 30 | — | x 56px / y 610px |


