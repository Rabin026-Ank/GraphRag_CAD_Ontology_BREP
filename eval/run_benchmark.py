"""Phase 3 (OPTIONAL) — run the QueryCAD 111-question benchmark.

Loads QueryCAD's questions (github.com/claudius-kienle/querycad), runs each through
pipeline.ask (no iterative refinement, matching the paper), writes per-question
sparql/result/answer to eval/runs/<model>.jsonl for grading.

TODO:
  - point QUERYCAD_DIR at the cloned benchmark
  - parse its question file (question text + gold answer + model id)
  - ensure every referenced model was converted (step_to_owl) and loaded
"""
from __future__ import annotations

import json
from pathlib import Path

from ontobrep_kg.pipeline import ask

QUERYCAD_DIR = Path("data/querycad")  # TODO: set to clone location
OUT_DIR = Path("eval/runs")


def load_questions() -> list[dict]:
    raise NotImplementedError("parse QueryCAD questions -> [{question, gold, model_id}]")


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    from ontobrep_kg.config import CFG
    out_path = OUT_DIR / f"{CFG.llm_model.replace('/', '_')}.jsonl"
    with out_path.open("w") as fh:
        for q in load_questions():
            rec = ask(q["question"], q["model_id"])
            rec["gold"] = q.get("gold")
            fh.write(json.dumps(rec) + "\n")
    print("wrote", out_path)


if __name__ == "__main__":
    main()
