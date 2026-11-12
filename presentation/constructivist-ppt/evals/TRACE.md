# TRACE 记分卡与人工评分

> 参考：SkillHub 首发的 TRACE 评测体系（Trust / Reliability / Adaptability / Convention / Effectiveness）。
> 你给的 `skillhub.cn/tutorials#trace-evaluation` 锚点当前不存在（该页是 CLI 教程）；这里采用腾讯官方公开的维度定义，**不引用未公开的权重、总分刻度或 pass 线**。

## 五维定义（映射到本 skill）

| 维度 | 官方关注 | 本 skill 的证据 | 工具 |
|---|---|---|---|
| **T Trust** | 元数据真实、声明与实现一致、来源可信、安全边界 | rules↔代码↔文档一致；FORBID 写盘前失败；pack-html 正白名单；远程图/渐变/阴影不静默丢弃 | `selfcheck`、`validate`、`00-converter`、`08-pack-security` |
| **R Reliability** | 依赖完整、异常处理、超时/重试、运行稳定、结果一致 | 空 deck/越界/缺参照/缺依赖不静默；gate 失败即停；同 plan 两次 scaffold 字节一致 | `doctor`、`gate`、`06-structure`、`--repeats` |
| **A Adaptability** | 能力边界、触发方式、参数/环境/版本兼容 | 触发集正例/近义负例；负面 case 拒绝得体；`--compat v2` | `07-trigger`、`03-negative` |
| **C Convention** | 渐进披露、文档结构、参数 schema、示例充分 | SKILL <300 行；rules/layouts/themes/plan schema；生成文档 | `selfcheck`、`gen-*-docs --check` |
| **E Effectiveness** | 结果正确、输出完整、开箱即用、减少返工 | 结构/槽位、原生可编辑、像素差、人工视觉评分 | `01-normal`、`02-edge`、`05-delivery`、`06-structure` |

## 三层证据链

1. **静态测评**：文档、schema、依赖、目录结构。只能说明“写了什么”。
2. **确定性管线**：plan → scaffold → validate → audit → render → build → verify。说明“运行时做了什么”。
3. **真实产物 + 人工**：真实 deck、联系表、拒绝话术、视觉评分。说明“是否值得复用”。

只做第 1 层会得到“文档很漂亮但跑不起来”；只做第 2 层会得到“能跑但审美不对”。三层都缺一不可。

## 四态

| 状态 | 含义 |
|---|---|
| `PASS` | 该 case 的所有自动断言通过，且没有待人工项 |
| `NEUTRAL` | 该 case 不适用（例如未装 LO 时的真渲染） |
| `FAIL` | 至少一个自动断言失败 |
| `INCOMPLETE` | 有断言缺证据（待 agent/人工）；**不算通过** |

`--require-complete` 会把 `INCOMPLETE` 也算失败。记分卡按维度汇总：任一 case FAIL → 维度 FAIL；否则任一 INCOMPLETE → 维度 INCOMPLETE；否则 PASS。

## 人工视觉评分卡

对每一页/整份 deck 按 0–3 打分：

| 项 | 0 | 1 | 2 | 3 |
|---|---|---|---|---|
| 主斜线 | 没有或只是装饰 | 有但不主导 | 主导且与标题咬合 | 方向本身就是论点 |
| 层级 | 看不出主次 | 有主次但含糊 | 一眼能指出最重块 | 尺度差与面积差互相加强 |
| 色板 | 超过四色/主题外 | 主题内但面积平均 | 四色且爆点克制 | 面积配比与内容情绪一致 |
| 字阶 | 掉出阶梯/标签承载句子 | 字号对但层级弱 | 标题/正文/标签清楚 | 字与几何咬合 |
| 遮挡/溢出 | 文字被盖/出界 | 擦边 | 安全区内、无遮挡 | 出血与安全区都刻意 |
| 跨页节奏 | 连续同版式 | 有变化但突兀 | 联系表上节奏成立 | 翻页有明确的“标点” |

**通过线**：均值 ≥2，且主斜线/层级/遮挡三项不得为 0。评分人需看 `render --sheet` 的联系表，不能只看单页。

## 当前 v3 状态

| 维度 | 状态 | 说明 |
|---|---|---|
| T | PASS | selfcheck 16/16；00-converter 18/18；08-pack-security 7/7；FORBID 全部在写盘前报出 |
| R | PASS | 00/02/04/06 全 PASS；scaffold 字节一致；空 deck/越界/缺参照会失败 |
| A | INCOMPLETE | 03/07 需要真实 agent 回复与人工判读 |
| C | INCOMPLETE | 05 的交付话术待 agent；其余生成文档同步 |
| E | INCOMPLETE | 05 的交付话术待 agent；视觉评分卡待人工 |

> 这份表由 `--score` 的自动结果 + 人工项共同维护；`INCOMPLETE` 不是“差不多通过”。
