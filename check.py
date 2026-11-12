#!/usr/bin/env python3
"""Check one research run against the protocol's structural rules. Read-only.

Usage:
    python3 check.py PROJECT_OR_RUN_DIR [--json] [--node NODE_ID] [--quiet] [--gates]

Finds the run under PROJECT/research/<run-id>/run.json, or takes the run dir directly.
Prints findings as P0 (blocks delivery), P1 (serious), P2 (advisory), then a verdict.
Exit codes: 0 clean or advisory only, 1 P1 present, 2 P0 present or the run could not be read.

`--gates` groups the same findings by the six gates instead of by file — the phase-acceptance
view. It exits 2 when any gate (or the ungrouped bucket) holds a P0, 1 when any holds a P1.
`--gates --json` prints the same grouping as JSON; the two flags never drop each other.

It checks structure, never scholarship: it cannot tell whether an argument is sound.
The schema it enforces is documented in references/09-ledger.md.
Standard library only; no network; writes nothing.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from collections import Counter
from contextlib import contextmanager

CLAIM_TYPES = {"fact", "inference", "interpretation", "normative"}
# The five citation states. The distinction between the last two is the point: treating a
# network failure as fabrication punishes correct work, and treating a rejected identifier as
# an outage lets the one unrecoverable error through.
CITATION_STATES = {"verified", "partial", "unverified", "unreachable", "invalid"}
GATES = ("angle", "coverage", "citation", "taxonomy", "calibration", "weaving")
GATE_LEVEL = {"angle": "critical", "citation": "critical",
              "coverage": "major", "taxonomy": "major", "calibration": "major", "weaving": "major"}
DISPOSITIONS = {"revise", "correct", "rebut", "concede", "covered", "park", "branch"}
GAP_DISPOSITIONS = {"revise", "rebut", "concede", "covered", "park"}
RELATION_KINDS = {"converge", "diverge", "resonates", "appropriates", "displaces"}
NODE_TERMINAL = {"closed", "skipped", "failed"}
RUN_STATES = {"active", "paused", "done", "abandoned"}
# The ledger schema this checker was written against (references/09-ledger.md).
SCHEMA_VERSION = 1
NODE_ALL = {
    "queued", "planning", "awaiting_approval", "executing", "synthesizing", "reviewing",
    "disposing", "possibility", "filling_gaps", "deciding", "closed", "skipped", "failed",
}
NODE_KINDS = {"root", "line", "join", "branch"}
OPTION_STATES = ("node", "reason", "covered_by")
# Phrases that are not reasons. A genuine possibility is opened, or the constraint that
# stopped it is named.
NON_REASONS = ("not worth it", "not worthwhile", "low value", "insufficient value", "不值得", "意义不大")
# Angles: an opening sentence that announces a survey instead of stating a judgement.
SUMMARY_OPENERS = (
    "this report surveys", "this paper reviews", "the literature on",
    "this section summarises", "this section summarizes", "this report reviews",
    "this paper surveys", "this study surveys", "this essay surveys", "the following surveys",
    "本文梳理", "本文综述", "本节概述", "本报告梳理", "本报告综述",
    "本文回顾", "本节梳理", "本节综述", "这篇报告综述", "下文梳理", "本报告回顾",
)
# Calibration: verbs the table reserves for several independent studies. Used alone against a
# thin evidence base they are overclaiming, which is the failure Calibration exists to catch.
STRONG_CLAIMS = ("proves", "proven", "demonstrates conclusively", "establishes beyond",
                 "证实了", "证明了")
HEDGES = ("may ", "might ", "possibly", "perhaps", "seems to", "appears to", "arguably",
          "可能", "或许", "似乎")
SUPERLATIVES = ("first study", "only study", "the best", "最优", "首次", "unique in the literature")
# Taxonomy: heading prefixes that are not topics. A section named after a card, a source or a
# phase is a filing cabinet, not a taxonomy — the material is not cut by what it shows.
NON_TOPIC_HEADING = re.compile(
    r"^\s*(?:card|卡|source|来源|node|节点|round|轮|step|阶段|phase|phase)\s*[\w\-]*\s*"
    r"[:：]?\s*\d*\s*$", re.I)
# Academic apparatus is not an argument section: 07-report.md *requires* 参考文献 and 附录, so
# a report that has them is not failing Taxonomy. They are excluded from the topic list.
APPARATUS_HEADING = re.compile(
    r"^\s*(?:references|参考文献|bibliography|appendix|附录|notes|注释|abstract|摘要"
    r"|keywords|关键词|acknowledg\w*|致谢)\s*[:：]?\s*[0-9IVXivx]*\s*$", re.I)
# Weaving: a paragraph whose citations are all one source is a catalogue entry.
CITATION_TOKEN = re.compile(r"`([^`]+)`|https?://\S+|doc:[0-9a-f]{12}")


class Report:
    def __init__(self, quiet: bool = False, only_node: str | None = None) -> None:
        self.items: list[tuple[str, str, str]] = []
        self.gate_of: dict[tuple[str, str, str], str] = {}
        self.quiet = quiet
        self.only_node = only_node
        self._gate: str | None = None

    @contextmanager
    def gate(self, name: str):
        """Tag the findings raised inside this block with the gate they belong to."""
        previous = self._gate
        self._gate = name
        try:
            yield
        finally:
            self._gate = previous

    def add(self, level: str, where: str, message: str) -> None:
        self.items.append((level, where, message))
        if self._gate:
            self.gate_of[(level, where, message)] = self._gate

    def p0(self, where: str, message: str) -> None:
        self.add("P0", where, message)

    def p1(self, where: str, message: str) -> None:
        self.add("P1", where, message)

    def p2(self, where: str, message: str) -> None:
        self.add("P2", where, message)

    def by_gate(self) -> dict[str, list[tuple[str, str, str]]]:
        out: dict[str, list[tuple[str, str, str]]] = {g: [] for g in GATES}
        out["ungated"] = []
        for item in self.items:
            out[self.gate_of.get(item, "ungated")].append(item)
        return out

    def gate_counts(self) -> dict[str, dict]:
        """Per-gate worst level and counts — the shape both gate views render from."""
        grouped = self.by_gate()
        out = {}
        for gate in list(GATES) + ["ungated"]:
            items = grouped[gate]
            counts = Counter(level for level, _, _ in items)
            worst = ("P0" if counts["P0"] else "P1" if counts["P1"]
                     else "P2" if counts["P2"] else None)
            out[gate] = {
                "level": GATE_LEVEL.get(gate),
                "state": {"P0": "FAIL", "P1": "FAIL", "P2": "note", None: "clear"}.get(worst),
                "worst": worst,
                "counts": {k: counts.get(k, 0) for k in ("P0", "P1", "P2")},
                "findings": [{"level": l, "where": w, "message": m} for l, w, m in items],
            }
        return out

    def aggregated(self) -> list[tuple[str, str, str]]:
        """Fold identical messages about different cards into one line with a count.

        A card-level mistake repeated across nine cards is one mistake; printing it nine times
        buries the other findings.
        """
        groups: dict[tuple[str, str], list[str]] = {}
        order: list[tuple[str, str]] = []
        for level, where, message in self.items:
            key = (level, message.split(";")[0])
            if key not in groups:
                groups[key] = []
                order.append(key)
            groups[key].append(where)
        out: list[tuple[str, str, str]] = []
        for key in order:
            level, message = key
            wheres = groups[key]
            out.append((level, wheres[0], message) if len(wheres) == 1
                       else (level, f"{len(wheres)} places", f"{message}  [{len(wheres)}×: {', '.join(wheres[:3])}"
                                                              + (", …" if len(wheres) > 3 else "") + "]"))
        return out

    def emit(self, as_json: bool) -> int:
        order = {"P0": 0, "P1": 1, "P2": 2}
        items = sorted(self.aggregated(), key=lambda i: (order[i[0]], i[1]))
        counts = Counter(level for level, _, _ in items)
        if as_json:
            print(json.dumps({
                "ok": not (counts["P0"] or counts["P1"]),
                "counts": {k: counts.get(k, 0) for k in ("P0", "P1", "P2")},
                "findings": [{"level": l, "where": w, "message": m} for l, w, m in items],
            }, ensure_ascii=False, indent=2))
        elif not self.quiet or counts["P0"] or counts["P1"]:
            for level, where, message in items:
                print(f"{level}  {where}  {message}")
            if not items:
                print("clean: no structural findings")
        if counts["P0"]:
            print(f"verdict: BLOCKED — {counts['P0']} P0, {counts['P1']} P1, {counts['P2']} P2", file=sys.stderr)
            return 2
        if counts["P1"]:
            print(f"verdict: FIX FIRST — {counts['P1']} P1, {counts['P2']} P2", file=sys.stderr)
            return 1
        if not self.quiet:
            print(f"verdict: OK — {counts['P2']} advisory note(s)", file=sys.stderr)
        return 0


# --------------------------------------------------------------------------- loading

def locate(arg: str) -> str:
    path = os.path.realpath(os.path.expanduser(arg))
    if os.path.isfile(os.path.join(path, "run.json")):
        return path
    research = os.path.join(path, "research")
    if not os.path.isdir(research):
        raise SystemExit(f"check: no research/ under {path}")
    runs = [os.path.join(research, d) for d in sorted(os.listdir(research))
            if os.path.isfile(os.path.join(research, d, "run.json"))]
    if not runs:
        raise SystemExit(f"check: no run.json under {research}")
    if len(runs) > 1:
        newest = max(runs, key=lambda d: os.path.getmtime(os.path.join(d, "run.json")))
        print(f"check: {len(runs)} runs found; checking the most recent ({os.path.basename(newest)}). "
              f"Pass the run folder to choose another.", file=sys.stderr)
        return newest
    return runs[0]


def load(run_dir: str, rep: Report) -> dict | None:
    path = os.path.join(run_dir, "run.json")
    try:
        with open(path, encoding="utf-8") as handle:
            run = json.load(handle)
    except (OSError, ValueError) as error:
        rep.p0("run.json", f"cannot read: {error}")
        return None
    if not isinstance(run, dict):
        rep.p0("run.json", "the run file is not a JSON object")
        return None
    if not isinstance(run.get("nodes"), list):
        rep.p0("run.json", "`nodes` is missing or is not a list")
        return None
    return run


def read(path: str) -> str | None:
    try:
        with open(path, encoding="utf-8") as handle:
            return handle.read()
    except (OSError, UnicodeDecodeError):
        return None


def one_line(text: object) -> str:
    return " ".join(str(text or "").split())


def as_list(value, rep: Report, where: str, key: str) -> list:
    """A malformed collection is a finding, never a traceback."""
    if value is None:
        return []
    if not isinstance(value, list):
        rep.p0(where, f"`{key}` must be a list (got {type(value).__name__})")
        return []
    return value


def as_dict(value, rep: Report, where: str, key: str) -> dict:
    if value is None:
        return {}
    if not isinstance(value, dict):
        rep.p0(where, f"`{key}` must be an object (got {type(value).__name__})")
        return {}
    return value


def has_heading(text: str, *needles: str) -> bool:
    """Whether any markdown heading line contains one of the needles, case-insensitively."""
    for line in text.splitlines():
        stripped = line.lstrip()
        if not stripped.startswith("#"):
            continue
        low = stripped.lower()
        if any(needle.lower() in low for needle in needles):
            return True
    return False


# --------------------------------------------------------------------------- entry

def main(argv=None) -> int:
    p = argparse.ArgumentParser(prog="check.py", description=__doc__.splitlines()[0])
    p.add_argument("target", help="Project folder or the run folder itself")
    p.add_argument("--json", action="store_true", help="Machine-readable output")
    p.add_argument("--node", help="Only report findings about this node (run-level still shown)")
    p.add_argument("--quiet", action="store_true", help="Print nothing when clean")
    p.add_argument("--gates", action="store_true",
                   help="Group findings by the six gates instead of by file; a phase-acceptance view")
    args = p.parse_args(argv)

    rep = Report(quiet=args.quiet, only_node=args.node)
    run_dir = locate(args.target)
    run = load(run_dir, rep)
    if run is None:
        return rep.emit(args.json)

    limits = as_dict(run.get("limits"), rep, "run.json", "limits")
    by_id = {n.get("id"): n for n in run["nodes"] if isinstance(n, dict) and n.get("id")}

    check_run(rep, run, run_dir, limits)
    for node in run["nodes"]:
        if not isinstance(node, dict):
            rep.p0("run.json", "a node entry is not an object")
            continue
        if rep.only_node and node.get("id") != rep.only_node:
            continue
        check_node(rep, run, run_dir, limits, node)
    check_graph(rep, run, by_id, limits)
    check_alternatives(rep, run, by_id)
    check_consent(rep, run)
    check_consent_shape(rep, run)
    check_report(rep, run, run_dir)

    if args.gates:
        return emit_gates(rep, as_json=args.json)
    return rep.emit(args.json)


def gate_verdict(gates: dict[str, dict]) -> tuple[int, str]:
    """The gate view's verdict. Ungated findings count: a P0 that belongs to no gate still
    blocks delivery — the grouping is a reading aid, not a jurisdiction."""
    blocking = [g for g in gates if gates[g]["counts"]["P0"]]
    p1 = [g for g in gates if gates[g]["counts"]["P1"]]
    critical = [g for g in ("angle", "citation") if gates[g]["counts"]["P0"]]
    if blocking:
        return 2, (f"BLOCKED — {len(blocking)} gate(s) at P0 ({', '.join(blocking)}); "
                   f"critical failures: {', '.join(critical) or 'none'}")
    if p1:
        return 1, f"FIX FIRST — {len(p1)} gate(s) at P1 ({', '.join(p1)})"
    return 0, "OK — all gates clear"


def emit_gates(rep: Report, as_json: bool = False) -> int:
    """A phase-acceptance view: which gates are clear, which are not, and why."""
    gates = rep.gate_counts()
    code, verdict = gate_verdict(gates)
    if as_json:
        print(json.dumps({
            "ok": code == 0,
            "verdict": verdict,
            "exit": code,
            "gates": gates,
        }, ensure_ascii=False, indent=2))
        return code
    for gate in GATES:
        info = gates[gate]
        print(f"{gate.upper():12} ({GATE_LEVEL[gate]:8})  {info['state']}")
        for item in info["findings"]:
            print(f"    {item['level']}  {item['where']}  {item['message']}")
    loose = gates["ungated"]
    if loose["findings"]:
        print(f"{'UNGATED':12} ({'—':8})  {loose['state']}  ({len(loose['findings'])} finding(s), "
              f"not attributable to one gate — still blocks verdict)")
    for item in loose["findings"]:
        print(f"    {item['level']}  {item['where']}  {item['message']}")
    print(f"\nverdict: {verdict}", file=sys.stderr)
    return code


# --------------------------------------------------------------------------- run level

def check_run(rep: Report, run: dict, run_dir: str, limits: dict) -> None:
    run_id = str(run.get("run_id") or "")
    if not run_id:
        rep.p0("run.json", "missing required field `run_id`")
    elif not re.fullmatch(r"[A-Za-z0-9_.-]{1,64}", run_id):
        rep.p0("run.json", f"run_id {run_id!r} is not letters, digits, dot, dash or underscore")
    for key in ("question", "status"):
        if not one_line(run.get(key)):
            rep.p0("run.json", f"missing required field `{key}`")
    if run.get("status") not in RUN_STATES:
        rep.p0("run.json", f"unknown run status {run.get('status')!r}; "
                           f"use one of {sorted(RUN_STATES)}")

    # `schema` documents that unknown values are refused (references/09-ledger.md). Check it,
    # or the promise is words only: a ledger from a future version would be read as this one.
    schema = run.get("schema")
    if schema is None:
        rep.p1("run.json", "no `schema` field; write the ledger's schema version (currently "
                           f"{SCHEMA_VERSION}) so a future reader knows what shape it is")
    elif not isinstance(schema, int) or isinstance(schema, bool) or schema < 1:
        rep.p0("run.json", f"`schema` must be a positive integer (got {schema!r})")
    elif schema > SCHEMA_VERSION:
        rep.p0("run.json", f"`schema` {schema} is newer than this checker understands "
                           f"({SCHEMA_VERSION}); refusing to read a ledger whose shape it cannot verify")
    elif schema != SCHEMA_VERSION:
        rep.p1("run.json", f"`schema` {schema} predates the current version ({SCHEMA_VERSION}); "
                           f"re-check the field rules in references/09-ledger.md")

    if not one_line(run.get("project")):
        rep.p1("run.json", "no `project`; the ledger should record where the research is written")
    language = one_line(run.get("language"))
    if not language:
        rep.p1("run.json", "no `language`; use auto, zh, en or a language tag")
    elif language != "auto" and not re.fullmatch(r"[A-Za-z]{2,3}(?:-[A-Za-z0-9]{2,8})*", language):
        rep.p1("run.json", f"language {language!r} is not `auto`, a language tag or an IETF tag")

    for key, minimum in (("depth", 0), ("max_nodes", 1), ("parallel", 1), ("cards", 1)):
        value = limits.get(key)
        if not isinstance(value, int) or isinstance(value, bool) or value < minimum:
            rep.p1("run.json", f"limits.{key} must be an integer >= {minimum} (got {value!r})")
    for key in ("followups", "revisions"):
        value = limits.get(key)
        if not isinstance(value, int) or isinstance(value, bool) or not 0 <= value <= 6:
            rep.p1("run.json", f"limits.{key} must be an integer 0..6 (got {value!r})")
    approval = limits.get("plan_approval")
    if approval not in (None, "", "require", "auto"):
        rep.p1("run.json", f"limits.plan_approval must be `require` or `auto` (got {approval!r})")
    # The budget is checked as it is spent, not only after the fact: parallel and cards are
    # promises about how the run is executed, so they are compared against what executed.
    max_nodes = limits.get("max_nodes")
    live = [n for n in run["nodes"] if isinstance(n, dict) and n.get("status") not in NODE_TERMINAL]
    if isinstance(max_nodes, int) and not isinstance(max_nodes, bool):
        if len(run["nodes"]) > max_nodes:
            rep.p0("run.json", f"{len(run['nodes'])} nodes exceed limits.max_nodes={max_nodes}")
        elif len(run["nodes"]) + (len(live) * 2) > max_nodes and len(live) > 1:
            rep.p2("run.json", f"node budget: {len(run['nodes'])}/{max_nodes} used with {len(live)} node(s) "
                              f"still open; a fork per open node would overrun the budget — decide now, not after")
    if isinstance(limits.get("parallel"), int) and len(live) > limits["parallel"]:
        rep.p1("run.json", f"{len(live)} nodes are in flight but limits.parallel={limits['parallel']}; "
                           f"the limit governs dispatch, so either raise it with the user's consent or "
                           f"queue the extra nodes")
    if isinstance(limits.get("cards"), int):
        for node in run["nodes"]:
            if not isinstance(node, dict):
                continue
            dispatched = as_list(node.get("cards"), rep, f"node {node.get('id')}", "cards")
            if len(dispatched) > limits["cards"]:
                rep.p1(f"node {node.get('id')}", f"{len(dispatched)} cards dispatched but "
                                                f"limits.cards={limits['cards']}; the limit is a promise about "
                                                f"how the run is executed, so record the consent that raised it "
                                                f"or declare the untouched cards as gaps")

    cost = run.get("cost")
    if cost is not None:
        check_cost(rep, run, "run.json", cost)

    if run.get("independent") is False and not one_line(run.get("independent_note")):
        rep.p1("run.json", "`independent: false` but no `independent_note`: a degraded run must say what it "
                           "could not do, so the report can disclose it")

    if not os.path.isfile(os.path.join(run_dir, "question.md")):
        rep.p2("question.md", "missing; the question as asked should be on disk unedited")
    for name in ("graph.md", "paths.md"):
        text = read(os.path.join(run_dir, name))
        if text is None:
            rep.p1(name, "missing; the coordinator rewrites this after each level")
        elif not text.strip() or "_Not written yet._" in text or "_尚未撰写。_" in text:
            rep.p2(name, "still the empty skeleton")

    revisions = as_list(run.get("question_revisions"), rep, "run.json", "question_revisions")
    for index, item in enumerate(revisions):
        if not isinstance(item, dict):
            rep.p0("run.json", "a question_revisions entry is not an object")
            continue
        if item.get("effect") not in ("carry", "replan", "abandon"):
            rep.p1("run.json", f"question_revisions[{index}].effect must be carry, replan or abandon "
                               f"(got {item.get('effect')!r})")
        if not one_line(item.get("what")):
            rep.p1("run.json", f"question_revisions[{index}] does not say what changed")

    final_dir = os.path.join(run_dir, "final")
    finals = sorted(f for f in os.listdir(final_dir) if f.endswith(".md")) if os.path.isdir(final_dir) else []
    stages = as_dict(run.get("final"), rep, "run.json", "final")
    if run.get("status") == "done":
        if not any("final" in f for f in finals):
            rep.p0("final/", f"run marked done but no *final*.md exists (found {finals or 'nothing'})")
        if not any("review" in f for f in finals):
            rep.p1("final/", "run marked done but no independent review file; the review is not optional")
    for stage in ("survey", "draft", "review", "final"):
        record = stages.get(stage)
        if not one_line(record):
            if run.get("status") == "done" and stage in ("survey", "draft", "final"):
                rep.p1("run.json", f"`final.{stage}` is not recorded; the report's stages are an audit trail")
            continue
        path = os.path.join(final_dir, str(record))
        if not os.path.isfile(path):
            rep.p0("run.json", f"final.{stage} points at {record}, which does not exist")
    if one_line(stages.get("final")) and run.get("status") != "done":
        rep.p2("run.json", "a final report is recorded but the run is not marked done")

    # Every locator in the delivered texts must resolve. A citation the reader cannot open is a
    # promise broken in the one artifact that leaves the run; this is what 07-report.md claims
    # the checker does, so it has to actually read the prose.
    for stage in ("survey", "draft", "review", "final"):
        record = one_line(stages.get(stage))
        if not record:
            continue
        path = os.path.join(final_dir, record)
        if not os.path.isfile(path):
            continue
        text = read(path)
        if text is None:
            rep.p0(f"final/{record}", "recorded as a report stage but is not readable as UTF-8")
            continue
        rep_gate = "citation"
        with rep.gate(rep_gate):
            check_locators(rep, f"final/{record}", text, run_dir)


def check_locators(rep: Report, where: str, text: str, run_dir: str) -> None:
    """Every path-like locator in a delivered text must resolve to a file.

    Only tokens that look like project-relative paths are checked: bare words, URLs and
    `doc:` identifiers are left alone, since a URL is not resolvable on disk and a doc_id is
    resolved elsewhere. This is the mechanical half of the Citation gate — it cannot tell
    whether a source says what the text claims, only whether the reader can open it.
    """
    seen: set[str] = set()
    for match in re.finditer(r"`([^`\n]+)`", text):
        token = match.group(1).strip()
        if token in seen or not token or " " in token:
            continue
        seen.add(token)
        if token.startswith(("http://", "https://", "doc:")):
            continue
        if not re.search(r"[./]", token) or not re.fullmatch(r"[\w./\-]+", token, re.UNICODE):
            continue
        if not token.endswith((".md", ".txt", ".json", ".csv", ".html", ".pdf", ".xml")):
            continue
        if resolve_from(token, run_dir) is None:
            rep.p1(where, f"locator `{token}` does not resolve; a citation the reader cannot open "
                          f"is a promise the delivery broke (references/07-report.md)")


def resolve_from(source: str, base: str) -> str | None:
    """Resolve a locator against the run, the project above it, or the exported sources.

    A report cites node-level paths (`sources/kampo.txt`), but delivery copies the material to
    `final/sources/`, so the basename is tried there too — otherwise every honest citation in a
    delivered report reads as broken.
    """
    if os.path.isabs(source):
        candidates = [source]
    else:
        project = os.path.dirname(os.path.dirname(base))
        candidates = [os.path.join(base, source), os.path.join(project, source), source,
                      os.path.join(base, "final", "sources", source),
                      os.path.join(base, "final", "sources", os.path.basename(source))]
    for candidate in candidates:
        path = os.path.realpath(candidate)
        if os.path.isfile(path):
            return path
    return None


def check_consent_shape(rep: Report, run: dict) -> None:
    consent = run.get("consent")
    if consent is None:
        return
    if not isinstance(consent, dict):
        rep.p1("run.json", f"`consent` must be an object (got {type(consent).__name__})")
        return
    note = consent.get("note")
    if note is not None and not isinstance(note, str):
        rep.p1("run.json", f"consent.note must be a string (got {type(note).__name__}); it carries the "
                           f"user's runtime constraints, so it has to be readable")
    dissolution = consent.get("dissolution")
    if dissolution not in (None, True, False):
        rep.p1("run.json", f"consent.dissolution must be null, true or false (got {dissolution!r})")


def check_cost(rep: Report, run: dict, where: str, cost) -> None:
    """`cost` is the real spend ledger written by scripts/node.py. Its shape is checked so a
    hand-edit that breaks `status.py --cost` is caught here rather than at reporting time."""
    if not isinstance(cost, dict):
        rep.p0(where, f"`cost` must be an object (got {type(cost).__name__})")
        return
    for key in ("tokens", "calls", "usd"):
        value = cost.get(key)
        if value is None:
            continue
        if not isinstance(value, (int, float)) or isinstance(value, bool) or value < 0:
            rep.p1(where, f"cost.{key} must be a non-negative number (got {value!r})")
    entries = cost.get("entries")
    if entries is None:
        return
    if not isinstance(entries, list):
        rep.p1(where, f"`cost.entries` must be a list (got {type(entries).__name__})")
        return
    for index, entry in enumerate(entries):
        if not isinstance(entry, dict):
            rep.p1(where, f"cost.entries[{index}] is not an object")
            continue
        for key in ("tokens", "calls"):
            value = entry.get(key)
            if value is not None and (not isinstance(value, int) or isinstance(value, bool) or value < 0):
                rep.p1(where, f"cost.entries[{index}].{key} must be a non-negative integer (got {value!r})")
        node_id = one_line(entry.get("node"))
        node_ids = {n.get("id") for n in run["nodes"] if isinstance(n, dict)}
        if node_id and node_id not in node_ids:
            rep.p1(where, f"cost.entries[{index}] attributes spend to {node_id!r}, which is not a node "
                          f"of this run")


# --------------------------------------------------------------------------- node level

def check_node(rep: Report, run: dict, run_dir: str, limits: dict, node: dict) -> None:
    nid = node.get("id")
    if not one_line(nid):
        rep.p0("run.json", "a node has no id")
        return
    where = f"node {nid}"

    status = node.get("status")
    if status not in NODE_ALL:
        rep.p0(where, f"unknown status {status!r}; see references/09-ledger.md for the states")
    kind = node.get("kind", "line")
    if kind not in NODE_KINDS:
        rep.p0(where, f"unknown kind {kind!r}; use one of {sorted(NODE_KINDS)}")

    # Documented fields whose shape was never enforced (references/09-ledger.md). A ledger key
    # nobody validates is a key that silently drifts; these are cheap to check and expensive
    # to reconstruct after the session is gone.
    seq = node.get("seq")
    if seq is not None and (not isinstance(seq, int) or isinstance(seq, bool) or seq < 1):
        rep.p1(where, f"`seq` must be a positive integer when present (got {seq!r})")
    opened_by = node.get("opened_by")
    if opened_by is not None:
        if not isinstance(opened_by, dict):
            rep.p1(where, f"`opened_by` must be an object or null (got {type(opened_by).__name__})")
        else:
            for key in ("decision", "option"):
                if not one_line(opened_by.get(key)):
                    rep.p1(where, f"`opened_by` names no `{key}`; record which decision and option "
                                  f"opened this node, or set it to null")
    dq = node.get("question")
    if kind != "root" and not one_line(dq):
        rep.p1(where, "no `question`; a node's question is what its cards and conclusion answer")
    versions = node.get("synthesis_versions")
    if versions is not None and (not isinstance(versions, int) or isinstance(versions, bool) or versions < 0):
        rep.p1(where, f"`synthesis_versions` must be a non-negative integer (got {versions!r})")
    elif isinstance(versions, int) and one_line(node.get("synthesis")) and versions < 1:
        rep.p1(where, "a conclusion is recorded but `synthesis_versions` is 0; the version count is the "
                      "audit trail of how many times it was rewritten")
    rounds = node.get("review_rounds")
    if rounds is not None and (not isinstance(rounds, int) or isinstance(rounds, bool) or rounds < 0):
        rep.p1(where, f"`review_rounds` must be a non-negative integer (got {rounds!r})")
    dissolves = node.get("dissolves")
    if dissolves not in (None, "this_node", "research_question", "question"):
        rep.p1(where, f"`dissolves` must be null, `this_node` or `research_question` (got {dissolves!r})")

    depth = node.get("depth")
    max_depth = limits.get("depth")
    if not isinstance(depth, int) or isinstance(depth, bool) or depth < 0:
        rep.p0(where, f"depth must be a non-negative integer (got {depth!r})")
        depth = None
    elif isinstance(max_depth, int) and depth > max_depth:
        rep.p1(where, f"depth {depth} exceeds limits.depth={max_depth}")

    parents = as_list(node.get("parents"), rep, where, "parents")
    if depth == 0 and parents:
        rep.p0(where, "the root node cannot have parents")
    if depth not in (0, None) and not parents and kind != "root":
        rep.p1(where, "a non-root node needs at least one parent")
    if kind == "join" and len(parents) < 2:
        rep.p0(where, "a join needs at least two parents")
    if kind == "root" and depth not in (0, None):
        rep.p0(where, "the only root is depth 0")

    folder = node.get("folder")
    node_dir = None
    if not one_line(folder):
        rep.p0(where, "no folder recorded")
    else:
        node_dir = os.path.join(run_dir, "nodes", str(folder))
        if not os.path.isdir(node_dir):
            rep.p0(where, f"folder nodes/{folder} does not exist")
            node_dir = None

    issues = as_list(node.get("issues"), rep, where, "issues")
    gaps = as_list(node.get("gaps"), rep, where, "gaps")
    check_reviews(rep, run, where, issues, gaps, limits)

    if node_dir is None or status == "queued":
        return

    plan = read(os.path.join(node_dir, "plan.md"))
    if plan is None or not plan.strip() or "_Not written yet._" in plan or "_尚未撰写。_" in plan:
        if status not in ("skipped", "failed"):
            rep.p0(where, "no plan.md; every node past `queued` must have one")
        return
    with rep.gate("coverage"):
        check_plan(rep, where, plan, kind)
        check_cards(rep, where, node_dir, node, kind, status)

    # Angle is a gate on the conclusion, so it runs whenever a conclusion exists — not only on
    # `closed`. Checking it at the end meant a node could sit in synthesizing/reviewing with a
    # survey-shaped conclusion for every phase in between and never be told.
    with rep.gate("angle"):
        _check_angle(rep, where, node_dir, node)

    if status == "closed":
        check_closed_evidence(rep, run, where, node, node_dir)

    synthesis = node.get("synthesis")
    if status in NODE_TERMINAL and status != "skipped":
        if not one_line(synthesis):
            rep.p0(where, f"node is {status} but records no conclusion")
        else:
            text = read(os.path.join(node_dir, str(synthesis)))
            if text is None:
                rep.p0(where, f"synthesis points at {synthesis}, which does not exist")
            else:
                check_synthesis(rep, where, text, node_dir)
    elif one_line(synthesis) and read(os.path.join(node_dir, str(synthesis))) is None:
        rep.p0(where, f"synthesis points at {synthesis}, which does not exist")


def _check_angle(rep: Report, where: str, node_dir: str, node: dict) -> None:
    """The conclusion must carry a judgement, not only a summary of the material.

    Angle is critical, so a conclusion that announces a survey instead of stating a claim is
    P0: it stops delivery. Machine checks cannot judge whether a claim is *good*, but they can
    catch the two shapes that reliably mean there is no claim at all — a conclusion that opens
    by describing the literature, and one with no prose outside its headings.
    """
    name = node.get("synthesis")
    if not one_line(name):
        return
    text = read(os.path.join(node_dir, str(name)))
    if not text:
        return
    body = [ln.strip() for ln in text.splitlines()
            if ln.strip() and not ln.lstrip().startswith(("#", ">", "-", "*", "|"))]
    if not body:
        rep.p0(where, "the conclusion has no prose outside its headings; Angle is critical — a "
                      "conclusion with no claim of its own does not leave this phase "
                      "(references/10-gates.md)")
        return
    opening = one_line(body[0]).lower()
    if any(opening.startswith(o) for o in SUMMARY_OPENERS):
        rep.p0(where, "the conclusion opens by announcing a survey rather than stating a judgement; "
                      "Angle is critical — delete the opener and you should not still have a complete "
                      "survey (references/10-gates.md)")
    if len(body) < 3:
        rep.p2(where, "the conclusion is very short; check that it carries a judgement and not only a summary")


def check_calibration(rep: Report, where: str, text: str, node_dir: str) -> None:
    """Claim strength must not exceed evidence strength — the parts a machine can see.

    Calibration is a major gate: SKILL.md promises that a failure must be fixed or explicitly
    accepted. A gate whose worst output is an advisory note is not a gate, so the two
    overclaiming shapes that a machine can see — a strong verb with no corroboration behind it,
    and an unqualified superlative — fail. Underclaiming stays advisory: stacked hedges are a
    style failure the coordinator can judge and the machine cannot.
    """
    lowered = text.lower()
    sources = count_sources(text)
    for phrase in STRONG_CLAIMS:
        if phrase in lowered:
            rep.p1(where, f"`{phrase.strip()}` claims more than the evidence can carry unless several "
                          f"independent studies stand behind it; the Calibration table reserves "
                          f"demonstrates/establishes for that case — name the studies or lower the verb "
                          f"(references/10-gates.md)")
            break
    for phrase in SUPERLATIVES:
        if phrase in lowered:
            rep.p1(where, f"\"{phrase}\" is an unqualified superlative; limit it to a named dataset and "
                          f"metric, or drop it — an unverified first/only/best is overclaiming")
            break
    stacked = sum(1 for h in HEDGES if h in lowered)
    if stacked >= 4:
        rep.p2(where, f"{stacked} hedge phrases in the conclusion; stacked hedges hide a finding the "
                      f"evidence supports (Calibration, underclaiming)")
    if sources == 0 and any(p in lowered for p in STRONG_CLAIMS):
        rep.p2(where, "a strong verb with no locator in the text; the claim has nothing beside it for a "
                      "reader to check")


def check_closed_evidence(rep: Report, run: dict, where: str, node: dict, node_dir: str) -> None:
    """A closed node must show that the review and the fork decision happened.

    Without this a node can be marked closed with no critique, no issues and no decision, and
    pass every other check — the conclusion exists, so nothing else asks how it was tested.
    """
    rounds = node.get("review_rounds")
    if not isinstance(rounds, int) or rounds < 1:
        rep.p0(where, "closed with `review_rounds` < 1; a conclusion that was never reviewed cannot be moved "
                      "past (if the run is degraded, set review_rounds anyway and label the review self-review)")
    files = as_list(node.get("review_files"), rep, where, "review_files")
    if not files:
        rep.p0(where, "closed with no `review_files`; record the critique files, or the review left no trace")
    for name in files:
        if not one_line(name):
            continue
        if not os.path.isfile(os.path.join(node_dir, str(name))):
            rep.p0(where, f"review_files names {name!r}, which does not exist in the node folder")
    possibility = one_line(node.get("possibility_file"))
    if not possibility:
        rep.p0(where, "closed with no `possibility_file`; the possibility review is a phase, not an option")
    elif not os.path.isfile(os.path.join(node_dir, possibility)):
        rep.p0(where, f"possibility_file {possibility!r} does not exist in the node folder")
    # The fork decision: either a decision names this node, or it said explicitly that nothing forks.
    decided = [d for d in (run.get("decisions") or [])
               if isinstance(d, dict) and d.get("decided_at") == node.get("id")]
    if not decided and not node.get("no_forks"):
        rep.p0(where, "closed with neither a decision recorded for it nor `no_forks: true`; the fork decision "
                      "is a phase, and \"nothing forks\" is a decision that gets recorded")
    if node.get("no_forks") and decided:
        rep.p2(where, "`no_forks: true` but a decision names this node; remove the flag")


def check_plan(rep: Report, where: str, plan: str, kind: str) -> None:
    if kind == "branch":
        if not has_heading(plan, "fork", "decision", "分叉", "决策"):
            rep.p0(where, "a branch node's plan must record the forks it opens (a heading naming them)")
    else:
        if not has_heading(plan, "card", "任务卡", "卡片", "assignment"):
            rep.p0(where, "plan.md has no section naming the cards; a plan with no assignments is not a design")
        check_coverage_table(rep, where, plan)
    for marker in ("TODO", "FIXME", "TBD", "<insert"):
        if marker in plan:
            rep.p1(where, f"plan.md contains the placeholder {marker!r}")
    if re.search(r"\bexample\.com\b", plan):
        rep.p2(where, "'example.com' in plan.md; make sure it is not presented as a real source")


def coverage_section(plan: str) -> list[str] | None:
    """The markdown table under the `## Coverage` heading, up to the next heading."""
    lines = plan.splitlines()
    start = None
    for index, line in enumerate(lines):
        stripped = line.lstrip()
        if stripped.startswith("#") and any(n in stripped.lower() for n in ("coverage", "覆盖")):
            start = index + 1
            break
    if start is None:
        return None
    out = []
    for line in lines[start:]:
        if line.lstrip().startswith("#"):
            break
        out.append(line)
    return out


def check_coverage_table(rep: Report, where: str, plan: str) -> None:
    """Coverage is a gate on the rows, not on the heading.

    The heading being present says nothing: the point of the table is that every row is served
    by a card or declared as a gap, and an unmarked empty cell is an oversight the gate exists
    to catch. So parse the rows and report the specific ones.
    """
    section = coverage_section(plan)
    if section is None:
        rep.p1(where, "plan.md has no coverage table; an empty cell should be a declared gap, not an "
                      "oversight (Coverage, references/10-gates.md)")
        return
    rows = [ln for ln in section if ln.lstrip().startswith("|")]
    rows = [ln for ln in rows if not re.fullmatch(r"\|[\s:|-]+\|", ln.strip())]
    if len(rows) < 2:
        rep.p1(where, "the coverage table has no rows; a design that has not asked what it leaves out "
                      "has not been written yet (Coverage)")
        return
    # A gap is declared by naming a reason, not by the absence of a card.
    no_card = ("", "-", "—", "–", "无", "none", "n/a", "na", "—", "tbd", "未定")
    unserved: list[str] = []
    undeclared: list[str] = []
    for row in rows[1:]:
        cells = [c.strip() for c in row.strip().strip("|").split("|")]
        if not cells or not any(cells):
            continue
        label = one_line(cells[0])
        if not label or set(label) <= set("-: "):
            continue
        card = one_line(cells[1]) if len(cells) > 1 else ""
        gap = one_line(cells[2]) if len(cells) > 2 else ""
        card_ids = re.findall(r"`?([A-Za-z0-9_][\w-]*)`?", card) if card.lower() not in no_card else []
        card_ids = [c for c in card_ids if c.lower() not in no_card]
        if card_ids:
            continue
        if gap and gap.lower() not in no_card:
            continue  # declared: served or a named gap, both are findings
        undeclared.append(label)
        if len(undeclared) == 1:
            unserved.append(label)
    if undeclared:
        listed = ", ".join(f"{u!r}" for u in undeclared[:3]) + ("…" if len(undeclared) > 3 else "")
        rep.p1(where, f"{len(undeclared)} coverage row(s) have neither a card nor a declared gap "
                      f"({listed}); an empty cell is a gap only when it says why — fill the card "
                      f"column or write declared gap + reason in the gap column (Coverage)")


def check_cards(rep: Report, where: str, node_dir: str, node: dict, kind: str, status: str) -> None:
    cards_dir = os.path.join(node_dir, "cards")
    cards = sorted(d for d in os.listdir(cards_dir)) if os.path.isdir(cards_dir) else []
    cards = [c for c in cards if os.path.isdir(os.path.join(cards_dir, c))] if cards else []

    declared = as_list(node.get("cards"), rep, where, "cards")
    for local_id in declared:
        if local_id not in cards:
            rep.p1(where, f"plan declares card {local_id!r} but nodes/.../cards/{local_id} does not exist")

    if kind == "branch" or status in ("planning", "awaiting_approval", "skipped", "failed"):
        return
    if not cards:
        rep.p0(where, "node passed planning but dispatched no cards "
                     "(a pure branch point must set kind=\"branch\")")
        return
    for card in cards:
        cdir = os.path.join(cards_dir, card)
        files = [f for f in os.listdir(cdir) if not f.startswith(".")]
        if not files:
            rep.p1(f"{where} / card {card}", "card folder is empty")
            continue
        if not any(f.endswith(".md") for f in files):
            rep.p1(f"{where} / card {card}", "no deliverable (*.md) in the card folder")
        check_findings(rep, f"{where} / card {card}", cdir, node_dir)


def check_findings(rep: Report, where: str, card_dir: str, node_dir: str) -> None:
    with rep.gate("citation"):
        _check_findings(rep, where, card_dir, node_dir)


def _check_findings(rep: Report, where: str, card_dir: str, node_dir: str) -> None:
    path = os.path.join(card_dir, "findings.json")
    if not os.path.isfile(path):
        rep.p0(where, "no findings.json; findings must be machine-readable for the ledger to be auditable")
        return
    text = read(path)
    if text is None:
        rep.p0(where, "findings.json is not readable UTF-8")
        return
    try:
        data = json.loads(text)
    except ValueError as error:
        rep.p0(where, f"findings.json is not valid JSON: {error}")
        return
    findings = data.get("findings") if isinstance(data, dict) else data
    if not isinstance(findings, list):
        rep.p0(where, "findings.json must be a list, or an object with a `findings` list")
        return
    seen: set[str] = set()
    for index, item in enumerate(findings):
        tag = f"{where} / finding {index + 1}"
        if not isinstance(item, dict):
            rep.p0(tag, "not an object")
            continue
        fid = one_line(item.get("id"))
        if fid:
            if fid in seen:
                rep.p0(tag, f"finding id {fid} repeated")
            seen.add(fid)
        if not one_line(item.get("text")):
            rep.p0(tag, "empty `text`")
        claim_type = item.get("claim_type")
        if claim_type not in CLAIM_TYPES:
            rep.p0(tag, f"claim_type must be one of {sorted(CLAIM_TYPES)} (got {claim_type!r})")
        source = one_line(item.get("source_file"))
        doc = one_line(item.get("doc_id"))
        basis = one_line(item.get("basis"))
        if claim_type == "fact" and not source and not doc:
            rep.p0(tag, "a `fact` with no `source_file` or `doc_id`; a fact is checkable or it is not a fact")
        elif claim_type != "fact" and not source and not doc and not basis:
            rep.p1(tag, f"no `source_file`, `doc_id` or `basis`; say what this {claim_type} rests on "
                        f"(a file, or a one-line statement of the premises or standpoint)")
        if doc and not re.fullmatch(r"[0-9a-f]{12}", doc):
            rep.p1(tag, f"doc_id {doc!r} is not 12 lowercase hex characters")
        if doc and item.get("page") is None:
            rep.p2(tag, "a `doc_id` without a `page`; a document locator should say where in it")
        quote = one_line(item.get("quote"))
        if claim_type == "fact" and not quote:
            rep.p1(tag, "a `fact` with no `quote`; the reader cannot find it on the page")
        page = item.get("page")
        if page is not None and (not isinstance(page, int) or isinstance(page, bool) or page < 1):
            rep.p1(tag, f"page must be a positive integer (got {page!r})")
        state = one_line(item.get("citation_state"))
        if state and state not in CITATION_STATES:
            rep.p1(tag, f"citation_state must be one of {sorted(CITATION_STATES)} (got {state!r})")
        if state == "invalid":
            rep.p0(tag, "citation_state `invalid`: a registry rejects this identifier or the work does not "
                        "exist. Remove the citation — this is the one state that is always an error")
        if state == "unverified":
            rep.p1(tag, "citation_state `unverified`: nobody checked this. Check it, or drop it; do not "
                        "present it as checked")
        if state == "unreachable":
            rep.p1(tag, "citation_state `unreachable`: the fetch failed. The source may be real — flag it "
                        "for a reader who can reach it rather than deleting it or calling it fabricated")
        if state == "partial":
            rep.p2(tag, "citation_state `partial`: the source supports only part of the claim — narrow the "
                        "claim to what it supports")
        if claim_type == "fact" and not state:
            rep.p2(tag, "no `citation_state`; an unmarked citation reads as unchecked (see the five states "
                        "in references/10-gates.md)")
        if item.get("single_source") is True and claim_type == "fact":
            rep.p2(tag, "`single_source: true`: legal for archives and unique documents, but the reader "
                        "should know this claim has one source, not corroboration")
        if "single_source" in item and not isinstance(item["single_source"], bool):
            rep.p1(tag, f"`single_source` must be true or false (got {item['single_source']!r})")
        if source and quote:
            check_quote(rep, tag, source, quote, node_dir)
        revises = one_line(item.get("revises"))
        if revises and revises not in seen:
            rep.p2(tag, f"`revises` names {revises!r}, which is not a finding id in this card")
        # Optional fields documented in references/02-cards.md. `depends_on` pointing at a
        # finding that does not exist silently breaks the forward trace a correction needs.
        depends = item.get("depends_on")
        if depends is not None:
            if not isinstance(depends, list) or not all(isinstance(d, str) and d.strip() for d in depends):
                rep.p1(tag, "`depends_on` must be a list of finding ids")
            else:
                for target in depends:
                    if target.strip() not in seen:
                        rep.p2(tag, f"`depends_on` names {target!r}, which is not a finding id in this card")
        uncertain = item.get("uncertain")
        if uncertain is not None and not one_line(uncertain):
            rep.p2(tag, "`uncertain` is present but empty; name the open question or drop the field")


def resolve_source(source: str, node_dir: str) -> str | None:
    """A source path may be relative to the project, the run, or the card's node."""
    if os.path.isabs(source):
        candidates = [source]
    else:
        run_dir = os.path.dirname(os.path.dirname(node_dir))
        project = os.path.dirname(os.path.dirname(run_dir))
        candidates = [source, os.path.join(run_dir, source), os.path.join(node_dir, source),
                      os.path.join(project, source)]
    for candidate in candidates:
        path = os.path.realpath(candidate)
        if os.path.isfile(path):
            return path
    return None


