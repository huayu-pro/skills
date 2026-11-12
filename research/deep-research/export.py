#!/usr/bin/env python3
"""把 run 的终稿导出到交付目录：重命名、转格式、导出参考文献与清单。

用法：
    python3 export.py PROJECT --dest <交付目录> [--run RUN-ID] [--name <名称>]
                        [--format md|html|pdf|docx] [--references] [--manifest]
                        [--force] [--partial]

导出内容（存在哪个导哪个；run 未完成时会拒绝，除非 --partial）：
    final/<run>-final.md   ->  <名称>.md            （终稿）
    final/<run>-survey.md  ->  <名称>-survey.md     （综述）
    final/<run>-draft.md   ->  <名称>-draft.md      （初稿）
    final/<run>-review.md  ->  <名称>-review.md     （独立审查）
    final/sources/         ->  <名称>-sources/      （引用的全部材料）
    question.md            ->  <名称>-question.md   （问题原话）

另可产出：
    --references    <名称>-references.md / .html
                    从终稿的 `## 参考文献` 节抽条目；没有该节时，按正文定位符与
                    sources/ 里的实际文件列出。引用了读者打不开的来源，这里先暴露。
    --manifest      <名称>-manifest.json
                    导出清单：每项的字节数、sha256、来源路径，以及本次导出跳过了什么。
    --format html   零依赖自研渲染（不引第三方库）；pandoc 存在时 pdf/docx 由它转，
                    pdf 无 pandoc 时退化为"打印成 PDF 即可"的 HTML 并说明。

--name 缺省用 run id。默认拒绝覆盖已存在文件；--force 才覆盖。
退出码：0 成功；2 参数错误或拒绝导出。
仅标准库；无网络（PDF/DOCX 需本机 pandoc）。
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
from datetime import datetime, timezone

STAGES = ("survey", "draft", "review", "final")
SUFFIX = {"survey": "-survey.md", "draft": "-draft.md", "review": "-review.md", "final": ".md"}
FORMATS = ("md", "html", "pdf", "docx")


def die(message: str, code: int = 2) -> None:
    print(f"export: {message}", file=sys.stderr)
    raise SystemExit(code)


def note(message: str) -> None:
    print(f"export: {message}", file=sys.stderr)


def pick_run(base: str, only: str | None) -> tuple[str, dict]:
    if not os.path.isdir(base):
        die(f"{base} 下没有 research/ 目录")
    run_ids = sorted(d for d in os.listdir(base)
                     if os.path.isfile(os.path.join(base, d, "run.json")))
    if only:
        if only not in run_ids:
            die(f"找不到 run {only}；现有：{', '.join(run_ids) or '无'}")
        chosen = only
    else:
        if not run_ids:
            die(f"{base} 下没有 run")
        if len(run_ids) > 1:
            die(f"{base} 下有 {len(run_ids)} 个 run（{', '.join(run_ids)}）；用 --run 指定一个")
        chosen = run_ids[0]
    run_dir = os.path.join(base, chosen)
    try:
        with open(os.path.join(run_dir, "run.json"), encoding="utf-8") as handle:
            run = json.load(handle)
    except (OSError, ValueError) as error:
        die(f"读取 {chosen}/run.json 失败：{error}")
    if not isinstance(run, dict):
        die(f"{chosen}/run.json 不是一份 run 账本")
    return run_dir, run


# --------------------------------------------------------------------------- HTML 渲染（零依赖）

def escape(text: str) -> str:
    return (text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;"))


def inline(text: str) -> str:
    """行内 markdown：代码、粗体、斜体、链接。够用即可——报告不需要 CommonMark 全量。"""
    out = []
    buffer = ""
    index = 0
    while index < len(text):
        char = text[index]
        if char == "`":
            end = text.find("`", index + 1)
            if end > index + 1:
                if buffer:
                    out.append(escape(buffer))
                    buffer = ""
                out.append(f"<code>{escape(text[index + 1:end])}</code>")
                index = end + 1
                continue
        elif char == "*" and text[index:index + 2] == "**":
            end = text.find("**", index + 2)
            if end > index + 1:
                if buffer:
                    out.append(escape(buffer))
                    buffer = ""
                out.append(f"<strong>{inline(text[index + 2:end])}</strong>")
                index = end + 2
                continue
        buffer += char
        index += 1
    if buffer:
        out.append(escape(buffer))
    return "".join(out)


def md_to_html(text: str, title: str) -> str:
    """把 markdown 报告渲染成一份自含 HTML。

    覆盖报告实际用得到的那部分 markdown：ATX 标题、段落、无序/有序列表、引用、代码块、
    表格、分隔线、YAML frontmatter（跳过）。不追 CommonMark 全量——零依赖比全量要紧，
    pandoc 在的时候用户会去用它。
    """
    lines = text.splitlines()
    body: list[str] = []
    index = 0
    if lines and lines[0].strip() == "---":
        for index in range(1, len(lines)):
            if lines[index].strip() == "---":
                index += 1
                break
    while index < len(lines):
        line = lines[index]
        stripped = line.strip()
        if not stripped:
            index += 1
            continue
        if stripped.startswith("```"):
            index += 1
            buf = []
            while index < len(lines) and not lines[index].strip().startswith("```"):
                buf.append(lines[index])
                index += 1
            index += 1
            body.append(f"<pre><code>{escape(chr(10).join(buf))}</code></pre>")
            continue
        if re.match(r"^\s*([-*_])\s*\1\s*\1[\s\1]*$", stripped):
            body.append("<hr>")
            index += 1
            continue
        heading = re.match(r"^(#{1,6})\s+(.*)$", stripped)
        if heading:
            level = len(heading.group(1))
            body.append(f"<h{level}>{inline(heading.group(2).strip())}</h{level}>")
            index += 1
            continue
        if stripped.startswith(">"):
            buf = []
            while index < len(lines) and lines[index].strip().startswith(">"):
                buf.append(lines[index].strip().lstrip(">").strip())
                index += 1
            body.append(f"<blockquote>{inline(' '.join(buf))}</blockquote>")
            continue
        if stripped.startswith("|") and index + 1 < len(lines) and re.match(
                r"^\|[\s:|-]+\|$", lines[index + 1].strip()):
            rows = []
            while index < len(lines) and lines[index].strip().startswith("|"):
                cells = [c.strip() for c in lines[index].strip().strip("|").split("|")]
                rows.append(cells)
                index += 1
            head, rest = rows[0], rows[1:]
            table = ["<table>", "<thead><tr>"
                     + "".join(f"<th>{inline(c)}</th>" for c in head) + "</tr></thead>", "<tbody>"]
            for row in rest:
                table.append("<tr>" + "".join(f"<td>{inline(c)}</td>" for c in row) + "</tr>")
            table += ["</tbody>", "</table>"]
            body.append("\n".join(table))
            continue
        if re.match(r"^\s*[-*+]\s+", stripped) or re.match(r"^\s*\d+[.)]\s+", stripped):
            ordered = bool(re.match(r"^\s*\d+[.)]\s+", stripped))
            items = []
            while index < len(lines):
                item = re.match(r"^\s*(?:[-*+]|\d+[.)])\s+(.*)$", lines[index])
                if not item:
                    break
                items.append(inline(item.group(1).strip()))
                index += 1
            tag = "ol" if ordered else "ul"
            body.append(f"<{tag}>" + "".join(f"<li>{i}</li>" for i in items) + f"</{tag}>")
            continue
        buf = []
        while index < len(lines) and lines[index].strip() and not lines[index].lstrip().startswith(
                ("#", ">", "|", "```", "-", "*", "+")) and not re.match(r"^\s*\d+[.)]\s+", lines[index]):
            buf.append(lines[index].strip())
            index += 1
        if buf:
            body.append(f"<p>{inline(' '.join(buf))}</p>")
        else:
            body.append(f"<p>{inline(stripped)}</p>")
            index += 1
    return (
        "<!DOCTYPE html>\n<html lang=\"zh\">\n<head>\n<meta charset=\"utf-8\">\n"
        f"<title>{escape(title)}</title>\n<style>\n"
        "body{max-width:44rem;margin:3rem auto;padding:0 1.2rem;line-height:1.75;"
        "font-family:Georgia,'Songti SC','Noto Serif CJK SC',serif;color:#1a1a1a}\n"
        "h1,h2,h3{line-height:1.3;margin-top:2rem}\nh1{font-size:1.9rem}\n"
        "h2{font-size:1.35rem;border-bottom:1px solid #ddd;padding-bottom:.3rem}\n"
        "code{background:#f4f4f4;padding:.1rem .3rem;border-radius:3px;font-size:.9em}\n"
        "pre{background:#f4f4f4;padding:.8rem;overflow-x:auto}\n"
        "blockquote{border-left:3px solid #ccc;margin:1rem 0;padding:.2rem 1rem;color:#555}\n"
        "table{border-collapse:collapse;width:100%;margin:1rem 0}\n"
        "th,td{border:1px solid #ddd;padding:.4rem .6rem;text-align:left;vertical-align:top}\n"
        "th{background:#f8f8f8}\nhr{border:0;border-top:1px solid #ddd;margin:2rem 0}\n"
        "@media print{body{margin:0;max-width:none}}\n"
        "</style>\n</head>\n<body>\n" + "\n".join(body) + "\n</body>\n</html>\n"
    )


def convert_via_pandoc(src: str, out_path: str, target: str) -> bool:
    pandoc = shutil.which("pandoc")
    if not pandoc:
        return False
    result = subprocess.run([pandoc, src, "-o", out_path, "--from=markdown",
                             "--to=" + ("pdf" if target == "pdf" else "docx")],
                            capture_output=True, text=True)
    return result.returncode == 0 and os.path.isfile(out_path)


# --------------------------------------------------------------------------- 参考文献与清单

def extract_references(text: str) -> list[str]:
    """终稿的 `## 参考文献` 节；没有该节时退回正文里的定位符。

    参考文献是交付里唯一让读者能核对"你引用的东西存在"的地方，所以两条路都走：
    写了节就用节，没写就从正文抽出定位符，并把"没写参考文献节"作为一条提醒。
    """
    lines = text.splitlines()
    start = None
    for index, line in enumerate(lines):
        stripped = line.lstrip()
        if stripped.startswith("#") and re.search(r"参考文献|references|bibliography",
                                                  stripped, re.I):
            start = index + 1
            break
    if start is not None:
        out = []
        for line in lines[start:]:
            if line.lstrip().startswith("#") and line.lstrip().lstrip("#").strip() and \
                    not line.lstrip().startswith(("-", "*", "|")):
                if out:
                    break
                continue
            if line.strip().startswith(("-", "*")):
                out.append(line.strip().lstrip("-*").strip())
            elif line.strip():
                out.append(line.strip())
        if out:
            return out
    seen, locators = set(), []
    for match in re.finditer(r"`([^`\n]+)`", text):
        token = match.group(1).strip()
        if token in seen or " " in token or not re.search(r"[./]", token):
            continue
        if token.startswith(("http://", "https://", "doc:")) or not re.fullmatch(
                r"[\w./\-]+", token, re.UNICODE):
            continue
        seen.add(token)
        locators.append(token)
    return locators


def references_text(items: list[str], have_section: bool) -> str:
    lines = ["# 参考文献", ""]
    if not have_section:
        lines += ["> 终稿没有 `## 参考文献` 节，以下条目是从正文定位符抽出的；"
                  "交付前补一节（见 references/07-report.md 的学术装置）。", ""]
    lines += [f"- {item}" for item in items] or ["_（无条目）_"]
    lines.append("")
    return "\n".join(lines)


def sha256_of(path: str) -> str:
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for chunk in iter(lambda: handle.read(65536), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main(argv=None) -> int:
    p = argparse.ArgumentParser(prog="export.py", description=__doc__.splitlines()[0])
    p.add_argument("project", help="研究所在的项目文件夹")
    p.add_argument("--dest", required=True, help="交付目录（不存在则创建）")
    p.add_argument("--run", help="导出这个 run（项目里只有一个时可省）")
    p.add_argument("--name", help="交付文件的基础名（默认用 run id）。示例：--name \"研究报告_继续革命理论\"")
    p.add_argument("--format", dest="fmt", default="md", choices=FORMATS,
                   help="交付格式（默认 md）。html 零依赖自研；pdf/docx 走 pandoc，缺失时降级并说明")
    p.add_argument("--references", action="store_true", help="另导出一份参考文献清单")
    p.add_argument("--manifest", action="store_true", help="另导出 manifest.json（每项字节数/sha256/来源）")
    p.add_argument("--force", action="store_true", help="覆盖目标目录中的同名文件")
    p.add_argument("--partial", action="store_true",
                   help="run 未完成也导出（导出已存在的阶段文件；一个都没有则失败）")
    args = p.parse_args(argv)

    project = os.path.realpath(os.path.expanduser(args.project))
    run_dir, run = pick_run(os.path.join(project, "research"), args.run)
    run_id = str(run.get("run_id") or os.path.basename(run_dir))
    name = args.name or run_id
    final_dir = os.path.join(run_dir, "final")
    stages = run.get("final") if isinstance(run.get("final"), dict) else {}

    sources: dict[str, str] = {}
    for stage in STAGES:
        record = stages.get(stage)
        if record and os.path.isfile(os.path.join(final_dir, str(record))):
            sources[stage] = os.path.join(final_dir, str(record))
    if not sources.get("final") and not args.partial:
        die(f"run {run_id} 还没有终稿（final 阶段缺失，status: {run.get('status')}）。"
            f"确要导出半成品就加 --partial。")
    if not sources:
        die("final/ 下没有任何阶段文件可导出。")
    for stage in STAGES:
        if not sources.get(stage):
            note(f"{stage} 阶段缺失，跳过")

    dest = os.path.realpath(os.path.expanduser(args.dest))
    os.makedirs(dest, exist_ok=True)
    copied: list[str] = []
    items: list[dict] = []
    skipped: list[dict] = []

    def copy_file(src: str, dst_name: str) -> None:
        dst = os.path.join(dest, dst_name)
        if os.path.exists(dst) and not args.force:
            die(f"目标已存在：{dst}；换 --name 或加 --force")
        shutil.copyfile(src, dst)
        copied.append(dst_name)
        items.append({"delivered": dst_name, "from": os.path.relpath(src, run_dir),
                      "bytes": os.path.getsize(dst), "sha256": sha256_of(dst)})

    def write_text(text: str, dst_name: str) -> None:
        dst = os.path.join(dest, dst_name)
        if os.path.exists(dst) and not args.force:
            die(f"目标已存在：{dst}；换 --name 或加 --force")
        with open(dst, "w", encoding="utf-8") as handle:
            handle.write(text)
        copied.append(dst_name)
        items.append({"delivered": dst_name, "from": "generated by export.py",
                      "bytes": os.path.getsize(dst), "sha256": sha256_of(dst)})

    def out_name(suffix: str) -> str:
        ext = {"md": ".md", "html": ".html", "pdf": ".pdf", "docx": ".docx"}[args.fmt]
        return f"{name}{suffix}{ext}" if suffix else f"{name}{ext}"

    for stage in STAGES:
        if not sources.get(stage):
            skipped.append({"stage": stage, "reason": "run.json 未记该阶段或文件不存在"})
            continue
        src = sources[stage]
        if args.fmt == "md":
            copy_file(src, out_name(SUFFIX[stage].replace(".md", "")))
            continue
        with open(src, encoding="utf-8") as handle:
            text = handle.read()
        if args.fmt == "html":
            target = out_name(SUFFIX[stage].replace(".md", ""))
            html = md_to_html(text, f"{name} {stage}")
            write_text(html, target)
            continue
        # pdf / docx：pandoc 在就转，不在就退化为 HTML 并把话说清楚——静默降级是丢信息。
        target = out_name(SUFFIX[stage].replace(".md", ""))
        if convert_via_pandoc(src, os.path.join(dest, target), args.fmt):
            copied.append(target)
            items.append({"delivered": target, "from": os.path.relpath(src, run_dir),
                          "bytes": os.path.getsize(os.path.join(dest, target)),
                          "sha256": sha256_of(os.path.join(dest, target))})
        else:
            fallback = target.rsplit(".", 1)[0] + ".html"
            write_text(md_to_html(text, f"{name} {stage}"), fallback)
            note(f"本机没有 pandoc，{args.fmt} 转不了；已改出 HTML（{fallback}），"
                 f"用浏览器打印即得 PDF。装 pandoc 后可重跑本命令得到 {args.fmt}。")
            skipped.append({"stage": stage, "reason": f"pandoc 不可用，降级为 HTML（{fallback}）"})

    src_dir = os.path.join(final_dir, "sources")
    if os.path.isdir(src_dir):
        dst_dir = os.path.join(dest, name + "-sources")
        if os.path.exists(dst_dir) and not args.force:
            die(f"目标已存在：{dst_dir}；换 --name 或加 --force")
        if os.path.exists(dst_dir):
            shutil.rmtree(dst_dir)
        shutil.copytree(src_dir, dst_dir)
        copied.append(os.path.basename(dst_dir) + "/")
        count = sum(len(f) for _r, _d, f in os.walk(dst_dir))
        items.append({"delivered": os.path.basename(dst_dir) + "/",
                      "from": "final/sources/", "files": count, "bytes": os.path.getsize(dst_dir)})
    else:
        note("final/sources/ 缺失——引用了读者打不开的来源；交付前补齐（见 references/07-report.md）")
        skipped.append({"item": "final/sources/", "reason": "目录不存在"})

    question = os.path.join(run_dir, "question.md")
    if os.path.isfile(question):
        copy_file(question, name + "-question.md")

    if args.references:
        if not sources.get("final"):
            note("没有终稿，跳过参考文献导出")
            skipped.append({"item": "references", "reason": "终稿缺失"})
        else:
            with open(sources["final"], encoding="utf-8") as handle:
                text = handle.read()
            refs = extract_references(text)
            have_section = bool(re.search(r"^#{1,6}\s*.*(参考文献|references|bibliography)",
                                          text, re.I | re.M))
            if not have_section:
                note("终稿没有 `## 参考文献` 节；清单从正文定位符抽出，交付前补该节")
            if args.fmt == "html":
                write_text(md_to_html(references_text(refs, have_section), f"{name} 参考文献"),
                           f"{name}-references.html")
            else:
                write_text(references_text(refs, have_section), f"{name}-references.md")
            # 每个定位符是否真的在 sources/ 里——引用了打不开的来源要在这里暴露。
            unresolved = []
            for ref in refs:
                token = ref.strip().strip("`").split(" ")[0]
                if token.startswith(("http", "doc:")):
                    continue
                if not os.path.isfile(os.path.join(src_dir, os.path.basename(token))) \
                        and not os.path.isfile(os.path.join(final_dir, token)) \
                        and not os.path.isfile(os.path.join(run_dir, token)):
                    unresolved.append(token)
            if unresolved:
                note(f"{len(unresolved)} 条参考文献在 final/sources/ 里找不到对应文件："
                     f"{', '.join(unresolved[:5])}")
                skipped.append({"item": "references", "reason": "以下条目在 sources/ 中无对应文件",
                                "entries": unresolved})

    if args.manifest:
        payload = {
            "run_id": run_id,
            "run_status": run.get("status"),
            "question": run.get("question"),
            "format": args.fmt,
            "delivered": items,
            "skipped": skipped,
            "exported_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        }
        write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
                   f"{name}-manifest.json")

    print(f"已从 run {run_id} 导出 {len(copied)} 项到 {dest}：")
    for item in copied:
        print(f"  {item}")
    if skipped and not args.manifest:
        print(f"跳过 {len(skipped)} 项；加 --manifest 看明细。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
