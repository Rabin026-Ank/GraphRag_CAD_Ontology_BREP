# Worked Example — "Largest hole on top of cad-00000182" (paper Listing 4)

This is the **Phase 2 acceptance test**: the pipeline must reproduce this end-to-end.

## Question
> "What is the diameter of the largest hole located on the top of the cad-00000182 object?"

## Reasoning the LLM must perform (encoded via the concept defs in `ontobrep_reference.md`)
1. A hole = a face represented by a cylindrical surface with `hasForwardOrientation false`.
2. Depth from v-bounds; a real round hole requires a full 360° sweep in u
   (`umax - umin ≈ 2π`).
3. "On top" ⇒ cylinder axis (`directionNormal`) z-component ≈ +1.
4. "Largest" ⇒ order by radius desc, limit 1. Diameter = 2·radius.

## Target SPARQL (from Listing 4 — golden output)
```sparql
PREFIX cad: <http://www.fortiss.org/ont/ontobrep#>
PREFIX xsd: <http://www.w3.org/2001/XMLSchema#>
SELECT DISTINCT ?face ((2 * ?radius) as ?diameter)
FROM <http://www.fortiss.org/ont/ontobrep/cad-00000182>
FROM <http://www.ontotext.com/implicit>
WHERE {
  ?face a cad:Face ;
        cad:hasForwardOrientation "false"^^xsd:boolean ;
        cad:representedBy+ ?cylSurf ; cad:position ?position ;
        cad:umax ?umax; cad:umin ?umin; cad:vmax ?vmax; cad:vmin ?vmin .
  # depth and 360 degree rotation
  BIND(?vmax-?vmin AS ?depth)
  FILTER (ABS(?umax - ?umin - 2 * 3.14159) < 1e-4)
  # Cylinder axis direction
  ?cylSurf a cad:CylindricalSurface ;
           cad:radius ?radius ; cad:directionNormal ?axis .
  ?axis cad:x ?ax ; cad:y ?ay ; cad:z ?az .
  FILTER(ABS(?az) > 0.99)   # vertical hole. NOTE: axis sign is arbitrary, so this
                            # cannot distinguish top from bottom (see reference §3).
                            # Listing 4's original ?az > 0.99 misses down-axis holes.
}
ORDER BY DESC(?radius)
LIMIT 1
```

## Answer generation
Given (question, SPARQL, JSON result), the LLM must:
1. rephrase the question,
2. state its thoughts,
3. produce the final answer (e.g. "The largest hole on top has a diameter of N mm.").

## Pass criterion
The generated SPARQL need not be byte-identical to the golden query — it must **return
the correct diameter** for `cad-00000182` when executed against the loaded named graph,
and the NL answer must state that value.
