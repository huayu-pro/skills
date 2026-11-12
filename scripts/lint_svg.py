#!/usr/bin/env python3
"""科研架构图 SVG 静态质检。

用法:
    python3 scripts/lint_svg.py <svg文件或目录> [--json] [--grid] [--skip CAT,...]

检查分三级：
    FAIL  结构性错误，必须修（XML 非法、marker 未定义、零长度箭头、文字出画布、白底未盖满画布、缺字号、分组贴边<8px）
    WARN  大概率是缺陷，需目检确认（文字出框、行距过挤、文字互压、箭头穿框、同层不齐、框重叠、分组贴边<12px、图题入图）
    INFO  提示性（调色板外颜色、未使用 marker、非 8px 网格）

退出码：0 无问题，1 有 FAIL，2 仅有 WARN。批量调用可直接看退出码决定是否交付。
这是估算式检查，WARN 不是判决——最终以渲染出的 PNG 目检为准。
"""
from __future__ import annotations

import argparse
import json
import math
import re
import sys
import unicodedata
import xml.etree.ElementTree as ET
from pathlib import Path

SVG_NS = "http://www.w3.org/2000/svg"

PALETTE = {
    "#2F6BB0", "#EEF4FB", "#4A86C5", "#F4F8FD", "#E8833A", "#FDF3EA",
    "#3E9B6C", "#EDF7F2", "#C94F44", "#FBF0EF", "#8A94A6", "#F3F5F8",
    "#5A6B7E", "#1A1A1A", "#666666", "#7B5EA7", "#7FA8D4", "#FFFFFF",
    "#4472C4", "#D9E2F3", "#ED7D31", "#FBE5D6", "#70AD47", "#E2EFDA",
    "#000000", "#333333",
}

LINE_PITCH_RATIO = 1.4      # 行距低于 1.4×字号判为过挤
TEXT_WIDTH_RATIO = 0.90     # 文字宽度超过框宽 90% 判为出框风险
GROUP_PAD_WARN = 12         # 分组框与成员框间距建议值（低于判黄）
GROUP_PAD_MIN = 8           # 硬下限（低于判红）
OVERLAP_RATIO = 0.30        # 矩形重叠超过 30% 才报
TEXT_OVERLAP_RATIO = 0.30   # 两个文字包围盒重叠超过 30% 判互压
GRID = 8


def tag(el) -> str:
    return el.tag.split("}")[-1] if isinstance(el.tag, str) else ""


def num(v, default=0.0) -> float:
    if v is None:
        return default
    m = re.match(r"^\s*(-?[\d.]+)", str(v))
    return float(m.group(1)) if m else default


def text_width(s: str, fs: float) -> float:
    """按字形宽度估算文本宽度（Noto Sans CJK 实测校准）。

    全角=1.0×字号；大写字母≈0.72×（W/M≈0.9×）；小写与数字≈0.55×；
    空格 0.3×；歧义宽字符（·、±、希腊字母等）出现在中文字串里时按全角算
    ——CJK 字体把它们排成全宽，按半角估会系统性偏小（lint 与文档共用本公式）。
    """
    has_cjk = any(unicodedata.east_asian_width(c) in ("W", "F") for c in s)
    w = 0.0
    for ch in s:
        ea = unicodedata.east_asian_width(ch)
        if ea in ("W", "F"):
            w += 1.0
        elif ch == " ":
            w += 0.30
        elif ch in "WM":
            w += 0.90
        elif ch.isalpha() and ch.isupper():
            w += 0.72
        elif ch.isdigit() or ch.isalpha():
            w += 0.55
        elif ea == "A":
            w += 1.0 if has_cjk else 0.5
        else:
            w += 0.40
    return w * fs


class Box:
    __slots__ = ("x", "y", "w", "h", "fill", "stroke", "rx", "id", "dashed")

    def __init__(self, x, y, w, h, fill, stroke, rx, eid, dashed):
        self.x, self.y, self.w, self.h = x, y, w, h
        self.fill, self.stroke, self.rx, self.id, self.dashed = fill, stroke, rx, eid, dashed

    @property
    def x2(self):
        return self.x + self.w

    @property
    def y2(self):
        return self.y + self.h

    def contains(self, px, py, inset=0.0):
        return (self.x + inset <= px <= self.x2 - inset
                and self.y + inset <= py <= self.y2 - inset)


