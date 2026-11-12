#!/usr/bin/env python3
"""
auto-resume-tasks · 决策链路测试集 (pytest)
覆盖 cases.md 的 E01-E06 主链路，以及边界与推断规则。
运行： pytest scripts/test_resume_decide.py -v
"""
import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from resume_decide import (
    TaskType, ErrorClass, Phase, TxAttr, DecisionAction, PreAction,
    TaskSignal, classify_error, infer_tx_attr, infer_pre_action,
    semantic_similar, jitter_backoff, decide, Decision, T_BASE, T_MAX,
    SEMANTIC_FALLBACK_THRESHOLD,
)


# ---------- E01-E06 主链路 ----------
def test_E01_network_timeout_transient_readonly():
    sig = TaskSignal(TaskType.SUBAGENT, "t1", "failed",
                     "Connection timeout: gateway timeout after 30s", Phase.PROCESSING)
    d = decide(sig)
    assert d.error_class == ErrorClass.TRANSIENT
    assert d.tx_attr == TxAttr.READONLY
    assert d.action == DecisionAction.RESUME


def test_E02_rate_limit_transient_reversible():
    sig = TaskSignal(TaskType.MEDIA, "t2", "failed",
                     "HTTP 429: Too Many Requests", Phase.PROCESSING)
    d = decide(sig)
    assert d.error_class == ErrorClass.TRANSIENT
    assert d.tx_attr == TxAttr.REVERSIBLE
    assert d.action == DecisionAction.RESUME


def test_E03_token_expired_fatal_readonly():
    sig = TaskSignal(TaskType.SUBAGENT, "t3", "failed",
                     "HTTP 401: Invalid or expired token", Phase.INIT)
    d = decide(sig)
    assert d.error_class == ErrorClass.FATAL
    assert d.action == DecisionAction.ABORT


def test_E04_format_error_logical_readonly():
    sig = TaskSignal(TaskType.SUBAGENT, "t4", "failed",
                     "Output validation failed: response format does not match", Phase.PROCESSING)
    d = decide(sig)
    assert d.error_class == ErrorClass.LOGICAL
    assert d.action == DecisionAction.RESUME


def test_E05_repeat_error_semantic_circuit_break():
    sig = TaskSignal(TaskType.WORKFLOW, "t5", "failed",
                     "node X failed with timeout", Phase.PROCESSING)
    d = decide(sig, history_errors=["node X failed with timeout"])
    assert d.action == DecisionAction.HUMAN
    assert "熔断" in d.note


def test_E06_payment_fatal_final_never_retry():
    sig = TaskSignal(TaskType.WORKFLOW, "t6", "failed",
                     "Payment gateway declined transaction", Phase.FINALIZING,
                     prompt_hint="执行付款")
    d = decide(sig)
    assert d.tx_attr == TxAttr.FINAL
    assert d.action == DecisionAction.HUMAN
    assert "绝不自动重试" in d.note


# ---------- 错误分类边界 ----------
def test_classify_fatal_400():
    assert classify_error("400 Bad Request: invalid param") == ErrorClass.FATAL


def test_classify_transient_503():
    assert classify_error("503 Service Unavailable") == ErrorClass.TRANSIENT


def test_classify_logical_hallucination():
    assert classify_error("agent entered infinite loop and hallucinated") == ErrorClass.LOGICAL


def test_classify_default_transient():
    # 未知错误默认按瞬态（宁可重试，不轻易放弃）
    assert classify_error("weird undefined glitch") == ErrorClass.TRANSIENT


# ---------- 事务属性推断 ----------
def test_infer_subagent_default_readonly():
    sig = TaskSignal(TaskType.SUBAGENT, "x", "failed", "timeout")
    assert infer_tx_attr(sig) == TxAttr.READONLY


def test_infer_media_default_reversible():
    sig = TaskSignal(TaskType.MEDIA, "x", "failed", "timeout")
    assert infer_tx_attr(sig) == TxAttr.REVERSIBLE


