# SELF-CHECK — ui-design 4.5.1

> 生成时间：2026-11-12。所有读数来自本机实跑；条件写在每项旁边。
> 本文件是 **5 轮 skill-creator-cn 迭代后的最终自检**；逐轮证据在
> `../reports/round-1.md` … `round-5.md`，汇总在 `../TRACE-REPORT.md`。

## 0. 包体

| 项 | 值 |
|---|---|
| 文件数 | 195（预算 ≤200） |
| 体积 | 5.9 MB |
| SKILL.md | 457 行（validator；<500） |
| 压缩包 | ≤200 files（当前 195） |
| references | 28 章（00–27） |
| scripts | 8 个 |
| evals | 8 审计 + 6 动效 + 触发/评分/工作流 |
| golden | 3 HTML + 3 桌面 PNG |
| binaries | 仅 3 张 golden 桌面 PNG |

## 1. 结构 / 触发

| 检查 | 命令 | 结果 |
|---|---|---|
| 校验器自测 | `validate_skill.py --self-test` | 必红全过 |
| 技能校验 | `validate_skill.py . --trigger` | 通过 |
| 目录名 == name | 自动 | `ui-design` = `ui-design` |
| description | 自动 | 682 字符，无尖括号 |
| 版本三处一致 | 自动 + `check_assets` | 4.5.1 |
| 触发 | `run_trigger_eval.py` | **44/44**（正 28 / 负 8 / 近邻 8） |

警告 1 项：SKILL.md 估算词数 >1500；这是内容密度，不是结构错误。

## 2. 审计金标准

| 检查 | 命令 | 结果 |
|---|---|---|
| 审计器自测 | `audit.py --self-test` | **35/35** |
| 8 个金标准（带品牌） | `--brand "#0f766e"` + `score.py` | **8/8** |
| 05-landing（不带品牌） | 同上，不传 `--brand` | **0/1**（漏品牌漂移） |

> 8/8 只在带 `--brand` 时成立；不带是 7/8。`score.py --self-check` 验证评分器，
> 不验证审计器。

## 3. 动效静态扫描

| 检查 | 命令 | 结果 |
|---|---|---|
| 扫描器自测 | `check_motion.py --self-test` | **13/13** |
| 6 组夹具 | `check_motion.py evals/motion --expect` | **6/6** |
| 17 个组件/merged | `check_motion.py <dir>/index.html` | **0 P1**；**2 P2** |
| 所有 shipped HTML | 26 手法 + 8 研究 + 3 golden + 17 组件 | **0 P1**；**8 P2** |

P2 说明（均为无限循环/降级 cube，且有 reduced 或暂停）：

- components：`12-editorial-motion`（1.4s 无限文字波）、`14-webgl-object`（CSS 降级 cube）。
- site-techniques：`11-blend-cursor`、`17-shimmer-text`、`24-conic-gradient`。
- site-studies：`04-midnight`。
- golden：`aperture`（状态点 pulse）、`studio`（环境循环）。

扫描器跟随本地 `<link>`/`<script src>`、query-string 与 `@import`；M-001 覆盖 CSS
keyframes/transition 与 WAAPI；JS 直接写布局属性列为人工项（静态定位合法）。

## 4. 运行时探针

```bash
PLAYWRIGHT_PATH=<...>/playwright/index.mjs BROWSER_PATH=/usr/bin/microsoft-edge \
  node scripts/verify_motion.mjs --dir assets/motion/code/components
PLAYWRIGHT_PATH=<...>/playwright/index.mjs BROWSER_PATH=/usr/bin/microsoft-edge \
  node scripts/verify_motion.mjs --dir assets/motion/code/merged
```

| 组 | 结果 | 条件 |
|---|---|---|
| 12 复合组件 | **12/12** | Edge headless + ANGLE |
| 5 补缺组件 | **5/5** | 同上 |
| 合计 | **17/17** | 1280/768/375；console 0；无溢出；strict reduced |

探针必须看到**变化**：`frameDelta>0 || animationDelta>0 || statsChanged`；加载时动画
必须 `running`。以下对抗输入均按预期失败：

- `__rfStats={frames:5}` 的静态页 → FAIL。
- `animation-play-state:paused` → FAIL。
- 假 stats + 隐藏 body → FAIL。
- reduced 下有限 transition 继续 → FAIL。
- query-string CSS `transition:width` → M-001 命中。
- `@import` CSS `transition:left` → M-001 命中。
- comment-only reduce block → M-002 命中。

**边界**：headless rAF 时间不是真机性能；只证「能画/循环/终态」。

## 5. 资产一致性

`python3 -I scripts/check_assets.py` → **0 errors / 0 warnings**。

覆盖：14 原型 ↔ 卡片、84 品牌 ↔ index、motion index 每条 path 存在、
17 组件目录 ↔ 索引双向、meta `verified: true`、5 文件契约、无 `sources[].path`、
28 手法页、8 研究页、3 golden、无 OPL/绝对路径、运行时无外部 URL、版本三处一致。

## 6. 视觉

- 3 个 golden 页在 1280/390 重新渲染；截图在 `assets/golden/`。
- R2 盲评（独立评审，A/B 随机）：
  - Acoustic：GREEN **4.6** vs RED 4.1。
  - Journal：GREEN **4.4** vs RED 4.1。
  - 反例：整屏高程图版本 3.4，被拒绝，规则写回「图表不是英雄」。
- 审美为主观判断；rubric + golden + 用户复核三层，不声称客观。

## 7. 三库路由（docs-verified）

| 库 | 实测版本 | 证据 |
|---|---|---|
| HeroUI | **3.2.7** | `list_components.mjs` → 73；Button docs/theme 正常 |
| Mantine | **9.8.0** | `npm view`；installed form/combobox/custom 技能对齐 |
| shadcn | **4.23.0** | `--help` / `add --help` / `apply --help` / `view` / `info --json` |
| HeroUI MCP | **1.1.4** | `npm view` |

**未验证**：没有建真实 React/Vite 项目跑安装与渲染；MCP 未真正握手。
使用前以项目 `package.json`、`info`、`list_components`、`list_items` 为准。

## 8. 未验证 / 已知缺口

- 302 复刻是静态种子（0 rAF / 0 shader），不是动效证据。
- 19 份原站引擎、57 套结构来源、302 资产/截图未打包；未逐份核对许可证。
- 品牌文档是第三方观察，不是官方规范；商用前核对商标政策。
- OPL 派生卡片只保留区间，未取得再分发授权；商用前联系 OPL。
- 运行时只测 Edge/Chromium；Safari/Firefox/真机未测。
- 8 个 P2 是已知的无限循环/降级 cube；不是 P1。
- 8 方向手势、inertia、WebGL context loss、Esc/Space/Enter 仍是人工项。
- 19 个原站引擎在 SOURCE-LEDGER 记为 provenance；未打包。

## 9. 结论

4.5.1 在**已声明的检查面**内通过：结构、审计、静态动效、运行时、资产一致性、
视觉基准、三库文档核对。未覆盖的面逐条列在上文；不声称「零缺陷」。
