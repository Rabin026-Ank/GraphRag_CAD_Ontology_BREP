"""Phase 1 — STEP file -> OntoBREP RDF graph (Turtle).

Reimplements the paper's occjava converter in Python using pythonocc (OCC.Core) + rdflib.
Emit the SUBSET of OntoBREP the queries touch: Solid/Shell/Face/Wire/Edge/Vertex topology
plus Plane / CylindricalSurface (+ ConicalSurface) geometry, Position, Vector, and the
decimal/boolean properties (area, umin/umax/vmin/vmax, radius, hasForwardOrientation,
directionNormal/X/Y, planeOffset). See references/ontobrep_reference.md §1-2 for the exact
predicates and the OCC.Core API mapping.

CLI:
    python -m ontobrep_kg.step_to_owl data/models/cad-00000182.step \
        --model-id cad-00000182 --out data/ttl/cad-00000182.ttl
"""
from __future__ import annotations

from rdflib import Graph, Literal, Namespace, RDF, URIRef
from rdflib.namespace import XSD

from .config import ONTOBREP_NS, MODEL_GRAPH_BASE

CAD = Namespace(ONTOBREP_NS)

# pythonocc imports (only needed when actually converting; kept local so the module
# can be imported for e.g. the CLI help without an installed OCC).
from OCC.Core.STEPControl import STEPControl_Reader  # noqa: E402
from OCC.Core.TopExp import TopExp_Explorer  # noqa: E402
from OCC.Core.TopoDS import topods  # noqa: E402
from OCC.Core.BRepAdaptor import BRepAdaptor_Surface  # noqa: E402
from OCC.Core.BRepTools import breptools  # noqa: E402
from OCC.Core.BRepGProp import brepgprop  # noqa: E402
from OCC.Core.GProp import GProp_GProps  # noqa: E402
import OCC.Core.TopAbs as TopAbs  # noqa: E402
from OCC.Core.GeomAbs import GeomAbs_Plane, GeomAbs_Cylinder, GeomAbs_Cone  # noqa: E402


class _Builder:
    """Mints stable IRIs and accumulates OntoBREP triples in an rdflib Graph."""

    def __init__(self, graph: Graph, model_id: str):
        self.g = graph
        # Entity IRIs must be <MODEL_GRAPH_BASE>/<model_id>#<Entity>_<n> — a SINGLE
        # '#'. This also matches the named-graph IRI (model_graph_iri) used to load
        # the data, so GraphDB keeps entities and graph in the same namespace.
        self.base = f"{MODEL_GRAPH_BASE}/{model_id}"
        self._counters: dict[str, int] = {}

    def iri(self, kind: str) -> URIRef:
        self._counters[kind] = self._counters.get(kind, 0) + 1
        return URIRef(f"{self.base}#{kind}_{self._counters[kind]}")

    # -- low-level helpers -------------------------------------------------
    def dec(self, v: float) -> Literal:
        # round to a sane precision to keep the .ttl readable / stable
        return Literal(round(float(v), 9), datatype=XSD.decimal)

    def bool(self, v: bool) -> Literal:
        return Literal(bool(v), datatype=XSD.boolean)

    def add(self, s, p, o) -> None:
        self.g.add((s, p, o))

    # -- geometry helpers --------------------------------------------------
    def vector(self, dir_) -> str:
        v = self.iri("Vector")
        self.add(v, RDF.type, CAD.Vector)
        self.add(v, CAD.x, self.dec(dir_.X()))
        self.add(v, CAD.y, self.dec(dir_.Y()))
        self.add(v, CAD.z, self.dec(dir_.Z()))
        return v

    def position(self, pnt) -> str:
        p = self.iri("Position")
        self.add(p, RDF.type, CAD.Position)
        self.add(p, CAD.x, self.dec(pnt.X()))
        self.add(p, CAD.y, self.dec(pnt.Y()))
        self.add(p, CAD.z, self.dec(pnt.Z()))
        return p

    def face(self, face_entity, solid_iri=None, shell_iri=None) -> str:
        face_iri = self.iri("Face")
        self.add(face_iri, RDF.type, CAD.Face)
        if solid_iri:
            self.add(solid_iri, CAD.contains, face_iri)
            self.add(face_iri, CAD.containedBy, solid_iri)
        if shell_iri:
            self.add(shell_iri, CAD.contains, face_iri)
            self.add(face_iri, CAD.containedBy, shell_iri)
        return face_iri