def test_infer_final_keyword_upgrade():
    sig = TaskSignal(TaskType.SUBAGENT, "x", "failed", "timeout",
                     prompt_hint="请帮我发送这封邮件并部署")
    assert infer_tx_attr(sig) == TxAttr.FINAL


def test_infer_explicit_override():
    sig = TaskSignal(TaskType.SUBAGENT, "x", "failed", "timeout",
                     tx_attr=TxAttr.COMPENSATABLE)
    assert infer_tx_attr(sig) == TxAttr.COMPENSATABLE


# ---------- 语义相似度 fallback ----------
def test_semantic_similar_true():
    assert semantic_similar("node X failed with timeout",
                            "node X failed due to timeout") is True


def test_semantic_similar_false_diff_type():
    # 错误类型不同不应误判（调用方需先按类型过滤）
    assert semantic_similar("timeout occurred", "400 bad request") is False


# ---------- 阶段矩阵上限 ----------
def test_finalizing_transient_cap_2():
    sig = TaskSignal(TaskType.SUBAGENT, "f", "failed",
                     "gateway timeout after 30s", Phase.FINALIZING)
    # 已重试 2 次，达到 Finalizing 瞬态上限 -> 转人工
    d = decide(sig, current_retry=2)
    assert d.action == DecisionAction.HUMAN


def test_processing_transient_cap_3():
    sig = TaskSignal(TaskType.SUBAGENT, "p", "failed",
                     "gateway timeout after 30s", Phase.PROCESSING)
    d = decide(sig, current_retry=3)
    assert d.action == DecisionAction.HUMAN


def test_phase_default_processing():
    sig = TaskSignal(TaskType.SUBAGENT, "d", "failed", "timeout")
    d = decide(sig)
    assert d.phase == Phase.PROCESSING


# ---------- 全抖动退避 ----------
def test_jitter_in_range():
    for attempt in range(4):
        t = jitter_backoff(attempt)
        assert 0 <= t <= 60.0


def test_jitter_capped_by_tmax():
    # 多次重试后理论窗口被 t_max 限制
    assert jitter_backoff(10) <= 60.0


# ---------- 前置动作（pre_action） ----------
def test_pre_action_media_overwrite_no_undo():
    # media 覆盖重提交：可逆但无需撤销（对齐 cases.md E02 口径）
    sig = TaskSignal(TaskType.MEDIA, "m", "failed", "gateway timeout", Phase.PROCESSING)
    d = decide(sig)
    assert d.action == DecisionAction.RESUME
    assert d.pre_action == PreAction.NONE


def test_pre_action_reversible_subagent_undo():
    sig = TaskSignal(TaskType.SUBAGENT, "r", "failed", "gateway timeout",
                     Phase.PROCESSING, tx_attr=TxAttr.REVERSIBLE)
    d = decide(sig)
    assert d.action == DecisionAction.RESUME
    assert d.pre_action == PreAction.UNDO


def test_pre_action_compensatable_compensate():
    sig = TaskSignal(TaskType.SUBAGENT, "c", "failed", "gateway timeout",
                     Phase.PROCESSING, tx_attr=TxAttr.COMPENSATABLE)
    d = decide(sig)
    assert d.action == DecisionAction.RESUME
    assert d.pre_action == PreAction.COMPENSATE


def test_final_action_no_pre_action():
    sig = TaskSignal(TaskType.WORKFLOW, "f", "failed", "gateway timeout",
                     Phase.FINALIZING, prompt_hint="执行付款")
    d = decide(sig)
    assert d.action == DecisionAction.HUMAN
    assert d.pre_action == PreAction.NONE


def test_infer_pre_action_media_reversible_is_none():
    sig = TaskSignal(TaskType.MEDIA, "m", "failed", "timeout")
    assert infer_pre_action(sig, TxAttr.REVERSIBLE) == PreAction.NONE