def check_quote(rep: Report, tag: str, source: str, quote: str, node_dir: str) -> None:
    path = resolve_source(source, node_dir)
    if path is None:
        rep.p0(tag, f"source_file {source!r} does not exist; a locator that resolves to nothing is not a locator")
        return
    text = read(path)
    if text is None:
        rep.p1(tag, f"{source!r} is not readable as UTF-8; the quotation could not be checked")
        return
    if one_line(quote) not in one_line(text):
        rep.p1(tag, f"the quotation is not in {source!r} (whitespace-normalised). OCR and typography can "
                    f"cause this legitimately; check the page before dismissing it")


def check_synthesis(rep: Report, where: str, text: str, node_dir: str) -> None:
    with rep.gate("coverage"):
        _check_synthesis_headings(rep, where, text, node_dir)
    with rep.gate("citation"):
        _check_source_states(rep, where, text, node_dir)
    with rep.gate("calibration"):
        check_calibration(rep, where, text, node_dir)


def count_sources(text: str) -> int:
    """How many distinct locators the text cites — the evidence base Calibration reads against."""
    return len({m.group(1) or m.group(0) for m in CITATION_TOKEN.finditer(text)})


# --------------------------------------------------------------------------- report gates

def check_report(rep: Report, run: dict, run_dir: str) -> None:
    """Taxonomy and Weaving are gates on the delivered text, so they read it.

    They are checked on the final report (and the draft, while it is the newest text). Both
    are major: a report can be delivered with them failed only if the failure is accepted, so
    each reports the specific sections or paragraphs that carry the problem — a gate that says
    "somewhere in the text" cannot be acted on.
    """
    stages = run.get("final") if isinstance(run.get("final"), dict) else {}
    final_dir = os.path.join(run_dir, "final")
    for stage in ("final", "draft"):
        record = one_line(stages.get(stage))
        if not record:
            continue
        path = os.path.join(final_dir, record)
        text = read(path)
        if text is None:
            continue
        where = f"final/{record}"
        with rep.gate("taxonomy"):
            _check_taxonomy(rep, where, text)
        with rep.gate("weaving"):
            _check_weaving(rep, where, text)
        break


