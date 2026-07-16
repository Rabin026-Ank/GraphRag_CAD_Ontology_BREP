"""GraphRAG-for-CAD package: STEP -> OntoBREP KG -> LLM NL->SPARQL -> NL answer.

See ../PLAN.md for the full spec. Modules:
    config              env-driven configuration (endpoints, model, namespaces)
    step_to_owl         Phase 1: STEP file -> rdflib Graph -> Turtle
    graphdb_client      Phase 0/2: load named graphs, run SPARQL over HTTP
    llm                 OpenAI-compatible chat wrapper
    nl_to_sparql        Phase 2: build prompt, generate + clean SPARQL
    answer_gen          Phase 2: SPARQL result JSON -> NL answer
    pipeline            ask(question, model_graph_iri) -> {sparql, results, answer}
    concepts_materialize  Phase 4 (optional): SPARQL INSERT for holes/cutouts
"""