# ---------- 二轮深审修复：中文指纹 / ID 归一 / 重试兜底 / 入口防呆 ----------
def test_cjk_identical_errors_circuit_break():
    # 评审 H2：_keywords 原本只匹配 [a-z0-9]+，纯中文错误关键词集为空 → 熔断失效
    err = "请求超时，网关无响应"
    sig = TaskSignal(TaskType.SUBAGENT, "c1", "failed", err, Phase.PROCESSING)
    d = decide(sig, history_errors=[err])
    assert d.action == DecisionAction.HUMAN
    assert "熔断" in d.note


def test_cjk_similar_true_false():
    assert semantic_similar("请求超时，网关无响应", "请求超时，网关无响应") is True
    # 不同中文错误不误熔断
    assert semantic_similar("请求超时，网关无响应", "请求失败，网关无响应") is False


def test_id_normalized_circuit_break():
    # 评审 H3：req_id/时间戳等变量片段压垮 Jaccard 导致漏熔断
    d = decide(
        TaskSignal(TaskType.SUBAGENT, "id1", "failed",
                   "request timeout after 30s (req_id=000001)", Phase.PROCESSING),
        history_errors=["request timeout after 30s (req_id=000002)"])
    assert d.action == DecisionAction.HUMAN
    assert "熔断" in d.note


def test_decide_fallback_retry_from_history_length():
    # 评审 H3：调用方不传 current_retry 时按历史条数兜底，上限不再永不触发。
    # 历史用同类但措辞不同的瞬态错误，避免误触发语义熔断
    hist = ["connection reset by peer", "read operation timed out",
            "503 service unavailable"]
    sig = TaskSignal(TaskType.SUBAGENT, "fb1", "failed",
                     "gateway timeout after 30s", Phase.PROCESSING)
    d = decide(sig, history_errors=hist)             # 已重试 3 次 = 上限
    assert d.action == DecisionAction.HUMAN
    assert "达到重试上限" in d.note
    d2 = decide(sig, history_errors=hist[:2])        # 已重试 2 次 < 上限
    assert d2.action == DecisionAction.RESUME
    assert d2.retry_count == 3


def test_final_keyword_negation_exempt():
    # 评审 M6 + 复核新发现：「撤销删除」「取消支付」「请勿删除」「不删除」语义相反，不应升级最终动作
    for hint in ("收到纠错指令后撤销删除操作", "取消支付并重试下单",
                 "请勿删除该文件", "不删除任何文件", "撤销了删除操作"):
        sig = TaskSignal(TaskType.SUBAGENT, "n", "failed", "gateway timeout",
                         Phase.PROCESSING, prompt_hint=hint)
        assert infer_tx_attr(sig) == TxAttr.READONLY, hint
    # 反向：无否定语义的正常最终动作仍命中
    assert infer_tx_attr(TaskSignal(
        TaskType.SUBAGENT, "n2", "failed", "gateway timeout",
        Phase.PROCESSING, prompt_hint="请立即付款并提交")) == TxAttr.FINAL


def test_final_keyword_en_word_boundary():
    # 评审 M6：resend/deleted 不应命中 \bsend\b / \bdelete\b
    assert infer_tx_attr(TaskSignal(
        TaskType.SUBAGENT, "w1", "failed", "timeout",
        prompt_hint="please resend the report")) == TxAttr.READONLY
    assert infer_tx_attr(TaskSignal(
        TaskType.SUBAGENT, "w2", "failed", "timeout",
        prompt_hint="please send the report")) == TxAttr.FINAL


def test_task_signal_normalizes_status():
    # 评审 L2：大小写/空白漂移不应把真实失败全部推向人工
    d = decide(TaskSignal(TaskType.SUBAGENT, "s1", "  FAILED  ", "gateway timeout",
                          Phase.PROCESSING))
    assert d.action == DecisionAction.RESUME


