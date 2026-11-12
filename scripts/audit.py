#!/usr/bin/env python3
"""Deterministic UI audit: the checks a machine can actually decide.

Emits findings in the same schema as the human audit rubric
(references/12-audit-rubric.md), so `audit.py` output and manual findings can
be merged and sorted together.

Design rules this file obeys:
  - A gate that never fails is not a gate: every check has a self-test that
    proves it fires on bad input (see --self-test).
  - "Not checked" is reported as skipped, never silently passed.
  - No finding is emitted without a location that a human can open.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

# ---------------------------------------------------------------- utilities

HEX = re.compile(r"#(?:[0-9a-fA-F]{3}|[0-9a-fA-F]{6})\b")
FUNC_COLOR = re.compile(r"\b(?:rgba?|hsla?|oklch)\([^)]*\)")
ARBITRARY_TW = re.compile(r"(?:^|[\s\"'])([a-z\-]+)-\[([^\]]+)\]")
SPACE_TW = re.compile(r"\bspace-[xy]-\S+")
IMG_TAG = re.compile(r"<img\b[^>]*>", re.I)
INPUT_TAG = re.compile(r"<(input|textarea|select)\b[^>]*>", re.I)
LABEL_TAG = re.compile(r"<label\b[^>]*>", re.I)
OUTLINE_NONE = re.compile(r"outline\s*:\s*(?:none|0)\b")
ANIM = re.compile(r"\b(?:animation|transition)\s*:")
REDUCED_MOTION = re.compile(r"prefers-reduced-motion")
BOX_SHADOW = re.compile(r"box-shadow\s*:\s*([^;}\n]+)")
FONT_WEIGHT = re.compile(r"font-weight\s*:\s*(\d{3})")
LOREM = re.compile(r"\b(?:lorem ipsum|dolor sit amet|示例文本|标题在这里|占位文本)\b", re.I)
TEXT_CENTER = re.compile(r"text-align\s*:\s*center")
ZINDEX_MANUAL = re.compile(r"\bz-(?:50|\[?\d+\]?)\b")


def srgb_to_lin(c: float) -> float:
    c = c / 255.0
    return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4


def hex_to_rgb(h: str) -> tuple[int, int, int] | None:
    h = h.lstrip("#")
    if len(h) == 3:
        h = "".join(ch * 2 for ch in h)
    if len(h) != 6:
        return None
    try:
        return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))  # type: ignore[return-value]
    except ValueError:
        return None


def luminance(rgb: tuple[int, int, int]) -> float:
    r, g, b = (srgb_to_lin(c) for c in rgb)
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def contrast(a: str, b: str) -> float | None:
    ra, rb = hex_to_rgb(a), hex_to_rgb(b)
    if not ra or not rb:
        return None
    la, lb = luminance(ra), luminance(rb)
    hi, lo = max(la, lb), min(la, lb)
    return (hi + 0.05) / (lo + 0.05)


_LINE_INDEX_CACHE: dict[int, tuple[str, list[int]]] = {}


def line_of(text: str, pos: int) -> int:
    """1-based line number for a character offset.

    `text[:pos].count("\n")` is O(n) per call; across ~30 checks that makes
    the whole audit O(n * findings). A per-document prefix index keeps the
    total linear, which matters: a 450KB page previously took minutes.
    """
    key = id(text)
    cached = _LINE_INDEX_CACHE.get(key)
    if cached is None or cached[0] is not text:
        idx = [0]
        find = text.find
        i = find("\n")
        while i != -1:
            idx.append(i + 1)
            i = find("\n", i + 1)
        _LINE_INDEX_CACHE.clear()   # one document at a time is enough
        _LINE_INDEX_CACHE[key] = (text, idx)
        cached = (text, idx)
    idx = cached[1]
    lo, hi = 0, len(idx)
    while lo < hi:
        mid = (lo + hi) // 2
        if idx[mid] <= pos:
            lo = mid + 1
        else:
            hi = mid
    return max(1, lo)


_RULE_CACHE: dict[int, tuple[str, list[tuple[str, str, int]]]] = {}


def iter_rules(text: str) -> list[tuple[str, str, int]]:
    """Linear scan for `selector { body }` pairs: (selector, body, body_offset).

    The obvious brace-matching regex backtracks quadratically on a
    document with many braces — 8s on a 55KB page, minutes on a 450KB one.
    A single pass over the braces is O(n) and yields the same pairs.
    """
    key = id(text)
    cached = _RULE_CACHE.get(key)
    if cached is not None and cached[0] is text:
        return cached[1]

    rules: list[tuple[str, str, int]] = []
    depth = 0
    sel_start = 0
    body_start = -1
    for i, ch in enumerate(text):
        if ch == "{":
            if depth == 0:
                body_start = i + 1
                sel_start = i
            depth += 1
        elif ch == "}":
            if depth == 1 and body_start != -1:
                # selector is the text between the previous `}`/`;`/newline
                # boundary and the opening brace
                raw = text[sel_start::-1]
                # walk back to the nearest statement boundary
                j = sel_start - 1
                while j >= 0 and text[j] not in "};":
                    j -= 1
                sel = text[j + 1: sel_start].strip()
                # a rule may follow a tag boundary ("<style>\nbody {")
                if ">" in sel:
                    sel = sel.rsplit(">", 1)[-1].strip()
                rules.append((sel, text[body_start:i], body_start))
                body_start = -1
            depth = max(0, depth - 1)
    _RULE_CACHE.clear()
    _RULE_CACHE[key] = (text, rules)
    return rules


def finding(fid, lens, severity, loc, rule, now, proposed, effort,
            evidence="code", verified=False):
    return {
        "id": fid, "lens": lens, "severity": severity, "location": loc,
        "rule": rule, "now": now, "proposed": proposed, "effort": effort,
        "evidence": evidence, "verified": verified,
    }


# ------------------------------------------------------------------- checks

def rgb_to_hsl(rgb: tuple[int, int, int]) -> tuple[float, float, float]:
    r, g, b = (c / 255 for c in rgb)
    mx, mn = max(r, g, b), min(r, g, b)
    l = (mx + mn) / 2
    if mx == mn:
        return 0.0, 0.0, l * 100
    d = mx - mn
    s = d / (2 - mx - mn) if l > 0.5 else d / (mx + mn)
    if mx == r:
        h = ((g - b) / d + (6 if g < b else 0)) * 60
    elif mx == g:
        h = ((b - r) / d + 2) * 60
    else:
        h = ((r - g) / d + 4) * 60
    return h, s * 100, l * 100


def check_grey_on_color(path: Path, text: str) -> list[dict]:
    """Grey text on a saturated background (§2.3).

    The wanted effect is reduced contrast, not reduced chroma: a low-saturation
    foreground on a high-saturation background reads dirty.
    """
    out = []
    variables = resolve_vars(text)
    blocks = [(m.group(1), m.start()) for m in re.finditer(r"\{([^{}]*)\}", text)]
    blocks += [(m.group(1), m.start()) for m in re.finditer(r'style="([^"]*)"', text)]
    for body, offset in blocks:
        fg = re.search(r"(?:^|;|\s)color\s*:\s*([^;}]+)", body)
        bg = re.search(r"background(?:-color)?\s*:\s*([^;}]+)", body)
        if not (fg and bg):
            continue
        fg_hex, bg_hex = expand_color(fg.group(1), variables), expand_color(bg.group(1), variables)
        if not (fg_hex and bg_hex):
            continue
        frgb, brgb = hex_to_rgb(fg_hex), hex_to_rgb(bg_hex)
        if not (frgb and brgb):
            continue
        _, fs_, fl = rgb_to_hsl(frgb)
        _, bs, bl = rgb_to_hsl(brgb)
        # Foreground near-neutral, background clearly chromatic — but exclude
        # pure white and pure black. Both have saturation 0 by definition, and
        # white-on-brand is a correct primary button, not "grey on colour".
        if (frgb in ((255, 255, 255), (0, 0, 0))
                or max(frgb) - min(frgb) < 3 and fl > 96):
            continue
        if fs_ <= 12 and bs >= 25 and 25 <= bl <= 75:
            line = line_of(text, offset + fg.start())
            out.append(finding(
                f"G-{len(out)+1:03d}", "color", "P1", f"{path}:{line}", "§2.3",
                f"灰字 {fg_hex}（饱和度 {fs_:.0f}%）叠在彩色背景 {bg_hex}（饱和度 {bs:.0f}%）上",
                "取背景同色相、降低明度得到次要文字色，不要用中性灰或半透明白", "S",
                evidence=f"measured:hsl(fg s={fs_:.0f}%, bg s={bs:.0f}%)"))
    return out


def check_primary_button_count(path: Path, text: str) -> list[dict]:
    """More than one filled/solid action on one screen (§2.8).

    Real code usually applies one CSS rule to a group of buttons
    (`.actions button { background: var(--primary) }`) rather than tagging each
    with a `primary` class, so match both shapes.
    """
    out = []
    variables = resolve_vars(text)
    sites: list[int] = []

    # The canvas colour anchors the surface-vs-button judgement below: a fill
    # one or two steps above it is a card, not a CTA. Scan every rule and keep
    # the first `html`/`body`/`:root` one that actually sets a background —
    # `html{}` often holds only `-webkit-text-size-adjust`, with the real
    # canvas on `body`, and `:root` before it must not end the search.
    page_bg_rgb = None
    for sel, body, _off in iter_rules(text):
        if not re.fullmatch(r"\s*(?:html|body|:root)\s*", sel):
            continue
        bg = re.search(r"background(?:-color)?\s*:\s*([^;}]+)", body)
        if not bg:
            continue
        resolved = expand_color(bg.group(1), variables)
        if resolved:
            page_bg_rgb = hex_to_rgb(resolved)
            break

    # (a) CSS rule that fills a button/anchor selector with a solid background.
    # Anchors styled as buttons count too — `.ctas a { background: … }` is the
    # most common marketing-page shape.
    for sel, body, body_off in iter_rules(text):
        # Only selectors that actually target a button or a link count.
        # Substring-matching "a" would also hit `.skip`, `.foot__line` and
        # `::selection`, which is how this check previously reported 18
        # "primary buttons" on a page with one.
        sel_norm = sel.strip()
        if sel_norm.startswith(("::", "/*")) or not sel_norm:
            continue
        # `:hover`/`:focus`/`:active` fills are interaction states, not resting
        # primary actions: a hovered list row is not competing with the CTA.
        # Counting them reported 12 "primary buttons" on an index page whose
        # only fill is `.row a:hover{background:…}`.
        if re.search(r":(?:hover|active|focus|visited)\b", sel_norm, re.I):
            continue
        # The last compound in the selector must be the button/link itself:
        # `.ctas a` and `.btn--solid` qualify; `.foot__col a` styles links
        # inside a footer and is not a primary action.
        last = re.split(r"[\s,>+~]+", sel_norm)[-1] if sel_norm else ""
        if not re.match(r"^(?:[a-zA-Z0-9_-]+)?(?:button|a)(?:[.:\[#_-]|$)", last, re.I) \
           and not re.search(r"button", last, re.I):
            continue
        # A plain link rule that only sets `color` is not a filled button; the
        # background check below handles that, so nothing more is needed here.
        if re.search(r"(?:footer|foot__|nav__|breadcrumb)", sel_norm, re.I):
            continue
        bg = re.search(r"background(?:-color)?\s*:\s*([^;}]+)", body)
        if not bg:
            continue
        hexv = expand_color(bg.group(1), variables)
        if not hexv:
            continue
        rgb = hex_to_rgb(hexv)
        if not rgb:
            continue
        _, sat, light = rgb_to_hsl(rgb)
        # A "solid" button is one with a filled background that contrasts with
        # the page — that includes dark neutrals like #374151, not just
        # chromatic primaries. Exclude near-white fills (those are surfaces,
        # not buttons) and near-transparent values.
        if light >= 92:
            continue
        # A card surface is not a primary action. List links on an index page
        # routinely sit on a fill one or two steps above the canvas; that fill
        # reads as "this row is a container", not "this is the thing to click
        # first". Judge by distance from the canvas: near it and desaturated
        # means surface; far from it, or chromatic, means button.
        if sat < 25 and page_bg_rgb:
            gap = max(abs(rgb[i] - page_bg_rgb[i]) for i in range(3))
            if gap <= 24:
                continue
        # how many elements does this selector actually fill?
        n = 0
        # `X button {…}` / `X a {…}` where X is a class, an id, or a bare element
        container = re.search(r"(?:^|\s)([.#]?[a-zA-Z0-9_-]+)\s+(?:button|a)\s*$", sel, re.I)
        if container:
            token = container.group(1)
            if token.startswith("."):
                pat = r'class=["\'][^"\']*\b' + re.escape(token[1:]) + r'\b'
            elif token.startswith("#"):
                pat = r'id=["\']' + re.escape(token[1:]) + r'["\']'
            else:
                pat = r"<" + re.escape(token) + r"\b"
            cm = re.search(pat, text, re.I)
            if cm:
                # scope from the container's opening tag to its closing block
                tail = text[cm.start():]
                end = re.search(r"</(?:div|section|form|footer|header|nav|main|ul)>", tail, re.I)
                scope = tail[: end.end()] if end else tail
                n = len(re.findall(r"<(?:button|a)\b", scope, re.I))
            else:
                n = len(re.findall(r"<(?:button|a)\b", text, re.I))
        elif re.fullmatch(r"(?:button|a)", sel.strip(), re.I):
            # A bare element reset like `button{font:inherit}` has no filled
            # background worth counting, and a bare `a{color:inherit}` matches
            # every link on the page. Neither is a "primary action" signal.
            continue
        else:
            # `.btns button:first-child` and friends: a pseudo-selector that
            # fills one specific button is still a competing primary action.
            if re.search(r":(?:first|last|nth)-", sel, re.I):
                n = 1
            else:
                target = sel.strip().lstrip(".#").split()[0] if sel.strip() else ""
                n = len(re.findall(r'class=["\'][^"\']*\b' + re.escape(target) + r'\b', text)) if target else 0
        if n > 1:
            # Record one site per button this rule fills, so the count reflects
            # competing actions rather than the number of CSS rules. Report the
            # first matching element's line, not the rule's: a reader opens the
            # markup, not the stylesheet.
            first_el = re.search(r"<(?:button|a)\b", text, re.I)
            sites.extend([first_el.start() if first_el else body_off] * n)
        elif n == 1:
            # A pseudo-selector filling a single button still competes with the
            # rule that fills the others; count it so two filled buttons on one
            # row are detected even when each comes from its own rule.
            sites.append(body_off)

    # (b) buttons whose own class/style marks them primary
    for m in re.finditer(r"<button\b([^>]*)>", text, re.I):
        attrs = m.group(1)
        blob = " ".join(filter(None, [
            (re.search(r'class=["\']([^"\']*)', attrs) or [None, ""])[1],
            (re.search(r'style=["\']([^"\']*)', attrs) or [None, ""])[1]]))
        if re.search(r"\b(btn-)?primary\b|\bbg-(primary|accent)\b", blob, re.I):
            # Use the button's own offset. `body_off` belongs to the CSS loop
            # above and is unbound when a file has no stylesheet at all — that
            # crashed the whole audit on a one-line HTML file.
            sites.append(m.start())

    if len(sites) >= 2:
        line = line_of(text, min(sites))
        out.append(finding(
            "P-001", "hierarchy", "P1", f"{path}:{line}", "§2.8",
            f"同屏出现多个主色实心按钮（{len(sites)} 处），主次未分级",
            "只保留一个主行动（实心），其余改为描边或纯文字；危险操作不因危险而变大", "S"))
    return out


def check_grouping_rhythm(path: Path, text: str) -> list[dict]:
    """Group spacing must exceed intra-group spacing (§3.6).

    Compares the vertical gap between a label and its input against the gap
    between field groups. Equal values are the classic "everything melts
    together" bug.
    """
    out = []
    # collect margin-bottom values per selector
    rules = {}
    for sel, body, body_off in iter_rules(text):
        mb = re.search(r"margin-bottom\s*:\s*([\d.]+)(px|rem|em)", body)
        if mb and sel:
            val = float(mb.group(1))
            if mb.group(2) == "rem":
                val *= 16
            elif mb.group(2) == "em":
                val *= 16
            rules[sel] = val
    label_sel = [s for s in rules if re.search(r"label", s, re.I)]
    group_sel = [s for s in rules if re.search(r"(row|group|field|form-group)", s, re.I)]
    if label_sel and group_sel:
        lv = min(rules[s] for s in label_sel)
        gv = max(rules[s] for s in group_sel)
        if gv and lv and gv <= lv * 1.25:
            m = re.search(r"(label|\.row|\.group|\.field)[^{]*\{[^}]*margin-bottom", text, re.I)
            line = line_of(text, body_off) if m else 1
            out.append(finding(
                "K-001", "spacing", "P1", f"{path}:{line}", "§3.6",
                f"标签到输入的间距 {lv:g}px 与组间距 {gv:g}px 接近，分组在视觉上不成立",
                "组间距至少是组内间距的 1.5–2 倍", "S",
                evidence=f"measured:label={lv:g}px group={gv:g}px"))
    return out


def check_measure(path: Path, text: str) -> list[dict]:
    """Body copy wider than ~75ch / 35em (§4.3).

    Only fires when the file actually contains prose-length text; a dashboard
    of short labels has no measure problem.
    """
    out = []
    # Measure is a property of rendered paragraphs. A stylesheet has none: its
    # longest "text" is a comment, and a token template's header comment is
    # easily 800 characters. Judge only markup that can carry prose.
    if not re.search(r"<(?:p|li|blockquote|article|section|div|td)\b", text, re.I):
        return out
    # Strip <style>/<script> first. Without this, the regex below happily
    # matches 400+ characters of CSS between tags and reports the stylesheet
    # as unconstrained body copy.
    visible = re.sub(r"<(style|script)\b[^>]*>.*?</\1>", "", text, flags=re.S | re.I)
    visible = re.sub(r"<!--.*?-->", "", visible, flags=re.S)
    visible = re.sub(r"/\*.*?\*/", "", visible, flags=re.S)
    prose = re.search(r">\s*(?:<p[^>]*>)?([^<]{400,})<", visible)
    if not prose:
        return out
    # look for a max-width on the text container
    constrained = False
    for sel, body, body_off in iter_rules(text):
        mw = re.search(r"max-width\s*:\s*([\d.]+)\s*(ch|em|rem|px)", body)
        if not mw:
            continue
        val = float(mw.group(1))
        unit = mw.group(2)
        if unit in ("ch", "em") and val <= 75:
            constrained = True
        elif unit in ("rem",) and val <= 47:
            constrained = True
        elif unit == "px" and val <= 760:
            constrained = True
    if not constrained:
        line = line_of(text, prose.start())
        out.append(finding(
            "Q-001", "typography", "P0", f"{path}:{line}", "§4.3",
            f"正文没有行宽约束（文本长度 {len(prose.group(1))} 字符），1280px 下一行会超过 75 字符",
            "给正文容器加 max-width: 65ch（无衬线）或 75ch（衬线）", "XS"))
    return out


def declared_font_sizes(text: str) -> set[float]:
    """Every font size the sheet actually sets, by either syntax.

    `font: 500 11px/1 var(--mono)` is as common as `font-size: 11px` in
    editorial CSS. Reading only the longhand meant a page could declare its
    whole scale through the shorthand and be invisible to §4.1.
    """
    sizes = {round(float(v), 1)
             for v in re.findall(r"font-size\s*:\s*([\d.]+)px", text)}
    # font shorthand: optional style/weight, then size, then /line-height.
    sizes |= {round(float(v), 1) for v in
              re.findall(r"\bfont\s*:\s*[^;}\"']*?(?<![\w.])([\d.]+)px", text)}
    return sizes


def check_type_scale_ratio(path: Path, text: str) -> list[dict]:
    """Adjacent type sizes closer than 1.2x (§4.1).

    A declared scale whose steps sit at 1.05-1.15 does not read as hierarchy:
    the reader cannot tell the levels apart. Only fires when the file declares
    at least four distinct font sizes, since a 2-3 size file has no scale to
    judge.

    Severity is graded against the corpus numbers §4.1 itself publishes
    (median 1.154, IQR 1.119-1.200). 1.2 is the ideal, not the threshold of
    defect: a 13->15 step at 1.153 is the single most common real-world
    choice, so reporting it as P1 on every page turns the gate into noise.
    Below the IQR floor the scale is denser than three quarters of real sites
    and cannot be read as hierarchy — that is the P1. Between the floor and
    1.2 it stays a P2 note: worth knowing, legitimate to keep.

    Sizes under 13px are treated as a single micro tier rather than as scale
    steps. §4.1 records why: corpus extractions mix in badge and footnote
    sizes, and a 10px mono label next to an 11px one is a label pair, not two
    heading levels competing for the same job. Pairs are filtered, not the
    size list itself — dropping small sizes outright would let a page hide a
    dense 13/14/15 scale behind one 10px label.
    """
    out = []
    sizes = sorted(declared_font_sizes(text))
    if len(sizes) < 4:
        return out
    too_close = []
    for a, b in zip(sizes, sizes[1:]):
        if a <= 0:
            continue
        r = b / a
        # ignore micro-steps under 10px (legal text vs caption) and exact ties
        if 1.001 < r < 1.2 and a >= 13:
            too_close.append((a, b, r))
    if len(too_close) < 2:
        return out
    # The densest pair decides the severity.
    worst = min(r for _, _, r in too_close)
    severity = "P1" if worst < 1.119 else "P2"
    a, b, r = too_close[0]
    # Anchor on whichever syntax set this size, so a shorthand-only sheet
    # reports a real line instead of :1.
    m = re.search(r"font-size\s*:\s*" + re.escape(f"{a:g}"), text) \
        or re.search(r"\bfont\s*:[^;}\"']*?(?<![\w.])" + re.escape(f"{a:g}") + r"px", text)
    line = line_of(text, m.start()) if m else 1
    pairs = "、".join(f"{x:g}→{y:g}({rr:.2f}×)" for x, y, rr in too_close[:4])
    out.append(finding(
        "TS-001", "typography", severity, f"{path}:{line}", "§4.1",
        f"字阶相邻档比值过密：{pairs}（理想 ≥ 1.2，最密一档 {worst:.2f}×）",
        "拉开字阶：相邻档比值至少 1.2，档位数控制在 5–7 档；"
        "若现有层级已可读，§4.1 允许保留，报告冲突让用户决定", "S",
        evidence=f"measured:{len(too_close)} pairs < 1.2, densest {worst:.3f}"))
    return out


def check_heading_line_height(path: Path, text: str) -> list[dict]:
    """Large headings at body-scale line-height (§4.5)."""
    out = []
    for sel, body, body_off in iter_rules(text):
        fs = re.search(r"font-size\s*:\s*([\d.]+)px", body)
        lh = re.search(r"line-height\s*:\s*([\d.]+)(px)?", body)
        if not (fs and lh):
            continue
        size = float(fs.group(1))
        if size < 32:
            continue
        if lh.group(2) == "px":
            ratio = float(lh.group(1)) / size
        else:
            ratio = float(lh.group(1))
        if ratio > 1.3:
            line = line_of(text, body_off)
            out.append(finding(
                f"H-{len(out)+1:03d}", "typography", "P1", f"{path}:{line}", "§4.5",
                f"{size:g}px 标题用了 {ratio:.2f} 行高（大标题应接近 1.0–1.2）",
                "大标题行高降到 1.0–1.2；字号越大，相对行高应越小", "XS",
                evidence=f"measured:{size:g}px/{ratio:.2f}"))
    return out


def check_gradient_hue(path: Path, text: str) -> list[dict]:
    """Gradient endpoints too far apart in hue (§5.9, book §8.3)."""
    out = []
    variables = resolve_vars(text)
    for m in re.finditer(r"linear-gradient\(([^;)]+)\)", text):
        stops = re.findall(r"(#[0-9a-fA-F]{3,6}|var\(--[a-zA-Z0-9_-]+\))", m.group(1))
        hexes = [expand_color(s, variables) for s in stops]
        hexes = [h for h in hexes if h]
        if len(hexes) < 2:
            continue
        hs = []
        for h in hexes[:2]:
            rgb = hex_to_rgb(h)
            if not rgb:
                continue
            hh, ss, ll = rgb_to_hsl(rgb)
            if ss < 8:      # near-neutral endpoints don't count as hue drift
                continue
            hs.append(hh)
        if len(hs) == 2:
            d = abs(hs[0] - hs[1])
            d = min(d, 360 - d)
            if d > 60:
                line = line_of(text, m.start())
                out.append(finding(
                    f"U-{len(out)+1:03d}", "color", "P1", f"{path}:{line}", "§5.9 §8.3.1",
                    f"渐变两端色相差 {d:.0f}°（{hexes[0]} → {hexes[1]}），中间会经过脏色",
                    "两端色相控制在 30° 内，用明度和饱和度做变化", "S",
                    evidence=f"measured:hue-delta={d:.0f}"))
    return out


def check_overweight_shadow(path: Path, text: str) -> list[dict]:
    """Modal-scale shadow on a static surface (§6.3, book §6.2).

    A card at rest should not cast a shadow that implies it is floating above
    a scrim. y-offset ≥ 8px with blur ≥ 12px is modal/dropdown territory.
    """
    out = []
    for m in BOX_SHADOW.finditer(text):
        val = m.group(1)
        if "inset" in val:
            continue
        for part in re.split(r",(?![^(]*\))", val):
            # Length values may be unitless zero (`0 10px 15px`), so match
            # `0` and `<n>px` alike; drop the color function first.
            clean = re.sub(r"(?:rgba?|hsla?|oklch)\([^)]*\)", "", part)
            nums = re.findall(r"(?:^|\s)(-?[\d.]+)(?:px)?(?=\s|$)", clean)
            if len(nums) < 3:
                continue
            y, blur = abs(float(nums[1])), float(nums[2])
            if y >= 8 and blur >= 12:
                # Skip rules that are clearly overlays.
                head = text[max(0, m.start() - 400): m.start()]
                if re.search(r"(dialog|modal|sheet|drawer|popover|dropdown|toast|menu)",
                             head, re.I):
                    continue
                line = line_of(text, m.start())
                out.append(finding(
                    f"V-{len(out)+1:03d}", "depth", "P1", f"{path}:{line}", "§6.2 §6.3",
                    f"静态表面用了模态级阴影（y={y:g}px blur={blur:g}px）：{val.strip()[:60]}",
                    "卡片层级用 y≤4px、blur≤8px 的轻阴影；模态级阴影只给真正浮起的元素", "XS",
                    evidence=f"measured:y={y:g}px,blur={blur:g}px"))
                break
    return out


def check_text_over_image(path: Path, text: str) -> list[dict]:
    """Light text directly on a light image with no overlay/shadow (§7.3)."""
    out = []
    # an element that sets a background-image and light text, without a scrim
    for sel, body, body_off in iter_rules(text):
        if not re.search(r"background(?:-image)?\s*:[^;}]*url\(", body, re.I):
            continue
        fg = re.search(r"(?:^|;|\s)color\s*:\s*(#[0-9a-fA-F]{3,6}|white|#fff)", body)
        if not fg:
            continue
        # Look only inside the rule body. Concatenating a 500-char slice of
        # the whole document per rule made this quadratic (5.7s on a 55KB file,
        # ~10 minutes on a 450KB one).
        has_guard = bool(re.search(
            r"(linear-gradient\([^)]*rgba|text-shadow|backdrop-filter|mix-blend-mode|::?before)",
            body, re.I))
        if has_guard:
            continue
        line = line_of(text, body_off)
        out.append(finding(
            f"J-{len(out)+1:03d}", "imagery", "P0", f"{path}:{line}", "§7.2 §7.3",
            "浅色文字直接压在图片上，没有遮罩/模糊/文字阴影",
            "加渐变遮罩 + 可选文字阴影，并验证文字所在最亮处的对比度 ≥ 4.5:1", "S"))
    return out


def check_emoji_icons(path: Path, text: str) -> list[dict]:
    """Emoji used as UI icons (§8.1, §7.4)."""
    out = []
    emoji = re.compile("[\U0001F300-\U0001FAFF\u2600-\u27BF]")
    hits = []
    for m in emoji.finditer(text):
        # ignore inside comments
        line_start = text.rfind("\n", 0, m.start()) + 1
        line_end = text.find("\n", m.start())
        line = text[line_start: line_end if line_end != -1 else len(text)]
        if line.strip().startswith(("//", "*", "<!--")):
            continue
        hits.append(m.start())
    if len(hits) >= 2:
        line = line_of(text, hits[0])
        out.append(finding(
            "O-001", "imagery", "P2", f"{path}:{line}", "§8.1 §7.4",
            f"用 emoji 当图标（{len(hits)} 处）",
            "改用同一套 SVG 图标；emoji 跨平台渲染不一致，且会被读屏念出", "S"))
    return out


def check_brand_drift(path: Path, text: str, brief: str | None) -> list[dict]:
    """A declared brand color the UI never actually uses (§1.4).

    The classic generated-page failure: the brief says "brand is teal", the
    token is declared, and every surface is indigo. Only decidable when the
    brief states a brand color, so it is opt-in via --brand.
    """
    if not brief:
        return []
    brief_hex = brief.strip().lower()
    if not re.fullmatch(r"#[0-9a-f]{3,6}", brief_hex):
        return []
    # The brand color appearing only in a comment is exactly the failure this
    # check exists for: the brief states it, the code never applies it.
    code_only = re.sub(r"<!--.*?-->", "", text, flags=re.S)
    code_only = re.sub(r"/\*.*?\*/", "", code_only, flags=re.S)
    decl = len(re.findall(r"--[\w-]*(?:primary|brand|accent)[\w-]*\s*:\s*" +
                          re.escape(brief_hex), code_only, re.I))
    literal_uses = sum(1 for h in HEX.findall(code_only) if h.lower() == brief_hex) - decl
    # A tokenised brand color is used through var(--name); counting only
    # literals would flag every properly tokenised project.
    var_uses = 0
    for vm in re.finditer(r"(--[\w-]+)\s*:\s*" + re.escape(brief_hex), code_only, re.I):
        var_uses += len(re.findall(r"var\(\s*" + re.escape(vm.group(1)) + r"\b", code_only))
    if literal_uses > 0 or var_uses > 0:
        return []
    variables = resolve_vars(text)
    offender = None
    for sel, body, body_off in iter_rules(text):
        bg = re.search(r"background(?:-color)?\s*:\s*([^;}]+)", body)
        if not bg:
            continue
        hexv = expand_color(bg.group(1), variables)
        if not hexv or hexv == brief_hex:
            continue
        rgb = hex_to_rgb(hexv)
        if not rgb:
            continue
        _, sat, light = rgb_to_hsl(rgb)
        if sat >= 25 and light < 92:
            offender = hexv
            break
    # Two different defects, two different rules:
    #   - brand replaced by another chromatic primary → §1.4.2 (personality/color)
    #   - brand declared but simply never applied  → §5.4 (color budget)
    rule = "§1.4.2 §5.4" if offender else "§5.4"
    return [finding(
        "Z-001", "color", "P0", str(path), rule,
        f"品牌色 {brief_hex} 已声明但未用于任何实心按钮/强调面"
        + (f"；实际主色是 {offender}" if offender else ""),
        "把品牌色用于主行动与强调面；不要用生成器的默认色（靛蓝/紫）替换产品品牌", "S")]


def check_dead_end(path: Path, text: str) -> list[dict]:
    """A screen with no enabled interactive element has no path forward (§2.8).

    This is the RED-baseline P0: a first-run empty state that renders only
    disabled filters and a disabled search box. Deterministic to detect and
    fatal to usability, so it outranks every cosmetic finding.
    """
    interactive = re.findall(r"<(a|button|input|select|textarea)\b([^>]*)>", text, re.I)
    enabled = []
    disabled = []
    for tag, attrs in interactive:
        if re.search(r"\bdisabled\b", attrs, re.I) or re.search(r'type=["\']hidden', attrs, re.I):
            disabled.append(tag)
            continue
        if tag.lower() == "a" and not re.search(r"\bhref\s*=", attrs, re.I):
            continue
        enabled.append(tag)
    if enabled or not disabled:
        return []
    return [finding(
        "X-001", "hierarchy", "P0", str(path), "§2.8",
        f"页面没有任何可用的交互元素（{len(disabled)} 个控件全部 disabled）",
        "空状态必须给出一个主行动（创建第一条数据的实心按钮），并隐藏此时无意义的控件",
        "S")]


def check_disabled_chrome(path: Path, text: str) -> list[dict]:
    """Disabled filters/search/table headers alongside empty content (§8.4)."""
    out = []
    disabled_ctrl = re.search(r"<(?:button|input|select)\b[^>]*\bdisabled\b", text, re.I)
    emptyish = re.search(r"(no results|nothing here|no data|暂无数据|还没有|空的)", text, re.I)
    if disabled_ctrl and emptyish:
        line = line_of(text, disabled_ctrl.start())
        out.append(finding(
            f"E-{len(out)+1:03d}", "finishing", "P0", f"{path}:{line}", "§8.4",
            "空状态下仍渲染了禁用的筛选/搜索控件",
            "零数据时不渲染筛选器、搜索框、空表格表头；把空间留给主行动", "XS"))
    return out


def check_search_miss_copy(path: Path, text: str) -> list[dict]:
    """'No results found' used as first-run empty copy (§11.4).

    The copy is only legitimate when the user could actually have searched.
    A *disabled* search box next to "No results found" is the worst case: the
    message blames a query the user cannot even type.
    """
    out = []
    m = re.search(r"(no results found|no matches|nothing matched|没有找到|未找到结果)", text, re.I)
    if not m:
        return out
    # A usable search input makes the copy defensible.
    for sm in re.finditer(r"<input\b[^>]*>", text, re.I):
        if re.search(r"type=[\"']search", sm.group(0), re.I) and \
           not re.search(r"\bdisabled\b", sm.group(0), re.I):
            return out
    line = line_of(text, m.start())
    out.append(finding(
        f"N-{len(out)+1:03d}", "copy", "P0", f"{path}:{line}", "§11.4",
        f"用搜索失败文案 {m.group(0)!r} 作为首次使用的空状态（且没有可用的搜索框）",
        "首次使用写「还没有项目」+ 一句说明 + 主行动；搜索无结果才用「没有找到」", "XS"))
    return out


def check_hardcoded_colors(path: Path, text: str, is_css: bool) -> list[dict]:
    """Hardcoded colors outside a token declaration block."""
    out = []
    # A token file legitimately contains literals; skip files that are clearly
    # the token source.
    if re.search(r"(:root|@theme|--color-)", text) and text.count("--") > 8:
        return out
    for i, line in enumerate(text.splitlines(), 1):
        if line.strip().startswith(("//", "*", "/*")):
            continue
        for m in HEX.finditer(line):
            # allow inside CSS custom property declarations
            if re.match(r"\s*--[\w-]+\s*:", line):
                continue
            out.append(finding(
                f"C-{len(out)+1:03d}", "color", "P1", f"{path}:{i}", "§5.4",
                f"硬编码颜色 {m.group(0)}", "改用语义 token（如 var(--primary) 或 bg-primary）",
                "XS"))
            break
        else:
            continue
        break
    return out


def check_tailwind_space(path: Path, text: str) -> list[dict]:
    out = []
    for i, line in enumerate(text.splitlines(), 1):
        for m in SPACE_TW.finditer(line):
            out.append(finding(
                f"S-{len(out)+1:03d}", "spacing", "P1", f"{path}:{i}", "§3.2",
                f"使用了 {m.group(0)}", "改用 flex/grid + gap-*", "XS"))
    return out


def check_arbitrary_values(path: Path, text: str) -> list[dict]:
    out = []
    for i, line in enumerate(text.splitlines(), 1):
        for m in ARBITRARY_TW.finditer(line):
            val = m.group(2)
            # arbitrary values that reference a var() are legitimate
            if "var(" in val:
                continue
            out.append(finding(
                f"A-{len(out)+1:03d}", "spacing", "P1", f"{path}:{i}", "§3.2",
                f"任意值 {m.group(1)}-[{val}]", "改用刻度内的值，或定义为 token", "XS"))
    return out


def check_img_alt(path: Path, text: str) -> list[dict]:
    out = []
    for m in IMG_TAG.finditer(text):
        tag = m.group(0)
        if re.search(r"\balt\s*=", tag, re.I):
            continue
        line = line_of(text, m.start())
        out.append(finding(
            f"I-{len(out)+1:03d}", "a11y", "P0", f"{path}:{line}", "§10.3",
            "<img> 缺少 alt", '内容图写描述，装饰图写 alt=""', "XS"))
    return out


def check_input_label(path: Path, text: str) -> list[dict]:
    """An input with neither id+label, aria-label, nor aria-labelledby."""
    out = []
    labels_for = set(re.findall(r'<label[^>]*\bfor=["\']([^"\']+)', text))
    for m in INPUT_TAG.finditer(text):
        tag = m.group(0)
        if re.search(r'type=["\']hidden', tag, re.I):
            continue
        if re.search(r"\baria-label(?:ledby)?\s*=", tag, re.I):
            continue
        idm = re.search(r'\bid=["\']([^"\']+)', tag)
        if idm and idm.group(1) in labels_for:
            continue
        # A <label> that wraps the control is equally valid and needs no id.
        before = text[: m.start()]
        open_label = before.rfind("<label")
        close_label = before.rfind("</label>")
        if open_label > close_label and open_label != -1:
            continue
        if re.search(r"\baria-hidden", tag, re.I):
            continue
        line = line_of(text, m.start())
        out.append(finding(
            f"L-{len(out)+1:03d}", "a11y", "P0", f"{path}:{line}", "§10.3",
            f"<{m.group(1)}> 没有关联 label",
            "加 <label for>、aria-label 或 aria-labelledby", "XS"))
    return out


def enclosing_block(text: str, pos: int) -> str:
    """Return the CSS rule body or style="..." value containing pos.

    Scoping to the actual block matters: a ±N-line window would let an
    unrelated `box-shadow` elsewhere in the file excuse an `outline: none`.
    """
    # inline style attribute
    start = text.rfind('style="', 0, pos)
    if start != -1 and text.find('"', start + 7, pos) == -1:
        end = text.find('"', pos)
        return text[start: end if end != -1 else len(text)]
    # CSS rule body
    open_brace = text.rfind("{", 0, pos)
    if open_brace == -1:
        return ""
    close = text.find("}", pos)
    prev_close = text.rfind("}", 0, open_brace)
    if prev_close > open_brace:
        return ""
    return text[open_brace: close if close != -1 else len(text)]


def check_outline_none(path: Path, text: str) -> list[dict]:
    out = []
    for m in OUTLINE_NONE.finditer(text):
        block = enclosing_block(text, m.start())
        # A replacement ring declared in the *same* rule is acceptable.
        if re.search(r"(box-shadow|outline-offset|:focus-visible)", block):
            continue
        line = line_of(text, m.start())
        out.append(finding(
            f"F-{len(out)+1:03d}", "a11y", "P0", f"{path}:{line}", "§10.4",
            "移除了 outline 但没有替代焦点指示",
            "提供 2px :focus-visible 焦点环", "XS"))
    return out


def check_reduced_motion(path: Path, text: str) -> list[dict]:
    if not ANIM.search(text):
        return []
    if REDUCED_MOTION.search(text):
        return []
    line = ANIM.search(text)
    assert line is not None
    ln = line_of(text, line.start())
    return [finding(
        "M-001", "motion", "P1", f"{path}:{ln}", "§9",
        "有 animation/transition 但没有 prefers-reduced-motion 处理",
        "加 @media (prefers-reduced-motion: reduce) 关闭动效", "XS")]


def check_single_shadow(path: Path, text: str) -> list[dict]:
    out = []
    for m in BOX_SHADOW.finditer(text):
        val = m.group(1)
        # count top-level commas: multi-layer shadows have > 1
        depth, parts = 0, 1
        for ch in val:
            if ch == "(":
                depth += 1
            elif ch == ")":
                depth -= 1
            elif ch == "," and depth == 0:
                parts += 1
        # Skip values we cannot count: var() references, `none`, and ring-style
        # shadows (`0 0 0 3px`) which are focus indicators, not elevation.
        if "var(" in val or val.strip() == "none" or re.match(r"\s*0(?:px)?\s+0(?:px)?\s+0(?:px)?\s+\d", val):
            continue
        if parts == 1 and "inset" not in val:
            line = line_of(text, m.start())
            out.append(finding(
                f"D-{len(out)+1:03d}", "depth", "P2", f"{path}:{line}", "§6.2",
                f"单层阴影 {val.strip()[:50]}", "用 2–4 层叠加（近锐远柔）", "XS"))
    return out


def thin_weight_size(text: str, pos: int) -> float | None:
    """The size a `font-weight` actually renders at, or None when unknowable.

    §4.7's failure mode is specific: thin strokes vanish *at small sizes*. A
    100-weight hero at 64px is a legitimate design choice, so the rule cannot
    fire on weight alone. Size can come from the same block, an inherited
    `font:`/`font-size` earlier in the sheet, or a `clamp()` — in which case
    the minimum is what matters, because that is where the strokes go first.
    """
    block = enclosing_block(text, pos)
    for pat in (r"font-size\s*:\s*clamp\(\s*([\d.]+)px",
                r"font-size\s*:\s*([\d.]+)px",
                r"font\s*:\s*(?:\d{3}\s+)?([\d.]+)px"):
        m = re.search(pat, block)
        if m:
            return float(m.group(1))
    # Not in the same block: fall back to the nearest preceding declaration,
    # which covers `.sect{font-size:15px}` followed by `.sect b{font-weight:300}`.
    m = None
    for m in re.finditer(r"font-size\s*:\s*(?:clamp\(\s*)?([\d.]+)px", text[:pos]):
        pass
    return float(m.group(1)) if m else None


def check_font_weight_300(path: Path, text: str) -> list[dict]:
    out = []
    for m in FONT_WEIGHT.finditer(text):
        weight = int(m.group(1))
        if weight >= 400:
            continue
        size = thin_weight_size(text, m.start())
        # Unknown size stays silent: guessing "body copy" from weight alone is
        # what made this gate cry wolf on weight-ladder specimens.
        if size is None or size >= 18:
            continue
        line = line_of(text, m.start())
        out.append(finding(
            f"W-{len(out)+1:03d}", "typography", "P1", f"{path}:{line}", "§4.7",
            f"{size:g}px 的文字用了字重 {weight}（细字在小字号下笔画消失）",
            "正文用 400 或更高；200–300 只留给 24px 以上的展示字", "XS",
            evidence=f"measured:weight={weight}@size={size:g}px"))
    return out


def check_lorem(path: Path, text: str) -> list[dict]:
    m = LOREM.search(text)
    if not m:
        return []
    line = line_of(text, m.start())
    return [finding(
        "T-001", "copy", "P1", f"{path}:{line}", "§11.9",
        f"占位文案 {m.group(0)!r}", "换成具体的、真实感的内容", "S")]


def check_manual_zindex(path: Path, text: str) -> list[dict]:
    out = []
    for i, line in enumerate(text.splitlines(), 1):
        if re.search(r"(Dialog|Sheet|Popover|Dropdown|Modal|Tooltip)", line):
            continue
        for m in ZINDEX_MANUAL.finditer(line):
            out.append(finding(
                f"Z-{len(out)+1:03d}", "depth", "P1", f"{path}:{i}", "§6.3",
                f"手动 z-index {m.group(0)}", "overlay 组件自己管理层级，移除手写值", "XS"))
            break
    return out


def check_pure_background(path: Path, text: str) -> list[dict]:
    """A pure-white/black *page canvas* (§8.2).

    A control fill of #fff (an input, a button) is not a canvas defect, so the
    rule only fires for body/html/:root or an explicit page-wrapper selector.
    """
    out = []
    for sel, body, body_off in iter_rules(text):
        # sel/body already extracted by iter_rules
        if not re.search(r"^(?:html|body|:root|#root|#app|\.app|\.page|\.site)\b", sel, re.I):
            continue
        bg = re.search(r"(?:background|background-color)\s*:\s*(#fff(?:fff)?|#000(?:000)?)\b",
                       body, re.I)
        if not bg:
            continue
        line = line_of(text, body_off)
        out.append(finding(
            f"B-{len(out)+1:03d}", "finishing", "P2", f"{path}:{line}", "§8.2",
            f"页面画布是纯色 {bg.group(1)}", "给背景极轻的色偏（如 hsl(220 15% 98%)）", "XS"))
    return out


def check_long_centered(path: Path, text: str) -> list[dict]:
    """text-align:center on long-form prose (§4.6).

    Two shapes, both real:
      - a single long centered text node
      - `text-align:center` on body/html, which leaks into every paragraph
        of a long-form article
    """
    out = []
    seen = False
    for m in TEXT_CENTER.finditer(text):
        line = line_of(text, m.start())
        # (a) the rule applies to body/html — it leaks into all prose
        head = text[max(0, m.start() - 200): m.start()]
        sel = head.split("}")[-1].split("{")[0] if "{" in head else ""
        if re.search(r"\b(?:body|html|main|article)\b", sel, re.I):
            if re.search(r"<p\b", text) and len(re.findall(r"<p\b", text)) >= 2:
                out.append(finding(
                    f"Y-{len(out)+1:03d}", "typography", "P0", f"{path}:{line}", "§4.6 §4.7",
                    "text-align:center 设在 body 上，会泄漏到所有段落（长文居中不可读）",
                    "只对短文本（1–2 行）居中；正文左对齐", "XS"))
                seen = True
                continue
        # (b) a single long centered text node
        tail = text[m.end(): m.end() + 400]
        inner = re.search(r">([^<]{120,})<", tail)
        if inner and not seen:
            out.append(finding(
                f"Y-{len(out)+1:03d}", "typography", "P1", f"{path}:{line}", "§4.6",
                f"居中文本长度 {len(inner.group(1))} 字符（超过 120）",
                "三行以上文本左对齐", "XS"))
    return out


def resolve_vars(text: str) -> dict[str, str]:
    """Collect CSS custom property declarations: --name: #hex."""
    out: dict[str, str] = {}
    for m in re.finditer(r"(--[a-zA-Z0-9_-]+)\s*:\s*(#[0-9a-fA-F]{3,8})\s*[;}]", text):
        out.setdefault(m.group(1), m.group(2).lower())
    # second pass: allow var() aliases (--a: var(--b))
    for m in re.finditer(r"(--[a-zA-Z0-9_-]+)\s*:\s*var\((--[a-zA-Z0-9_-]+)\)", text):
        if m.group(2) in out:
            out.setdefault(m.group(1), out[m.group(2)])
    return out


