#!/usr/bin/env python3
"""
auto-resume-tasks · 一致性门禁必红用例 (pytest)
门禁原则：永不失败的门禁等于没有门禁。
本文件先证明门禁对当前技能目录通过（绿），再对 SKILL.md 的每类口径
构造篡改副本，证明门禁在这些输入上真的失败（必红）。
运行： pytest scripts/test_check_consistency.py -v
"""
import re
import shutil
import subprocess
import sys
from pathlib import Path

SCRIPTS_DIR = Path(__file__).resolve().parent
SKILL_ROOT = SCRIPTS_DIR.parent
GATE = SCRIPTS_DIR / "check_consistency.py"


def run_gate(skill_dir: Path) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, str(GATE), "--skill-dir", str(skill_dir)],
        capture_output=True, text=True,
    )


def mutated_skill_dir(tmp_path: Path, mutate=None, mutate_code=None) -> Path:
    """复制技能目录到临时位置并施加篡改（文档和/或代码）。"""
    dst = tmp_path / "auto-resume-tasks-mutated"
    shutil.copytree(SKILL_ROOT, dst, ignore=shutil.ignore_patterns(
        "__pycache__", ".pytest_cache"))
    if mutate:
        doc = (dst / "SKILL.md").read_text(encoding="utf-8")
        (dst / "SKILL.md").write_text(mutate(doc), encoding="utf-8")
    if mutate_code:
        code = (dst / "scripts" / "resume_decide.py").read_text(encoding="utf-8")
        (dst / "scripts" / "resume_decide.py").write_text(mutate_code(code),
                                                          encoding="utf-8")
    return dst


def assert_gate_fails(tmp_path: Path, mutate=None, label: str = "", mutate_code=None):
    # 兼容两种调用：位置式 (tmp, doc_mutate, "label") 与
    # 关键字式 (tmp, mutate_code=..., label=...)
    result = run_gate(mutated_skill_dir(tmp_path, mutate, mutate_code))
    assert result.returncode == 1, f"{label}：门禁未失败，输出：\n{result.stdout}"
    assert "[失败]" in result.stdout, f"{label}：失败输出缺 [失败] 标记"


def assert_gate_passes(tmp_path: Path, mutate=None, label: str = ""):
    result = run_gate(mutated_skill_dir(tmp_path, mutate))
    assert result.returncode == 0, f"{label}：门禁应通过，输出：\n{result.stdout}"


# ---------- 绿：当前目录必须通过 ----------
def test_gate_passes_current_repo():
    result = run_gate(SKILL_ROOT)
    assert result.returncode == 0, f"门禁应通过，输出：\n{result.stdout}"


# ---------- 必红：矩阵上限被改 ----------
def test_gate_fails_when_matrix_cap_mutated(tmp_path):
    assert_gate_fails(
        tmp_path,
        lambda d: d.replace("| Init | 全抖动退避，最多 3 次 |", "| Init | 全抖动退避，最多 5 次 |"),
        "矩阵上限 3→5",
    )


# ---------- 必红：退避参数被改 ----------
def test_gate_fails_when_tbase_mutated(tmp_path):
    assert_gate_fails(
        tmp_path,
        lambda d: d.replace("t_base = 5s", "t_base = 6s"),
        "t_base 5s→6s",
    )


# ---------- 必红：fallback 阈值被改 ----------
def test_gate_fails_when_threshold_mutated(tmp_path):
    assert_gate_fails(
        tmp_path,
        lambda d: d.replace("Jaccard ≥ 0.8", "Jaccard ≥ 0.7"),
        "fallback 阈值 0.8→0.7",
    )


# ---------- 必红：摘要模板删字段 ----------
def test_gate_fails_when_summary_field_removed(tmp_path):
    assert_gate_fails(
        tmp_path,
        lambda d: d.replace("前置动作：{none | undo | compensate}\n", ""),
        "摘要模板删「前置动作」行",
    )


