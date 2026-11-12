#!/usr/bin/env python3
"""
auto-resume-tasks · 双源一致性门禁（十项）
SKILL.md 与 scripts/resume_decide.py 是同一决策逻辑的两份实现，
本脚本逐项对账两侧的关键口径，任何不一致即失败（退出码 1）：
  1. 阶段-错误重试矩阵（双向：文档行集合==MATRIX 键集、上限值、列数、allow 标志）
  2. 全抖动退避参数（T_BASE/T_MAX：文档所有出现处取值必须一致且等于代码）
  3. 语义相似度阈值（余弦/Jaccard 行级数值枚举，主方案 0.9 与 fallback 阈值）
  4. 【恢复摘要】模板（字段名+值枚举，全部块一致，与 Decision.summary() 一致）
  5. 最终动作关键词（FINAL_KEYWORDS+EN：所有列举行集合一致）
  6. Retry Policy 口径（行绑定，节内诱饵行不满足）
  7. 旧称清理（文档不得再使用「语义哈希」）
  8. 信号字段完备性（prompt 片段行 + 触发模板占位符）
  9. 错误分类与状态枚举（致命/瞬态错误码双向、payment 兜底、未知默认瞬态、状态枚举）
  10. 事务属性推断锚点（文档规则锚点 + infer_tx_attr 行为探针双向对账）

设计原则（二轮加固）：
  - 反诱饵：扫描全部匹配并要求一致/唯一，不接受「第一处正确」即放行
  - 双向对账：文档侧多余内容（矩阵多余行/列）同样算不一致
  - 值对账而非字面量对账：同义改写应通过，数值/集合漂移必须失败

用法：
  python3 scripts/check_consistency.py [--skill-dir <技能根目录>]
默认技能根目录为本脚本所在目录的上一级。
"""
from __future__ import annotations
import argparse
import importlib.util
import re
import sys
from pathlib import Path


def load_decide_module(skill_dir: Path):
    script = skill_dir / "scripts" / "resume_decide.py"
    if not script.is_file():
        raise FileNotFoundError(f"找不到 {script}")
    # 独立模块名，避免覆盖宿主进程中已导入的 resume_decide；
    # 必须先注册 sys.modules，否则 dataclass 解析注解时找不到所属模块
    name = "resume_decide_consistency_gate"
    spec = importlib.util.spec_from_file_location(name, str(script))
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


def fmt_num(v: float) -> str:
    return str(int(v)) if float(v).is_integer() else str(v)


def _num_tokens(line: str) -> list:
    """行内数值 token（小数与百分数），供阈值行级枚举"""
    return re.findall(r"\d+(?:\.\d+)?%?", line)


def _section(doc: str, header_pat: str, until: str = r"\n## |\n### ") -> Optional[str]:
    """截取 header 之后到下一个同级标题之前的正文；外层 h2 章节传 until=r"\\n## "。"""
    m = re.search(header_pat + r"[^\n]*\n(.*?)(?=" + until + r"|\Z)", doc, re.S)
    return m.group(1) if m else None