class Text:
    __slots__ = ("x", "y", "fs", "anchor", "lines", "eid", "fill", "rotated")

    def __init__(self, x, y, fs, anchor, lines, eid, fill, rotated=False):
        self.x, self.y, self.fs, self.anchor = x, y, fs, anchor
        self.lines, self.eid, self.fill = lines, eid, fill
        self.rotated = rotated


class Seg:
    __slots__ = ("x1", "y1", "x2", "y2", "marker", "eid", "single")

    def __init__(self, x1, y1, x2, y2, marker, eid, single=True):
        self.x1, self.y1, self.x2, self.y2 = x1, y1, x2, y2
        self.marker, self.eid, self.single = marker, eid, single


PATH_TOKEN = re.compile(r"[MmLlHhVvCcSsQqTtAaZz]|-?\d*\.?\d+(?:[eE][-+]?\d+)?")


def path_segments(d: str):
    """只解析 M/L/H/V（含相对指令）为折线段，曲线/圆弧不参与几何判定。"""
    toks = PATH_TOKEN.findall(d or "")
    segs, pts = [], []
    cx = cy = sx = sy = 0.0
    cmd = None
    i = 0
    while i < len(toks):
        t = toks[i]
        if re.fullmatch(r"[A-Za-z]", t):
            cmd = t
            i += 1
            if cmd in "Zz":
                if pts and (cx, cy) != (sx, sy):
                    segs.append((cx, cy, sx, sy))
                cx, cy = sx, sy
            continue
        rel = cmd.islower() if cmd else False
        c = cmd.upper() if cmd else "M"
        try:
            if c == "M":
                x, y = float(toks[i]), float(toks[i + 1]); i += 2
                cx, cy = (cx + x, cy + y) if rel else (x, y)
                sx, sy = cx, cy
                cmd = "l" if rel else "L"
            elif c == "L":
                x, y = float(toks[i]), float(toks[i + 1]); i += 2
                nx, ny = (cx + x, cy + y) if rel else (x, y)
                segs.append((cx, cy, nx, ny)); cx, cy = nx, ny
            elif c == "H":
                nx = cx + float(toks[i]) if rel else float(toks[i]); i += 1
                segs.append((cx, cy, nx, cy)); cx = nx
            elif c == "V":
                ny = cy + float(toks[i]) if rel else float(toks[i]); i += 1
                segs.append((cx, cy, cx, ny)); cy = ny
            elif c == "C":
                i += 6
            elif c == "S" or c == "Q":
                i += 4
            elif c == "T":
                i += 2
            elif c == "A":
                i += 7
            else:
                i += 1
        except (IndexError, ValueError):
            break
    return segs


