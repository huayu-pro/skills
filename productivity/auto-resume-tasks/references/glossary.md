# 中文术语对照表

按需查阅：阅读 SKILL.md 或 `scripts/resume_decide.py` 遇到术语疑问时再读本表。

| 英文术语 | 中文含义 | 说明 |
|---------|---------|------|
| subagent | 子代理 | 派生的对话式子智能体任务 |
| workflow | 工作流 | 确定性编排脚本（agent 节点编排） |
| media | 媒体生成 | 图片/视频生成任务 |
| transient error | 瞬态错误 | 临时故障，值得重试 |
| fatal error | 致命错误 | 参数/权限/资源问题，立即放弃 |
| logical error | 逻辑错误 | 死循环/幻觉/格式错，有限重试 |
| full jitter backoff | 全抖动退避 | 随机化重试窗口防惊群 |
| semantic fingerprint | 语义指纹 | 用语义相似度判重，防死循环 |
| transaction attribute | 事务属性 | 动作副作用等级（只读/可逆/可补偿/最终） |
| pre-action | 前置动作 | 重试前的撤销/补偿动作（none/undo/compensate） |
| circuit break | 熔断 | 同类错误超阈值后停止重试 |
| human_pending | 待人工处理 | 重试用尽/熔断/最终动作后的终态；宿主据此在后续回调进入决策前静默丢弃 |
| prompt hint | prompt 片段 | 触发任务时的原始 prompt 片段，用于事务属性推断 |
