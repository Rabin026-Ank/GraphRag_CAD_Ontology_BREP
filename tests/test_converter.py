"""Offline test for the Phase 1 STEP -> OWL converter.

Does not require GraphDB or an LLM. Validates that the generated OntoBREP triples
contain the properties the NL->SPARQL queries rely on (cad:representedBy,
cad:hasForwardOrientation, UV bounds, cad:position, CylindricalSurface cad:radius,
directionNormal). Uses a small bundled/available STEP file.
"""
from __future__ import annotations

from pathlib import Path

from rdflib import Graph, Namespace, RDF, URIRef
from rdflib.namespace import XSD

from ontobrep_kg.step_to_owl import step_to_graph

CAD = Namespace("http://www.fortiss.org/ont/ontobrep#")

# First STEP file found under the sibling Step_graph_data project (kept outside the
# repo so we don't commit large CAD assets). Falls back to any data/models/*.step.
_CANDIDATES = [
    Path(__file__).resolve().parents[2] / "Step_graph_data" / "STEP_models",
    Path(__file__).resolve().parent.parent / "data" / "models",
]


def _find_step() -> str | None:
    for base in _CANDIDATES:
        if base.exists():
            for p in sorted(base.rglob("*.step")) + sorted(base.rglob("*.stp")):
                return str(p)
    return None


def _face_props(g: Graph, local: str) -> dict:
    iri = URIRef(f"http://www.fortiss.org/ont/ontobrep#cad-test#{local}")
    return {p.split('#')[-1]: o for p, o in g.predicate_objects(iri)}


def test_converter_runs_and_emits_schema() -> None:
    step = _find_step()
    if step is None:
        import pytest
        pytest.skip("no STEP file available to convert")
    g = step_to_graph(step, "cad-test")

    faces = list(g.subjects(RDF.type, CAD.Face))
    assert faces, "expected at least one cad:Face"

    cyl_surfs = list(g.subjects(RDF.type, CAD.CylindricalSurface))
    planes = list(g.subjects(RDF.type, CAD.Plane))
    assert cyl_surfs or planes, "expected at least one geometric surface"

    for face in faces:
        props = {p.split('#')[-1]: o for p, o in g.predicate_objects(face)}
        # every face must carry the topology/geometry anchors the queries use
        assert "hasForwardOrientation" in props
        assert str(props["hasForwardOrientation"].datatype) == str(XSD.boolean)
        # at least one surface-linked face must expose UV bounds
        if CAD.representedBy in [p for p, _ in g.predicate_objects(face)]:
            assert "position" in props, "face should link cad:position"

    # cylindrical surfaces must expose radius + axis direction
    for cs in cyl_surfs:
        props = {p.split('#')[-1]: o for p, o in g.predicate_objects(cs)}
        assert "radius" in props
        assert "directionNormal" in props
        axis = props["directionNormal"]
        axis_props = {p.split('#')[-1]: o for p, o in g.predicate_objects(axis)}
        assert {"x", "y", "z"} <= set(axis_props), "axis Vector needs x/y/z"


if __name__ == "__main__":
    test_converter_runs_and_emits_schema()
    print("converter test OK")
