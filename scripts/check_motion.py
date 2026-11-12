#!/usr/bin/env python3
"""Deterministic motion-pattern scanner for the ui-design skill.

This is the static layer of the three-layer motion acceptance:
    static scan  ->  runtime probe  ->  human review

It flags patterns that are almost always defects, not taste. It never claims a
page "has good motion"; it only proves the absence of known bad patterns.

Usage:
    python3 -I scripts/check_motion.py page.html --json
    python3 -I scripts/check_motion.py evals/motion --expect
    python3 -I scripts/check_motion.py --self-test
"""
import argparse
import json
import re
import sys
import tempfile
from pathlib import Path

LAYOUT_PROPS = (
    "width", "height", "top", "left", "right", "bottom",
    "margin", "margin-top", "margin-right", "margin-bottom", "margin-left",
    "padding", "padding-top", "padding-right", "padding-bottom", "padding-left",
)

ENTRANCE_RE = re.compile(
    r'class=["\'][^"\']*\b(?:fade-in-up|fadeInUp|reveal|animate-in)\b[^"\']*["\']',
    re.I,
)

KF_RE = re.compile(r"@(?:-webkit-)?keyframes\s+([A-Za-z_][\w-]*)\s*\{", re.I)
REDUCE_RE = re.compile(r"@media[^{]*prefers-reduced-motion[^{]*\{", re.I)
POINTER_FINE_RE = re.compile(r"@media[^{]*pointer\s*:\s*fine[^{]*\{", re.I)
IMPORT_RE = re.compile(r"@import\s+(?:url\()?[\"']([^\"']+\.css[^\"']*)", re.I)


def media_bodies(text, pattern):
    out = []
    pos = 0
    while True:
        match = pattern.search(text, pos)
        if not match:
            break
        start = match.end() - 1
        depth = 0
        index = start
        while index < len(text):
            char = text[index]
            if char == "{":
                depth += 1
            elif char == "}":
                depth -= 1
                if depth == 0:
                    index += 1
                    break
            index += 1
        out.append(text[start + 1:index - 1])
        pos = index
    return out


def pointer_fine_blocks(text):
    return media_bodies(text, POINTER_FINE_RE)


def reduce_blocks(text):
    """Yield the body of every @media (prefers-reduced-motion) block."""
    out = []
    pos = 0
    while True:
        match = REDUCE_RE.search(text, pos)
        if not match:
            break
        start = match.end() - 1
        depth = 0
        index = start
        while index < len(text):
            char = text[index]
            if char == "{":
                depth += 1
            elif char == "}":
                depth -= 1
                if depth == 0:
                    index += 1
                    break
            index += 1
        out.append(text[start + 1:index - 1])
        pos = index
    return out


def has_reduce_reset(text):
    """True only when a reduce block actually disables motion."""
    for body in reduce_blocks(text):
        body = re.sub(r"/\*.*?\*/", "", body, flags=re.S)
        if re.search(r"animation\s*:\s*(?:none|0m?s)\b", body, re.I):
            return True
        if re.search(r"transition\s*:\s*(?:none|0m?s)\b", body, re.I):
            return True
        if re.search(r"animation-play-state\s*:\s*paused", body, re.I):
            return True
        if re.search(r"(?:animation|transition)-duration\s*:\s*(?:0|\.01m?s)\b", body, re.I):
            return True
    return False


def read(path):
    try:
        return path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return ""


def line_of(text, offset):
    return text.count("\n", 0, max(0, offset)) + 1


def finding(rule, severity, path, text, offset, message, fix):
    return {
        "id": rule,
        "severity": severity,
        "file": str(path),
        "line": line_of(text, offset),
        "message": message,
        "fix": fix,
    }


def keyframe_blocks(text):
    out = []
    pos = 0
    while True:
        match = KF_RE.search(text, pos)
        if not match:
            break
        start = match.end() - 1
        depth = 0
        index = start
        while index < len(text):
            char = text[index]
            if char == "{":
                depth += 1
            elif char == "}":
                depth -= 1
                if depth == 0:
                    index += 1
                    break
            index += 1
        out.append((match.group(1), text[start + 1:index - 1], match.start()))
        pos = index
    return out


