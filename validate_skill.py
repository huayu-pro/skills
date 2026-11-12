#!/usr/bin/env python3
"""skill-creator-cn 自带校验器：对任意技能目录做结构与规范校验。

用法：python3 validate_skill.py <技能目录> [--trigger] [--self-test]
--trigger 在结构校验通过后联动运行触发冒烟评测（run_trigger_eval.py）；
存在结构性失败时跳过并显式说明，不在坏包上盲跑。
--self-test 不校验目标目录，改为对校验器自身跑必红自测：每条检查规则
配一个应失败的迷你坏包，断言校验器真的会失败——永不失败的门禁等于没有门禁。
检查项：frontmatter/字段白名单/name/description/行数词数/TODO/资源引用/
脚本语法/触发用例（含 near_neighbor 桶）/版本一致性（frontmatter vs
_meta.json vs CHANGELOG.md；版本源不足两处时显式警告未交叉比对）/
SKILL.md 与 references 递归内嵌代码块语法（bash -n、ast、node --check，
围栏状态机抗嵌套）/references 递归相对引用存在性/裸文本 .md 提及存在性。
退出码：0 全部通过；1 存在失败项（警告不计失败）。
"""

import argparse
import ast
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

try:
    import yaml
except ImportError:
    print("[失败] 缺少 PyYAML 依赖，先执行: pip install pyyaml")
    sys.exit(1)

ALLOWED_KEYS = {
    # 核心字段（agentskills.io 通用集）
    "name", "description", "license", "allowed-tools", "metadata", "compatibility",
    # Claude Code 专有字段（见 references/frontmatter-fields.md）
    "when_to_use", "argument-hint", "arguments", "user-invocable",
    "disable-model-invocation", "disallowed-tools", "model", "effort",
    "context", "agent", "background", "hooks", "paths", "shell",
    # SkillHub 上架字段与国内生态扩展（发布时追加，字段名同名不同值，见 references/frontmatter-fields.md）
    "slug", "displayName", "version", "summary", "tags",
}

REF_RE = re.compile(r"(?:references|scripts|assets|evals)/[\w\-./]+\.(?:md|py|json|html|txt|csv|png|jpg|jpeg|svg|webp)")


# ---------------- 必红自测（--self-test） ----------------
# 每条检查规则配一个应失败的迷你技能包；另有全绿样本防自测自身永真。
# 期望三元组：(kind, 需要出现在输出里的子串...)，kind ∈ fail(exit1)/warn(exit0+警告)/pass(exit0)/package

GREEN_SKILL_MD = """---
name: {name}
description: 转换工具：把 CSV 转成 JSON。Use when 用户说 csv 转 json 或格式转换。Exclude 其他格式与网页抓取。
---

# {title}

把 CSV 转成 JSON 的小工具技能。

## 步骤

1. 读取输入 CSV，输出 JSON 文件。

```bash
python3 convert.py input.csv output.json
```

## 验证清单

- [ ] 输出 JSON 可被 json.load 解析
"""


def _write(path, content):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def _green(root, name="green-skill"):
    d = root / name
    _write(d / "SKILL.md", GREEN_SKILL_MD.format(name=name, title="Green Skill"))
    _write(d / "evals" / "trigger_cases.json", json.dumps({
        "recommended_threshold": 0.34,
        "description_required_concepts": ["convert"],
        "positive_concepts": {"convert": ["convert", "转换"]},
        "negative_patterns": ["翻译一下"],
        "should_trigger": [{"text": "帮我把这个 csv 转成 json", "family": "t"}],
        "should_not_trigger": [{"text": "把这篇文章翻译成英文", "family": "n"}],
        "near_neighbor": [],
    }, ensure_ascii=False, indent=2))
    return d


def _unknown_key(root):
    d = root / "unknown-key"
    _write(d / "SKILL.md", GREEN_SKILL_MD.format(name="unknown-key", title="U").replace(
        "Exclude 其他格式与网页抓取。",
        "Exclude 其他格式与网页抓取。\nextra-key: nope"))
    return d


def _dir_mismatch(root):
    d = _green(root, "right-name")
    renamed = root / "wrong-name"
    d.rename(renamed)
    return renamed