# ---------- 1. 阶段-错误矩阵 ----------
def check_matrix(doc: str, mod) -> list:
    problems = []
    section = _section(doc, r"### 4\. 阶段-错误联合判断")
    if section is None:
        return ["SKILL.md 缺少阶段-错误矩阵章节（### 4. 阶段-错误联合判断）"]

    doc_rows = {}
    for line in section.splitlines():
        line = line.strip()
        if not line.startswith("|"):
            continue
        cells = [c.strip() for c in line.strip("|").split("|")]
        if not cells or all(set(c) <= set("-: ") for c in cells):
            continue  # 分隔行
        if "阶段" in cells[0] and "瞬态" in cells[1]:
            continue  # 表头
        if len(cells) != 4:
            problems.append(f"矩阵行列数异常（应为 4 列）：{line[:60]}")
            continue
        if cells[0] in doc_rows:
            problems.append(f"矩阵出现重复阶段行：{cells[0]}")
        doc_rows[cells[0]] = cells[1], cells[2], cells[3]

    code_phases = {p.value for (p, _e) in mod.MATRIX}
    for name in sorted(set(doc_rows) - code_phases):
        problems.append(f"文档矩阵多出代码不存在的阶段：{name}")
    for name in sorted(code_phases - set(doc_rows)):
        problems.append(f"文档矩阵缺少代码矩阵的阶段：{name}")

    for (phase, err), (max_retry, allow) in mod.MATRIX.items():
        row = doc_rows.get(phase.value)
        if not row:
            continue
        t_cell, f_cell, l_cell = row
        if err.value == "transient":
            nums = set(re.findall(r"最多\s*(\d+)\s*次", t_cell))
            if nums != {str(max_retry)}:
                problems.append(
                    f"矩阵不一致：{phase.value}/transient 代码上限 {max_retry}，"
                    f"文档瞬态列取值 {sorted(nums) if nums else '无'}")
            if not allow and ("退避" in t_cell or "重试" in t_cell):
                problems.append(f"矩阵不一致：代码 {phase.value}/transient 已禁止续跑，文档仍写可重试")
        else:
            nums = set(re.findall(r"(\d+)\s*次", l_cell))
            if nums != {"1"} or "重试" not in l_cell:
                problems.append(
                    f"矩阵不一致：{phase.value}/logical 代码上限 1，"
                    f"文档逻辑列取值 {sorted(nums) if nums else '无'}")
            if not allow and "重试" in l_cell:
                problems.append(f"矩阵不一致：代码 {phase.value}/logical 已禁止续跑，文档仍写可重试")

    # 致命列：所有阶段行一致地「立即放弃」且不含重试次数（逐行解析，不再跨行匹配）
    for name, (_t, f_cell, _l) in doc_rows.items():
        if "立即放弃" not in f_cell or re.search(r"\d+\s*次", f_cell):
            problems.append(f"矩阵致命列异常（应仅「立即放弃」）：{name} → {f_cell}")
    return problems


# ---------- 2. 全抖动退避参数 ----------
def check_backoff(doc: str, mod) -> list:
    problems = []
    for name, value in (("t_base", mod.T_BASE), ("t_max", mod.T_MAX)):
        found = set(re.findall(name + r"\s*=\s*(\d+(?:\.\d+)?)\s*s", doc))
        expect = fmt_num(value)
        if not found:
            problems.append(f"退避参数不一致：文档缺少「{name} = {expect}s」")
        elif found != {expect}:
            problems.append(
                f"退避参数不一致：代码 {name}={expect}，文档出现取值 {sorted(found)}")
    return problems


# ---------- 3. 语义相似度阈值 ----------
def check_threshold(doc: str, mod) -> list:
    problems = []
    th = float(mod.SEMANTIC_FALLBACK_THRESHOLD)
    th_str = fmt_num(th)
    jaccard_lines = [ln for ln in doc.splitlines() if "Jaccard" in ln]
    cosine_lines = [ln for ln in doc.splitlines() if "余弦" in ln]
    if not jaccard_lines:
        problems.append("文档缺少 fallback 方案关键词「Jaccard」")
    if not cosine_lines:
        problems.append("文档缺少主方案关键词「余弦」")
    # 行级数值枚举：阈值行内只允许 0.9（主方案）与 fallback 阈值；
    # 百分数写法一律拒绝（堵「≥ 80%」式口径分叉）；全部出现处都要检查（堵诱饵行）
    allowed = {th, 0.9}
    for tag, lines in (("Jaccard", jaccard_lines), ("余弦", cosine_lines)):
        for ln in lines:
            for tok in _num_tokens(ln):
                if tok.endswith("%") or float(tok.rstrip("%")) not in allowed:
                    problems.append(
                        f"{tag} 阈值行出现非口径数值（主方案 0.9 / fallback {th_str}）："
                        f"{ln.strip()[:60]}（token {tok}）")
                    break
    if "semantic=fallback" not in doc:
        problems.append("文档未说明 fallback 结果需标注 semantic=fallback")
    return problems


def extract_summary_keys(text: str) -> list:
    keys = []
    for line in text.splitlines():
        m = re.match(r"^([^：{|\-\s][^：]*)：", line.strip())
        if m:
            keys.append(m.group(1).strip())
    return keys


