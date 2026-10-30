#!/usr/bin/env python3
"""打包技能目录为压缩包（默认 zip 格式，扩展名 .skill）。

打包前默认先跑同级 validate_skill.py 校验（--no-validate 跳过）；
排除 .git、__pycache__、node_modules、.venv 与编译缓存/临时文件。
--manifest/--include：按原包清单锁定交付面（工作目录混入验证产物时用）。

布局约定（对应两类真实交付场景）：
- 默认：文件嵌套在 <name>/ 目录下，产出 <name>-v<version>.skill；
- --flat：文件直接放压缩包根（SkillHub 等扁平布局的存量包用），需配 --format zip；
- --out-name：自定义输出文件名，用于优化交付时保持原包命名（如 constructivistppt-3.1.0.zip）。

用法：python3 package_skill.py <技能目录> [--out <输出目录>] [--no-validate]
                 [--format skill|zip] [--flat] [--out-name <文件名>]
                 [--manifest <清单.zip|txt>] [--include <相对路径>]…
退出码：0 成功；1 失败。
"""

import argparse
import re
import subprocess
import sys
import time
import zipfile
from pathlib import Path

try:
    import yaml
except ImportError:
    yaml = None

EXCLUDE_DIRS = {".git", "__pycache__", "node_modules", ".venv"}
EXCLUDE_SUFFIXES = {".pyc", ".pyo", ".swp", ".DS_Store"}


def read_name_version(skill_md):
    text = skill_md.read_text(encoding="utf-8")
    m = re.match(r"^---\n(.*?)\n---", text, re.DOTALL)
    name, version = "skill", "0.0.0"
    if m:
        if yaml is not None:
            fm = yaml.safe_load(m.group(1))
            if isinstance(fm, dict):
                name = str(fm.get("name", name))
                metadata = fm.get("metadata")
                if isinstance(metadata, dict):
                    version = str(metadata.get("version") or version)
    return name, version


def main():
    parser = argparse.ArgumentParser(description="打包技能目录为 .skill/.zip")
    parser.add_argument("skill_dir", help="技能目录")
    parser.add_argument("--out", type=Path, help="输出目录（默认技能目录的父目录）")
    parser.add_argument("--no-validate", action="store_true", help="跳过打包前校验")
    parser.add_argument("--format", choices=["skill", "zip"], default="skill",
                        help="输出格式（默认 skill，即 <name>-v<version>.skill；zip 产同名 .zip）")
    parser.add_argument("--flat", action="store_true",
                        help="压缩包内文件直接放根（扁平布局）；默认嵌套在 <name>/ 下")
    parser.add_argument("--out-name", help="自定义输出文件名（如 constructivistppt-3.1.0.zip）")
    parser.add_argument("--manifest", help="允许打包的文件清单（zip=取其文件列表，或每行一个相对路径的 txt）。"
                        "工作目录里混有验证产物时用它锁定交付面与原包一致")
    parser.add_argument("--include", action="append", default=[],
                        help="--manifest 模式下额外纳入的相对路径，可多次")
    args = parser.parse_args()

    root = Path(args.skill_dir).resolve()
    if not (root / "SKILL.md").is_file():
        print(f"[失败] 缺少 SKILL.md：{root}")
        sys.exit(1)

    manifest = None
    if args.manifest:
        mpath = Path(args.manifest)
        if mpath.suffix == ".zip":
            with zipfile.ZipFile(mpath) as mz:
                manifest = {n for n in mz.namelist() if not n.endswith("/")}
        else:
            manifest = {ln.strip() for ln in mpath.read_text(encoding="utf-8").splitlines()
                        if ln.strip() and not ln.startswith("#")}
        manifest |= set(args.include)
        root_name = root.name
        manifest = {n.removeprefix(f"{root_name}/") for n in manifest}

    if not args.no_validate:
        validator = Path(__file__).resolve().parent / "validate_skill.py"
        if validator.exists():
            result = subprocess.run([sys.executable, str(validator), str(root)],
                                    capture_output=True, text=True)
            print(result.stdout.strip())
            if result.returncode != 0:
                print("[失败] 校验未通过，取消打包（可用 --no-validate 强制）")
                sys.exit(1)

    name, version = read_name_version(root / "SKILL.md")
    out_dir = (args.out.resolve() if args.out else root.parent)
    if out_dir.exists() and not out_dir.is_dir():
        print(f"[失败] --out 指向的不是目录：{out_dir}")
        sys.exit(1)
    out_dir.mkdir(parents=True, exist_ok=True)
    if args.out_name:
        archive = out_dir / args.out_name
    else:
        archive = out_dir / f"{name}-v{version}.{args.format}"
    if args.flat:
        if args.format != "zip":
            print("[失败] --flat 仅用于 --format zip（.skill 交付保持 <name>/ 嵌套布局）")
            sys.exit(1)
        prefix = ""
    else:
        prefix = f"{name}/"

    # 清单漂移检查必须在写盘之前——写完再查失败会留下残缺压缩包（二轮深审 L2 实录）
    if manifest is not None:
        packed = {str(p.relative_to(root)) for p in root.rglob("*")
                  if p.is_file() and not any(part in EXCLUDE_DIRS for part in p.parts)}
        missing = sorted(m for m in manifest if m not in packed)
        if missing:
            print(f"[失败] 清单里有但目录中不存在的文件（清单漂移）：{', '.join(missing[:10])}")
            sys.exit(1)

    count = 0
    with zipfile.ZipFile(archive, "w", zipfile.ZIP_DEFLATED) as zf:
        for path in sorted(root.rglob("*")):
            if path.is_dir():
                continue
            if any(part in EXCLUDE_DIRS for part in path.parts):
                continue
            if path.suffix in EXCLUDE_SUFFIXES:
                continue
            rel = str(path.relative_to(root))
            if manifest is not None and rel not in manifest:
                continue
            # zip 格式不支持 1980 前的时间戳（存量包里偶见 mtime=0 的文件），下限钳制；
            # 必须用 gmtime——localtime 在 UTC 负偏移时区会把 1980-01-01 UTC 折回 1979，仍然崩溃
            mtime = path.stat().st_mtime
            zip_info = zipfile.ZipInfo(prefix + rel,
                                       date_time=time.gmtime(max(mtime, 315532800))[:6])
            zip_info.compress_type = zipfile.ZIP_DEFLATED
            zip_info.external_attr = 0o644 << 16
            with path.open("rb") as f:
                zf.writestr(zip_info, f.read())
            count += 1
    print(f"[通过] 已打包 {count} 个文件 → {archive}（{archive.stat().st_size} 字节）")
    sys.exit(0)


if __name__ == "__main__":
    main()
