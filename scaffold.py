#!/usr/bin/env python3
"""为一次研究 run 建立磁盘骨架。

用法：
    python3 scaffold.py PROJECT --question "..." [--depth 3] [--max-nodes 30]
                        [--parallel 3] [--cards 3] [--followups 2] [--revisions 2]
                        [--approval require|auto] [--language auto|zh|en]

在 PROJECT/research/<run-id>/ 下写入：
    run.json          账本，后续每个阶段都更新它
    question.md       用户原话的研究问题
    graph.md          节点表，协调人每层调和后重写
    paths.md          提出过的每个可能及其归宿
    nodes/<node>/     每节点一个文件夹（此处创建根节点）
    final/            run 级产物

退出码：0 创建成功；2 拒绝（参数不合法，或已存在的 run 会被覆盖）。
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

PLACEHOLDER_MARKERS = ("TODO", "FIXME", "TBD", "<insert", "占位")

NODE_TERMINAL = {"closed", "skipped", "failed"}
# 恢复时每个状态该从哪个阶段接续（与 references/09-ledger.md 的状态机一致）。
RESUME_HINT = {
    "queued": "读 references/01-plan.md，写 plan.md",
    "planning": "继续写 plan.md，然后按审批设置等放行或直接派卡",
    "awaiting_approval": "计划已记，等用户放行；放行后置 executing 再派卡",
    "executing": "卡在跑：重读 plan.md 与各卡交付物，收齐后进 synthesizing",
    "synthesizing": "读 references/03-synthesis.md，写或修订 synthesis-N.md",
    "reviewing": "派审查员做批判审查（references/04-critique.md）",
    "disposing": "逐条处置 issues（references/04-critique.md）",
    "possibility": "新会话跑可能性审查（references/05-possibility.md）",
    "filling_gaps": "处置 gaps：一张卡填它，或 concede / park",
    "deciding": "记分叉决策，然后置 closed",
}


def die(message: str, code: int = 2) -> None:
    print(f"scaffold: {message}", file=sys.stderr)
    raise SystemExit(code)


def warn(message: str) -> None:
    print(f"scaffold: 警告：{message}", file=sys.stderr)


def new_id(prefix: str) -> str:
    return f"{prefix}_{secrets.token_hex(4)}"


def node_dir_name(node_id: str, seq: int, question: str) -> str:
    """稳定、人眼可扫的文件夹名：01-<slug>。id 留在 run.json 里。

    截断尽量落在分隔符（'-'）或 CJK 标点上，避免切出半个词或以连字符收尾。
    """
    slug = re.sub(r"[^\w\u4e00-\u9fff]+", "-", question.strip().lower()).strip("-")
    cut = slug[:40]
    # 切点落在词中间时退回到最后一个分隔符（分隔符位置太靠前则不退，保留更多信息）
    last_sep = max(cut.rfind("-"), cut.rfind("，"), cut.rfind("。"), cut.rfind("、"))
    if 16 <= last_sep < len(cut) - 1:
        cut = cut[:last_sep]
    return f"{seq:02d}-{cut.strip('-') or 'node'}"


def validate_question(question: str) -> None:
    """研究问题的合理性检查：硬错误拒绝建 run，软警告放行但说清楚。"""
    if len(question) < 8:
        die(f"--question 太短（{len(question)} 字符）：一个研究问题至少要说清对象与疑问，"
            f"例如 \"1918年大流感改变了日本的公共卫生立法吗？\"。"
            f"查单个事实/日期/名词不需要建 run，直接回答即可。")
    if len(question) > 500:
        warn(f"问题长达 {len(question)} 字符。超长问题往往混着多个子问题——"
             f"考虑拆分，或把各子问题交给不同的卡。")
    marks = question.count("？") + question.count("?")
    if marks >= 3:
        warn(f"问题里有 {marks} 个问号。多个独立问题应各自成卡（同一 run 的覆盖表里分行），"
             f"而不是都塞进根问题。")
    if question.endswith(("。", ".", "；", ";")):
        warn("问题以句号/分号结尾。研究问题通常以问句收尾；若是陈述式任务，确认它确实要的是研究而非执行。")
    for marker in PLACEHOLDER_MARKERS:
        if marker in question:
            die(f"--question 含占位符 {marker!r}：请传入用户原话的完整问题，不要传模板。")
    if re.fullmatch(r"[什么怎么如何为什么为啥儿]{1,3}", question.strip()):
        die("--question 只有疑问词没有对象。请传入完整问题。")


def validate_limits(args) -> None:
    """限额的合理区间：下限是硬错误（原有），上限区分警告（贵但合法）与硬错误（明显误用）。"""
    if args.depth > 4:
        warn(f"--depth {args.depth}：每层节点数按选项数相乘，30 节点预算在 depth 3 通常已用尽。"
             f"确认问题真的需要这么深的分叉树，否则建议 ≤3。")
    if args.max_nodes > 50:
        warn(f"--max-nodes {args.max_nodes}：每个节点都是一组派发（卡＋审查）。"
             f"按\"成本\"一节的估算想清楚再跑。")
    if args.parallel > 6:
        warn(f"--parallel {args.parallel}：并行过高会撞供应方限流（实战中 8 并发曾被 502 拒）。"
             f"建议 ≤3，用户明确要求才提高。")
    if args.cards > 16:
        die(f"--cards {args.cards} 超出合理上限（16）。一张卡是一个研究员会话；"
            f"需要这么多卡的问题应拆成多个节点或多个 run。")
    if args.cards > 8:
        warn(f"--cards {args.cards}：单节点 8 卡以上，协调人的阅读量与审查成本都会显著上升，"
             f"考虑按问题结构拆节点。")
    if args.followups > 4:
        warn(f"--followups {args.followups}：后续轮是补缺口的，不是补广度的。")
    if args.revisions > 4:
        warn(f"--revisions {args.revisions}：若结论需要这么多轮修订，通常说明审查与写作的配合有问题。")


def check_duplicate_question(project: str, question: str) -> None:
    """同一项目里已有相同问题的 run 时提醒一句（不阻止——重跑是合法需求）。"""
    base = os.path.join(project, "research")
    if not os.path.isdir(base):
        return
    for entry in sorted(os.listdir(base)):
        ledger = os.path.join(base, entry, "run.json")
        if not os.path.isfile(ledger):
            continue
        try:
            with open(ledger, encoding="utf-8") as handle:
                prior = json.load(handle)
        except (OSError, ValueError):
            continue
        if isinstance(prior, dict) and prior.get("question") == question:
            status = prior.get("status", "?")
            warn(f"项目里已有同问题的 run：{entry}（status: {status}）。"
                 f"要续跑请用 --resume {entry}；确属重跑才继续。")
            return


def main(argv=None) -> int:
    p = argparse.ArgumentParser(prog="scaffold.py", description=__doc__.splitlines()[0])
    p.add_argument("project", help="研究写入的项目文件夹；不存在则创建")
    p.add_argument("--question", help="研究问题，用户原话（--resume 时不需要）")
    p.add_argument("--depth", type=int, default=3, help="问题之下允许的另类路径层数（默认 3）")
    p.add_argument("--max-nodes", type=int, default=30, help="节点预算，含根节点（默认 30）")
    p.add_argument("--parallel", type=int, default=3, help="同时运行的节点数（默认 3）")
    p.add_argument("--cards", type=int, default=3, help="每节点同时运行的研究员数（默认 3）")
    p.add_argument("--followups", type=int, default=2, help="首批卡之后允许的追补轮数（默认 2）")
    p.add_argument("--revisions", type=int, default=2, help="每轮审查循环的结论修订次数（默认 2）")
    p.add_argument("--approval", choices=("require", "auto"), default="require",
                   help="计划是否等用户放行（默认 require）")
    p.add_argument("--language", default="auto", help="报告语言：auto、zh、en 或语言标签如 ja（默认 auto）")
    p.add_argument("--run-id", help="使用此 run id 而不是生成一个")
    p.add_argument("--force", action="store_true",
                   help="写入已存在的 run 文件夹，只补缺失文件。已有 run.json 绝不覆盖；重建视图用 --resume。")
    p.add_argument("--resume", action="store_true",
                   help="从 run.json 重建派生视图（graph.md、paths.md），不碰其他任何东西。"
                        "项目里恰好只有一个 run 时可省略 --run-id。")
    p.add_argument("--node", dest="resume_node",
                   help="--resume 时只重建该节点的视图，并报告它下次该从哪个阶段接续"
                        "（默认重建全部节点视图并报告第一个非终态节点）")
    args = p.parse_args(argv)

    question = (args.question or "").strip()
    if args.depth < 0:
        die("--depth 必须 ≥ 0")
    if args.max_nodes < 1:
        die("--max-nodes 至少为 1（问题本身就是一个节点）")
    for name in ("parallel", "cards"):
        if getattr(args, name) < 1:
            die(f"--{name} 必须 ≥ 1")
    for name in ("followups", "revisions"):
        value = getattr(args, name)
        if not 0 <= value <= 6:
            die(f"--{name} 必须在 0 到 6 之间")

    if args.resume and not args.run_id:
        return resume(pick_run(os.path.join(
            os.path.realpath(os.path.expanduser(args.project)), "research")), args.resume_node)

    project = os.path.realpath(os.path.expanduser(args.project))

    if args.resume:
        return resume(os.path.join(project, "research", args.run_id), args.resume_node)

    if not question:
        die("--question 为空")

    validate_question(question)
    validate_limits(args)

    os.makedirs(project, exist_ok=True)
    check_duplicate_question(project, question)
    base = os.path.join(project, "research")
    run_id = args.run_id or new_id("r")
    if not re.fullmatch(r"[A-Za-z0-9_.-]{1,64}", run_id):
        die("--run-id 只能含字母、数字、点、连字符、下划线，长度 1–64")

    run_dir = os.path.join(base, run_id)

    exists = os.path.isdir(run_dir) and os.path.isfile(os.path.join(run_dir, "run.json"))
    if exists and not args.force:
        die(f"{run_dir} 已有 run.json；用 --resume 重建其视图、--force 只补缺文件，"
            f"或换一个 --run-id")
    if os.path.isdir(run_dir) and os.listdir(run_dir) and not (args.force or exists):
        die(f"{run_dir} 非空且没有 run.json；拒绝把新 run 混进去")

    nodes_root = os.path.join(run_dir, "nodes")
    final_root = os.path.join(run_dir, "final")
    for path in (run_dir, nodes_root, final_root):
        os.makedirs(path, exist_ok=True)

    if exists:
        # 对已有 run 用 --force：只补缺，绝不重写账本与问题。
        run = load_run(run_dir)
        root_id = run["nodes"][0]["id"] if run.get("nodes") else None
        root_dir = os.path.join(nodes_root, run["nodes"][0]["folder"]) if root_id else None
        made = []
        if root_dir:
            for sub in ("cards", "sources"):
                made.append(ensure_dir(os.path.join(root_dir, sub)))
            made.append(ensure_file(os.path.join(root_dir, "node.md"), node_md(run, run["nodes"][0])))
            made.append(ensure_file(os.path.join(root_dir, "plan.md"), "# 研究计划\n\n_尚未撰写。_\n"))
            made.append(ensure_file(os.path.join(root_dir, "sources.md"), "# 来源\n\n_尚未撰写。_\n"))
        made.append(ensure_file(os.path.join(run_dir, "graph.md"), graph_md(run)))
        made.append(ensure_file(os.path.join(run_dir, "paths.md"), paths_md(run)))
        created = [m for m in made if m]
        print(f"run {run_id} 已存在于 {run_dir}")
        print("补建了：" + ("、".join(created) if created else "没有缺失文件"))
        print("run.json 与 question.md 未改动")
        return 0

    node_id = new_id("n")
    folder = node_dir_name(node_id, 1, question)
    root_dir = os.path.join(nodes_root, folder)
    for sub in ("cards", "sources"):
        os.makedirs(os.path.join(root_dir, sub), exist_ok=True)

    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    run = {
        "schema": SCHEMA,
        "run_id": run_id,
        "created_at": now,
        "updated_at": now,
        "project": project,
        "question": question,
        "language": args.language,
        "status": "active",
        "independent": True,
        "independent_note": "",
        "limits": {
            "depth": args.depth,
            "max_nodes": args.max_nodes,
            "parallel": args.parallel,
            "cards": args.cards,
            "followups": args.followups,
            "revisions": args.revisions,
            "plan_approval": args.approval,
        },
        "nodes": [
            {
                "id": node_id,
                "folder": folder,
                "seq": 1,
                "depth": 0,
                "parents": [],
                "question": question,
                "kind": "root",
                "status": "queued",
                "opened_by": None,
                "cards": [],
                "synthesis": None,
                "synthesis_versions": 0,
                "review_rounds": 0,
                "dissolves": None,
                "issues": [],
                "gaps": [],
            }
        ],
        "decisions": [],
        "joins": [],
        "not_pursued": [],
        "declined": [],
        "relations": [],
        "alternatives": [],
        "errata": [],
        "consent": {"dissolution": None, "note": ""},
        "cost": {"tokens": 0, "calls": 0, "usd": 0.0, "entries": []},
    }

    write(os.path.join(run_dir, "run.json"), json.dumps(run, ensure_ascii=False, indent=2) + "\n")
    write(os.path.join(run_dir, "question.md"), f"# 研究问题\n\n{question}\n")
    write(os.path.join(run_dir, "graph.md"), graph_md(run))
    write(os.path.join(run_dir, "paths.md"), paths_md(run))
    write(os.path.join(root_dir, "node.md"), node_md(run, run["nodes"][0]))
    write(os.path.join(root_dir, "plan.md"), "# 研究计划\n\n_尚未撰写。_\n")
    write(os.path.join(root_dir, "sources.md"), "# 来源\n\n_尚未撰写。_\n")

    print(f"run {run_id} 创建于 {run_dir}")
    print(f"根节点 {node_id} 位于 {root_dir}")
    print("下一步：写 nodes/<node>/plan.md，然后跑 scripts/check.py")
    return 0


def write(path: str, text: str) -> None:
    with open(path, "w", encoding="utf-8") as handle:
        handle.write(text)


def ensure_dir(path: str) -> str | None:
    """目录不存在则创建；建了才返回其名。"""
    if os.path.isdir(path):
        return None
    os.makedirs(path, exist_ok=True)
    return os.path.basename(path) + "/"


def ensure_file(path: str, text: str) -> str | None:
    """只在文件缺失时写入；绝不覆盖进行中的工作。"""
    if os.path.exists(path):
        return None
    write(path, text)
    return os.path.basename(path)


def load_run(run_dir: str) -> dict:
    path = os.path.join(run_dir, "run.json")
    try:
        with open(path, encoding="utf-8") as handle:
            run = json.load(handle)
    except (OSError, ValueError) as error:
        die(f"无法读取 {path}: {error}")
    if not isinstance(run, dict) or not isinstance(run.get("nodes"), list):
        die(f"{path} 不是一份 run 账本")
    return run


def pick_run(base: str) -> str:
    """项目里唯一的 run，供省略 --run-id 的 --resume 用。"""
    if not os.path.isdir(base):
        die(f"{base} 下没有 research/")
    runs = [os.path.join(base, d) for d in sorted(os.listdir(base))
            if os.path.isfile(os.path.join(base, d, "run.json"))]
    if not runs:
        die(f"{base} 下没有 run.json")
    if len(runs) > 1:
        die(f"{base} 下有 {len(runs)} 个 run；用 --run-id 选一个："
            + ", ".join(os.path.basename(r) for r in runs))
    return runs[0]


def resume(run_dir: str, only_node: str | None = None) -> int:
    """从 run.json 重建视图，其他一概不碰。

    `--node <id>` 时只重建该节点的视图并打印它该从哪个阶段接续；否则重建全部，并点名
    第一个非终态节点——那是恢复的手把处。
    """
    if not os.path.isfile(os.path.join(run_dir, "run.json")):
        die(f"{run_dir} 下没有 run.json；无从恢复")
    run = load_run(run_dir)
    write(os.path.join(run_dir, "graph.md"), graph_md(run))
    write(os.path.join(run_dir, "paths.md"), paths_md(run))
    nodes = [n for n in (run.get("nodes") or []) if isinstance(n, dict)]
    if only_node:
        target = next((n for n in nodes if n.get("id") == only_node), None)
        if target is None:
            die(f"本 run 里没有节点 {only_node}；现有："
                + ", ".join(str(n.get("id")) for n in nodes))
        nodes = [target]
    missing = []
    for node in nodes:
        if not node.get("folder"):
            continue
        ndir = os.path.join(run_dir, "nodes", str(node["folder"]))
        if not os.path.isdir(ndir):
            missing.append(str(node["folder"]))
            continue
        ensure_file(os.path.join(ndir, "node.md"), node_md(run, node))
    print(f"run {run.get('run_id')} 的视图已重写")
    next_up = next((n for n in nodes if n.get("status") not in NODE_TERMINAL), None)
    if only_node:
        print(f"节点 {only_node}：status={only_node and nodes[0].get('status')}"
              f" → {RESUME_HINT.get(nodes[0].get('status'), '已终态；无需接续')}")
    elif next_up is not None:
        print(f"续跑点：节点 {next_up.get('id')}（status={next_up.get('status')}）"
              f" → {RESUME_HINT.get(next_up.get('status'), '继续')}")
        print(f"  目录：{os.path.join(run_dir, 'nodes', str(next_up.get('folder') or ''))}")
    else:
        print("所有节点已终态；接 references/07-report.md 写终稿。")
    if missing:
        print("警告：账本记录的节点文件夹缺失：" + ", ".join(missing), file=sys.stderr)
        print("      先跑 scripts/check.py，对齐账本后再继续；中断会话遗留的材料须逐字核对后才能引用", file=sys.stderr)
        return 1
    return 0


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
    if run.get("relations"):
        lines += ["", "## 关系（Relations）", ""]
        # `note` is optional: check.py only warns when it is missing, so this view must not
        # assume it. A relation without a note still names its nodes.
        lines += [f"- {r['kind']}: " + ", ".join(f"`{n}`" for n in r.get("nodes") or [])
                  + (f" —— {one_line(r.get('note'))}" if one_line(r.get("note")) else "")
                  for r in run["relations"] if isinstance(r, dict)]
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
        f"# 节点 {node['id']}",
        "",
        f"- **问题：** {node['question']}",
        f"- **深度：** {node['depth']}",
        f"- **类型：** {node.get('kind') or 'line'}",
        f"- **父节点：** {', '.join(node.get('parents') or []) or '—（这就是用户所问的问题）'}",
    ]
    if node.get("opened_by"):
        lines.append(f"- **开出方式：** {node['opened_by']}")
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


def one_line(text: object, limit: int = 120) -> str:
    flat = " ".join(str(text).split())
    return flat if len(flat) <= limit else flat[: limit - 1] + "…"


if __name__ == "__main__":
    sys.exit(main())
