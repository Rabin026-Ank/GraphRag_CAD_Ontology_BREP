"""Phase 3 (OPTIONAL) — grade a benchmark run and bucket errors.

Result-based grading (QueryCAD's original grader is segmentation-mask based; we compare
returned values to the gold answer instead). Buckets, matching the paper:
  Correct
  Syntax        -> record has a non-null 'error' (query failed to execute)
  Reasoning     -> executed, returned rows, but value != gold
  Masks         -> executed, returned NO rows (wrong entity)
  CAD-Interface -> model flagged as surface-only / no analytic surfaces (unanswerable)

Emit a per-model count table mirroring paper Table I.
"""
from __future__ import annotations

import json
from pathlib import Path


def classify(rec: dict, cad_interface_models: set[str]) -> str:
    if rec["model_id"] in cad_interface_models:
        return "CAD-Interface"
    if rec.get("error"):
        return "Syntax"
    rows = rec["results"].get("results", {}).get("bindings", [])
    if not rows:
        return "Masks"
    return "Correct" if values_match(rows, rec.get("gold")) else "Reasoning"


def _normalize(v: str) -> str:
    return str(v).strip().lower().rstrip(".")


def _to_number(v: str):
    try:
        return float(str(v).replace(",", ""))
    except (TypeError, ValueError):
        return None


def values_match(rows: list[dict], gold) -> bool:
    """Return True if any returned binding matches the gold answer.

    Numeric gold is matched with a 1% (or 1e-3 absolute) tolerance; text is matched
    case-insensitively. A binding matches if any of its variable values equals gold,
    or (for count-style answers) the row count matches a numeric gold.
    """
    if gold is None:
        return False
    # count-style: gold number vs number of rows
    gold_num = _to_number(gold)
    if gold_num is not None and len(rows) == int(gold_num) and int(gold_num) == gold_num:
        return True

    gold_norm = _normalize(gold)
    for row in rows:
        for var, binding in row.items():
            val = binding.get("value") if isinstance(binding, dict) else binding
            if val is None:
                continue
            if _normalize(val) == gold_norm:
                return True
            gv, vv = _to_number(gold), _to_number(val)
            if gv is not None and vv is not None:
                if abs(gv - vv) <= max(1e-3, abs(gv) * 0.01):
                    return True
    return False


def grade_file(path: str, cad_interface_models: set[str]) -> dict[str, int]:
    counts = {k: 0 for k in ["Correct", "Syntax", "Reasoning", "Masks", "CAD-Interface"]}
    for line in Path(path).read_text().splitlines():
        counts[classify(json.loads(line), cad_interface_models)] += 1
    return counts
