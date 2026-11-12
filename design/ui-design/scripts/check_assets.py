#!/usr/bin/env python3
"""Asset and package consistency gate for the ui-design skill.

Checks what a structural validator cannot: every index entry resolves to a file,
every component has the five-file contract, no source-site URL or absolute
workspace path leaks, and the three version sources agree.

Usage:
    python3 -I scripts/check_assets.py
    python3 -I scripts/check_assets.py --json
"""
import argparse
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ERRORS = []
WARNINGS = []


def error(message):
    ERRORS.append(message)


def warn(message):
    WARNINGS.append(message)


def load_json(path, label):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        error("%s missing: %s" % (label, path))
    except json.JSONDecodeError as exc:
        error("%s invalid JSON: %s (%s)" % (label, path, exc))
    return None


def check_version():
    skill = ROOT / "SKILL.md"
    if not skill.exists():
        error("SKILL.md missing")
        return
    text = skill.read_text(encoding="utf-8")
    match = re.search(r'^\s*version:\s*"([^"]+)"', text, re.M)
    if not match:
        try:
            meta = json.loads((ROOT / "_meta.json").read_text(encoding="utf-8"))
            version = meta.get("version")
        except Exception:
            error("version not found in SKILL.md frontmatter or _meta.json")
            return
    else:
        version = match.group(1)

    meta_path = ROOT / "_meta.json"
    if meta_path.exists():
        meta = load_json(meta_path, "_meta.json")
        if meta and str(meta.get("version")) != version:
            error("version mismatch: SKILL.md %s vs _meta.json %s" % (version, meta.get("version")))
    else:
        warn("_meta.json missing (version single source)")

    self_check = ROOT / "SELF-CHECK.md"
    if self_check.exists():
        head = "\n".join(self_check.read_text(encoding="utf-8").splitlines()[:4])
        found = re.search(r"ui-design\s+([0-9]+\.[0-9]+\.[0-9]+)", head)
        if found and found.group(1) != version:
            error("version mismatch: SELF-CHECK.md %s vs SKILL.md %s" % (found.group(1), version))
        elif not found:
            warn("SELF-CHECK.md has no version in its first 4 lines")
    else:
        warn("SELF-CHECK.md missing")

    changelog = ROOT / "CHANGELOG.md"
    if changelog.exists():
        first = changelog.read_text(encoding="utf-8").splitlines()[:40]
        found = None
        for line in first:
            match = re.match(r"^##+\s*\[?([0-9]+\.[0-9]+\.[0-9]+)\]?", line.strip())
            if match:
                found = match.group(1)
                break
        if found and found != version:
            error("version mismatch: CHANGELOG %s vs SKILL.md %s" % (found, version))
        elif not found:
            warn("CHANGELOG has no semver heading in the first 40 lines")

    desc_match = re.search(r"^description:\s*>-?\s*\n((?:\s{2,}.*\n)+)", text, re.M)
    if desc_match:
        description = re.sub(r"\s+", " ", desc_match.group(1)).strip()
        if len(description) > 1024:
            error("description is %d chars (max 1024)" % len(description))
        if "<" in description or ">" in description:
            error("description contains angle brackets")


def check_patterns():
    folder = ROOT / "assets" / "patterns"
    data = load_json(folder / "archetypes.json", "archetypes.json")
    if not data:
        return
    archetypes = data.get("archetypes", [])
    if len(archetypes) != 14:
        error("archetypes.json has %d records (expected 14)" % len(archetypes))
    ids = [item.get("id") for item in archetypes]
    if len(set(ids)) != len(ids):
        error("archetypes.json has duplicate IDs")
    consolidated = folder / "patterns.md"
    if consolidated.exists():
        text = consolidated.read_text(encoding="utf-8", errors="replace")
        for aid in ids:
            if ("<!-- ARCH:%s -->" % aid) not in text:
                error("patterns.md missing marker for %s" % aid)
        if len(re.findall(r"<!-- ARCH:[\w-]+ -->", text)) != len(ids):
            error("patterns.md marker count does not match archetypes.json")
        for aid in ids:
            if not data or not next((a for a in archetypes if a.get("id") == aid), {}).get("n"):
                error("archetype %s has no sample size" % aid)
        return
    for item in archetypes:
        if "slugs" in item:
            error("archetype %s still contains slugs" % item.get("id"))
        card = folder / (str(item.get("id")) + ".md")
        if not card.exists():
            error("archetype card missing: %s" % card.name)
        if not item.get("n"):
            error("archetype %s has no sample size" % item.get("id"))
    card_ids = {card.stem for card in folder.glob("arch-*.md")}
    for orphan in sorted(card_ids - set(ids)):
        error("archetype card %s has no record in archetypes.json" % orphan)


