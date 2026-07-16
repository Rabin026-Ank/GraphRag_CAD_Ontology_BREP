"""Smoke test — the Phase 2 acceptance path on one model.

Prereqs: GraphDB up, `graphrag` repo with OntoBREP loaded, cad-00000182 converted and
loaded into its named graph, env vars set. Run:  python -m tests.test_smoke
"""
from ontobrep_kg.pipeline import ask

QUESTION = "What is the diameter of the largest hole located on the top of the cad-00000182 object?"


def main() -> None:
    out = ask(QUESTION, model_id="cad-00000182")
    print("SPARQL:\n", out["sparql"])
    print("\nERROR:", out["error"])
    print("\nRESULT rows:", out["results"].get("results", {}).get("bindings", []))
    print("\nANSWER:\n", out["answer"])
    assert out["error"] is None, "SPARQL failed to execute"
    assert out["results"]["results"]["bindings"], "no rows returned (Masks-type failure)"


if __name__ == "__main__":
    main()
