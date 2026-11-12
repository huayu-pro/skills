#!/usr/bin/env python3
"""开节点、分叉、汇合、推进状态、记决策——协议里除建 run 之外的全部写操作。

用法：
    python3 node.py PROJECT fork   --node <id> --question "..." [--kind line]
                                   [--option <option-id>] [--decision <decision-id>] [--seq N]
    python3 node.py PROJECT join   --parents <id,id> --question "..." --rationale "..."
    python3 node.py PROJECT advance <node-id> [--to <status>]
    python3 node.py PROJECT decide  --node <id> --id <d-id> --question "..." --stakes "..."
                                    [--option id=o1,label=...,premise=...[,own][,node=<id>][,reason=...]]
                                    [--no-forks]
    python3 node.py PROJECT spend   --node <id> --tokens N [--calls N] [--usd F] [--what "..."]

写 `run.json` 并顺带重写 `graph.md` / `paths.md`；每次写入都更新 `updated_at`。

在 `scaffold.py` 之后，本脚本覆盖协议的全部写路径：分叉与汇合开节点、推进状态机、
记分叉决策、记真实开销。手改 `run.json` 仍然允许，但那 14 个被文档写进 schema 的键
此前没有任何脚本写入路径——本脚本给它们一个。

退出码：0 成功；2 拒绝（参数不合法、节点不存在、状态机不允许该跃迁、id 重复）。
仅标准库；无网络。
"""

from __future__ import annotations

import argparse
import json
import os
import re
import secrets
import sys
from datetime import datetime, timezone

SCHEMA = 1

NODE_KINDS = {"root", "line", "join", "branch"}
NODE_TERMINAL = {"closed", "skipped", "failed"}
# 状态机的合法跃迁。允许跳级（awaiting_approval → executing 是常规动作），但不允许
# 从终态无声复活：那会让"已关闭"失去意义。
NEXT_STATES = {
    "queued": {"planning", "skipped", "failed"},
    "planning": {"awaiting_approval", "executing", "skipped", "failed"},
    "awaiting_approval": {"executing", "planning", "skipped", "failed"},
    "executing": {"synthesizing", "failed", "skipped"},
    "synthesizing": {"reviewing", "failed", "skipped"},
    "reviewing": {"disposing", "synthesizing", "failed", "skipped"},
    "disposing": {"synthesizing", "possibility", "reviewing", "closed", "failed", "skipped"},
    "possibility": {"filling_gaps", "deciding", "failed", "skipped"},
    "filling_gaps": {"synthesizing", "deciding", "failed", "skipped"},
    "deciding": {"closed", "possibility", "failed", "skipped"},
    "closed": set(),
    "skipped": {"planning"},
    "failed": {"planning", "skipped", "closed"},
}
PHASE_AFTER = {
    "queued": "planning",
    "planning": "awaiting_approval",
    "awaiting_approval": "executing",
    "executing": "synthesizing",
    "synthesizing": "reviewing",
    "reviewing": "disposing",
    "disposing": "possibility",
    "possibility": "filling_gaps",
    "filling_gaps": "deciding",
    "deciding": "closed",
}
RELATION_KINDS = {"converge", "diverge", "resonates", "appropriates", "displaces"}


def die(message: str, code: int = 2) -> None:
    print(f"node: {message}", file=sys.stderr)
    raise SystemExit(code)


def warn(message: str) -> None:
    print(f"node: 警告：{message}", file=sys.stderr)


def now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def new_id(prefix: str) -> str:
    return f"{prefix}_{secrets.token_hex(4)}"


def one_line(text, limit: int = 120) -> str:
    flat = " ".join(str(text or "").split())
    return flat if len(flat) <= limit else flat[: limit - 1] + "…"


# --------------------------------------------------------------------------- 视图（与 scaffold.py 同源）

def node_dir_name(node_id: str, seq: int, question: str) -> str:
    slug = re.sub(r"[^\w\u4e00-\u9fff]+", "-", str(question).strip().lower()).strip("-")
    cut = slug[:40]
    last_sep = max(cut.rfind("-"), cut.rfind("，"), cut.rfind("。"), cut.rfind("、"))
    if 16 <= last_sep < len(cut) - 1:
        cut = cut[:last_sep]
    return f"{seq:02d}-{cut.strip('-') or 'node'}"


