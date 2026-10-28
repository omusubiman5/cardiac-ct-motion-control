"""Headless verification of CStampModule's logic layer in Slicer.

Loads the real module file, exercises MRML display node creation,
commit -> ledger, and ledger reload. Exits 0 on success.
"""
import importlib.util
import json
import math
import os
import sys

import slicer
import vtk


def _node_exists(name):
    try:
        slicer.util.getNode(name)
        return True
    except slicer.util.MRMLNodeNotFoundException:
        return False

MODULE_FILE = r"C:\Projects\Cardiac-CT-Motion-Control\prototypes\slicer-cstamp\CStampModule.py"
SCENE = r"C:\Projects\Cardiac-CT-Motion-Control\artifacts\slicer\CARTO3_EA_Map_Demo.mrb"
OUT_DIR = r"C:\Projects\Cardiac-CT-Motion-Control\artifacts\cstamp"
LEDGER = os.path.join(OUT_DIR, "module_events.jsonl")
PLAN_LEDGER = os.path.join(OUT_DIR, "module_plan.jsonl")
RESULT = os.path.join(OUT_DIR, "module_result.json")

exit_code = 1
result = {}
try:
    spec = importlib.util.spec_from_file_location("CStampModule", MODULE_FILE)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    result["module_loaded"] = True

    slicer.util.loadScene(SCENE)
    model = slicer.util.getNode("CARTOmesh_1-OG")
    poly = model.GetPolyData()

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
    locator.IntersectWithLine(origin, center, 1e-6, t, hit, pcoords,
                              sub_id, cell_id)
    cell = poly.GetCell(cell_id.get())
    p0, p1, p2 = (cell.GetPoints().GetPoint(i) for i in range(3))
    e1 = [p1[i] - p0[i] for i in range(3)]
    e2 = [p2[i] - p0[i] for i in range(3)]
    n = [e1[1]*e2[2]-e1[2]*e2[1], e1[2]*e2[0]-e1[0]*e2[2],
         e1[0]*e2[1]-e1[1]*e2[0]]
    ln = math.sqrt(sum(c*c for c in n))
    normal = tuple(c/ln for c in n)

    os.makedirs(OUT_DIR, exist_ok=True)
    if os.path.exists(LEDGER):
        os.remove(LEDGER)

    logic = module.CStampModuleLogic()
    logic.stamp_on_surface(tuple(hit), normal, model)

    draft_node = slicer.util.getNode(module.DRAFT_CURVE_NAME)
    result["draft_points"] = draft_node.GetNumberOfControlPoints()

    logic.rotate(math.radians(20.0))
    logic.rotate_to(math.radians(45.0))
    result["in_plane_deg"] = math.degrees(
        logic.controller.draft.placement.in_plane_angle)

    stored = logic.commit(LEDGER)
    result["event_id"] = stored["event_id"]
    points = slicer.util.getNode(module.PERFORMED_POINTS_NAME)
    result["performed_points"] = points.GetNumberOfControlPoints()
    shape = slicer.util.getNode(
        module.PERFORMED_SHAPE_PREFIX + stored["event_id"])
    result["shape_hidden"] = shape.GetDisplayVisibility() == 0

    # reshape via label selection
    points.SetNthControlPointSelected(0, True)
    logic.reshape_selected()
    result["reshape_visible"] = shape.GetDisplayVisibility() == 1

    # ledger reload on a fresh scene restores point + hidden shape
    slicer.mrmlScene.RemoveNode(points)
    logic2 = module.CStampModuleLogic()
    restored = logic2.load_ledger(LEDGER)
    points2 = slicer.util.getNode(module.PERFORMED_POINTS_NAME)
    result["restored"] = restored
    result["performed_points_after_reload"] = \
        points2.GetNumberOfControlPoints()

    # second reload must not duplicate the same event
    logic2.load_ledger(LEDGER)
    result["performed_points_after_second_load"] = \
        points2.GetNumberOfControlPoints()

    # cancel path: stamp again then cancel -> curve node removed
    logic2.stamp_on_surface(tuple(hit), normal, model)
    logic2.cancel()
    try:
        slicer.util.getNode(module.DRAFT_CURVE_NAME)
        result["cancel_removed"] = False
    except slicer.util.MRMLNodeNotFoundException:
        result["cancel_removed"] = True

    # view commands: parse + apply on a real vtkCamera
    from view_commands import apply_to_camera, parse_command

    camera = vtk.vtkCamera()
    camera.SetPosition(0, 0, 200)
    camera.SetFocalPoint(0, 0, 0)
    camera.SetViewUp(0, 1, 0)
    before = list(camera.GetPosition())
    apply_to_camera(camera, parse_command('{"cmd":"rotate","dx":10,"dy":5}'))
    result["camera_rotated"] = list(camera.GetPosition()) != before
    distance_before = camera.GetDistance()
    apply_to_camera(camera, parse_command('{"cmd":"zoom","ratio":1.5}'))
    result["camera_zoomed"] = camera.GetDistance() < distance_before
    result["bad_command_inert"] = parse_command(
        '{"cmd":"shell","line":"x"}') is None

    # loopback command server: typed protocol hello -> arm -> zoom
    import json as _json
    import socket
    import time as _time

    def _send_recv(stream, obj):
        stream.sendall((_json.dumps(obj) + "\n").encode("utf-8"))
        buf = b""
        deadline = _time.time() + 5.0
        while b"\n" not in buf and _time.time() < deadline:
            slicer.app.processEvents()
            try:
                chunk = stream.recv(4096)
            except socket.timeout:
                continue
            if not chunk:
                break
            buf += chunk
        return _json.loads(buf.decode().splitlines()[0])

    logic2.start_command_server(18944)
    try:
        stream = socket.create_connection(("127.0.0.1", 18944), timeout=2)
        stream.settimeout(0.2)
        hello = _send_recv(stream, {"cmd": "hello", "v": 1})
        session = hello["session"]
        arm = _send_recv(stream, {
            "v": 1, "session": session, "seq": 1, "req": "a1",
            "cmd": "arm", "ts": _time.time(), "params": {},
        })
        status = _send_recv(stream, {
            "v": 1, "session": session, "seq": 2, "req": "s1",
            "cmd": "status", "ts": _time.time(), "params": {},
        })
        bogus = _send_recv(stream, {
            "v": 1, "session": session, "seq": 3, "req": "b1",
            "cmd": "shell", "ts": _time.time(), "params": {},
        })
        stream.close()
        result["server_accepted"] = bool(
            hello.get("ok") and arm.get("ok") and status.get("ok")
            and not bogus.get("ok")
        )
        result["server_bogus_rejected"] = not bogus.get("ok")
    finally:
        logic2.stop_command_server()

    # --- plan following: PLANNED commit -> ghost -> PERFORMED match ---
    if os.path.exists(PLAN_LEDGER):
        os.remove(PLAN_LEDGER)
    if os.path.exists(LEDGER):
        os.remove(LEDGER)

    logic3 = module.CStampModuleLogic()
    logic3.stamp_on_surface(tuple(hit), normal, model)
    planned = logic3.commit(PLAN_LEDGER, layer="PLANNED")
    result["planned_layer"] = planned["layer"]
    result["planned_points"] = \
        slicer.util.getNode(
            module.PLANNED_POINTS_NAME).GetNumberOfControlPoints()

    logic3.load_plan(PLAN_LEDGER)
    ghost = slicer.util.getNode(module.GHOST_CURVE_NAME)
    result["ghost_visible"] = ghost.GetDisplayVisibility() == 1

    # performed commit near the plan -> matched, ghost advances/clears
    logic3.stamp_on_surface(
        (hit[0] + 2.0, hit[1] + 2.0, hit[2]), normal, model)
    performed = logic3.commit(LEDGER)
    from cstamp import EventLedger
    records = [
        e for e in EventLedger(LEDGER).events()
        if e.get("record_type") == "plan_match"
    ]
    result["match_recorded"] = len(records) == 1
    result["match_matched"] = records[0]["matched"] is True
    result["match_planned_id"] = records[0]["planned_event_id"] == \
        planned["event_id"]
    result["ghost_cleared"] = not _node_exists(module.GHOST_CURVE_NAME)

    # out-of-plan performed event: stamp on a distant surface cell
    ncells = poly.GetNumberOfCells()
    cell2 = poly.GetCell((cell_id.get() + ncells // 2) % ncells)
    q0, q1, q2 = (cell2.GetPoints().GetPoint(i) for i in range(3))
    centroid2 = tuple((q0[i] + q1[i] + q2[i]) / 3.0 for i in range(3))
    f1 = [q1[i] - q0[i] for i in range(3)]
    f2 = [q2[i] - q0[i] for i in range(3)]
    n2 = [f1[1]*f2[2]-f1[2]*f2[1], f1[2]*f2[0]-f1[0]*f2[2],
          f1[0]*f2[1]-f1[1]*f2[0]]
    l2 = math.sqrt(sum(c*c for c in n2)) or 1.0
    normal2 = tuple(c/l2 for c in n2)
    logic3.stamp_on_surface(centroid2, normal2, model)
    logic3.commit(LEDGER)
    records2 = [
        e for e in EventLedger(LEDGER).events()
        if e.get("record_type") == "plan_match"
    ]
    result["out_of_plan_recorded"] = (
        len(records2) == 2
        and records2[1]["matched"] is False
    )

    # widget smoke test: setup() and refresh without a main window.
    # (aim clicks still require a real 3D view -> GUI-only)
    try:
        widget = module.CStampModuleWidget()
        widget.setup()
        widget._refresh()
        result["widget_setup"] = True
        result["widget_status"] = widget.statusLabel.text[:40]
        widget.cleanup()
    except Exception as error:  # noqa: BLE001
        result["widget_setup"] = False
        result["widget_error"] = repr(error)

    ok = (
        result["module_loaded"]
        and result["draft_points"] == 33
        and abs(result["in_plane_deg"] - 45.0) < 1e-6
        and result["performed_points"] >= 1
        and result["shape_hidden"]
        and result["reshape_visible"]
        and result["restored"] == 1
        and result["performed_points_after_reload"] == 1
        and result["performed_points_after_second_load"] == 1
        and result["cancel_removed"]
        and result["camera_rotated"]
        and result["camera_zoomed"]
        and result["bad_command_inert"]
        and result["server_accepted"]
        and result["planned_layer"] == "PLANNED"
        and result["planned_points"] == 1
        and result["ghost_visible"]
        and result["match_recorded"]
        and result["match_matched"]
        and result["match_planned_id"]
        and result["ghost_cleared"]
        and result["out_of_plan_recorded"] is not False
        and result["widget_setup"]
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