def _bad_name(root):
    d = root / "bad-name"
    _write(d / "SKILL.md", GREEN_SKILL_MD.format(name="My Skill", title="B"))
    return d


def _desc_too_long(root):
    d = root / "desc-long"
    _write(d / "SKILL.md", GREEN_SKILL_MD.format(
        name="desc-long", title="D").replace(
        "转换工具：把 CSV 转成 JSON。Use when 用户说 csv 转 json 或格式转换。Exclude 其他格式与网页抓取。",
        "转换工具。" + "补" * 1100))
    return d


def _desc_angle(root):
    d = root / "desc-angle"
    _write(d / "SKILL.md", GREEN_SKILL_MD.format(
        name="desc-angle", title="D").replace(
        "转换工具：把 CSV 转成 JSON。Use when 用户说 csv 转 json 或格式转换。Exclude 其他格式与网页抓取。",
        "转换工具。Use when 输入 <input.csv>。"))
    return d


def _too_many_lines(root):
    d = root / "lines-over"
    body = GREEN_SKILL_MD.format(name="lines-over", title="L").rstrip("\n")
    body += "".join(f"\n第 {i} 行填充内容" for i in range(1, 520))
    _write(d / "SKILL.md", body + "\n")
    return d


def _missing_ref(root):
    d = root / "missing-ref"
    _write(d / "SKILL.md", GREEN_SKILL_MD.format(name="missing-ref", title="M")
           + "\n细则见 [references/ghost.md](references/ghost.md)。\n")
    return d


def _bad_script(root):
    d = _green(root, "bad-script")
    _write(d / "scripts" / "bad.py", "def (:\n")
    return d


def _bad_cases_json(root):
    d = _green(root, "bad-cases")
    _write(d / "evals" / "trigger_cases.json", "{not json")
    return d


def _version_mismatch(root):
    d = root / "version-skill"
    _write(d / "SKILL.md", GREEN_SKILL_MD.format(name="version-skill", title="V")
           .replace("description:", 'metadata:\n  version: "1.0.0"\ndescription:'))
    _write(d / "_meta.json", json.dumps({"name": "version-skill", "version": "9.9.9"}))
    return d


def _version_single_source(root):
    d = root / "single-source"
    _write(d / "SKILL.md", GREEN_SKILL_MD.format(name="single-source", title="S")
           .replace("description:", 'metadata:\n  version: "1.0.0"\ndescription:'))
    return d


def _embedded_bash(root):
    d = root / "embed-bash"
    _write(d / "SKILL.md", GREEN_SKILL_MD.format(name="embed-bash", title="E")
           + "\n```bash\nfi fi\n```\n")
    return d


def _embedded_python(root):
    d = root / "embed-py"
    _write(d / "SKILL.md", GREEN_SKILL_MD.format(name="embed-py", title="E")
           + "\n```python\ndef (:\n```\n")
    return d


def _nested_ref_broken(root):
    d = root / "nested-ref"
    _write(d / "SKILL.md", GREEN_SKILL_MD.format(name="nested-ref", title="N"))
    _write(d / "references" / "sub" / "deep.md",
           "# 深层细则\n\n参见 [ghost.md](ghost.md)。\n")
    return d


def _bare_md_missing(root):
    d = root / "bare-md"
    _write(d / "SKILL.md", GREEN_SKILL_MD.format(name="bare-md", title="B")
           + "\n详见 ghost_notes.md 的说明。\n")
    return d


def _todo_warn(root):
    d = root / "todo-skill"
    _write(d / "SKILL.md", GREEN_SKILL_MD.format(name="todo-skill", title="T")
           + "\nTODO: 接入批量模式，真实未完成。\n")
    return d


def _package_mtime(root):
    d = _green(root, "pkg-mtime")
    os.utime(d / "SKILL.md", (0, 0))
    return d


def _no_skill_md(root):
    d = root / "no-skill-md"
    d.mkdir(parents=True, exist_ok=True)
    return d


def _no_frontmatter(root):
    d = root / "no-fm"
    _write(d / "SKILL.md", "# No Frontmatter\n\n正文没有 YAML 头。\n")
    return d


