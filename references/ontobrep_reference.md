# OntoBREP Reference — Schema + Higher-Level Concept Definitions

Namespace: `cad: <http://www.fortiss.org/ont/ontobrep#>`
XSD:       `xsd: <http://www.w3.org/2001/XMLSchema#>`

This file is the **ground truth for the triples the converter emits** and for the
**entity descriptions injected into the NL→SPARQL prompt**. Source: the paper's
Listing 3 + Section IV/V and the OntoBREP GitHub schema.

---

## 1. Class–class relationships (from paper Listing 3, Turtle)

```turtle
cad:Face
    cad:position              cad:Position ;
    cad:boundedBy             cad:Wire ;
    cad:hasForwardOrientation xsd:boolean ;
    cad:representedBy         cad:Plane , cad:CylindricalSurface ,
                              cad:RectangularTrimmedSurface ;
    cad:area                  xsd:decimal ;
    cad:color                 cad:ColorRGB ;
    cad:triangulatedBy        cad:Triangulation ;
    cad:contains              cad:Wire ;
    cad:containedBy           cad:Shell ;
    cad:umax xsd:decimal ; cad:umin xsd:decimal ;
    cad:vmax xsd:decimal ; cad:vmin xsd:decimal .

cad:Plane
    cad:represents      cad:Face ;
    cad:directionX      cad:Vector ;
    cad:directionY      cad:Vector ;
    cad:directionNormal cad:Vector ;
    cad:position        cad:Position ;
    cad:planeOffset     xsd:decimal .

# CylindricalSurface (used by holes/shafts) — key properties used in queries:
cad:CylindricalSurface
    cad:represents      cad:Face ;
    cad:radius          xsd:decimal ;
    cad:directionNormal cad:Vector ;      # cylinder axis direction
    cad:position        cad:Position .

# A Vector carries components; a Position carries a location point.
cad:Vector   cad:x xsd:decimal ; cad:y xsd:decimal ; cad:z xsd:decimal .
cad:Position ... (x/y/z location) .
```

> **Equivalence to encode:** `cad:directionNormal` ≡ `cad:directionZ` (the paper treats
> the cylinder normal and the Z direction as equivalent for hole orientation).

The converter should emit the **topology chain** too: `Solid → Shell → Face → Wire →
Edge → Vertex`, with `cad:boundedBy`, `cad:contains`, `cad:containedBy` links, so that
containment/adjacency queries work.

---

## 2. Topology → OCC.Core mapping (for `step_to_owl.py`)

| OntoBREP                     | pythonocc (`OCC.Core`)                                             |
|------------------------------|-------------------------------------------------------------------|
| read STEP                    | `STEPControl.STEPControl_Reader`                                  |
| iterate faces/edges/…        | `TopExp.TopExp_Explorer(shape, TopAbs_FACE)` etc.                |
| cast to typed shape          | `TopoDS.topods.Face(...)`, `.Edge(...)`                          |
| surface + type               | `BRepAdaptor.BRepAdaptor_Surface(face)` → `.GetType()`          |
| plane params                 | `.Plane()` → `gp_Pln`: `.Location()`, `.Axis()`, `.XAxis()`, `.YAxis()` |
| cylinder params              | `.Cylinder()` → `gp_Cylinder`: `.Radius()`, `.Axis()`           |
| UV bounds (umin/umax/…)      | `BRepTools.breptools.UVBounds(face)` → (umin,umax,vmin,vmax)    |
| face area                    | `BRepGProp.brepgprop.SurfaceProperties(face, props)` → `.Mass()` |
| forward orientation (bool)   | `face.Orientation() == TopAbs.TopAbs_FORWARD`                    |
| surface type enum            | `GeomAbs.GeomAbs_Plane`, `GeomAbs.GeomAbs_Cylinder`, …           |

IRI scheme suggestion: `<{model_ns}#Face_{n}>`, `<{model_ns}#Cyl_{n}>`, etc., where
`model_ns = http://www.fortiss.org/ont/ontobrep/cad-XXXXXXXX`.

---

## 3. Higher-level concept definitions (inject verbatim into the NL→SPARQL prompt)

OntoBREP only defines **primitives**. Concepts like *hole* are **not** in the ontology;
they are described textually in the prompt so the LLM can compose the right SPARQL:

- **Cylindrical hole** = a `cad:Face` `cad:representedBy` a `cad:CylindricalSurface`,
  with `cad:hasForwardOrientation "false"` (inward-facing cylinder = material removed).
