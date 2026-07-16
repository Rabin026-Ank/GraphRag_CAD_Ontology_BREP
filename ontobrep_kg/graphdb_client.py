"""Phase 0/2 — GraphDB REST client: load named graphs, run SPARQL SELECT/UPDATE.

Endpoints (see config.py):
    SPARQL query : GET/POST  {graphdb_url}/repositories/{repo}
    statements   : POST      {graphdb_url}/repositories/{repo}/statements
Named-graph load uses the RDF4J statements endpoint with a ?context=<iri> parameter.
"""
from __future__ import annotations

from typing import Any

import requests

from .config import CFG


def load_ttl(ttl_path: str, graph_iri: str) -> None:
    """Load a Turtle file into a specific named graph.

    Uses the SPARQL Graph Store Protocol endpoint (NOT /statements), which takes a
    bare (URL-encoded) graph IRI via `?graph=` and appends the file's triples to that
    named graph. The /statements endpoint's `?context=` wants N-Triples `<...>` brackets
    and is the wrong tool for bulk file loading.
    """
    url = f"{CFG.graphdb_url}/repositories/{CFG.graphdb_repo}/rdf-graphs/service"
    with open(ttl_path, "rb") as fh:
        r = requests.post(
            url,
            params={"graph": graph_iri},
            headers={"Content-Type": "text/turtle"},
            data=fh,
            timeout=120,
        )
    r.raise_for_status()


def run(sparql: str) -> dict[str, Any]:
    """Run a SPARQL SELECT/ASK, return SPARQL-JSON results (dict)."""
    r = requests.post(
        CFG.graphdb_sparql_url,
        data={"query": sparql},
        headers={"Accept": "application/sparql-results+json"},
        timeout=60,
    )
    r.raise_for_status()
    return r.json()


def update(sparql_update: str) -> None:
    """Run a SPARQL UPDATE (INSERT/DELETE) — used by Phase 4 materialization."""
    r = requests.post(
        CFG.graphdb_statements_url,
        data={"update": sparql_update},
        timeout=120,
    )
    r.raise_for_status()