def graph_md(run: dict) -> str:
    lines = [
        f"# 研究图 —— {run['run_id']}",
        "",
        "由协调人在每层调和后重写。机器可读的副本是 `run.json`；",
        "此文件的存在是为了让人一眼看清研究的形状。",
        "",
        "| 深度 | 节点 | 类型 | 父节点 | 问题 | 状态 | 结论 |",
        "|---|---|---|---|---|---|---|",
    ]
    for node in run["nodes"]:
        if not isinstance(node, dict):
            continue
        conclusion = node.get("synthesis") or "—"
        parents = ", ".join(node.get("parents") or []) or "—"
        lines.append(
            f"| {node.get('depth', '?')} | `{node.get('id') or '?'}` | {node.get('kind') or 'line'} | "
            f"{parents} | {one_line(node.get('question'))} | {node.get('status') or '?'} | `{conclusion}` |"
        )
    joins = [j for j in (run.get("joins") or []) if isinstance(j, dict)]
    if joins:
        lines += ["", "## 汇合（Joins）", ""]
        lines += [f"- `{j.get('id') or '?'}`: " + " + ".join(f"`{p}`" for p in j.get("parents") or [])
                  + (f" —— {one_line(j.get('rationale'))}" if one_line(j.get("rationale")) else "")
                  for j in joins]
    relations = [r for r in (run.get("relations") or []) if isinstance(r, dict)]
    if relations:
        lines += ["", "## 关系（Relations）", ""]
        lines += [f"- {r.get('kind')}: " + ", ".join(f"`{n}`" for n in r.get("nodes") or [])
                  + (f" —— {one_line(r.get('note'))}" if one_line(r.get("note")) else "")
                  for r in relations]
    declined = [d for d in (run.get("declined") or []) if isinstance(d, dict)]
    if declined:
        lines += ["", "## 已拒绝（Declined）", ""]
        lines += [f"- `{d.get('issue_id') or d.get('option') or '?'}`：{one_line(d.get('reason'))}"
                  for d in declined]
    lines.append("")
    return "\n".join(lines)


def paths_md(run: dict) -> str:
    lines = [
        f"# 路径表 —— {run['run_id']}",
        "",
        "本 run 提出过的每个可能及其归宿。一个可能只出现一次；",
        "提出新的之前，先查这里——run 是否已经带着它。",
        "",
        "| id | 提出于 | 可能 | 前提 | 归宿 |",
        "|---|---|---|---|---|",
    ]
    for decision in run.get("decisions") or []:
        if not isinstance(decision, dict):
            continue
        for option in decision.get("options") or []:
            if not isinstance(option, dict):
                continue
            outcome = "待定"
            if option.get("node"):
                outcome = f"由 `{option['node']}` 在追"
            elif option.get("covered_by"):
                outcome = f"被 `{option['covered_by']}` 覆盖"
            elif option.get("reason"):
                outcome = f"未开：{option['reason']}"
            lines.append(
                f"| `{option.get('id') or '?'}` | `{decision.get('decided_at') or '?'}` | "
                f"{one_line(option.get('label'))} | {one_line(option.get('premise'))} | {outcome} |"
            )
    if len(lines) == 7:
        lines.append("| — | — | _尚无记录_ | — | — |")
    lines.append("")
    return "\n".join(lines)


def node_md(run: dict, node: dict) -> str:
    lines = [
        f"# 节点 {node.get('id')}",
        "",
        f"- **问题：** {node.get('question')}",
        f"- **深度：** {node.get('depth')}",
        f"- **类型：** {node.get('kind') or 'line'}",
        f"- **父节点：** {', '.join(node.get('parents') or []) or '—（这就是用户所问的问题）'}",
    ]
    opened = node.get("opened_by")
    if opened:
        lines.append(f"- **开出方式：** {json.dumps(opened, ensure_ascii=False)}")
    lines += [
        "",
        "## 本节点在图上的位置",
        "",
        "_首次计划时填写：它追的是哪个选项、其前提是什么、它对父节点欠什么。_",
        "",
        "## 文件",
        "",
        "- `plan.md` —— 研究设计与它分派的卡",
        "- `cards/<card>/` —— 各研究员的交付物与笔记",
        "- `synthesis.md`、`synthesis-N.md` —— 结论及其修订",
        "- `sources.md` —— 本节点全部文本所依赖的文件",
        "",
    ]
    return "\n".join(lines)


