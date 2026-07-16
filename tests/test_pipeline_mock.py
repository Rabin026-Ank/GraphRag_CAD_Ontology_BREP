"""Offline end-to-end test for the Phase 2 pipeline wiring.

Mocks the LLM (nl_to_sparql + answer_gen) and the GraphDB client (run SPARQL against a
local rdflib graph) so the full `pipeline.ask` path is exercised without any network or
external service. Validates: SPARQL fences are stripped, the query executes, results are
non-empty, and the NL answer is produced.
"""
from __future__ import annotations

import json
from pathlib import Path

from rdflib import Graph, Namespace

import ontobrep_kg.answer_gen as answer_gen
import ontobrep_kg.graphdb_client as graphdb_client
import ontobrep_kg.llm as llm
import ontobrep_kg.nl_to_sparql as nl_to_sparql
from ontobrep_kg import pipeline
from ontobrep_kg.step_to_owl import step_to_graph

CAD = Namespace("http://www.fortiss.org/ont/ontobrep#")

_TTL_SOURCES = [
    Path(__file__).resolve().parents[2] / "Step_graph_data" / "STEP_models",
    Path(__file__).resolve().parent.parent / "data" / "models",
]


def _find_step() -> str | None:
    for base in _TTL_SOURCES:
        if base.exists():
            for p in sorted(base.rglob("*.step")) + sorted(base.rglob("*.stp")):
                return str(p)
    return None


# A query the local graph can actually answer (the shared test STEP has a hole
# with radius 4.25 / diameter 8.5, axis along Y so not "on top").
_GOLDEN_SPARQL = """
PREFIX cad: <http://www.fortiss.org/ont/ontobrep#>
PREFIX xsd: <http://www.w3.org/2001/XMLSchema#>
SELECT ?face ((2 * ?radius) as ?diameter)
WHERE {
  ?face a cad:Face ;
        cad:hasForwardOrientation "false"^^xsd:boolean ;
        cad:representedBy+ ?cylSurf ;
        cad:umax ?umax ; cad:umin ?umin ; cad:vmax ?vmax ; cad:vmin ?vmin .
  FILTER (ABS(?umax - ?umin - 2 * 3.141592653589793) < 1e-3)
  ?cylSurf a cad:CylindricalSurface ; cad:radius ?radius ; cad:directionNormal ?axis .
  ?axis cad:x ?ax ; cad:y ?ay ; cad:z ?az .
}
ORDER BY DESC(?radius)
LIMIT 1
"""


def _run_sparql_on_local(sparql: str) -> dict:
    g = Graph()
    g.parse("data/ttl/cad-pipeline-test.ttl", format="turtle")
    res = g.query(sparql)
    return json.loads(res.serialize(format="json"))


def test_pipeline_end_to_end() -> None:
    import os
    os.environ.setdefault("GRAPHRAG_LLM_BASE_URL", "http://localhost/v1")
    os.environ.setdefault("GRAPHRAG_LLM_API_KEY", "dummy")
    os.environ.setdefault("GRAPHRAG_LLM_MODEL", "dummy")

    step = _find_step()
    if step is None:
        import pytest
        pytest.skip("no STEP file available")
    # build a KG locally and persist for the mocked GraphDB client
    g = step_to_graph(step, "cad-pipeline-test")
    g.serialize(destination="data/ttl/cad-pipeline-test.ttl", format="turtle")

    orig_chat = llm.chat

    def fake_chat(system, user, temperature=0.0, max_tokens=2048):
        if system.startswith("You are an expert in SPARQL"):
            # NL->SPARQL step: return a fenced golden query (exercise _clean)
            return "```sparql\n" + _GOLDEN_SPARQL + "\n```"
        return "The largest hole has a diameter of 8.5 mm."

    llm.chat = fake_chat
    graphdb_client.run = _run_sparql_on_local
    try:
        out = pipeline.ask("What is the diameter of the largest hole?", "cad-pipeline-test")
    finally:
        llm.chat = orig_chat
        del graphdb_client.run

    # 1. SPARQL was cleaned (no fences / no markdown)
    assert "```" not in out["sparql"]
    assert out["sparql"].strip().startswith("PREFIX cad:")
    # 2. results returned rows
    assert out["results"]["results"]["bindings"], "expected non-empty SPARQL results"
    # 3. answer produced
    assert "8.5" in out["answer"]
    assert out["error"] is None


if __name__ == "__main__":
    test_pipeline_end_to_end()
    print("pipeline mock test OK")
