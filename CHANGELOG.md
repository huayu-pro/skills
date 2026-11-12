# Changelog

## 1.2.1 (2026-10-25)

残余风险整改轮：针对 1.2.0 TRACE 报告第五节的残余风险逐项修复（全部归修复栏，patch 升版）。

### 修复

- **R1 支付兜底/致命分类优先级重排**：致命错误判断前移至支付兜底之前——含 payment 字样但命中 401/400 等明确致命码的按致命放弃（请求未成功、未产生扣款），不再一律涌向人工；其余支付类错误（含超时子类）仍转人工确认扣款状态。SKILL.md 致命节与 anti-patterns FAQ 口径同步
- **R1+ 支付兜底中英文均识别**（复核 F3，中危）：原仅匹配英文 `payment|transaction declined`，中文「订单支付失败」「扣款异常」「交易失败」漏识别并被默认瞬态自动重试（重复扣款风险）。现补中文词表；英文不含裸 `declined`（connection declined 属瞬态）
- **R2 中文近义归一化**：语义指纹比对前将「没有→无」「无法→不能」归一并去除「了吗呢的」语气助词——「网关没有响应 / 网关无响应」类近义改写此前 Jaccard≈0.5 漏熔断，现可熔断；确认不引入误熔断（"请求超时 vs 请求失败"仍不相似）
- **R3 ID 归一化精确化**：`_normalize_ids` 要求长 token 至少含一位数字（前瞻断言），"facade" 等纯 hex 字母英文词不再被误归一为 `<id>`
- **R4 触发评测说明更正**（复核 F1）：复核实测 metaskill 评测器为**整词匹配**，「4290」类数字串本就不会误命中 `429` 概念词，此前记录的"收窄为 `429 ` 规避误命中"因果不成立，已回退并在 cases.md 记录真实机制
- **R5 门禁新增第 10 项「事务属性推断锚点」**：历史缺陷"推断规则曾三方分叉且门禁零覆盖"的制度性封堵——文档锚点（"对所有任务类型生效"/默认值/显式传入 tx_attr）+ **代码行为探针**（门禁直接调用 `infer_tx_attr` 验证 media→reversible、subagent/workflow→readonly 默认值）双向对账；配 2 个必红用例（文档锚点被改、代码默认行为漂移均必须报警）
- 已知局限记录补全：否定前缀豁免窗口为 4 字符（窗口外仍保守转人工）、fallback 词面粒度（近义改写由重试上限兜底）→ anti-patterns FAQ

## 1.2.0 (2026-10-25)

二轮深审（脚本线 / 门禁线 / 文档线，三路只读审计均以可运行反例证实）后的修复版。

### 修复

- **G1 中文语义指纹失效**（高危）：`_keywords` 原本只匹配 `[a-z0-9]+`，纯中文错误串关键词集为空 → 熔断对中文 100% 失效。修复：中文按相邻二字组入集，英文逻辑不变；补中文熔断单测
- **G2 dispatch 多路径静默失败**（高危）：handler 缺失时 RESUME 只打印摘要、ABORT/HUMAN 完全静默、undo/compensate 缺失时静默跳过前置动作仍续跑。修复：dispatch 返回 `DispatchResult`（executed/pre_action_done/warnings）；前置动作缺失或抛异常一律**拒绝续跑**转 on_human；所有路径输出摘要与告警
- **G3 重试上限形同虚设**（高危）：文档示例不传 current_retry（恒 0）→ max_retry 永不触发；req_id/时间戳变量片段压垮 Jaccard → 漏熔断。修复：decide() 未传 current_retry 时按 history_errors 条数兜底；semantic_similar 增加长 ID 归一化二次比对；adapter 示例与宿主状态契约明确传参
- **入口防呆前移**：TaskSignal `__post_init__` 归一化校验（裸串 task_type/phase 非法值响亮报错、status strip+lower、prompt_hint/error None 容错），不再出现"handler 已执行后才崩溃"或"小写 phase 静默查空矩阵误判"
- **错误分类补漏**：429/503 补 `\b`（"5039" 不再误命中）；多行错误文本空白归一化（换行不再把 logical 拆成默认瞬态）；"invalid token" 语序补模式
- **最终动作关键词精确化**：英文改词边界匹配（resend/deleted 不误报），中文加否定前缀豁免（撤销删除/取消支付不升级 final）
- **支付兜底从 ABORT 改为 HUMAN**：转人工确认扣款状态；payment+timeout 不再被直接放弃
- **空串/纯符号错误** → HUMAN（错误信息缺失，无法归因）；current_retry 负数归零；jitter_backoff 大参数防溢出；"timed out"→"timeout" 归一化（1.1.0 已做）保持
- **退避口径**：decide() 的 note 改报告窗口"0~Ns（全抖动随机）"，消除"计划值≠实际等待"的双采样不一致；Retry-After 协调实装进 adapter（解析错误串取 max 等待，可测），文档声称不再无双源
- **`__main__` 自检改为断言式**：回归时退出码 1，不再静默通过

