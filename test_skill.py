#!/usr/bin/env python3
"""deep-research skill 的回归测试。

固化本 skill 修订史上手工跑过的那组检查（破坏/集成/健壮性），使任何改动都能一键复验。
覆盖：check.py 的关键 P0/P1 判定、六道关卡各自的必红用例、scaffold.py 的输入校验与
生成物、node.py 的开节点/汇合/推进/决策/记账、status.py/export.py/manifest.py、
行为级回归（evals/artifact_cases）、文档一致性（JSON 块可解析、引用文件存在、枚举
冻结、中文标题被识别）。

每个门禁都有一条"A*"用例证明它在应失败的输入上真的失败——永不失败的门禁等于没有门禁。

用法：
    python3 test_skill.py            # 跑全部用例
    python3 test_skill.py -k 关键词   # 只跑名称含关键词的用例

退出码：0 全过；1 有失败。仅标准库；无网络；全部在临时目录中进行。
"""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import unicodedata
from datetime import datetime, timezone

HERE = os.path.dirname(os.path.abspath(__file__))
SKILL_DIR = os.path.dirname(HERE)

CASES: list = []


def case(name):
    def wrap(fn):
        CASES.append((name, fn))
        return fn
    return wrap


def run(script: str, *args, cwd=None):
    return subprocess.run([sys.executable, os.path.join(HERE, script), *args],
                          capture_output=True, text=True, cwd=cwd)


def read_json(path: str):
    with open(path, encoding="utf-8") as handle:
        return json.load(handle)


def write_json(path: str, data) -> None:
    with open(path, "w", encoding="utf-8") as handle:
        json.dump(data, handle, ensure_ascii=False, indent=2)


def scaffold(project: str, question="1918年大流感改变了日本的公共卫生立法吗？", *extra):
    return run("scaffold.py", project, "--question", question, *extra)


def node_dir_of(project: str) -> str:
    base = os.path.join(project, "research")
    run_id = sorted(os.listdir(base))[0]
    nodes = os.listdir(os.path.join(base, run_id, "nodes"))
    return os.path.join(base, run_id, "nodes", nodes[0])


def run_dir_of(project: str) -> str:
    base = os.path.join(project, "research")
    return os.path.join(base, sorted(os.listdir(base))[0])


PLAN_CN = """# 研究计划

## 问题实际在问什么

1918 年大流感是否推动了立法文本的改动。

## 任务卡

| id | 任务 | 研究员 | 理由 | 依赖 |
|---|---|---|---|---|
| `c1-statutes` | 查 1918–1922 年法令与官报 | general-purpose | 读法令 | — |

### `c1-statutes`

- **问题：** 立了什么法？
- **交付物：** `statutes.md`　逐年法令清单，每行注来源
- **证伪条件：** 若立法早于大流行第一波

## 覆盖

| 子问题 | 卡 | 缺口 |
|---|---|---|
| 法令文本 | `c1-statutes` | — |
| 府县执行 | — | **declared gap：经约定不在范围** |
"""

FINDINGS = {
    "findings": [
        {
            "text": "1918 年内务省防疫令发布于 1918-10-25。",
            "claim_type": "fact",
            "source_file": "sources/kampo.txt",
            "page": 3,
            "quote": "流行性感冒ニ関スル件",
            "citation_state": "verified",
            "single_source": False,
        },
        {
            "text": "该令针对的是第一波造成的行政紧张。",
            "claim_type": "inference",
            "basis": "由发布时点与第一波高峰的先后推出",
        },
    ]
}

SYNTHESIS = """# 结论 —— 测试问题

1918 年大流感没有直接改写立法文本；它改变的是行政实践与立法气候，
把 1922 年修法早已准备好的条款推过了门槛。

## 共同发现

各线一致：法令文本的变化集中在行政规范层。

## 关键证据

- `nodes/01-x/cards/c1-statutes/statutes.md` 逐年清单
- `sources/kampo.txt` —— 官报原文

## 反证（Counterevidence）

1922 年修法的直接动因在委员会报告里被归为预算，而非疫情。

## 方法局限

只检了中央文本，地方执行未覆盖。

## 价值前提

以公共行政史立场评估。

## 前提（Premises）

- 立法文本可作为政策变化的指示器

## 本结论不知道什么

殖民地行政层的反应。

## 未决问题

府县层面的执行差异。

## 未走的路

- 帝国行政读法：见 paths.md。

## 来源（Sources）

- `sources/kampo.txt` — verified
- `nodes/01-x/cards/c1-statutes/statutes.md` — verified
"""


def build_full_run(root: str, question="1918年大流感改变了日本的公共卫生立法吗？"):
    """搭一个形态完整、应通过全部检查的 run（中文计划/结论/审查齐备）。"""
    project = os.path.join(root, "proj")
    result = scaffold(project, question, "--depth", "1", "--cards", "2",
                      "--followups", "1", "--revisions", "1")
    assert result.returncode == 0, result.stderr
    run_dir = run_dir_of(project)
    ndir = node_dir_of(project)
    ledger_path = os.path.join(run_dir, "run.json")
    run_data = read_json(ledger_path)

    with open(os.path.join(ndir, "plan.md"), "w", encoding="utf-8") as fh:
        fh.write(PLAN_CN)
    os.makedirs(os.path.join(ndir, "sources"), exist_ok=True)
    with open(os.path.join(ndir, "sources", "kampo.txt"), "w", encoding="utf-8") as fh:
        fh.write("官报原文……流行性感冒ニ関スル件……昭和前夜\n")
    card_dir = os.path.join(ndir, "cards", "c1-statutes")
    os.makedirs(card_dir, exist_ok=True)
    with open(os.path.join(card_dir, "statutes.md"), "w", encoding="utf-8") as fh:
        fh.write("# 法令清单\n\n1918-10-25 内务省令……\n")
    write_json(os.path.join(card_dir, "findings.json"), FINDINGS)
    with open(os.path.join(ndir, "synthesis.md"), "w", encoding="utf-8") as fh:
        fh.write(SYNTHESIS)
    with open(os.path.join(ndir, "review-01.md"), "w", encoding="utf-8") as fh:
        fh.write("# 审查 第1轮\n\n无实质问题。\n")
    with open(os.path.join(ndir, "possibility.md"), "w", encoding="utf-8") as fh:
        fh.write("# 可能性审查\n\n{\"alternatives\": []}\n")

    run_id = run_data["run_id"]
    final_dir = os.path.join(run_dir, "final")
    for stage in ("survey", "draft", "review", "final"):
        name = f"{run_id}-{stage}.md"
        with open(os.path.join(final_dir, name), "w", encoding="utf-8") as fh:
            fh.write(f"# {stage}\n\n占位内容。\n")
    os.makedirs(os.path.join(final_dir, "sources"), exist_ok=True)
    with open(os.path.join(final_dir, "sources", "kampo.txt"), "w", encoding="utf-8") as fh:
        fh.write("官报原文……流行性感冒ニ関スル件……\n")

    node = run_data["nodes"][0]
    node.update({
        "status": "closed",
        "cards": ["c1-statutes"],
        "synthesis": "synthesis.md",
        "synthesis_versions": 1,
        "review_rounds": 1,
        "review_files": ["review-01.md"],
        "possibility_file": "possibility.md",
        "no_forks": True,
    })
    run_data["status"] = "done"
    run_data["final"] = {s: f"{run_id}-{s}.md" for s in ("survey", "draft", "review", "final")}
    write_json(ledger_path, run_data)
    return project, run_dir, ndir, ledger_path, run_data


