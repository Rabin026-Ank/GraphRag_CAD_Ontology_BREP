# Paper Notes — source text & extracted facts

**Title:** Ontology-Based CAD Analysis with LLMs: Natural Language Querying of Boundary
Representations
**Authors:** Dominik Mittel, Alexander Perzylo — fortiss (Research Institute of the Free
State of Bavaria), Munich, Germany. `{mittel, perzylo}@fortiss.org`
**Venue/host:** mediaTUM doc 1792874 (2025). Funded by the Bavarian Ministry of Economic
Affairs, Regional Development and Energy.
**Index terms:** CAD Querying, GraphRAG, Ontology, LLM.

> The mediaTUM PDF host is behind an Anubis anti-bot wall (JS proof-of-work), so the PDF
> cannot be fetched programmatically. The abstract + method + evaluation text below was
> provided directly and is the authoritative source for this replication.

## Extracted facts

- **Problem:** BREP CAD models (STEP, ISO 10303-21) hold precise geometry/topology but
  require expert tools to interrogate; no semantic/NL access.
- **Approach:** GraphRAG. Convert STEP → OWL following the **OntoBREP** ontology [ref 5],
  capturing full BREP geometry + topology. Store in a **knowledge graph** (GraphDB). An
  **LLM translates NL questions → SPARQL**; a second LLM step turns SPARQL results → NL
  answers. Explainable, deterministic, geometry-aware — contrasted with vector-embedding
  RAG which loses explicit structure/semantics.
- **Why not vector RAG:** embeddings lose explicit structure, semantics, and precise
  geometric relations (adjacency, containment). Explicit queryable KG preferred for
  deterministic, explainable, geometry-aware reasoning.
- **Higher-level concepts** (holes, shafts, tips) are NOT in OntoBREP; they are described
  in the prompt so the LLM can compose queries. Example: cylindrical hole = cylindrical
  surface + `hasForwardOrientation`; depth from v-bounds; full 360° from u-bounds;
  orientation from `directionNormal` (≡ `directionZ`). Through/beveled/mounting holes
  add a conical countersink.
- **Query hints:** `LIMIT 500` general; `ORDER BY … LIMIT 1` for extremes; math via
  `ofn:` prefix (GraphDB). Balance flexibility vs precision; strict adherence to entity
  descriptions. LLM emits intermediate thoughts/assumptions/summaries before the query
  (these map to tabs in the OntoBREP viewer).
- **Answer generation:** run SPARQL at the endpoint; on empty result an interactive
  system *could* refine (not done in the eval). LLM instructed to (1) rephrase question,
  (2) state thoughts, (3) create the answer. Visual feedback via OntoBREP Viewer
  highlighting matched entities.

## Evaluation (QueryCAD benchmark [ref 8], 111 questions)

LLMs tested: GPT-4o (2024-08-06, 2024-11-20), o3 (2025-04-16), o3-mini (2025-04-16),
and a **top proprietary LLM (2025-05-14; exact identity in the original paper)**. Queries generated via provider batch APIs, no iterative
refinement.

**Table I (Correct / Incorrect, and error buckets):**

| Metric        | QueryCAD GPT-4o | Ours GPT-4o(240806) | Ours GPT-4o(241120) | Ours o3 | Ours o3-mini | Ours TopLLM |
|---------------|-----------------|---------------------|---------------------|---------|--------------|-------------|
| Correct       | 44              | 40                  | 40                  | 48      | 43           | **62**      |
| Incorrect     | 67              | 71                  | 71                  | 63      | 68           | 49          |
| Syntax        | 0               | 0                   | 3                   | 4       | 2            | 0           |
| Reasoning     | 1               | 17                  | 15                  | 12      | 13           | 11          |
| Masks         | 52              | 34                  | 33                  | 27      | 33           | 18          |
| CAD-Interface | 14              | 20                  | 20                  | 20      | 20           | 20          |
| p-value       | —               | 0.58                | 0.59                | 0.89    | 0.02*        | 0.02*       |
| Odds Ratio    | —               | 0.86                | 1.16                | 0.96    | —            | **1.93**    |

*p < 0.05. **Only the top proprietary LLM was a statistically significant improvement over the
QueryCAD GPT-4o baseline** (OR 1.93, p 0.02, ≈93% higher odds of a correct answer;
62/111 correct).

**Error categories:**
- **Syntax** — query has syntax errors.
- **Reasoning** — executes & returns a result but semantically incorrect.
- **Masks** — query yields NO results (wrong entity selected; analog of QueryCAD's
  visual segmentation masks defining entities of interest).
- **CAD-Interface** — model unsuitable: missing analytic surface representations or
  surface-only (non-solid) models. Affects all LLMs equally (~20/111).

Findings: syntax errors negligible; most errors are reasoning / incorrect part ID.
Avoiding surface-only models would improve results.

## Discussion / future work
- OntoBREP alone can't auto-identify semantic parts (holes/shafts/tips); NL must be
  mapped to BREP structure; LLM handles synonym flexibility.
- Through-holes: single stored normal but viewable from both sides → direction must be
  specified; "visible from the left" shaft queries need bounding-box / property
  comparison, possibly visual raycasting from the GUI view.
- **Enhance KG by precomputing higher-level concepts** (holes/cutouts) via SPARQL INSERT;
  materialize inferred radius/surface-type/orientation. ← highest-value extension.
- Integrate visual/structural analysis (segmentation) for part ID and view-based queries.
- Link CAD data to further automation ontologies (processes, factory layouts).

## Conclusion
Semantically enriched BREP + LLM-based SPARQL generation = promising foundation for
intuitive, automated interaction with geometric models. The top proprietary LLM was best for SPARQL
generation among tested LLMs.

## Key references cited
- [5] OntoBREP ontology (Perzylo et al.). GitHub: https://github.com/OntoBREP/ontobrep
- [8] QueryCAD benchmark. GitHub: https://github.com/claudius-kienle/querycad ·
  arXiv 2409.08704
