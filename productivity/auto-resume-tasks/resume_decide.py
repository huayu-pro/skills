#!/usr/bin/env python3
"""
auto-resume-tasks · 最小决策骨架
仅实现「错误分类 + 语义指纹 + 全抖动退避 + 事务属性」的纯逻辑决策，
不绑定任何平台 IO，便于独立单元测试与后续接入真实工具。

接入方式：
  1. 宿主 Agent 收到后台任务失败信号后（信号格式见 SKILL.md「激活与接线」），
     先按 references/host-contract.md 读取状态：human_pending 命中则静默丢弃
     本条回调（不调用本模块）；否则取出 current_retry 与 history_errors
  2. 构造 TaskSignal 调用 decide()，宿主按返回 Decision 的 action 行动：
     - resume  -> 先执行 decision.pre_action（undo/compensate），再
                  subagent_reply / workflow(resumeFromRunId) / 覆盖重提交 media
     - abort   -> 直接标记不可恢复并通知
     - human   -> 转人工审核
  3. 本文件与 SKILL.md 是同一决策逻辑的双源，修改任一侧后必须运行
     python3 scripts/check_consistency.py 对账，并跑 pytest scripts/ 回归
"""

from __future__ import annotations
import random
import re
from dataclasses import dataclass
from enum import Enum
from typing import Optional


# ---------- 枚举定义 ----------
class TaskType(str, Enum):
    SUBAGENT = "subagent"
    WORKFLOW = "workflow"
    MEDIA = "media"


class ErrorClass(str, Enum):
    TRANSIENT = "transient"   # 瞬态：值得重试
    FATAL = "fatal"           # 致命：立即放弃
    LOGICAL = "logical"       # 逻辑：有限重试


class Phase(str, Enum):
    INIT = "Init"
    PROCESSING = "Processing"
    FINALIZING = "Finalizing"


class TxAttr(str, Enum):
    READONLY = "readonly"             # 只读
    REVERSIBLE = "reversible"         # 可逆
    COMPENSATABLE = "compensatable"   # 可补偿
    FINAL = "final"                   # 最终动作（不可逆转）


class DecisionAction(str, Enum):
    RESUME = "resume"     # 续跑/重试
    ABORT = "abort"       # 放弃，不可恢复
    HUMAN = "human"       # 转人工


class PreAction(str, Enum):
    NONE = "none"              # 无前置动作
    UNDO = "undo"              # 重试前先执行撤销，清理残局
    COMPENSATE = "compensate"  # 重试前先触发补偿工作流


# ---------- 数据结构 ----------
@dataclass
class TaskSignal:
    task_type: TaskType
    task_id: str
    status: str                  # failed | timeout | interrupted
    error: str                   # 原始错误摘要
    phase: Optional[Phase] = None
    tx_attr: Optional[TxAttr] = None
    prompt_hint: str = ""        # 用于推断事务属性的原始 prompt 片段

    def __post_init__(self):
        # 入口归一化：裸字符串/大小写/None 在此收敛，非法枚举值响亮报错
        # （防裸串 task_type 在 handler 已执行后才于 summary 崩溃、
        #  防 phase 传小写串时静默查空矩阵误判、防 status 大小写漂移）
        if not isinstance(self.task_type, TaskType):
            self.task_type = TaskType(self.task_type)
        if self.phase is not None and not isinstance(self.phase, Phase):
            self.phase = Phase(self.phase)
        self.status = "" if self.status is None else str(self.status).strip().lower()
        self.error = "" if self.error is None else str(self.error)
        self.prompt_hint = "" if self.prompt_hint is None else str(self.prompt_hint)


@dataclass
class Decision:
    action: DecisionAction
    error_class: ErrorClass
    tx_attr: TxAttr
    phase: Phase
    retry_count: int = 0
    pre_action: PreAction = PreAction.NONE
    note: str = ""

    def summary(self, task_id: str = "", task_type: str = "") -> str:
        return (
            "【恢复摘要】\n"
            f"任务类型：{task_type}\n"
            f"任务ID：{task_id}\n"
            f"错误类型：{self.error_class.value}\n"
            f"事务属性：{self.tx_attr.value}\n"
            f"阶段：{self.phase.value}\n"
            f"重试次数：{self.retry_count}\n"
            f"前置动作：{self.pre_action.value}\n"
            f"恢复动作：{self.action.value}\n"
            f"备注：{self.note}"
        )