# ---------------------------------------------------------------- 破坏类（应被拦下）


@case("D1_完整中文run通过全检")
def d1(root):
    project, *_ = build_full_run(root)
    result = run("check.py", project)
    assert result.returncode == 0, f"exit={result.returncode}\n{result.stdout}\n{result.stderr}"


@case("D2_非法claim_type被拦")
def d2(root):
    project, run_dir, ndir, *_ = build_full_run(root)
    card = os.path.join(ndir, "cards", "c1-statutes", "findings.json")
    data = read_json(card)
    data["findings"][0]["claim_type"] = "guess"
    write_json(card, data)
    result = run("check.py", project)
    assert result.returncode == 2 and "claim_type" in result.stdout, result.stdout + result.stderr


@case("D3_source_file不存在被拦")
def d3(root):
    project, run_dir, ndir, *_ = build_full_run(root)
    card = os.path.join(ndir, "cards", "c1-statutes", "findings.json")
    data = read_json(card)
    data["findings"][0]["source_file"] = "sources/nope.txt"
    write_json(card, data)
    result = run("check.py", project)
    assert result.returncode == 2 and "does not exist" in result.stdout, result.stdout + result.stderr


@case("D4_引文不在文件中报P1")
def d4(root):
    project, run_dir, ndir, *_ = build_full_run(root)
    card = os.path.join(ndir, "cards", "c1-statutes", "findings.json")
    data = read_json(card)
    data["findings"][0]["quote"] = "这句话不在来源文件里"
    write_json(card, data)
    result = run("check.py", project)
    assert result.returncode == 1 and "quotation is not in" in result.stdout, result.stdout + result.stderr


@case("D5_closed缺审查记录被拦")
def d5(root):
    project, run_dir, ndir, ledger_path, run_data = build_full_run(root)
    run_data["nodes"][0]["review_rounds"] = 0
    run_data["nodes"][0]["review_files"] = []
    write_json(ledger_path, run_data)
    result = run("check.py", project)
    assert result.returncode == 2 and "review_rounds" in result.stdout, result.stdout + result.stderr


@case("D6_结论缺反证节被拦")
def d6(root):
    project, run_dir, ndir, *_ = build_full_run(root)
    path = os.path.join(ndir, "synthesis.md")
    with open(path, encoding="utf-8") as fh:
        text = fh.read()
    text = text.replace("## 反证（Counterevidence）", "## 某节")
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(text)
    result = run("check.py", project)
    assert result.returncode == 2 and "counterevidence" in result.stdout, result.stdout + result.stderr


@case("D7_单选项决策被拦")
def d7(root):
    project, run_dir, ndir, ledger_path, run_data = build_full_run(root)
    node = run_data["nodes"][0]
    node["no_forks"] = False
    run_data["decisions"].append({
        "id": "d1", "decided_at": node["id"], "question": "q?", "stakes": "s",
        "options": [{"id": "o1", "label": "a", "premise": "p", "own": True,
                     "node": node["id"], "reason": "", "covered_by": ""}],
    })
    write_json(ledger_path, run_data)
    result = run("check.py", project)
    assert result.returncode == 2, result.stdout + result.stderr


@case("D8_选项双重归宿被拦")
def d8(root):
    project, run_dir, ndir, ledger_path, run_data = build_full_run(root)
    node = run_data["nodes"][0]
    node["no_forks"] = False
    run_data["decisions"].append({
        "id": "d1", "decided_at": node["id"], "question": "q?", "stakes": "s",
        "options": [
            {"id": "o1", "label": "a", "premise": "p", "own": True,
             "node": node["id"], "reason": "同时给了未开理由", "covered_by": ""},
            {"id": "o2", "label": "b", "premise": "p2", "own": False,
             "node": None, "reason": "", "covered_by": ""},
        ],
    })
    write_json(ledger_path, run_data)
    result = run("check.py", project)
    assert result.returncode == 2, result.stdout + result.stderr


@case("D9_深度跳跃被拦")
def d9(root):
    project, run_dir, ndir, ledger_path, run_data = build_full_run(root)
    run_data["nodes"].append({
        "id": "n_child001", "folder": run_data["nodes"][0]["folder"], "seq": 2, "depth": 0,
        "question": "child?", "kind": "line", "parents": [run_data["nodes"][0]["id"]],
        "status": "queued", "cards": [], "synthesis": None, "synthesis_versions": 0,
        "review_rounds": 0, "dissolves": None, "issues": [], "gaps": [],
    })
    write_json(ledger_path, run_data)
    result = run("check.py", project)
    assert result.returncode == 2, result.stdout + result.stderr


@case("D10_followups为零时缺口revise报P1")
def d10(root):
    project, run_dir, ndir, ledger_path, run_data = build_full_run(root)
    run_data["limits"]["followups"] = 0
    run_data["nodes"][0]["gaps"].append({
        "id": "g1", "material": True, "disposition": "revise",
        "reason": "补", "revision": "synthesis.md",
    })
    write_json(ledger_path, run_data)
    result = run("check.py", project)
    assert result.returncode == 1, result.stdout + result.stderr


@case("D11_中文综述式开头触发Angle门")
def d11(root):
    """Angle 是 critical：综述式开头现在必须阻断（exit 2），不是提醒（exit 1）。"""
    project, run_dir, ndir, *_ = build_full_run(root)
    path = os.path.join(ndir, "synthesis.md")
    with open(path, encoding="utf-8") as fh:
        text = fh.read()
    text = text.replace("1918 年大流感没有直接改写立法文本；",
                        "本报告梳理了 1918 年前后的相关立法：")
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(text)
    result = run("check.py", project)
    assert result.returncode == 2 and "survey" in result.stdout, result.stdout + result.stderr
    # 关卡视图也必须把 ANGLE 显示为 FAIL 并退出 2。
    gated = run("check.py", project, "--gates")
    assert gated.returncode == 2, gated.stdout + gated.stderr
    assert re.search(r"ANGLE\s+\(critical\s*\)\s+FAIL", gated.stdout), gated.stdout


