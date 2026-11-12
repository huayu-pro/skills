# 规则码与故障排查

`validate` 的每个输出都带一个规则码。先按码定位，再按修法改，不要凭症状猜。

<!-- CODES:BEGIN 由 scripts/gen-rules-doc.mjs 生成，勿手改 -->
| 码 | 级别 | 判据 | 典型修法 |
|---|---|---|---|
| `AXIS`<br><sub>规则 1</sub> | error | 一页只有一条主斜线，且它必须主导画面（面积 ≥0.03，长边 ≥0.3 画布宽） | 放大主斜带到贯穿画面，统一角度或删掉竞争的那条；确需正交版面加 data-axis-ok |
| `BALANCE`<br><sub>规则 2</sub> | error | 面积必须不均，首栏 ≥1.7× 第二栏 | 抬高首栏或压缩次栏；确需等价并列加 data-balance-ok |
| `INK`<br><sub>规则 3</sub> | error | 一页最多 4 色（纸 + 主墨 + 爆点 + 次墨；--mute 不计入），且必须来自当前主题 token | 删掉多余颜色；反白用 var(--bg)；色板展示页加 data-palette-ok |
| `WEIGHT`<br><sub>规则 4</sub> | error | 线宽 ≥2px | 1px 发丝线是编辑设计，不是构成主义；改成 2px 或用色块 |
| `WRAP`<br><sub>规则 5</sub> | error | 展示字（.t-hero/.t-h1/.t-h2）必须 nowrap，一行一个元素 | 要两行就写两个 div 各自定位，不要靠自动折行 |
| `TEXTAREA`<br><sub>规则 6</sub> | error | 正文面积 ≤15% 画布 | 删减正文或拆页；构成主义靠面积差说话，不靠字数 |
| `CLASS`<br><sub>规则 7</sub> | error | 只用 deck.css 里已定义的类 | 浏览器对未定义类静默 fallback，版式会塌；先查 references/components.md |
| `CONTRAST`<br><sub>规则 8</sub> | error | 正文 ≥4.5，≥28px 或 ≥700 字重时 ≥3 | 换墨色、加深底色，或把字号提到大字号档 |
| `FONT`<br><sub>规则 9</sub> | error | 信息文本 ≥18px，标签 ≥15px，微字 ≥13px 且只做装饰 | 升一档字号阶梯，或把内容移出标签 |
| `DENSITY`<br><sub>规则 10</sub> | warn | 每页 ≤240 字（汉字 + 拉丁词） | 删到只留一个主张；支撑点移进讲稿 |
| `PURPOSE`<br><sub>支撑检查</sub> | error | 每页必须有 data-purpose：这页要让观众记住什么 | 补一句“任务”；结构化 deck 缺它直接报错，短稿至少报警 |
| `NOTES`<br><sub>支撑检查</sub> | error | 每页必须有 data-notes 讲稿 | 写 1–3 句能直接照读的话；封面/证据/结尾至少 2 句 |
| `FOOTER`<br><sub>规则 11</sub> | warn | 页脚不许连续三页同一种形态 | 在默认贴左、`.folio--cut`、`.folio--block`、`.folio--end` 之间轮换 |
| `GATE`<br><sub>规则 12</sub> | gate | 交付前跑完验证链：validate / audit-text / render --sheet / build / verify-pptx（有 LO 再 verify-render） | 没跑完 gate 不算交付 |
| `BOUNDS`<br><sub>支撑检查</sub> | error | 文字越出 1280×720 画布（容差 ±1px） | 改坐标或拆行；色块出血是刻意的，只有文字算错 |
| `OVERFLOW`<br><sub>支撑检查</sub> | error | 文字被容器裁切 | PPT 没有裁切概念，被切掉的内容会直接消失 |
| `OVERLAP`<br><sub>支撑检查</sub> | warn | 两段文字相互压叠 | 挪开；构图上的故意压字加 data-overlap-ok |
| `RHYTHM`<br><sub>支撑检查</sub> | warn | 相邻两页色块面积指纹完全相同 | 换骨架；联系表上一眼就能看出连续同版式 |
| `OPACITY`<br><sub>支撑检查</sub> | warn | 元素半透明：文本 <0.95 error，形状 <0.99 warn；PPTX 会拍平 | 文字必须不透明；形状改预混实色，或用 --alt 做层级 |
| `THEME`<br><sub>支撑检查</sub> | error | 一份 deck 只用一套主题；样张可用 data-showcase 豁免 | 选定一套 theme-*，其余页统一；风格对照交给 style-preview.mjs |
| `FORBID`<br><sub>支撑检查</sub> | error | 用了转换器表达不了的 CSS（渐变/阴影/滤镜/混合/层级/fixed/伪元素/嵌套变换/裁切/svg/transform/远程图） | 删掉该属性，或用真实 DOM 元素重做 |
| `DECK`<br><sub>支撑检查</sub> | error | 空 deck 或 --slide 越界 | 每页一个 section.slide；--slide 取 1–页数，不能拿“0 页 0 问题”当通过 |
| `SAFE`<br><sub>支撑检查</sub> | error | 正文越出 56px 安全区 | 正文收回安全区；展示字可以出血，但正文不出。确需出血加 data-safe-ok |
| `OCCLUDE`<br><sub>支撑检查</sub> | error | 文字被后序不透明色块盖住 | 把文字放到色块之后（DOM 后序），或挪开色块；故意的叠压加 data-overlap-ok |
| `MUTE`<br><sub>规则 3</sub> | error | --mute 只给 ≤15px 的非信息微字，不能做副标 | 信息文本改用 --fg 或 --alt；--mute 不进入四色统计 |
| `STRUCTURE`<br><sub>支撑检查</sub> | error | 结构化 deck 每页必须有 data-role + data-layout，且首 cover、尾 closing、版式有轮换 | 补 data-role/data-layout；连续同版式不超过 2 页，单版式占比不超过 40% |
| `LAYOUT`<br><sub>支撑检查</sub> | error | data-layout 不在 layouts.json 里，或 layout 不支持该 role | 用目录里的 L01–L21；自定义版式写 data-layout="custom" |
| `SLOTS`<br><sub>支撑检查</sub> | error | 目录版式缺少必填槽位、槽位超字数或展示字折行 | 按 references/layout-specs.md 的槽位表补齐；超字数先删内容再调坐标 |
| `WIDTH`<br><sub>规则 5</sub> | warn | 单行正文没有显式 width，文本框贴着墨迹 | 给 T2 正文写 width；否则用户在 PPT 里加字不会重排 |
| `TRANSFORM`<br><sub>支撑检查</sub> | error | 静态 translate/scale/skew/matrix 不是纯 rotate | 只允许单层 rotate；位移用 left/top，缩放用真实尺寸，斜切用 polygon |
| `PLACEHOLDER`<br><sub>支撑检查</sub> | error | 不得残留占位文案（TODO/待补/xxx） | 换成真实内容；占位文案进了 PPT 就是交付事故 |
| `DUPLICATE`<br><sub>规则 10</sub> | error | 同一 deck 内不得出现重复的整句主张 | 合并重复页，或改写其中一页的主张 |
| `SPACING`<br><sub>支撑检查</sub> | warn | 中文与拉丁词之间要有空格 | 补空格；排版细节影响可读性 |
| `PUNCT`<br><sub>支撑检查</sub> | warn | 标点不得连用或中英文混用 | 统一中文标点；连用只保留一个 |
| `QUOTE`<br><sub>支撑检查</sub> | warn | 中文正文用「」而非弯引号 | 改成「」；弯引号在中文字体里字重不对 |
| `EMPTY`<br><sub>规则 10</sub> | warn | 几乎空页（汉字+词数过少） | 补内容或删掉这一页；空页在投影上是尴尬 |
| `TERM`<br><sub>支撑检查</sub> | warn | 同一术语大小写不一致 | 全 deck 统一写法 |
<!-- CODES:END -->

