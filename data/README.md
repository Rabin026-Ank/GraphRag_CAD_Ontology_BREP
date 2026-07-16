# data/

Gitignored (STEP files and generated `.ttl` are large). Layout:

```
data/
├── ontology/          # OntoBREP OWL/TTL schema (from github.com/OntoBREP/ontobrep, owl/)
├── models/            # STEP files, one per CAD model
│   ├── cad-00000182.step
│   └── ...
├── ttl/               # generated KG per model (step_to_owl.py output)
└── graphdb/           # GraphDB docker volume (do not touch)
```

## Where to get CAD models
- **QueryCAD benchmark** (optional, for evaluation): clone
  https://github.com/claudius-kienle/querycad — 18 models (10 from the ABC dataset,
  8 others) + 111 annotated questions. Use its model IDs (e.g. `cad-00000182`) as the
  named-graph suffixes so the reference SPARQL in `references/example_query.md` matches.
- **Your own MEDA CAD**: drop any `.step`/`.stp` here; the converter is model-agnostic.

## Named-graph convention
Each model loads into GraphDB as:
`http://www.fortiss.org/ont/ontobrep/<model-id>`  (e.g. `.../cad-00000182`)