def check_brands():
    consolidated = ROOT / "assets" / "brands.json"
    if consolidated.exists():
        data = load_json(consolidated, "brands.json")
        if data is None:
            return
        rows = data.get("brands", [])
        if len(rows) != 84:
            error("brands.json has %d entries (expected 84)" % len(rows))
        seen = set()
        for entry in rows:
            brand = entry.get("brand")
            if not brand:
                error("brand entry without brand key")
                continue
            if brand in seen:
                error("duplicate brand: %s" % brand)
            seen.add(brand)
            if not entry.get("content"):
                error("brand %s has empty content" % brand)
            if entry.get("color_tokens", 0) <= 0:
                warn("brand %s has no hex tokens" % brand)
        return
    folder = ROOT / "assets" / "brands"
    data = load_json(folder / "index.json", "brands/index.json")
    if data is None:
        return
    if len(data) != 84:
        error("brand index has %d entries (expected 84)" % len(data))
    seen = set()
    for entry in data:
        brand = entry.get("brand")
        if not brand:
            error("brand entry without brand key")
            continue
        if brand in seen:
            error("duplicate brand: %s" % brand)
        seen.add(brand)
        if not (folder / brand / "DESIGN.md").exists():
            error("brand file missing: %s/DESIGN.md" % brand)
        if entry.get("color_tokens", 0) <= 0:
            warn("brand %s has no hex tokens" % brand)
    disk = {path.name for path in folder.iterdir() if (path / "DESIGN.md").exists()}
    for orphan in sorted(disk - seen):
        error("brand directory %s has no entry in brands/index.json" % orphan)


def check_motion():
    folder = ROOT / "assets" / "motion"
    index = load_json(folder / "index.json", "motion/index.json")
    if index is None:
        return
    for key, expected in (
        ("kits", 12), ("components", 12), ("merged", 5), ("prompts", 10),
        ("keyframes", 24), ("snippets", 8),
    ):
        items = index.get(key, [])
        if len(items) != expected:
            error("motion index %s has %d entries (expected %d)" % (key, len(items), expected))
        for item in items:
            rel = item.get("path")
            if not rel:
                error("motion index %s entry %r has no path" % (key, item.get("id")))
            elif not (ROOT / rel.split("#", 1)[0]).exists():
                error("motion index %s entry %r points to missing %s" % (key, item.get("id"), rel))

    indexed = {item.get("id") for item in index.get("components", []) + index.get("merged", [])}
    on_disk = set()
    component_dirs = list((folder / "code" / "components").iterdir())
    merged_dirs = list((folder / "code" / "merged").iterdir())
    for path in component_dirs + merged_dirs:
        if not path.is_dir():
            continue
        on_disk.add(path.name)
        if path.name not in indexed:
            error("%s exists on disk but is absent from motion/index.json" % path.name)
        for name in ("index.html", "component.css", "component.js", "README.md", "meta.json"):
            if not (path / name).exists():
                error("%s missing %s" % (path.name, name))
        meta_path = path / "meta.json"
        if not meta_path.exists():
            continue
        meta = load_json(meta_path, "%s/meta.json" % path.name)
        if not meta:
            continue
        if meta.get("family") not in {"F%d" % i for i in range(1, 15)}:
            error("%s has invalid family %r" % (path.name, meta.get("family")))
        if "sources" in meta:
            for source in meta["sources"]:
                if "path" in source:
                    error("%s leaks sources[].path" % path.name)
        if "engines" in meta:
            for engine in meta["engines"]:
                if "path" in engine:
                    error("%s leaks engines[].path" % path.name)
        motion = meta.get("motion") or {}
        for key in ("trigger", "duration_ms", "easing", "states", "fallback", "properties", "verified"):
            if key not in motion:
                error("%s meta.motion missing %s" % (path.name, key))
        if motion.get("verified") is not True:
            error("%s meta.motion.verified is not true" % path.name)
        js = (path / "component.js").read_text(encoding="utf-8", errors="replace")
        if "mount" not in js:
            error("%s component.js has no mount" % path.name)
        if "prefers-reduced-motion" not in js and "prefers-reduced-motion" not in (
            path / "component.css"
        ).read_text(encoding="utf-8", errors="replace"):
            error("%s has no prefers-reduced-motion path" % path.name)
        readme = (path / "README.md").read_text(encoding="utf-8", errors="replace")
        if "verify_motion.mjs" not in readme:
            warn("%s README does not point at verify_motion.mjs" % path.name)

    for missing in sorted(indexed - on_disk):
        error("motion index entry %r has no directory on disk" % missing)

    prompts_file = folder / "prompts.md"
    if prompts_file.exists():
        text = prompts_file.read_text(encoding="utf-8", errors="replace")
        sections = re.findall(r"^##\s+(F(?:[1-9]|1[0-4])-[^\n]+)$", text, re.M)
        if len(sections) != 10:
            error("prompts.md has %d sections (expected 10)" % len(sections))
    else:
        prompts = list((folder / "prompts").glob("*.md"))
        if len(prompts) != 10:
            error("prompts has %d files (expected 10)" % len(prompts))
        for prompt in prompts:
            if not re.match(r"^F(?:[1-9]|1[0-4])-", prompt.name):
                error("prompt not family-prefixed: %s" % prompt.name)

    keyframes = folder / "code" / "css" / "keyframes.css"
    if not keyframes.exists():
        error("keyframes.css missing")
    else:
        count = len(re.findall(r"@keyframes\s+[\w-]+\s*\{", keyframes.read_text(encoding="utf-8")))
        if count != 24:
            error("keyframes.css has %d blocks (expected 24)" % count)

    snippets_file = folder / "code" / "snippets.js"
    if snippets_file.exists():
        text = snippets_file.read_text(encoding="utf-8", errors="replace")
        markers = re.findall(r"/\* ==== ([\w-]+) ==== \*/", text)
        if len(markers) != 8:
            error("snippets.js has %d blocks (expected 8)" % len(markers))
    else:
        snippets = list((folder / "code" / "snippets").glob("*.js"))
        if len(snippets) != 8:
            error("snippets has %d files (expected 8)" % len(snippets))


