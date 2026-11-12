# Changelog

本文件记录 ascii-web-design 技能包的版本变更。格式参照 Keep a Changelog 中文版，版本号遵循 semver。

## [1.4.0] — 2026-10-25

本次升级分「修复」与「功能新增」两栏；`1.3.0 → 1.4.0` 为 minor（功能新增），其中含 **1 项行为变更**（见下）。

### 行为变更（有意修正，会改变已生成产物）

- **亮度→字符索引公式统一为 `floor(lum × (n−1))`**。1.3.0 里 Python 管线用 `ramp[min(n-1, int(lum*n))]`（乘 `n`），而 JS 端（`image-to-ascii.md` / `web-implementation.md` / `remotion-video.md`）用 `Math.floor(lum*(RAMP.length-1))`（乘 `n−1`）。同一契约下 `lum ∈ [0.5, 1)` 区间的字符**系统性差一级**（Python 端偏密）。1.4.0 统一为乘 `n−1`，三端 + 管线 + Remotion 现在产出同一帧同一字符。
  - 影响面：用 `scripts/ascii_pipeline.py` 在 1.3.0 生成的 `frames.json`，中间调到亮部（亮度 ≥ 0.5）的格子会**变浅一级**（字符更疏）。重跑一次管线即可对齐；不需要改任何调用参数。
  - 回归保护：`ascii_pipeline.py self-test` 新增 9 个「新旧写法必然分歧」的灰阶探针 + 纯白端点断言；`selfcheck.sh` 断言管线 / 三端骨架 / 4 篇文档 / 契约表 6 处写法一致。

### 修复

- **8 条【自动】验收项此前无脚本兑现**。§7 第 5/9/11/13/14/16/19 条与第 20 条前半（GIF 完整帧、三端齐套、ASCII-safe、浮点元数据、图表数据同源、回显消毒、Remotion 交付、网络加载卫生）现在由新增的 `scripts/verify_deliverable.py` 落地，每条都带必红用例（`self-test`）。`selfcheck.sh` 头部注释改为如实描述其覆盖范围（包自身完整性，不含用户交付物）。
- **`selfcheck.sh` 的 ramp 一致性只数文件数**（`wc -l ≥ 4`）。现在抽出 6 处实际字符串逐字比对，改成任意别的串会立即失败。
- **`selfcheck.sh` 无 ASCII-safe 断言**，而 §7 第 24 条声称已覆盖。现补：契约 ramp 码位区间、字符产物（`.txt/.ascii/.art`）无 CR/无非 ASCII、包内文本文件全 LF。
- **Math.random 红线门禁只扫 3 个文件**（`remotion-video.md` / `audio-visual.md` / `animation-patterns.md`）。现扩到 `references/` 全部 11 篇，并按围栏语言区分：`tsx/ts/jsx`（Remotion 示例）内禁用，`js`（网页示例）放行——网页端 `Math.random()` 本身合法。门禁自带必红用例（注入 tsx 样本必须被抓出）。
- **§7 第 18 条的文档命令与实际脚本不同步**：文档写 `grep -c '^version:\|^ *last_verified:'`（实测得 1，因 `version` 在 `metadata` 嵌套下），脚本用 `^ *version:`（得 2）。已同步文档文本，并新增一条自检断言「文档命令 == 脚本命令」，防止再次漂移。
- **两处悬空引用**：`image-to-ascii.md` §2.2 的「有序抖动（§3.4）」改指 `web-implementation.md §3.4`（GPU 版）与本文 §2.4（CPU 版）；`ascii-charts.md §F.0` 引用的「圆润度/浮点密度」探问点已补进 SKILL.md §0.2 技术精度组。
- **`web-implementation.md` 章节编号洞**：§3.7 之后直接跳 §3.9，§3.8 不存在。已补 §3.8「等宽校准」（用 `measureCell` 实测字符格反推 aspect），并保留原 §3.9 编号不动（多处外部引用指向 §3.9）。
- **Halftone 列数三口径冲突**：代码默认 `COLS=100`、要点写「150–240 起步」、§7 第 15 条写「≥150」，且后两者超出 §1.2 契约的 80–160。统一为：**默认 160**（契约上沿且能被 Bayer 4×4 周期整除），细粒肖像可到 240，**不得低于 80**；代码、要点、验收清单三处同文。
- **`remotion-video.md` 的 `ROWS = 40` 硬编码**未走纵横比公式。改为 `Math.round(COLS * (9/16) * ASPECT)` = 37，并注明竖屏（16:9 转 9:16）时的取值。
- **SKILL.md §1.0 的 §B–§H 枚举与实际层级不符**：饼图族与动态播放实际在 `ascii-charts.md` §F 之下，不与 §C/D/E 平级。已改为「§B 架构 → §C/D/E → §F 图表类型库（含 §F.1 饼图族 / §F.2 动态播放 / §F.3 扩展图表）→ §G / §H」。
- **`walkthrough.md` 的 HTML 骨架 `<script>` 未闭合**（全包唯一的端到端示例，照抄会得到坏文件）。已补成可直接运行：完整的字符雨实现、canvas 铺满、reduced-motion 静态帧、后台停转。
- **`terminal-templates.md` 的 Python 模板 `frames()` 是 `...` stub**。已补全：内置演示帧（开箱即跑）+ PPM(P6) 零依赖采样路径，并注明 `sample_frame()` 与 `scripts/ascii_pipeline.py` 同源、改公式须两处同步（selfcheck 会比对）。
- **时间戳字段滚动**：`_meta.json.publishedAt` 从 1.2.0 时刻更新到 2026-10-25T00:00:00Z；`SKILL.md` 的 `last_verified` 与 §1 依赖红线快照日期同步到 2026-10-25。

