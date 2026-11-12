# 变更记录

版本号三处同步：`SKILL.md` frontmatter `metadata.version`、`_meta.json` 的 `version`、本文件顶部条目。
semver：仅修复 → patch；功能新增 → minor；破坏性变更 → major。

## 1.3.0（2026-10-25）

有功能新增，也有**有意收紧**的门禁。收紧会让既有的一些 run 从 OK 变 FAIL——那正是收紧的目的，
但它们不是悄悄发生的，逐条列在下面。

### ⚠ 有意收紧（破坏性，会让既有 run 变红）

1. **Angle 从"最高 P1"提到 P0。** 结论以"本文综述……""本报告梳理……"这类宣告综述的句式开头，
   或正文除标题外没有散文，现在**阻断交付**（exit 2），不再只是提醒。Angle 在
   `references/10-gates.md` 里就是 critical（"失败即停止交付"），但代码里最高只发 P1，
   因此永远达不到它自己声明的后果。
2. **Angle 在阶段 3（结论写就时）就跑，不再等到 `closed`。** 此前它只在 `status == "closed"`
   时可达，而 SKILL.md:64 把它放在阶段 3——于是一份综述形态的结论可以在 synthesizing /
   reviewing 之间一路无人问津。
3. **Coverage 逐行解析覆盖表。** 此前只查 `## 覆盖` 标题在场；现在卡列为空且缺口列也没写
   理由的行会被点名报 P1。空格 = declared gap 是这门禁的全部意义。
4. **Calibration 的过度断言从 P2 提到 P1。** `proves / 证实了 / 证明了` 一类动词，或
   `first study / the best / 首次 / 最优` 一类无限定最高级，现在让门禁真的 FAIL。SKILL.md:230
   称 Calibration 是 major「失败必须修复或明确接受」，而只能发 P2 的门禁永远只是 note。
   不足断言（堆叠对冲）仍只报 P2——它要协调人判断。
5. **Taxonomy 与 Weaving 从死门禁变成真门禁。** 此前 `check.py` 的 `GATES` 声明了它们，但全库
   没有一处 `rep.gate("taxonomy"/"weaving")` 调用，`emit_gates()` 因此**每次都打印 clear**，
   而 SKILL.md:316 让协调人把关卡当清单看。现在两者都读终稿正文并点名出问题的章节/段落。
6. **`--gates` 的 verdict 计入未归类发现。** 此前 verdict 只检查六个门禁桶，未归类桶里的 P0
   被打印却不计入判定与退出码——于是存在 5 个 P0 时它仍输出 `verdict: OK` 并 exit 0。
   现在未归类桶的 P0 同样 BLOCKED：**有 P0 时 `--gates` 的退出码从 0 变成 2**。
7. **`schema` 真的拒绝不认识的值。** `09-ledger.md:43` 这么写了，但全库无校验；现在比本技能
   更新的 schema 报 P0 并拒绝运行，非正整数报 P0，缺字段或更旧的值报 P1。

### 修复

- `--gates --json` 曾静默丢掉全部关卡数据（`check.py:251` 的 `and not args.json`）；现在同一
  分组同时支持两种输出，`--json` 还带 `exit` 与 `verdict` 字段。
- **`scaffold.py --resume` 崩溃**：对每个 relation 取 `r['note']`，而 `check.py` 不要求 `note`——
  合法输入让会话恢复入口 `KeyError` 退出 1，且此时 `graph.md` 已被覆写。现在 `note` 明确为
  可选：scaffold 与 node 都不再假设它，`check.py` 对缺失只报 P2（提醒它让关系不可读）。
- **`evals/trigger_cases.json` 是孤儿**：SKILL.md 的文件表与正文零处提及。已补进文件表，并写明
  怎么跑、改 `description` 后必须重跑。
- **14 个文档化但从不校验的账本键**已补校验：`seq`、`opened_by`、`project`、`language`、
  `limits.plan_approval`、`consent.note`（及 `consent` 本身不是对象）、`synthesis_versions`、
  `issue.priority` / `issue.round` / `issue.revision`、`decision.stakes`、`option.label` /
  `option.sources` / `option.own`、`alternative.outcome_ref`、`findings.depends_on` /
  `findings.uncertain`。run 级 `declined: [...]` 数组只存在于 `05-possibility.md` 的示例里、
  顶层 schema 未列——已补进 schema 并校验其 `reason` 必须点名约束。
- **`MANIFEST.txt` 陈旧**：header 仍写 1.1.0、4 个 SHA-256 与实际不符、2 个行数错。已改由
  `scripts/manifest.py` 生成（`--check` 比对），版本从 SKILL.md frontmatter 读，不再手改。
- **`R8_检查脚本只读` 断言形同虚设**：它给 `status.py` 传 `--gates`（status.py 的 argparse 根本
  不接受），却不检查 returncode——于是"只读"从未真正被测。现在每种参数组合都断言 exit 0，
  并反向断言不被接受的参数组合必须被拒绝。
- `limits.parallel` 与 `limits.cards` 此前只校验是整数、从不与实际执行情况核对；现在在飞节点
  数超 `parallel`、某节点派卡数超 `cards` 都会被点名。
- 补 `LICENSE`（`license: MIT` 而包内无 LICENSE 文件）。
- `_meta.json` 的 `slug` 仍是 `deepreaserch`（拼写错误）——**沿用不改**：改名会被平台视为新
  条目。`publishedAt` 与 `SKILL.md` 的 `metadata.updated` 同步到 2026-10-25。

### 功能新增

- **F1 `scripts/node.py`** —— 脚本化开节点 / 分叉 / 汇合 / 推进状态 / 记决策 / 记关系 / 记拒绝 /
  记账。此前 `scaffold.py` 之后整个协议全靠手改 JSON，而上面那 14 个键没有任何脚本写入路径。
  用法已写进 `references/09-ledger.md`。
- **F2 Taxonomy + Weaving 两门禁** —— 判据与关卡视图读法已写进 `references/10-gates.md`。
- **F3 行为级回归 eval** —— `evals/artifact_cases/`（黄金 run：plan / findings / possibility /
  run / 终稿四件套）＋ `scripts/run_artifact_eval.py`：干净产物全清，再把每个门禁逐个破坏、
  逐个断言它**必须**失败。此前只有词法级触发用例。
- **F4 成本与预算真实化** —— ledger 增加 `cost` 字段并由 `node.py spend` 写入；`status.py --cost`
  改读真实数据，无数据时如实说"未记录"并给出记账命令（不再用 `cards*5000 + rounds*2000`
  的系数编数字），并在预算逼近上限时预警。同一脚本能力用于重生成 `MANIFEST.txt`。
- **F5 导出扩格式** —— `export.py --format html`（零依赖自研渲染，自含样式可打印成 PDF）；
  pdf / docx 走 pandoc，缺失时降级为 HTML 并说明；`--references` 导出参考文献清单（终稿没写
  `## 参考文献` 节时从正文定位符抽出并提醒）；`--manifest` 产出逐项 sha256 与跳过明细。
- **F6 恢复增强** —— `scaffold.py --resume --node <id>` 只重建该节点视图并报告它该从哪个阶段
  接续；不带 `--node` 时点名第一个非终态节点。

### 测试

`scripts/test_skill.py` 从 31 条扩到 54 条。新增 `A*` 一组是全套用例里最要紧的一组：此前
**没有任何一条断言"某门禁应该失败"**，这是最大的测试盲区。现在六门禁各有一条必红用例，另加
`--gates` 判定、schema、定位符、未文档化键、`declined`、resume 崩溃各一条。`evals/artifact_cases`
另在行为级复验同一组门禁。