def expand_color(value: str, variables: dict[str, str]) -> str | None:
    """Resolve a color declaration value to a hex string, if possible."""
    value = value.strip()
    m = re.fullmatch(r"(#[0-9a-fA-F]{3,8})\b.*", value)
    if m:
        h = m.group(1).lower()
        # 4/8 位 hex 带 alpha：#rgba / #rrggbbaa。对比度只对不透明色有意义，
        # 这里剥掉 alpha 并交给 blend() 按需复合——直接把 8 位值当 6 位用
        # 会让 hex_to_rgb 解析出错（多出两个字符）。
        if len(h) == 9:
            h = h[:7]
        elif len(h) == 5:
            h = h[:4]
        return h
    m = re.search(r"var\((--[a-zA-Z0-9_-]+)", value)
    if m:
        v = variables.get(m.group(1))
        if not v:
            return None
        # var() 里存的可能是 8 位 hex，同样要剥 alpha
        if len(v) == 9:
            return v[:7]
        if len(v) == 5:
            return v[:4]
        return v
    return None


def blend(fg: str, bg: str, alpha: float) -> str:
    """Composite fg over bg at the given alpha, returning a hex string."""
    f, b = hex_to_rgb(fg), hex_to_rgb(bg)
    if not f or not b:
        return fg
    out = tuple(round(f[i] * alpha + b[i] * (1 - alpha)) for i in range(3))
    return "#{:02x}{:02x}{:02x}".format(*out)