def check_m001(path, text):
    out = []
    for name, body, offset in keyframe_blocks(text):
        for match in re.finditer(
            r"(?:^|[;{])\s*(?:width|height|top|left|right|bottom|margin(?:-[a-z]+)?|padding(?:-[a-z]+)?)\s*:",
            body,
            re.I,
        ):
            out.append(finding(
                "M-001", "P1", path, text, offset + match.start(),
                "keyframes 动画布局属性（%s）" % name,
                "改 transform/opacity；必须动尺寸时用 scale/clip-path，并写代价",
            ))
            break
    for match in re.finditer(r"transition(?:-property)?\s*:\s*([^;}]+)", text, re.I):
        value = match.group(1)
        for prop in LAYOUT_PROPS:
            if re.search(r"\b" + re.escape(prop) + r"\b", value, re.I):
                out.append(finding(
                    "M-001", "P1", path, text, match.start(),
                    "transition 包含布局属性（%s）" % prop,
                    "改成 transform/opacity；不要过渡 width/height/top/left",
                ))
                break
    # WAAPI keyframes are an animation channel; direct style writes are left to
    # manual review because static positioning (left/top at creation) is common.
    for match in re.finditer(
        r"\.animate\s*\(\s*\[[^\]]*(?:width|height|top|left|right|bottom|margin|padding)",
        text,
        re.I | re.S,
    ):
        out.append(finding(
            "M-001", "P1", path, text, match.start(),
            "WAAPI 动画布局属性",
            "改 transform/opacity",
        ))
    return out


def check_m002(path, text):
    has_motion = re.search(r"@keyframes|animation\s*:|transition\s*:|requestAnimationFrame", text, re.I)
    if not has_motion:
        return []
    if path.suffix.lower() == ".js" and re.search(r"prefers-reduced-motion", text, re.I):
        return []
    if has_reduce_reset(text):
        return []
    return [finding(
        "M-002", "P1", path, text, 0,
        "有动画但缺少真正禁用动画的 prefers-reduced-motion 块",
        "加 @media (prefers-reduced-motion: reduce)，并在块内写 animation:none / transition:none（注释不算）",
    )]


def check_m003(path, text):
    out = []
    for match in re.finditer(r"<video\b[^>]*>", text, re.I):
        tag = match.group(0)
        if re.search(r"\bautoplay\b", tag, re.I) and not re.search(r"\bmuted\b", tag, re.I):
            out.append(finding(
                "M-003", "P1", path, text, match.start(),
                "video autoplay 但没有 muted",
                "加 muted playsinline，或改为用户手势后播放",
            ))
    for match in re.finditer(r"<audio\b[^>]*\bautoplay\b[^>]*>", text, re.I):
        out.append(finding(
            "M-003", "P1", path, text, match.start(),
            "audio autoplay",
            "移除 autoplay；用用户手势解锁 AudioContext",
        ))
    return out


def check_m004(path, text):
    count = len(ENTRANCE_RE.findall(text))
    if count < 3:
        return []
    match = ENTRANCE_RE.search(text)
    return [finding(
        "M-004", "P1", path, text, match.start() if match else 0,
        "同页 %d 个元素使用 reveal/fade-in-up 入场" % count,
        "只保留一个注意瞬间；其余元素直接出现或只做一次 IO reveal",
    )]


def check_m005(path, text):
    match = re.search(r"transition\s*:\s*all\b", text, re.I)
    if not match:
        return []
    return [finding(
        "M-005", "P2", path, text, match.start(),
        "transition: all",
        "明确列 transform, opacity；不要过渡所有属性",
    )]


def check_m006(path, text):
    out = []
    for match in re.finditer(r"([^{}]+)\{([^{}]*scroll-behavior\s*:\s*smooth[^{}]*)\}", text, re.I | re.S):
        selector = match.group(1).strip().splitlines()[-1].strip()
        if re.search(r"(?:^|[\s,>])(?:html|body|\*)(?:$|[\s,>])", selector, re.I):
            out.append(finding(
                "M-006", "P2", path, text, match.start(),
                "全局 scroll-behavior:smooth（%s）" % selector,
                "只给锚点链接用；长页/横向叙事不要全局平滑滚动",
            ))
    return out


def check_m007(path, text):
    match = re.search(r"animation[^;{}]*\binfinite\b", text, re.I)
    if not match:
        return []
    if re.search(r"animation-play-state\s*:\s*paused|data-pause|is-paused|visibilitychange", text, re.I):
        return []
    return [finding(
        "M-007", "P2", path, text, match.start(),
        "无限循环动画且未见暂停/hidden 处理",
        "提供 hover 减速/暂停或页面隐藏暂停；reduced-motion 停止",
    )]


