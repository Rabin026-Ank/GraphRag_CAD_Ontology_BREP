# SETUP — Environment & GraphDB

## 1. Python environment

pythonocc (`OCC.Core`) is easiest via conda-forge. The `uv_net` conda env on this
machine already has `OCC.Core` (py3.9) as a fallback, but prefer a clean env:

```bash
conda create -n graphrag -c conda-forge python=3.11 pythonocc-core=7.* -y
conda activate graphrag
pip install rdflib SPARQLWrapper openai requests python-dotenv statsmodels pandas
# sanity
python -c "from OCC.Core.STEPControl import STEPControl_Reader; import rdflib, openai; print('deps OK')"
```

If conda-forge `pythonocc-core` resolution fights you, fall back to the existing env:
```bash
conda activate uv_net           # has OCC.Core (py3.9)
pip install rdflib SPARQLWrapper openai requests python-dotenv statsmodels pandas
```

## 2. Environment variables (secrets — never commit)

Create `.env` (gitignored) from `.env.example`:

```bash
# LLM (OpenAI-compatible endpoint, e.g. a local vLLM server)
GRAPHRAG_LLM_BASE_URL=https://<your-vllm-host>/v1
GRAPHRAG_LLM_API_KEY=<rotate the key that leaked in chat>
GRAPHRAG_LLM_MODEL=<model id served by your vLLM>

# GraphDB
GRAPHRAG_GRAPHDB_URL=http://localhost:7200
GRAPHRAG_GRAPHDB_REPO=graphrag
```

`ontobrep_kg/config.py` loads these via `python-dotenv`.

## 3. GraphDB Free (Docker)

`docker-compose.yml`:

```yaml
services:
  graphdb:
    image: ontotext/graphdb:10.6.4
    ports:
      - "7200:7200"
    volumes:
      - ./data/graphdb:/opt/graphdb/home
```

```bash
docker compose up -d
# open http://localhost:7200
```

Create the repository (UI: Setup → Repositories → Create → GraphDB repository):
- Repository ID: `graphrag`
- Ruleset: **RDFS-Plus (Optimized)** (populates `http://www.ontotext.com/implicit`)

Or via REST:
```bash
curl -X POST http://localhost:7200/rest/repositories \
  -H "Content-Type: application/json" \
  -d @graphdb_repo_config.json
```

## 4. Load the OntoBREP ontology

```bash
# Turtle/OWL file from https://github.com/OntoBREP/ontobrep (owl/ folder)
curl -X POST \
  "http://localhost:7200/repositories/graphrag/statements" \
  -H "Content-Type: text/turtle" \
  --data-binary @data/ontology/ontobrep.ttl
```

## 5. Smoke test

```bash
python -m tests.test_smoke     # STEP -> .ttl -> GraphDB named graph -> SPARQL -> answer
```