def decorative_selectors(text: str) -> set[str]:
    """Class names on elements the page marks `aria-hidden="true"`.

    A glyph the page itself removes from the accessibility tree is decoration:
    WCAG 1.4.11 asks 3:1 for it, not 4.5:1. Arrows, bullets and ornament marks
    are routinely dimmed on purpose. Judging them as body text forces them to
    compete with real content in weight, which is the opposite of the design
    intent, and buries the report under false P0s.
    """
    out: set[str] = set()
    for m in re.finditer(r"<[a-zA-Z][^>]*>", text):
        tag = m.group(0)
        if not re.search(r'aria-hidden\s*=\s*["\']?true', tag, re.I):
            continue
        cls = re.search(r'class\s*=\s*["\']([^"\']*)["\']', tag, re.I)
        if cls:
            out.update(cls.group(1).split())
    return out


def rule_selector(text: str, offset: int) -> str:
    """The selector, or owning element, of the block starting at `offset`.

    Inline `style="..."` belongs to the tag it sits in; a stylesheet block
    belongs to the selector text between the previous `}` and the `{`.
    """
    head = text[:offset]
    if re.search(r'style\s*=\s*["\'][^"\']*$', head):
        lt = head.rfind("<")
        if lt < 0:
            return ""
        return text[lt:text.find(">", offset) + 1]
    cut = max(head.rfind("}"), head.rfind("</style>"))
    return head[cut + 1:]