def _check_taxonomy(rep: Report, where: str, text: str) -> None:
    """Sections must be mutually exclusive and jointly exhaustive over the material.

    What a machine can see: headings that name a source, card or phase instead of a topic
    (the material is filed, not cut); and headings that repeat each other's words, which is
    what overlapping sections look like from outside.
    """
    headings = [(m.group(1), m.group(2).strip())
                for m in re.finditer(r"^(#{2,4})\s+(.+?)\s*$", text, re.M)]
    topics = [h for level, h in headings if len(level) >= 2]
    topics = [h for h in topics if not APPARATUS_HEADING.match(h)]
    filed = [h for h in topics if NON_TOPIC_HEADING.match(h)]
    if filed:
        rep.p1(where, f"{len(filed)} section(s) name a source, card or phase rather than a topic "
                      f"({', '.join(repr(f) for f in filed[:3])}{'…' if len(filed) > 3 else ''}); "
                      f"Taxonomy asks the sections to be cut by what the material shows "
                      f"(references/10-gates.md)")
    # Overlap: two headings that share most of their words. CJK has no spaces, so a heading is
    # cut into character bigrams as well as whole Latin words.
    if len(topics) >= 4:
        seen: list[tuple[set[str], str]] = []
        for topic in topics:
            words = topic_words(topic)
            if not words:
                continue
            for earlier, original in seen:
                overlap = words & earlier
                if len(overlap) >= 2 and len(overlap) >= min(len(words), len(earlier)) * 0.6:
                    sample = ", ".join(sorted(overlap)[:3])
                    rep.p1(where, f"sections {original!r} and {topic!r} overlap on “{sample}”; either "
                                  f"they are one section or the taxonomy is not yet cut by what the "
                                  f"material shows (Taxonomy)")
                    break
            seen.append((words, topic))


