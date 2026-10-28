"""Headless verification of the cstamp core against the real CARTO mesh.

Runs inside Slicer:  Slicer.exe --python-script <this file>
Opens the saved non-clinical demo scene, intersects a ray with the
allowed surface, stamps/adjusts/commits via the pure cstamp package and
writes a JSONL ledger + result summary into artifacts/cstamp/.
Exits 0 on success, 1 on failure.
"""
import json
import math
import os
import sys

import slicer
import vtk

MODULE_DIR = os.path.dirname(os.path.realpath(__file__))
SCENE = r"C:\Projects\Cardiac-CT-Motion-Control\artifacts\slicer\CARTO3_EA_Map_Demo.mrb"
OUT_DIR = r"C:\Projects\Cardiac-CT-Motion-Control\artifacts\cstamp"
LEDGER = os.path.join(OUT_DIR, "headless_events.jsonl")
RESULT = os.path.join(OUT_DIR, "headless_result.json")

exit_code = 1
result = {"steps": []}
try:
    sys.path.insert(0, MODULE_DIR)
    from cstamp import CStampController, CTemplate, EventLedger, StampState

    os.makedirs(OUT_DIR, exist_ok=True)
    if os.path.exists(LEDGER):
        os.remove(LEDGER)

    slicer.util.loadScene(SCENE)
    node = slicer.util.getNode("CARTOmesh_1-OG")
    poly = node.GetPolyData()
    result["mesh_cells"] = poly.GetNumberOfCells()

    # ray from outside the mesh toward its center
    bounds = poly.GetBounds()
    center = [(bounds[0] + bounds[1]) / 2, (bounds[2] + bounds[3]) / 2,
              (bounds[4] + bounds[5]) / 2]
    origin = [center[0], center[1], bounds[5] + 50.0]

    locator = vtk.vtkCellLocator()
    locator.SetDataSet(poly)
    locator.BuildLocator()
    t = vtk.mutable(0.0)
    hit = [0.0, 0.0, 0.0]
    pcoords = [0.0, 0.0, 0.0]
    sub_id = vtk.mutable(0)
    cell_id = vtk.mutable(0)
    intersected = locator.IntersectWithLine(
        origin, center, 1e-6, t, hit, pcoords, sub_id, cell_id)
    result["intersected"] = bool(intersected)
    if not intersected:
        raise RuntimeError("ray did not hit surface")

    cell = poly.GetCell(cell_id.get())
    p0, p1, p2 = (cell.GetPoints().GetPoint(i) for i in range(3))
    e1 = [p1[i] - p0[i] for i in range(3)]
    e2 = [p2[i] - p0[i] for i in range(3)]
    n = [e1[1]*e2[2]-e1[2]*e2[1], e1[2]*e2[0]-e1[0]*e2[2],
         e1[0]*e2[1]-e1[1]*e2[0]]
    ln = math.sqrt(sum(c*c for c in n))
    normal = tuple(c/ln for c in n)

    controller = CStampController(template=CTemplate())
    draft = controller.stamp(tuple(hit), normal)
    result["steps"].append(("stamp", controller.state.value))
    controller.rotate_opening(math.radians(15.0))
    result["steps"].append(
        ("rotate", controller.draft.placement.in_plane_angle))

    ledger = EventLedger(LEDGER)
    event = controller.commit(ledger.append, {
        "event_kind": "cstamp", "layer": "PERFORMED",
        "scene": {"model_node": node.GetName(),
                  "coordinate_system": {"name": "RAS", "units": "mm"}},
        "input_method": "headless-test", "correction_of": None,
    })
    result["steps"].append(("commit", controller.state.value))
    result["event_id"] = event["event_id"]
    result["shape_points"] = len(event["shape_points"])
    result["integrity_ok"] = ledger.verify_integrity(event)

    dup = controller.commit(ledger.append, {"input_method": "headless-test"})
    result["deduplicated"] = dup.get("deduplicated") is True
    result["event_count"] = len(ledger.events())

    controller.stamp(tuple(hit), normal)
    controller.cancel()
    result["steps"].append(("cancel", controller.state.value))

    ok = (
        result["intersected"]
        and result["integrity_ok"]
        and result["deduplicated"]
        and result["event_count"] == 1
        and controller.state is StampState.IDLE
    )
    result["ok"] = ok
    exit_code = 0 if ok else 1
except Exception as error:  # noqa: BLE001
    result["error"] = repr(error)
finally:
    os.makedirs(OUT_DIR, exist_ok=True)
    with open(RESULT, "w", encoding="utf-8") as stream:
        json.dump(result, stream, ensure_ascii=False, indent=2)
    slicer.util.exit(exit_code)