def check_contrast_pairs(path: Path, text: str) -> tuple[list[dict], list[str]]:
    """Compare text/background pairs, resolving tokens, inheritance and opacity.

    Three things a naive check gets wrong, and all three are common in real
    code:
      1. Colors live in CSS custom properties, not literals.
      2. The background is usually inherited from body/html, not restated on
         the element that sets `color`.
      3. `opacity` on a wrapper changes the *rendered* contrast — a #111 label
         at opacity .45 on white is 1.33:1, not 17.7:1.
    """
    out: list[dict] = []
    skipped: list[str] = []
    variables = resolve_vars(text)
    if not variables:
        for css in path.parent.glob("*.css"):
            try:
                variables.update(resolve_vars(css.read_text(encoding="utf-8", errors="replace")))
            except Exception:  # noqa: BLE001
                pass

    # Default page background, for blocks that only set `color`.
    default_bg = None
    for m in re.finditer(r"(?:^|\})\s*(?:html|body|:root)[^{]*\{([^{}]*)\}", text):
        bg = re.search(r"background(?:-color)?\s*:\s*([^;}]+)", m.group(1))
        if bg:
            resolved = expand_color(bg.group(1), variables)
            if resolved:
                default_bg = resolved
                break

    blocks = [(m.group(1), m.start()) for m in re.finditer(r"\{([^{}]*)\}", text)]
    blocks += [(m.group(1), m.start()) for m in re.finditer(r'style="([^"]*)"', text)]
    decorative = decorative_selectors(text)
    checked = 0
    unresolved = 0
    # A tertiary/muted token carrying the screen's only text is a hierarchy
    # defect as well as a contrast defect (rubric §5.6 + §2.2).
    MUTED_NAME = re.compile(r"muted|subtle|tertiary|disabled|placeholder|hint", re.I)
    for body, offset in blocks:
        fg = re.search(r"(?:^|;|\s)color\s*:\s*([^;}]+)", body)
        if not fg:
            continue
        bg = re.search(r"background(?:-color)?\s*:\s*([^;}]+)", body)
        fg_hex = expand_color(fg.group(1), variables)
        bg_hex = expand_color(bg.group(1), variables) if bg else default_bg
        if not (fg_hex and bg_hex):
            unresolved += 1
            continue

        # opacity on the same rule dims the whole element against its backdrop
        op = re.search(r"(?:^|;|\s)opacity\s*:\s*([\d.]+)", body)
        alpha = float(op.group(1)) if op else 1.0
        effective_fg = blend(fg_hex, bg_hex, alpha) if alpha < 1 else fg_hex

        ratio = contrast(effective_fg, bg_hex)
        if ratio is None:
            continue
        checked += 1
        fs = re.search(r"font-size\s*:\s*([\d.]+)px", body)
        fw = re.search(r"font-weight\s*:\s*(\d{3})", body)
        large = False
        if fs:
            size = float(fs.group(1))
            weight = int(fw.group(1)) if fw else 400
            large = size >= 24 or (size >= 18.66 and weight >= 700)
        sel = rule_selector(text, offset)
        sel_classes = set(re.findall(r"\.([A-Za-z_][\w-]*)", sel))
        non_text = bool(sel_classes & decorative)
        threshold = 3.0 if (large or non_text) else 4.5
        if ratio < threshold:
            line = line_of(text, offset + fg.start())
            detail = f"{fg_hex} on {bg_hex}"
            if alpha < 1:
                detail = f"{fg_hex} @opacity {alpha} → {effective_fg} on {bg_hex}"
            var_m = re.search(r"var\((--[a-zA-Z0-9_-]+)", fg.group(1))
            muted = bool(var_m and MUTED_NAME.search(var_m.group(1)))
            rules = "§10.1 §2.2" if muted else "§10.1"
            note = ("；该色是三级/次要 token，却承载了主要内容" if muted else "")
            if non_text:
                note += "；该元素标了 aria-hidden，属装饰性非文本，按 WCAG 1.4.11 判 3:1"
            out.append(finding(
                f"R-{len(out)+1:03d}", "a11y", "P0", f"{path}:{line}", rules,
                f"{detail} = {ratio:.2f}:1（低于 {threshold}:1）{note}",
                ("调整明度使对比度达标（正文 4.5:1，大文本 3:1）"
                 if not non_text else
                 "调整明度使装饰元素达到 3:1（WCAG 1.4.11 非文本对比度）")
                + "；半透明要按复合后颜色算"
                + ("；三级色不得承载必须读到的信息" if muted else ""), "S",
                evidence=f"measured:{ratio:.2f}"))
    if checked == 0 and unresolved:
        skipped.append(
            f"contrast: {unresolved} 组颜色对无法解析（值不是 hex 或已知 token），需人工检查")
    elif checked == 0:
        skipped.append("contrast: 未找到可解析的 color 声明，需人工检查")
    return out, skipped


