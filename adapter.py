#!/usr/bin/env python3
"""
auto-resume-tasks · 平台适配层
把 resume_decide.decide() 的决策结果，dispatch 到宿主平台的真实工具：
  - subagent  -> subagent_reply(threadId, 续跑/纠错指令)
  - workflow  -> workflow(resumeFromRunId=taskId)
  - media     -> 重新提交生成请求（覆盖式，无需先撤销；原始参数由宿主从平台任务记录取回）
  - abort/human -> 升级通知宿主或用户

RESUME 前按 decision.pre_action 执行前置动作：
  - undo        -> 可逆动作先撤销清理残局（handlers.undo）
  - compensate  -> 可补偿动作先触发补偿工作流（handlers.compensate）
  前置动作 handler 缺失或抛异常时**拒绝续跑**并转 on_human
  （宁可转人工，不可带残局重试）。

dispatch 返回 DispatchResult（executed / pre_action_done / warnings）：
任何 handler 缺失都不再静默——warnings 会注明哪个动作未落地，
所有决策路径都会输出恢复摘要。

退避等待含 Retry-After 协调：错误串带 retry-after N 时取 max(抖动值, N)。

本层不直接 import 平台 SDK（skill 运行在 Agent 上下文内）。
宿主 Agent 通过注入 handler 函数，把平台工具接进来。
"""
from __future__ import annotations
import re
import time
from dataclasses import dataclass, field
from typing import Callable, List, Optional

from resume_decide import (
    TaskSignal, Decision, DecisionAction, TaskType, PreAction,
    jitter_backoff,
)


# 宿主需注入的 handler 签名
ResumeSubagent = Callable[[str, str], None]          # (threadId, instruction)
ResumeWorkflow = Callable[[str], None]               # (runId)
ResumeMedia = Callable[[dict], None]                 # (signal_summary) 宿主据此取回原始参数后重提交
PreActionHandler = Callable[[TaskSignal, Decision], None]  # 撤销/补偿等前置动作
OnAbort = Callable[[TaskSignal, Decision], None]
OnHuman = Callable[[TaskSignal, Decision], None]


@dataclass
class Handlers:
    resume_subagent: Optional[ResumeSubagent] = None
    resume_workflow: Optional[ResumeWorkflow] = None
    resume_media: Optional[ResumeMedia] = None
    undo: Optional[PreActionHandler] = None        # 可逆动作：重试前清理残局
    compensate: Optional[PreActionHandler] = None  # 可补偿动作：重试前先补偿
    on_abort: Optional[OnAbort] = None
    on_human: Optional[OnHuman] = None


@dataclass
class DispatchResult:
    executed: bool = True                    # 决策动作是否真正落地（任一 handler 成功执行）
    pre_action_done: Optional[bool] = None   # None=无前置动作；True/False=执行成功/失败
    warnings: List[str] = field(default_factory=list)


# 不同错误类型对应的续跑指令模板
RESUME_INSTRUCTIONS = {
    "transient": "后台任务因瞬态错误中断，请基于已有上下文继续完成原任务。",
    "logical": "后台任务因输出/逻辑错误失败，请修正后重试；附上一次失败摘要：{error}",
}

RETRY_AFTER_PATTERN = re.compile(r"retry[- ]after[:\s]*(\d+)", re.IGNORECASE)