# --------------------------------------------------------------------------- 账本读写

def load(run_dir: str) -> dict:
    path = os.path.join(run_dir, "run.json")
    try:
        with open(path, encoding="utf-8") as handle:
            run = json.load(handle)
    except (OSError, ValueError) as error:
        die(f"无法读取 {path}: {error}")
    if not isinstance(run, dict) or not isinstance(run.get("nodes"), list):
        die(f"{path} 不是一份 run 账本")
    return run


def save(run_dir: str, run: dict) -> None:
    run["updated_at"] = now()
    with open(os.path.join(run_dir, "run.json"), "w", encoding="utf-8") as handle:
        json.dump(run, handle, ensure_ascii=False, indent=2)
        handle.write("\n")
    with open(os.path.join(run_dir, "graph.md"), "w", encoding="utf-8") as handle:
        handle.write(graph_md(run))
    with open(os.path.join(run_dir, "paths.md"), "w", encoding="utf-8") as handle:
        handle.write(paths_md(run))


def pick_run(base: str, only: str | None) -> tuple[str, dict]:
    if not os.path.isdir(base):
        die(f"{base} 下没有 research/ 目录——先跑 scaffold.py 建 run")
    run_ids = sorted(d for d in os.listdir(base)
                     if os.path.isfile(os.path.join(base, d, "run.json")))
    if only:
        if only not in run_ids:
            die(f"找不到 run {only}；现有：{', '.join(run_ids) or '无'}")
        chosen = only
    else:
        if not run_ids:
            die(f"{base} 下没有 run")
        if len(run_ids) > 1:
            die(f"{base} 下有 {len(run_ids)} 个 run（{', '.join(run_ids)}）；用 --run 指定一个")
        chosen = run_ids[0]
    return os.path.join(base, chosen), load(os.path.join(base, chosen))


def find_node(run: dict, node_id: str) -> dict:
    for node in run["nodes"]:
        if isinstance(node, dict) and node.get("id") == node_id:
            return node
    die(f"本 run 里没有节点 {node_id}")


def blank_node(run: dict, node_id: str, seq: int, depth: int, question: str,
               kind: str, parents: list, opened_by) -> dict:
    return {
        "id": node_id,
        "folder": node_dir_name(node_id, seq, question),
        "seq": seq,
        "depth": depth,
        "kind": kind,
        "question": question,
        "parents": parents,
        "opened_by": opened_by,
        "status": "queued",
        "cards": [],
        "synthesis": None,
        "synthesis_versions": 0,
        "review_rounds": 0,
        "review_files": [],
        "possibility_file": None,
        "no_forks": False,
        "dissolves": None,
        "issues": [],
        "gaps": [],
    }


def make_node_dir(run_dir: str, run: dict, node: dict) -> str:
    """建节点目录与骨架文件；已存在时不覆盖进行中的工作。"""
    ndir = os.path.join(run_dir, "nodes", str(node["folder"]))
    os.makedirs(os.path.join(ndir, "cards"), exist_ok=True)
    for name, text in (("node.md", node_md(run, node)),
                       ("plan.md", "# 研究计划\n\n_尚未撰写。_\n"),
                       ("sources.md", "# 来源\n\n_尚未撰写。_\n")):
        path = os.path.join(ndir, name)
        if not os.path.exists(path):
            with open(path, "w", encoding="utf-8") as handle:
                handle.write(text)
    return ndir


# --------------------------------------------------------------------------- 子命令

