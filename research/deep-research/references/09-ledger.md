# 账本 —— `run.json`

`run.json` 是 run 唯一的持久状态。会话死了，新会话恢复靠的就是它。**每个**阶段之后写它，不是最后才写。

`scripts/check.py` 强制下述形状。第一次写 `run.json` 前读本文件；手改之前再读一遍。

## 顶层

```json
{
  "schema": 1,
  "run_id": "r_a78c357a",
  "created_at": "2026-10-22T15:44:00Z",
  "updated_at": "2026-10-22T18:02:11Z",
  "project": "/home/me/Documents/influenza-law",
  "question": "1918年大流感如何改变了日本的公共卫生立法？",
  "language": "auto",
  "status": "active",
  "independent": true,
  "independent_note": "",
  "limits": {
    "depth": 3,
    "max_nodes": 30,
    "parallel": 3,
    "cards": 3,
    "followups": 2,
    "revisions": 2,
    "plan_approval": "require"
  },
  "consent": {"dissolution": null, "note": ""},
  "nodes": [],
  "decisions": [],
  "joins": [],
  "not_pursued": [],
  "declined": [],
  "relations": [],
  "alternatives": [],
  "errata": [],
  "cost": {"tokens": 0, "calls": 0, "usd": 0.0, "entries": []}
}
```

| 字段 | 类型 | 规则 |
|---|---|---|
| `schema` | int | `1`。不认识的值拒绝运行：`check.py` 对非正整数报 P0，对比本技能更新的值**报 P0 并拒绝运行**，对更旧的值报 P1 |
| `run_id` | string | `[A-Za-z0-9_.-]{1,64}`，与文件夹名一致 |
| `created_at`、`updated_at` | ISO-8601 UTC | 每次写入都更新 `updated_at` |
| `project` | 绝对路径 | 研究写到哪里；缺失报 P1 |
| `question` | string | 用户原话；绝不就地编辑 |
| `language` | string | `auto`、`zh`、`en` 或语言标签（IETF 标签如 `ja`、`zh-Hans` 亦可）；缺失或不合规报 P1 |
| `status` | `active` \| `paused` \| `done` \| `abandoned` | `done` 只在终稿存在之后；不认识的取值报 P0 |
| `independent` | bool | 卡或审查跑在协调人自己的上下文时为 `false` |
| `independent_note` | string | `independent` 为 `false` 时必填：丢了什么 |
| `limits` | object | 创建时固定；中途改需用户同意并记录 |
| `consent` | object | `dissolution`：`null`（没问）/`true`（同意）/`false`（拒绝）；`note` 必须是字符串（记用户运行时约束） |
| `nodes` | array | 每研究节点一条 |
| `decisions` | array | 分叉，各属于做出它的节点 |
| `joins` | array | 为把多个父节点带向前而开的节点 |
| `not_pursued` | array | 刻意不开的选项，及拦住它的约束 |
| `declined` | array | 被拒绝的提案：`{"issue_id": "a3", "disposition": "decline", "reason": "…", "covered_by": ""}`；`reason` 必填且必须点名约束（"不值得"会被拒） |
| `relations` | array | converge / diverge / resonates / appropriates / displaces；`note` 可选，缺了会在 `graph.md` 里只剩类型 |
| `alternatives` | array | 可能性审查的每条提案及其归宿 |
| `errata` | array | 针对早前节点记的更正 |
| `cost` | object | 真实开销记账：`{"tokens": int, "calls": int, "usd": float, "entries": [{at, node, tokens, calls, usd, what}]}`。由 `node.py spend` 写入，`status.py --cost` 读它；形状错了会被 `check.py` 报出来 |
| `final` | object | `{"survey": "...", "draft": "...", "review": "...", "final": "..."}`——`final/` 下的文件名；`check.py` 校验各自存在 |
| `question_revisions` | array | `{"at": "...", "what": "...", "effect": "carry" \| "replan" \| "abandon"}`——中途每次改题一条（见 `SKILL.md`"用户改问题时"） |

