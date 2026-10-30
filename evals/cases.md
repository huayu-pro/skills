# Auto-Resume Evals

最小验证集。执行方式：人工走查或脚本注入模拟错误通知，验证 SKILL.md 中的决策逻辑是否正确。

## E01: 网络超时 - 瞬态错误 - 只读任务

- **任务类型:** subagent
- **错误:** `Connection timeout: gateway timeout after 30s`
- **事务属性:** 只读（推断）
- **阶段:** Processing
- **预期:** 进入全抖动退避，最多 3 次；恢复成功则输出摘要，失败则转人工

## E02: 429 Rate Limit - 瞬态错误 - 可逆任务

- **任务类型:** media
- **错误:** `HTTP 429: Too Many Requests, retry after 60s`
- **事务属性:** 可逆（推断）
- **阶段:** Processing
- **预期:** 全抖动退避，最多 3 次；恢复前不执行撤销（media 可覆盖重提交）

## E03: 401 Token 过期 - 致命错误 - 只读任务

- **任务类型:** subagent
- **错误:** `HTTP 401: Invalid or expired token`
- **事务属性:** 只读（推断）
- **阶段:** Init
- **预期:** 立即放弃，直接通知用户；不进入重试流程

## E04: 子代理输出格式错误 - 逻辑错误 - 只读任务

- **任务类型:** subagent
- **错误:** `Output validation failed: response format does not match expected schema`
- **事务属性:** 只读（推断）
- **阶段:** Processing
- **预期:** 重试 1 次，附加纠错 prompt；仍失败则转人工

## E05: 同类错误重复出现 - 瞬态错误 - 只读任务

- **任务类型:** workflow
- **错误:** `node X failed with timeout`（历史错误与当前错误为同一文本；错误串含 timeout，实现分类为瞬态）
- **事务属性:** 只读（推断）
- **阶段:** Processing
- **预期:** 语义相似度超阈值（同一错误类型前提下，阈值数值以 SKILL.md 为准）→ 熔断，不再重试；直接转人工

## E06: 付款操作失败 - 致命错误 - 最终动作

- **任务类型:** workflow
- **错误:** `Payment gateway declined transaction`
- **事务属性:** 最终动作（推断：prompt 含"付款"关键词）
- **阶段:** Finalizing
- **预期:** 绝不重试；直接转人工审核

---

## 补充说明（已补全）

### A. `check_pending_tasks` 真实返回格式样例
宿主 Agent 调用该工具后，平台返回当前会话所有后台任务状态。用于提升事务属性与阶段推断准确率：
```json
{
  "tasks": [
    {
      "task_id": "task_8f2a",
      "type": "subagent",
      "thread_id": "thr_11",
      "status": "failed",
      "error": "Connection timeout: gateway timeout after 30s",
      "phase": "Processing",
      "created_at": "2026-07-07T23:01:00+08:00"
    }
  ]
}
```
字段说明：`type` ∈ {subagent, workflow, media}；`status` ∈ {pending, resolved, failed}——注意 pending/resolved 属任务生命周期状态，**不得**作为失败信号传入本 Skill（仅 failed 及失败回调的 timeout/interrupted 可传入）；`error` 为原始错误串，用于语义指纹；`phase` 缺失时按默认规则推断。

### B. 语义相似度计算方案与 fallback
- **主方案（有 embedding）：** 对「错误类型 + 错误摘要」做向量化，计算余弦相似度；阈值数值以 SKILL.md 的 Core Principles / Retry Policy 为准（单一事实源，本节不重复数值），达到阈值判定为同类错误，触发熔断。
- **fallback（无 embedding）：** 取错误摘要的关键词集合（去停用词、保留错误码与核心动词；中文按相邻二字组入集），计算 Jaccard 相似度；阈值同样以 SKILL.md 为准，并在恢复摘要中标注 `semantic=fallback`。长数字/十六进制 ID（req_id、时间戳等）在二次比对时归一化，防止变量片段压垮相似度导致漏熔断。
- **防误熔断：** 仅在「错误类型相同」前提下比较相似度；类型不同即使文本相似也视为新错误。

### C. 阶段（Init / Processing / Finalizing）的平台信号定义
| 阶段 | 平台信号 | 推断兜底 |
|------|---------|----------|
| Init | 任务已创建但未进入实质处理（首个 agent 节点未执行 / 生成请求未提交） | 根本未启动即按 Init |
| Processing | 任务执行中（子代理已对话 / 工作流节点运行中 / 媒体生成渲染中） | 默认阶段 |
| Finalizing | 接近完成（输出已生成待落盘 / 工作流末节点 / 媒体已渲染待回传） | 已输出接近完成即按 Finalizing |
若平台不提供阶段，默认 `Processing`，推断结果在摘要标注。

---

## 真实联调演练（E07 · 本平台实测）

> 本记录产生于 1.0.x 时代。按 1.1.0+ 的九行摘要模板回填：阶段 Processing、前置动作 none、恢复动作 resume、重试次数 1（计划值口径）。

环境：HanaAgent 会话内真实 subagent 实例。验证「创建 → 模拟失败信号 → decide → 真实续跑」全链路。

- **创建真实实例：** `subagent(agent=can-2, access=read, task="回复一句陶渊明诗句")`
  - 返回真实 `threadId = subagent-1783437164932-040752`，首轮输出 `采菊东篱下，悠然见南山。`
- **模拟后台失败信号（<hana-background-result>）：**
  - 错误：`Output validation failed: response format does not match expected schema (expected JSON)`
  - 任务类型：subagent｜阶段：Processing
- **decide() 决策：**
  - 错误分类：`logical`｜事务属性推断：`readonly`｜动作：`resume`｜重试次数：1
  - 备注：计划退避后重试，附纠错 prompt
- **真实续跑：** `subagent_reply(threadId, 纠错指令)` 注入「请按 JSON 格式重新回答」
- **结果：** 子代理返回 `{"poem": "采菊东篱下，悠然见南山", "author": "陶渊明"}`，符合预期 schema。

**结论：** decide → adapter.dispatch → 真实 `subagent_reply` 链路在真实平台工具下闭环可用。
`adapter.py` 中宿主 handler 的签名（`subagent_reply(threadId=, task=)`、`workflow(resumeFromRunId=)`、`media_generate_image(**params)`）与平台工具一致，可直接注入使用。

## 待补充（仍开放）
- 更多跨任务类型的真实 `check_pending_tasks` 多任务并发样例。

## 触发评测说明（evals/trigger_cases.json）
- 该文件是**词法级冒烟**用例（概念组命中打分，阈值见文件内 `recommended_threshold`），模型级触发以 SKILL.md frontmatter 的 description 为准。
- 已知词法局限与说明：metaskill 评测器（run_trigger_eval.py）为**整词匹配**，「任务 4290 次重试」类数字串本就不会误命中 `429` 概念词（复核 F1 实测澄清）；英文用例依赖小写写法。`should_not_trigger`（负模式一票否决）与 `near_neighbor`（概念不足）的区分标准为——前者命中禁止模式，后者概念覆盖不足但话题相近。判定存疑时以人工/子代理走查为准。
