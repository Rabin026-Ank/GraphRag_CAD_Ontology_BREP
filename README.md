# GraphRag_CAD_Ontology_BREP

Natural-language querying of CAD **boundary representations (BREP)** using an
**ontology-based knowledge graph** and an **LLM** that translates questions into SPARQL.

Given a STEP file, the system converts its geometry and topology into an OntoBREP RDF
knowledge graph (stored in GraphDB), then lets you ask questions in plain English
("What is the diameter of the largest hole?"). An LLM turns the question into a SPARQL
query, GraphDB returns the exact facts, and the LLM phrases the answer.

This is an independent re-implementation of the concept described in *Ontology-Based CAD
Analysis with LLMs: Natural Language Querying of Boundary Representations* (Mittel &
Perzylo, fortiss, 2025). The paper is not open source; only the public **OntoBREP**
vocabulary and the public **QueryCAD** benchmark are reused.

---

## How it works

```
STEP file ──▶ [Python + OpenCascade] ──▶ RDF facts (.ttl) ──▶ GraphDB (named graph)
                                                                    ▲ SPARQL
   question (English) ──▶ [LLM: NL → SPARQL] ──────────────────────┘
                                                    │ result JSON
                                                    ▼
                                   [LLM: result → natural-language answer]
```

- **Knowledge graph, not text search** — CAD needs exact numbers and relationships;
  triples in GraphDB preserve them, so answers are exact and explainable.
- **LLM only translates + phrases** — it writes the SPARQL and reads back the result;
  the numbers come from the graph, never from the model's memory.

---

## Tech stack

| Part | Tool |
|---|---|
| CAD geometry parsing | OpenCascade via `pythonocc` (`OCC.Core`) |
| RDF / knowledge graph | `rdflib` + **GraphDB Free** (triplestore) |
| Ontology (vocabulary) | **OntoBREP** — https://github.com/OntoBREP/ontobrep |
| LLM | any OpenAI-compatible endpoint (e.g. a local vLLM server) |
| Benchmark (optional) | **QueryCAD** — https://github.com/claudius-kienle/querycad |

---

## Setup (once)

### 1. Python environment
```bash
conda create -n graphrag -c conda-forge python=3.11 pythonocc-core -y
conda activate graphrag
pip install -r requirements.txt
python -c "from OCC.Core.STEPControl import STEPControl_Reader; import rdflib, openai; print('deps OK')"
```

### 2. Start GraphDB (Docker)
```bash
docker compose up -d          # UI at http://localhost:7200
```
Create a repository named `graphrag` (UI: Setup → Repositories → Create) with the
**RDFS-Plus (Optimized)** ruleset.

### 3. Load the OntoBREP ontology (once)
Clone https://github.com/OntoBREP/ontobrep and put its OWL/TTL schema at
`data/ontology/ontobrep.ttl`, then:
```bash
curl -X POST "http://localhost:7200/repositories/graphrag/rdf-graphs/service?default" \
     -H "Content-Type: text/turtle" --data-binary @data/ontology/ontobrep.ttl
```

### 4. Configure the LLM + GraphDB (secrets in `.env`, never committed)
```bash
cp .env.example .env
```
Edit `.env`:
```
GRAPHRAG_LLM_BASE_URL=https://your-llm-host/v1
GRAPHRAG_LLM_API_KEY=your-key
GRAPHRAG_LLM_MODEL=your-model-id
GRAPHRAG_GRAPHDB_URL=http://localhost:7200
GRAPHRAG_GRAPHDB_REPO=graphrag
```
Quick check:
```bash
python -c "from ontobrep_kg import llm; print(llm.chat('You are a bot.', 'say OK'))"
```

---

## Run — per CAD file (two commands)

### Step 1 — Ingest a STEP file
Converts geometry → facts, loads them into a named graph, and precomputes hole/shaft
entities:
```bash
python -m scripts.ingest data/models/yourpart.step --model-id yourpart --materialize
```

### Step 2 — Ask a question
```bash
python -m ontobrep_kg.pipeline \
    "What is the diameter of the largest hole on top of yourpart?" \
    --model-id yourpart
```
Prints the generated SPARQL and the natural-language answer.

More examples:
```bash
python -m ontobrep_kg.pipeline "How many holes does yourpart have?"      --model-id yourpart
python -m ontobrep_kg.pipeline "What is the diameter of the shaft?"      --model-id yourpart
```

### Verify data landed in GraphDB
```bash
curl -s http://localhost:7200/repositories/graphrag \
  -H "Accept: application/sparql-results+json" \
  --data-urlencode 'query=SELECT (COUNT(*) AS ?n) FROM <http://www.fortiss.org/ont/ontobrep/yourpart> WHERE {?s ?p ?o}'
```

---

## Project layout

```
ontobrep_kg/
  step_to_owl.py         STEP -> RDF facts (OpenCascade + rdflib)
  graphdb_client.py      load facts / run SPARQL against GraphDB
  concepts_materialize.py  add explicit cad:Hole / cad:Shaft facts (SPARQL INSERT)
  nl_to_sparql.py        English -> SPARQL (LLM)
  answer_gen.py          SPARQL result -> English answer (LLM)
  pipeline.py            ask(question, model_id) -> answer
  llm.py                 OpenAI-compatible client
  config.py              env-driven settings
scripts/ingest.py        one-command: convert -> load -> materialize
prompts/                 LLM prompt templates + few-shot examples
references/              ontology reference, prompt notes, paper notes
eval/                    optional QueryCAD benchmark harness
data/                    STEP files + generated .ttl (gitignored)
```

See `PLAN.md` for the full design and `RUN.md` for the detailed run/troubleshooting guide.

---

## Notes
- Query accuracy depends on the LLM: a larger model produces more correct SPARQL. The
  endpoint is OpenAI-compatible, so the model is swappable via `.env` only.
- Known conversion limitations (split cylinders, top/bottom disambiguation, edge
  adjacency) are documented in `references/ontobrep_reference.md` §5.
- No credentials are stored in the repo; all secrets live in `.env` (gitignored).
