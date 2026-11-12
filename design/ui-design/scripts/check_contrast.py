#!/usr/bin/env python3
"""
Check color pairs against WCAG contrast minimums (§5.6), and report the
per-hue perceived brightness from §5.4.1.

  §5.6    4.5:1 for normal text (under ~18px), 3:1 for large text
  §5.4.1  perceived brightness = sqrt(0.299r^2 + 0.587g^2 + 0.114b^2) / 255

Stdlib only. No dependencies.

  python3 check_contrast.py --pair '#ffffff' '#bd4d28'
  python3 check_contrast.py --pair '#6b7280' '#ffffff' --size large
  python3 check_contrast.py --matrix tokens.json
  python3 check_contrast.py --brightness '#eab308' '#bd4d28'

Exit status is 1 if any checked pair fails, so it can gate a build.
"""
from __future__ import annotations
import argparse, json, math, re, sys

AA_NORMAL, AA_LARGE = 4.5, 3.0


def hex_to_rgb(s: str) -> tuple[int, int, int]:
    s = s.strip().lstrip('#')
    if len(s) == 3:
        s = ''.join(c * 2 for c in s)
    if len(s) != 6:
        raise ValueError(f'not a hex color: {s}')
    return tuple(int(s[i:i + 2], 16) for i in (0, 2, 4))


def parse_color(s: str) -> tuple[int, int, int, float]:
    """Parse #rgb/#rrggbb or rgb()/rgba() into (r, g, b, alpha)."""
    value = s.strip()
    if value.startswith('#'):
        return (*hex_to_rgb(value), 1.0)
    match = re.fullmatch(r'rgba?\(([^)]+)\)', value, re.I)
    if not match:
        raise ValueError(f'not a color: {s}')
    parts = [p.strip() for p in re.split(r'[,\s/]+', match.group(1)) if p.strip()]
    if len(parts) not in (3, 4):
        raise ValueError(f'not a color: {s}')
    channels = []
    for part in parts[:3]:
        if part.endswith('%'):
            channels.append(round(float(part[:-1]) * 2.55))
        else:
            channels.append(round(float(part)))
    alpha = float(parts[3]) if len(parts) == 4 else 1.0
    if alpha > 1:
        alpha /= 255.0
    return (channels[0], channels[1], channels[2], max(0.0, min(1.0, alpha)))


def composite(fg: tuple[int, int, int, float], bg: tuple[int, int, int, float]) -> tuple[int, int, int, float]:
    a = fg[3]
    return (
        round(fg[0] * a + bg[0] * (1 - a)),
        round(fg[1] * a + bg[1] * (1 - a)),
        round(fg[2] * a + bg[2] * (1 - a)),
        1.0,
    )


def flatten(color: tuple[int, int, int, float], base: tuple[int, int, int, float] = (255, 255, 255, 1.0)):
    return color if color[3] >= 1.0 else composite(color, base)


def relative_luminance(rgb: tuple[int, int, int]) -> float:
    """WCAG 2.x relative luminance. Note this is not the book's formula --
    it is the standard the 4.5:1 threshold is defined against."""
    def lin(c: int) -> float:
        c /= 255.0
        return c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4
    r, g, b = (lin(c) for c in rgb)
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def contrast_ratio(a: str, b: str) -> float:
    bg = flatten(parse_color(b))
    fg = flatten(parse_color(a), bg)
    la, lb = relative_luminance(fg[:3]), relative_luminance(bg[:3])
    hi, lo = max(la, lb), min(la, lb)
    return (hi + 0.05) / (lo + 0.05)


def perceived_brightness(c: str) -> float:
    """§5.4.1. Distinct from WCAG luminance: this is the book's model for why
    yellow reads lighter than blue at identical HSL lightness."""
    r, g, b = flatten(parse_color(c))[:3]
    return math.sqrt(0.299 * r * r + 0.587 * g * g + 0.114 * b * b) / 255