def _enum_values(block_text: str, field_name: str) -> set:
    for ln in block_text.splitlines():
        s = ln.strip()
        if s.startswith(field_name + "：") or s.startswith(field_name + ":"):
            return set(re.findall(r"[a-z_]+", s.split("：", 1)[-1].split(":", 1)[-1]))
    return set()


# ---------- 4. 恢复摘要模板 ----------
def check_summary_template(doc: str, mod) -> list:
    # 只取内容以【恢复摘要】开头的代码块；全部块必须一致（堵诱饵块顶替）
    blocks = re.findall(r"```[^\n]*\n(【恢复摘要】[^`]*)```", doc)
    if not blocks:
        return ["SKILL.md 缺少【恢复摘要】模板代码块"]
    problems = []
    doc_keys_list = [extract_summary_keys(b) for b in blocks]
    uniq = {tuple(k) for k in doc_keys_list}
    if len(uniq) > 1:
        problems.append(f"文档存在多个不一致的【恢复摘要】模板块：{[list(u) for u in uniq]}")
    doc_keys = doc_keys_list[0]
    sample = mod.Decision(
        mod.DecisionAction.RESUME, mod.ErrorClass.TRANSIENT, mod.TxAttr.READONLY,
        mod.Phase.PROCESSING)
    code_keys = extract_summary_keys(sample.summary("x", "subagent"))
    if doc_keys != code_keys:
        only_doc = [k for k in doc_keys if k not in code_keys]
        only_code = [k for k in code_keys if k not in doc_keys]
        problems.append(
            f"恢复摘要模板字段不一致：文档={doc_keys}，代码={code_keys}"
            + (f"（文档多出：{only_doc}）" if only_doc else "")
            + (f"（代码多出：{only_code}）" if only_code else ""))
    # 值枚举对账：前置动作/恢复动作行必须列全代码枚举（堵枚举缩水）
    pre_doc = _enum_values(blocks[0], "前置动作")
    pre_code = {v.value for v in mod.PreAction}
    if pre_doc != pre_code:
        problems.append(f"摘要模板「前置动作」枚举不一致：文档={sorted(pre_doc)}，代码={sorted(pre_code)}")
    act_doc = _enum_values(blocks[0], "恢复动作")
    act_code = {v.value for v in mod.DecisionAction}
    if act_doc != act_code:
        problems.append(f"摘要模板「恢复动作」枚举不一致：文档={sorted(act_doc)}，代码={sorted(act_code)}")
    return problems


# ---------- 5. 最终动作关键词 ----------
def check_final_keywords(doc: str, mod) -> list:
    matches = re.findall(r"最终动作关键词[：:]\s*([^\n（(]+)", doc)
    if not matches:
        return ["SKILL.md 缺少「最终动作关键词：」列举行"]
    want = set(mod.FINAL_KEYWORDS) | set(mod.FINAL_KEYWORDS_EN)
    problems = []
    for i, raw in enumerate(matches):
        listed = {k.strip() for k in re.split(r"[、,，]", raw) if k.strip()}
        if listed != want:
            problems.append(
                f"最终动作关键词列表第 {i + 1} 处与代码不一致："
                f"文档缺 {sorted(want - listed)}，多 {sorted(listed - want)}")
    return problems


