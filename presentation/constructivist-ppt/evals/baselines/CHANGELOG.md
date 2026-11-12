# 基线变更记录

只有 `node evals/run.mjs --update-baseline <case> --reason "…"` 能改基线。
每次变更必须在这里追加一行。**阈值随基线一起偷偷漂移是所有验收体系最失效的方式。**

- 2026-10-21 · v2 建立基线 · `pre-refactor/`（v1 假绿：validate 0/0 但含 P4 方框、
  `.t-h2` 缺 nowrap、单行正文 wrap=false）与 `post-refactor/`（v2 真绿，三个缺陷各有 diff 证据）。
  理由：从 v1 迁移到 v2，规则与阈值发生破坏性变更，需要两组可对比的锚点。
- 2026-10-21 · 06-structure · v3 structured generation: plan/scaffold determinism and bad-plan rejection · repeats=3