# ---------- 必红：最终动作关键词从文档删除 ----------
def test_gate_fails_when_final_keyword_removed(tmp_path):
    assert_gate_fails(
        tmp_path,
        lambda d: d.replace("付款、支付、部署、删库、删除、提交、发送", "付款、支付、部署、删库、删除、提交"),
        "文档删「发送」关键词",
    )


# ---------- 必红：Retry Policy 口径被改 ----------
def test_gate_fails_when_retry_policy_mutated(tmp_path):
    assert_gate_fails(
        tmp_path,
        lambda d: d.replace("- 逻辑错误：最多 1 次", "- 逻辑错误：最多 2 次"),
        "Retry Policy 逻辑 1→2 次",
    )


# ---------- 必红：旧称回潮 ----------
def test_gate_fails_when_stale_term_returns(tmp_path):
    assert_gate_fails(
        tmp_path,
        lambda d: d.replace("语义指纹熔断防死循环", "语义哈希熔断防死循环"),
        "旧称「语义哈希」回潮",
    )


# ---------- 必红：信号字段表丢 prompt 片段 ----------
def test_gate_fails_when_prompt_field_removed(tmp_path):
    assert_gate_fails(
        tmp_path,
        lambda d: d.replace("| 任务 prompt 片段 | 触发任务时的原始 prompt 片段 | 可选；缺失时无法识别最终动作关键词 |\n", ""),
        "信号字段表删「任务 prompt 片段」行",
    )


# ---------- 必红：触发模板丢 prompt 提示 ----------
def test_gate_fails_when_prompt_hint_removed_from_template(tmp_path):
    assert_gate_fails(
        tmp_path,
        lambda d: d.replace(" 阶段={phase} prompt提示={prompt_hint}", " 阶段={phase}"),
        "触发模板删 prompt提示",
    )



# ---------- 二轮加固必红：门禁绕过形态逐项钉死 ----------
def test_gate_fails_matrix_extra_row(tmp_path):
    # T01：文档侧多出代码 MATRIX 没有的阶段行
    assert_gate_fails(
        tmp_path,
        lambda d: d.replace(
            "| Finalizing | 全抖动退避，最多 2 次 | 立即放弃 | 重试 1 次 |",
            "| Finalizing | 全抖动退避，最多 2 次 | 立即放弃 | 重试 1 次 |\n"
            "| Deploying | 全抖动退避，最多 9 次 | 立即放弃 | 重试 1 次 |"),
        "矩阵加 Deploying 行",
    )


def test_gate_fails_matrix_extra_column(tmp_path):
    # T02：矩阵行追加第 5 列
    assert_gate_fails(
        tmp_path,
        lambda d: d.replace(
            "| Init | 全抖动退避，最多 3 次 | 立即放弃 | 重试 1 次 |",
            "| Init | 全抖动退避，最多 3 次 | 立即放弃 | 重试 1 次 | 脚注 |"),
        "矩阵加第 5 列",
    )


def test_gate_fails_decoy_matrix_row(tmp_path):
    # T23：真实上限被改 + 节内塞回正确值诱饵行，first-match 顶替不再有效
    def mutate(d):
        d = d.replace("| Processing | 全抖动退避，最多 3 次 | 立即放弃 | 重试 1 次 |",
                      "| Processing | 全抖动退避，最多 9 次 | 立即放弃 | 重试 1 次 |")
        return d.replace(
            "| Finalizing | 全抖动退避，最多 2 次 | 立即放弃 | 重试 1 次 |",
            "| Finalizing | 全抖动退避，最多 2 次 | 立即放弃 | 重试 1 次 |\n"
            "| Processing | 全抖动退避，最多 3 次 | 立即放弃 | 重试 1 次 |")
    assert_gate_fails(tmp_path, mutate, "诱饵矩阵行顶替")