## 用户约束与同意的记录惯例

`consent.note` 不只存消解答复。计划审批时用户给出的**运行时约束**——子代理数量上限（"子代理限 2–3 个"）、外部站点不可达时要报告、交付目录与命名——也记在这里（数量的优先记入 `limits.parallel`）。执行全程遵守；事后审计靠它。

## 节点

```json
{
  "id": "n_d8acf9fa",
  "folder": "01-1918年大流感如何改变了日本的公共卫生立法",
  "seq": 1,
  "depth": 0,
  "kind": "root",
  "question": "1918年大流感如何改变了日本的公共卫生立法？",
  "parents": [],
  "opened_by": null,
  "status": "closed",
  "cards": ["c1-statutes", "c2-archives", "c3-prefectures"],
  "synthesis": "synthesis.md",
  "synthesis_versions": 2,
  "review_rounds": 2,
  "review_files": ["review-01.md", "review-02.md"],
  "possibility_file": "possibility.md",
  "no_forks": false,
  "dissolves": null,
  "issues": [],
  "gaps": []
}
```

| 字段 | 类型 | 规则 |
|---|---|---|
| `id` | string | `n_<8位hex>`，run 内唯一 |
| `folder` | string | `nodes/` 下的文件夹名；必须存在 |
| `seq` | int ≥ 1 | 展示顺序，从 1 起；非正整数会被报 |
| `depth` | int ≥ 0 | 根为 0；子恰比最深父多一 |
| `kind` | `root` \| `line` \| `join` \| `branch` | `branch`＝无卡的纯分叉点 |
| `question` | string | 为本节点的协调人写的问句；非根节点缺失会被报 |
| `parents` | 节点 id 数组 | 非根 ≥1；join ≥2 |
| `opened_by` | object 或 null | `{"decision": "d1", "option": "o2"}`；写成字符串会被报 |
| `status` | 见下方状态机 | |
| `cards` | 卡 id 数组 | 本节点计划声明的卡文件夹；超过 `limits.cards` 会被报 |
| `synthesis` | string 或 null | **当前**版本的文件名，如 `synthesis-2.md` |
| `synthesis_versions` | int ≥ 0 | 存在几个版本；有结论却写 0 会被报 |
| `review_rounds` | int ≥ 0 | 跑了几轮批判；**0 阻断 `closed`** |
| `review_files` | array | 节点文件夹里的每份批判文件；**空阻断 `closed`** |
| `possibility_file` | string | 可能性审查产出在节点文件夹内；**`closed` 必需** |
| `no_forks` | bool | 分叉决策结论为无分叉时 `true`；否则必须有决策点名本节点 |
| `dissolves` | `null` \| `"this_node"` \| `"research_question"` | 只有 `research_question` 需要用户同意；未知取值会被报 |
| `issues` | array | 批判的问题及其处置 |
| `gaps` | array | 可能性审查的缺口及其处置 |

## 用 `node.py` 写，而不是手改

`scaffold.py` 建 run 之后，协议里其余全部写操作都有脚本入口。手改 `run.json` 仍然允许
（崩溃的阶段、写错的文件夹名），但脚本会把状态机与"一个可能只开一次"这类规则挡在前面。