# ---------------------------------------------------------------- 必红类（A*：每个门禁证明它会失败）
#
# 这一组是全套用例里最要紧的一组：上面每条 D* 只证明"畸形输入被拒绝"，而门禁的真正
# 契约是"在应失败的输入上失败"。一个永远 clear 的门禁等于没有门禁——1.2.0 的
# Taxonomy 与 Weaving 正是那样躺了两版。每条 A* 都构造一个该门禁非失败不可的产物。


def write_final_report(run_dir: str, run_id: str, body: str, stage: str = "final") -> str:
    path = os.path.join(run_dir, "final", f"{run_id}-{stage}.md")
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(body)
    return path


@case("A1_gates视图在P0存在时退出非0")
def a1(root):
    """最大的一条必红：--gates 曾经在 5 个 P0 存在时仍打印 verdict: OK 并 exit 0。"""
    project, run_dir, ndir, ledger_path, run_data = build_full_run(root)
    # 制造 5 个 P0：每个都落在不同的关卡与未归类桶里。
    run_data["nodes"][0]["review_rounds"] = 0                      # 未归类桶
    run_data["nodes"][0]["review_files"] = []                      # 未归类桶
    run_data["nodes"][0]["possibility_file"] = None                # 未归类桶
    run_data["nodes"][0]["no_forks"] = False                       # 未归类桶
    run_data["nodes"][0]["depth"] = 9                              # 未归类桶（超 limits.depth→P1）
    run_data["nodes"][0]["synthesis"] = "synthesis-missing.md"     # P0
    write_json(ledger_path, run_data)

    plain = run("check.py", project)
    assert plain.returncode == 2, plain.stdout + plain.stderr
    gated = run("check.py", project, "--gates")
    assert gated.returncode == 2, f"--gates 在有 P0 时必须 exit 2，实得 {gated.returncode}\n" \
                                 + gated.stdout + gated.stderr
    assert "BLOCKED" in gated.stderr, gated.stderr
    # --gates --json 曾静默丢掉 gate 数据；现在必须带着同样的判定。
    both = run("check.py", project, "--gates", "--json")
    assert both.returncode == 2, both.stdout + both.stderr
    payload = json.loads(both.stdout)
    assert payload["exit"] == 2 and payload["gates"], "gate 数据在 --json 下丢失"
    assert payload["gates"]["ungated"]["counts"]["P0"] >= 4, payload["gates"]["ungated"]
    # 未归类桶的 P0 也要进 verdict：这正是 1.2.0 漏掉的那一半。
    assert payload["gates"]["ungated"]["state"] == "FAIL", payload["gates"]["ungated"]


@case("A2_gates视图全清时退出0且六门禁都在场")
def a2(root):
    """反向对照：干净 run 的关卡视图必须全 clear 且 exit 0，含新实现的两门禁。"""
    project, *_ = build_full_run(root)
    gated = run("check.py", project, "--gates")
    assert gated.returncode == 0, gated.stdout + gated.stderr
    for gate in ("ANGLE", "COVERAGE", "CITATION", "TAXONOMY", "CALIBRATION", "WEAVING"):
        assert re.search(rf"^{gate}\s+\(", gated.stdout, re.M), f"{gate} 不在关卡视图里"
    assert "UNGATED" not in gated.stdout, gated.stdout


@case("A3_Angle在非closed阶段也可达")
def a3(root):
    """Angle 曾经只在 status == closed 时才跑，而 SKILL.md 把它放在阶段 3。"""
    project, run_dir, ndir, ledger_path, run_data = build_full_run(root)
    run_data["nodes"][0]["status"] = "reviewing"
    write_json(ledger_path, run_data)
    path = os.path.join(ndir, "synthesis.md")
    with open(path, encoding="utf-8") as fh:
        text = fh.read()
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(text.replace("1918 年大流感没有直接改写立法文本；", "本文综述了 1918 年前后的立法："))
    result = run("check.py", project, "--gates")
    assert result.returncode == 2, result.stdout + result.stderr
    assert re.search(r"ANGLE\s+\(critical\s*\)\s+FAIL", result.stdout), result.stdout


@case("A4_Coverage未声明的空格必红")
def a4(root):
    """覆盖表只查标题存在是不够的：空格 = declared gap 才是这门禁的全部意义。"""
    project, run_dir, ndir, *_ = build_full_run(root)
    path = os.path.join(ndir, "plan.md")
    with open(path, encoding="utf-8") as fh:
        text = fh.read()
    # 把府县执行那行的"declared gap"抹掉：卡列空、缺口列也空 → 未声明的疏忽。
    text = text.replace("| 府县执行 | — | **declared gap：经约定不在范围** |",
                        "| 府县执行 |  |  |")
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(text)
    result = run("check.py", project, "--gates")
    assert result.returncode != 0, "未声明的覆盖表空格必须被拦下"
    assert "coverage row" in result.stdout.lower(), result.stdout
    assert re.search(r"COVERAGE\s+\(major\s*\)\s+FAIL", result.stdout), result.stdout


@case("A5_Citation定位符不存在必红")
def a5(root):
    project, run_dir, ndir, *_ = build_full_run(root)
    card = os.path.join(ndir, "cards", "c1-statutes", "findings.json")
    data = read_json(card)
    data["findings"][0]["source_file"] = "sources/ghost.txt"
    write_json(card, data)
    gated = run("check.py", project, "--gates")
    assert gated.returncode == 2, gated.stdout + gated.stderr
    assert re.search(r"CITATION\s+\(critical\s*\)\s+FAIL", gated.stdout), gated.stdout


@case("A6_Taxonomy按来源分节必红")
def a6(root):
    """Taxonomy 曾经是死门禁：GATES 声明了它，全库没有一处 rep.gate("taxonomy")。"""
    project, run_dir, ndir, ledger_path, run_data = build_full_run(root)
    run_id = run_data["run_id"]
    write_final_report(run_dir, run_id, (
        "# 报告\n\n"
        "## Card 1\n\n第一张卡报告的内容，足有一段的长度，用来凑成正文段落。\n\n"
        "## Source 2\n\n第二份来源报告的内容，也要够长才能被算作正文段落之一。\n\n"
        "## 附录\n\n附录里列了所有材料，同样写足一段以便进入正文统计。\n\n"
        "## 参考文献\n\n最后一段同样写足长度，使正文段落数量达到门槛。\n"
    ))
    gated = run("check.py", project, "--gates")
    assert gated.returncode != 0, "按来源/卡分节必须触发 Taxonomy"
    assert re.search(r"TAXONOMY\s+\(major\s*\)\s+FAIL", gated.stdout), gated.stdout
    assert "Card 1" in gated.stdout, "门禁必须点名是哪几节有问题"


