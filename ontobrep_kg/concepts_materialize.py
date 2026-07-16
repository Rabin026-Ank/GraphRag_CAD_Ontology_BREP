"""Phase 4 (OPTIONAL, high value for a small local model) — materialize higher-level
concepts into the KG via SPARQL INSERT so the LLM queries simple explicit concepts
instead of reconstructing them from primitives each time.

The paper's #1 future-work item. We create explicit cad:Hole (and cad:Shaft) individuals
with precomputed radius / depth / orientation from the cylindrical-surface pattern. After
materialization the LLM can ask e.g. "diameter of the largest hole" with a trivial query:

    SELECT ?hole ((2 * ?r) as ?diameter) WHERE {
      GRAPH <g> { ?hole a cad:Hole ; cad:radius ?r }
    } ORDER BY DESC(?r) LIMIT 1

Run once per named graph after loading the .ttl. Requires GraphDB (the UPDATE endpoint).
"""
from __future__ import annotations

from . import graphdb_client
from .config import CFG

# A "real" round hole = inward-facing full 360-deg cylinder (material removed).
_HOLE_INSERT = """
PREFIX cad: <http://www.fortiss.org/ont/ontobrep#>
PREFIX xsd: <http://www.w3.org/2001/XMLSchema#>
INSERT {{
  GRAPH <{g}> {{
    ?face a cad:Hole ;
          cad:radius ?radius ;
          cad:diameter ?diameter ;
          cad:depth ?depth ;
          cad:directionNormal ?axis ;
          cad:representedBy ?surf .
  }}
}}
WHERE {{
  GRAPH <{g}> {{
    ?face a cad:Face ;
          cad:hasForwardOrientation "false"^^xsd:boolean ;
          cad:representedBy ?surf ;
          cad:umax ?umax ; cad:umin ?umin ;
          cad:vmax ?vmax ; cad:vmin ?vmin .
    ?surf a cad:CylindricalSurface ;
          cad:radius ?radius ; cad:directionNormal ?axis .
    BIND ((2 * ?radius) AS ?diameter)
    BIND ((?vmax - ?vmin) AS ?depth)
    FILTER (ABS(?umax - ?umin - 2 * 3.141592653589793) < 1e-3)
  }}
}}
"""

# A "shaft" = outward-facing full 360-deg cylinder (solid material).
_SHAFT_INSERT = """
PREFIX cad: <http://www.fortiss.org/ont/ontobrep#>
PREFIX xsd: <http://www.w3.org/2001/XMLSchema#>
INSERT {{
  GRAPH <{g}> {{
    ?face a cad:Shaft ;
          cad:radius ?radius ;
          cad:diameter ?diameter ;
          cad:depth ?depth ;
          cad:directionNormal ?axis ;
          cad:representedBy ?surf .
  }}
}}
WHERE {{
  GRAPH <{g}> {{
    ?face a cad:Face ;
          cad:hasForwardOrientation "true"^^xsd:boolean ;
          cad:representedBy ?surf ;
          cad:umax ?umax ; cad:umin ?umin ;
          cad:vmax ?vmax ; cad:vmin ?vmin .
    ?surf a cad:CylindricalSurface ;
          cad:radius ?radius ; cad:directionNormal ?axis .
    BIND ((2 * ?radius) AS ?diameter)
    BIND ((?vmax - ?vmin) AS ?depth)
    FILTER (ABS(?umax - ?umin - 2 * 3.141592653589793) < 1e-3)
  }}
}}
"""


def materialize_holes(model_id: str) -> None:
    """Create explicit cad:Hole (and cad:Shaft) entities in the model's named graph."""
    graph = CFG.model_graph_iri(model_id)
    graphdb_client.update(_HOLE_INSERT.format(g=graph))
    graphdb_client.update(_SHAFT_INSERT.format(g=graph))


if __name__ == "__main__":  # pragma: no cover
    import argparse

    ap = argparse.ArgumentParser()
    ap.add_argument("--model-id", required=True)
    args = ap.parse_args()
    materialize_holes(args.model_id)
    print(f"materialized holes/shafts for {args.model_id}")
