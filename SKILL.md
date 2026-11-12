---
name: auto-resume-tasks
description: 后台任务失败自动恢复决策。Use when：收到子代理/工作流/媒体生成等后台任务失败、超时或中断的信号、回调或用户求助，需要判断自动重试、续跑、放弃还是转人工时（如"后台任务失败了怎么办"）。按错误分类（瞬态/致命/逻辑）与动作事务属性（只读/可逆/可补偿/最终动作）决策，含全抖动退避防惊群、语义指纹熔断防死循环。Exclude：前台同步代码的常规调试与修 bug、用户明确要求放弃或手动处理的任务、系统运维层面的进程/服务重启与定时任务排查、仅要求分析总结或汇报失败原因而不做恢复决策。
metadata:
  version: 1.2.1
  updated: 2026-10-25
---

# Auto-Resume on Failure

被动响应型决策规范：不主动轮询，仅在宿主收到后台任务异常信号时被调用；默认不启用，需宿主在后台任务处理钩子中显式接线。SKILL.md 与 `scripts/resume_decide.py` 为同一决策逻辑的双源，改任一侧后必须运行 `python3 scripts/check_consistency.py` 对账并跑 pytest 回归。

## 激活与接线

**触发时机**：宿主收到后台任务失败/超时/中断信号或回调、状态查询返回 `failed`、后台任务状态异常或长时间无响应。信号按下述字段传入，按 Workflow 执行并输出【恢复摘要】。

### 通用信号字段

| 字段 | 取值 | 缺失时处理 |
|------|------|-----------|
| 任务类型 | subagent / workflow / media | 必填 |
| 任务ID | 平台提供的 threadId / taskId | 必填 |
| 状态 | failed / timeout / interrupted（仅失败信号） | 必填；pending / resolved 属任务生命周期状态，不得传入 |
| 错误摘要 | 原始错误串，用于语义指纹 | 必填 |
| 已执行阶段 | Init / Processing / Finalizing | 默认 Processing |
| 事务属性 | readonly / reversible / compensatable / final | 按「事务属性推断」补全 |
| 任务 prompt 片段 | 触发任务时的原始 prompt 片段 | 可选；缺失时无法识别最终动作关键词 |

### 最小触发模板（宿主调用本 Skill 的 prompt）

```
收到后台任务异常，请按 auto-resume-tasks 规范处理：
任务类型={type} 任务ID={id} 状态={status} 错误={error_summary} 阶段={phase} prompt提示={prompt_hint}
先判断错误分类与事务属性，再决定重试/放弃/转人工，并输出【恢复摘要】。
```

## 平台适配示例（HanaAgent）

决策逻辑与平台无关，恢复出口因平台而异；其他平台按同样方式接入：

| 任务类型 | 重试/续跑工具 | 备注 |
|---------|-------------|------|
| subagent | `subagent_reply(threadId, 纠错/续跑指令)` | 逻辑错误需附纠错 prompt |
| workflow | `workflow(resumeFromRunId=taskId)` | 平台不支持时通知用户 |
| media | 重新提交生成请求（含原始参数） | 覆盖式重提交；原始参数由宿主取回 |
| 状态查询 | `check_pending_tasks` | 仅在信号不足以判断时调用 |

HanaAgent 以 `<hana-background-result>` 标签送达上述字段（中文键名）；`check_pending_tasks` 样例见 `evals/cases.md` 补充说明 A；宿主经 `scripts/adapter.py` 注入 handler 接入。

术语对照见 `references/glossary.md`；反模式与 FAQ 见 `references/anti-patterns.md`，首次执行前必读。

## Core Principles