def test_task_signal_rejects_illegal_enums():
    # 评审 M4/M5：裸字符串在此收敛，非法值响亮报错而非半路崩溃/静默错判
    import pytest
    with pytest.raises(ValueError):
        TaskSignal("bogus", "x", "failed", "timeout")
    with pytest.raises(ValueError):
        TaskSignal(TaskType.SUBAGENT, "x", "failed", "timeout", phase="bogus")
    # 裸字符串的合法值可用
    sig = TaskSignal("subagent", "x", "failed", "gateway timeout", phase="Processing")
    assert sig.task_type == TaskType.SUBAGENT
    assert sig.phase == Phase.PROCESSING


def test_task_signal_tolerates_none_fields():
    # 评审 M8：prompt_hint/error 为 None 不再在防呆之前崩溃
    d = decide(TaskSignal(TaskType.SUBAGENT, "x", "failed", None, None, None, None))
    assert d.action == DecisionAction.HUMAN
    assert "错误信息缺失" in d.note


def test_empty_error_human():
    d = decide(TaskSignal(TaskType.SUBAGENT, "e1", "failed", "!!!", Phase.PROCESSING))
    assert d.action == DecisionAction.HUMAN
    assert "错误信息缺失" in d.note


def test_negative_retry_clamped():
    # 评审 L3：负数重试计数不再产出负数摘要
    d = decide(TaskSignal(TaskType.SUBAGENT, "r-", "failed", "gateway timeout",
                          Phase.PROCESSING), current_retry=-3)
    assert d.action == DecisionAction.RESUME
    assert d.retry_count == 1


def test_jitter_no_overflow():
    # 评审 L4：公共 API 大参数不再 OverflowError
    assert jitter_backoff(10 ** 6) <= 60.0


def test_invalid_token_order_fatal():
    # 评审 L5：语序颠倒的 token 失效描述仍判致命
    assert classify_error("invalid token format") == ErrorClass.FATAL


def test_multiline_logical_error():
    # 评审 M7：多行错误文本不再断开模式匹配
    assert classify_error("Output validation\nfailed") == ErrorClass.LOGICAL


def test_transient_code_boundary():
    # 评审 M3：429/503 加词边界，"5039" 等数字串不再误判为瞬态
    assert classify_error("output validation failed for request 5039") == ErrorClass.LOGICAL


def test_backoff_note_reports_window():
    # 评审 M1：note 报告退避窗口而非随机采样值（计划值≠实际值问题根治）
    d = decide(TaskSignal(TaskType.SUBAGENT, "bw", "failed", "gateway timeout",
                          Phase.PROCESSING))
    assert "计划退避 0~5s" in d.note
    assert "全抖动随机" in d.note


# ---------- 残余风险整改（1.2.1）：近义归一 / hex 精确化 ----------
def test_cjk_synonym_variant_circuit_break():
    # 评审复核新发现：「网关没有响应」vs「网关无响应」近义改写曾漏熔断
    d = decide(TaskSignal(TaskType.SUBAGENT, "syn1", "failed",
                          "请求超时，网关没有响应", Phase.PROCESSING),
               history_errors=["请求超时，网关无响应"])
    assert d.action == DecisionAction.HUMAN
    assert "熔断" in d.note


def test_cjk_synonym_no_false_positive():
    # 归一化不得引入误熔断：不同错误仍不相似
    assert semantic_similar("请求超时，网关无响应", "请求失败，网关无响应") is False


def test_normalize_ids_requires_digit():
    # 评审复核新发现：纯 hex 字母英文词（facade）不应被误归一
    from resume_decide import _normalize_ids
    assert "facade" in _normalize_ids("facade layer crashed")
    assert "<id>" in _normalize_ids("request timeout (req_id=000001)")
    assert "<id>" in _normalize_ids("job a3f9c2 retry exhausted")  # 含数字的 hex 仍归一
    assert "abcdef" in _normalize_ids("word abcdef here")          # 纯字母 hex 形词保留