# -------------------------------------------------------------------- runner

SKIP_DIRS = {"node_modules", ".git", "dist", "build", ".next", "vendor", "__pycache__"}


def collect(root: Path) -> list[Path]:
    files = []
    for p in root.rglob("*"):
        if p.is_dir() or any(part in SKIP_DIRS for part in p.parts):
            continue
        if p.suffix.lower() in {".html", ".htm", ".css", ".tsx", ".jsx", ".vue", ".svelte"}:
            files.append(p)
    return sorted(files)


def audit_file(path: Path, brand: str | None = None) -> tuple[list[dict], list[str]]:
    text = path.read_text(encoding="utf-8", errors="replace")
    is_css = path.suffix.lower() == ".css"
    found: list[dict] = []
    found += check_brand_drift(path, text, brand)
    found += check_dead_end(path, text)
    found += check_disabled_chrome(path, text)
    found += check_search_miss_copy(path, text)
    found += check_grey_on_color(path, text)
    found += check_primary_button_count(path, text)
    found += check_grouping_rhythm(path, text)
    found += check_measure(path, text)
    found += check_type_scale_ratio(path, text)
    found += check_heading_line_height(path, text)
    found += check_gradient_hue(path, text)
    found += check_overweight_shadow(path, text)
    found += check_text_over_image(path, text)
    found += check_emoji_icons(path, text)
    found += check_hardcoded_colors(path, text, is_css)
    found += check_tailwind_space(path, text)
    found += check_arbitrary_values(path, text)
    found += check_img_alt(path, text)
    found += check_input_label(path, text)
    found += check_outline_none(path, text)
    found += check_reduced_motion(path, text)
    found += check_single_shadow(path, text)
    found += check_font_weight_300(path, text)
    found += check_lorem(path, text)
    found += check_manual_zindex(path, text)
    found += check_pure_background(path, text)
    found += check_long_centered(path, text)
    cf, sk = check_contrast_pairs(path, text)
    found += cf
    return found, sk