# ---------- 错误分类 ----------
FATAL_PATTERNS = [
    r"\b400\b", r"\b401\b", r"\b403\b", r"\b404\b",
    r"bad request", r"unauthorized", r"forbidden",
    r"not found", r"token.*(expired|invalid)|(?:invalid|expired)\s+token",
    r"permission",
]
LOGICAL_PATTERNS = [
    r"output validation failed", r"format does not match",
    r"schema", r"infinite loop", r"deadlock", r"hallucinat",
]
TRANSIENT_PATTERNS = [
    r"timeout", r"timed out", r"\b429\b", r"\b503\b",
    r"rate limit", r"service unavailable", r"connection.*(reset|fail|refused)",
    r"gateway timeout",
]
# 支付/交易类兜底：不参与三分类，由 decide() 直接转人工确认扣款状态。
# 中英文均识别（中文优先的宿主环境，中文支付错误漏识别会有重复扣款风险；
# 英文不含裸 declined——connection declined 等属瞬态）
PAYMENT_PATTERN = re.compile(
    r"payment|transaction declined|支付|付款|扣款|交易失败", re.IGNORECASE)

FINAL_KEYWORDS = ["付款", "支付", "部署", "删库", "删除", "提交", "发送"]
FINAL_KEYWORDS_EN = ["send", "deploy", "pay", "delete"]
# 否定前缀：关键词前邻窗口内出现否定语义不算最终动作（如「撤销删除」「取消支付」「请勿删除」）
NEGATION_WORDS = ("撤销", "取消", "撤回", "停止", "勿", "不")
_NEGATION_WINDOW = 4  # 向前看的字符数，容忍「撤销了」「请勿」等插入

# 失败信号允许的状态；check_pending_tasks 的 pending/resolved 属任务生命周期状态
ALLOWED_STATUS = {"failed", "timeout", "interrupted"}


def classify_error(error: str) -> ErrorClass:
    # 空白归一化：多行错误文本不再断开模式匹配（换行会把 logical 拆成默认瞬态）
    e = " ".join(str(error or "").split()).lower()
    if any(re.search(p, e) for p in FATAL_PATTERNS):
        return ErrorClass.FATAL
    if any(re.search(p, e) for p in LOGICAL_PATTERNS):
        return ErrorClass.LOGICAL
    if any(re.search(p, e) for p in TRANSIENT_PATTERNS):
        return ErrorClass.TRANSIENT
    # 默认按瞬态处理（宁可重试，不轻易放弃）
    return ErrorClass.TRANSIENT


# ---------- 事务属性推断 ----------
def _hits_final_keyword(hint: str) -> bool:
    """中文子串匹配（前邻窗口含否定词则豁免）；英文词边界匹配（resend/deleted 不误报）"""
    h = hint or ""
    for kw in FINAL_KEYWORDS:
        start = 0
        while True:
            idx = h.find(kw, start)
            if idx == -1:
                break
            window = h[max(0, idx - _NEGATION_WINDOW):idx]
            if not any(neg in window for neg in NEGATION_WORDS):
                return True
            start = idx + len(kw)
    for kw in FINAL_KEYWORDS_EN:
        if re.search(r"\b" + re.escape(kw) + r"\b", h, re.IGNORECASE):
            return True
    return False


def infer_tx_attr(sig: TaskSignal) -> TxAttr:
    if sig.tx_attr:
        return sig.tx_attr
    if _hits_final_keyword(sig.prompt_hint):
        return TxAttr.FINAL
    if sig.task_type == TaskType.MEDIA:
        return TxAttr.REVERSIBLE          # 媒体可覆盖重提交
    # subagent / workflow 默认只读，除非发现副作用关键词
    return TxAttr.READONLY


# ---------- 语义指纹（fallback：Jaccard；主方案为平台 embedding 余弦相似度） ----------
SEMANTIC_FALLBACK_THRESHOLD = 0.8   # 与 SKILL.md「fallback Jaccard ≥ 0.8」对账
STOPWORDS = {"the", "a", "an", "of", "to", "is", "error", "failed", "with",
             "due", "after", "for", "on", "in", "at", "by", "from", "and", "or",
             "that", "this", "it", "as"}


# 中文近义归一：比对前统一写法，让「没有响应/无响应」类近义改写也能熔断
_CJK_SYNONYMS = {"没有": "无", "无法": "不能"}


def _keywords(text: str) -> set:
    # 归一化常见同义写法，避免 "timed out" 与 "timeout" 词集不相交导致漏熔断
    text = re.sub(r"timed\s+out", "timeout", str(text or "").lower())
    out = set()
    for t in re.findall(r"[a-z0-9]+", text):
        if t in STOPWORDS or len(t) <= 1:
            continue
        # 轻量词干化：去常见后缀，让 "timeout"/"timeouts" 命中
        out.add(re.sub(r"(ing|ed|s|es)$", "", t))
    # 中文按相邻二字组入集：纯中文错误串不再得到空集（否则熔断对中文完全失效）
    for seg in re.findall(r"[\u4e00-\u9fff]+", text):
        for syn, std in _CJK_SYNONYMS.items():
            seg = seg.replace(syn, std)
        seg = re.sub(r"[了吗呢的]", "", seg)  # 语气助词不影响语义比对
        if len(seg) == 1:
            out.add(seg)
        else:
            out.update(seg[i:i + 2] for i in range(len(seg) - 1))
    return out