# ---------- 6. Retry Policy 口径 ----------
def check_retry_policy(doc: str, mod) -> list:
    m = re.search(r"## Retry Policy(.*?)(?=\n## |\Z)", doc, re.S)
    if not m:
        return ["SKILL.md 缺少 Retry Policy 章节"]
    lines = m.group(1).splitlines()
    problems = []
    transient_max = max(r for (_p, e), (r, _a) in mod.MATRIX.items() if e.value == "transient")
    transient_min = min(r for (_p, e), (r, _a) in mod.MATRIX.items() if e.value == "transient")
    logical_max = max(r for (_p, e), (r, _a) in mod.MATRIX.items() if e.value == "logical")

    def concept_lines(kw):
        return [ln for ln in lines if kw in ln and re.search(r"\d+\s*次", ln)]

    # 行绑定 + 恰一条：节内诱饵行会造出第二条，直接失败
    tl = concept_lines("瞬态")
    if len(tl) != 1:
        problems.append(f"Retry Policy 瞬态行应恰有 1 条，实际 {len(tl)} 条")
    else:
        nums = set(re.findall(r"(\d+)\s*次", tl[0]))
        if nums != {str(transient_max), str(transient_min)}:
            problems.append(
                f"Retry Policy 瞬态口径与矩阵不一致：文档 {sorted(nums)}，"
                f"代码 {transient_max}（其他阶段 {transient_min}）")
    ll = concept_lines("逻辑")
    if len(ll) != 1:
        problems.append(f"Retry Policy 逻辑行应恰有 1 条，实际 {len(ll)} 条")
    else:
        nums = set(re.findall(r"(\d+)\s*次", ll[0]))
        if nums != {str(logical_max)}:
            problems.append(f"Retry Policy 逻辑口径与矩阵不一致：文档 {sorted(nums)}，代码 {logical_max}")
    for kw in ("致命", "最终动作"):
        kl = [ln for ln in lines if kw in ln and re.search(r"\d+\s*次", ln)]
        if not kl or any("0 次" not in ln for ln in kl):
            problems.append(f"Retry Policy 未写明{kw} 0 次")
    if "human_pending" not in m.group(1):
        problems.append("Retry Policy 未写明 human_pending 不再自动处理")
    return problems


# ---------- 7. 旧称清理 ----------
def check_stale_terms(doc: str, _mod) -> list:
    if "语义哈希" in doc:
        return ["文档仍在使用旧称「语义哈希」，应统一为「语义指纹」"]
    return []


# ---------- 8. 信号字段完备性 ----------
def check_signal_fields(doc: str, _mod) -> list:
    """信号字段完备性：prompt 片段缺失会导致最终动作关键词永不生效。"""
    problems = []
    n_sections = len(re.findall(r"### 通用信号字段", doc))
    if n_sections != 1:
        return [f"「通用信号字段」章节应恰有 1 处，实际 {n_sections} 处"]
    table = _section(doc, r"### 通用信号字段")
    for col in ("错误摘要", "prompt 片段"):
        rows = [ln for ln in table.splitlines() if ln.startswith("|") and col in ln]
        if len(rows) != 1:
            problems.append(f"信号字段表「{col}」行应恰有 1 条，实际 {len(rows)} 条")
    n_template = len(re.findall(r"prompt提示=\{prompt_hint\}", doc))
    if n_template != 1:
        problems.append(f"最小触发模板的 prompt提示={{prompt_hint}} 应恰有 1 处，实际 {n_template} 处")
    return problems


# ---------- 9. 错误分类与状态枚举 ----------
def check_error_classification(doc: str, mod) -> list:
    sec = _section(doc, r"## Error Classification", until=r"\n## ")
    if sec is None:
        return ["SKILL.md 缺少 Error Classification 章节"]
    fatal = _section(sec, r"### 致命错误")
    trans = _section(sec, r"### 瞬态错误")
    logical = _section(sec, r"### 逻辑/内容错误")
    if fatal is None or trans is None or logical is None:
        return ["Error Classification 缺少致命/瞬态/逻辑三小节"]

    def pattern_codes(patterns) -> set:
        out = set()
        for p in patterns:
            out.update(re.findall(r"\d{3}", p))
        return out

    problems = []
    want_fatal = pattern_codes(mod.FATAL_PATTERNS)
    want_transient = pattern_codes(mod.TRANSIENT_PATTERNS)
    doc_fatal = set(re.findall(r"\b(\d{3})\b", fatal))
    doc_trans = set(re.findall(r"\b(\d{3})\b", trans))
    if doc_fatal != want_fatal:
        problems.append(f"致命错误码不一致：文档 {sorted(doc_fatal)}，代码 {sorted(want_fatal)}")
    if doc_trans != want_transient:
        problems.append(f"瞬态错误码不一致：文档 {sorted(doc_trans)}，代码 {sorted(want_transient)}")
    if "支付/交易" not in fatal or "扣款状态" not in fatal:
        problems.append("致命错误小节缺少支付/交易类兜底说明（不自动重试、转人工确认扣款状态）")
    if "无法归类" not in sec or "瞬态" not in sec:
        problems.append("Error Classification 未写明「无法归类的错误默认按瞬态」")
    for kw in ("死循环", "幻觉", "格式"):
        if kw not in logical:
            problems.append(f"逻辑错误小节缺少示例「{kw}」")
    # 状态枚举双向：失败状态必须出现；生命周期状态必须出现并标注不得传入
    for st in sorted(mod.ALLOWED_STATUS):
        if st not in doc:
            problems.append(f"失败状态枚举 {st} 未在文档出现")
    if "pending / resolved" not in doc:
        problems.append("文档未说明 pending / resolved 属任务生命周期状态（不得传入）")
    return problems