def _viewer_count(path):
    text = path.read_text(encoding="utf-8", errors="replace")
    m = re.search(r'<script id="demo-data" type="application/json">(.*?)</script>', text, re.S)
    if not m:
        return None
    try:
        return len(json.loads(m.group(1)).get("items", []))
    except Exception:
        return None


def check_site_assets():
    tech_viewer = ROOT / "assets" / "site-techniques.html"
    if tech_viewer.exists():
        n = _viewer_count(tech_viewer)
        if n != 28:
            error("site-techniques.html has %r demos (expected 28)" % n)
    else:
        techniques = list((ROOT / "assets" / "site-techniques").glob("*.html"))
        if len(techniques) != 28:
            error("site-techniques has %d html files (expected 28)" % len(techniques))
    studies_viewer = ROOT / "assets" / "site-studies.html"
    if studies_viewer.exists():
        n = _viewer_count(studies_viewer)
        if n != 8:
            error("site-studies.html has %r demos (expected 8)" % n)
    else:
        studies = list((ROOT / "assets" / "site-studies").glob("*.html"))
        if len(studies) != 8:
            error("site-studies has %d html files (expected 8)" % len(studies))
    golden = list((ROOT / "assets" / "golden").glob("*.html"))
    if len(golden) != 3:
        error("golden has %d html files (expected 3)" % len(golden))
    if not (ROOT / "assets" / "golden" / "studio-desktop.png").exists():
        warn("studio-desktop.png not rendered yet")


def check_text():
    # Assemble the needles so this checker does not flag its own source.
    opl_needle = "onepage" + "love.com"
    home_needle = "/home/" + "huayu/"
    needles = (opl_needle, home_needle)
    runtime_suffixes = {".html", ".js", ".mjs", ".css", ".py"}
    allowed_hosts = {"www.w3.org", "localhost", "127.0.0.1"}
    external_any = re.compile(r"https?://([^/\s\"'<>)]+)", re.I)
    for path in sorted(ROOT.rglob("*")):
        if not path.is_file() or path.suffix.lower() not in {".md", ".html", ".js", ".mjs", ".css", ".py", ".json"}:
            continue
        if "reports" in path.parts:
            continue
        text = path.read_text(encoding="utf-8", errors="replace")
        for needle in needles:
            if needle in text:
                if needle == opl_needle and path.name == "ATTRIBUTION.md":
                    continue
                error("%s contains forbidden string %r" % (path.relative_to(ROOT), needle))
        if path.suffix.lower() in runtime_suffixes:
            for match in external_any.finditer(text):
                host = match.group(1).split(":")[0]
                if host not in allowed_hosts:
                    error("%s has runtime external ref %s" % (path.relative_to(ROOT), host))


def check_file_budget():
    count = sum(1 for p in ROOT.rglob("*") if p.is_file())
    if count > 200:
        error("skill has %d files (budget 200)" % count)


def check_evals():
    cases = [p for p in (ROOT / "evals" / "cases").iterdir() if p.is_dir()]
    if len(cases) != 8:
        error("evals/cases has %d dirs (expected 8)" % len(cases))
    motion = [p for p in (ROOT / "evals" / "motion").iterdir() if p.is_dir()]
    if len(motion) != 6:
        error("evals/motion has %d dirs (expected 6)" % len(motion))
    for path in motion:
        if not (path / "expected.json").exists():
            error("%s missing expected.json" % path.name)


def main():
    parser = argparse.ArgumentParser(description="Asset consistency gate")
    parser.add_argument("--json", action="store_true", help="JSON output")
    args = parser.parse_args()

    check_version()
    check_patterns()
    check_brands()
    check_motion()
    check_site_assets()
    check_text()
    check_evals()
    check_file_budget()

    report = {"errors": ERRORS, "warnings": WARNINGS, "ok": not ERRORS}
    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        for item in ERRORS:
            print("ERROR %s" % item)
        for item in WARNINGS:
            print("WARN  %s" % item)
        print("check_assets: %d errors, %d warnings" % (len(ERRORS), len(WARNINGS)))
    sys.exit(0 if not ERRORS else 1)


if __name__ == "__main__":
    main()