def _emit_surface(b: _Builder, face_iri: str, surf):
    """Emit geometry triples for the surface underlying a face.

    Returns (surface_iri, position_iri). position_iri is the surface/face location
    and is also linked to the Face (cad:position) so the OntoBREP schema's
    `cad:Face cad:position cad:Position` pattern holds. Returns (None, None) for
    unsupported surface types.
    """
    gtype = surf.GetType()

    if gtype == GeomAbs_Plane:
        pln = surf.Plane()
        s = b.iri("Plane")
        b.add(s, RDF.type, CAD.Plane)
        b.add(s, CAD.represents, face_iri)
        b.add(s, CAD.directionX, b.vector(pln.XAxis().Direction()))
        b.add(s, CAD.directionY, b.vector(pln.YAxis().Direction()))
        normal = b.vector(pln.Axis().Direction())
        b.add(s, CAD.directionNormal, normal)
        # equivalence: directionNormal == directionZ for hole orientation
        b.add(s, CAD.directionZ, normal)
        pos = b.position(pln.Location())
        b.add(s, CAD.position, pos)
        # plane offset = scalar D of plane equation Ax+By+Cz+D=0 (normal is unit)
        coef = pln.Coefficients()
        b.add(s, CAD.planeOffset, b.dec(coef[3]))
        return s, pos

    if gtype == GeomAbs_Cylinder:
        cyl = surf.Cylinder()
        s = b.iri("CylindricalSurface")
        b.add(s, RDF.type, CAD.CylindricalSurface)
        b.add(s, CAD.represents, face_iri)
        normal = b.vector(cyl.Axis().Direction())
        b.add(s, CAD.directionNormal, normal)
        b.add(s, CAD.directionZ, normal)  # equivalence (gotcha #3)
        b.add(s, CAD.radius, b.dec(cyl.Radius()))
        pos = b.position(cyl.Location())
        b.add(s, CAD.position, pos)
        return s, pos

    if gtype == GeomAbs_Cone:
        cone = surf.Cone()
        s = b.iri("ConicalSurface")
        b.add(s, RDF.type, CAD.ConicalSurface)
        b.add(s, CAD.represents, face_iri)
        normal = b.vector(cone.Axis().Direction())
        b.add(s, CAD.directionNormal, normal)
        b.add(s, CAD.directionZ, normal)
        b.add(s, CAD.radius, b.dec(cone.RefRadius()))
        b.add(s, CAD.semiAngle, b.dec(cone.SemiAngle()))
        pos = b.position(cone.Location())
        b.add(s, CAD.position, pos)
        return s, pos

    # Other surface kinds (sphere, torus, surface-of-revolution, ...) are not
    # part of the emitted subset; the face is still recorded (topology + area).
    return None, None