@case("A7_Taxonomy章节重叠必红")
def a7(root):
    project, run_dir, ndir, ledger_path, run_data = build_full_run(root)
    write_final_report(run_dir, run_data["run_id"], (
        "# 报告\n\n"
        "## 赔偿政治的起源\n\n赔偿政治如何起源，这一段写足长度以进入正文段落统计。\n\n"
        "## 赔偿政治的后果\n\n赔偿政治带来什么后果，这一段同样写足长度以进入统计。\n\n"
        "## 行政结构的演变\n\n行政结构如何演变，这一段也写足长度以进入正文统计。\n\n"
        "## 司法实践的转折\n\n司法实践在何处转折，这一段同样写足以进入正文统计。\n"
    ))
    gated = run("check.py", project, "--gates")
    assert gated.returncode != 0, "两节标题重叠必须触发 Taxonomy"
    assert "overlap" in gated.stdout, gated.stdout


@case("A8_Weaving一段一来源必红")
def a8(root):
    """Weaving 与 Taxonomy 同为死门禁；这里证明它现在会失败并点名段落。"""
    project, run_dir, ndir, ledger_path, run_data = build_full_run(root)
    paras = []
    for index in range(5):
        paras.append(
            f"第 {index + 1} 段只谈一份材料 `sources/kampo.txt`，"
            f"从头到尾不复述第二位作者的说法、也不比较两种记录之间的差异，"
            f"只是把这一份材料的内容平铺开来写成一段足够长的正文以便被统计到。"
        )
    write_final_report(run_dir, run_data["run_id"], "# 报告\n\n" + "\n\n".join(paras) + "\n")
    gated = run("check.py", project, "--gates")
    assert gated.returncode != 0, "一段一来源的目录式行文必须触发 Weaving"
    assert re.search(r"WEAVING\s+\(major\s*\)\s+FAIL", gated.stdout), gated.stdout
    assert "paragraph" in gated.stdout.lower(), gated.stdout


@case("A9_Calibration过度断言必红")
def a9(root):
    """Calibration 曾经最高只发 P2，机器视图永远只是 note，从不 FAIL。"""
    project, run_dir, ndir, *_ = build_full_run(root)
    path = os.path.join(ndir, "synthesis.md")
    with open(path, encoding="utf-8") as fh:
        text = fh.read()
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(text.replace("它改变的是行政实践与立法气候，", "这证明了行政实践与立法气候被彻底改变，"))
    gated = run("check.py", project, "--gates")
    assert gated.returncode != 0, "过度断言必须让 Calibration 失败，而不仅是提示"
    assert re.search(r"CALIBRATION\s+\(major\s*\)\s+FAIL", gated.stdout), gated.stdout


@case("A10_final定位符不可解析必红")
def a10(root):
    """07-report.md 声称 check.py 校验交付文本里每个定位符可解析——此前没有任何代码读正文。"""
    project, run_dir, ndir, ledger_path, run_data = build_full_run(root)
    run_id = run_data["run_id"]
    path = os.path.join(run_dir, "final", f"{run_id}-final.md")
    with open(path, "w", encoding="utf-8") as fh:
        fh.write("# 终稿\n\n见 `sources/kampo.txt` 与 `sources/never-fetched.txt`。\n")
    # sources/ 下只有 kampo.txt，第二条指不到。
    result = run("check.py", project)
    assert result.returncode != 0, "交付文本里指不到的定位符必须被拦下"
    assert "never-fetched" in result.stdout, result.stdout


@case("A11_schema不认识的值拒绝运行")
def a11(root):
    """09-ledger.md 写着"不认识的值拒绝运行"；此前全库无一处校验 schema。"""
    project, run_dir, ndir, ledger_path, run_data = build_full_run(root)
    run_data["schema"] = 99
    write_json(ledger_path, run_data)
    result = run("check.py", project)
    assert result.returncode == 2, result.stdout + result.stderr
    assert "schema" in result.stdout, result.stdout
    # 缺 schema 也是要提醒的（P1），不是静默通过。
    run_data["schema"] = None
    write_json(ledger_path, run_data)
    missing = run("check.py", project)
    assert missing.returncode != 0 and "schema" in missing.stdout, missing.stdout


@case("A12_未文档化的账本键被校验")
def a12(root):
    """14 个被文档写进 schema 却从不校验的键；这里抽查其中六个的形状错误。"""
    project, run_dir, ndir, ledger_path, run_data = build_full_run(root)
    node = run_data["nodes"][0]
    node["seq"] = "one"                       # 应为 int
    node["opened_by"] = "d1/o2"               # 应为对象
    node["synthesis_versions"] = -1           # 应为非负
    run_data["limits"]["plan_approval"] = "maybe"
    run_data["consent"]["note"] = 42          # 见下方：consent 非对象
    write_json(ledger_path, run_data)
    result = run("check.py", project)
    for needle in ("seq", "opened_by", "synthesis_versions", "plan_approval", "consent"):
        assert needle in result.stdout, f"{needle} 的形状错误未被报出：{result.stdout}"

    # issue.priority / round 与 decision.stakes / option.label 同样要报。
    project2, _, _, ledger2, run2 = build_full_run(os.path.join(root, "b"))
    run2["nodes"][0]["issues"].append(
        {"id": "i9", "material": True, "disposition": "rebut", "reason": "因为",
         "priority": "high", "round": 0})
    run2["decisions"].append({
        "id": "d9", "decided_at": run2["nodes"][0]["id"], "question": "q?", "stakes": "",
        "options": [{"id": "o9", "premise": "p", "own": True, "node": run2["nodes"][0]["id"]},
                    {"id": "o10", "premise": "p2", "reason": "预算"}],
    })
    run2["nodes"][0]["no_forks"] = False
    write_json(ledger2, run2)
    checked = run("check.py", project2)
    for needle in ("priority", "round", "stakes", "label"):
        assert needle in checked.stdout, f"{needle} 的形状错误未被报出：{checked.stdout}"