```bash
# 分叉：把待决选项开成新节点（会自动把该选项的 node 指过去，并建好节点目录骨架）
python3 "$SKILL_DIR/scripts/node.py" <project> fork --node n_a1b2 --option o2 \
        --question "敕令把殖民卫生范畴移植进国内行政了吗？"

# 汇合：把两条已完成的线带到一起（父节点未终态会警告，少于两个父会被拒）
python3 "$SKILL_DIR/scripts/node.py" <project> join --parents n_a1b2,n_c3d4 \
        --question "若财政与殖民两种叙述都成立，分期该怎样改写？" \
        --rationale "两线都把断裂定在 1919；一起带向前是对峙，不是合并。"

# 推进状态：不给 --to 就走状态机下一态；非法跃迁会被拒；closed 缺四项前提也会被拒
python3 "$SKILL_DIR/scripts/node.py" <project> advance n_a1b2
python3 "$SKILL_DIR/scripts/node.py" <project> advance n_a1b2 --to closed

# 记决策：一条带利害的问题 + ≥2 个带前提的选项；无分叉就声明
python3 "$SKILL_DIR/scripts/node.py" <project> decide --node n_a1b2 --id d1 \
        --question "国内国家建构的工具，还是帝国行政的工具？" --stakes "它决定比较对象。" \
        --option "id=o1,label=国内国家建构,premise=立法跟在战前行政能力之后,own" \
        --option "id=o2,label=帝国剧目,premise=敕令移植殖民卫生范畴"
python3 "$SKILL_DIR/scripts/node.py" <project> decide --node n_a1b2 --no-forks \
        --reason "本问题此处只容一条回答线。"

# 记关系与拒绝（拒绝理由必须点名约束，"不值得"会被拒）
python3 "$SKILL_DIR/scripts/node.py" <project> relation --kind converge \
        --nodes n_a1b2,n_c3d4 --note "两线从独立证据把断裂定在 1919。"
python3 "$SKILL_DIR/scripts/node.py" <project> decline --option a3 \
        --reason "节点预算已用尽：30/30。"

# 记真实开销（status.py --cost 读的就是它）
python3 "$SKILL_DIR/scripts/node.py" <project> spend --node n_a1b2 \
        --tokens 8400 --calls 4 --usd 0.52 --what "两卡 + 一轮批判"
```

每次写入都更新 `updated_at`，并顺带重写 `graph.md` 与 `paths.md`。

### 卡的降级执行记录（card_note）

某张卡因子代理派发失败（上游 502、超时、取消）或用户子代理上限而由协调人亲自执行时，在该节点对象上添加 `card_note`（字符串或对象数组），写明：哪张卡、为何降级、由谁执行、外部材料（若有）从何而来。终稿的方法说明须披露同样的内容。示例（来自真实 run）：

```json
{"card_note": "c3-institutionalization-evaluation 由协调人执行（该卡两次子代理派发因上游 502/取消失败，用户同时要求限制子代理数）；按 skill 降级路径记录于此，最终报告的方法说明须披露。其外部材料由前一位中断的研究员抓取并经协调人逐字核对。"}
```

`check.py` 不校验 `card_note`——它是对读者的诚实记录，不是闸门。

### 节点状态机

```text
queued ──> planning ──> awaiting_approval ──> executing ──> synthesizing ──> reviewing
              │                                                              │
              │                                          ┌───────────────────┤
              │                                          ▼                   │
              │                                     disposing ───────────────┘ (revise)
              │                                          │
              │                                          ▼
              └──(branch 节点：无卡)──────────> possibility ──> filling_gaps ──┐
                                                          │                 │        │
                                                          │                 └────────┘ (revise)
                                                          ▼
                                                       deciding ──> closed
```

| 状态 | 含义 | 下一态 |
|---|---|---|
| `queued` | 已创建，未动笔 | `planning` |
| `planning` | 写 `plan.md`／等澄清答复 | `awaiting_approval` 或 `executing` |
| `awaiting_approval` | 计划已记，等用户放行 | `executing` |
| `executing` | 卡在跑 | `synthesizing` |
| `synthesizing` | 写结论或修订 | `reviewing` |
| `reviewing` | 批判在跑 | `disposing` |
| `disposing` | 问题已记，写处置 | `synthesizing`（有 `revise`）或 `possibility` |
| `possibility` | 可能性审查在跑 | `filling_gaps` 或 `deciding` |
| `filling_gaps` | 处置缺口 | `synthesizing`（有 `revise`）或 `deciding` |
| `deciding` | 记分叉决策 | `closed` |
| `closed` | 结论定稿、已审、决策已记 | — |
| `skipped` | 经用户决定，未研究即关闭 | — |
| `failed` | 节点没能完成 | 重试时回 `planning` |

