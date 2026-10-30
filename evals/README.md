# evals — 验证 skill 本身，而不是某一张 deck

评测方法对齐 SkillHub TRACE 的三层证据链：**静态测评（写了什么）→ 确定性管线（运行时做什么）→ 真实产物/人工（是否值得复用）**。这里不假装能全自动判断审美；脚本只断言可观察产物，审美留给评分卡。

## 怎么跑

```bash
node evals/run.mjs --list
node evals/run.mjs --pipeline             # 确定性断言，改回归用
node evals/run.mjs --pipeline 06-structure
node evals/run.mjs --score                # TRACE 四态汇总
node evals/run.mjs --agent <case> --dir <产物目录>
node evals/run.mjs --update-baseline <case> --reason "…" [--repeats N]
```

- `INCOMPLETE` 不等于通过；`--require-complete` 会把待人工也算失败。
- `--repeats N` 只对可重复的 case 有意义（如 scaffold 确定性）；agent 行为仍靠人工。

## Cases

| case | 维度 | 验什么 |
|---|---|---|
| `00-converter` | T / R | 全部 FORBID 在写盘前报出；不留下 pptx；无 ReferenceError |
| `01-normal` | E / C | 结构完整、验证链跑通、文字真可编辑、形状原生 |
| `02-edge` | R / E | 色板豁免、圆描边、单行正文 `wrap=true`、竖排 `h>w` |
| `03-negative` | A | 不该出活时不出活；拒绝是否得体（人工） |
| `04-recovery` | R | pipeline 验检测；agent 模式验修复；不再自动修 fixture |
| `05-delivery` | C / E | 预览数 == pptx 页数、新鲜联系表、体积、真渲染 |
| `06-structure` | R / C / E | plan→scaffold→validate→build、scaffold 确定性、坏 plan、plan↔deck 漂移 |
| `07-trigger` | A | 正例与近义负例（人工/agent 记录） |
| `08-pack-security` | T | pack-html 正白名单、隐藏路径、非 HTML 输入 |

## TRACE 记分卡

| 维度 | 证据 |
|---|---|
| **T 信任** | selfcheck、FORBID 写盘前失败、规则↔代码↔文档一致、pack-html 正白名单、无静默丢弃 |
| **R 可靠** | 空 deck/越界/缺参照/缺依赖不静默、gate 失败即停、scaffold 字节一致 |
| **A 适用** | 触发集、负面 case、能力边界写清 |
| **C 规范** | 三层披露、SKILL 行数上限、plan/layout/rules schema、生成文档 |
| **E 有效** | 结构/槽位、原生可编辑、像素差、人工视觉评分 |

状态：`PASS / NEUTRAL / FAIL / INCOMPLETE`。**证据缺失即 INCOMPLETE**，不折算成通过。详细定义与人工评分卡见 `TRACE.md`。

## Baseline 政策

`--update-baseline <case> --reason "…"` 会写 `baselines/<case>/metrics.json`，并在 `baselines/CHANGELOG.md` 追加一行。**阈值随基线偷偷漂移**是所有验收体系最失效的方式；没有 reason 的基线更新会被拒绝。

当前基线：

- `v2/` — 改版前快照：10 页样例、163,720 B、117 runs、151 sps；`verify-pptx` 最大 3.44%，`verify-render` 最大 5.85%。注：v2 的 02 “单行正文”是假绿，`wrap` 仍按 `ink.lines` 判断。
- `v3/` — 结构化、FORBID 写盘前失败、15 个版式、TRACE 记分卡；指标见 `baselines/v3/metrics.json`。

## 为什么有些断言是人工

`03-negative` 的“拒绝是否得体”、`07-trigger` 的“该不该触发”、`05-delivery` 的“联系表观感”、视觉评分卡的“主斜线是否有论点”，脚本判不了。硬编关键词只会教会 agent 糊弄；这些项明确标 `manual` / `INCOMPLETE`，不伪装成 pass。