# ---------- 10. 事务属性推断锚点 ----------
def check_inference_anchors(doc: str, mod) -> list:
    """推断规则的文档锚点 + 代码行为探针双向对账（历史缺陷：推断规则曾三方分叉且门禁零覆盖）"""
    m = re.search(r"#### 事务属性推断(.*?)(?=\n### |\n## |\Z)", doc, re.S)
    if not m:
        return ["SKILL.md 缺少「事务属性推断」小节"]
    sec = m.group(1)
    problems = []
    if "对所有任务类型生效" not in sec:
        problems.append("推断小节缺少锚点「最终动作关键词对所有任务类型生效」")
    if "reversible" not in sec or "readonly" not in sec:
        problems.append("推断小节缺少默认值锚点（media→reversible / subagent,workflow→readonly）")
    if "显式传入" not in sec:
        problems.append("推断小节缺少 workflow 副作用「显式传入 tx_attr」锚点")
    # 代码行为探针：默认推断必须与文档声称一致
    if not hasattr(mod, "infer_tx_attr"):
        problems.append("resume_decide.py 缺少 infer_tx_attr")
        return problems
    probes = [
        (mod.TaskType.MEDIA, mod.TxAttr.REVERSIBLE, "media 默认"),
        (mod.TaskType.SUBAGENT, mod.TxAttr.READONLY, "subagent 默认"),
        (mod.TaskType.WORKFLOW, mod.TxAttr.READONLY, "workflow 默认"),
    ]
    for task_type, want, label in probes:
        sig = mod.TaskSignal(task_type, "gate-probe", "failed", "timeout")
        got = mod.infer_tx_attr(sig)
        if got != want:
            problems.append(f"代码推断行为与文档不符：{label}应为 {want.value}，实际 {got.value}")
    return problems


CHECKS = [
    ("阶段-错误矩阵", check_matrix),
    ("全抖动退避参数", check_backoff),
    ("语义相似度阈值", check_threshold),
    ("恢复摘要模板", check_summary_template),
    ("最终动作关键词", check_final_keywords),
    ("Retry Policy 口径", check_retry_policy),
    ("旧称清理", check_stale_terms),
    ("信号字段完备性", check_signal_fields),
    ("错误分类与状态枚举", check_error_classification),
    ("事务属性推断锚点", check_inference_anchors),
]


def main() -> int:
    parser = argparse.ArgumentParser(description="SKILL.md 与 resume_decide.py 双源一致性对账")
    parser.add_argument("--skill-dir", default=None,
                        help="技能根目录（默认：脚本所在目录的上一级）")
    args = parser.parse_args()
    skill_dir = Path(args.skill_dir).resolve() if args.skill_dir \
        else Path(__file__).resolve().parent.parent
    doc_path = skill_dir / "SKILL.md"
    if not doc_path.is_file():
        print(f"[失败] 找不到 {doc_path}")
        return 1
    doc = doc_path.read_text(encoding="utf-8")
    mod = load_decide_module(skill_dir)

    all_problems: list = []
    for name, fn in CHECKS:
        problems = fn(doc, mod)
        if problems:
            for p in problems:
                print(f"[失败] {name}：{p}")
            all_problems.extend(problems)
        else:
            print(f"[通过] {name}")

    if all_problems:
        print(f"结论：双源不一致（{len(all_problems)} 项）")
        return 1
    print("结论：SKILL.md 与 resume_decide.py 双源一致")
    return 0


if __name__ == "__main__":
    sys.exit(main())