def step_to_graph(step_path: str, model_id: str) -> Graph:
    """Parse a STEP file and return an rdflib Graph of OntoBREP triples.

    IRIs are minted under f"{ONTOBREP_NS}{model_id}#{Entity}_{n}".
    """
    reader = STEPControl_Reader()
    reader.ReadFile(step_path)
    nb_roots = reader.TransferRoots()
    if nb_roots <= 0:
        raise RuntimeError(f"STEPControl_Reader transferred 0 roots from {step_path}")
    shape = reader.OneShape()
    if shape.IsNull():
        raise RuntimeError(f"STEPControl_Reader produced a null shape for {step_path}")

    g = Graph()
    b = _Builder(g, model_id)

    # Walk solids (a STEP part is usually a single solid, sometimes a compound).
    solid_exp = TopExp_Explorer(shape, TopAbs.TopAbs_SOLID)
    if not solid_exp.More():
        # No explicit solid: treat the whole shape as one implicit solid.
        solid_exp = None

    def iter_solids():
        if solid_exp is None:
            yield None
            return
        while solid_exp.More():
            yield topods.Solid(solid_exp.Current())
            solid_exp.Next()

    for solid in iter_solids():
        solid_iri = b.iri("Solid") if solid is not None else None
        if solid_iri is not None:
            g.add((solid_iri, RDF.type, CAD.Solid))

        parent_for_faces = solid if solid is not None else shape
        shell_exp = TopExp_Explorer(parent_for_faces, TopAbs.TopAbs_SHELL)
        shell_iri = None
        if shell_exp.More():
            shell = topods.Shell(shell_exp.Current())
            shell_iri = b.iri("Shell")
            g.add((shell_iri, RDF.type, CAD.Shell))
            if solid_iri is not None:
                g.add((solid_iri, CAD.contains, shell_iri))
                g.add((shell_iri, CAD.containedBy, solid_iri))

        face_exp = TopExp_Explorer(parent_for_faces, TopAbs.TopAbs_FACE)
        while face_exp.More():
            face = topods.Face(face_exp.Current())
            face_iri = b.face(face, solid_iri=solid_iri, shell_iri=shell_iri)

            # topology: wire -> edge -> vertex
            wire_exp = TopExp_Explorer(face, TopAbs.TopAbs_WIRE)
            while wire_exp.More():
                wire = topods.Wire(wire_exp.Current())
                wire_iri = b.iri("Wire")
                g.add((wire_iri, RDF.type, CAD.Wire))
                g.add((face_iri, CAD.boundedBy, wire_iri))
                g.add((wire_iri, CAD.containedBy, face_iri))
                edge_exp = TopExp_Explorer(wire, TopAbs.TopAbs_EDGE)
                while edge_exp.More():
                    edge = topods.Edge(edge_exp.Current())
                    edge_iri = b.iri("Edge")
                    g.add((edge_iri, RDF.type, CAD.Edge))
                    g.add((wire_iri, CAD.contains, edge_iri))
                    g.add((edge_iri, CAD.containedBy, wire_iri))
                    vert_exp = TopExp_Explorer(edge, TopAbs.TopAbs_VERTEX)
                    while vert_exp.More():
                        vert = topods.Vertex(vert_exp.Current())
                        vert_iri = b.iri("Vertex")
                        g.add((vert_iri, RDF.type, CAD.Vertex))
                        g.add((edge_iri, CAD.boundedBy, vert_iri))
                        g.add((vert_iri, CAD.containedBy, edge_iri))
                        vert_exp.Next()
                    edge_exp.Next()
                wire_exp.Next()

            # geometry
            surf = BRepAdaptor_Surface(face)
            try:
                umin, umax, vmin, vmax = breptools.UVBounds(face)
                g.add((face_iri, CAD.umin, b.dec(umin)))
                g.add((face_iri, CAD.umax, b.dec(umax)))
                g.add((face_iri, CAD.vmin, b.dec(vmin)))
                g.add((face_iri, CAD.vmax, b.dec(vmax)))
            except Exception:
                # UVBounds can fail for non-trimmed/infinite surfaces; skip bounds.
                pass

            props = GProp_GProps()
            try:
                brepgprop.SurfaceProperties(face, props)
                g.add((face_iri, CAD.area, b.dec(props.Mass())))
            except Exception:
                pass

            g.add((face_iri, CAD.hasForwardOrientation,
                   b.bool(face.Orientation() == TopAbs.TopAbs_FORWARD)))

            surf_iri, pos_iri = _emit_surface(b, face_iri, surf)
            if surf_iri is not None:
                g.add((face_iri, CAD.representedBy, surf_iri))
            if pos_iri is not None:
                g.add((face_iri, CAD.position, pos_iri))

            face_exp.Next()

    return g


def serialize(graph: Graph, out_ttl: str) -> None:
    graph.serialize(destination=out_ttl, format="turtle")


if __name__ == "__main__":  # pragma: no cover
    import argparse

    ap = argparse.ArgumentParser()
    ap.add_argument("step_path")
    ap.add_argument("--model-id", required=True)
    ap.add_argument("--out", required=True)
    args = ap.parse_args()
    g = step_to_graph(args.step_path, args.model_id)
    serialize(g, args.out)
    print(f"wrote {len(g)} triples -> {args.out}")