## 按症状查

| 症状 | 先看哪个码 | 说明 |
|---|---|---|
| 预览就塌了、字号不对 | `CLASS` | 用了 deck.css 里没有的类，浏览器静默 fallback |
| 页面比别人的"软" | `BALANCE` / `WEIGHT` | 面积太平均，或出现了 1px 发丝线 |
| 颜色显脏、显花 | `INK` / `MUTE` | 超过四色；或 `--mute` 被拿去做副标 |
| 标题突然折行 | `WRAP` / `SLOTS` | 覆盖了 `white-space`，或槽位超字数 |
| 投影上看不清 | `CONTRAST` / `FONT` | 对比度不足，或字号掉到地板以下 |
| 文字压在一起 | `OVERLAP` / `OCCLUDE` | 文字互压，或被后序色块盖住 |
| 文字被切掉 | `OVERFLOW` / `BOUNDS` / `SAFE` | 容器裁切、越出画布或安全区 |
| 连续几页看着一样 | `RHYTHM` / `FOOTER` / `STRUCTURE` | 版式指纹相同、页脚三页同形、或版式连续/占比超限 |
| 生成物里元素消失 | `FORBID` | 渐变/伪元素/svg/translate 这类转换器表达不了的写法 |
| plan 和页面不一致 | `LAYOUT` / `SLOTS` / `STRUCTURE` | data-role/layout 与 plan 不符，或槽位缺失 |
| 0 页也显示"通过" | `DECK` | 空 deck 或 `--slide` 越界；v3 会直接 error |

## v3 新增码怎么修