### 门禁加固（第 9 项 + 反诱饵）

- 新增第 9 项「错误分类与状态枚举对账」：致命/瞬态错误码双向对账、支付兜底行、"未知默认瞬态"、状态枚举、逻辑示例齐全性
- 反诱饵：所有文档侧检查从"取第一处匹配"升级为"扫描全部匹配并要求一致/唯一"（诱饵行/诱饵块/重复口径不再能顶替或共存）
- 矩阵双向对账：文档侧多出/缺失阶段行、行列数异常、allow 标志篡改全部纳入
- 阈值/参数检查堵洞：余弦阈值行级数值枚举（0.9→0.95 不再逃逸）、百分数写法拒绝、退避参数第二处冲突值、Retry Policy 行绑定（节内诱饵行不满足）、摘要模板值枚举与代码枚举比对
- 必红用例 9 → 19（新增矩阵加行/加列/诱饵行/删错误分类行/余弦 0.95/冲突退避值/枚举缩水/代码侧 allow 篡改）；新增"同义改写/行序对调应通过"绿灯回归，防门禁退化为字面量比对

### 文档

- 新增 `references/host-contract.md` 宿主状态契约：状态键 `resume_state.{task_id}`、字段表、读写时机、**human_pending 拦截责任在宿主（调用 decide 前查标记）**、跨会话按 task_id 隔离、resumed 在途新回调覆盖规则、历史保留最近 10 条、任务 ID 复用防护——一揽子落地"幂等查重/状态标记/静默丢弃/语义指纹记录"等此前无机制的声称
- 单一事实源化：anti-patterns.md 与 cases.md B 的阈值数值改为引用 SKILL.md（消除 "90%/80%" 残留）；E05 用例标签修正（瞬态/只读，与实现一致）；E07 补"产生于 1.0.x + 1.1.0 模板回填"标注；token 阈值给建议默认值（20000 token/任务，宿主可配）；"历史较长"给判据（超上下文预算约一半）
- trigger_cases.json 负模式补「服务器进程」；词法局限与三桶区分标准记入 cases.md；SKILL.md Evals 节补该文件引用；glossary 补 human_pending / prompt 片段
- 门禁项数口径三处对齐（SKILL.md / 门禁头注释 / CHANGELOG）

## 1.1.0 (2026-10-25)

### 修复