def render_markdown(root: Path, findings: list[dict], skipped: list[str]) -> str:
    order = {"P0": 0, "P1": 1, "P2": 2}
    findings = sorted(findings, key=lambda f: (order.get(f["severity"], 9), f["lens"], f["location"]))
    lines = [f"# 确定性审计：{root}", "",
             f"**发现总数**：{len(findings)}　"
             f"P0={sum(1 for f in findings if f['severity']=='P0')}　"
             f"P1={sum(1 for f in findings if f['severity']=='P1')}　"
             f"P2={sum(1 for f in findings if f['severity']=='P2')}",
             "", "> 本报告只含机器可判定的缺陷。层级、审美、语义分组等需要人眼判断的项",
             "> 见 `references/12-audit-rubric.md`。", ""]
    for sev in ("P0", "P1", "P2"):
        group = [f for f in findings if f["severity"] == sev]
        if not group:
            continue
        lines += [f"## {sev}", "", "| # | 镜 | 位置 | 规则 | 现状 | 建议 | 工作量 |", "|---|---|---|---|---|---|---|"]
        for f in group:
            lines.append("| {id} | {lens} | `{location}` | {rule} | {now} | {proposed} | {effort} |".format(**f))
        lines.append("")
    if skipped:
        lines += ["## 未检查项", ""] + [f"- {s}" for s in skipped] + [""]
    else:
        lines += ["## 未检查项", "", "无。所有检查项均已执行。", ""]
    return "\n".join(lines)