def _normalize_ids(text: str) -> str:
    """长数字/十六进制 ID（≥6 位且至少含一位数字）归一为占位符，
    避免 req_id/时间戳压垮相似度；纯 hex 字母的英文词（如 facade）不受影响"""
    return re.sub(r"\b(?=[0-9a-f]*\d)[0-9a-f]{6,}\b", "<id>", str(text or "").lower())


def semantic_similar(a: str, b: str, threshold: float = SEMANTIC_FALLBACK_THRESHOLD) -> bool:
    """fallback 方案：Jaccard 相似度（结果由调用方标注 semantic=fallback）。
    主方案：平台 embedding 余弦相似度 > 0.9，由宿主侧实现后替换本函数。
    原始串不达标时再对 ID 归一化后的串比对一次，防止变量片段导致漏熔断。"""
    for x, y in ((a, b), (_normalize_ids(a), _normalize_ids(b))):
        ka, kb = _keywords(x), _keywords(y)
        if ka and kb and len(ka & kb) / len(ka | kb) >= threshold:
            return True
    return False


# ---------- 全抖动退避 ----------
T_BASE = 5.0   # 秒，与 SKILL.md「t_base = 5s」对账
T_MAX = 60.0   # 秒，与 SKILL.md「t_max = 60s」对账


def jitter_backoff(attempt: int, t_base: float = T_BASE, t_max: float = T_MAX) -> float:
    # attempt 封顶防 2**attempt 溢出（公共 API，宿主可能直接调用）；负数归零
    t_calc = min(t_max, t_base * (2 ** min(max(int(attempt), 0), 64)))
    return random.uniform(0, t_calc)


# ---------- 阶段-错误联合矩阵 ----------
# (phase, error_class) -> (max_retry, allow_resume)
MATRIX = {
    (Phase.INIT, ErrorClass.TRANSIENT): (3, True),
    (Phase.INIT, ErrorClass.LOGICAL): (1, True),
    (Phase.PROCESSING, ErrorClass.TRANSIENT): (3, True),
    (Phase.PROCESSING, ErrorClass.LOGICAL): (1, True),
    (Phase.FINALIZING, ErrorClass.TRANSIENT): (2, True),
    (Phase.FINALIZING, ErrorClass.LOGICAL): (1, True),
}


def infer_pre_action(sig: TaskSignal, tx: TxAttr) -> PreAction:
    """可逆/可补偿动作在重试前需要的前置动作。
    media 例外：恢复动作是覆盖重提交，无需先撤销。"""
    if tx == TxAttr.REVERSIBLE and sig.task_type != TaskType.MEDIA:
        return PreAction.UNDO
    if tx == TxAttr.COMPENSATABLE:
        return PreAction.COMPENSATE
    return PreAction.NONE


def _error_has_content(error: str) -> bool:
    """空串/纯符号串视为无归因内容（评审 L1）"""
    e = str(error or "")
    return bool(e.strip()) and bool(re.search(r"[a-z0-9\u4e00-\u9fff]", e.lower()))


