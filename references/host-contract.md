# 宿主状态契约

何时读：宿主接入本 Skill、实现幂等检查与状态标记时。存储载体由宿主自选（会话状态、键值库、文件均可），本契约只约定键名、字段与读写时机。

## 状态键与作用域

- 键名：`resume_state.{task_id}`
- 作用域：**宿主级**（跨会话共享），多任务按 task_id 天然隔离；同一 task_id 的回调落到任何会话都能查到同一份状态
- 任务ID 复用防护：状态中记录任务创建时间戳；发现同 ID 但创建时间变化的任务视为新任务，清空旧状态后重新开始

## 字段

| 字段 | 类型 | 写入时机 | 用途 |
|------|------|---------|------|
| current_retry | int | 每次 RESUME 决策后（= decision.retry_count） | 下次 decide() 传参；未传时 decide 按 history_errors 条数兜底 |
| history_errors | list[str]（**只保留最近 10 条**） | 每次失败回调追加 | decide() 的历史错误参数（fallback 语义指纹的比对源） |
| status | resumed / failed / human_pending | dispatch 后按 DispatchResult 回填（executed=False 记 failed） | 幂等与拦截判断 |
| tx_attr / pre_action | str | 决策后 | 审计 |
| last_retry_at | ISO8601 含时区 | 每次重试前 | 排查与超时判断 |

语义指纹记录口径：主方案为 embedding 向量（由启用主方案的宿主自行序列化）；fallback 为原始错误串本身（即 history_errors），不做额外派生存储。

## 读写时机与拦截责任

1. 收到失败回调 → 读 `resume_state.{task_id}`
2. **status == human_pending → 静默丢弃本条回调**：不调用 decide、不输出摘要、不消耗资源。拦截由**宿主**在调用 decide 之前执行（decide 本身不接收该状态）
3. status == resumed（重试在途）又收到失败回调 → 用新错误**覆盖** history_errors 最后一条，current_retry 沿用，重新 decide（不排队、不另开恢复流程）
4. 调用 `decide(sig, history_errors=..., current_retry=...)`
5. dispatch 后：按返回的 DispatchResult 回填 status（executed=False 记 failed 并输出 warnings）与 current_retry；决策为 HUMAN 且触发条件为重试用尽/熔断/最终动作时，status 记 human_pending