def check_m008(path, text):
    out = []
    for name, body, offset in keyframe_blocks(text):
        if re.search(r"box-shadow\s*:|filter\s*:\s*blur", body, re.I):
            out.append(finding(
                "M-008", "P2", path, text, offset,
                "keyframes 动画 box-shadow/filter:blur（%s）" % name,
                "改用 opacity/transform 或预分层；长循环不要每帧绘制",
            ))
    return out


def check_m009(path, text):
    cursor = re.search(r"cursor\s*:\s*none", text, re.I)
    if not cursor:
        return []
    for body in pointer_fine_blocks(text):
        if re.search(r"cursor\s*:\s*none", body, re.I):
            return []
    return [finding(
        "M-009", "P2", path, text, cursor.start(),
        "cursor:none 没有 pointer:fine 回退",
        "包在 @media (pointer:fine) 里，触屏保留原生光标",
    )]


def check_m010(path, text):
    count = len(re.findall(r"will-change\s*:", text, re.I))
    if count <= 20:
        return []
    return [finding(
        "M-010", "P2", path, text, 0,
        "will-change 出现 %d 次" % count,
        "只在动画期间加，结束移除；常驻会吃显存",
    )]


def check_m011(path, text):
    if not re.search(r"addEventListener\s*\(\s*['\"]wheel", text, re.I):
        return []
    if not re.search(r"preventDefault\s*\(", text):
        return []
    if re.search(r"keydown|keyup|Arrow(Up|Down|Left|Right)", text, re.I):
        return []
    match = re.search(r"addEventListener\s*\(\s*['\"]wheel", text, re.I)
    return [finding(
        "M-011", "P2", path, text, match.start(),
        "wheel + preventDefault 但没有键盘出口",
        "加 Arrow/PageUp/PageDown/Home/End，或不要劫持滚动",
    )]


def check_m012(path, text):
    out = []
    for match in re.finditer(r"([^{}]+)\{([^{}]*)\}", text, re.S):
        selector = match.group(1).strip().splitlines()[-1].strip()
        body = match.group(2)
        if not selector or selector.startswith("@"):
            continue
        if re.search(r"animation\s*:\s*none", body, re.I) and re.search(r"transition\s*:\s*none", body, re.I):
            continue
        if re.search(r"transition\s*:", body, re.I) and re.search(r"animation\s*:", body, re.I):
            out.append(finding(
                "M-012", "P2", path, text, match.start(),
                "同一选择器同时有 transition 与 animation（%s）" % selector[:60],
                "确认两者不争抢同一属性；否则拆成两个元素/状态",
            ))
    return out


CHECKS = [
    check_m001, check_m002, check_m003, check_m004, check_m005, check_m006,
    check_m007, check_m008, check_m009, check_m010, check_m011, check_m012,
]


def scan_file(path):
    findings = []
    scanned = set()

    def run(target):
        key = str(target.resolve())
        if key in scanned:
            return
        scanned.add(key)
        text = read(target)
        for check in CHECKS:
            findings.extend(check(target, text))
        if target.suffix.lower() == ".css":
            for imported in IMPORT_RE.findall(text):
                child = (target.parent / imported.split("?")[0].split("#")[0]).resolve()
                if child.exists():
                    run(child)

    run(path)
    if path.suffix.lower() == ".html":
        html = read(path)
        for href in re.findall(r'<link[^>]+href=["\']([^"\']+\.css[^"\']*)["\']', html, re.I):
            clean = href.split("?")[0].split("#")[0]
            target = (path.parent / clean).resolve()
            if target.exists():
                run(target)
        for src in re.findall(r'<script[^>]+src=["\']([^"\']+\.js[^"\']*)["\']', html, re.I):
            clean = src.split("?")[0].split("#")[0]
            target = (path.parent / clean).resolve()
            if target.exists():
                run(target)

    # Stable dedupe: same rule + file + line + message once.
    seen = set()
    deduped = []
    for item in findings:
        key = (item["id"], item["file"], item["line"], item["message"])
        if key in seen:
            continue
        seen.add(key)
        deduped.append(item)
    deduped.sort(key=lambda item: (item["severity"], item["id"], item["line"]))
    return deduped


def html_files(target):
    path = Path(target)
    if path.is_file():
        return [path]
    return sorted(p for p in path.rglob("*.html") if p.is_file())