def decide(sig: TaskSignal, history_errors: Optional[list[str]] = None,
           current_retry: Optional[int] = None) -> Decision:
    # 0. 状态防呆：非失败信号不得进入恢复流程（如误传 pending/resolved 任务）
    if sig.status not in ALLOWED_STATUS:
        return Decision(DecisionAction.HUMAN, classify_error(sig.error),
                        infer_tx_attr(sig), sig.phase or Phase.PROCESSING, 0,
                        pre_action=PreAction.NONE,
                        note=f"非失败状态（{sig.status}），不走自动恢复，请检查接线")

    # 0.5 重试计数归一：未显式传入时按历史错误条数兜底（防止重试上限永不触发）
    if current_retry is None:
        current_retry = len(history_errors) if history_errors else 0
    current_retry = max(0, int(current_retry))

    err_cls = classify_error(sig.error)
    tx = infer_tx_attr(sig)
    phase = sig.phase or Phase.PROCESSING
    pre = infer_pre_action(sig, tx)

    # 1. 空串/纯符号错误：无法归因，直接转人工
    if not _error_has_content(sig.error):
        return Decision(DecisionAction.HUMAN, err_cls, tx, phase, current_retry,
                        pre_action=PreAction.NONE,
                        note="错误信息缺失或无可归因内容，转人工")

    # 2. 最终动作：任何错误绝不重试
    if tx == TxAttr.FINAL:
        return Decision(DecisionAction.HUMAN, err_cls, tx, phase, 0,
                        pre_action=PreAction.NONE,
                        note="最终动作，绝不自动重试，转人工审核")

    # 3. 致命错误：立即放弃（优先于支付兜底——含 payment 字样但命中 401/400 等
    #    明确致命码的按致命放弃：请求未成功、未产生扣款）
    if err_cls == ErrorClass.FATAL:
        return Decision(DecisionAction.ABORT, err_cls, tx, phase, 0,
                        pre_action=PreAction.NONE,
                        note="致命错误，标记为不可恢复")

    # 4. 支付/交易类兜底：未命中致命码的支付类错误转人工确认扣款状态
    #    （不判 ABORT——payment+timeout 未必已扣款，放弃或重试都可能资损）
    if PAYMENT_PATTERN.search(sig.error):
        return Decision(DecisionAction.HUMAN, err_cls, tx, phase, current_retry,
                        pre_action=PreAction.NONE,
                        note="支付/交易类错误，需人工确认扣款状态，不自动重试")

    # 5. 语义熔断：同类错误重复出现（本实现为 Jaccard fallback，须标注）
    if history_errors:
        for prev in history_errors:
            if classify_error(prev) == err_cls and semantic_similar(prev, sig.error):
                return Decision(DecisionAction.HUMAN, err_cls, tx, phase, current_retry,
                                pre_action=PreAction.NONE,
                                note=f"语义相似度≥{SEMANTIC_FALLBACK_THRESHOLD}"
                                     f"（semantic=fallback），熔断，不再重试")

    # 6. 阶段-错误联合判断
    max_retry, allow = MATRIX.get((phase, err_cls), (0, False))
    if not allow or current_retry >= max_retry:
        return Decision(DecisionAction.HUMAN, err_cls, tx, phase, current_retry,
                        pre_action=PreAction.NONE,
                        note="达到重试上限或不可重试，转人工")
    # 退避只报告窗口（不采样具体值）：实际等待由 adapter 按 Retry-After 协调后采样
    window = min(T_MAX, T_BASE * (2 ** min(current_retry, 64)))
    return Decision(DecisionAction.RESUME, err_cls, tx, phase, current_retry + 1, pre,
                    f"计划退避 0~{window:.0f}s（全抖动随机）后第 {current_retry + 1} 次重试")


if __name__ == "__main__":
    # 快速自检：E01-E06 决策链路（含断言，回归时退出码 1）
    cases = [
        TaskSignal(TaskType.SUBAGENT, "t1", "failed", "Connection timeout: gateway timeout after 30s", Phase.PROCESSING),
        TaskSignal(TaskType.MEDIA, "t2", "failed", "HTTP 429: Too Many Requests", Phase.PROCESSING),
        TaskSignal(TaskType.SUBAGENT, "t3", "failed", "HTTP 401: Invalid or expired token", Phase.INIT),
        TaskSignal(TaskType.SUBAGENT, "t4", "failed", "Output validation failed: response format does not match", Phase.PROCESSING),
        TaskSignal(TaskType.WORKFLOW, "t5", "failed", "node X failed with timeout", Phase.PROCESSING),
        TaskSignal(TaskType.WORKFLOW, "t6", "failed", "Payment gateway declined transaction", Phase.FINALIZING, prompt_hint="执行付款"),
    ]
    expected = {
        "t1": (DecisionAction.RESUME, ErrorClass.TRANSIENT),
        "t2": (DecisionAction.RESUME, ErrorClass.TRANSIENT),
        "t3": (DecisionAction.ABORT, ErrorClass.FATAL),
        "t4": (DecisionAction.RESUME, ErrorClass.LOGICAL),
        "t5": (DecisionAction.HUMAN, ErrorClass.TRANSIENT),
        "t6": (DecisionAction.HUMAN, ErrorClass.TRANSIENT),
    }
    failures = []
    for c in cases:
        hist = ["node X failed with timeout"] if c.task_id == "t5" else None
        d = decide(c, history_errors=hist)
        print(f"[{c.task_id}] {d.action.value:6} | {d.error_class.value:9} | {d.tx_attr.value:12} | {d.note}")
        want_action, want_cls = expected[c.task_id]
        if d.action != want_action or d.error_class != want_cls:
            failures.append(f"{c.task_id}: got {d.action.value}/{d.error_class.value}, "
                            f"want {want_action.value}/{want_cls.value}")
        _ = d.summary(c.task_id, c.task_type.value)
    if failures:
        print("自检失败：\n" + "\n".join(failures))
        raise SystemExit(1)
    print("自检通过：E01-E06 决策链路正确")