- **F1 相似度口径统一**：主方案 embedding 余弦 > 0.9 / fallback Jaccard ≥ 0.8，熔断备注显式标注 `semantic=fallback`；消除原文档"余弦>90%"与代码"Jaccard≥0.8"的分叉
- **F2 media 撤销口径统一**：media 为覆盖式重提交，恢复前不执行撤销（对齐 evals/cases.md E02 实测口径），修正 SKILL.md 反模式列表与 E02 预期
- **F3 待补充回写**：SKILL.md 尾部开放的 `check_pending_tasks` 样例改为引用 evals/cases.md 补充说明 A/C（早已补全但正文未回写）
- **F4 正名**：「语义哈希」统一为「语义指纹」（与实现一致），术语对照表同步；门禁含旧称回潮检查
- **F5 代码卫生**：resume_decide.py STOPWORDS 去重（"to" 重复项）
- **F6 frontmatter 规范化**：description 重写为触发条件式（Use when / Exclude）；平台私有字段 `triggers` / `default-enabled` 移出 frontmatter，内容并入正文「激活与接线」；新增 `metadata.version` / `metadata.updated`
- **F7 文档-代码逐项对账**：恢复摘要模板统一为 9 行（原"结果"行改为"恢复动作"+"前置动作"）；FINAL_KEYWORDS 补「发送」并列出完整中英清单；退避参数/矩阵上限/摘要字段逐项核对
- **F8 二轮评审修复（GREEN 走查 + 对抗审查证实项）**：
  - 通用信号字段与最小触发模板补充「任务 prompt 片段 / prompt提示={prompt_hint}」——否则按文档接线时 prompt_hint 恒为空、最终动作关键词永不生效，付款失败会被当作瞬态自动重试（评审实测反例）
  - 事务属性推断规则文档对齐代码：最终动作关键词对所有任务类型生效；workflow 副作用由宿主显式传入 tx_attr，不做关键词猜测
  - decide() 增加状态防呆：pending/resolved 等非失败信号不进入恢复流程（评审实测反例：resolved 任务被判 resume）
  - FATAL_PATTERNS 补 payment/transaction declined 兜底：付款类错误即使漏传 prompt_hint 也绝不重试
  - fallback 相似度归一化 "timed out"→"timeout"（评审实测反例：两种写法词集不相交导致漏熔断）
  - 可补偿定义示例改写（"如发送邮件"→"如邮件已递送、通知已群发"），消除与「发送」最终动作关键词的规范内冲突
  - 补 Retry-After 协调（取 max(t_retry, Retry-After)）、attempt_count 从 0 起算、重试次数"计划值"口径、abort/human 边界定义、media 原始参数由宿主取回的路径说明
  - adapter.py 接入示例键名对齐 check_pending_tasks 返回样例（task_id），标注 subagent 续跑目标为 thread_id、prompt_hint 来源
  - cases.md E05 用例串修正（原串喂入实现不熔断）与阈值口径残留清理；状态枚举口径对齐（pending/resolved 不得传入）
  - 触发评测：删除过宽负模式「帮我重启」（拦截了"帮我重启一下上次失败的后台图片生成任务"这类核心场景）并补正例锁定；positive_concepts 补「子智能体」近义词
  - 门禁新增第 8 项「信号字段完备性」并配 2 个必红用例（prompt 片段行/模板占位符被删时门禁必须失败）
  - anti-patterns.md 补 FAQ：最终动作关键词子串匹配偏保守是有意取舍，可用显式 tx_attr 覆盖

### 新增

- **N1 双源一致性门禁**：`scripts/check_consistency.py` 对账 SKILL.md 与 resume_decide.py 的重试矩阵、退避参数、相似度阈值、摘要模板、最终动作关键词、Retry Policy 口径；配必红用例 `scripts/test_check_consistency.py`（首轮 7 类，二轮评审后扩充至 9 个必红用例）
- **N2 可逆/可补偿前置动作实装**：`Decision.pre_action`（none/undo/compensate）+ `adapter.py` Handlers 新增 undo/compensate 回调，dispatch 在续跑前执行前置动作（media 覆盖重提交除外）；新增 4 个 dispatch 顺序断言 + 5 个 pre_action 推断断言
- **N3 触发评测用例**：`evals/trigger_cases.json`（正例 9 / 负例 4 / 近邻 4 三桶），作为触发冒烟评测用例（可经 metaskill 工具链 run_trigger_eval.py 执行）

### 其他

- 打包剔除 `.pytest_cache/`；SKILL.md 标题移除硬编码版本号（版本统一由 frontmatter / _meta.json / CHANGELOG 三处管理）；正文抽象为通用信号字段 + 平台适配示例章节（HanaAgent 映射降级为示例）；本 CHANGELOG 与 references/（术语表、反模式 FAQ）自此版本引入

## 1.0.1

初始发布版本（2025-10-24 导出包）。