| 码 | 典型原因 | 修法 |
|---|---|---|
| `DECK` | 空文件、`--slide` 越界 | 补 `section.slide`；页码取 1–页数 |
| `SAFE` | 正文太靠边 | 收回 56px 安全区；确实要出血加 `data-safe-ok` |
| `OCCLUDE` | 后画的色块盖住文字 | 把文字放到块之后（DOM 后序），或挪开块；故意叠压加 `data-overlap-ok` |
| `MUTE` | `--mute` 用于正文/副标 | 改用 `--fg`/`--alt`；`--mute` 只给标签档 |
| `STRUCTURE` | 缺 role/layout、首尾角色不对、版式连续/占比超限 | 补属性；换骨架；8 页以上先写 plan |
| `LAYOUT` | layout 不存在，或 layout 不支持该 role | 查 `layout-specs.md` 的角色表；自定义写 `custom` |
| `SLOTS` | 必填槽缺失、槽位超字数、展示字折行 | 按 `layout-specs.md` 补；先删内容再调坐标 |
| `WIDTH` | 单行正文没有显式宽度 | 给 T2 正文写 `width`；否则改字不重排 |
| `TRANSFORM` | translate/scale/skew/偏心 origin | 只保留单层 rotate；位移用 left/top |

## 计划与骨架

| 报错 | 原因 | 改法 |
|---|---|---|
| `plan.mjs` 报页数/时长 | 页数与 `durationMin` 不匹配 | 调 `minutes` 或 `durationMin`；允许 ±20% |
| `plan.mjs` 报 role/layout | layout 不支持这个角色 | 查 `layout-specs.md`；换一个候选版式 |
| `plan.mjs` 报槽位/字数 | 槽位超预算 | 先删内容；不要靠缩字号硬塞 |
| `scaffold.mjs` 报 plan 未通过 | 结构检查失败 | 先修 plan，再 scaffold |
| `gate.mjs` 报"必须先有 plan" | 8 页以上没有 `--plan` | 先写 plan，或把 deck 缩到 8 页以下 |
| `plan --deck` 报漂移 | 页面被手删/手改 | 重新 scaffold；或同步改 plan |

## 兼容旧 deck

- `node scripts/validate.mjs old.html --compat v2`：新检查降为 warn；`DECK` / `FORBID` 仍是 error。
- 迁移三步：补 `data-purpose/role/layout`；反白 `#FFFFFF` 改 `var(--bg)`；1px 线改 2px；半透明改预混实色。
- `data-fidelity` 的旧值 `image` 已废弃；要栅格化写 `raster`，或用 `--raster-slides`。

## PPT 里不对，但预览是对的

这类问题一律先读 `html-contract.md`。最常见几种：

1. **文字整体偏右下** —— margin 传了 `0` 而不是数组。别绕过 `lib/emit.mjs` 自己拼。
2. **斜带变大变歪** —— 页面里用了 `translate/scale`，或拿 `getBoundingClientRect` 当盒子。转换器只读布局盒。
3. **圆形描边变成方框** —— 已修（v2）。若仍出现，检查是否用了 `border-radius` 加四边不同色的边框；圆只支持单色描边。
4. **旋转元素的边框错位** —— v3 已按元素中心旋转边框；自己拼 XML 时别假设 rotate=0。
5. **竖排文字变成小方块** —— v3 已改为 `h=ink.h`；若仍出现，检查 `writing-mode` 是否写在 flex 子项上。

## 构建失败

| 报错 | 原因 | 改法 |
|---|---|---|
| `custGeom is not a shape` | pptxgenjs 3.x | `npm i pptxgenjs@4.0.1` |
| 多边形位置偏了 | points 用了页面绝对坐标 | points 必须是相对形状自身的局部坐标 |
| PPT 打开提示"需要修复" | 动画 timing 插错位置，或 spid 对不上 | 先 `--no-anim` 出静态稿，再逐个加 `data-anim` |
| `verify-render` 报"转换失败" | LO 路径不对，或 pptx 真的坏了 | 手跑 `soffice --headless --convert-to pdf:impress_pdf_Export`，过滤器必须写全 |
| `FORBID` 让构建退出 1 | 页面里有渐变/混合/伪元素/translate 等 | 按提示删掉该属性；`--allow-forbid` 只用于定位，不用于交付 |

## 字体

输出字体名写在 PPTX 里，目标机器没有就会回退成宋体。

- 交付给别人：`--font-profile office`（微软雅黑 / Arial Narrow）。
- 自己团队都装了思源：`--font-profile source`。
- 关键大字实在不放心：给那个元素加 `data-fidelity="raster"`，**必须落在纯色区**，否则会把背景形状一起截进去。

## 真渲染阈值

`verify-render` 默认 12%。全幅网点/颗粒图在 LibreOffice 里的重采样可能制造假差异；gate 用 `--compare-width 640 --compare-height 360` 做布局级比对。若单页仍超阈值，先看 `diff-XX.png`：整块丢失/错位是硬伤，细密纹理的偏移不是。

## 联系表看不出问题？

`--sheet` 拼的是缩略图，能看出"连续同版式"和"某页偏重"，看不出字号与对比度。那两件事交给 `validate`，不要靠眼睛。
