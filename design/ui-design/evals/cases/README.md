# 金标准用例的调用契约

这 8 个用例继承自上游 `refactoring-ui-skill`（MIT），测的是 **Workflow D 的审计质量**。

## 必须这样调用

```bash
mkdir -p /tmp/audit_runs
for c in 01-settings 02-login 03-empty 04-stats 05-landing 06-article 07-hero 08-blotter; do
  python3 -I scripts/audit.py evals/cases/$c/index.html \
    --brand "#0f766e" --out /tmp/audit_runs/$c.md
  python3 -I evals/score.py --case $c /tmp/audit_runs/$c.md
done
```

## `--brand` 不是可选的

6 个用例的 `stack.tokens` 都声明了 `primary #0f766e`。**不传 `--brand` 时，
`05-landing` 的 `must` 会漏一条**（品牌色被 indigo 替换）——因为品牌漂移检查只有在
知道品牌色是什么的时候才能做。

所以：

| 调用方式 | 结果 |
|---|---|
| 带 `--brand "#0f766e"` | **8/8 PASS** |
| 不带 `--brand` | **7/8**（`05-landing` 漏 §1.4.2） |

两者都是真实结果。**不要**只报「8/8」而不说调用条件——这是本技能最容易被误读的一处。

## `score.py --self-check` 测的不是审计器

`--self-check` 用 `expected.json` 里的规则合成一份报告，再打分。它验证的是**评分器**
（规则提取 + 匹配）能正常工作，**不验证 `audit.py` 能发现这些问题**。

判断 `audit.py` 是否合格，只看上面的循环是否 8/8。两者不能互相替代。

## 这 8 个用例没覆盖什么

- Workflow B 的原型检索与约束简报（见 `../workflow_cases.md`）
- `query_corpus.py` 的任何行为
- Workflow A / B / E / G
- `--brand` 之外的任何参数

`../workflow_cases.md` 补了 A/B/E/G，但那是手动用例，不是自动回归。