def _fm_not_dict(root):
    d = root / "fm-list"
    _write(d / "SKILL.md", "---\n- a\n- b\n---\n\n# F\n\n正文。\n")
    return d


def _name_not_str(root):
    d = root / "name-num"
    _write(d / "SKILL.md",
           "---\nname: 123\ndescription: 转换工具。Use when 用户说转换。Exclude 其他。\n---\n\n# N\n\n正文。\n")
    return d


def _metadata_not_dict(root):
    d = root / "meta-str"
    _write(d / "SKILL.md", GREEN_SKILL_MD.format(name="meta-str", title="M").replace(
        "description:", 'metadata: "1.5.0"\ndescription:'))
    return d


def _word_over(root):
    d = root / "wordy"
    body = GREEN_SKILL_MD.format(name="wordy", title="W").rstrip("\n")
    body += "\n\n" + ("长" * 3100) + "\n"
    _write(d / "SKILL.md", body + "\n")
    return d


def _unclosed_fence(root):
    d = root / "unclosed"
    _write(d / "SKILL.md", GREEN_SKILL_MD.format(name="unclosed", title="U")
           + "\n```bash\necho 未闭合\n")
    return d


def _url_no_false_positive(root):
    d = root / "url-ok"
    _write(d / "SKILL.md", GREEN_SKILL_MD.format(name="url-ok", title="U")
           + "\n外链示例：https://example.com/references/ghost.md 与 https://example.com/scripts/x.py\n")
    return d


def _nested_script(root):
    d = _green(root, "nested-script")
    _write(d / "scripts" / "sub" / "bad.py", "def (:\n")
    return d


def _cases_not_dict(root):
    d = root / "cases-list"
    _write(d / "SKILL.md", GREEN_SKILL_MD.format(name="cases-list", title="C"))
    _write(d / "evals" / "trigger_cases.json", "[]")
    return d


def _empty_buckets_trigger(root):
    d = root / "empty-buckets"
    _write(d / "SKILL.md", GREEN_SKILL_MD.format(name="empty-buckets", title="E"))
    _write(d / "evals" / "trigger_cases.json", json.dumps({
        "recommended_threshold": 0.34,
        "description_required_concepts": ["convert"],
        "positive_concepts": {"convert": ["convert", "转换"]},
        "negative_patterns": [],
        "should_trigger": [], "should_not_trigger": [], "near_neighbor": [],
    }, ensure_ascii=False, indent=2))
    return d


def _run_validator(case_dir, extra_args=()):
    return subprocess.run(
        [sys.executable, str(Path(__file__).resolve()), str(case_dir), *extra_args],
        capture_output=True, text=True, timeout=120)