def topic_words(topic: str) -> set[str]:
    """The comparable tokens of a heading: Latin words plus CJK character bigrams."""
    words = {w for w in re.findall(r"[A-Za-z]{3,}", topic.lower())}
    cjk = re.findall(r"[\u4e00-\u9fff]", topic)
    words |= {cjk[i] + cjk[i + 1] for i in range(len(cjk) - 1)}
    return words


def _check_weaving(rep: Report, where: str, text: str) -> None:
    """Prose must compare sources inside a paragraph, not list them one per paragraph.

    The shape a machine can see: a body paragraph that cites exactly one source and does not
    name a second voice, a contrast or a condition. One such paragraph is a catalogue entry,
    and a report made of them is an annotated bibliography — which is exactly what the Weaving
    gate exists to catch. It is only reported when it is the dominant shape, since a report
    legitimately has some single-source paragraphs (a unique archive, a method note).
    """
    paragraphs, current = [], []
    for line in text.splitlines():
        if not line.strip():
            if current:
                paragraphs.append("\n".join(current))
                current = []
            continue
        stripped = line.lstrip()
        if stripped.startswith(("#", "|", ">", "```")) or re.match(r"^\s*[-*+]\s", stripped):
            if current:
                paragraphs.append("\n".join(current))
                current = []
            continue
        current.append(line)
    if current:
        paragraphs.append("\n".join(current))
    # Length is measured in words for Latin scripts and characters for CJK: a dense Chinese
    # paragraph is long while holding very few whitespace-separated tokens.
    def size(p: str) -> int:
        return max(len(p.split()), len(re.findall(r"[\u4e00-\u9fff]", p)) // 2)
    body = [p for p in paragraphs if size(p) >= 25]
    if len(body) < 4:
        return
    single = []
    for para in body:
        cites = {m.group(1) for m in CITATION_TOKEN.finditer(para) if m.group(1)}
        if len(cites) != 1:
            continue
        if re.search(r"(whereas|however|but|although|while|in contrast|by contrast|unlike|"
                     r"相比之下|然而|但|不同于|与此相反|相反地)", para, re.I):
            continue
        single.append(para)
    if len(single) >= 3 and len(single) >= len(body) * 0.5:
        sample = one_line(single[0])[:60]
        rep.p1(where, f"{len(single)} of {len(body)} body paragraphs cite exactly one source and name no "
                      f"contrast (e.g. “{sample}…”); that is the catalogue shape — Weaving asks the "
                      f"comparison to happen inside the paragraph (references/10-gates.md)")


def _check_synthesis_headings(rep: Report, where: str, text: str, node_dir: str) -> None:
    if not has_heading(text, "sources", "来源"):
        rep.p0(where, "conclusion has no `## Sources` section; every text carries the sources it rests on")
    if not has_heading(text, "counterevidence", "counter-evidence", "反证", "反面证据"):
        rep.p0(where, "conclusion has no counterevidence section; a conclusion with none has not looked")
    if not has_heading(text, "premise", "presupposition", "前提", "预设"):
        rep.p1(where, "conclusion names no premise it rests on")
    if not has_heading(text, "limit", "uncertain", "unresolved", "局限", "不确定", "未决"):
        rep.p1(where, "conclusion names no limits, unresolved questions or uncertainty")
    for entry in re.findall(r"`([^`]+)`", text):
        if "/" not in entry or " " in entry:
            continue
        if resolve_source(entry, node_dir) is None:
            rep.p2(where, f"a code span {entry!r} looks like a path but does not resolve")


def _check_source_states(rep: Report, where: str, text: str, node_dir: str) -> None:
    """Read the `## Sources` list: each entry may carry a state after its locator."""
    section = source_section(text)
    if section is None:
        return
    for line in section:
        if not line.strip().startswith(("-", "*")):
            continue
        body = one_line(line.lstrip().lstrip("-*").strip())
        if not body:
            continue
        state = None
        for candidate in CITATION_STATES:
            if re.search(rf"(?:—|--|:)\s*{candidate}\b", body, re.I):
                state = candidate
                break
        if state == "invalid":
            rep.p0(where, f"a source is marked `invalid`: {body[:110]}")
        elif state == "unverified":
            rep.p1(where, f"a source is `unverified` — check it or drop it: {body[:110]}")
        elif state == "unreachable":
            rep.p1(where, f"a source is `unreachable` (not the same as fabricated; flag it): {body[:110]}")
        elif state is None:
            rep.p2(where, f"a source carries no citation state, so it reads as unchecked: {body[:110]}")


def source_section(text: str) -> list[str] | None:
    """The lines under the `## Sources` heading, up to the next heading of the same or higher rank."""
    lines = text.splitlines()
    start = None
    for index, line in enumerate(lines):
        stripped = line.lstrip()
        if stripped.startswith("#") and any(n in stripped.lower() for n in ("sources", "来源")):
            start = index + 1
            break
    if start is None:
        return None
    out = []
    for line in lines[start:]:
        if line.lstrip().startswith("#"):
            break
        out.append(line)
    return out


# --------------------------------------------------------------------------- reviews

def check_reviews(rep: Report, run: dict, where: str, issues: list, gaps: list, limits: dict) -> None:
    node_ids = {n.get("id") for n in run["nodes"] if isinstance(n, dict)}
    for key, items, allowed, label in (
        ("issues", issues, DISPOSITIONS, "issue"),
        ("gaps", gaps, GAP_DISPOSITIONS, "gap"),
    ):
        seen: set[str] = set()
        for item in items:
            if not isinstance(item, dict):
                rep.p0(where, f"an entry of `{key}` is not an object")
                continue
            iid = one_line(item.get("id"))
            if not iid:
                rep.p0(where, f"a {label} has no id")
                continue
            if iid in seen:
                rep.p0(where, f"{label} id {iid} repeated")
            seen.add(iid)
            if key == "issues" and item.get("material") is False:
                continue
            # Documented fields that were never checked. `round` is what lets a reader tell
            # which critique produced the objection; `priority` orders the work.
            priority = item.get("priority")
            if priority is not None and (not isinstance(priority, int) or isinstance(priority, bool)):
                rep.p1(where, f"{label} {iid} has a non-integer `priority` (got {priority!r})")
            if key == "issues":
                rnd = item.get("round")
                if rnd is not None and (not isinstance(rnd, int) or isinstance(rnd, bool) or rnd < 1):
                    rep.p1(where, f"issue {iid} has a non-positive-integer `round` (got {rnd!r})")
                revision = item.get("revision")
                if revision is not None and not isinstance(revision, str):
                    rep.p1(where, f"issue {iid} has a `revision` that is not a filename string")
                elif one_line(item.get("disposition")) == "revise" and not one_line(revision):
                    rep.p1(where, f"issue {iid} is `revise` but names no `revision`; the reader needs to "
                                  f"know which synthesis-N.md answers it")
            disposition = one_line(item.get("disposition"))
            if not disposition:
                rep.p0(where, f"{label} {iid} has no disposition; every material {label} needs exactly one")
                continue
            if disposition not in allowed:
                hint = ""
                if key == "gaps" and disposition == "branch":
                    hint = "; a gap is never a fork — reclassify it as a possibility, or fill, concede or park it"
                if key == "issues" and disposition == "correct" and limits.get("revisions", 0) > 0:
                    hint = "; `correct` only when no revision is left"
                rep.p0(where, f"{label} {iid} has the invalid disposition {disposition!r}{hint}")
                continue
            if disposition in ("rebut", "concede", "covered", "park", "correct", "branch") \
                    and not one_line(item.get("reason")):
                rep.p1(where, f"{label} {iid} is {disposition} but records no reason")
            if disposition == "covered":
                target = one_line(item.get("covered_by"))
                if not target:
                    rep.p1(where, f"{label} {iid} is covered but names no node")
                elif target not in node_ids:
                    rep.p0(where, f"{label} {iid} is covered by {target!r}, which is not a node of this run")
            if disposition == "revise" and key == "gaps" and limits.get("followups", 0) <= 0:
                rep.p1(where, f"gap {iid} is `revise` but no follow-up round remains; a gap cannot be closed by "
                              f"rewriting prose — concede or park it")


# --------------------------------------------------------------------------- graph

def check_graph(rep: Report, run: dict, by_id: dict, limits: dict) -> None:
    for node in run["nodes"]:
        if not isinstance(node, dict) or not one_line(node.get("id")):
            continue
        nid = node["id"]
        depth = node.get("depth")
        parents = node.get("parents") if isinstance(node.get("parents"), list) else []
        for parent in parents:
            other = by_id.get(parent)
            if other is None:
                rep.p0(f"node {nid}", f"parent {parent} is not a node of this run")
                continue
            pd = other.get("depth")
            if isinstance(depth, int) and isinstance(pd, int):
                if pd >= depth:
                    rep.p0(f"node {nid}", f"parent {parent} is not above it (depth {pd} >= {depth})")
                elif pd != depth - 1:
                    rep.p1(f"node {nid}", f"depth {depth} but its deepest parent is at {pd}; a node sits one "
                                          f"level below its parents")

    state: dict[str, int] = {}

    def visit(nid: str, trail: list[str]) -> None:
        if state.get(nid) == 1:
            rep.p0("run.json", "cycle in parents: " + " → ".join(trail + [nid]))
            return
        if state.get(nid) == 2 or nid not in by_id:
            return
        state[nid] = 1
        parents = by_id[nid].get("parents")
        for parent in parents if isinstance(parents, list) else []:
            visit(parent, trail + [nid])
        state[nid] = 2

    for nid in list(by_id):
        visit(nid, [])

    roots = [n for n in by_id.values() if n.get("depth") == 0]
    if len(roots) != 1:
        rep.p0("run.json", f"{len(roots)} nodes at depth 0; a run has exactly one root")

    option_ids: set[str] = set()
    decision_ids: set[str] = set()
    for index, decision in enumerate(as_list(run.get("decisions"), rep, "run.json", "decisions")):
        if not isinstance(decision, dict):
            rep.p0("run.json", "a decision is not an object")
            continue
        did = one_line(decision.get("id"))
        tag = f"decision {did or index + 1}"
        if not did:
            rep.p0(tag, "no id")
        elif did in decision_ids:
            rep.p0("run.json", f"decision id {did} repeated")
        decision_ids.add(did)
        decided_at = one_line(decision.get("decided_at"))
        if not decided_at:
            rep.p1(tag, "no `decided_at` node; a fork belongs to the node that decided it")
        elif decided_at not in by_id:
            rep.p0(tag, f"decided_at {decided_at!r} is not a node of this run")
        if not one_line(decision.get("question")):
            rep.p1(tag, "no `question`; a decision without the question it splits on cannot be judged")
        if not one_line(decision.get("stakes")):
            rep.p1(tag, "no `stakes`; a decision must say what turns on it, or the reader cannot tell "
                        "why the fork was worth a node")
        options = as_list(decision.get("options"), rep, tag, "options")
        if len(options) < 2:
            rep.p0(tag, "a decision needs at least two options")
        own = [o for o in options if isinstance(o, dict) and o.get("own")]
        if len(own) > 1:
            rep.p0(tag, "at most one option may be the node's own line")
        for option in options:
            if not isinstance(option, dict):
                rep.p0(tag, "an option is not an object")
                continue
            oid = one_line(option.get("id"))
            if not oid:
                rep.p0(tag, "an option has no id; dispositions and decisions reference it")
                continue
            if oid in option_ids:
                rep.p0("run.json", f"option id {oid} appears in more than one decision")
            option_ids.add(oid)
            if not one_line(option.get("premise")):
                rep.p1(f"option {oid}", "no premise; a path that does not state what it assumes cannot be judged")
            if not one_line(option.get("label")):
                rep.p1(f"option {oid}", "no `label`; paths.md and the report name the option by it")
            srcs = option.get("sources")
            if srcs is not None:
                if not isinstance(srcs, list) or not all(isinstance(s, str) and s.strip() for s in srcs):
                    rep.p1(f"option {oid}", "`sources` must be a list of alternative ids")
                else:
                    known = {str(a.get("id")) for a in as_list(run.get("alternatives"), rep, "run.json",
                                                               "alternatives") if isinstance(a, dict)}
                    for src in srcs:
                        if src not in known:
                            rep.p2(f"option {oid}", f"`sources` names {src!r}, which is not an alternative "
                                                    f"of this run; the premise it carries cannot be traced back")
            if "own" in option and not isinstance(option["own"], bool):
                rep.p1(f"option {oid}", f"`own` must be true or false (got {option['own']!r})")
            states = [k for k in OPTION_STATES if one_line(option.get(k))]
            if len(states) > 1:
                rep.p0(f"option {oid}", f"two outcomes at once ({', '.join(states)}); an option has exactly one")
            target = one_line(option.get("node"))
            if target and target not in by_id:
                rep.p0(f"option {oid}", f"pursued by {target}, which is not a node of this run")
            if not states:
                rep.p2(f"option {oid}", "pending: no node pursues it and no reason is recorded yet")
            reason = one_line(option.get("reason"))
            if reason and any(phrase in reason.lower() for phrase in NON_REASONS):
                rep.p1(f"option {oid}", f"{reason!r} is not a reason; name the constraint that stopped it")

    for relation in as_list(run.get("relations"), rep, "run.json", "relations"):
        if not isinstance(relation, dict):
            rep.p0("run.json", "a relation is not an object")
            continue
        if relation.get("kind") not in RELATION_KINDS:
            rep.p0("run.json", f"unknown relation kind {relation.get('kind')!r}")
        nodes = as_list(relation.get("nodes"), rep, "run.json", "relations[].nodes")
        if len(nodes) < 2:
            rep.p0("run.json", "a relation needs at least two nodes")
        for nid in nodes:
            if nid not in by_id:
                rep.p0("run.json", f"relation names {nid}, which is not a node of this run")
        # `note` is what makes a relation readable in graph.md; scaffold.py used to assume it
        # always existed, which is how a legal relation crashed the resume entry point.
        if not one_line(relation.get("note")):
            rep.p2("run.json", f"a {relation.get('kind')!r} relation has no `note`; say what the two "
                               f"nodes share or how they differ, or the relation is unreadable in graph.md")

    for join in as_list(run.get("joins"), rep, "run.json", "joins"):
        if not isinstance(join, dict):
            rep.p0("run.json", "a join is not an object")
            continue
        tag = f"join {join.get('id') or '?'}"
        parents = as_list(join.get("parents"), rep, tag, "parents")
        if len(parents) < 2:
            rep.p0(tag, "a join needs at least two parents")
        for parent in parents:
            other = by_id.get(parent)
            if other is None:
                rep.p0(tag, f"parent {parent} is not a node of this run")
            elif other.get("status") not in NODE_TERMINAL:
                rep.p1(tag, f"parent {parent} is {other.get('status')}, not finished")
        if not one_line(join.get("question")):
            rep.p0(tag, "no question for the joined node")
        if not one_line(join.get("rationale")):
            rep.p1(tag, "no rationale saying what each parent brings and where they differ")

    for item in as_list(run.get("not_pursued"), rep, "run.json", "not_pursued"):
        if not isinstance(item, dict):
            rep.p0("run.json", "a not_pursued entry is not an object")
            continue
        option = one_line(item.get("option"))
        reason = one_line(item.get("reason"))
        if option and option not in option_ids:
            rep.p1(f"option {option}", "recorded as not pursued but is not an option of this run")
        if not reason:
            rep.p1(f"option {option}", "not pursued with no reason")
        elif any(phrase in reason.lower() for phrase in NON_REASONS):
            rep.p1(f"option {option}", f"{reason!r} is not a reason; a genuine possibility is opened or the "
                                       f"constraint that stopped it is named")

    for erratum in as_list(run.get("errata"), rep, "run.json", "errata"):
        if not isinstance(erratum, dict):
            rep.p0("run.json", "an erratum is not an object")
            continue
        target = one_line(erratum.get("against"))
        if target and target not in by_id:
            rep.p0("run.json", f"erratum against {target!r}, which is not a node of this run")
        for key in ("claim", "correction", "grounds"):
            if not one_line(erratum.get(key)):
                rep.p1("run.json", f"erratum against {target or '?'} has no `{key}`")


def check_alternatives(rep: Report, run: dict, by_id: dict) -> None:
    """Every proposal from a possibility review has exactly one outcome."""
    proposals = as_list(run.get("alternatives"), rep, "run.json", "alternatives")
    for item in proposals:
        if not isinstance(item, dict):
            rep.p0("run.json", "an alternative is not an object")
            continue
        oid = one_line(item.get("id"))
        if not oid:
            rep.p0("run.json", "an alternative has no id")
            continue
        if not one_line(item.get("proposal")):
            rep.p0(f"alternative {oid}", "no proposal text")
        gap = item.get("gap")
        if not isinstance(gap, bool):
            rep.p0(f"alternative {oid}", f"`gap` must be true or false (got {gap!r})")
        outcome = one_line(item.get("outcome"))
        covered = one_line(item.get("covered_by"))
        if not outcome and not covered:
            rep.p1(f"alternative {oid}", "no outcome recorded; every proposal ends in an option, a decline, "
                                        f"a gap disposition, or a covered_by")
        if outcome and outcome not in ("option", "declined", "gap_revise", "gap_rebut", "gap_concede",
                                       "gap_covered", "gap_park"):
            rep.p1(f"alternative {oid}", f"unknown outcome {outcome!r}")
        if outcome == "option" and not one_line(item.get("outcome_ref")):
            rep.p1(f"alternative {oid}", "`outcome: option` but no `outcome_ref`; name the option that "
                                        "carries this proposal, or the proposal's归宿 cannot be traced")
        elif one_line(item.get("outcome_ref")) and outcome in ("option", None, ""):
            ref = one_line(item["outcome_ref"])
            known = {str(o.get("id")) for d in as_list(run.get("decisions"), rep, "run.json", "decisions")
                     if isinstance(d, dict) for o in as_list(d.get("options"), rep, "run.json", "options")
                     if isinstance(o, dict)}
            if ref not in known:
                rep.p1(f"alternative {oid}", f"`outcome_ref` names {ref!r}, which is not an option of this run")

    # `declined` is the run-level record of proposals that were refused (references/05-possibility.md).
    option_ids = {str(o.get("id")) for d in as_list(run.get("decisions"), rep, "run.json", "decisions")
                  if isinstance(d, dict) for o in as_list(d.get("options"), rep, "run.json", "options")
                  if isinstance(o, dict)}
    alt_ids = {str(a.get("id")) for a in as_list(run.get("alternatives"), rep, "run.json", "alternatives")
               if isinstance(a, dict)}
    for entry in as_list(run.get("declined"), rep, "run.json", "declined"):
        if not isinstance(entry, dict):
            rep.p0("run.json", "a declined entry is not an object")
            continue
        target = one_line(entry.get("issue_id")) or one_line(entry.get("option")) \
            or one_line(entry.get("alternative"))
        if not target:
            rep.p1("run.json", "a declined entry names no proposal (`issue_id`, `option` or `alternative`)")
        elif alt_ids or option_ids:
            if target not in alt_ids and target not in option_ids:
                rep.p1("run.json", f"declined names {target!r}, which is neither an alternative nor an "
                                   f"option of this run")
        if not one_line(entry.get("reason")):
            rep.p1("run.json", f"declined {target or '?'} has no reason; a refusal with no reason is "
                               f"indistinguishable from an oversight")
        elif any(phrase in one_line(entry["reason"]).lower() for phrase in NON_REASONS):
            rep.p1("run.json", f"declined {target or '?'}: {one_line(entry['reason'])!r} is not a reason; "
                               f"name the constraint that stopped it")


def check_consent(rep: Report, run: dict) -> None:
    dissolving = [n.get("id") for n in run["nodes"]
                  if isinstance(n, dict) and n.get("dissolves") in ("research_question", "question")]
    if not dissolving:
        return
    consent = as_dict(run.get("consent"), rep, "run.json", "consent").get("dissolution")
    if consent is None:
        rep.p0("run.json", f"nodes {', '.join(dissolving)} dissolve the research question but the user has not been "
                           f"asked; record consent.dissolution before delivering")
    elif consent is False:
        rep.p1("run.json", "the user did not agree to the dissolution; the report must answer the question as asked "
                           "and give the dissolution as one reading")


if __name__ == "__main__":
    sys.exit(main())