def verdict(ratio: float, size: str) -> tuple[bool, str]:
    need = AA_LARGE if size == 'large' else AA_NORMAL
    ok = ratio >= need
    return ok, f'{"PASS" if ok else "FAIL"}  {ratio:.2f}:1  (needs {need}:1, {size} text)'


def advise(fg: str, bg: str, size: str) -> list[str]:
    """Point at the book's two techniques rather than just saying 'darken it'."""
    tips = []
    if perceived_brightness(bg) < 0.45:
        tips.append('§5.6.1 flip the contrast: dark colored text on a light tint of '
                    'the same color, instead of light text on a dark fill')
        tips.append('§5.6.2 or rotate the text hue toward cyan/magenta/yellow to gain '
                    'contrast without moving toward white (cap 20-30 deg)')
    else:
        tips.append('§5.6.1 darken the foreground, or move it further down its ramp')
    if size == 'normal':
        tips.append('§5.6 if this text is 18px+, it only needs 3:1 -- re-check with '
                    '--size large')
    return tips


def check_matrix(path: str, size: str) -> int:
    """Check every foreground/background pair declared in a token file.

    Expects: {"pairs": [{"fg": "...", "bg": "...", "name": "...",
                          "size": "normal|large"}, ...]}
    """
    try:
        with open(path, encoding='utf-8') as handle:
            data = json.load(handle)
    except FileNotFoundError:
        print(f'{path}: file not found', file=sys.stderr)
        return 2
    except json.JSONDecodeError as exc:
        print(f'{path}: invalid JSON ({exc})', file=sys.stderr)
        return 2
    pairs = data.get('pairs')
    if not pairs:
        print(f'{path}: no "pairs" array found.\n'
              'Declare the combinations that actually occur in the UI -- §5.6 says '
              'verify across the token matrix, not per component.', file=sys.stderr)
        return 2
    failures = 0
    width = max((len(p.get('name', '')) for p in pairs), default=4)
    for p in pairs:
        s = p.get('size', size)
        r = contrast_ratio(p['fg'], p['bg'])
        ok, line = verdict(r, s)
        failures += not ok
        print(f'{p.get("name", ""):<{width}}  {p["fg"]} on {p["bg"]}  {line}')
        if not ok:
            for t in advise(p['fg'], p['bg'], s):
                print(f'{"":<{width}}    -> {t}')
    print(f'\n{len(pairs) - failures}/{len(pairs)} pass')
    return 1 if failures else 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--pair', nargs=2, metavar=('FG', 'BG'), help='check one pair')
    ap.add_argument('--matrix', metavar='TOKENS.JSON', help='check a declared pair list')
    ap.add_argument('--brightness', nargs='+', metavar='COLOR',
                    help='report §5.4.1 perceived brightness')
    ap.add_argument('--size', choices=('normal', 'large'), default='normal',
                    help='normal = under ~18px (4.5:1); large = 3:1')
    a = ap.parse_args()

    if a.brightness:
        for c in a.brightness:
            try:
                rgb = parse_color(c)
            except ValueError as exc:
                ap.error(str(exc))
            print(f'{c}  perceived brightness {perceived_brightness(c):.3f}  '
                  f'wcag luminance {relative_luminance(flatten(rgb)[:3]):.3f}')
        return 0

    if a.pair:
        fg, bg = a.pair
        try:
            ok, line = verdict(contrast_ratio(fg, bg), a.size)
        except ValueError as exc:
            ap.error(str(exc))
        print(f'{fg} on {bg}   {line}')
        if not ok:
            for t in advise(fg, bg, a.size):
                print(f'  -> {t}')
        return 0 if ok else 1

    if a.matrix:
        return check_matrix(a.matrix, a.size)

    ap.error('pass --pair, --matrix, or --brightness')


if __name__ == '__main__':
    raise SystemExit(main())