def cmd_fork(run_dir: str, run: dict, args) -> int:
    parent = find_node(run, args.node)
    depth = parent.get("depth")
    if not isinstance(depth, int):
        die(f"父节点 {parent.get('id')} 的 depth 不是整数；先修账本")
    max_depth = (run.get("limits") or {}).get("depth")
    if isinstance(max_depth, int) and depth + 1 > max_depth:
        die(f"分叉到 depth {depth + 1} 超出 limits.depth={max_depth}；"
            f"要么提高限额（需用户同意并记录），要么把该选项记入 not_pursued")
    max_nodes = (run.get("limits") or {}).get("max_nodes")
    if isinstance(max_nodes, int) and len(run["nodes"]) + 1 > max_nodes:
        die(f"节点预算已满（{len(run['nodes'])}/{max_nodes}）；"
            f"把该选项记入 not_pursued 并写明预算约束")
    if not args.question.strip():
        die("--question 为空；新节点的问题要写成可规划的问句，不是选项标签")

    seq = args.seq or (max((n.get("seq") or 0) for n in run["nodes"] if isinstance(n, dict)) + 1)
    if args.seq and any((n.get("seq") == args.seq) for n in run["nodes"] if isinstance(n, dict)):
        die(f"seq {args.seq} 已占用；展示顺序必须唯一")
    node_id = args.id or new_id("n")
    if any(n.get("id") == node_id for n in run["nodes"] if isinstance(n, dict)):
        die(f"节点 id {node_id} 已存在")

    opened_by = None
    if args.option:
        opened_by = {"decision": args.decision or "", "option": args.option}
        if not args.decision:
            # 从决策里反查：一个选项只属于一个决策，不必让协调人重打一遍。
            for decision in run.get("decisions") or []:
                if not isinstance(decision, dict):
                    continue
                for option in decision.get("options") or []:
                    if isinstance(option, dict) and option.get("id") == args.option:
                        opened_by["decision"] = decision.get("id") or ""
        if not opened_by["decision"]:
            warn(f"选项 {args.option} 找不到所属决策；`opened_by.decision` 留空，"
                 f"check.py 会报 P1。建议补 --decision")
    node = blank_node(run, node_id, seq, depth + 1, args.question.strip(),
                      args.kind, [parent.get("id")], opened_by)
    run["nodes"].append(node)
    ndir = make_node_dir(run_dir, run, node)

    if args.option:
        linked = False
        for decision in run.get("decisions") or []:
            if not isinstance(decision, dict):
                continue
            for option in decision.get("options") or []:
                if isinstance(option, dict) and option.get("id") == args.option:
                    if option.get("node") and option["node"] != node_id:
                        die(f"选项 {args.option} 已由 {option['node']} 在追；一个可能只开一次"
                            f"（references/06-graph.md）")
                    option["node"] = node_id
                    option.pop("reason", None)
                    linked = True
        if not linked:
            warn(f"选项 {args.option} 不在任何决策里；新节点已开，但 paths.md 不会显示归宿")
    save(run_dir, run)
    print(f"已开节点 {node_id}（depth {depth + 1}，kind {args.kind}）于 {ndir}")
    print(f"下一步：写 {os.path.join('nodes', node['folder'], 'plan.md')}，然后跑 scripts/check.py")
    return 0


def cmd_join(run_dir: str, run: dict, args) -> int:
    parents = [p.strip() for p in args.parents.split(",") if p.strip()]
    if len(parents) < 2:
        die("汇合至少两个父节点")
    nodes = [find_node(run, p) for p in parents]
    for node in nodes:
        if node.get("status") not in NODE_TERMINAL:
            warn(f"父节点 {node.get('id')} 还是 {node.get('status')}，未终态；"
                 f"check.py 会报 P1。汇合应在父节点都完成后开")
    depths = [n.get("depth") for n in nodes if isinstance(n.get("depth"), int)]
    if not depths:
        die("父节点的 depth 都不是整数；先修账本")
    max_nodes = (run.get("limits") or {}).get("max_nodes")
    if isinstance(max_nodes, int) and len(run["nodes"]) + 1 > max_nodes:
        die(f"节点预算已满（{len(run['nodes'])}/{max_nodes}）")

    seq = args.seq or (max((n.get("seq") or 0) for n in run["nodes"] if isinstance(n, dict)) + 1)
    node_id = args.id or new_id("n")
    if any(n.get("id") == node_id for n in run["nodes"] if isinstance(n, dict)):
        die(f"节点 id {node_id} 已存在")
    if not args.question.strip():
        die("--question 为空；汇合节点的问题要写成可规划的问句")
    if not args.rationale.strip():
        die("--rationale 为空；写明每个父带来什么、它们在哪里不同")

    node = blank_node(run, node_id, seq, max(depths) + 1, args.question.strip(),
                      "join", parents, None)
    run["nodes"].append(node)
    run.setdefault("joins", []).append({
        "id": node_id, "parents": parents,
        "question": args.question.strip(), "rationale": args.rationale.strip(),
    })
    ndir = make_node_dir(run_dir, run, node)
    save(run_dir, run)
    print(f"已开汇合节点 {node_id}（父：{', '.join(parents)}）于 {ndir}")
    return 0


