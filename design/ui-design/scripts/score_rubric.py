#!/usr/bin/env python3
"""Weighted v5.0 rubric scorer (7 aesthetic dimensions by surface profile).

This scores *declared evidence*, not pixels. A human/LLM must supply the 0-5
scores; the script only applies the profile weights and gate. It never writes
`accepted:true` on its own.
"""
from __future__ import annotations
import argparse, json, sys

DIMS = ["subject", "physical", "type", "composition", "restraint", "finish", "motion"]
WEIGHTS = {
    "expressive": dict(zip(DIMS, [20, 20, 15, 20, 10, 10, 5])),
    "product":    dict(zip(DIMS, [15, 10, 20, 10, 15, 20, 10])),
    "utility":    dict(zip(DIMS, [5, 5, 15, 5, 25, 35, 10])),
    "editorial":  dict(zip(DIMS, [15, 10, 25, 15, 10, 15, 10])),
    "catalog":    dict(zip(DIMS, [10, 10, 15, 10, 20, 25, 10])),
}

def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--profile", required=True, choices=sorted(WEIGHTS))
    ap.add_argument("--scores", required=True, help='JSON object with the seven 0-5 scores')
    ap.add_argument("--label", default="")
    ap.add_argument("--evidence", default="")
    a = ap.parse_args()
    try:
        scores = json.loads(a.scores)
    except json.JSONDecodeError as exc:
        ap.error(f"invalid --scores JSON: {exc}")
    missing = [d for d in DIMS if d not in scores]
    if missing:
        ap.error("missing scores: " + ", ".join(missing))
    for d in DIMS:
        v = scores[d]
        if not isinstance(v, (int, float)) or not 0 <= v <= 5:
            ap.error(f"{d} must be a number 0-5")
    weights = WEIGHTS[a.profile]
    weighted = round(sum(scores[d] * weights[d] for d in DIMS) / 100, 2)
    no_bad = all(scores[d] > 2 for d in DIMS)
    profile_gate = True
    if a.profile == "utility":
        profile_gate = scores["restraint"] >= 3 and scores["finish"] >= 3
    if a.profile == "product":
        profile_gate = scores["motion"] >= 3
    result = {
        "label": a.label,
        "profile": a.profile,
        "scores": {d: scores[d] for d in DIMS},
        "weights": weights,
        "weighted": weighted,
        "pass": weighted >= 4.0 and no_bad and profile_gate,
        "gates": {"weighted_ge_4": weighted >= 4.0, "no_dimension_le_2": no_bad,
                  "profile_gate": profile_gate},
        "evidence": a.evidence,
        "accepted": False,
        "note": "rubric score is evidence-backed human/LLM review; accepted also requires compliance + appropriateness",
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["pass"] else 1

if __name__ == "__main__":
    raise SystemExit(main())