### `closed` 需要什么

四条全部成立才许 `closed`。`check.py` 对每条失败各报一个 P0——所以什么都缺的节点显示四行，不是一行：

| 前提 | 字段 | 失败时的 P0 |
|---|---|---|
| 1. 结论存在 | `synthesis` → 真实文件 | `synthesis points at X, which does not exist` |
| 2. 被审过 | `review_rounds` ≥ 1 **且** `review_files` 每个文件存在 | 两个 P0：`closed with review_rounds < 1` 与 `closed with no review_files` |
| 3. 可能性被问过 | `possibility_file` → 真实文件 | `closed with no possibility_file` |
| 4. 分叉决策已做 | 有 `decided_at` 等于本节点的决策，**或** `no_forks: true` | `closed with neither a decision recorded for it nor no_forks: true` |

第 4 条是同一检查里的二选一：记一条决策，*或*声明无分叉。都算数；都不是默认。

要点在于：结论没被攻击过、没人问过它拒绝了什么，就成不了节点的答案。不能审查的 run（无子代理）也照样记轮数并标注 self-review——记录显示的是审查*不独立*，这与显示没有审查是两回事。

## issue

```json
{
  "id": "i1",
  "kind": "因果推断",
  "question": "该令的十月日期真的早于东京的第二波吗？",
  "rationale": "结论把第二波定为'1918 年秋'而无月份。",
  "priority": 3,
  "material": true,
  "round": 1,
  "disposition": "rebut",
  "reason": "据府县死亡序列（c3 表 2），东京峰值为 1918-10-18。",
  "covered_by": "",
  "revision": ""
}
```

| 字段 | 规则 |
|---|---|
| `id` | 节点内跨轮唯一 |
| `kind`、`question`、`rationale` | 来自审查员 |
| `priority` | 整数，大者先行；非整数会被报 |
| `material` | bool。`false` 的无需处置 |
| `round` | 第几轮批判提出；必须是 ≥1 的整数 |
| `disposition` | 七值之一，`material` 为 true 时必填 |
| `reason` | `rebut`、`concede`、`covered`、`park`、`correct`、`branch` 必填 |
| `covered_by` | `covered` 必填：本 run 的节点 id |
| `revision` | `revise` 时：回应它的那个 `synthesis-N.md`；`revise` 却没写会被报 |

**缺口（gap）同形**，但 `disposition` 限于 `revise`、`rebut`、`concede`、`covered`、`park`。`branch` 不可用：缺口绝不是分叉。

## 决策与选项

```json
{
  "id": "d1",
  "decided_at": "n_d8acf9fa",
  "question": "1918 年立法是国内国家建构的工具，还是帝国行政的工具？",
  "stakes": "它决定比较对象，进而决定什么算这部立法的原因。",
  "options": [
    {
      "id": "o1",
      "label": "国内国家建构",
      "premise": "立法跟在战前国内行政能力之后。",
      "own": true,
      "node": "n_d8acf9fa",
      "reason": "",
      "covered_by": ""
    },
    {
      "id": "o2",
      "label": "帝国剧目",
      "premise": "敕令移植殖民卫生范畴。",
      "own": false,
      "node": "n_new1",
      "reason": "",
      "covered_by": "",
      "sources": ["a1"]
    }
  ]
}
```