class ResumeAdapter:
    def __init__(self, handlers: Handlers, wait: bool = True):
        self.h = handlers
        self.wait = wait  # 是否实际 sleep 退避；单测时可置 False

    def _sleep(self, attempt: int, sig: Optional[TaskSignal] = None) -> float:
        """计算并（wait=True 时）执行退避，返回实际等待秒数（便于测试）。
        Retry-After 协调：错误串带 retry-after N 时取 max(抖动值, N)。"""
        delay = jitter_backoff(attempt)
        if sig is not None:
            m = RETRY_AFTER_PATTERN.search(sig.error)
            if m:
                delay = max(delay, float(m.group(1)))
        if self.wait:
            time.sleep(delay)
        return delay

    def _emit(self, sig: TaskSignal, decision: Decision, result: DispatchResult) -> None:
        for w in result.warnings:
            print(f"[恢复警告] {w}")
        print(decision.summary(sig.task_id, sig.task_type.value))

    def _route_human(self, sig: TaskSignal, decision: Decision,
                     result: DispatchResult, reason: str) -> None:
        result.warnings.append(reason)
        result.executed = False
        if self.h.on_human:
            self.h.on_human(sig, decision)
        else:
            result.warnings.append("on_human 未注入：转人工动作未执行")

    def dispatch(self, sig: TaskSignal, decision: Decision) -> DispatchResult:
        result = DispatchResult()
        action = decision.action

        if action == DecisionAction.ABORT:
            if self.h.on_abort:
                self.h.on_abort(sig, decision)
            else:
                result.executed = False
                result.warnings.append("on_abort 未注入：放弃动作未执行")
            self._emit(sig, decision, result)
            return result

        if action == DecisionAction.HUMAN:
            if self.h.on_human:
                self.h.on_human(sig, decision)
            else:
                result.executed = False
                result.warnings.append("on_human 未注入：转人工动作未执行")
            self._emit(sig, decision, result)
            return result

        # action == RESUME
        # 1. 前置动作：缺失或执行失败一律拒绝续跑（宁可转人工，不可带残局重试）。
        #    media 例外由 decide 保证：覆盖重提交，pre_action 为 none。
        if decision.pre_action == PreAction.UNDO:
            if self.h.undo is None:
                self._route_human(sig, decision, result, "undo 未注入：拒绝续跑，请人工处理")
                self._emit(sig, decision, result)
                return result
            try:
                self.h.undo(sig, decision)
                result.pre_action_done = True
            except Exception as exc:
                result.pre_action_done = False
                self._route_human(sig, decision, result,
                                  f"undo 执行失败（{exc}）：拒绝续跑，请人工处理")
                self._emit(sig, decision, result)
                return result
        elif decision.pre_action == PreAction.COMPENSATE:
            if self.h.compensate is None:
                self._route_human(sig, decision, result,
                                  "compensate 未注入：拒绝续跑，请人工处理")
                self._emit(sig, decision, result)
                return result
            try:
                self.h.compensate(sig, decision)
                result.pre_action_done = True
            except Exception as exc:
                result.pre_action_done = False
                self._route_human(sig, decision, result,
                                  f"compensate 执行失败（{exc}）：拒绝续跑，请人工处理")
                self._emit(sig, decision, result)
                return result

        # 2. 执行退避（含 Retry-After 协调）
        self._sleep(decision.retry_count - 1, sig)

        err_kind = "logical" if decision.error_class.value == "logical" else "transient"
        instruction = RESUME_INSTRUCTIONS[err_kind].format(error=sig.error)

        # 3. 续跑分发：handler 缺失不再静默，记入 warnings
        if sig.task_type == TaskType.SUBAGENT:
            if self.h.resume_subagent:
                self.h.resume_subagent(sig.task_id, instruction)
            else:
                result.executed = False
                result.warnings.append("resume_subagent 未注入：续跑未执行")
        elif sig.task_type == TaskType.WORKFLOW:
            if self.h.resume_workflow:
                self.h.resume_workflow(sig.task_id)
            else:
                result.executed = False
                result.warnings.append("resume_workflow 未注入：续跑未执行")
        elif sig.task_type == TaskType.MEDIA:
            if self.h.resume_media:
                self.h.resume_media({"task_id": sig.task_id, "error": sig.error})
            else:
                result.executed = False
                result.warnings.append("resume_media 未注入：续跑未执行")

        # 4. 输出恢复摘要（供当前会话复盘）
        self._emit(sig, decision, result)
        return result


# ---------- 宿主接入示例（伪代码，运行在 Agent 上下文） ----------
"""
from resume_decide import decide
from adapter import ResumeAdapter, Handlers

def handle_signal(raw: dict):
    # 状态契约见 references/host-contract.md：
    #   human_pending 命中 → 静默丢弃本回调（不调用 decide、不输出）
    #   否则读 current_retry 与 history_errors（保留最近 10 条）
    state = load_resume_state(raw["task_id"])
    if state and state.get("status") == "human_pending":
        return  # 静默丢弃
    sig = TaskSignal(
        task_type=TaskType(raw["type"]),
        task_id=raw["task_id"],        # 与 check_pending_tasks 返回键一致；subagent 续跑目标为其 thread_id
        status=raw["status"],
        error=raw["error"],
        phase=Phase(raw["phase"]) if raw.get("phase") else None,
        prompt_hint=raw.get("prompt_hint", ""),  # 缺失时无法识别最终动作关键词
    )
    decision = decide(
        sig,
        history_errors=state.get("history_errors") if state else [],
        current_retry=state.get("current_retry") if state else None,  # None 时按历史条数兜底
    )
    adapter = ResumeAdapter(Handlers(
        resume_subagent=lambda tid, instr: subagent_reply(threadId=tid, task=instr),
        resume_workflow=lambda rid: workflow(script="", resumeFromRunId=rid),
        # media 原始参数不在信号中：宿主按 signal_summary 里的 task_id 从平台
        # 任务记录取回生成参数后重提交
        resume_media=lambda p: media_generate_image(**recover_params(p)),
        undo=lambda s, d: undo_artifacts(s),          # 可逆动作的撤销实现
        compensate=lambda s, d: run_compensation(s, d),  # 可补偿动作的补偿实现
        on_abort=lambda s, d: notify_abort(s, d),
        on_human=lambda s, d: notify_human(s, d),
    ))
    result = adapter.dispatch(sig, decision)
    # 回填状态：result.executed=False 时记 failed 并告警；否则按 decision.retry_count 回填
    save_resume_state(sig.task_id, decision, result)
"""