def run_scan(target, as_json=False):
    path = Path(target)
    if not path.exists():
        print("target not found: %s" % target, file=sys.stderr)
        return 2
    files = html_files(target)
    if not files:
        print("no html files under: %s" % target, file=sys.stderr)
        return 2
    all_findings = []
    for item_path in files:
        all_findings.extend(scan_file(item_path))
    if as_json:
        print(json.dumps(all_findings, ensure_ascii=False, indent=2))
    else:
        for item in all_findings:
            print("%s %-5s %s:%d  %s" % (
                item["severity"], item["id"], item["file"], item["line"], item["message"]))
        if not all_findings:
            print("no motion findings")
    return 1 if any(item["severity"] in {"P0", "P1"} for item in all_findings) else 0


def run_expect(target):
    root = Path(target)
    if not root.exists() or not root.is_dir():
        print("case directory not found: %s" % target, file=sys.stderr)
        return 2
    cases = sorted(p for p in root.iterdir() if p.is_dir())
    if not cases:
        print("no case dirs under %s" % root)
        return 2
    passed = 0
    for case in cases:
        expected_path = case / "expected.json"
        if not expected_path.exists():
            print("SKIP %s (no expected.json)" % case.name)
            continue
        expected = json.loads(expected_path.read_text(encoding="utf-8"))
        html = next(iter(sorted(case.glob("*.html"))), None)
        if html is None:
            print("FAIL %s (no html)" % case.name)
            continue
        ids = {item["id"] for item in scan_file(html)}
        must = set(expected.get("must", []))
        must_not = set(expected.get("must_not", []))
        missing = sorted(must - ids)
        unexpected = sorted(must_not & ids)
        if not missing and not unexpected:
            passed += 1
            print("PASS %s  findings=%s" % (case.name, ",".join(sorted(ids)) or "-"))
        else:
            print("FAIL %s  missing=%s unexpected=%s actual=%s" % (
                case.name, missing or "-", unexpected or "-", sorted(ids) or "-"))
    print("expect: %d/%d" % (passed, len(cases)))
    return 0 if passed == len(cases) else 1


def self_test():
    fixtures = {
        "M-001": '<style>@keyframes x{to{width:100px}}</style>',
        "M-002": '<style>@keyframes x{to{opacity:0}}</style>',
        "M-003": '<video autoplay src="x.mp4"></video>',
        "M-004": '<div class="reveal"></div><div class="reveal"></div><div class="reveal"></div>',
        "M-005": '<style>.a{transition:all .3s}</style>',
        "M-006": '<style>html{scroll-behavior:smooth}</style>',
        "M-007": '<style>@keyframes x{to{opacity:0}} .a{animation:x 2s infinite}</style>',
        "M-008": '<style>@keyframes x{to{box-shadow:0 0 1px #000}}</style>',
        "M-009": '<style>body{cursor:none}</style>',
        "M-010": "<style>" + "".join(".a%d{will-change:transform}" % i for i in range(21)) + "</style>",
        "M-011": "<script>addEventListener('wheel',e=>{e.preventDefault()})</script>",
        "M-012": "<style>@keyframes x{to{opacity:0}} .a{transition:opacity .3s;animation:x 1s}</style>",
    }
    clean = "<style>@media (prefers-reduced-motion: reduce){*{animation:none}}</style><p>ok</p>"

    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        passed = 0
        total = 0
        for rule, body in fixtures.items():
            total += 1
            path = tmp_path / (rule + ".html")
            path.write_text(body, encoding="utf-8")
            ids = {item["id"] for item in scan_file(path)}
            if rule in ids:
                passed += 1
                print("ok   %s -> %s" % (rule, ",".join(sorted(ids))))
            else:
                print("FAIL %s not detected; got %s" % (rule, sorted(ids) or "-"))
        total += 1
        clean_path = tmp_path / "clean.html"
        clean_path.write_text(clean, encoding="utf-8")
        clean_findings = scan_file(clean_path)
        if not clean_findings:
            passed += 1
            print("ok   clean -> no findings")
        else:
            print("FAIL clean produced %s" % clean_findings)
        print("self-test: %d/%d" % (passed, total))
        return 0 if passed == total else 1


def main():
    parser = argparse.ArgumentParser(description="Static motion-pattern scanner")
    parser.add_argument("target", nargs="?", help="HTML file or directory")
    parser.add_argument("--json", action="store_true", help="JSON output")
    parser.add_argument("--expect", action="store_true",
                        help="run fixtures under target and compare expected.json")
    parser.add_argument("--self-test", action="store_true", help="run built-in red/green tests")
    args = parser.parse_args()

    if args.self_test:
        sys.exit(self_test())
    if not args.target:
        parser.error("target is required unless --self-test")
    if args.expect:
        sys.exit(run_expect(args.target))
    sys.exit(run_scan(args.target, args.json))


if __name__ == "__main__":
    main()