def cmd_advance(run_dir: str, run: dict, args) -> int:
    node = find_node(run, args.node)
    current = node.get("status")
    target = args.to or PHASE_AFTER.get(current)
    if not target:
        die(f"节点已是终态 {current}；不动它。重试用 scripts/node.py advance --to planning")
    if target not in NEXT_STATES.get(current, set()):
        allowed = ", ".join(sorted(NEXT_STATES.get(current, set()))) or "（无）"
        die(f"{current} → {target} 不是状态机允许的跃迁；从 {current} 可去：{allowed}")
    node["status"] = target
    note = ""
    if target == "closed":
        # 关闭是协议里最重的动作。缺什么就说什么，让协调人去补——不要替它编。
        problems = []
        if not node.get("synthesis"):
            problems.append("synthesis 未记（结论文件名）")
        if not (node.get("review_rounds") or 0):
            problems.append("review_rounds 为 0")
        if not node.get("possibility_file"):
            problems.append("possibility_file 未记")
        if not node.get("no_forks") and not any(
                isinstance(d, dict) and d.get("decided_at") == node.get("id")
                for d in run.get("decisions") or []):
            problems.append("既无决策点名本节点，也无 no_forks")
        if problems:
            node["status"] = current
            die("不能置 closed：" + "；".join(problems)
                + "。补齐后再 advance，或先置 deciding 继续流程")
        note = "（四项前提已齐）"
    save(run_dir, run)
    print(f"节点 {node.get('id')}：{current} → {target}{note}")
    return 0


def parse_option(spec: str) -> dict:
    option: dict = {}
    for part in spec.split(","):
        part = part.strip()
        if not part:
            continue
        if "=" in part:
            key, value = part.split("=", 1)
            option[key.strip()] = value.strip()
        elif part == "own":
            option["own"] = True
        else:
            die(f"无法解析 --option 片段 {part!r}；用 id=,label=,premise= 形式，own 单独写")
    if not option.get("id"):
        die("每个 --option 都要有 id=")
    return option


def cmd_decide(run_dir: str, run: dict, args) -> int:
    node = find_node(run, args.node)
    options = [parse_option(spec) for spec in args.option]
    if args.no_forks:
        # "Nothing forks" is a declaration, not a decision: it has no question and no
        # options, only the reason the question admits one line here.
        if options:
            die("--no-forks 与 --option 不能同用；无分叉就是一个明确的声明，不是一条决策")
        if not args.reason.strip():
            die("--no-forks 需要 --reason：写明为何此处只容一条回答线")
        node["no_forks"] = True
        run.setdefault("not_pursued", []).append({
            "option": "", "reason": args.reason.strip(),
        })
        save(run_dir, run)
        print(f"节点 {node.get('id')}：已记 no_forks（{args.reason.strip()}）")
        return 0
    if not args.question.strip():
        die("--question 为空；决策要写成带利害的问题")
    if not args.stakes.strip():
        die("--stakes 为空；写明答案取决于它的是什么")
    if len(options) < 2:
        die("一个决策至少两个选项；无分叉就用 --no-forks --reason ...")
    seen = set()
    for decision in run.get("decisions") or []:
        if not isinstance(decision, dict):
            continue
        if decision.get("id") == args.id:
            die(f"决策 id {args.id} 已存在")
        for option in decision.get("options") or []:
            if isinstance(option, dict) and option.get("id"):
                seen.add(option["id"])
    for option in options:
        if option["id"] in seen:
            die(f"选项 id {option['id']} 已在本 run 用过；一个可能只出现一次")
        seen.add(option["id"])
        if not option.get("premise"):
            die(f"选项 {option['id']} 缺 premise=；不陈述假设的路无法被判断")
        for key in ("node", "covered_by", "reason"):
            if key in option and not option[key]:
                option.pop(key)
        filled = [k for k in ("node", "covered_by", "reason") if option.get(k)]
        if len(filled) > 1:
            die(f"选项 {option['id']} 同时给了 {', '.join(filled)}；一个选项恰好一个归宿")
        if option.get("node") and option["node"] not in {n.get("id") for n in run["nodes"]
                                                         if isinstance(n, dict)}:
            die(f"选项 {option['id']} 由 {option['node']} 在追，但那不是本 run 的节点")
        option.setdefault("own", False)
        option.setdefault("label", option["id"])
    if sum(1 for o in options if o.get("own")) > 1:
        die("至多一个选项可以是本节点自己的线（own）")

    run.setdefault("decisions", []).append({
        "id": args.id or new_id("d"),
        "decided_at": node.get("id"),
        "question": args.question.strip(),
        "stakes": args.stakes.strip(),
        "options": options,
    })
    if node.get("status") == "deciding":
        node["status"] = "closed"
        print(f"节点 {node.get('id')}：deciding → closed（决策已记）")
    save(run_dir, run)
    print(f"已记决策 {args.id} 于节点 {node.get('id')}：{len(options)} 个选项")
    print("待决选项请用 `node.py PROJECT fork --node <id> --option <option-id> --question \"...\"` 开出")
    return 0


