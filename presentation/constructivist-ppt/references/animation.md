# 动画：实现细节

**这份文件是给改转换器的人看的。** 写页面只需要 SKILL.md 里那三行：`data-anim` + `data-anim-step`，不写就没有动画。

## 设计约束

构成主义的动画只做一件事：**让观众按设计的顺序看**。所以：

- 一页最多三个对象动。
- 斜带先入、大字后压。
- 不做逐字打字机、不做旋转飞入——那两样和这套语言冲突。

```html
<div class="band"   data-anim="wipe-up" data-anim-step="0"></div>
<div class="sun"    data-anim="fade"    data-anim-step="1"></div>
<div class="t-hero" data-anim="fade"    data-anim-step="2">构成主义</div>
```

`step` 越大越晚（每级 120ms）。默认 `chain`：首个元素 `clickEffect`，同页后续 `withEffect`，一次点击整组依次揭示。`--anim-mode=click` 则每个元素各点一次。

## 支持的取值

`fade` / `dissolve` / `wipe` / `wipe-up` / `wipe-down` / `wipe-left` / `wipe-right` / `wedge` / `circle-in` / `circle-out`

`wipe` 是 `wipe-up` 的别名；写哪个都行，效果相同。

不在这个集合里的值会在 build 时报 warning 并退化成无动画。别用 `wheel-*` / `blinds` / `checker` 那批——`anim.mjs` 里虽然定义了，但不在白名单，写了也不生效。

## preset 映射（实证过，照抄别猜）

| filter | presetID / subtype | 方向 |
|---|---|---|
| `fade` | 9 / 0 | 无方向 |
| `dissolve` | 10 / 0 | 无方向 |
| `wipe-up` | 22 / 1 | 自下而上 |
| `wipe-down` | 22 / 4 | 自上而下 |
| `wipe-left` | 22 / 8 | 自右向左 |
| `wipe-right` | 22 / 2 | 自左向右 |
| `wedge` | 37 / 0 | 楔形 |
| `circle-in` | 18 / 12 | 圆入 |
| `circle-out` | 19 / 12 | 圆出 |

**两个反直觉的点**：`fade` 是 9 不是 10（10 是 dissolve）；`wipe-up` 的 subtype 是 1 不是 4（4 是 wipe-down，方向整个反掉）。这张表来自 `pptx-animation-skill` 的 `filter_vocabulary.xml`，在 PowerPoint 里逐帧验证过，不要按 ECMA 文档"修正"。

## XML 结构

每个 par 必须是两个子节点，顺序固定：

```xml
<p:par>
  <p:cTn id="…" presetID="9" presetClass="entr" presetSubtype="0" fill="hold" nodeType="clickEffect">
    <p:set>…style.visibility → visible…</p:set>
    <p:animEffect transition="in" filter="fade">…</p:animEffect>
  </p:cTn>
</p:par>
```

缺 `p:set`，入场没有过渡起点，动画不会播——PowerPoint 不报错，只是"点了没反应"。

## spid 映射的脆弱点

`anim.mjs` 用"第 N 个 shape ↔ 第 N 个 `<p:sp>`"来定位目标：`ids[sh.emitIndex]`。

所以**任何让 pptxgenjs 多写或少写一个 `sp` 的改动都会错位**，而 `verifyTiming()` 只能发现 spid 不存在，发现不了"指到了隔壁形状"。改 `emit.mjs` 的发射逻辑后，必须肉眼验证一次动画落在哪个对象上。

## 自检

`lib/anim.mjs` 的 `verifyTiming()` 在写入前校验五件事，不过就构建失败：

1. 每个 par 都有 `p:set` + `p:animEffect`。
2. presetID 与 filter 匹配。
3. presetSubtype 匹配。
4. 所有 spid 在 slide 里存在。
5. timing 节点位置在 `<p:transition>` 之后、`</p:sld>` 之前。

`--no-anim` 会整体跳过注入，用来定位"是不是动画导致打不开"。
