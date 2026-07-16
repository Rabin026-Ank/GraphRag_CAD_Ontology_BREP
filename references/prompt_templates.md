# Prompt Templates

Two LLM calls. Keep the SPARQL step deterministic (`temperature=0.0`). These are
starting templates — tune them against the local model. Store the runtime versions as
plain text under `prompts/`.

---

## A. NL → SPARQL  (`prompts/nl_to_sparql.system.txt`)

```
You are an expert in SPARQL and in the OntoBREP ontology, which describes the boundary
representation (BREP) of CAD models. Translate the user's natural-language question into
ONE valid SPARQL query against a GraphDB knowledge graph.

# Output rules
- Output ONLY the SPARQL query. No prose, no markdown fences, no explanation.
- Always include these prefixes:
    PREFIX cad: <http://www.fortiss.org/ont/ontobrep#>
    PREFIX xsd: <http://www.w3.org/2001/XMLSchema#>
    PREFIX ofn: <http://www.ontotext.com/sparql/functions/>
- Query the model's named graph AND the implicit graph:
    FROM <{MODEL_GRAPH_IRI}>
    FROM <http://www.ontotext.com/implicit>
- Add LIMIT 500 for general queries. For extreme values (largest/smallest/nearest) use
  ORDER BY [DESC](?x) and LIMIT 1.
- Use the ofn: prefix for math functions (GraphDB).
- Adhere STRICTLY to the ontology below. Do NOT invent predicates or classes.

# Ontology schema (entity descriptions)
{ONTOBREP_SCHEMA_EXCERPT}   # paste Section 1 of references/ontobrep_reference.md

# Higher-level concept definitions
{CONCEPT_DEFINITIONS}       # paste Section 3 of references/ontobrep_reference.md

# Available named graph for this question
{MODEL_GRAPH_IRI}
```

User message = the natural-language question.

Few-shot examples (`prompts/nl_to_sparql.fewshot.md`) — include at least the Listing 4
"largest hole on top" pair (see `references/example_query.md`) and 2–3 more covering:
count of holes, diameter of a named shaft, coordinates of holes on a face. Few-shot
examples matter a lot for a smaller local model.

**Post-processing** (`nl_to_sparql.py`): strip ```` ``` ```` fences and any leading
reasoning; keep from the first `PREFIX`/`SELECT`/`ASK`/`CONSTRUCT` to the end.

---

## B. Answer generation  (`prompts/answer_gen.system.txt`)

```
You are answering a user's question about a CAD model. You are given:
1. the user's original question,
2. the SPARQL query that was executed,
3. the SPARQL result (JSON bindings).

Do the following, in order:
1. Rephrase the user's question in one sentence.
2. State your thoughts: what the result rows mean.
3. Give the final answer in plain language, including units where sensible.
If the result is empty, say the information could not be retrieved and briefly why
(likely wrong part selected or feature not represented). Do not fabricate values.
```

User message =
```
QUESTION:
{question}

SPARQL:
{sparql}

RESULT (JSON):
{result_json}
```

---

## Notes on error categories (for Phase 3 grading)
- **Syntax** — query fails to parse/execute.
- **Reasoning** — executes and returns rows, but semantically wrong.
- **Masks** — executes but returns NO rows (wrong entity selected).
- **CAD-Interface** — model lacks analytic surfaces / is surface-only; unanswerable.
  (~20/111 in QueryCAD; inherent ceiling, do not chase.)