def cmd_spend(run_dir: str, run: dict, args) -> int:
    """记一笔真实开销。账本此前没有 token/cost 字段，成本视图因此只能靠系数虚构。"""
    if args.tokens is None and args.calls is None and args.usd is None:
        die("至少给 --tokens、--calls 或 --usd 之一")
    for name, value in (("tokens", args.tokens), ("calls", args.calls)):
        if value is not None and (not isinstance(value, int) or value < 0):
            die(f"--{name} 必须是非负整数")
    if args.usd is not None and args.usd < 0:
        die("--usd 必须是非负数")
    node = find_node(run, args.node) if args.node else None
    cost = run.setdefault("cost", {"tokens": 0, "calls": 0, "usd": 0.0, "entries": []})
    if not isinstance(cost, dict):
        die("run.json 的 `cost` 不是对象；先修账本")
    entry = {
        "at": now(),
        "node": node.get("id") if node else None,
        "tokens": args.tokens or 0,
        "calls": args.calls or 0,
        "usd": args.usd or 0.0,
        "what": args.what.strip() if args.what else "",
    }
    cost["tokens"] = int(cost.get("tokens") or 0) + entry["tokens"]
    cost["calls"] = int(cost.get("calls") or 0) + entry["calls"]
    cost["usd"] = round(float(cost.get("usd") or 0.0) + entry["usd"], 4)
    cost.setdefault("entries", []).append(entry)
    save(run_dir, run)
    print(f"已记开销：+{entry['tokens']} token，+{entry['calls']} 次派发，+{entry['usd']} USD"
          + (f"（节点 {node.get('id')}）" if node else ""))
    print(f"累计：{cost['tokens']} token，{cost['calls']} 次派发，{cost['usd']} USD")
    return 0


def cmd_relation(run_dir: str, run: dict, args) -> int:
    nodes = [n.strip() for n in args.nodes.split(",") if n.strip()]
    if len(nodes) < 2:
        die("关系至少点名两个节点")
    for nid in nodes:
        find_node(run, nid)
    if args.kind not in RELATION_KINDS:
        die(f"未知关系类型 {args.kind!r}；用 {', '.join(sorted(RELATION_KINDS))}")
    run.setdefault("relations", []).append({
        "kind": args.kind, "nodes": nodes, "note": (args.note or "").strip(),
    })
    save(run_dir, run)
    print(f"已记关系 {args.kind}：{', '.join(nodes)}")
    return 0


def cmd_decline(run_dir: str, run: dict, args) -> int:
    """记录一条被拒绝的提案。`declined` 此前只在 05-possibility.md 的示例里存在。"""
    if not args.option.strip():
        die("--option 为空；点名被拒绝的提案或选项 id")
    reason = args.reason.strip()
    if not reason:
        die("--reason 为空；拒绝必须写明约束")
    lowered = reason.lower()
    if any(p in lowered for p in ("not worth it", "not worthwhile", "low value", "不值得", "意义不大")):
        die(f"{reason!r} 不是理由；点名拦住它的约束（预算、深度、已被追、互补）")
    run.setdefault("declined", []).append({
        "issue_id": args.option.strip(), "disposition": "decline", "reason": reason,
        "covered_by": args.covered_by.strip() if args.covered_by else "",
    })
    save(run_dir, run)
    print(f"已记拒绝：{args.option.strip()} —— {reason}")
    return 0