# ---------- 恢复摘要模板（与 SKILL.md 6.5 对账） ----------
def test_summary_has_nine_fields():
    sig = TaskSignal(TaskType.SUBAGENT, "s9", "failed", "gateway timeout",
                     Phase.PROCESSING, tx_attr=TxAttr.REVERSIBLE)
    d = decide(sig)
    text = d.summary("s9", "subagent")
    lines = text.splitlines()
    assert lines[0] == "【恢复摘要】"
    keys = [ln.split("：")[0] for ln in lines[1:]]
    assert keys == ["任务类型", "任务ID", "错误类型", "事务属性", "阶段",
                    "重试次数", "前置动作", "恢复动作", "备注"]


def test_circuit_break_note_marks_fallback():
    sig = TaskSignal(TaskType.WORKFLOW, "w", "failed",
                     "node X failed with timeout", Phase.PROCESSING)
    d = decide(sig, history_errors=["node X failed with timeout"])
    assert d.action == DecisionAction.HUMAN
    assert "semantic=fallback" in d.note


# ---------- 状态防呆与相似度归一化 ----------
def test_status_resolved_skips_recovery():
    # check_pending_tasks 的 resolved 任务不得被"恢复"
    sig = TaskSignal(TaskType.MEDIA, "r1", "resolved", "no error text", Phase.PROCESSING)
    d = decide(sig)
    assert d.action == DecisionAction.HUMAN
    assert "非失败状态" in d.note


def test_status_pending_skips_recovery():
    sig = TaskSignal(TaskType.SUBAGENT, "r2", "pending", "whatever", Phase.PROCESSING)
    d = decide(sig)
    assert d.action == DecisionAction.HUMAN
    assert "非失败状态" in d.note


def test_semantic_timed_out_normalizes_to_timeout():
    # 评审发现的漏熔断反例："timed out" 与 "timeout" 词集原本不相交
    assert semantic_similar("job timed out", "job timeout") is True


def test_payment_error_human_even_without_prompt_hint():
    # 评审实测反例：付款失败漏传 prompt_hint 时曾被默认瞬态而重试；
    # 1.2.0 起由支付兜底直接转人工确认扣款状态（不再误判为 RESUME/ABORT）
    sig = TaskSignal(TaskType.WORKFLOW, "pay1", "failed",
                     "Payment gateway declined transaction", Phase.FINALIZING)
    d = decide(sig)
    assert d.action == DecisionAction.HUMAN
    assert "扣款状态" in d.note


def test_payment_timeout_human_not_abort():
    # payment+timeout：无法自动判断是否已扣款，转人工而非放弃（评审 L6）
    d = decide(TaskSignal(TaskType.WORKFLOW, "pt", "failed",
                          "payment gateway timeout", Phase.PROCESSING))
    assert d.action == DecisionAction.HUMAN
    assert "扣款状态" in d.note


def test_payment_with_fatal_code_aborts():
    # 残余风险整改 R1：致命错误码优先于支付兜底——
    # 含 payment 字样但命中 401 的按致命放弃（请求未成功、未产生扣款）
    d = decide(TaskSignal(TaskType.SUBAGENT, "pf", "failed",
                          "HTTP 401: payment token expired", Phase.PROCESSING))
    assert d.action == DecisionAction.ABORT
    assert d.error_class == ErrorClass.FATAL


def test_chinese_payment_error_human():
    # 复核 F3（中危）：支付兜底中英文均识别——
    # 「订单支付失败」此前漏识别，会被默认瞬态自动重试（重复扣款风险）
    for err in ("订单支付失败：余额不足", "扣款异常，请核实账户", "交易失败：银行拒绝该笔交易"):
        d = decide(TaskSignal(TaskType.WORKFLOW, "cp", "failed", err, Phase.PROCESSING))
        assert d.action == DecisionAction.HUMAN, err
        assert "扣款状态" in d.note, err