def run_self_test():
    """必红自测：对每条检查规则构造应失败的迷你包并断言校验器真的报错。"""
    bash_ok = shutil.which("bash") is not None
    node_ok = shutil.which("node") is not None
    cases = [
        ("全绿样本不误报", _green, ("pass",)),
        ("未知字段必红", _unknown_key, ("fail", "未知字段")),
        ("目录名与 name 不一致必红", _dir_mismatch, ("fail", "不一致")),
        ("name 非 kebab-case 必红", _bad_name, ("fail", "kebab-case")),
        ("description 超 1024 必红", _desc_too_long, ("fail", "超过 1024")),
        ("description 含尖括号必红", _desc_angle, ("fail", "尖括号")),
        ("SKILL.md 达 500 行上限必红", _too_many_lines, ("fail", "500 行")),
        ("正文引用断链必红", _missing_ref, ("fail", "包内不存在的文件")),
        ("脚本语法错误必红", _bad_script, ("fail", "脚本语法错误")),
        ("触发用例坏 JSON 必红", _bad_cases_json, ("fail", "不是合法 JSON")),
        ("版本号不一致必红", _version_mismatch, ("fail", "版本号不一致")),
        ("版本单源显式警告（未交叉比对）", _version_single_source, ("warn", "未做交叉比对")),
        ("内嵌 bash 语法错误必红", _embedded_bash, ("fail", "内嵌 bash 代码块语法错误")),
        ("内嵌 python 语法错误必红", _embedded_python, ("fail", "内嵌 python 代码块语法错误")),
        ("嵌套 references 断链必红（递归扫描）", _nested_ref_broken, ("fail", "包内不存在的文件")),
        ("裸文本 .md 提及断链必红", _bare_md_missing, ("fail", "提及但包内不存在")),
        ("真实 TODO 触发警告", _todo_warn, ("warn", "TODO")),
        ("打包时间戳钳制（TZ=UTC-5 + mtime=0 不崩）", _package_mtime, ("package",)),
        ("缺 SKILL.md 必红", _no_skill_md, ("fail", "缺少 SKILL.md")),
        ("缺 frontmatter 必红", _no_frontmatter, ("fail", "缺少 YAML frontmatter")),
        ("frontmatter 非字典必红", _fm_not_dict, ("fail", "frontmatter 必须是 YAML 字典")),
        ("name 非字符串必红", _name_not_str, ("fail", "name 必须是字符串")),
        ("metadata 非字典显式警告", _metadata_not_dict, ("warn", "metadata 不是字典")),
        ("词数超限触发警告", _word_over, ("warn", "估算词数")),
        ("未闭合围栏显式警告", _unclosed_fence, ("warn", "未闭合")),
        ("URL 路径不误报断链", _url_no_false_positive, ("pass",)),
        ("嵌套 scripts 语法错误必红（递归）", _nested_script, ("fail", "脚本语法错误")),
        ("触发用例顶层非对象必红", _cases_not_dict, ("fail", "顶层必须是 JSON 对象")),
        ("空桶评测不再空转通过（--trigger 必红）", _empty_buckets_trigger, ("fail-trigger", "触发冒烟评测未通过")),
    ]
    skipped = []
    if not bash_ok:
        skipped.append("内嵌 bash 语法错误必红（bash 不可用）")
    print(f"必红自测：{len(cases)} 个用例（每条检查规则一个应失败的迷你包 + 全绿样本防永真）")
    failures = []
    with tempfile.TemporaryDirectory(prefix="skill-selftest-") as tmp:
        tmp_root = Path(tmp)
        for name, builder, expect in cases:
            if name.startswith("内嵌 bash") and not bash_ok:
                continue
            try:
                case_dir = builder(tmp_root)
                if expect[0] == "package":
                    out_dir = tmp_root / "pkg-out"
                    probe = subprocess.run(
                        [sys.executable, str(Path(__file__).resolve().parent / "package_skill.py"),
                         str(case_dir), "--no-validate", "--out", str(out_dir),
                         "--out-name", "pkg-test.zip"],
                        capture_output=True, text=True, timeout=120,
                        env={**os.environ, "TZ": "Etc/GMT+5"})
                    problems = []
                    if probe.returncode != 0:
                        problems.append(f"期望打包成功（exit 0），实际 exit {probe.returncode}")
                    if "已打包" not in probe.stdout:
                        problems.append("输出缺少「已打包」")
                else:
                    kind = expect[0]
                    extra_args = ["--trigger"] if kind == "fail-trigger" else []
                    probe = _run_validator(case_dir, extra_args)
                    want_exit = 1 if kind in ("fail", "fail-trigger") else 0
                    problems = []
                    if probe.returncode != want_exit:
                        problems.append(f"期望 exit {want_exit}，实际 {probe.returncode}")
                    for needle in expect[1:]:
                        if needle not in probe.stdout:
                            problems.append(f"输出缺少「{needle}」")
                    if kind == "pass" and "[失败]" in probe.stdout:
                        problems.append("全绿样本出现 [失败]")
                if problems:
                    failures.append(name)
                    print(f"[自测失败] {name}：{'；'.join(problems)}")
                else:
                    print(f"[自测通过] {name}")
            except subprocess.TimeoutExpired:
                failures.append(name)
                print(f"[自测失败] {name}：子进程超时")
            except Exception as e:
                failures.append(name)
                print(f"[自测失败] {name}：用例构造异常 {type(e).__name__}: {e}")
    for note in skipped:
        print(f"[自测跳过] {note}")
    print()
    if failures:
        print(f"结论：自测未通过（{len(failures)} 项）——存在「永不失败的门禁」或检查行为漂移")
        return 1
    print("结论：必红自测全部通过——每条规则都在应失败的输入上真的失败了")
    return 0


