# 交付前检查

下面每一项都对应一个工具或一个明确的人工判断。**没跑完 gate 不算交付。**

每条带规则码的都可以工具化；标「人工」的只能靠眼睛，别假装工具查过。

## 规划与结构（8 页以上）

- [ ] **1. plan 已通过**：`node scripts/plan.mjs check plan.json --strict` 零 error。
- [ ] **2. plan ↔ deck 一致**：`node scripts/plan.mjs check --deck deck.html --plan plan.json` 零 error；页数、id、role、layout 都对得上。
- [ ] **3. 每页有 `data-role` + `data-layout` + `data-purpose`**（`STRUCTURE` / `LAYOUT`）。自定义版式写 `custom`。
- [ ] **4. 目录版式的必填槽位齐全、没有超字数**（`SLOTS`）。槽位表见 `layout-specs.md`。
- [ ] **5. 叙事顺序成立**：首 cover、尾 closing；连续同 layout 不超过 2 页；单版式占比 ≤40%（`STRUCTURE`）。

## 硬伤（必须全过）

- [ ] **6. `validate` 零 error、`audit-text` 零占位。** 不是“大部分修了”，是零。
- [ ] **7. 每页有主斜线或楔形，而且它是画面主导**（`AXIS`）。正交版面不叫构成主义。
- [ ] **8. 没有等价并列的色块**（`BALANCE`）。首栏按规则 2 的判据做。
- [ ] **9. 单页四色含纸，且都在主题 token 里**（`INK`）。`--mute` 只给标签档（`MUTE`）。
- [ ] **10. 没有细于规则 4 的线**（`WEIGHT`）。
- [ ] **11. 展示字没有折行**（`WRAP`）。每行都是独立元素。
- [ ] **12. 正文面积、字号、对比度都达标**（`TEXTAREA` / `FONT` / `CONTRAST`）。
- [ ] **13. 全篇只有一套主题**（`THEME`）。样张文件才挂 `data-showcase`。
- [ ] **14. 文字没有越出画布/安全区，也没有被容器裁掉**（`BOUNDS` / `SAFE` / `OVERFLOW`）。
- [ ] **15. 没有文字被后序色块盖住**（`OCCLUDE`）；故意的叠压加 `data-overlap-ok`。
- [ ] **16. 没有转换器表达不了的写法**（`FORBID`）：渐变/阴影/滤镜/混合/z-index/fixed/伪元素/嵌套旋转/translate/scale/非 polygon 裁切/非正圆圆角/远程图/内联 SVG。

## 内容（audit-text 兜底）

- [ ] **17. 每页有 `data-notes` 和 `data-purpose`**（`NOTES` / `PURPOSE`）。讲稿 1–3 句，能直接照读。
- [ ] **18. 没有占位文案。** `xxx` / `TODO` / 待补 / Lorem / 示例文本，一个都不留。
- [ ] **19. 数字有来源或标注“示意”。** 不编精确数字。
- [ ] **20. 中英之间有空格、标点全角统一、术语大小写一致**（`SPACING` / `PUNCT` / `QUOTE` / `TERM`）。

## 质量（过不了要说理由）

- [ ] **21. 单页字数达标**（`DENSITY`）、相邻两页骨架不同（`RHYTHM`）、页脚三页不同形（`FOOTER`）。
- [ ] **22. 翻一遍联系表，能说出每一页在强调什么。** 说不出来的一页就是废页（人工）。
- [ ] **23. 全图页的字落在实色带上，不是半透明蒙层上**（人工；`OPACITY` 会判代码层）。
- [ ] **24. 去“模板味”走查（人工）**：逐页问三个问题——这页和上一页是不是同一个构图的换字版？标题是不是永远待在同一个角落？所有元素是不是都在安全区里端端正正？连续两页答“是”就换骨架、翻转 `axisDeg` 方向或换一种 folio 形态。
- [ ] **25. 缺图页的兜底成立（人工）**：没配图版式的几何底块要像“有意设计的空窗”，不能像“图没加载出来”。`render` 后逐页看一眼。

---

## 交付话术

```
N 页，[子风格]，[配色]。
文字、色块、斜带、多边形都是原生对象，可以直接改字改色改角度。
纸张颗粒是一层透明 PNG，删掉不影响内容。
备注栏里有讲稿。
如字体偏细，是目标机器缺 [字体名]，用"开始 → 字体替换"换成微软雅黑即可。
```

三句话说完，不要写设计说明。

---

## 无障碍与可读性（投影场合）

幻灯片的最终归宿是投影仪，不是显示器。

- [ ] 正文与元数据不低于规则 9 的地板。投影时太小的正文等于没写。
- [ ] 对比度过规则 8，重要信息再高一档。深底上的深灰是重灾区。
- [ ] 不靠颜色单独传达信息。红绿对比在色盲眼里是同一片灰——要么加形状，要么改用明度差。
- [ ] 字号层级只用“大小 + 字重”区分，不引入第三种字体。
- [ ] 纯装饰微字不承载任何信息，删掉不影响理解。

---

## 交付前的验证链

按顺序跑，前一步不过不进下一步：

```bash
node scripts/plan.mjs check plan.json --strict                         # 1 规划
node scripts/validate.mjs deck.html --strict                           # 2 版式/构图/结构
node scripts/audit-text.mjs deck.html --strict                         # 3 内容与中文排版
node scripts/render.mjs deck.html --out preview --sheet                # 4 逐页图 + 联系表，人眼看
node scripts/build-deck.mjs deck.html -o deck.pptx                     # 5 编译
node scripts/verify-pptx.mjs deck.pptx --out pptx-render --vs preview  # 6 反渲比对
node scripts/verify-render.mjs deck.pptx --out render --vs preview     # 7 真渲染（有 LO 才跑）
node scripts/gate.mjs deck.html --plan plan.json                       # 8 一条命令串起以上
```

缺第 6 步，“原生对象”只是承诺；缺第 7 步，“PowerPoint 打得开”只是承诺。`gate.mjs` 会把每一步的退出码写进 `gate.json`。