@case("A13_declined与dependedOn等键被接受且被校验")
def a13(root):
    """run 级 declined[] 此前只存在于 05-possibility.md 的示例里，schema 未列也未校验。"""
    project, run_dir, ndir, ledger_path, run_data = build_full_run(root)
    run_data["alternatives"].append({"id": "a3", "proposal": "读作殖民行政工具", "gap": False,
                                     "outcome": "declined", "outcome_ref": ""})
    run_data["declined"] = [{"issue_id": "a3", "disposition": "decline", "reason": "不值得"}]
    write_json(ledger_path, run_data)
    bad = run("check.py", project)
    assert bad.returncode != 0 and "is not a reason" in bad.stdout, bad.stdout
    # 写明约束的拒绝是合法结局。
    run_data["declined"] = [{"issue_id": "a3", "disposition": "decline",
                             "reason": "节点预算已用尽：30/30。"}]
    write_json(ledger_path, run_data)
    good = run("check.py", project)
    assert good.returncode == 0, good.stdout + good.stderr

    # findings 的可选字段：depends_on 指向不存在的 id 要被点名。
    card = os.path.join(ndir, "cards", "c1-statutes", "findings.json")
    data = read_json(card)
    data["findings"][1]["depends_on"] = ["f-nope"]
    write_json(card, data)
    dep = run("check.py", project)
    assert "depends_on" in dep.stdout, dep.stdout


@case("A14_resume对无note的relation不崩溃")
def a14(root):
    """scaffold.py:383 曾对每个 relation 取 r['note']，而 check.py 不要求它 —— 合法输入
    让会话恢复入口崩掉（KeyError），且此时 graph.md 已被覆写。"""
    project, run_dir, ndir, ledger_path, run_data = build_full_run(root)
    run_data["relations"] = [{"kind": "converge", "nodes": [run_data["nodes"][0]["id"]] * 2}]
    write_json(ledger_path, run_data)
    result = run("scaffold.py", project, "--resume")
    assert result.returncode == 0, f"无 note 的 relation 让 --resume 崩了：{result.stderr}"
    assert "Traceback" not in result.stderr, result.stderr
    with open(os.path.join(run_dir, "graph.md"), encoding="utf-8") as fh:
        assert "converge" in fh.read()
    # check.py 对缺 note 只提醒，不阻断。
    checked = run("check.py", project)
    assert checked.returncode == 0, checked.stdout + checked.stderr


# ---------------------------------------------------------------- 集成类（应通过）


@case("I1_worked_example逐字通过")
def i1(root):
    project = os.path.join(root, "ordinance")
    result = scaffold(project, "1918年大流感改变了日本的公共卫生立法吗？",
                      "--depth", "1", "--cards", "2", "--followups", "1", "--revisions", "1")
    assert result.returncode == 0 and "创建" in result.stdout + result.stderr, result.stderr
    checked = run("check.py", project)
    assert checked.returncode == 0, checked.stdout + checked.stderr


@case("I2_中文plan在planning态通过")
def i2(root):
    project = os.path.join(root, "p2")
    assert scaffold(project).returncode == 0
    ndir = node_dir_of(project)
    ledger_path = os.path.join(run_dir_of(project), "run.json")
    with open(os.path.join(ndir, "plan.md"), "w", encoding="utf-8") as fh:
        fh.write(PLAN_CN)
    run_data = read_json(ledger_path)
    run_data["nodes"][0]["status"] = "planning"
    write_json(ledger_path, run_data)
    result = run("check.py", project)
    assert result.returncode == 0, result.stdout + result.stderr


@case("I3_骨架视图含中文且check不误报")
def i3(root):
    project = os.path.join(root, "p3")
    assert scaffold(project).returncode == 0
    with open(os.path.join(run_dir_of(project), "graph.md"), encoding="utf-8") as fh:
        graph = fh.read()
    assert "研究图" in graph and "根节点" not in graph  # 表头中文、非种子残留
    with open(os.path.join(run_dir_of(project), "paths.md"), encoding="utf-8") as fh:
        paths = fh.read()
    assert "路径表" in paths and "尚无记录" in paths
    result = run("check.py", project)
    assert result.returncode == 0, result.stdout + result.stderr


@case("I4_scaffold输入校验")
def i4(root):
    project = os.path.join(root, "v")
    r1 = scaffold(project, "查一下")
    assert r1.returncode == 2 and "太短" in r1.stderr, r1.stderr
    r2 = scaffold(project, "这是一个带TODO的问题吗？")
    assert r2.returncode == 2 and "占位符" in r2.stderr, r2.stderr
    r3 = scaffold(project, "合理的研究问题应该通过吗？", "--cards", "20")
    assert r3.returncode == 2 and "超出合理上限" in r3.stderr, r3.stderr
    r4 = scaffold(project, "合理的研究问题应该通过吗？", "--depth", "5")
    assert r4.returncode == 0 and "警告" in r4.stderr, r4.stderr
    r5 = scaffold(os.path.join(root, "v2"), "第一问是什么？第二问是什么？第三问是什么？")
    assert r5.returncode == 0 and "问号" in r5.stderr, r5.stderr
    r6 = scaffold(os.path.join(root, "v"), "合理的研究问题应该通过吗？")
    assert r6.returncode == 0 and "同问题" in r6.stderr, r6.stderr


@case("I5_长中文问题的节点目录名不以连字符收尾")
def i5(root):
    project = os.path.join(root, "long")
    question = ("1956—1981年间，是什么原因使毛泽东及中央领导层关于社会主义社会阶级关系、"
                "社会矛盾与资本主义复辟风险的认识，逐步发展为继续革命理论？")
    assert scaffold(project, question).returncode == 0
    folders = os.listdir(os.path.join(run_dir_of(project), "nodes"))
    assert len(folders) == 1
    name = folders[0]
    assert name.startswith("01-") and not name.endswith("-"), name


@case("I6_resume重建视图")
def i6(root):
    project = os.path.join(root, "r")
    assert scaffold(project).returncode == 0
    os.remove(os.path.join(run_dir_of(project), "graph.md"))
    result = run("scaffold.py", project, "--resume")
    assert result.returncode == 0 and os.path.isfile(os.path.join(run_dir_of(project), "graph.md"))


@case("I7_文档内所有json块可解析")
def i7(root):
    docs = [os.path.join(SKILL_DIR, "SKILL.md")]
    refs = os.path.join(SKILL_DIR, "references")
    docs += [os.path.join(refs, f) for f in sorted(os.listdir(refs)) if f.endswith(".md")]
    for doc in docs:
        with open(doc, encoding="utf-8") as fh:
            text = fh.read()
        for index, block in enumerate(re.findall(r"```json\n(.*?)```", text, re.S)):
            try:
                json.loads(block)
            except ValueError as error:
                raise AssertionError(f"{os.path.basename(doc)} 第{index + 1}个 json 块无法解析: {error}")


@case("I8_SKILL引用的文件全部存在")
def i8(root):
    with open(os.path.join(SKILL_DIR, "SKILL.md"), encoding="utf-8") as fh:
        text = fh.read()
    for rel in set(re.findall(r"`((?:references|scripts|assets|evals)/[\w./-]+)`", text)):
        assert os.path.exists(os.path.join(SKILL_DIR, rel)), f"SKILL.md 引用的 {rel} 不存在"