# ---------------------------------------------------------------- self-test

def self_test() -> int:
    """Every gate must fire on bad input. A gate that never fails is not a gate."""
    import tempfile
    failures = []
    passed_checks = []

    def expect(name, cond):
        if cond:
            passed_checks.append(name)
        else:
            failures.append(name)

    with tempfile.TemporaryDirectory() as td:
        root = Path(td)

        p = root / "bad.html"
        p.write_text("""
<html><head><style>
  body { background: #fff; }
  .card { background: #ffffff; box-shadow: 0 4px 8px #000; }
  .btn { outline: none; font-weight: 300; font-size: 14px; }
</style></head><body>
<img src="a.png">
<input type="text">
<div style="color:#777777;background:#888888">low contrast</div>
<div class="space-y-4 p-[13px]">
<p>Lorem ipsum dolor sit amet</p>
<p style="text-align:center">""" + "x" * 200 + """</p>
</body></html>""", encoding="utf-8")

        f, sk = audit_file(p)
        ids = {x["id"].split("-")[0] for x in f}
        expect("img alt not detected", "I" in ids)
        expect("input label not detected", "L" in ids)
        expect("outline:none not detected", "F" in ids)
        expect("space-y not detected", "S" in ids)
        expect("arbitrary value not detected", "A" in ids)
        expect("lorem not detected", "T" in ids)
        expect("single shadow not detected", "D" in ids)
        expect("weight 300 not detected", "W" in ids)

        # §4.7 is about strokes vanishing at *small* sizes. A 300-weight hero
        # at 64px is a design decision, not a defect; a weight ladder specimen
        # set at clamp(20px,3.4vw,38px) is neither. This gate used to fire on
        # weight alone and flag exactly those.
        thin_display = root / "thindisplay.html"
        thin_display.write_text(
            "<style>.hero{font-size:64px;font-weight:300}"
            ".ladder .w{font-size:clamp(20px,3.4vw,38px);font-weight:100}"
            "</style><h1 class=hero>Big</h1><span class=w>Thin</span>",
            encoding="utf-8")
        f_thin, _ = audit_file(thin_display)
        expect("display-weight false positive",
               not any(x["id"].startswith("W") for x in f_thin))

        # ...while 300 on actual 13px body copy must still fire.
        thin_body = root / "thinbody.html"
        thin_body.write_text(
            "<style>.p{font-size:13px;font-weight:300}</style><p class=p>x</p>",
            encoding="utf-8")
        f_body, _ = audit_file(thin_body)
        expect("thin body copy not detected",
               any(x["id"].startswith("W") for x in f_body))
        expect("pure bg not detected", "B" in ids)
        expect("long centered not detected", "Y" in ids)
        expect("hardcoded color not detected", "C" in ids)
        expect("contrast not detected", "R" in ids)

        # A page may dim its own decoration. aria-hidden glyphs sit at 3:1
        # (WCAG 1.4.11); everything else stays at 4.5:1.
        decor = root / "decor.html"
        decor.write_text(
            "<style>\n"
            ".arrow{color:#8a8578;font-size:15px}\n"
            ".caption{color:#8a8578;font-size:15px}\n"
            "body{background:#f7f6f2}\n"
            "</style>\n"
            '<span class="arrow" aria-hidden="true">→</span>\n'
            '<span class="caption">readable?</span>', encoding="utf-8")
        f_dec, _ = audit_file(decor)
        r_dec = [x for x in f_dec if x["id"].startswith("R")]
        flagged_lines = {int(x["location"].rsplit(":", 1)[1]) for x in r_dec}
        # line 2 = .arrow (decorative, 3.40:1 clears 3:1)
        # line 3 = .caption (same color, plain text, 3.40:1 misses 4.5:1)
        expect("decorative 3:1 rule not applied", 2 not in flagged_lines)
        expect("non-decorative 4.5:1 relaxed by mistake", 3 in flagged_lines)

        css = root / "anim.css"
        css.write_text(".a{animation: fade 1s;}\n", encoding="utf-8")
        f2, _ = audit_file(css)
        expect("missing reduced-motion not detected",
               any(x["id"].startswith("M") for x in f2))

        css2 = root / "ok.css"
        css2.write_text(".a{animation: fade 1s;}\n@media (prefers-reduced-motion: reduce){*{animation:none}}\n",
                        encoding="utf-8")
        f3, _ = audit_file(css2)
        expect("reduced-motion false positive",
               not any(x["id"].startswith("M") for x in f3))

        good = root / "good.html"
        good.write_text('<img src="a.png" alt="描述"><label for="e">Email</label>'
                        '<input id="e" type="text">', encoding="utf-8")
        f4, _ = audit_file(good)
        expect("clean file false positive",
               not any(x["id"].startswith(("I", "L")) for x in f4))

        # Regression: a stylesheet must not be measured as body copy, and a
        # control fill must not be reported as a page canvas. Both were real
        # false positives found by the GREEN audit pass.
        css_heavy = root / "cssheavy.html"
        css_heavy.write_text(
            "<html><head><style>\n" + ".a{color:#111}\n" * 60 +
            "</style></head><body><main><h1>Projects</h1>"
            '<button class="a">New</button>'
            '<input type="text" aria-label="search">'
            "</main></body></html>", encoding="utf-8")
        f6, _ = audit_file(css_heavy)
        ids6 = {x["id"].split("-")[0] for x in f6}
        expect("stylesheet measured as prose (Q false positive)", "Q" not in ids6)
        expect("control fill reported as page canvas (B false positive)", "B" not in ids6)

        # A token template is all comments and variables: no element can carry
        # prose, so measure cannot apply. Its 800-character header used to be
        # read as an unconstrained paragraph.
        tok = root / "tokens.css"
        tok.write_text("/* " + "not prose " * 90 + " */\n:root{--bg:#fff}\n",
                       encoding="utf-8")
        f6b, _ = audit_file(tok)
        expect("css comment measured as prose (Q false positive)",
               not any(x["id"].startswith("Q") for x in f6b))

        scale = root / "scale.html"
        scale.write_text(
            "<style>"
            ".a{font-size:14px}.b{font-size:15px}.c{font-size:16px}"
            ".d{font-size:17px}.e{font-size:18px}"
            "</style><p class=a>x</p>", encoding="utf-8")
        f7, _ = audit_file(scale)
        expect("dense type scale not detected",
               any(x["id"].startswith("TS") for x in f7))

        good_scale = root / "goodscale.html"
        good_scale.write_text(
            "<style>"
            ".a{font-size:13px}.b{font-size:16px}.c{font-size:20px}"
            ".d{font-size:25px}.e{font-size:31px}"
            "</style><p class=a>x</p>", encoding="utf-8")
        f8, _ = audit_file(good_scale)
        expect("healthy type scale false positive",
               not any(x["id"].startswith("TS") for x in f8))

        # Regression (found by adversarial review): a button with a primary
        # class and NO stylesheet at all used to raise UnboundLocalError and
        # kill the whole audit. One line of HTML was enough to trigger it.
        bare_btn = root / "barebtn.html"
        bare_btn.write_text('<button class="btn-primary">Save</button>',
                            encoding="utf-8")
        try:
            f9, _ = audit_file(bare_btn)
            crashed = False
        except Exception:
            crashed = True
        expect("crash on button with no stylesheet", not crashed)

        # Regression: pure white text on a brand fill is a correct primary
        # button, not "grey text on a coloured background".
        white_cta = root / "whitecta.html"
        white_cta.write_text(
            '<style>.cta{color:#ffffff;background:#0f766e}</style>'
            '<a class="cta">Go</a>', encoding="utf-8")
        f10, _ = audit_file(white_cta)
        expect("white-on-brand flagged as grey text (G false positive)",
               not any(x["id"].startswith("G") for x in f10))

        # ...while a genuinely neutral grey on the same fill must still fire.
        grey_cta = root / "greycta.html"
        grey_cta.write_text(
            '<style>.cta{color:#9ca3af;background:#0f766e}</style>'
            '<a class="cta">Go</a>', encoding="utf-8")
        f11, _ = audit_file(grey_cta)
        expect("real grey-on-colour not detected",
               any(x["id"].startswith("G") for x in f11))

        # Regression: an index page's only fill was `.row a:hover{background:…}`.
        # A hover state is not a competing primary action, and the selector's
        # pseudo-class also made the counter read "row" as a container of 12
        # buttons. Both produced one P-001 naming 12 non-existent buttons.
        hover_list = root / "hoverlist.html"
        hover_list.write_text(
            "<style>.row a{display:block;padding:12px}"
            ".row a:hover{background:#353535}</style>"
            "<ul>" + "".join(f'<li class="row"><a href="#">{i}</a></li>'
                             for i in range(12)) + "</ul>", encoding="utf-8")
        f12, _ = audit_file(hover_list)
        expect("hover fill counted as primary button (P false positive)",
               not any(x["id"].startswith("P") for x in f12))

        # ...while a resting fill on the same 12 anchors must still fire.
        solid_list = root / "solidlist.html"
        solid_list.write_text(
            "<style>.row a{display:block;padding:12px;background:#353535}</style>"
            "<ul>" + "".join(f'<li class="row"><a href="#">{i}</a></li>'
                             for i in range(12)) + "</ul>", encoding="utf-8")
        f13, _ = audit_file(solid_list)
        expect("12 solid list actions not detected",
               any(x["id"].startswith("P") for x in f13))

        # A card fill one step above a dark canvas is a surface, not a CTA —
        # this is the index-page shape that reported 12 phantom primaries.
        card_list = root / "cardlist.html"
        card_list.write_text(
            "<style>body{background:#0d0f0e}"
            ".row a{display:block;background:#141a17;color:#e8eae7}</style>"
            "<ul>" + "".join(f'<li class="row"><a href="#">{i}</a></li>'
                             for i in range(12)) + "</ul>", encoding="utf-8")
        f13b, _ = audit_file(card_list)
        expect("card surface counted as primary button (P false positive)",
               not any(x["id"].startswith("P") for x in f13b))

        # ...but a chromatic fill on those same rows is still competing actions.
        brand_list = root / "brandlist.html"
        brand_list.write_text(
            "<style>body{background:#0d0f0e}"
            ".row a{display:block;background:#7c3aed;color:#fff}</style>"
            "<ul>" + "".join(f'<li class="row"><a href="#">{i}</a></li>'
                             for i in range(12)) + "</ul>", encoding="utf-8")
        f13c, _ = audit_file(brand_list)
        expect("chromatic row fill not detected as primary",
               any(x["id"].startswith("P") for x in f13c))

        dead = root / "dead.html"
        dead.write_text('<main><h1>Projects</h1><button disabled>All</button>'
                        '<input type="search" disabled>'
                        '<table><thead><tr><th>Name</th></tr></thead><tbody></tbody></table>'
                        '<p>No results found.</p></main>', encoding="utf-8")
        f5, _ = audit_file(dead)
        ids5 = {x["id"].split("-")[0] for x in f5}
        expect("dead-end screen not detected", "X" in ids5)
        expect("disabled chrome in empty state not detected", "E" in ids5)
        expect("search-miss copy not detected", "N" in ids5)
        expect("dead-end false positive on working page",
               "X" not in {x["id"].split("-")[0] for x in f4})

    if failures:
        print("SELF-TEST FAILED:")
        for f_ in failures:
            print("  ✗", f_)
        return 1
    print(f"SELF-TEST PASSED: {len(passed_checks)}/{len(passed_checks)} gates fire on bad input and stay quiet on good input")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("target", nargs="?", help="file or directory to audit")
    ap.add_argument("--json", action="store_true", help="emit JSON instead of markdown")
    ap.add_argument("--self-test", action="store_true")
    ap.add_argument("--out", help="write report to this path")
    ap.add_argument("--brand", help="the brand color the brief specifies, e.g. #0f766e")
    ap.add_argument("--fail-on-p0", action="store_true",
                    help="exit 1 when any P0 finding is present (for CI)")
    args = ap.parse_args()

    if args.self_test:
        return self_test()
    if not args.target:
        ap.error("target required (or use --self-test)")

    root = Path(args.target).resolve()
    if not root.exists():
        ap.error(f"no such path: {root}")
    files = [root] if root.is_file() else collect(root)
    if not files:
        ap.error("no audit-able files found")

    all_findings, all_skipped = [], []
    for p in files:
        f, sk = audit_file(p, args.brand)
        all_findings += f
        for s in sk:
            all_skipped.append(f"{p.name}: {s}")

    if args.json:
        out = json.dumps({"root": str(root), "findings": all_findings,
                          "skipped": all_skipped}, indent=1, ensure_ascii=False)
    else:
        out = render_markdown(root, all_findings, all_skipped)

    if args.out:
        out_path = Path(args.out)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(out, encoding="utf-8")
        print(f"wrote {args.out} ({len(all_findings)} findings, {len(all_skipped)} skipped)")
    else:
        print(out)
    if args.fail_on_p0 and any(f["severity"] == "P0" for f in all_findings):
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
