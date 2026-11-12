#!/usr/bin/env python3
"""Build optional self-contained skill distributions from one source tree."""
from __future__ import annotations
import argparse, json, shutil, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
DIST = ROOT / "dist"
CORE = ["SKILL.md", "LICENSE", "NOTICE", "ATTRIBUTION.md", "CHANGELOG.md", "SELF-CHECK.md", "_meta.json",
        "references", "assets", "scripts", "evals", "subskills", "packs"]
SUB = {
  "ui-direction": ["subskills/direction/SKILL.md", "references", "assets/golden", "assets/patterns", "assets/brands.json"],
  "ui-tokens": ["subskills/tokens/SKILL.md", "references", "assets/tokens", "scripts/generate_palette.py", "scripts/check_contrast.py", "scripts/emit_tokens.py"],
  "ui-motion": ["subskills/motion/SKILL.md", "references", "assets/motion", "assets/tokens", "scripts/check_motion.py", "scripts/verify_motion.mjs", "evals/motion"],
  "ui-audit": ["subskills/audit/SKILL.md", "references", "assets/golden", "scripts/audit.py", "scripts/check_motion.py", "scripts/verify_motion.mjs", "evals"],
}

def check() -> int:
    errors = []
    for rel in CORE:
        if not (ROOT / rel).exists(): errors.append("missing core: " + rel)
    for name, items in SUB.items():
        for rel in items:
            if not (ROOT / rel).exists(): errors.append("%s missing %s" % (name, rel))
    core = [p for p in ROOT.rglob("*") if p.is_file() and ".git" not in p.parts and "dist" not in p.parts and "packs" not in p.parts]
    packs = [p for p in (ROOT/"packs").rglob("*") if p.is_file()]
    if len(core) > 190: errors.append("core budget %d > 190" % len(core))
    if len(packs) > 12: errors.append("packs budget %d > 12" % len(packs))
    notice = (ROOT/"NOTICE").read_text(encoding="utf-8", errors="replace")
    for needle in ["naplesblue", "Emil Kowalski", "Lucide", "Edison Li", "XiaoyeCodes", "Remotion", "AGPL"]:
        if needle not in notice: errors.append("NOTICE missing " + needle)
    # links in new docs: only check relative paths that are simple and exist
    for p in list((ROOT/"subskills").rglob("*.md")) + list((ROOT/"packs").rglob("*.md")) + [ROOT/"SKILL.md"]:
        text = p.read_text(encoding="utf-8", errors="replace")
        if "guizang" in text and "AGPL" not in text and p.name not in {"README.md", "SKILL.md"}:
            errors.append("guizang mentioned without license warning: " + str(p.relative_to(ROOT)))
    print(json.dumps({"ok": not errors, "core_files": len(core), "pack_files": len(packs), "errors": errors}, ensure_ascii=False, indent=2))
    return 0 if not errors else 1

def copy(rel: str, dst: Path):
    src = ROOT / rel
    target = dst / Path(rel).name
    if src.is_dir():
        if target.exists(): shutil.rmtree(target)
        shutil.copytree(src, target, ignore=shutil.ignore_patterns(".git", "__pycache__"))
    else:
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, target)

def build(out: Path) -> int:
    if out.exists(): shutil.rmtree(out)
    out.mkdir(parents=True)
    full = out / "ui-design"
    full.mkdir()
    for rel in CORE: copy(rel, full)
    for name, items in SUB.items():
        d = out / name; d.mkdir()
        (d/"SKILL.md").write_text((ROOT/SUB[name][0]).read_text(encoding="utf-8"), encoding="utf-8")
        for rel in items[1:]: copy(rel, d)
        for rel in ["LICENSE","NOTICE","ATTRIBUTION.md"]:
            shutil.copy2(ROOT/rel, d/rel)
        (d/"_meta.json").write_text(json.dumps({"name":name,"version":"5.0.0","parent":"ui-design"},ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print(json.dumps({"out":str(out),"distributions":["ui-design"]+list(SUB)},ensure_ascii=False,indent=2))
    return 0

def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--check", action="store_true")
    ap.add_argument("--out", default=str(DIST))
    a = ap.parse_args()
    if a.check: return check()
    return build(Path(a.out))
if __name__ == "__main__": raise SystemExit(main())