| 字段 | 规则 |
|---|---|
| `id` | 全 run 唯一 |
| `decided_at` | 做出决策的节点；必须存在 |
| `question` | 带利害的那个问题；缺失会被报 |
| `stakes` | 取决于它的是什么；缺失会被报 |
| `options` | ≥2、互斥、各带 `premise` |
| `own` | 每决策至多一个：决策节点自己的线；必须是 bool |
| `node` / `reason` / `covered_by` | 每选项**恰好一个**归宿：被节点追／带理由不开／被覆盖 |
| `label` | 路径表与报告按它点名该选项；缺失会被报 |
| `sources` | 组成此选项的 alternatives id 与 branch 处置的 issue id；必须是 id 列表 |

三样都没有的选项是*待决*——run 中途没问题，本层关闭后是提醒。三样占两个是错误：不能既被追又被拒。

## alternatives、joins、relations、errata

```json
{"alternatives": [{"id": "a1", "kind": "框架", "proposal": "...", "premise": "...",
                   "rationale": "...", "gap": false, "covered_by": "",
                   "outcome": "option", "outcome_ref": "o2"}]}
```

| 字段 | 规则 |
|---|---|
| `gap` | bool，必填。`true`＝缺口（留在节点内）；`false`＝未走的可能 |
| `outcome` | `option` \| `declined` \| `gap_revise` \| `gap_rebut` \| `gap_concede` \| `gap_covered` \| `gap_park` |
| `outcome_ref` | `outcome: option` 时必填：承载该提案的选项 id；指向 run 外的选项会被报 |
| `covered_by` | 已有节点或选项在追它时的节点 id 或选项 id |

```json
{"joins": [{"id": "n_join1", "parents": ["n_e5f6", "n_g7h8"], "question": "...", "rationale": "..."}],
 "not_pursued": [{"option": "o9", "reason": "节点预算已用尽：30/30。"}],
 "declined": [{"issue_id": "a3", "disposition": "decline", "reason": "该提案只是给既有线换个名字；答案不因此改变。", "covered_by": ""}],
 "relations": [{"kind": "converge", "nodes": ["n_e5f6", "n_g7h8"], "note": "..."}],
 "errata": [{"against": "n_a1b2c3d4", "claim": "...", "correction": "...", "grounds": "..."}]}
```

- 汇合的父节点必须存在且已完成。
- `not_pursued[].reason` 必须点名**约束**（预算、深度、已被追、更正、互补）。"不值得"会被拒。
- `declined[]` 记被拒绝的**提案**（`issue_id` 指向 alternatives id），与 `not_pursued[]` 记不开的
  **选项**是两件事；`reason` 同样必须点名约束，且必须指向本 run 已知的提案或选项。
- 关系点名 ≥2 个存在节点与已知类型。`note` 可选——缺了 `graph.md` 里只剩类型，所以建议写。
- 勘误的 `against` 点名一个既存在、又不是记录它的节点的节点。

## 恢复

中断后恢复：

1. 读 `run.json`。
2. 找第一个 `status` 非终态的节点，从该状态对应的阶段继续。
3. 重读该节点的 `plan.md`、各卡交付物、账本指向的 `synthesis-N.md`。不要依赖对话记忆——它可能已经没了。
4. 继续前从 `run.json` 重写派生视图（`graph.md`、`paths.md`）；它们是缓存，过期缓存导致重复劳动。`python3 "$SKILL_DIR/scripts/scaffold.py" <project> --resume` 干这个。
5. 跑 `check.py`。花下一次派发之前修掉它报的。
6. **中断会话遗留的材料（半成品交付物、抓来的源文件）逐字核对后才能引用**，并注明来源会话。快速看一眼进度与账本新鲜度：`python3 "$SKILL_DIR/scripts/status.py" <project>`。

## 手工编辑

允许且有时必要（崩溃的阶段、写错的文件夹名）。两条规则：

- **绝不为过检查而删除记录。**缺处置就补上；选项被拒就记理由。删掉节点等于删掉工作发生过的证据。
- **任何手改之后跑 `check.py`。**畸形的账本比缺失的更糟，因为下一个会话会信任它。
