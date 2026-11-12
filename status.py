#!/usr/bin/env python3
"""查看研究 run 的进度、预算用量与停滞节点。

用法：
    python3 status.py PROJECT [--run RUN-ID] [--stale-hours N] [--json] [--cost]

对项目下每个 run（或指定 run）打印：
    - run 状态、问题、账本更新时间与距今多久；
    - 预算用量：已开节点数 / max_nodes，已派卡数，审查轮数；
    - 每节点：所处阶段、卡、结论版本、审查轮数、目录最后活动时间；
    - 停滞警示：非终态节点且账本与目录都长时间无动静；
    - 缺失文件摘要（closed 节点的四项前提、final 四阶段）。

只读，不写任何文件。退出码：0 正常；1 发现停滞的非终态节点（供自动化用）；
2 参数错误。
仅标准库；无网络。
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime, timezone, timedelta

TERMINAL_NODE = {"closed", "skipped", "failed"}
PHASE_HINT = {
    "queued": "尚未开始",
    "planning": "写计划",
    "awaiting_approval": "等用户放行",
    "executing": "卡在跑",
    "synthesizing": "写结论",
    "reviewing": "批判审查在跑",
    "disposing": "处置异议",
    "possibility": "可能性审查在跑",
    "filling_gaps": "补缺口",
    "deciding": "分叉决策",
    "closed": "已关闭",
    "skipped": "经用户跳过",
    "failed": "失败",
}


def die(message: str, code: int = 2) -> None:
    print(f"status: {message}", file=sys.stderr)
    raise SystemExit(code)


def parse_time(stamp) -> datetime | None:
    if not isinstance(stamp, str) or not stamp:
        return None
    text = stamp.strip().replace("Z", "+00:00")
    try:
        return datetime.fromisoformat(text)
    except ValueError:
        return None


def dir_last_activity(path: str) -> datetime | None:
    """目录树里所有文件 mtime 的最大值；目录不存在返回 None。"""
    if not os.path.isdir(path):
        return None
    latest = None
    for root, _dirs, files in os.walk(path):
        for name in files:
            try:
                mtime = datetime.fromtimestamp(os.path.getmtime(os.path.join(root, name)), timezone.utc)
            except OSError:
                continue
            if latest is None or mtime > latest:
                latest = mtime
    return latest


def load_ledger(run_dir: str):
    path = os.path.join(run_dir, "run.json")
    try:
        with open(path, encoding="utf-8") as handle:
            return json.load(handle)
    except (OSError, ValueError) as error:
        return {"_error": f"无法读取 run.json: {error}"}


def node_missing_files(run: dict, node: dict, run_dir: str) -> list[str]:
    """closed 节点的四项前提 + 各状态常见文件，快速点名缺失。"""
    if node.get("status") != "closed":
        return []
    missing = []
    node_dir = os.path.join(run_dir, "nodes", str(node.get("folder") or ""))
    synthesis = node.get("synthesis")
    if not synthesis or not os.path.isfile(os.path.join(node_dir, str(synthesis))):
        missing.append("synthesis")
    if not node.get("review_files"):
        missing.append("review_files")
    else:
        for name in node.get("review_files"):
            if not os.path.isfile(os.path.join(node_dir, str(name))):
                missing.append(f"review:{name}")
    possibility = node.get("possibility_file")
    if not possibility or not os.path.isfile(os.path.join(node_dir, str(possibility))):
        missing.append("possibility_file")
    return missing


def final_missing(run: dict, run_dir: str) -> list[str]:
    if run.get("status") != "done":
        return []
    stages = run.get("final") if isinstance(run.get("final"), dict) else {}
    missing = []
    final_dir = os.path.join(run_dir, "final")
    for stage in ("survey", "draft", "review", "final"):
        name = stages.get(stage)
        if not name or not os.path.isfile(os.path.join(final_dir, str(name))):
            missing.append(stage)
    if not os.path.isdir(os.path.join(final_dir, "sources")):
        missing.append("final/sources/")
    return missing


def fmt_age(delta) -> str:
    if delta is None:
        return "未知"
    seconds = delta.total_seconds()
    if seconds < 90:
        return f"{int(seconds)} 秒前"
    if seconds < 90 * 60:
        return f"{int(seconds // 60)} 分钟前"
    if seconds < 36 * 3600:
        return f"{delta.seconds // 3600 + int(delta.days) * 24} 小时前"
    return f"{delta.days} 天前"


def collect(project: str, only_run: str | None, stale_hours: float) -> tuple[list[dict], list[str]]:
    base = os.path.join(project, "research")
    if not os.path.isdir(base):
        die(f"{project} 下没有 research/ 目录——先跑 scaffold.py 建 run")
    run_ids = sorted(d for d in os.listdir(base)
                     if os.path.isfile(os.path.join(base, d, "run.json")))
    if only_run:
        if only_run not in run_ids:
            die(f"找不到 run {only_run}；现有：{', '.join(run_ids) or '无'}")
        run_ids = [only_run]
    now = datetime.now(timezone.utc)
    threshold = timedelta(hours=stale_hours)
    summaries, stale = [], []
    for run_id in run_ids:
        run_dir = os.path.join(base, run_id)
        run = load_ledger(run_dir)
        if "_error" in run:
            summaries.append({"run_id": run_id, "error": run["_error"], "nodes": []})
            continue
        limits = run.get("limits") if isinstance(run.get("limits"), dict) else {}
        nodes_out = []
        for node in run.get("nodes") or []:
            if not isinstance(node, dict):
                continue
            node_dir = os.path.join(run_dir, "nodes", str(node.get("folder") or ""))
            activity = dir_last_activity(node_dir)
            updated = parse_time(run.get("updated_at"))
            status = str(node.get("status") or "?")
            is_stale = False
            if status not in TERMINAL_NODE and stale_hours > 0:
                reference = updated or activity
                if reference is not None and (now - reference) > threshold:
                    is_stale = True
            entry = {
                "id": node.get("id"),
                "folder": node.get("folder"),
                "depth": node.get("depth"),
                "kind": node.get("kind") or "line",
                "status": status,
                "phase": PHASE_HINT.get(status, status),
                "cards": len(node.get("cards") or []),
                "synthesis_versions": node.get("synthesis_versions") or 0,
                "review_rounds": node.get("review_rounds") or 0,
                "card_note": bool(one_line(node.get("card_note"))) if isinstance(node.get("card_note"), (str, list)) else False,
                "last_activity": activity.isoformat() if activity else None,
                "stale": is_stale,
                "missing": node_missing_files(run, node, run_dir),
            }
            nodes_out.append(entry)
            if is_stale:
                stale.append(f"{run_id}/{node.get('id')}")
        updated = parse_time(run.get("updated_at"))
        run_note = run.get("card_note")
        summaries.append({
            "run_id": run_id,
            "status": run.get("status"),
            "question": one_line(run.get("question")),
            "created_at": run.get("created_at"),
            "updated_at": run.get("updated_at"),
            "age": fmt_age(now - updated) if updated else "未知",
            "independent": run.get("independent"),
            "card_note": bool(one_line(run_note)) if isinstance(run_note, (str, list)) else False,
            "budget": {
                "nodes_used": len(run.get("nodes") or []),
                "max_nodes": limits.get("max_nodes"),
                "cards_dispatched": sum(len(n.get("cards") or []) for n in run.get("nodes") or [] if isinstance(n, dict)),
                "review_rounds": sum((n.get("review_rounds") or 0) for n in run.get("nodes") or [] if isinstance(n, dict)),
            },
            "limits": limits,
            "cost": run.get("cost") if isinstance(run.get("cost"), dict) else None,
            "final_missing": final_missing(run, run_dir),
            "nodes": nodes_out,
        })
    return summaries, stale


def one_line(text, limit: int = 80) -> str:
    if text is None:
        return ""
    flat = " ".join(str(text).split())
    return flat if len(flat) <= limit else flat[: limit - 1] + "…"


def render(summaries: list[dict], stale: list[str], stale_hours: float) -> None:
    for run in summaries:
        if "error" in run:
            print(f"run {run['run_id']}：{run['error']}")
            continue
        budget = run["budget"]
        max_nodes = budget["max_nodes"] if budget["max_nodes"] is not None else "?"
        indep = "" if run.get("independent") else "（降级运行：审查非独立）"
        run_note = "  ⚠ card_note：有卡被降级执行，终稿须披露" if run.get("card_note") else ""
        print(f"run {run['run_id']}  [{run['status']}]{indep}  账本更新：{run['age']}{run_note}")
        print(f"  问题：{run['question']}")
        print(f"  预算：节点 {budget['nodes_used']}/{max_nodes}，已派卡 {budget['cards_dispatched']}，"
              f"审查 {budget['review_rounds']} 轮")
        for node in run["nodes"]:
            flag = "  ⚠停滞" if node["stale"] else ""
            note = "（card_note：有卡被降级执行）" if node.get("card_note") else ""
            missing = f"  缺：{', '.join(node['missing'])}" if node["missing"] else ""
            print(f"  [{node['status']:<18}] {node['id']}  深度{node['depth']}  "
                  f"{node['phase']}  卡{node['cards']}  结论v{node['synthesis_versions']}  "
                  f"审查{node['review_rounds']}轮{note}{flag}{missing}")
        if run["final_missing"]:
            print(f"  ⚠ run 已标 done 但终稿缺：{', '.join(run['final_missing'])}")
        print()
    if stale:
        print(f"⚠ 停滞警示（超过 {stale_hours} 小时无动静且非终态）：{', '.join(stale)}")
        print("  处置见 SKILL.md\"故障、重试与降级\"：报告用户 → 降级执行或记 failed，不要无声挂起。")
    else:
        print("无停滞节点。")


def cost_view(summaries: list[dict]) -> list[dict]:
    """成本视图：账本记的真实开销优先，没记就如实说没记。

    账本此前没有 token/cost 字段，所以这里只能按"每卡 5k、每轮审查 2k"的系数估一个数——
    那是个看起来像测量的虚构。现在 `run.cost` 由 `scripts/node.py spend` 写入；有记录就报
    真实值，没有就报"未记录"并给出记账命令，绝不拿系数填坑。
    """
    out = []
    for run in summaries:
        if "error" in run:
            continue
        budget = run["budget"]
        t0, t1 = parse_time(run.get("created_at")), parse_time(run.get("updated_at"))
        duration = fmt_age(t1 - t0) if (t0 and t1 and t1 >= t0) else "未知（缺时间戳）"
        recorded = run.get("cost")
        entry = {
            "run_id": run["run_id"],
            "status": run["status"],
            "duration": duration,
            "nodes": budget["nodes_used"],
            "cards": budget["cards_dispatched"],
            "review_rounds": budget["review_rounds"],
        }
        if isinstance(recorded, dict) and (recorded.get("tokens") or recorded.get("calls")
                                          or recorded.get("usd")):
            tokens = int(recorded.get("tokens") or 0)
            calls = int(recorded.get("calls") or 0)
            usd = float(recorded.get("usd") or 0.0)
            per_node = (recorded.get("entries") or [])
            entry.update({
                "recorded": True,
                "tokens": tokens,
                "calls": calls,
                "usd": usd,
                "entries": len(per_node),
                "tokens_per_call": round(tokens / calls) if calls else None,
            })
            warn = budget_warning(run)
            if warn:
                entry["budget_warning"] = warn
        else:
            entry.update({
                "recorded": False,
                "tokens": None,
                "calls": None,
                "usd": None,
                "how_to_record": f'python3 "$SKILL_DIR/scripts/node.py" <project> spend '
                                 f'--run {run["run_id"]} --node <id> --tokens N --calls N --usd F',
            })
        out.append(entry)
    return out


def budget_warning(run: dict) -> str | None:
    """预算预警：规模已用掉大半而 run 还在跑，说在超支之前而不是之后。"""
    limits = run.get("limits") if isinstance(run.get("limits"), dict) else {}
    max_nodes = limits.get("max_nodes")
    if not isinstance(max_nodes, int):
        return None
    used = len(run.get("nodes") or [])
    open_nodes = sum(1 for n in (run.get("nodes") or [])
                     if isinstance(n, dict) and n.get("status") not in TERMINAL_NODE)
    if run.get("status") == "done":
        return None
    if used >= max_nodes:
        return f"节点预算已用尽（{used}/{max_nodes}）；停止分叉，未开的选项记入 paths.md 并写明预算约束"
    if used + open_nodes > max_nodes * 0.8:
        return (f"节点预算已用 {used}/{max_nodes}（{open_nodes} 个在跑）；按 SKILL.md“预算见底就停分叉”，"
                f"现在就该决定哪些选项不开")
    return None


def render_cost(costs: list[dict]) -> None:
    if not costs:
        print("无 run 可统计。")
        return
    for c in costs:
        print(f"run {c['run_id']}  [{c['status']}]")
        print(f"  用时：{c['duration']}   规模：节点 {c['nodes']}，卡 {c['cards']}，审查 {c['review_rounds']} 轮")
        if c.get("recorded"):
            per = f"，每次派发≈{c['tokens_per_call']} token" if c.get("tokens_per_call") else ""
            print(f"  实际开销：{c['tokens']} token，{c['calls']} 次派发，{c['usd']} USD"
                  f"（{c['entries']} 笔记账{per}）")
            if c.get("budget_warning"):
                print(f"  ⚠ {c['budget_warning']}")
        else:
            print("  实际开销：未记录——账本里没有 token/cost 数据，本视图不再编数字。")
            print(f"    记账：{c['how_to_record']}")
    print("\n注：用时=created_at→updated_at 的账本时间戳差；实际开销读 run.json 的 `cost`"
          "（由 node.py spend 写入），未记账的 run 只报规模不报数字。")


def main(argv=None) -> int:
    p = argparse.ArgumentParser(prog="status.py", description=__doc__.splitlines()[0])
    p.add_argument("project", help="研究所在的项目文件夹")
    p.add_argument("--run", help="只看这个 run id（默认看全部）")
    p.add_argument("--stale-hours", type=float, default=2.0,
                   help="非终态节点超过这么多小时无动静算停滞（默认 2；0 关闭检测）")
    p.add_argument("--json", action="store_true", help="机器可读输出")
    p.add_argument("--cost", action="store_true",
                   help="成本视图：每 run 的用时/规模与 token 粗估（系数为经验假设，见输出注）")
    args = p.parse_args(argv)

    project = os.path.realpath(os.path.expanduser(args.project))
    summaries, stale = collect(project, args.run, args.stale_hours)

    if args.cost:
        costs = cost_view(summaries)
        if args.json:
            print(json.dumps({"cost": costs, "stale": stale}, ensure_ascii=False, indent=2))
        else:
            render_cost(costs)
        return 0

    if args.json:
        print(json.dumps({"runs": summaries, "stale": stale}, ensure_ascii=False, indent=2))
    else:
        render(summaries, stale, args.stale_hours)
    return 1 if stale else 0


if __name__ == "__main__":
    sys.exit(main())