@case("I9_触发用例与description一致")
def i9(root):
    cases = read_json(os.path.join(SKILL_DIR, "evals", "trigger_cases.json"))
    for key in ("should_trigger", "should_not_trigger", "near_neighbor",
                "positive_concepts", "negative_patterns", "description_required_concepts"):
        assert key in cases, f"trigger_cases.json 缺 {key}"
    with open(os.path.join(SKILL_DIR, "SKILL.md"), encoding="utf-8") as fh:
        skill = fh.read()
    for concept in cases["description_required_concepts"]:
        words = cases["positive_concepts"].get(concept, [])
        assert any(w in skill for w in words), f"description 未覆盖概念 {concept}"


@case("I10_冻结枚举在文档中原样保留")
def i10(root):
    checks = {
        "references/02-cards.md": ["fact", "inference", "interpretation", "normative",
                                   "verified", "unreachable", "single_source"],
        "references/04-critique.md": ["revise", "correct", "rebut", "concede",
                                      "covered", "park", "branch"],
        "references/10-gates.md": ["verified", "partial", "unverified", "unreachable", "invalid"],
        "references/09-ledger.md": ["question_revisions", "decided_at", "possibility_file"],
    }
    for rel, needles in checks.items():
        with open(os.path.join(SKILL_DIR, rel), encoding="utf-8") as fh:
            text = fh.read()
        for needle in needles:
            assert needle in text, f"{rel} 缺冻结标识 {needle}"


@case("I11_card_note被接受且status可见")
def i11(root):
    project, run_dir, ndir, ledger_path, run_data = build_full_run(root)
    run_data["nodes"][0]["card_note"] = "c1 由协调人执行（上游 502 两次失败）；材料经逐字核对。"
    write_json(ledger_path, run_data)
    checked = run("check.py", project)
    assert checked.returncode == 0, checked.stdout + checked.stderr
    status = run("status.py", project)
    assert status.returncode == 0 and "card_note" in status.stdout, status.stdout + status.stderr


# ---------------------------------------------------------------- 健壮性


@case("R1_无参与坏路径不崩溃")
def r1(root):
    assert run("check.py").returncode == 2
    assert run("check.py", os.path.join(root, "nope")).returncode == 1
    assert run("scaffold.py").returncode == 2


@case("R2_畸形run.json报P0不traceback")
def r2(root):
    project = os.path.join(root, "broken")
    assert scaffold(project).returncode == 0
    ledger_path = os.path.join(run_dir_of(project), "run.json")
    with open(ledger_path, "w", encoding="utf-8") as fh:
        fh.write("{not json")
    result = run("check.py", project)
    assert "Traceback" not in result.stderr, result.stderr
    assert result.returncode in (1, 2), result.stderr


@case("R3_空findings通过")
def r3(root):
    project, run_dir, ndir, *_ = build_full_run(root)
    write_json(os.path.join(ndir, "cards", "c1-statutes", "findings.json"), {"findings": []})
    result = run("check.py", project)
    assert result.returncode == 0, result.stdout + result.stderr


@case("R4_status对完整run与停滞run")
def r4(root):
    project, *_ = build_full_run(root)
    ok = run("status.py", project)
    assert ok.returncode == 0 and "无停滞" in ok.stdout, ok.stdout + ok.stderr

    project2 = os.path.join(root, "stale")
    assert scaffold(project2).returncode == 0
    ledger_path = os.path.join(run_dir_of(project2), "run.json")
    run_data = read_json(ledger_path)
    run_data["nodes"][0]["status"] = "executing"
    run_data["updated_at"] = "2020-01-01T00:00:00Z"
    write_json(ledger_path, run_data)
    stale = run("status.py", project2)
    assert stale.returncode == 1 and "停滞" in stale.stdout, stale.stdout + stale.stderr
    as_json = run("status.py", project2, "--json")
    payload = json.loads(as_json.stdout)
    assert payload["runs"] and payload["stale"]


@case("R5_status对畸形账本不崩溃")
def r5(root):
    project = os.path.join(root, "sbroken")
    assert scaffold(project).returncode == 0
    with open(os.path.join(run_dir_of(project), "run.json"), "w", encoding="utf-8") as fh:
        fh.write("{oops")
    result = run("status.py", project)
    assert "Traceback" not in result.stderr and "无法读取" in result.stdout + result.stderr


@case("R4b_status成本视图未记账时如实说未记录")
def r4b(root):
    """成本视图曾经用 cards*5000 + rounds*2000 的硬编码系数"估算"——那是个看起来像测量的
    虚构。现在没有真实记账就只报规模，并给出记账命令，绝不编数字。"""
    project, run_dir, *_ = build_full_run(root)
    cost = run("status.py", project, "--cost")
    assert cost.returncode == 0, cost.stdout + cost.stderr
    assert "未记录" in cost.stdout, cost.stdout
    assert "token 粗估" not in cost.stdout, "不应再输出系数估算"
    as_json = run("status.py", project, "--cost", "--json")
    payload = json.loads(as_json.stdout)
    entry = payload["cost"][0]
    assert entry["recorded"] is False and entry["tokens"] is None, as_json.stdout
    assert entry["cards"] >= 1, as_json.stdout
    # 有 research/ 但没有任何 run：不崩溃、退出 0、明确提示
    bare_dir = os.path.join(root, "no-runs")
    os.makedirs(os.path.join(bare_dir, "research"), exist_ok=True)
    bare = run("status.py", bare_dir, "--cost")
    assert bare.returncode == 0 and "无 run 可统计" in bare.stdout, bare.stdout + bare.stderr
    # 完全空的目录：防呆报错而不是崩溃
    empty = os.path.join(root, "not-a-project")
    os.makedirs(empty, exist_ok=True)
    guard = run("status.py", empty, "--cost")
    assert guard.returncode == 2 and "Traceback" not in guard.stderr, guard.stdout + guard.stderr