def main(argv=None) -> int:
    p = argparse.ArgumentParser(prog="node.py", description=__doc__.splitlines()[0])
    p.add_argument("project", help="研究所在的项目文件夹")
    p.add_argument("--run", help="操作这个 run（项目里只有一个时可省）")
    sub = p.add_subparsers(dest="command", required=True)

    f = sub.add_parser("fork", help="从某节点分叉出一个新节点")
    f.add_argument("--node", required=True, help="父节点 id")
    f.add_argument("--question", required=True, help="新节点的问题（可规划的问句）")
    f.add_argument("--kind", default="line", choices=sorted(NODE_KINDS - {"root", "join"}),
                   help="新节点类型（默认 line）")
    f.add_argument("--option", help="它追的那个选项 id（会把该选项的 node 指向新节点）")
    f.add_argument("--decision", help="该选项所属决策 id（给 --option 时可省，会自动反查）")
    f.add_argument("--id", help="指定新节点 id（默认生成 n_xxxxxxxx）")
    f.add_argument("--seq", type=int, help="展示顺序（默认取现有最大 seq + 1）")

    j = sub.add_parser("join", help="把多个已完成节点汇合成一个新节点")
    j.add_argument("--parents", required=True, help="父节点 id，逗号分隔（≥2）")
    j.add_argument("--question", required=True)
    j.add_argument("--rationale", required=True, help="每个父带来什么、它们在哪里不同")
    j.add_argument("--id", help="指定新节点 id")
    j.add_argument("--seq", type=int)

    a = sub.add_parser("advance", help="把节点推进到下一状态（或 --to 指定）")
    a.add_argument("node", help="节点 id")
    a.add_argument("--to", help=f"目标状态（默认按状态机下一态）")

    d = sub.add_parser("decide", help="记一条分叉决策，或声明无分叉")
    d.add_argument("--node", required=True, help="做出决策的节点 id")
    d.add_argument("--id", help="决策 id（默认生成 d_xxxxxxxx）")
    d.add_argument("--question", default="", help="带利害的问题")
    d.add_argument("--stakes", default="", help="取决于它的是什么")
    d.add_argument("--option", action="append", default=[],
                   help="一个选项：id=o1,label=...,premise=...[,own][,node=<id>][,reason=...]")
    d.add_argument("--no-forks", action="store_true", help="声明本节点无分叉")
    d.add_argument("--reason", default="", help="--no-forks 时的理由")

    s = sub.add_parser("spend", help="记一笔真实开销（token / 派发次数 / 金额）")
    s.add_argument("--node", help="归属节点（可省：run 级开销）")
    s.add_argument("--tokens", type=int)
    s.add_argument("--calls", type=int)
    s.add_argument("--usd", type=float)
    s.add_argument("--what", default="", help="这笔开销是什么（卡、审查、终稿）")

    r = sub.add_parser("relation", help="记一条节点间关系")
    r.add_argument("--kind", required=True, choices=sorted(RELATION_KINDS))
    r.add_argument("--nodes", required=True, help="节点 id，逗号分隔（≥2）")
    r.add_argument("--note", default="", help="它们共享什么、在哪里不同")

    x = sub.add_parser("decline", help="记一条被拒绝的提案及其约束")
    x.add_argument("--option", required=True, help="被拒绝的提案或选项 id")
    x.add_argument("--reason", required=True, help="拦住它的约束")
    x.add_argument("--covered_by", default="", help="若已有节点在追它，点名该节点")

    args = p.parse_args(argv)

    project = os.path.realpath(os.path.expanduser(args.project))
    run_dir, run = pick_run(os.path.join(project, "research"), args.run)
    handlers = {"fork": cmd_fork, "join": cmd_join, "advance": cmd_advance,
                "decide": cmd_decide, "spend": cmd_spend, "relation": cmd_relation,
                "decline": cmd_decline}
    return handlers[args.command](run_dir, run, args)


if __name__ == "__main__":
    sys.exit(main())
