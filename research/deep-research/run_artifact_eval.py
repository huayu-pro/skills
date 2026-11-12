#!/usr/bin/env python3
"""行为级回归评测：用黄金产物跑通真管线，而不是只比对词法。

用法：
    python3 run_artifact_eval.py

`evals/trigger_cases.json` 只测"该不该触发"（词法级）；本脚本测"触发之后产出的东西对不对"
（行为级）：把 `evals/artifact_cases/` 里的黄金 run 当成一个真实 run 跑一遍，断言

    1. `check.py` 全清且 `--gates` 六门禁全 clear（exit 0）；
    2. 把黄金产物按已知方式破坏后，对应门禁**必须**失败（必红）；
    3. `status.py --cost` 读到真实记账；
    4. `export.py` 能导出四件套与参考文献、清单；
    5. `scaffold.py --resume` 与 `node.py` 对它不报错。

第 2 条是本脚本存在的理由：只断言"干净产物能通过"的评测会与一个把所有门禁都放松成
note 的实现同时变绿。

退出码：0 全部通过；1 有失败。仅标准库；无网络；全部在临时目录中进行（黄金目录只读）。
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
SKILL_DIR = os.path.dirname(HERE)
GOLDEN = os.path.join(SKILL_DIR, "evals", "artifact_cases")


def run(script: str, *args, cwd=None):
    return subprocess.run([sys.executable, os.path.join(HERE, script), *args],
                          capture_output=True, text=True, cwd=cwd)


def copy_golden(dest: str) -> str:
    target = os.path.join(dest, "proj", "research", "r_golden")
    os.makedirs(os.path.dirname(target), exist_ok=True)
    shutil.copytree(GOLDEN, target)
    return os.path.join(dest, "proj")


def read_json(path: str):
    with open(path, encoding="utf-8") as handle:
        return json.load(handle)


def write_json(path: str, data) -> None:
    with open(path, "w", encoding="utf-8") as handle:
        json.dump(data, handle, ensure_ascii=False, indent=2)


class Failures:
    def __init__(self):
        self.items: list[str] = []

    def expect(self, condition: bool, message: str) -> None:
        if not condition:
            self.items.append(message)

    def __bool__(self):
        return not self.items


def main(argv=None) -> int:
    p = argparse.ArgumentParser(prog="run_artifact_eval.py", description=__doc__.splitlines()[0])
    p.parse_args(argv)

    if not os.path.isfile(os.path.join(GOLDEN, "run.json")):
        print(f"缺黄金产物：{GOLDEN}/run.json", file=sys.stderr)
        return 1
    bad = Failures()

    # ---- 1. 干净产物：全清
    with tempfile.TemporaryDirectory(prefix="dr-artifact-") as tmp:
        project = copy_golden(tmp)
        clean = run("check.py", project)
        bad.expect(clean.returncode == 0,
                   f"黄金 run 应全清，实得 exit={clean.returncode}\n{clean.stdout}{clean.stderr}")
        gated = run("check.py", project, "--gates")
        bad.expect(gated.returncode == 0,
                   f"黄金 run 的关卡视图应 exit 0，实得 {gated.returncode}\n{gated.stdout}")
        for gate in ("ANGLE", "COVERAGE", "CITATION", "TAXONOMY", "CALIBRATION", "WEAVING"):
            bad.expect(gate in gated.stdout, f"关卡视图缺 {gate}")
        bad.expect("FAIL" not in gated.stdout, f"黄金 run 不该有关卡失败：\n{gated.stdout}")

        # ---- 3. 真实记账
        cost = run("status.py", project, "--cost")
        bad.expect(cost.returncode == 0 and "12400" in cost.stdout,
                   f"成本视图应读到真实记账 12400 token：{cost.stdout}{cost.stderr}")

        # ---- 4. 导出
        dest = os.path.join(tmp, "交付")
        exported = run("export.py", project, "--dest", dest, "--name", "golden",
                       "--format", "html", "--references", "--manifest")
        bad.expect(exported.returncode == 0, f"导出失败：{exported.stdout}{exported.stderr}")
        for name in ("golden.html", "golden-survey.html", "golden-question.md",
                     "golden-references.html", "golden-manifest.json"):
            bad.expect(os.path.isfile(os.path.join(dest, name)), f"导出缺 {name}")
        html = open(os.path.join(dest, "golden.html"), encoding="utf-8").read() \
            if os.path.isfile(os.path.join(dest, "golden.html")) else ""
        bad.expect("<h1>" in html and "</html>" in html, "HTML 渲染不完整")

        # ---- 5. 恢复与写操作
        resumed = run("scaffold.py", project, "--resume")
        bad.expect(resumed.returncode == 0, f"--resume 失败：{resumed.stderr}")
        node_id = read_json(os.path.join(project, "research", "r_golden", "run.json"))["nodes"][0]["id"]
        declined = run("node.py", project, "decline", "--option", "a9",
                       "--reason", "深度限制：本层不再分叉。")
        bad.expect(declined.returncode == 0, f"node.py decline 失败：{declined.stderr}")
        bad.expect(bool(node_id), "黄金 run 没有节点 id")

    # ---- 2. 必红：逐个破坏，逐个断言对应门禁失败
    for label, mutate, expect_gate in MUTATIONS:
        with tempfile.TemporaryDirectory(prefix="dr-artifact-") as tmp:
            project = copy_golden(tmp)
            run_dir = os.path.join(project, "research", "r_golden")
            mutate(run_dir)
            gated = run("check.py", project, "--gates")
            bad.expect(gated.returncode != 0,
                       f"[{label}] 破坏后 --gates 应 exit 非 0，实得 {gated.returncode}\n{gated.stdout}")
            if expect_gate:
                bad.expect(f"{expect_gate.ljust(12)} (major" in gated.stdout
                           or f"{expect_gate.ljust(12)} (critical" in gated.stdout,
                           f"[{label}] 关卡视图未把 {expect_gate} 显示为 FAIL：\n{gated.stdout}")
                line = next((ln for ln in gated.stdout.splitlines()
                             if ln.startswith(expect_gate)), "")
                bad.expect("FAIL" in line, f"[{label}] {expect_gate} 行不是 FAIL：{line!r}")

    if bad:
        print(f"行为级回归：全部通过（{len(MUTATIONS) + 1} 组）")
        return 0
    print("行为级回归：失败", file=sys.stderr)
    for item in bad.items:
        if item:
            print(f"  ✗ {item}", file=sys.stderr)
    return 1


def break_coverage(run_dir: str) -> None:
    """抹掉覆盖表里那行 declared gap：卡列空、缺口列也空 → 未声明的疏忽。"""
    path = os.path.join(run_dir, "nodes", "01-golden", "plan.md")
    text = open(path, encoding="utf-8").read()
    text = text.replace("| 府县执行 | — | **declared gap：无卡，经约定不在范围** |",
                        "| 府县执行 |  |  |")
    open(path, "w", encoding="utf-8").write(text)


def break_angle(run_dir: str) -> None:
    path = os.path.join(run_dir, "nodes", "01-golden", "synthesis.md")
    text = open(path, encoding="utf-8").read()
    text = text.replace("1918 年大流感没有直接改写立法文本；", "本文综述了 1918 年前后的相关立法：")
    open(path, "w", encoding="utf-8").write(text)


def break_citation(run_dir: str) -> None:
    path = os.path.join(run_dir, "nodes", "01-golden", "cards", "c1-statutes", "findings.json")
    data = read_json(path)
    data["findings"][0]["citation_state"] = "invalid"
    write_json(path, data)


def break_calibration(run_dir: str) -> None:
    path = os.path.join(run_dir, "nodes", "01-golden", "synthesis.md")
    text = open(path, encoding="utf-8").read()
    text = text.replace("它改变的是行政实践与立法气候，", "这证明了行政实践与立法气候被彻底改变，")
    open(path, "w", encoding="utf-8").write(text)


def break_taxonomy(run_dir: str) -> None:
    path = os.path.join(run_dir, "final", "r_golden-final.md")
    text = open(path, encoding="utf-8").read()
    text = text.replace("## 立法文本与行政实践的分野", "## Card 1\n\n")
    text = text.replace("## 行政能力读法与其反对者", "## Source 2\n\n")
    open(path, "w", encoding="utf-8").write(text)


def break_weaving(run_dir: str) -> None:
    paras = [f"第 {i + 1} 段只谈一份材料 `sources/kampo.txt`，不复述第二位作者的说法，"
             f"也不比较两种记录之间的差异，只是把这一份材料的内容平铺开来写成一段足够长的正文。"
             for i in range(5)]
    open(os.path.join(run_dir, "final", "r_golden-final.md"), "w", encoding="utf-8").write(
        "# 报告\n\n" + "\n\n".join(paras) + "\n")


def break_locator(run_dir: str) -> None:
    path = os.path.join(run_dir, "final", "r_golden-final.md")
    text = open(path, encoding="utf-8").read()
    open(path, "w", encoding="utf-8").write(
        text + "\n另见 `sources/never-fetched.txt`。\n")


def break_schema(run_dir: str) -> None:
    path = os.path.join(run_dir, "run.json")
    data = read_json(path)
    data["schema"] = 99
    write_json(path, data)


MUTATIONS = [
    ("Coverage 未声明空格", break_coverage, "COVERAGE"),
    ("Angle 综述式开头", break_angle, "ANGLE"),
    ("Citation invalid", break_citation, "CITATION"),
    ("Calibration 过度断言", break_calibration, "CALIBRATION"),
    ("Taxonomy 按来源分节", break_taxonomy, "TAXONOMY"),
    ("Weaving 一段一来源", break_weaving, "WEAVING"),
    ("终稿定位符不解析", break_locator, "CITATION"),
    ("schema 不认识的值", break_schema, None),
]


if __name__ == "__main__":
    sys.exit(main())