@case("R4c_status成本视图读真实记账")
def r4c(root):
    """记账后：报真实值 + 超预算预警。"""
    project, run_dir, ndir, ledger_path, run_data = build_full_run(root)
    node_id = run_data["nodes"][0]["id"]
    spent = run("node.py", project, "spend", "--node", node_id, "--tokens", "8400",
                "--calls", "4", "--usd", "0.52", "--what", "两卡+审查")
    assert spent.returncode == 0, spent.stdout + spent.stderr
    cost = run("status.py", project, "--cost")
    assert cost.returncode == 0 and "8400" in cost.stdout, cost.stdout + cost.stderr
    payload = json.loads(run("status.py", project, "--cost", "--json").stdout)
    entry = payload["cost"][0]
    assert entry["recorded"] is True and entry["tokens"] == 8400 and entry["calls"] == 4, entry
    # 预算预警：把 max_nodes 压到已用规模之下、run 仍在跑，应给出停止分叉的提醒。
    # 重读账本再改——用内存里的旧副本回写会把刚记的开销抹掉（手改 run.json 的真实风险）。
    fresh = read_json(ledger_path)
    fresh["limits"]["max_nodes"] = 1
    fresh["status"] = "active"
    write_json(ledger_path, fresh)
    warned = json.loads(run("status.py", project, "--cost", "--json").stdout)
    assert warned["cost"][0].get("budget_warning"), warned["cost"][0]


@case("R6_export完整导出与拒覆盖")
def r6(root):
    project, *_ = build_full_run(root)
    dest = os.path.join(root, "交付")
    result = run("export.py", project, "--dest", dest, "--name", "测试报告")
    assert result.returncode == 0, result.stdout + result.stderr
    for name in ("测试报告.md", "测试报告-survey.md", "测试报告-draft.md",
                 "测试报告-review.md", "测试报告-question.md"):
        assert os.path.isfile(os.path.join(dest, name)), f"缺 {name}"
    assert os.path.isdir(os.path.join(dest, "测试报告-sources"))
    again = run("export.py", project, "--dest", dest, "--name", "测试报告")
    assert again.returncode == 2 and "已存在" in again.stderr, again.stderr
    forced = run("export.py", project, "--dest", dest, "--name", "测试报告", "--force")
    assert forced.returncode == 0


@case("R7_export拒绝未完成run")
def r7(root):
    project = os.path.join(root, "half")
    assert scaffold(project).returncode == 0
    dest = os.path.join(root, "out")
    result = run("export.py", project, "--dest", dest)
    assert result.returncode == 2 and "终稿" in result.stderr, result.stderr
    partial = run("export.py", project, "--dest", dest, "--partial")
    assert partial.returncode == 2 and "没有任何阶段文件" in partial.stderr, partial.stderr


@case("R8_检查脚本只读")
def r8(root):
    """check.py 与 status.py 是只读契约：任何参数组合都不得写 run 目录。

    这条断言此前形同虚设——它给 status.py 传 --gates，而 status.py 根本不接受这个参数
    （argparse 直接 exit 2），于是"只读"只测了 check.py 的一半，且 returncode 从未被检查。
    """
    project, *_ = build_full_run(root)
    def snapshot(base):
        out = {}
        for r, _d, files in os.walk(base):
            for f in files:
                p = os.path.join(r, f)
                st = os.stat(p)
                out[p] = (st.st_mtime_ns, st.st_size)
        return out
    before = snapshot(project)
    # check.py：每种视图与组合都跑一遍，并确认它们都真的执行成功（不是参数错退出）。
    for args in ((), ("--gates",), ("--json",), ("--gates", "--json"), ("--quiet",)):
        done = run("check.py", project, *args)
        assert done.returncode == 0, f"check.py {args} 在干净 run 上应 exit 0，实得 " \
                                    f"{done.returncode}\n{done.stdout}{done.stderr}"
    # status.py：只用它自己接受的参数。
    for args in ((), ("--json",), ("--cost",), ("--cost", "--json")):
        done = run("status.py", project, *args)
        assert done.returncode == 0, f"status.py {args} 应 exit 0，实得 {done.returncode}\n" \
                                    f"{done.stdout}{done.stderr}"
    assert snapshot(project) == before, "check.py/status.py 留下了写入"
    # 反向对照：确实不被接受的参数组合要被 argparse 拒绝，而不是被静默忽略。
    bogus = run("status.py", project, "--gates")
    assert bogus.returncode == 2 and "Traceback" not in bogus.stderr, bogus.stderr


@case("R9_manifest与包内容一致")
def r9(root):
    """MANIFEST.txt 曾漂移（版本写 1.1.0、4 个哈希错、2 个行数错）。现在它由脚本生成，
    并用 --check 比对：手改包而不重跑它就会被这条用例抓住。"""
    checked = run("manifest.py", "--check")
    assert checked.returncode == 0, f"MANIFEST.txt 与包内容不一致：{checked.stderr}"


@case("N1_node开节点与汇合")
def n1(root):
    """F1：协议里除建 run 之外的写操作此前全靠手改 JSON。"""
    project = os.path.join(root, "forkproj")
    assert scaffold(project, "1918年大流感改变了日本的公共卫生立法吗？", "--depth", "2").returncode == 0
    ledger_path = os.path.join(run_dir_of(project), "run.json")
    root_id = read_json(ledger_path)["nodes"][0]["id"]
    decided = run("node.py", project, "decide", "--node", root_id, "--id", "d1",
                  "--question", "国内建构还是帝国剧目？", "--stakes", "决定比较对象",
                  "--option", "id=o1,label=国内,premise=战前能力,own",
                  "--option", "id=o2,label=帝国,premise=殖民范畴")
    assert decided.returncode == 0, decided.stdout + decided.stderr
    forked = run("node.py", project, "fork", "--node", root_id, "--option", "o2",
                 "--question", "敕令把殖民卫生范畴移植进国内行政了吗？")
    assert forked.returncode == 0, forked.stdout + forked.stderr
    run_data = read_json(ledger_path)
    assert len(run_data["nodes"]) == 2
    child = run_data["nodes"][1]
    assert child["depth"] == 1 and child["parents"] == [root_id]
    assert child["opened_by"] == {"decision": "d1", "option": "o2"}, child["opened_by"]
    # 选项的归宿被写回：paths.md 现在显示"由谁在追"。
    assert run_data["decisions"][0]["options"][1]["node"] == child["id"]
    with open(os.path.join(run_dir_of(project), "paths.md"), encoding="utf-8") as fh:
        assert child["id"] in fh.read()
    # 节点目录与骨架文件真的建出来了。
    ndir = os.path.join(run_dir_of(project), "nodes", child["folder"])
    assert os.path.isfile(os.path.join(ndir, "plan.md"))
    # 一个可能只开一次：再为同一选项开节点要被拒。
    again = run("node.py", project, "fork", "--node", root_id, "--option", "o2",
                "--question", "换个说法再问一遍？")
    assert again.returncode == 2 and "只开一次" in again.stderr, again.stderr