- **Radius / diameter**: `cylSurf cad:radius ?r` ; `diameter = 2 * ?r`.
- **Depth**: from the v-bounds of the face → `depth = vmax - vmin`.
- **Full 360° cylinder** (a real round hole, not a fillet segment):
  `ABS(umax - umin - 2*PI) < 1e-4` (PI ≈ 3.14159).
- **Orientation / axis**: the cylinder's `cad:directionNormal` vector (≡ `directionZ`).
  Its z-component tells you the hole is **vertical**, NOT whether it is on the top or
  the bottom. The axis sign is a modelling convention (the SAME physical hole can be
  stored with axis +z or −z), so **use `FILTER(ABS(?az) > 0.99)` to select vertical
  holes** — `FILTER(?az > 0.99)` silently misses every hole whose axis was stored as −z.
  ⚠️ To truly distinguish **top vs bottom** you need the hole opening's *position*
  relative to the part's z-extent (bounding box), which OntoBREP does not give directly
  — treat "on top" as "vertical" (order by size) unless position data is available. This
  is the paper's acknowledged view/orientation limitation (future work: bounding-box /
  raycasting analysis).
- **Through-hole vs blind hole**: through-holes pass fully through; blind holes have a
  planar or conical bottom. Note a through-hole is viewable from either side but the
  ontology stores a single normal — direction in the query must match.
- **Countersink / beveled / mounting hole**: characterized by an additional conical
  surface (`ConicalSurface`) adjoining the cylinder.
- **Shaft**: a cylindrical face with `hasForwardOrientation "true"` (outward = solid
  material), radius = shaft radius. Note its axis may differ from a stated viewing
  direction — needs bounding-box / property comparison for "visible from X" queries.

---

## 4. SPARQL generation hints (also injected into the prompt)

- Prefixes to always include:
  ```sparql
  PREFIX cad: <http://www.fortiss.org/ont/ontobrep#>
  PREFIX xsd: <http://www.w3.org/2001/XMLSchema#>
  PREFIX ofn: <http://www.ontotext.com/sparql/functions/>   # GraphDB math
  ```
- Query the correct named graph plus the implicit graph:
  ```sparql
  FROM <http://www.fortiss.org/ont/ontobrep/cad-00000182>
  FROM <http://www.ontotext.com/implicit>
  ```
- **Default** general queries: add `LIMIT 500` (bounds results for LLM evaluation).
- **Extreme-value** queries (smallest/biggest/largest/nearest): use
  `ORDER BY [DESC](?x)` + `LIMIT 1`.
- Math functions go through the `ofn:` prefix (GraphDB), e.g. `ofn:sqrt`, `ofn:asin`.
- Prefer property-path `cad:representedBy+ ?surf` to reach the surface of a face.
- Be **strict** about entity descriptions; minor flexibility only on named-graph
  spelling correction. Do not invent predicates.

---

## 5. Known conversion limitations (verified empirically on test parts)

These are properties of the STEP→graph conversion + concept definitions, confirmed by
converting known synthetic parts (box + Ø12 through-hole, protruding shaft):

1. **Hole/shaft classification is correct** — a removed-material cylinder yields
   `hasForwardOrientation "false"` (→ hole); protruding material yields `"true"`
   (→ shaft). Radius, `umax−umin ≈ 2π`, and depth `vmax−vmin` all come out correct.
2. **Axis sign is arbitrary (FIXED in queries).** The same hole can be stored with axis
   +z or −z. Verticality must use `ABS(?az)`, and top-vs-bottom is NOT derivable from the
   axis (see §3).
3. **Full-360° filter misses split cylinders.** `ABS(umax−umin−2π)<tol` assumes the hole
   wall is ONE cylindrical face. Some kernels split a cylinder into two ~180° faces at a
   seam; those holes are then missed by both detection and materialization. Robust
   handling would group co-axial, co-radial cylindrical faces before applying the sweep
   test — not yet implemented.
4. **Edges/vertices are duplicated per face.** Each face mints its own Edge/Vertex IRIs,
   so a shared edge between two faces is two distinct nodes. Containment queries work;
   **adjacency queries ("faces sharing an edge") do NOT** — would require deduping edges
   by geometric identity (`TopExp.MapShapesAndAncestors`).
5. **`cad:position` on a cylinder is the axis reference point** (`gp_Cylinder.Location()`),
   not the hole-opening center. "Center coordinates of a hole" queries are therefore
   approximate; a precise center needs the bounding box of the face's vertices.
