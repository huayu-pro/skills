# 会话日志考古操作手册

反思回环（SKILL.md 第五步）与优化入口要从历史会话汲取教训时读本文件。会话日志是比交付报告更原始的矿藏：报告会压缩叙事、遗漏用户原话约束，日志不会。v1.3.0 与 v1.5.0 两次元技能升级的直接依据都是日志考古。

## 日志位置与命名

目录 `~/.zcode/cli/rollout/`，三类文件：

| 前缀 | 含义 |
|---|---|
| `model-io-session_<hex>.jsonl` | 主会话（要考古的对象） |
| `model-io-sess_<uuid>.jsonl` | 旧命名的主会话 |
| `model-io-sess_subagent_agent_<uuid>.jsonl` | 子代理会话（二期素材，通常不读） |

按文件 mtime 圈定时间窗；注意 **mtime 是本地时间，行内 `completedAt` 是 UTC**，相差 8 小时。今天正在进行的会话文件要排除，避免考古到当前会话自己。

## 行结构

每行 = 一次模型 API 调用记录，顶层键含 `request / response / sessionId / startedAt / completedAt` 等。关键事实：`request.body.messages` 是**调用时刻的全量对话历史**——所以同一条用户消息会在后续每一行重复出现。还原用户全部发言的方法：取「每行最后一条 role=user 的纯文本消息」，跨行**按内容去重**（不能按整行去重，行号前缀会破坏去重）。

## 提取用户消息（jq 配方，实测可用）

```bash
jq -r '[(input_line_number|tostring),
  (((.request.body.messages // []) | map(select(.role=="user")) | last | .content
    | if type=="string" then . else ([.[]? | select(.type=="text") | .text] | join("\n")) end)
   | gsub("(?s)<system-reminder>.*?</system-reminder>";"") | gsub("[\\t\\n ]+";" ") | .[0:2500])]
  | join("|")' FILE.jsonl \
 | awk -F'|' '$2!="" && $2!="null" && !seen[$2]++ {print}'
```

要点：剥离 `<system-reminder>` 块（里面是环境注入不是用户原话）；`head -1 FILE | jq 'keys'` 先摸结构再改表达式；输出带行号方便回查原文（`sed -n '<行号>p' FILE.jsonl`）。

## 压缩摘要的两种形态

1. 本 harness 现行：一条 role=user 消息以 `This session is being continued from a previous conversation` 开头，且**在压缩点之后的每一行都持久存在**——用 `grep -n -m1` 找首现行即压缩点；压缩点之前的历史要用其他线索（用户消息、计划文件）还原。
2. 旧流程：`CRITICAL: Respond with TEXT ONLY` 的总结指令行，其 `response.text` 就是当时全量总结。

## 最终交付总结

`tail -1 FILE.jsonl` 的 `.response.text` 是该会话最后一条 assistant 消息（即最终交付总结）；错误记录的 response 只有 headers/toolCalls/usage，无 text。

## 大文件纪律

- 单文件可达 GB 级：**绝不 cat / 整读**，只用 jq -c 流式、grep -n 定位后 sed -n 取行、head/tail。
- jq 全量解析 1-2GB 约几分钟，属正常；给外层命令加超时，对超大文件先 `head -c 2000` 验结构。
- 单条消息超长时在 jq 里切片截断（如 `.[0:2500]`），不要全量吐出。

## 交叉验证与注意事项

- 防漏消息：对无压缩会话，用 `tail -1 FILE | jq '.request.body.messages'` 提取**全部** role=user 消息，与逐行去重结果比对（逐行法可能漏掉「连续两条用户消息」中的第一条）。
- 证据新鲜度：会话文件可能被外部清理（实测有文件在考古进行中消失）——先抢救关键内容再深挖。
- 报告 vs 日志冲突时：日志是原始证据，报告是二手叙事；版本号演进常被报告压缩进单轮叙事，以多会话日志交叉定位真实出处。
- 考古结论与普通教训一样过 lessons.md 的泛化门，一次性细节留在当轮报告。