### 功能新增

- **`assets/templates/` 三端可复制骨架**（`ascii.html` / `ascii.py` / `ascii.c`）。此前 §7 第 9 条要求 `ls <slug>.html <slug>.py <slug>.c`，但包内一个成品都没有。三份骨架同一 ramp、同一行数公式（`round(cols × 9/16 × 0.55)`）、同一强调色 `#00FF41`、同一帧间隔 `1/12s`；HTML 版双击即开（零依赖零请求），Python 版 `--dump N` 与 C 版 `--dump N` 输出逐字节相同。`selfcheck.sh` 断言三端可编译可运行（`gcc -O2 -std=c99`、`py_compile`、Python/C 同帧一致），`verify_deliverable.py three-ends` 进一步把 HTML 内核抽到 node 里跑，做三端逐字节比对。
- **`scripts/verify_deliverable.py`**：8 个子命令（`gif-frames` / `three-ends` / `ascii-safe` / `float-meta` / `chart-data` / `sanitize` / `remotion` / `network`）+ `all` + `self-test`，逐条兑现 §7 的【自动】项。`self-test` 为每条断言构造必红用例（共 31 个用例：20 红 + 11 绿），证明门禁真的会失败。
- **视觉契约扩项（F3）**：§1.2 表新增「亮度→字符索引」（明文公式）、「帧率 / 帧间隔」（12 fps、1/12s，三端 + 管线同源）、「强调色（24-bit ANSI）」（`#00FF41` ⇄ `\033[38;2;0;255;65m`）三行；`terminal-templates.md` 补 24-bit ANSI 色表与 256 色降级，并与 §1.2 双向互链。
- **CJK / 全角网格的等宽替代方案（F4）**：`image-to-ascii.md` 新增 §2.6。给出宽度契约表（终端硬 2 格 vs 浏览器软契约）、三条可行方案（全角补位 / CJK 感知列宽 + CSS Grid / 混排行宽对齐）、五条反模式与验收补充。同时 SKILL.md §0.2 新增「等宽网格语言」探问项。
- **SVG / 矢量 → ASCII 路线（F5）**：`image-to-ascii.md` 新增 §2.5。三条路线（`<img>` 超采样栅格 + 覆盖率采样 / Path2D 点内测试 / 构建期 resvg 栅格化进管线），含细线存活的原理说明与矢量专属验收表。SKILL.md §1.0 速查表新增两行路由（SVG 素材、CJK 文案）。
- **`web-implementation.md` §3.8 等宽校准**（补齐编号洞时顺带新增的能力）：用 `measureCell()` 实测字符格 `w/h` 反推 aspect，含 Web Font 竞态、CJK 全角 2:1 校验、项目级 `VISUAL` 常量。
- **FAQ 增补 3 条**（Q25 SVG 细线消失 / Q26 CJK 错位 / Q27 换字体变形），SKILL.md 的条数声称同步为 27。
- **description 触发词补 SVG / 矢量 / logo / 中文**（对应 §2.5、§2.6 两条新路线），456 字符（< 1024 上限）。

### 有意保留

- **`_meta.json` 的 `slug` 仍为 `ascii01`，与 `name: ascii-web-design` 不一致**。这是平台条目标识，改名会被视为新条目、丢失既有发布记录与统计，故 1.4.0 沿用不改。目录名与 frontmatter `name` 仍严格一致（校验器硬门）。

### 校验

```bash
python3 /home/huayu/桌面/metaskill/skill-creator-cn/scripts/validate_skill.py "/home/huayu/桌面/优化3/ascii-web-design" --trigger
bash scripts/selfcheck.sh
python3 scripts/ascii_pipeline.py self-test
python3 scripts/verify_deliverable.py self-test
python3 scripts/verify_deliverable.py all assets/templates
```

## [1.3.0] — 2026-10-24

见上一版交付报告（本文件自 1.4.0 起建立，历史变更未回溯补录）。