@case("N2_汇合需两个已完成的父")
def n2(root):
    project, run_dir, ndir, ledger_path, run_data = build_full_run(root)
    parent = run_data["nodes"][0]["id"]
    # 第二个父：另一个已完成节点。
    run_data["nodes"].append({
        "id": "n_second01", "folder": "02-second", "seq": 2, "depth": 0, "kind": "root",
        "question": "第二问？", "parents": [], "status": "closed", "cards": [],
        "synthesis": None, "synthesis_versions": 0, "review_rounds": 1,
        "dissolves": None, "issues": [], "gaps": [], "no_forks": True,
    })
    os.makedirs(os.path.join(run_dir, "nodes", "02-second"), exist_ok=True)
    write_json(ledger_path, run_data)
    one = run("node.py", project, "join", "--parents", parent, "--question", "q?", "--rationale", "r")
    assert one.returncode == 2 and "至少两个" in one.stderr, one.stderr
    joined = run("node.py", project, "join", "--parents", f"{parent},n_second01",
                 "--question", "两线都把断裂定在 1919，之后怎样？",
                 "--rationale", "各带各的证据，一起带向前是对峙")
    assert joined.returncode == 0, joined.stdout + joined.stderr
    after = read_json(ledger_path)
    new_node = after["nodes"][-1]
    assert new_node["kind"] == "join" and len(new_node["parents"]) == 2
    assert after["joins"] and after["joins"][0]["rationale"]


@case("N3_状态机拒绝非法跃迁")
def n3(root):
    project, run_dir, ndir, ledger_path, run_data = build_full_run(root)
    node_id = run_data["nodes"][0]["id"]
    bad = run("node.py", project, "advance", node_id, "--to", "executing")
    assert bad.returncode == 2 and "跃迁" in bad.stderr, bad.stderr
    # 合法：failed → planning（重试）。
    run_data["nodes"][0]["status"] = "failed"
    write_json(ledger_path, run_data)
    ok = run("node.py", project, "advance", node_id, "--to", "planning")
    assert ok.returncode == 0, ok.stdout + ok.stderr
    # closed 的四项前提缺一就拒绝，不许无声关闭（重读账本，别用内存旧副本回写）。
    fresh = read_json(ledger_path)
    fresh["nodes"][0]["status"] = "deciding"
    fresh["nodes"][0]["possibility_file"] = None
    write_json(ledger_path, fresh)
    closed = run("node.py", project, "advance", node_id)
    assert closed.returncode == 2 and "possibility_file" in closed.stderr, closed.stderr


@case("N4_decide无分叉与拒绝约束")
def n4(root):
    project = os.path.join(root, "decide")
    assert scaffold(project, "另一个够长的研究问题会怎么展开？").returncode == 0
    ledger_path = os.path.join(run_dir_of(project), "run.json")
    node_id = read_json(ledger_path)["nodes"][0]["id"]
    ok = run("node.py", project, "decide", "--node", node_id, "--no-forks",
             "--reason", "本问题此处只容一条回答线")
    assert ok.returncode == 0, ok.stdout + ok.stderr
    assert read_json(ledger_path)["nodes"][0]["no_forks"] is True
    # 只给一个选项、或缺 stakes，同样要被拒（决策是 ≥2 个互斥选项）。
    one = run("node.py", project, "decide", "--node", node_id, "--id", "d2",
              "--question", "q?", "--stakes", "s", "--option", "id=o1,premise=p")
    assert one.returncode == 2, one.stdout + one.stderr
    no_stakes = run("node.py", project, "decide", "--node", node_id, "--id", "d3",
                    "--question", "q?", "--option", "id=o1,premise=p",
                    "--option", "id=o2,premise=p2")
    assert no_stakes.returncode == 2 and "stakes" in no_stakes.stderr, no_stakes.stderr
    # "不值得"不是拒绝的理由。
    refused = run("node.py", project, "decline", "--option", "a9", "--reason", "不值得")
    assert refused.returncode == 2 and "不是理由" in refused.stderr, refused.stderr
    good = run("node.py", project, "decline", "--option", "a9", "--reason", "节点预算已用尽：30/30。")
    assert good.returncode == 0, good.stdout + good.stderr


@case("N5_resume按节点续跑")
def n5(root):
    """F6：--resume 除重建视图外，还要说出下一次该从哪个阶段接手。"""
    project, run_dir, ndir, ledger_path, run_data = build_full_run(root)
    run_data["nodes"][0]["status"] = "disposing"
    write_json(ledger_path, run_data)
    node_id = run_data["nodes"][0]["id"]
    result = run("scaffold.py", project, "--resume", "--node", node_id)
    assert result.returncode == 0, result.stdout + result.stderr
    assert "disposing" in result.stdout and "处置" in result.stdout, result.stdout
    # 不带 --node 时点名第一个非终态节点。
    plain = run("scaffold.py", project, "--resume")
    assert plain.returncode == 0 and "续跑点" in plain.stdout, plain.stdout
    # 未知节点 id 要被拒，而不是静默重建全部。
    assert run("scaffold.py", project, "--resume", "--node", "n_nope").returncode == 2


@case("E1_行为级回归用例")
def e1(root):
    """F3：evals/artifact_cases 是行为级黄金样例（此前只有词法级触发用例）。"""
    result = run("run_artifact_eval.py")
    assert result.returncode == 0, result.stdout + result.stderr
    assert "全部通过" in result.stdout, result.stdout


@case("E2_行为用例目录被SKILL登记")
def e2(root):
    with open(os.path.join(SKILL_DIR, "SKILL.md"), encoding="utf-8") as fh:
        skill = fh.read()
    assert "evals/artifact_cases" in skill, "SKILL.md 的文件表未登记行为级用例"
    assert "run_artifact_eval.py" in skill, "SKILL.md 未说明怎么跑行为级用例"
    with open(os.path.join(SKILL_DIR, "evals", "trigger_cases.json"), encoding="utf-8") as fh:
        pass  # 触发用例仍在，且仍被 I9 校验


def normalize(text: str) -> str:
    return unicodedata.normalize("NFKC", text)


def main(argv=None) -> int:
    p = argparse.ArgumentParser(prog="test_skill.py", description=__doc__.splitlines()[0])
    p.add_argument("-k", dest="keyword", help="只跑名称含关键词的用例")
    args = p.parse_args(argv)

    selected = [c for c in CASES if not args.keyword or args.keyword in c[0]]
    failures = []
    for name, fn in selected:
        with tempfile.TemporaryDirectory(prefix="dr-test-") as root:
            try:
                fn(root)
                print(f"PASS  {name}")
            except AssertionError as error:
                failures.append(name)
                print(f"FAIL  {name}\n      {error}")
            except Exception as error:  # noqa: BLE001 - 测试要报一切异常
                failures.append(name)
                print(f"ERROR {name}\n      {type(error).__name__}: {error}")
    print(f"\n{len(selected) - len(failures)}/{len(selected)} 通过")
    if failures:
        print("失败用例：" + ", ".join(failures))
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