class Linter:
    def __init__(self, path: Path, skip: set[str]):
        self.path = path
        self.skip = skip
        self.fail: list[str] = []
        self.warn: list[str] = []
        self.info: list[str] = []
        self.boxes: list[Box] = []
        self.texts: list[Text] = []
        self.segs: list[Seg] = []
        self.markers: set[str] = set()
        self.used_markers: set[str] = set()
        self.colors: set[str] = set()
        self._fonts: set[str] = set()

    # ---------- 解析 ----------
    def parse(self):
        try:
            tree = ET.parse(self.path)
        except ET.ParseError as e:
            self.fail.append(f"XML 非法：{e}")
            return None
        root = tree.getroot()
        # viewBox 可以带偏移（裁画布后常见），判定边界要用绝对坐标；合法分隔含逗号
        self.x0 = self.y0 = 0.0
        self.W = self.H = None
        vb = [p for p in re.split(r"[,\s]+", (root.get("viewBox") or "").strip()) if p]
        w_attr, h_attr = (root.get("width") or "").strip(), (root.get("height") or "").strip()
        if len(vb) == 4:
            try:
                self.x0, self.y0, self.W, self.H = (float(v) for v in vb)
            except ValueError:
                pass
        elif (re.fullmatch(r"-?[\d.]+(px)?", w_attr)
                and re.fullmatch(r"-?[\d.]+(px)?", h_attr)):
            self.W = float(re.match(r"-?[\d.]+", w_attr).group())
            self.H = float(re.match(r"-?[\d.]+", h_attr).group())
        if self.W is None:
            self.warn.append("画布尺寸含百分比/单位或 viewBox 非法，出画布/白底类检查跳过")
        self.root = root
        self._walk(root, {"font-family": None, "transform": False})
        return root

    def _walk(self, el, inherited):
        t = tag(el)
        eid = el.get("id") or ""
        if el.get("font-family"):
            self._fonts.add(el.get("font-family"))
        fs = el.get("font-size")
        cur = dict(inherited)
        cur["transform"] = bool(el.get("transform")) or inherited.get("transform", False)
        if fs:
            cur["font-size"] = num(fs)
        for attr in ("fill", "stroke"):
            v = el.get(attr)
            if v and v.startswith("#"):
                self.colors.add(v.upper())

        if t == "marker":
            if eid:
                self.markers.add(eid)
        for attr in ("marker-start", "marker-mid", "marker-end"):
            v = el.get(attr) or ""
            m = re.search(r"url\(\s*['\"]?#([^'\"\)\s]+)", v)
            if m:
                self.used_markers.add(m.group(1))

        if t == "rect":
            self.boxes.append(Box(num(el.get("x")), num(el.get("y")), num(el.get("width")),
                                  num(el.get("height")), el.get("fill"), el.get("stroke"),
                                  num(el.get("rx")), eid, bool(el.get("stroke-dasharray"))))
        elif t in ("circle", "ellipse"):
            cx, cy = num(el.get("cx")), num(el.get("cy"))
            rx = num(el.get("r")) or num(el.get("rx"))
            ry = num(el.get("r")) or num(el.get("ry"))
            self.boxes.append(Box(cx - rx, cy - ry, 2 * rx, 2 * ry, el.get("fill"),
                                  el.get("stroke"), rx, eid, bool(el.get("stroke-dasharray"))))
        elif t == "line":
            self.segs.append(Seg(num(el.get("x1")), num(el.get("y1")), num(el.get("x2")),
                                 num(el.get("y2")), self._marker(el), eid))
        elif t == "path":
            segs = path_segments(el.get("d") or "")
            # 多段折线里的退化段（如 H 后接 V 的同点）不是缺陷，只有整条路径零长才是
            for (x1, y1, x2, y2) in segs:
                self.segs.append(Seg(x1, y1, x2, y2, self._marker(el), eid,
                                     single=len(segs) == 1))
        elif t == "polyline" or t == "polygon":
            pts = [float(v) for v in re.findall(r"-?\d*\.?\d+", el.get("points") or "")]
            n_seg = max(1, (len(pts) - 2) // 2)
            for i in range(0, len(pts) - 3, 2):
                self.segs.append(Seg(pts[i], pts[i + 1], pts[i + 2], pts[i + 3],
                                     self._marker(el), eid, single=n_seg == 1))
        elif t == "text":
            self._read_text(el, cur)

        for ch in el:
            self._walk(ch, cur)

    @staticmethod
    def _marker(el) -> str | None:
        v = el.get("marker-end") or el.get("marker-start") or ""
        m = re.search(r"url\(\s*['\"]?#([^'\"\)\s]+)", v)
        return m.group(1) if m else None

    def _read_text(self, el, inherited):
        # font-size 可以写在 text 上，也可以逐 tspan 写（多字号混排时的常见写法）
        child_fs = next((num(s.get("font-size")) for s in el
                         if tag(s) == "tspan" and s.get("font-size")), 0)
        fs = num(el.get("font-size"), child_fs or inherited.get("font-size") or 0)
        content = "".join(el.itertext()).strip()
        if not fs:
            if content:
                self.fail.append(f"<text> 缺 font-size（id={el.get('id') or '无'}）：{content[:16]}")
            fs = 13.0
        anchor = el.get("text-anchor") or "start"
        x, y = num(el.get("x")), num(el.get("y"))
        lines = []  # (x, y, 文本, 该行字号)
        if (el.text or "").strip():
            lines.append((x, y, el.text.strip(), fs))
        # tspan 只写 dy（相对上一行）时必须累加，否则整段被当成同一基线；
        # 无 x/y/dy 的行内 tspan（多字号混排接排）并入当前行，不新开行
        cur_x, cur_y = x, y
        for s in el:
            if tag(s) != "tspan":
                continue
            seg = "".join(s.itertext()).strip()
            if not seg:
                continue
            sfs = num(s.get("font-size"), fs)
            if s.get("y") is not None:
                cur_y = num(s.get("y"))
            elif s.get("dy") is not None:
                cur_y += num(s.get("dy"))
            if s.get("x") is not None or s.get("y") is not None or s.get("dy") is not None:
                if s.get("x") is not None:
                    cur_x = num(s.get("x"))
                lines.append((cur_x, cur_y, seg, sfs))
            elif lines:
                lx, ly, prev, pfs = lines[-1]
                lines[-1] = (lx, ly, prev + seg, max(pfs, sfs))
            else:
                lines.append((cur_x, cur_y, seg, sfs))
        if not lines:
            lines.append((x, y, "".join(el.itertext()).strip(), fs))
        for (lx, ly, s, lfs) in lines:
            self.texts.append(Text(lx, ly, lfs, anchor, [(lx, ly, s)], el.get("id") or "",
                                   el.get("fill"), inherited.get("transform", False)
                                   or bool(el.get("transform"))))
        self._check_pitch(el, lines)

    def _check_pitch(self, el, lines):
        if "layout" in self.skip or len(lines) < 2:
            return
        if all(len(s.strip()) <= 1 for _, _, s, _ in lines):
            return  # 竖排：逐字 tspan 的字距规范是 字号+2px（约 1.15×），不按横向行距判
        seq = [(ly, lf) for _, ly, _, lf in lines]
        for (ya, fa), (yb, fb) in zip(seq, seq[1:]):
            if abs(fa - fb) > 0.5:
                continue
            pitch, fs = yb - ya, fa
            if 0 < pitch < fs * LINE_PITCH_RATIO:
                self.warn.append(
                    f"[行距] id={el.get('id') or '无'} 行距 {pitch:.0f}px < {fs * LINE_PITCH_RATIO:.1f}px"
                    f"（{pitch / fs:.2f}×字号 {fs:.0f}），文字会挤在一起")
                break

    # ---------- 检查 ----------
    def run(self):
        if self.parse() is None:
            return
        if not (self.root.get("font-family") or self.root.get("style")) and not self._fonts:
            self.warn.append("全文档未声明 font-family，渲染器将回退到默认字体")
        self._check_markers()
        self._check_zero_len()
        self._check_canvas()
        self._check_bg_cover()
        self._check_caption()
        if "text" not in self.skip:
            self._check_text_fit()
            self._check_text_overlap()
        if "layout" not in self.skip:
            self._check_arrow_cross()
            self._check_overlap()
            self._check_group_pad()
            self._check_rows()
        self._check_palette()
        if "grid" in self.skip:
            self.grid_off = 0
        else:
            self._check_grid()

    def _check_markers(self):
        missing = self.used_markers - self.markers
        for m in sorted(missing):
            self.fail.append(f"引用了未定义的 marker：url(#{m})")
        unused = self.markers - self.used_markers
        if unused:
            self.info.append(f"定义了但未使用的 marker：{', '.join(sorted(unused))}")

    def _check_zero_len(self):
        for s in self.segs:
            if abs(s.x1 - s.x2) < 0.01 and abs(s.y1 - s.y2) < 0.01:
                if s.marker and s.single:
                    self.fail.append(
                        f"零长度线段带箭头（id={s.eid or '无'}，坐标 {s.x1:.0f},{s.y1:.0f}）："
                        "多数渲染器不画箭头，会静默丢线")

    def _check_canvas(self):
        if self.W is None:
            return
        for t in self.texts:
            if t.rotated:
                continue  # 旋转文字的 x/y 是变换前坐标，包围盒不可直接比较
            for (x, y, s) in t.lines:
                if not s.strip():
                    continue
                w = text_width(s, t.fs)
                x0 = x - w / 2 if t.anchor == "middle" else (x - w if t.anchor == "end" else x)
                if (x0 < self.x0 - 2 or x0 + w > self.x0 + self.W + 2
                        or y - t.fs * 0.85 < self.y0 - 2 or y > self.y0 + self.H + 2):
                    self.fail.append(f"文字超出画布：{s.strip()[:20]!r}（x≈{x0:.0f}, y={y:.0f}）")

    def _check_bg_cover(self):
        """画布必须被不透明底色矩形盖满，否则渲染 PNG 会出现透明底/透明边（交付缺陷）。"""
        if self.W is None:
            return
        for b in self.boxes:
            if (b.fill or "").upper() in ("", "NONE"):
                continue
            if (b.x <= self.x0 + 1 and b.y <= self.y0 + 1
                    and b.x2 >= self.x0 + self.W - 1 and b.y2 >= self.y0 + self.H - 1):
                return
        self.fail.append(
            f"画布没有被任何不透明底色矩形盖满（viewBox {self.x0:.0f},{self.y0:.0f} "
            f"{self.W:.0f}×{self.H:.0f}），PNG 会出现透明底/透明边")

    def _canvas_size(self):
        return (self.W if self.W is not None else float("inf"),
                self.H if self.H is not None else float("inf"))

    CAPTION_RE = re.compile(r"^\s*(图\s*\d+|图\s*[一二三四五六七八九十]+|Fig(?:ure)?\.?\s*\d+)", re.I)

    def _check_caption(self):
        for t in self.texts:
            for (_, _, s) in t.lines:
                if self.CAPTION_RE.match(s or ""):
                    self.warn.append(f"[图题] 图内出现图题字样 {s.strip()[:24]!r}：图题应由论文排版添加，仿绘不画")

    def _check_text_fit(self):
        W, H = self._canvas_size()
        inner = [b for b in self.boxes if b.w >= 60 and b.h >= 32
                 and not (abs(b.w - W) < 1 and abs(b.h - H) < 1)]
        for t in self.texts:
            if t.rotated:
                continue  # 旋转文字按变换前坐标估宽没有意义，与画布检查口径一致
            for (x, y, s) in t.lines:
                if not s.strip():
                    continue
                host = None
                for b in inner:
                    if b.contains(x, y - t.fs * 0.35, inset=-1):
                        if host is None or b.w * b.h < host.w * host.h:
                            host = b
                if not host:
                    continue
                w = text_width(s, t.fs)
                if w > host.w * TEXT_WIDTH_RATIO:
                    self.warn.append(
                        f"[出框] {s.strip()[:18]!r} 估算宽 {w:.0f}px > 框宽 {host.w:.0f}×90%"
                        f"（框 id={host.id or '无'}），需手动 <tspan> 换行")

    def _check_text_overlap(self):
        """不同 <text> 的墨迹包围盒互压（同一 text 内的行距由 _check_pitch 管）。"""
        items = []
        for t in self.texts:
            if t.rotated:
                continue
            for (x, y, s) in t.lines:
                if not s.strip():
                    continue
                w = text_width(s, t.fs)
                x0 = x - w / 2 if t.anchor == "middle" else (x - w if t.anchor == "end" else x)
                items.append((x0, y - t.fs * 0.85, x0 + w, y + t.fs * 0.25, s.strip()))
        for i, a in enumerate(items):
            for b in items[i + 1:]:
                ix = min(a[2], b[2]) - max(a[0], b[0])
                iy = min(a[3], b[3]) - max(a[1], b[1])
                if ix <= 0 or iy <= 0:
                    continue
                area = min((a[2] - a[0]) * (a[3] - a[1]), (b[2] - b[0]) * (b[3] - b[1]))
                if area and ix * iy > area * TEXT_OVERLAP_RATIO:
                    self.warn.append(
                        f"[互压] {a[4][:12]!r} 与 {b[4][:12]!r} 文字包围盒重叠 "
                        f"{ix:.0f}×{iy:.0f}px，拉开行距或垫白底")

    def _solid_boxes(self):
        W, H = self._canvas_size()
        return [b for b in self.boxes if b.w >= 40 and b.h >= 24 and b.stroke
                and not (abs(b.w - W) < 1 and abs(b.h - H) < 1)]

    def _check_arrow_cross(self):
        boxes = self._solid_boxes()
        for s in self.segs:
            if not s.marker:
                continue
            length = math.hypot(s.x2 - s.x1, s.y2 - s.y1)
            if length < 12:
                continue
            for b in boxes:
                if (b.contains(s.x1, s.y1, inset=-4) or b.contains(s.x2, s.y2, inset=-4)):
                    continue  # 起止点落在本框上，正常
                hits = 0
                for k in range(1, 10):
                    px = s.x1 + (s.x2 - s.x1) * k / 10
                    py = s.y1 + (s.y2 - s.y1) * k / 10
                    if b.contains(px, py, inset=6):
                        hits += 1
                if hits:
                    self.warn.append(
                        f"[穿框] 箭头 ({s.x1:.0f},{s.y1:.0f})→({s.x2:.0f},{s.y2:.0f}) "
                        f"穿过 {b.id or '某个框'}({b.x:.0f},{b.y:.0f},{b.w:.0f}×{b.h:.0f})")
                    break

    def _check_overlap(self):
        boxes = [b for b in self._solid_boxes() if not b.dashed]
        for i, a in enumerate(boxes):
            for b in boxes[i + 1:]:
                ix = max(0, min(a.x2, b.x2) - max(a.x, b.x))
                iy = max(0, min(a.y2, b.y2) - max(a.y, b.y))
                inter = ix * iy
                if inter >= min(a.w * a.h, b.w * b.h) * 0.85:
                    continue  # 一个框整体嵌在另一个框里，是嵌套不是重叠
                if inter > min(a.w * a.h, b.w * b.h) * OVERLAP_RATIO:
                    self.warn.append(
                        f"[重叠] {a.id or f'({a.x:.0f},{a.y:.0f})'} 与 "
                        f"{b.id or f'({b.x:.0f},{b.y:.0f})'} 重叠 {ix:.0f}×{iy:.0f}px")

    def _bands(self):
        W, H = self._canvas_size()
        return [b for b in self.boxes if b.rx >= 8 and b.w >= 120 and b.h >= 80
                and not (abs(b.w - W) < 1 and abs(b.h - H) < 1)]

    def _check_group_pad(self):
        for band in self._bands():
            members = [b for b in self._solid_boxes()
                       if b is not band and b.w < band.w and b.h < band.h
                       and band.contains(b.x, b.y) and band.contains(b.x2, b.y2)]
            for m in members:
                pad = min(m.x - band.x, m.y - band.y, band.x2 - m.x2, band.y2 - m.y2)
                if pad < 0:
                    self.warn.append(
                        f"[越界] 成员框 {m.id or f'({m.x:.0f},{m.y:.0f})'} 越出分组框 "
                        f"{band.id or f'({band.x:.0f},{band.y:.0f})'}（pad={pad:.0f}px）")
                elif pad == 0:
                    pass  # 标题条骑在分组框边线上是常见设计，不报
                elif pad < GROUP_PAD_MIN:
                    self.fail.append(
                        f"[贴边] 成员框 {m.id or f'({m.x:.0f},{m.y:.0f})'} 距分组框 "
                        f"{band.id or f'({band.x:.0f},{band.y:.0f})'} 仅 {pad:.0f}px（硬下限 {GROUP_PAD_MIN}px）")
                elif pad < GROUP_PAD_WARN:
                    self.warn.append(
                        f"[贴边] 成员框 {m.id or f'({m.x:.0f},{m.y:.0f})'} 距分组框 "
                        f"{band.id or f'({band.x:.0f},{band.y:.0f})'} 仅 {pad:.0f}px（规范建议 ≥{GROUP_PAD_WARN}px）")

    def _check_rows(self):
        boxes = [b for b in self._solid_boxes() if not b.dashed]
        rows: dict[int, list[Box]] = {}
        for b in boxes:
            # 按行分组不按颜色分组：同一行常有意用不同语义色（如流程链的强调阶段）
            rows.setdefault(round(b.y / 8) * 8, []).append(b)
        for _, row in rows.items():
            if len(row) < 3:
                continue
            # 同高度的一批框才构成"同一层"，必须中线对齐；高度不同是刻意分层，不参与比较
            tiers = {}
            for b in row:
                tiers.setdefault(round(b.h / 8) * 8, []).append(b)
            for hv, group in tiers.items():
                if len(group) < 3:
                    continue
                centers = {round(b.y + b.h / 2) for b in group}
                if max(centers) - min(centers) > 2:
                    self.warn.append(f"[同层] 同高度({hv}px)的 3+ 个框中线不齐：y≈{group[0].y:.0f}")
            row.sort(key=lambda b: b.x)
            # 只有等宽框才比较间距；不同宽的框排在同一行是刻意的层级差异，不是缺陷
            widths = {round(b.w) for b in row}
            gaps = [round(b.x - a.x2) for a, b in zip(row, row[1:]) if b.x - a.x2 > 0]
            # 树形/分支布局里跨父节点的间距本来就是结构跳变（如 24 与 144 并存），不算缺陷
            structural = gaps and max(gaps) >= max(3 * min(gaps), 72)
            if len(widths) <= 1 and len(gaps) >= 2 and max(gaps) - min(gaps) > 4 and not structural:
                self.warn.append(f"[等距] 同一行 3+ 个框间距不一致：{gaps}（y≈{row[0].y:.0f}）")

    def _check_palette(self):
        odd = sorted(c for c in self.colors if c not in PALETTE and c != "NONE")
        if odd:
            self.info.append(f"调色板外颜色：{', '.join(odd[:8])}")

    def _check_grid(self):
        off = 0
        for b in self.boxes:
            for v in (b.x, b.y, b.w, b.h):
                if abs(v - round(v / GRID) * GRID) > 0.5:
                    off += 1
        self.grid_off = off
        if off:
            self.info.append(f"{off} 个坐标未落在 {GRID}px 网格上（对齐检查，非强制）")



BAD_SVG = """<svg xmlns="http://www.w3.org/2000/svg" width="400" height="200" viewBox="0 0 400 200">
  <defs><marker id="arrow" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7"><path d="M0,0 L10,5 L0,10 z" fill="#5A6B7E"/></marker></defs>
  <rect width="380" height="180" fill="#FFFFFF"/>
  <rect x="40" y="40" width="120" height="48" rx="6" fill="#EEF4FB" stroke="#2F6BB0" stroke-width="1.5"/>
  <text x="100" y="68" font-size="13" text-anchor="middle" fill="#1A1A1A">这是一个明显超出框宽百分之九十的很长的模块名称</text>
  <text x="100" y="140" font-size="13" text-anchor="middle" fill="#1A1A1A">第一行<tspan x="100" y="152">第二行</tspan></text>
  <text x="200" y="120" font-size="11" fill="#1A1A1A">互压甲乙丙丁</text>
  <text x="206" y="125" font-size="11" fill="#1A1A1A">重叠标签戊己</text>
  <rect x="270" y="40" width="120" height="100" rx="10" fill="#2F6BB0" fill-opacity="0.06" stroke="#2F6BB0" stroke-width="1.5"/>
  <rect x="276" y="46" width="80" height="40" rx="6" fill="#EEF4FB" stroke="#2F6BB0" stroke-width="1.5"/>
  <line x1="200" y1="64" x2="200" y2="64" stroke="#5A6B7E" stroke-width="1.5" marker-end="url(#arrow)"/>
  <line x1="200" y1="100" x2="260" y2="100" stroke="#5A6B7E" stroke-width="1.5" marker-end="url(#nosuch)"/>
  <text x="390" y="190" font-size="13" fill="#1A1A1A">画布外的字</text>
</svg>"""

GOOD_SVG = """<svg xmlns="http://www.w3.org/2000/svg" width="480" height="240" viewBox="0 0 480 240"
     font-family="Noto Sans CJK SC, sans-serif">
  <defs><marker id="arrow" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7"
      orient="auto-start-reverse"><path d="M0,0 L10,5 L0,10 z" fill="#5A6B7E"/></marker></defs>
  <rect width="480" height="240" fill="#FFFFFF"/>
  <rect x="48" y="48" width="160" height="56" rx="6" fill="#EEF4FB" stroke="#2F6BB0" stroke-width="1.5"/>
  <text x="128" y="81" font-size="13" text-anchor="middle" fill="#1A1A1A">源模块</text>
  <rect x="272" y="48" width="160" height="56" rx="6" fill="#EDF7F2" stroke="#3E9B6C" stroke-width="1.5"/>
  <text x="352" y="81" font-size="13" text-anchor="middle" fill="#1A1A1A">结果模块</text>
  <line x1="208" y1="76" x2="268" y2="76" stroke="#5A6B7E" stroke-width="1.5" marker-end="url(#arrow)"/>
</svg>"""

SELF_TEST_CASES = [
    ("未定义 marker 必红", "fail", "未定义的 marker"),
    ("零长度箭头必红", "fail", "零长度线段"),
    ("文字出画布必红", "fail", "文字超出画布"),
    ("白底未盖满画布必红", "fail", "透明"),
    ("分组贴边硬下限必红", "fail", "硬下限"),
    ("行距过挤必黄", "warn", "行距"),
    ("文字出框必黄", "warn", "出框"),
    ("文字互压必黄", "warn", "互压"),
    ("缺 font-family 必黄", "warn", "font-family"),
]


def self_test() -> int:
    import tempfile
    bad = 0
    with tempfile.TemporaryDirectory() as td:
        for name, content, expect_missing in (("bad.svg", BAD_SVG, False), ("good.svg", GOOD_SVG, True)):
            (Path(td) / name).write_text(content, encoding="utf-8")
        res = lint_one(Path(td) / "bad.svg", set())
        got = res["fail"] + res["warn"]
        for label, kind, needle in SELF_TEST_CASES:
            hit = any(needle in m for m in got) and any(needle in m for m in (res["fail"] if kind == "fail" else res["warn"]))
            print(("  OK   " if hit else "  漏检 ") + label)
            bad += 0 if hit else 1
        good = lint_one(Path(td) / "good.svg", set())
        clean = good["status"] == "PASS"
        print(("  OK   " if clean else "  误报 ") + "合规样例应全绿" + ("" if clean else f"：{good['fail'] + good['warn']}"))
        bad += 0 if clean else 1
    print("\n自测：" + ("全部通过" if not bad else f"{bad} 项不达预期"))
    return 1 if bad else 0


def lint_one(path: Path, skip: set[str]) -> dict:
    l = Linter(path, skip)
    l.run()
    return {
        "file": path.name,
        "fail": l.fail,
        "warn": l.warn,
        "info": l.info,
        "status": "FAIL" if l.fail else ("WARN" if l.warn else "PASS"),
    }


def main() -> int:
    ap = argparse.ArgumentParser(description="科研架构图 SVG 静态质检")
    ap.add_argument("target", nargs="?", help="SVG 文件或目录（不递归）")
    ap.add_argument("--json", action="store_true", help="输出 JSON")
    ap.add_argument("--grid", action="store_true", help="显示 8px 网格偏差计数")
    ap.add_argument("--skip", default="", help="跳过检查类别，逗号分隔：text,layout,grid")
    ap.add_argument("--quiet", action="store_true", help="只输出汇总，不列条目")
    ap.add_argument("--self-test", action="store_true", help="用内置缺陷样例验证检查规则确实会报错")
    args = ap.parse_args()

    if args.self_test:
        return self_test()

    if args.target is None:
        ap.error("需要提供 SVG 文件或目录（或用 --self-test）")
    t = Path(args.target)
    if not t.exists():
        print(f"目标不存在：{t}")
        return 1
    files = (sorted(p for p in t.iterdir() if p.is_file() and p.suffix.lower() == ".svg")
             if t.is_dir() else [t])
    if not files:
        print("未找到 SVG 文件")
        return 1

    skip = {s.strip() for s in args.skip.split(",") if s.strip()}
    unknown = skip - {"text", "layout", "grid"}
    if unknown:
        print(f"忽略未知 --skip 类别：{', '.join(sorted(unknown))}（可选 text,layout,grid）")
    if not args.grid:
        skip.add("grid")

    results = [lint_one(f, skip) for f in files]
    counts = {"PASS": 0, "WARN": 0, "FAIL": 0}
    for r in results:
        counts[r["status"]] += 1

    if args.json:
        print(json.dumps({"results": results, "summary": counts}, ensure_ascii=False, indent=2))
    else:
        for r in results:
            if r["status"] == "PASS":
                if not args.quiet:
                    print(f"PASS  {r['file']}")
                continue
            print(f"{r['status']}  {r['file']}")
            if args.quiet:
                continue
            for m in r["fail"]:
                print(f"      FAIL  {m}")
            for m in r["warn"]:
                print(f"      WARN  {m}")
            for m in r["info"]:
                print(f"      INFO  {m}")
        print(f"\n汇总：PASS {counts['PASS']} / WARN {counts['WARN']} / FAIL {counts['FAIL']}"
              f"  （共 {len(results)} 个文件）")
        if counts["FAIL"]:
            print("有 FAIL，不要交付。")
        elif counts["WARN"]:
            print("有 WARN，逐条目检确认；结构性 WARN 应修。")

    if counts["FAIL"]:
        return 1
    return 2 if counts["WARN"] else 0


if __name__ == "__main__":
    sys.exit(main())