def test_connection_declined_still_transient():
    # 英文裸 declined 不纳入支付兜底（connection declined 属瞬态）
    d = decide(TaskSignal(TaskType.SUBAGENT, "cd", "failed",
                          "connection declined by peer", Phase.PROCESSING))
    assert d.action == DecisionAction.RESUME


# ---------- adapter 前置动作路由（undo/compensate 先于续跑） ----------
def test_adapter_undo_before_resume():
    from adapter import ResumeAdapter, Handlers
    calls = []
    sig = TaskSignal(TaskType.SUBAGENT, "a1", "failed", "gateway timeout",
                     Phase.PROCESSING, tx_attr=TxAttr.REVERSIBLE)
    d = decide(sig)
    h = Handlers(
        resume_subagent=lambda tid, instr: calls.append("resume"),
        undo=lambda s, dec: calls.append("undo"),
    )
    ResumeAdapter(h, wait=False).dispatch(sig, d)
    assert calls == ["undo", "resume"]


def test_adapter_compensate_before_resume():
    from adapter import ResumeAdapter, Handlers
    calls = []
    sig = TaskSignal(TaskType.SUBAGENT, "a2", "failed", "gateway timeout",
                     Phase.PROCESSING, tx_attr=TxAttr.COMPENSATABLE)
    d = decide(sig)
    h = Handlers(
        resume_subagent=lambda tid, instr: calls.append("resume"),
        compensate=lambda s, dec: calls.append("compensate"),
    )
    ResumeAdapter(h, wait=False).dispatch(sig, d)
    assert calls == ["compensate", "resume"]


def test_adapter_media_no_undo():
    from adapter import ResumeAdapter, Handlers
    calls = []
    sig = TaskSignal(TaskType.MEDIA, "a3", "failed", "gateway timeout", Phase.PROCESSING)
    d = decide(sig)
    h = Handlers(
        resume_media=lambda p: calls.append("resume_media"),
        undo=lambda s, dec: calls.append("undo"),
    )
    ResumeAdapter(h, wait=False).dispatch(sig, d)
    assert calls == ["resume_media"]


def test_adapter_human_skips_pre_action():
    from adapter import ResumeAdapter, Handlers
    calls = []
    sig = TaskSignal(TaskType.WORKFLOW, "a4", "failed", "gateway timeout",
                     Phase.FINALIZING, prompt_hint="执行付款")
    d = decide(sig)
    h = Handlers(
        on_human=lambda s, dec: calls.append("human"),
        undo=lambda s, dec: calls.append("undo"),
    )
    ResumeAdapter(h, wait=False).dispatch(sig, d)
    assert calls == ["human"]


# ---------- 二轮深审修复：DispatchResult 执行状态 / 静默失败根治 / Retry-After ----------
def test_dispatch_reports_missing_handlers(capfd):
    # 评审 H1：全 None handlers 时不再"什么都不做且无告警"
    from adapter import ResumeAdapter, Handlers
    sig = TaskSignal(TaskType.SUBAGENT, "h1", "failed", "gateway timeout", Phase.PROCESSING)
    d = decide(sig)
    result = ResumeAdapter(Handlers(), wait=False).dispatch(sig, d)
    assert result.executed is False
    assert any("resume_subagent 未注入" in w for w in result.warnings)
    out = capfd.readouterr().out
    assert "【恢复摘要】" in out and "恢复警告" in out  # 摘要仍输出


def test_dispatch_abort_without_handler_warns():
    # 评审 H1：ABORT 分支不再完全静默
    from adapter import ResumeAdapter, Handlers
    sig = TaskSignal(TaskType.SUBAGENT, "h2", "failed", "HTTP 401 invalid token", Phase.INIT)
    d = decide(sig)
    result = ResumeAdapter(Handlers(), wait=False).dispatch(sig, d)
    assert result.executed is False
    assert any("on_abort 未注入" in w for w in result.warnings)


