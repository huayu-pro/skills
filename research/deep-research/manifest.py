#!/usr/bin/env python3
"""重新生成 MANIFEST.txt —— 包内每个文件的 SHA-256 前 16 位与行数。

用法：
    python3 manifest.py [--check]

漂移的根源是手写清单：改了任何一个文件，清单里的哈希与行数就过期，而没有人会
在交付前逐行核对。所以清单由本脚本生成，`--check` 供回归测试与交付前自检比对。

退出码：0 一致（或已重写）；1 `--check` 发现不一致；2 参数错误。
仅标准库；无网络。
"""

from __future__ import annotations

import argparse
import hashlib
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
SKILL_DIR = os.path.dirname(HERE)

# 清单自身与这些产物不进清单：前者自指，后者是运行时/打包噪声。
EXCLUDED_FILES = {"MANIFEST.txt"}
EXCLUDED_SUFFIX = (".pyc",)
EXCLUDED_DIRS = {"__pycache__", ".git", ".venv", "node_modules"}


def collect(root: str) -> list[tuple[str, int, str]]:
    """返回 [(相对路径, 行数, sha256 前 16 位)]，按路径排序。"""
    out = []
    for base, dirs, files in os.walk(root):
        dirs[:] = sorted(d for d in dirs if d not in EXCLUDED_DIRS)
        for name in sorted(files):
            if name in EXCLUDED_FILES or name.endswith(EXCLUDED_SUFFIX):
                continue
            path = os.path.join(base, name)
            rel = os.path.relpath(path, root).replace(os.sep, "/")
            try:
                with open(path, "rb") as handle:
                    blob = handle.read()
            except OSError:
                continue
            digest = hashlib.sha256(blob).hexdigest()[:16]
            try:
                lines = blob.decode("utf-8").count("\n") + (0 if blob.endswith(b"\n") or not blob else 1)
            except UnicodeDecodeError:
                lines = 0
            out.append((rel, lines, digest))
    return sorted(out)


def render(root: str, entries: list[tuple[str, int, str]]) -> str:
    version = read_version(root)
    lines = [f"deep-research {version} — 文件清单（SHA-256 前 16 位）", ""]
    for rel, count, digest in entries:
        lines.append(f"{digest}    {count:>4}行  {rel}")
    lines += ["", f"共 {len(entries)} 个文件（不含本清单自身）",
              "由 scripts/manifest.py 生成；改包后重跑它，不要手改本文件。", ""]
    return "\n".join(lines)


def read_version(root: str) -> str:
    """从 SKILL.md 的 frontmatter 取版本，清单标题就不必再手改。"""
    path = os.path.join(root, "SKILL.md")
    try:
        with open(path, encoding="utf-8") as handle:
            for line in handle:
                if line.startswith("  version:"):
                    return line.split(":", 1)[1].strip().strip('"')
                if line.strip() and not line.startswith(("---", "name:", "description:", "license:",
                                                        "metadata:", "  ")):
                    break
    except OSError:
        pass
    return "?"


def main(argv=None) -> int:
    p = argparse.ArgumentParser(prog="manifest.py", description=__doc__.splitlines()[0])
    p.add_argument("--check", action="store_true",
                   help="只比对：清单与包内实际内容不一致则退出 1（不写文件）")
    args = p.parse_args(argv)

    entries = collect(SKILL_DIR)
    wanted = render(SKILL_DIR, entries)
    target = os.path.join(SKILL_DIR, "MANIFEST.txt")
    current = ""
    if os.path.isfile(target):
        with open(target, encoding="utf-8") as handle:
            current = handle.read()
    if args.check:
        if current.strip() == wanted.strip():
            print(f"MANIFEST.txt 与包内 {len(entries)} 个文件一致")
            return 0
        print("MANIFEST.txt 已过期；重跑 `python3 scripts/manifest.py`", file=sys.stderr)
        for line in _diff(current, wanted):
            print(f"  {line}", file=sys.stderr)
        return 1
    with open(target, "w", encoding="utf-8") as handle:
        handle.write(wanted)
    print(f"MANIFEST.txt 已重写：{len(entries)} 个文件")
    return 0


def _diff(current: str, wanted: str) -> list[str]:
    old = {ln.split()[-1]: ln for ln in current.splitlines() if ln.endswith(tuple("md py json txt"))}
    new = {ln.split()[-1]: ln for ln in wanted.splitlines() if ln and not ln.startswith(("deep-research",
                                                                                        "由 scripts", "共 "))}
    out = []
    for key in sorted(set(old) | set(new)):
        if key not in old:
            out.append(f"新增 {key}")
        elif key not in new:
            out.append(f"已移除 {key}")
        elif old[key].split()[:2] != new[key].split()[:2]:
            out.append(f"已变更 {key}")
    return out[:20]


if __name__ == "__main__":
    sys.exit(main())
