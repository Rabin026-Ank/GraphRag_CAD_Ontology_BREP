"""Phase 2 — end-to-end: question -> SPARQL -> results -> NL answer.

    from ontobrep_kg.pipeline import ask
    out = ask("What is the diameter of the largest hole on top of cad-00000182?",
              model_id="cad-00000182")
    print(out["answer"])

No iterative refinement in the baseline (matches the paper). Returns the intermediate
sparql + results so callers/eval can inspect them.
"""
from __future__ import annotations

from typing import Any

from . import answer_gen, graphdb_client, nl_to_sparql
from .config import CFG


def ask(question: str, model_id: str) -> dict[str, Any]:
    graph_iri = CFG.model_graph_iri(model_id)
    sparql = nl_to_sparql.nl_to_sparql(question, graph_iri)
    try:
        results = graphdb_client.run(sparql)
        error = None
    except Exception as e:  # syntax / execution failure
        results, error = {"results": {"bindings": []}}, str(e)
    answer = answer_gen.generate_answer(question, sparql, results)
    return {"question": question, "model_id": model_id,
            "sparql": sparql, "results": results, "error": error, "answer": answer}


if __name__ == "__main__":  # pragma: no cover
    import argparse

    ap = argparse.ArgumentParser(description="Ask a CAD model a natural-language question.")
    ap.add_argument("question")
    ap.add_argument("--model-id", required=True)
    args = ap.parse_args()
    out = ask(args.question, args.model_id)
    print("SPARQL:\n", out["sparql"])
    if out["error"]:
        print("\nSPARQL ERROR:", out["error"])
    print("\nANSWER:\n", out["answer"])