- **错误归因优先**：不按进度百分比判断，而按错误类型决定是否重试
- **动作事务属性优先**：恢复前先判断动作副作用等级，最终动作绝不自动重试
- **语义指纹防循环**：仅在同一错误类型前提下比较语义相似度，超阈值（余弦 > 0.9 主方案 / Jaccard ≥ 0.8 fallback）即熔断
- **全抖动退避**：随机化重试时间窗口，防止惊群效应
- **静默优先**：能自己解决的不打扰用户，只有需要人工决策时才通知，避免对 doomed task 浪费资源

## Error Classification

### 瞬态错误（值得重试）
- 网络超时、连接失败
- 429 Rate Limit / 503 Service Unavailable
- 模型服务暂时不可用

### 致命错误（立即放弃）
- 400 Bad Request / 参数校验失败
- 401/403 权限不足 / Token 过期
- 404 资源不存在
- 支付/交易类失败（兜底：转人工确认扣款状态；命中 401/400 等致命码的按致命放弃——请求未成功、未扣款）

### 逻辑/内容错误（有限重试）
- 子代理陷入死循环 / 幻觉 / 输出格式错误
- 工作流节点逻辑异常

无法归类的错误默认按瞬态重试（宁可重试，不轻易放弃）；策略见下方矩阵与 Retry Policy。

## Action Transaction Classification

恢复任何任务前，先判断该动作的事务属性，优先级高于阶段-错误矩阵：

| 属性 | 定义 | 前置动作 | 恢复策略 |
|------|------|---------|---------|
| 只读 (Read-only) | 查询/检索，不改变外部状态 | 无 | 可放心重试，适用全部退避策略 |
| 可逆 (Reversible) | 改变状态但有确定性撤销操作（如创建草稿后删除） | 先撤销清理残局（media 除外：覆盖重提交） | 清理残局后全抖动退避重试 |
| 可补偿 (Compensatable) | 改变外部状态且无法物理撤销（如邮件已递送、通知已群发） | 先触发补偿工作流（如补发勘误） | 补偿完成后全抖动退避重试 |
| 最终动作 (Final/Irreversible) | 不可逆转的关键操作（如付款、删库、部署） | 不进入恢复流程 | 任何错误都绝不重试，直接转人工审核 |

## Workflow

### 1. 解析通知
从信号中提取通用信号字段；仅在信息不足以判断时才调用状态查询工具。

#### 事务属性推断（缺失时）
- **最终动作关键词对所有任务类型生效**（命中即判 `final`，优先于默认值）；未命中时 `media` → 默认 `reversible`（可覆盖重提交），`subagent` / `workflow` → 默认 `readonly`
- `workflow` 确有多阶段副作用（写入文件、发送通知等）时，由宿主依据平台任务详情显式传入 `tx_attr`，不做关键词猜测
- 最终动作关键词：付款、支付、部署、删库、删除、提交、发送、send、deploy、pay、delete（中英任一命中即视为最终动作）

推断结果必须在恢复摘要中显式标注，供后续审计。

### 2. 幂等检查与语义指纹
- 会话内查重该任务ID；human_pending 拦截与状态读取按宿主状态契约执行（`references/host-contract.md`）
- 计算错误语义指纹：仅在**同一错误类型**的历史错误间比较语义相似度（主方案余弦 > 0.9；fallback Jaccard ≥ 0.8 并标注 `semantic=fallback`）
- 超阈值 → 熔断，不再重试，直接转人工

### 3. 事务属性优先判断（确定前置动作）
前置动作按上方事务属性表确定：可逆→undo、可补偿→compensate、其余→none（media 例外：覆盖重提交，为 none）。前置动作与恢复动作一并写入【恢复摘要】。

### 4. 阶段-错误联合判断（仅对非最终动作）

| 阶段 | 瞬态错误 | 致命错误 | 逻辑错误 |
|------|---------|---------|---------|
| Init | 全抖动退避，最多 3 次 | 立即放弃 | 重试 1 次 |
| Processing | 全抖动退避，最多 3 次 | 立即放弃 | 重试 1 次 |
| Finalizing | 全抖动退避，最多 2 次 | 立即放弃 | 重试 1 次 |

