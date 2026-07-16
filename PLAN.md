# GraphRAG for CAD — Implementation Plan (Handoff Spec)

> **Purpose of this document.** This is a self-contained implementation plan for a
> fresh coding agent (Kilo Code) that has **no access to the conversation that
> produced it**. Everything needed to build the system is here or in the
> `references/` files. Read `PLAN.md` → `SETUP.md` → `references/*` before writing code.

---

## 0. What we are building (one paragraph)

We are replicating the **core ideas** of the paper *"Ontology-Based CAD Analysis with
LLMs: Natural Language Querying of Boundary Representations"* (Mittel & Perzylo,
fortiss, 2025). It is **not a model-training paper** — there is no architecture,
no dataset training, no weights. It is a **GraphRAG system**: convert a CAD STEP
file into an OWL/RDF **Knowledge Graph** (following the *OntoBREP* ontology), load
it into a **triplestore**, and let a **Large Language Model translate natural-language
questions into SPARQL queries** against that KG, then turn the SPARQL results back
into a natural-language answer.

**Our goal (user's stated intent):** *store the BREP data in a KG, and use a local
LLM to communicate with it.* The published benchmark evaluation is **optional** —
it is a way to *measure* quality later, not the deliverable.

---

## 1. The pipeline (target architecture)

```
                          Phase 1                         Phase 0
  STEP file ──▶ [Python: OCP walks BREP topology] ──▶ rdflib Graph (OntoBREP triples)
                                                          │  .ttl  /  SPARQL INSERT
                                                          ▼
                                                   GraphDB (one named graph per model)
                                                          ▲ SPARQL over HTTP :7200
   NL question ──▶ [LLM: NL → SPARQL] ────────────────────┘
                       ▲ prompt =                          │ JSON result bindings
                       │  ontology schema excerpt          ▼
                       │  + entity descriptions      [LLM: result + question + query
                       │  + SPARQL hints (ofn:, LIMIT)      → NL answer]
                       │  + higher-level concept defs
                       │  + few-shot NL→SPARQL examples          Phase 2
```

Two LLM calls per question:
1. **NL → SPARQL** (the hard part; heavy prompt engineering).
2. **SPARQL-result → NL answer** (easy: rephrase question, state thoughts, answer).

No iterative refinement / self-repair in the baseline (matches the paper). It can be
added later as an extension.

---

## 2. Finalized technology decisions (do not re-litigate)

| Concern            | Decision                                                                 | Why |
|--------------------|--------------------------------------------------------------------------|-----|
| Triplestore        | **GraphDB Free** (local, port 7200)                                      | Matches the paper; supports `ofn:` math functions used in the reference SPARQL, named graphs, and an implicit inference graph. |
| STEP → OWL         | **Python** — `pythonocc` (`OCC.Core`) + `rdflib`                         | Reimplement the converter in Python (the paper's `occjava` is Java+native and painful to build). pythonocc is already installed in the `uv_net` conda env. |
| Ontology           | Reuse **OntoBREP** OWL schema — https://github.com/OntoBREP/ontobrep     | Don't invent a schema; emit triples matching `cad:` classes. |
| LLM                | **Local model via OpenAI-compatible endpoint** (user's vLLM server)      | User runs a local Qwen model behind an OpenAI-compatible API. Use the `openai` Python SDK with a custom `base_url`. Model + endpoint are swappable via env vars. |
| Benchmark          | **QueryCAD** — https://github.com/claudius-kienle/querycad (optional)    | 111 questions / 18 CAD models. Only needed if we want to *measure* accuracy. |

### 2.1 LLM configuration (IMPORTANT — do not hardcode secrets)

The model is served on an OpenAI-compatible endpoint. **Read all of these from
environment variables — never commit them:**

```bash
export GRAPHRAG_LLM_BASE_URL="https://<your-vllm-host>/v1"
export GRAPHRAG_LLM_API_KEY="<your-key>"      # rotate the one that was shared in chat!
export GRAPHRAG_LLM_MODEL="<model-id served by your vLLM, e.g. a local Qwen>"
```

```python
from openai import OpenAI
import os
client = OpenAI(base_url=os.environ["GRAPHRAG_LLM_BASE_URL"],
                api_key=os.environ["GRAPHRAG_LLM_API_KEY"])
resp = client.chat.completions.create(
    model=os.environ["GRAPHRAG_LLM_MODEL"],
    messages=[...],
    temperature=0.0,          # deterministic SPARQL generation
)
```

> **SECURITY NOTE.** During planning, a live API key and a Penpot token were pasted
> into the chat. Those must be **rotated/revoked** — treat them as compromised. This
> repo must contain **zero** credentials; use env vars and add a `.env` to
> `.gitignore`.

### 2.2 Realistic expectation about the local model

The paper's headline result (**62/111 correct**) required a **top-tier proprietary LLM**; even
GPT-4o only reached ~40/111. NL→**SPARQL** generation is genuinely hard. A smaller
local model will produce **more syntax and reasoning errors**. This is acceptable for
the goal (a working KG + NL interface), but it means:

- Lean heavily on **few-shot NL→SPARQL examples** and the **concept descriptions** in
  the prompt (see `references/prompt_templates.md`).
- Keep temperature at **0.0** for the SPARQL step.
- Because the client is OpenAI-compatible, a **frontier model can be swapped in** by
  changing 3 env vars — do this only for a fair accuracy comparison, if desired.
- **Phase 4 (materialize higher-level concepts via `SPARQL INSERT`)** is especially
  valuable here: it moves reasoning burden out of the LLM and into precomputed triples.

---

## 3. Environment

Full commands are in `SETUP.md`. Summary:

- **Conda env `graphrag`** (create fresh; python 3.10/3.11): install `pythonocc-core`
  from conda-forge, then pip `rdflib SPARQLWrapper openai requests python-dotenv
  statsmodels pandas`. (Fallback: `uv_net` env already has `OCC.Core` if conda-forge
  install fights you — but it is py3.9; prefer a clean env.)
- **GraphDB Free** running locally (Docker recommended), REST + SPARQL at
  `http://localhost:7200`.

---

## 4. Repository layout (create exactly this)

```
/home/braj-server/MEDA/Graphrag/
├── PLAN.md                     # this file
├── SETUP.md                    # env + GraphDB bring-up
├── .gitignore                  # must ignore .env, data/, *.ttl (large)
├── .env.example                # names of required env vars, NO values
├── docker-compose.yml          # GraphDB Free service
├── pyproject.toml              # or requirements.txt
├── references/
│   ├── ontobrep_reference.md   # the cad: schema + higher-level concept defs
│   ├── prompt_templates.md     # NL→SPARQL and answer-gen prompts
│   └── example_query.md        # the "largest hole on top" worked example (Listing 4)
├── ontobrep_kg/                # the Python package
│   ├── __init__.py
│   ├── config.py               # loads env vars, endpoints, model id
│   ├── step_to_owl.py          # Phase 1: STEP -> rdflib Graph -> .ttl
│   ├── graphdb_client.py       # Phase 0/2: load graph, run SPARQL over HTTP
│   ├── llm.py                  # OpenAI-compatible client wrapper
│   ├── nl_to_sparql.py         # Phase 2: prompt build + NL->SPARQL
│   ├── answer_gen.py           # Phase 2: SPARQL result -> NL answer
│   ├── pipeline.py             # ties it together: ask(question, model_graph)->answer
│   └── concepts_materialize.py # Phase 4 (optional): SPARQL INSERT for holes/cutouts
├── prompts/                    # prompt text files loaded at runtime
│   ├── nl_to_sparql.system.txt
│   ├── nl_to_sparql.fewshot.md
│   └── answer_gen.system.txt
├── data/                       # STEP files + generated .ttl (gitignored)
│   └── README.md               # where to get models
├── eval/                       # Phase 3 (optional)
│   ├── run_benchmark.py
│   ├── grade.py                # result-based grading (adapted from QueryCAD)
│   └── logistic_regression.py  # reproduce the OR / p-value analysis
└── tests/
    └── test_smoke.py           # one STEP -> KG -> one SPARQL -> answer
```

---

## 5. Phased task list

### Phase 0 — Assets & GraphDB up  *(target: ½ day)*
- [ ] `git clone https://github.com/OntoBREP/ontobrep` somewhere; copy the OWL schema
      from its `owl/` folder into `data/ontology/`. Note the namespace
      `http://www.fortiss.org/ont/ontobrep#` (prefix `cad:`).
- [ ] Bring up GraphDB Free via `docker-compose.yml`. Create a repository (e.g.
      `graphrag`) with **RDFS-Plus (Optimized)** or OWL-Horst inference enabled so the
      implicit graph `http://www.ontotext.com/implicit` is populated.
- [ ] Load the OntoBREP ontology into the repo. Confirm a hand-written SPARQL query
      returns rows via the REST endpoint (`graphdb_client.py`).
- **Done when:** `graphdb_client.run("SELECT * WHERE {?s ?p ?o} LIMIT 5")` returns JSON.

### Phase 1 — STEP → OWL converter in Python  *(the main build)*
- [ ] `step_to_owl.py`: read STEP with `OCC.Core.STEPControl.STEPControl_Reader`.
- [ ] Walk topology with `OCC.Core.TopExp.TopExp_Explorer` (Solid→Shell→Face→Wire→
      Edge→Vertex); cast with `OCC.Core.TopoDS`. Assign stable IRIs per entity.
- [ ] For each **Face**: get surface via `BRepAdaptor_Surface`; branch on
      `GetType()` (`GeomAbs_Plane`, `GeomAbs_Cylinder`, …). Extract:
      - Plane: `Plane()` → position + X/Y/normal directions + offset.
      - Cylinder: `Cylinder()` → `Radius()`, axis location + direction (`directionNormal`).
      - UV bounds via `BRepTools.UVBounds` → `umin/umax/vmin/vmax`.
      - Area via `BRepGProp` (`SurfaceProperties`).
      - `hasForwardOrientation`: `face.Orientation() == TopAbs_FORWARD`.
- [ ] Emit triples into an `rdflib.Graph` matching the OntoBREP schema (see
      `references/ontobrep_reference.md` for exact predicates). Serialize to
      `data/<model>.ttl` (Turtle).
- [ ] Load the `.ttl` into GraphDB as a **named graph**, e.g.
      `http://www.fortiss.org/ont/ontobrep/cad-00000182` (one graph per model).
- **Done when:** one benchmark model round-trips STEP → .ttl → GraphDB, and a manual
  SPARQL query for its cylindrical faces returns correct radii.

### Phase 2 — KG ↔ LLM loop  *(the core deliverable)*
- [ ] `llm.py`: OpenAI-compatible wrapper (§2.1), temperature 0.0.
- [ ] `nl_to_sparql.py`: build the prompt from `prompts/nl_to_sparql.system.txt` +
      few-shot file + the ontology schema excerpt + higher-level concept definitions +
      SPARQL hints (`LIMIT 500` default; `ORDER BY … LIMIT 1` for extremes; `ofn:` for
      math; correct `FROM <named graph>` and `FROM <implicit>`). Return the SPARQL
      string (strip markdown fences / any chain-of-thought).
- [ ] `answer_gen.py`: given (question, SPARQL, result JSON) → instruct the model to
      (1) rephrase the question, (2) state thoughts, (3) produce the answer.
- [ ] `pipeline.py`: `ask(question, model_graph_iri) -> {sparql, results, answer}`.
- **Done when:** the worked example in `references/example_query.md` (*"diameter of the
  largest hole on top of cad-00000182"*) runs end-to-end and returns the right diameter.

### Phase 3 — Measure it (OPTIONAL)
- [ ] Pull QueryCAD's 18 models + 111 questions (`data/README.md`). Convert all models
      (Phase 1) into named graphs.
- [ ] `eval/run_benchmark.py`: loop all 111 questions (no refinement), log
      sparql/result/answer.
- [ ] `eval/grade.py`: **result-based** grading (QueryCAD's original grader is
      segmentation-mask based; adapt to compare returned values to gold answers).
      Bucket failures: **Syntax / Reasoning / Masks(=no-result) / CAD-Interface**.
- [ ] `eval/logistic_regression.py`: reproduce the paper's analysis (Odds Ratio,
      p-value) comparing configs. `statsmodels` in the `graphrag` env.
- **Note:** ~20/111 QueryCAD questions fail structurally on surface-only models with no
  analytic surfaces ("CAD-Interface" category) — this is an inherent ceiling even in the
  paper. Do not chase them.

### Phase 4 — Materialize higher-level concepts (OPTIONAL, high value for a small model)
- [ ] `concepts_materialize.py`: run `SPARQL INSERT` queries that create explicit
      `cad:Hole` (and cutouts) entities with precomputed `radius`, `depth`, `orientation`
      so the LLM queries a simple materialized concept instead of reconstructing it from
      primitives each time. This is the paper's #1 "future work" item and directly
      reduces the local model's reasoning error rate.

---

## 6. Key gotchas (learned during planning)

1. **`ofn:` math functions are GraphDB-specific.** They appear in the paper's reference
   SPARQL (`ofn:` prefix, GraphDB). If you ever switch triplestore, you must rewrite
   them (Jena uses `afn:`/`math:`). Staying on GraphDB avoids this.
2. **occjava is not used** — we reimplement STEP→OWL in Python. Only emit the subset of
   OntoBREP classes the queries actually touch (Face, Plane, CylindricalSurface,
   Position, Vector, and their decimal/boolean properties). Don't try to emit the whole
   ontology.
3. **`cad:directionNormal` ≡ `cad:directionZ`** — the paper treats the cylinder normal
   and Z direction as equivalent for hole orientation. Encode/handle this.
4. **Through-holes have one normal but two viewing sides** — "visible from the left"
   type questions need direction reasoning the ontology doesn't fully capture; expect
   some of these to fail (paper does too).
5. **Named graphs + implicit graph** — queries must include both
   `FROM <…/cad-XXXX>` and `FROM <http://www.ontotext.com/implicit>` (see Listing 4).
6. **Strip LLM output** — local models often wrap SPARQL in ```` ```sparql ```` fences or
   emit reasoning; `nl_to_sparql.py` must extract just the query.
7. **The mediaTUM PDF host is behind an Anubis bot-wall** — the paper text is captured in
   `references/` so no re-fetch is needed.

---

## 7. Definition of done

- **Minimum (user's goal):** any STEP file → OWL KG in GraphDB, and
  `pipeline.ask("What is the diameter of the largest hole on top of cad-00000182?")`
  returns a correct natural-language answer using the local LLM. (Phases 0–2.)
- **Full replication (optional):** Phase 3 produces a per-model accuracy number and the
  logistic-regression comparison table, mirroring the paper's Table I methodology.

---

## 8. References (external)

- Paper: *Ontology-Based CAD Analysis with LLMs* — Mittel & Perzylo, fortiss, 2025
  (mediaTUM doc 1792874). Full text pasted into `references/paper_notes.md`.
- OntoBREP ontology + `occjava` + examples: https://github.com/OntoBREP/ontobrep
- OntoBREP namespace: `http://www.fortiss.org/ont/ontobrep#`
- QueryCAD benchmark: https://github.com/claudius-kienle/querycad ·
  arXiv 2409.08704 (111 Q / 18 models, 10 from the ABC dataset)
- GraphDB Free: https://graphdb.ontotext.com/
- pythonocc-core (OCC.Core): https://github.com/tpaviot/pythonocc-core