def test_dispatch_human_without_handler_warns():
    from adapter import ResumeAdapter, Handlers
    sig = TaskSignal(TaskType.WORKFLOW, "h3", "failed", "gateway timeout",
                     Phase.FINALIZING, prompt_hint="执行付款")
    result = ResumeAdapter(Handlers(), wait=False).dispatch(sig, decide(sig))
    assert result.executed is False
    assert any("on_human 未注入" in w for w in result.warnings)


def test_undo_missing_refuses_resume():
    # 评审 H1 最危险变体：前置动作 handler 缺失时不得静默跳过仍续跑
    from adapter import ResumeAdapter, Handlers
    calls = []
    sig = TaskSignal(TaskType.SUBAGENT, "h4", "failed", "gateway timeout",
                     Phase.PROCESSING, tx_attr=TxAttr.REVERSIBLE)
    h = Handlers(
        resume_subagent=lambda tid, instr: calls.append("resume"),
        on_human=lambda s, dec: calls.append("human"),
    )
    result = ResumeAdapter(h, wait=False).dispatch(sig, decide(sig))
    assert calls == ["human"]                      # 续跑被拒绝，转人工
    assert result.executed is False
    assert any("拒绝续跑" in w for w in result.warnings)


def test_undo_raises_refuses_resume():
    from adapter import ResumeAdapter, Handlers
    calls = []
    sig = TaskSignal(TaskType.SUBAGENT, "h5", "failed", "gateway timeout",
                     Phase.PROCESSING, tx_attr=TxAttr.REVERSIBLE)

    def boom(s, d):
        raise RuntimeError("undo failed")

    h = Handlers(
        resume_subagent=lambda tid, instr: calls.append("resume"),
        undo=boom,
        on_human=lambda s, dec: calls.append("human"),
    )
    result = ResumeAdapter(h, wait=False).dispatch(sig, decide(sig))
    assert calls == ["human"]
    assert result.pre_action_done is False
    assert any("undo 执行失败" in w for w in result.warnings)


def test_compensate_missing_refuses_resume():
    from adapter import ResumeAdapter, Handlers
    calls = []
    sig = TaskSignal(TaskType.SUBAGENT, "h6", "failed", "gateway timeout",
                     Phase.PROCESSING, tx_attr=TxAttr.COMPENSATABLE)
    h = Handlers(
        resume_subagent=lambda tid, instr: calls.append("resume"),
        on_human=lambda s, dec: calls.append("human"),
    )
    result = ResumeAdapter(h, wait=False).dispatch(sig, decide(sig))
    assert calls == ["human"]
    assert any("compensate 未注入" in w for w in result.warnings)


def test_retry_after_coordination():
    # 评审 M3：Retry-After 协调有双源承载（错误串 retry after 60s → 实际等待 60s）
    from adapter import ResumeAdapter, Handlers
    sig = TaskSignal(TaskType.MEDIA, "ra1", "failed",
                     "HTTP 429: Too Many Requests, retry after 60s", Phase.PROCESSING)
    adapter = ResumeAdapter(Handlers(), wait=False)
    assert adapter._sleep(0, sig) == 60.0          # max(抖动≤5, 60) = 60
    sig2 = TaskSignal(TaskType.MEDIA, "ra2", "failed", "HTTP 429: Too Many Requests",
                      Phase.PROCESSING)
    assert adapter._sleep(0, sig2) <= 5.0          # 无提示时维持抖动窗口


def test_resume_media_payload():
    # 补覆盖：media 续跑载荷契约（宿主据此取回原始参数）
    from adapter import ResumeAdapter, Handlers
    seen = {}
    sig = TaskSignal(TaskType.MEDIA, "m9", "failed", "gateway timeout", Phase.PROCESSING)
    h = Handlers(resume_media=lambda p: seen.update(p))
    ResumeAdapter(h, wait=False).dispatch(sig, decide(sig))
    assert seen == {"task_id": "m9", "error": "gateway timeout"}


if __name__ == "__main__":
    import pytest
    raise SystemExit(pytest.main([__file__, "-v"]))
