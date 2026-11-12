# 06 结构化生成

用 `examples/plan.json` 走完 plan → scaffold → validate → build 的结构化路径。

## 要验什么

- `plan.mjs check --strict` 与 `plan.mjs check --deck` 都通过。
- 同一份 plan 两次 scaffold 输出**字节一致**。
- 生成页每页都有 `data-plan-id` / `data-role` / `data-layout`。
- `validate --strict` / `audit-text --strict` / `build --check` 全过。
- 六类坏 plan 必须被拒绝，并给出对应原因：
  role 不匹配、缺必填槽位、槽位超字数、claim 重复、时长漂移、版式连续超过上限。
- 删掉一页后，`plan --deck` 必须报漂移。

## 判据

见 `run.mjs` 的 `CASES['06-structure']`。
