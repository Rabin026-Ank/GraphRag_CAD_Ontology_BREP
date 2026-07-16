"""Environment-driven configuration. No secrets in source — everything via .env.

Usage:
    from ontobrep_kg.config import CFG
    CFG.llm_model, CFG.graphdb_sparql_url, CFG.model_graph_iri("cad-00000182")
"""
from __future__ import annotations

import os
from dataclasses import dataclass

try:
    from dotenv import load_dotenv
    load_dotenv()  # loads .env from cwd / project root
except ImportError:  # dotenv optional if vars are already exported
    pass

ONTOBREP_NS = "http://www.fortiss.org/ont/ontobrep#"
MODEL_GRAPH_BASE = "http://www.fortiss.org/ont/ontobrep"  # + /<model-id>
IMPLICIT_GRAPH = "http://www.ontotext.com/implicit"


def _require(name: str) -> str:
    val = os.environ.get(name)
    if not val:
        raise RuntimeError(f"Missing required environment variable: {name} (see .env.example)")
    return val


@dataclass(frozen=True)
class Config:
    # LLM (OpenAI-compatible)
    llm_base_url: str
    llm_api_key: str
    llm_model: str
    # GraphDB
    graphdb_url: str
    graphdb_repo: str

    @property
    def graphdb_sparql_url(self) -> str:
        return f"{self.graphdb_url}/repositories/{self.graphdb_repo}"

    @property
    def graphdb_statements_url(self) -> str:
        return f"{self.graphdb_url}/repositories/{self.graphdb_repo}/statements"

    @staticmethod
    def model_graph_iri(model_id: str) -> str:
        return f"{MODEL_GRAPH_BASE}/{model_id}"


def load_config() -> "Config":
    return Config(
        llm_base_url=_require("GRAPHRAG_LLM_BASE_URL"),
        llm_api_key=_require("GRAPHRAG_LLM_API_KEY"),
        llm_model=_require("GRAPHRAG_LLM_MODEL"),
        graphdb_url=os.environ.get("GRAPHRAG_GRAPHDB_URL", "http://localhost:7200"),
        graphdb_repo=os.environ.get("GRAPHRAG_GRAPHDB_REPO", "graphrag"),
    )


# Lazily constructed singleton is fine for a small app; import CFG where needed.
# A proxy so that merely importing config (e.g. for ONTOBREP_NS) does not force
# the LLM/GraphDB env vars to be present until a property is actually accessed.
class _ConfigProxy:
    _instance: "Config | None" = None

    def _resolve(self) -> "Config":
        if _ConfigProxy._instance is None:
            _ConfigProxy._instance = load_config()
        return _ConfigProxy._instance

    def __getattr__(self, name: str):
        return getattr(self._resolve(), name)


CFG = _ConfigProxy()
