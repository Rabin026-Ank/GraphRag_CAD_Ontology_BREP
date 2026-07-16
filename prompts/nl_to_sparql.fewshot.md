# Few-shot NL -> SPARQL examples

Keep examples short; they strongly help smaller local models. Each shows a Q followed by
the exact SPARQL to generate. The model should mirror this style (prefixes, FROM clauses,
LIMIT 500 / ORDER BY ... LIMIT 1).

## Example 1 — largest hole on top
Q: What is the diameter of the largest hole located on the top of the cad-00000182 object?
SPARQL:
```
PREFIX cad: <http://www.fortiss.org/ont/ontobrep#>
PREFIX xsd: <http://www.w3.org/2001/XMLSchema#>
SELECT DISTINCT ?face ((2 * ?radius) as ?diameter)
FROM <http://www.fortiss.org/ont/ontobrep/cad-00000182>
FROM <http://www.ontotext.com/implicit>
WHERE {
  ?face a cad:Face ;
        cad:hasForwardOrientation "false"^^xsd:boolean ;
        cad:representedBy+ ?cylSurf ;
        cad:umax ?umax; cad:umin ?umin; cad:vmax ?vmax; cad:vmin ?vmin .
  BIND(?vmax-?vmin AS ?depth)
  FILTER (ABS(?umax - ?umin - 2 * 3.14159) < 1e-4)
  ?cylSurf a cad:CylindricalSurface ;
           cad:radius ?radius ; cad:directionNormal ?axis .
  ?axis cad:x ?ax ; cad:y ?ay ; cad:z ?az .
  FILTER(ABS(?az) > 0.99)   # vertical hole (axis sign is arbitrary; top vs bottom
                            # cannot be told from axis alone — see reference §3)
}
ORDER BY DESC(?radius)
LIMIT 1
```

## Example 2 — count of holes
Q: How many holes does the cad-00000182 model have?
SPARQL:
```
PREFIX cad: <http://www.fortiss.org/ont/ontobrep#>
PREFIX xsd: <http://www.w3.org/2001/XMLSchema#>
SELECT (COUNT(DISTINCT ?face) as ?count)
FROM <http://www.fortiss.org/ont/ontobrep/cad-00000182>
FROM <http://www.ontotext.com/implicit>
WHERE {
  ?face a cad:Face ;
        cad:hasForwardOrientation "false"^^xsd:boolean ;
        cad:representedBy+ ?cylSurf ;
        cad:umax ?umax ; cad:umin ?umin .
  ?cylSurf a cad:CylindricalSurface .
  FILTER (ABS(?umax - ?umin - 2 * 3.14159) < 1e-4)
}
LIMIT 500
```

## Example 3 — diameter of a named shaft
Q: What is the diameter of the shaft on the cad-00000182 object?
SPARQL:
```
PREFIX cad: <http://www.fortiss.org/ont/ontobrep#>
PREFIX xsd: <http://www.w3.org/2001/XMLSchema#>
SELECT DISTINCT ((2 * ?radius) as ?diameter)
FROM <http://www.fortiss.org/ont/ontobrep/cad-00000182>
FROM <http://www.ontotext.com/implicit>
WHERE {
  ?face a cad:Face ;
        cad:hasForwardOrientation "true"^^xsd:boolean ;
        cad:representedBy+ ?cylSurf ;
        cad:umax ?umax ; cad:umin ?umin .
  ?cylSurf a cad:CylindricalSurface ;
           cad:radius ?radius .
  FILTER (ABS(?umax - ?umin - 2 * 3.14159) < 1e-4)
}
ORDER BY DESC(?radius)
LIMIT 1
```

## Example 4 — coordinates of holes on a face
Q: What are the coordinates of the centers of the holes on the front face of cad-00000182?
SPARQL:
```
PREFIX cad: <http://www.fortiss.org/ont/ontobrep#>
PREFIX xsd: <http://www.w3.org/2001/XMLSchema#>
SELECT ?face ?px ?py ?pz
FROM <http://www.fortiss.org/ont/ontobrep/cad-00000182>
FROM <http://www.ontotext.com/implicit>
WHERE {
  ?face a cad:Face ;
        cad:hasForwardOrientation "false"^^xsd:boolean ;
        cad:representedBy+ ?cylSurf ;
        cad:position ?pos .
  ?pos cad:x ?px ; cad:y ?py ; cad:z ?pz .
  ?cylSurf a cad:CylindricalSurface .
}
LIMIT 500
```