### 5. 全抖动退避公式

```
t_calculated = min(t_max, t_base * 2^attempt_count)
t_retry = Random(0, t_calculated)
```

- t_base = 5s, t_max = 60s
- attempt_count 从 0 起算：首次重试窗口为 [0, t_base]
- 每次重试时间在 [0, 当前最大退避时间] 内均匀随机，多任务并发时自动打散
- 服务器返回 Retry-After 提示时，实际等待取 max(t_retry, Retry-After)

### 6. 恢复动作（工具名见适配示例）
- **subagent**：先执行前置动作，再发送续跑指令——瞬态错误发简单重试指令；逻辑错误附失败日志摘要 + 纠错 prompt；历史对话超平台上下文预算约一半时先压缩为关键摘要再注入（宿主执行）
- **workflow**：平台支持则按 runId 续跑，否则通知用户平台限制
- **media**：重新提交生成请求（覆盖式）；原始参数由宿主按任务ID从平台记录取回

### 6.5 恢复日志输出
每次恢复尝试后，立即向会话上下文输出结构化摘要（与 `resume_decide.py` 的 `Decision.summary()` 一致）：

```
【恢复摘要】
任务类型：{type}
任务ID：{id}
错误类型：{error_type}
事务属性：{transaction_type}
阶段：{phase}
重试次数：{retry_count}
前置动作：{none | undo | compensate}
恢复动作：{resume | abort | human}
备注：{note，含 semantic=fallback 标注（如适用）}
```

该摘要仅供当前会话复盘，不持久化。字段口径：
- 重试次数为计划进行的第几次重试（首次为 1），已执行次数由宿主回填；前置动作仅对 `resume` 有意义，其余填 `none`
- `abort` = 致命终止无需人工介入；`human` = 需人工决策（重试用尽、语义熔断、最终动作）

### 7. 升级通知（仅必要时）

触发条件（满足其一）：达到重试上限、致命错误、同类错误相似度超阈值重现、任务涉及最终动作、累积 token 消耗超阈值（建议默认 20000 token/任务，宿主可配）。通知格式：

```
【任务中断需人工处理】
任务：{type} / {id}
原因：{error_type} - {reason}
动作属性：{transaction_type}
阶段：{phase}
已自动恢复：{retry_count} 次
建议：{suggestion}
```

### 8. 状态标记

恢复尝试后按**宿主状态契约**（`references/host-contract.md`）记录：键 `resume_state.{task_id}`（宿主级、跨会话、按 task_id 隔离），字段 current_retry、history_errors（最近 10 条）、status（resumed / failed / human_pending，dispatch 后按 DispatchResult 回填）等。标记为 `human_pending` 后，宿主在后续同一任务回调进入决策前直接静默丢弃（拦截责任在宿主）。

## Evals

快速自检：`python3 scripts/resume_decide.py`（内置 E01–E06 自检）。
E01–E07 详例、平台样例、阶段定义与联调记录见 `evals/cases.md`；触发冒烟用例见 `evals/trigger_cases.json`（词法级，模型级触发以 description 为准）。

## Retry Policy

- 瞬态错误：最多 3 次（Finalizing 阶段最多 2 次），全抖动退避
- 逻辑错误：最多 1 次
- 致命错误：0 次
- 最终动作：0 次，直接转人工
- 同类错误语义相似度超阈值（余弦 > 0.9 / fallback Jaccard ≥ 0.8）→ 直接熔断
- 标记为 `human_pending` 后，不再自动处理

## 维护与一致性

- **双源对账**：改任一侧后运行 `python3 scripts/check_consistency.py`（十项：矩阵/退避/阈值/摘要模板/关键词/Retry Policy/旧称/信号字段/错误分类/推断锚点），不一致退出码 1。
- **回归**：`pytest scripts/` 全绿。
- **打包**：剔除 `.pytest_cache/` 等缓存后再打包。