def test_gate_fails_payment_guard_removed(tmp_path):
    # T15：错误分类清单（第三类双源口径）删除支付兜底行。
    # 用正则按关键内容定位整行，避免正文措辞微调导致锚点失配
    def mutate(d):
        return re.sub(r"^-\s*支付/交易类失败.*$", "", d, flags=re.M)
    assert_gate_fails(tmp_path, mutate, "删支付/交易类兜底行")


def test_gate_fails_cosine_threshold_095(tmp_path):
    # T08：余弦 0.9 → 0.95（"0.9"⊂"0.95" 的子串检查已升级为行级数值枚举）
    assert_gate_fails(
        tmp_path,
        lambda d: d.replace("余弦 > 0.9", "余弦 > 0.95"),
        "余弦阈值 0.9→0.95",
    )


def test_gate_fails_conflicting_backoff_value(tmp_path):
    # T17：退避参数出现第二个冲突取值
    assert_gate_fails(
        tmp_path,
        lambda d: d.replace("- t_base = 5s, t_max = 60s",
                            "- t_base = 5s, t_max = 60s\n- t_base = 6s（旧值仅存档）"),
        "退避参数第二处冲突值",
    )


def test_gate_fails_summary_enum_shrunk(tmp_path):
    # T19：摘要模板值枚举缩水
    assert_gate_fails(
        tmp_path,
        lambda d: d.replace("前置动作：{none | undo | compensate}", "前置动作：{undo}"),
        "摘要模板前置动作枚举缩水",
    )


def test_gate_fails_code_allow_flag(tmp_path):
    # C2：代码侧把某组合改为禁止续跑而文档不变
    assert_gate_fails(
        tmp_path,
        mutate_code=lambda c: c.replace(
            "(Phase.INIT, ErrorClass.TRANSIENT): (3, True),",
            "(Phase.INIT, ErrorClass.TRANSIENT): (3, False),"),
        label="代码侧 allow 标志篡改",
    )


# ---------- 绿灯回归：值对账而非字面量对账 ----------
def test_gate_green_synonym_rewording(tmp_path):
    # 同义改写（数值与集合不变）应通过——防止门禁退化为写死字面量
    assert_gate_passes(
        tmp_path,
        lambda d: d.replace("| Finalizing | 全抖动退避，最多 2 次 |",
                            "| Finalizing | 退避重试，最多 2 次 |"),
        "矩阵同义改写",
    )


def test_gate_green_matrix_row_reorder(tmp_path):
    # 行序对调（集合不变）应通过
    def mutate(d):
        init_row = "| Init | 全抖动退避，最多 3 次 | 立即放弃 | 重试 1 次 |\n"
        proc_row = "| Processing | 全抖动退避，最多 3 次 | 立即放弃 | 重试 1 次 |\n"
        return d.replace(init_row + proc_row, proc_row + init_row)
    assert_gate_passes(tmp_path, mutate, "矩阵行序对调")


def test_gate_fails_inference_anchor_removed(tmp_path):
    # R5：推断规则锚点被删（历史缺陷：推断规则曾三方分叉且门禁零覆盖）
    assert_gate_fails(
        tmp_path,
        lambda d: d.replace("**最终动作关键词对所有任务类型生效**（命中即判 `final`，优先于默认值）",
                            "**最终动作关键词仅对 subagent 生效**（命中即判 `final`）"),
        "推断锚点「对所有任务类型生效」被改",
    )


def test_gate_fails_code_inference_behavior_drift(tmp_path):
    # R5 代码侧：infer_tx_attr 默认行为被改而文档不变 → 行为探针必须报警
    assert_gate_fails(
        tmp_path,
        mutate_code=lambda c: c.replace(
            "    if sig.task_type == TaskType.MEDIA:\n        return TxAttr.REVERSIBLE          # 媒体可覆盖重提交",
            "    if sig.task_type == TaskType.MEDIA:\n        return TxAttr.READONLY"),
        label="代码 media 默认推断漂移",
    )

if __name__ == "__main__":
    import pytest
    raise SystemExit(pytest.main([__file__, "-v"]))