def main():
    parser = argparse.ArgumentParser(description="技能目录结构规范校验器")
    parser.add_argument("skill_dir", nargs="?", help="技能目录（--self-test 时可省略）")
    parser.add_argument("--trigger", action="store_true",
                        help="联动运行触发冒烟评测 run_trigger_eval.py")
    parser.add_argument("--self-test", action="store_true",
                        help="对校验器自身跑必红用例自测（忽略 skill_dir）")
    args = parser.parse_args()
    if args.self_test:
        sys.exit(run_self_test())
    if not args.skill_dir:
        parser.error("请提供技能目录，或用 --self-test 自测校验器本身")
    root = Path(args.skill_dir).resolve()
    failures, warnings = [], []

    def ok(msg):
        print(f"[通过] {msg}")

    def warn(msg):
        warnings.append(msg)
        print(f"[警告] {msg}")

    def fail(msg):
        failures.append(msg)
        print(f"[失败] {msg}")

    skill_md = root / "SKILL.md"
    if not skill_md.is_file():
        fail(f"缺少 SKILL.md：{skill_md}")
        sys.exit(1)
    text = skill_md.read_text(encoding="utf-8")

    # 1. frontmatter 可解析
    m = re.match(r"^---\n(.*?)\n---", text, re.DOTALL)
    if not m:
        fail("缺少 YAML frontmatter")
        sys.exit(1)
    try:
        fm = yaml.safe_load(m.group(1))
        if not isinstance(fm, dict):
            fail("frontmatter 必须是 YAML 字典")
            sys.exit(1)
    except yaml.YAMLError as e:
        fail(f"frontmatter YAML 解析失败：{e}")
        sys.exit(1)
    ok("frontmatter 可解析")

    # 2. 字段白名单
    unknown = set(fm) - ALLOWED_KEYS
    if unknown:
        fail(f"未知字段：{', '.join(sorted(unknown))}")
    else:
        ok("字段均在白名单内")

    # 3. name 规范与目录一致性
    name = fm.get("name", "")
    if not isinstance(name, str):
        fail(f"name 必须是字符串，实际为 {type(name).__name__}：{name!r}")
    elif not re.fullmatch(r"[a-z0-9-]+", name or ""):
        fail(f"name 不符合 kebab-case：{name!r}")
    elif name.startswith("-") or name.endswith("-") or "--" in name:
        fail(f"name 连字符使用不合规：{name}")
    elif len(name) > 64:
        fail(f"name 超过 64 字符：当前 {len(name)}")
    elif root.name != name:
        fail(f"目录名 {root.name!r} 与 name {name!r} 不一致")
    else:
        ok(f"name 合规且与目录名一致：{name}")

    # 4. description 规范
    desc = fm.get("description", "")
    if not isinstance(desc, str) or not desc.strip():
        fail("description 缺失或为空")
    elif len(desc) > 1024:
        fail(f"description 超过 1024 字符：当前 {len(desc)}")
    elif "<" in desc or ">" in desc:
        fail("description 含尖括号")
    else:
        ok(f"description 合规（{len(desc)} 字符）")

    # 5. 行数（硬门）与词数（软警告，中文按 2 字符≈1 词估算）
    lines = text.count("\n") + (0 if text.endswith("\n") else 1)
    if lines >= 500:
        fail(f"SKILL.md 已 {lines} 行，达到 500 行上限，深度内容应下沉 references/")
    else:
        ok(f"SKILL.md {lines} 行（<500）")
    cjk = len(re.findall(r"[\u4e00-\u9fff]", text))
    words = len(re.findall(r"[A-Za-z0-9]+", text)) + cjk // 2
    if words > 1500:
        warn(f"估算词数约 {words}（>1500），建议精简或下沉到 references/")
    else:
        ok(f"估算词数约 {words}（≤1500）")

    # 6. TODO/FIXME（命中需人工确认，检查示例中的字样不算）
    hits = [
        f"第 {i} 行：{line.strip()[:50]}"
        for i, line in enumerate(text.splitlines(), 1)
        if re.search(r"\b(TODO|FIXME)\b", line)
    ]
    if hits:
        warn("TODO/FIXME 命中，逐条确认为真实未完成标记（示例字样不算）：\n      " + "\n      ".join(hits))
    else:
        ok("无 TODO/FIXME 命中")

    # 7. 正文引用的打包资源必须存在（先剥 URL，外链路径里的包内样式片段不算包内引用）
    ref_text = re.sub(r"(?:https?|ftp)://\S+", "", text)
    missing = [ref for ref in sorted(set(REF_RE.findall(ref_text))) if not (root / ref).exists()]
    if missing:
        fail("正文引用但包内不存在的文件：" + ", ".join(missing))
    else:
        ok("正文引用的资源文件均存在")

    # 8. 包内脚本语法检查（ast 解析，无副作用；递归扫描子目录）
    scripts_dir = root / "scripts"
    if scripts_dir.is_dir():
        for script in sorted(scripts_dir.rglob("*.py")):
            try:
                ast.parse(script.read_text(encoding="utf-8"))
                ok(f"脚本语法通过：{script.relative_to(root)}")
            except SyntaxError as e:
                fail(f"脚本语法错误 {script.relative_to(root)}：{e}")

    # 9. 触发用例与 evals JSON（Production 档；递归扫描子目录）
    cases = root / "evals" / "trigger_cases.json"
    if cases.exists():
        try:
            data = json.loads(cases.read_text(encoding="utf-8"))
            if not isinstance(data, dict):
                fail("trigger_cases.json 顶层必须是 JSON 对象（dict）")
            else:
                pos = len(data.get("should_trigger", []))
                neg = len(data.get("should_not_trigger", []))
                near = len(data.get("near_neighbor", []))
                if pos and neg:
                    detail = f"触发用例可解析：正例 {pos} 条，负例 {neg} 条"
                    if near:
                        detail += f"，近邻 {near} 条"
                    ok(detail)
                else:
                    warn("trigger_cases.json 缺少 should_trigger 或 should_not_trigger")
        except json.JSONDecodeError as e:
            fail(f"trigger_cases.json 不是合法 JSON：{e}")
    else:
        warn("无 evals/trigger_cases.json（Production 档应补触发用例）")
    evals_dir = root / "evals"
    if evals_dir.is_dir():
        for extra in sorted(evals_dir.rglob("*.json")):
            if extra.name == "trigger_cases.json":
                continue
            try:
                json.loads(extra.read_text(encoding="utf-8"))
                ok(f"evals JSON 可解析：{extra.relative_to(root)}")
            except json.JSONDecodeError as e:
                fail(f"{extra.relative_to(root)} 不是合法 JSON：{e}")

    # 10. 版本一致性（frontmatter vs _meta.json vs CHANGELOG.md）
    # 版本源不足两处时显式警告「未交叉比对」——条件不满足就当通过是校验器最大的盲区来源；
    # 源文件存在但提取不到版本号时同样显式警告且不计入有效版本源（防空转通过）
    raw_metadata = fm.get("metadata")
    if raw_metadata is not None and not isinstance(raw_metadata, dict):
        warn(f"frontmatter metadata 不是字典（{type(raw_metadata).__name__}），忽略其内容")
        raw_metadata = None
    fm_version = str((raw_metadata or {}).get("version") or "").strip()
    if not fm_version:
        warn("frontmatter 无 metadata.version，跳过版本一致性比对")
    else:
        mismatches = []
        sources = 1
        meta_path = root / "_meta.json"
        if meta_path.exists():
            try:
                meta = json.loads(meta_path.read_text(encoding="utf-8"))
                if not isinstance(meta, dict):
                    warn("_meta.json 顶层不是 JSON 对象，跳过其版本比对")
                else:
                    meta_ver = str(meta.get("version") or "").strip()
                    if meta_ver:
                        sources += 1
                        if meta_ver != fm_version:
                            mismatches.append(f"_meta.json={meta_ver}")
                    else:
                        warn("_meta.json 存在但没有 version 字段，未参与版本比对")
                    meta_name = str(meta.get("name") or "").strip()
                    if meta_name and meta_name != fm.get("name"):
                        warn(f"_meta.json 的 name（{meta_name}）与 frontmatter name 不一致")
            except json.JSONDecodeError as e:
                warn(f"_meta.json 不是合法 JSON，跳过其版本比对：{e}")
        changelog = root / "CHANGELOG.md"
        if changelog.exists():
            head = changelog.read_text(encoding="utf-8")[:2000]
            m2 = re.search(r"(\d+\.\d+\.\d+)", head)
            if m2:
                sources += 1
                if m2.group(1) != fm_version:
                    mismatches.append(f"CHANGELOG.md={m2.group(1)}")
            else:
                warn("CHANGELOG.md 存在但开头未提取到版本号，未参与版本比对")
        if mismatches:
            fail(f"版本号不一致：frontmatter={fm_version}，{', '.join(mismatches)}")
        elif sources < 2:
            warn(f"版本一致性仅 {sources} 处有效版本源（缺 _meta.json 或 CHANGELOG.md，"
                 "或其中未含版本号），未做交叉比对——本项未完整检查，不等于通过")
        else:
            ok(f"版本号一致：{fm_version}（{sources} 处源交叉比对）")

    # 11. SKILL.md 与 references/*.md 内嵌代码块语法（bash -n / ast / node --check，工具缺失则跳过该语言）
    # 文档占位符 <xxx> 在 bash/python 里必然是语法错误，校验前统一替换为合法标识符；
    # 围栏扫描用状态机：任意围栏（含 markdown 等非五语言）开启后进入收集态直到闭合，
    # 其内部行不再开新块——防止「示例文档块内嵌代码块」的元文档被错误配对
    lang_alias = {"sh": "bash", "py": "python", "js": "javascript"}
    fence_langs = {"bash", "sh", "python", "py", "javascript", "js"}
    bash_bin = shutil.which("bash")
    node_bin = shutil.which("node")

    def scan_fences(md_text):
        blocks, lang, buf = {}, None, []
        for line in md_text.splitlines():
            stripped = line.strip()
            if lang is None:
                m = re.match(r"^```(\S*)", stripped)
                if m:
                    lang = m.group(1) or "plain"
            elif stripped.startswith("```"):
                if lang in fence_langs:
                    body = re.sub(r"<[^<>\n]+>", "PLACEHOLDER", "\n".join(buf))
                    key = lang_alias.get(lang, lang)
                    blocks.setdefault(key, []).append(body)
                lang, buf = None, []
            else:
                buf.append(line)
        # 未闭合围栏必须上报：静默丢弃会让其后所有代码块逃过语法检查（M3 实录）
        return blocks, lang

    refs_dir = root / "references"
    # 递归收集 references/**/*.md——只扫顶层子目录会让嵌套细则成为盲区
    ref_docs = sorted(refs_dir.rglob("*.md")) if refs_dir.is_dir() else []
    doc_files = [skill_md] + ref_docs
    doc_pass_notes = []
    for doc in doc_files:
        blocks, unclosed = scan_fences(doc.read_text(encoding="utf-8"))
        if unclosed is not None:
            warn(f"{doc.relative_to(root)} 存在未闭合的 ```{unclosed} 围栏，围栏内内容未做语法检查")
        notes = []
        for lang in sorted(blocks):
            bodies = blocks[lang]
            errs = []
            checked = True
            if lang == "bash":
                if bash_bin:
                    for i, body in enumerate(bodies, 1):
                        with tempfile.NamedTemporaryFile("w", suffix=".sh", delete=False) as tf:
                            tf.write(body)
                            tf_path = tf.name
                        probe = subprocess.run(["bash", "-n", tf_path], capture_output=True, text=True)
                        Path(tf_path).unlink(missing_ok=True)
                        if probe.returncode != 0:
                            errs.append(f"第 {i} 块：{probe.stderr.strip() or '语法错误'}")
                else:
                    checked = False
                    notes.append(f"bash {len(bodies)} 块（bash 不可用，跳过）")
            elif lang == "python":
                for i, body in enumerate(bodies, 1):
                    try:
                        ast.parse(body)
                    except SyntaxError as e:
                        errs.append(f"第 {i} 块：{e}")
            elif lang == "javascript":
                if node_bin:
                    for i, body in enumerate(bodies, 1):
                        with tempfile.NamedTemporaryFile("w", suffix=".mjs", delete=False) as tf:
                            tf.write(body)
                            tf_path = tf.name
                        probe = subprocess.run(["node", "--check", tf_path],
                                               capture_output=True, text=True)
                        Path(tf_path).unlink(missing_ok=True)
                        if probe.returncode != 0:
                            first = probe.stderr.strip().splitlines()
                            errs.append(f"第 {i} 块：{first[0] if first else '语法错误'}")
                else:
                    checked = False
                    notes.append(f"javascript {len(bodies)} 块（node 不可用，跳过）")
            if errs:
                fail(f"{doc.relative_to(root)} 内嵌 {lang} 代码块语法错误：" + "；".join(errs))
            elif checked and lang in ("bash", "python", "javascript"):
                notes.append(f"{lang} {len(bodies)} 块")
        if notes:
            doc_pass_notes.append(f"{doc.relative_to(root)}：{', '.join(notes)}")
    if doc_pass_notes:
        ok(f"内嵌代码块语法通过（递归扫描 {len(doc_files)} 份文档）：{'；'.join(doc_pass_notes)}")

    # 12. references/**/*.md 内相对引用存在性（markdown 链接与包内路径，双基准解析防误报）
    md_link_re = re.compile(r"\]\(([^)\s]+)\)")
    if ref_docs:
        missing_refs = []
        for doc in ref_docs:
            doc_text = doc.read_text(encoding="utf-8")
            candidates = set(md_link_re.findall(doc_text)) | set(REF_RE.findall(doc_text))
            for ref in sorted(candidates):
                if ref.startswith(("http://", "https://", "mailto:")):
                    continue
                if not ((doc.parent / ref).exists() or (root / ref).exists()):
                    missing_refs.append(f"{doc.relative_to(root)} → {ref}")
        if missing_refs:
            fail("references 内引用但包内不存在的文件：" + "；".join(missing_refs))
        else:
            ok("references 内引用的文件均存在")

    # 12b. 裸文本 .md 提及（「见 xxx.md」这类无链接记号同样是契约）。
    # 无论有无 references/ 都检查 SKILL.md——「没有细则文件就不查」是静默跳过盲区
    bare_md_re = re.compile(r"(?<![A-Za-z0-9_\-./])([\w\-]+(?:/[\w\-]+)*\.md)(?![A-Za-z0-9_\-])")
    missing_bare = set()
    for doc in [skill_md] + ref_docs:
        doc_text = re.sub(r"(?:https?|ftp)://\S+", "", doc.read_text(encoding="utf-8"))
        covered = set(REF_RE.findall(doc_text)) | {
            t for t in md_link_re.findall(doc_text) if t.endswith(".md")}
        for token in bare_md_re.findall(doc_text):
            if token in covered:
                continue
            if not ((doc.parent / token).exists() or (root / token).exists()):
                missing_bare.add(f"{doc.relative_to(root)} 提及 {token}")
    if missing_bare:
        fail("正文/细则提及但包内不存在的 .md 文件：" + "；".join(sorted(missing_bare)))
    else:
        ok("裸文本提及的 .md 文件均存在")

    # 13. 可选：联动触发冒烟评测（存在结构性失败时显式跳过，不静默）
    if args.trigger:
        if failures:
            warn("触发评测跳过：存在结构性失败，先修复再联动（不在坏包上盲跑）")
        else:
            runner = Path(__file__).resolve().parent / "run_trigger_eval.py"
            if not runner.exists():
                warn("触发评测跳过：找不到同级 run_trigger_eval.py")
            else:
                print()
                result = subprocess.run([sys.executable, str(runner), str(root)],
                                        capture_output=True, text=True)
                print(result.stdout.strip())
                if result.returncode != 0:
                    err_lines = [ln for ln in (result.stderr or "").strip().splitlines() if ln.strip()]
                    detail = err_lines[-1] if err_lines else f"exit code {result.returncode}"
                    fail(f"触发冒烟评测未通过（评测器 stderr 末行：{detail}）")

    print()
    if failures:
        print(f"结论：未通过（失败 {len(failures)} 项，警告 {len(warnings)} 项）")
        sys.exit(1)
    print(f"结论：通过（警告 {len(warnings)} 项）")
    sys.exit(0)


if __name__ == "__main__":
    main()
