"""GUI-level verification: run with a real Slicer main window.

    Slicer.exe --python-script gui_verify.py

Loads the scene, instantiates the module widget, synthesizes a left
click on the CARTO surface through the real 3D-view interactor, then
exercises adjust -> commit -> cancel -> ledger. Writes
artifacts/cstamp/gui_result.json. Not for clinical use.
"""
import importlib.util
import json
import math
import os
import sys

import slicer
import vtk

MODULE_FILE = r"C:\Projects\Cardiac-CT-Motion-Control\prototypes\slicer-cstamp\CStampModule.py"
SCENE = r"C:\Projects\Cardiac-CT-Motion-Control\artifacts\slicer\CARTO3_EA_Map_Demo.mrb"
OUT_DIR = r"C:\Projects\Cardiac-CT-Motion-Control\artifacts\cstamp"
LEDGER = os.path.join(OUT_DIR, "gui_events.jsonl")
RESULT = os.path.join(OUT_DIR, "gui_result.json")

exit_code = 1
result = {"mode": "gui"}
try:
    if slicer.app.layoutManager() is None:
        raise RuntimeError("no main window; run without --no-main-window")

    spec = importlib.util.spec_from_file_location(
        "CStampModule", MODULE_FILE)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    result["module_loaded"] = True

    slicer.util.loadScene(SCENE)
    slicer.app.processEvents()
    model = slicer.util.getNode("CARTOmesh_1-OG")

    widget = module.CStampModuleWidget()
    widget.setup()
    result["widget_setup"] = True

    if os.path.exists(LEDGER):
        os.remove(LEDGER)
    widget.ledgerEdit.text = LEDGER

    view = slicer.app.layoutManager().threeDWidget(0).threeDView()
    view.resetCamera()
    view.forceRender()
    slicer.app.processEvents()
    renderer = (
        view.renderWindow().GetRenderers().GetFirstRenderer())

    # pick a mesh vertex and project it to display coordinates
    poly = model.GetPolyData()
    world = poly.GetPoint(poly.GetNumberOfPoints() // 3)
    renderer.SetWorldPoint(world[0], world[1], world[2], 1.0)
    renderer.WorldToDisplay()
    dx, dy = renderer.GetDisplayPoint()[:2]
    result["click_display_xy"] = [dx, dy]

    interactor = view.interactor()
    interactor.SetEventPosition(int(dx), int(dy))

    # AC-001: aim -> stamp via the real interactor path
    widget.stampButton.setChecked(True)
    widget.onStamp(True)
    interactor.InvokeEvent(vtk.vtkCommand.LeftButtonPressEvent)
    slicer.app.processEvents()
    try:
        draft = slicer.util.getNode(module.DRAFT_CURVE_NAME)
        result["ac001_draft_points"] = draft.GetNumberOfControlPoints()
    except slicer.util.MRMLNodeNotFoundException:
        result["ac001_draft_points"] = 0

    # AC-002: adjust opening direction (continuous slider path)
    widget.openingSlider.value = 60
    slicer.app.processEvents()
    result["ac002_angle_deg"] = math.degrees(
        widget.logic.controller.draft.placement.in_plane_angle)

    # AC-003: explicit commit
    widget.onCommit()
    slicer.app.processEvents()
    result["ac003_performed_points"] = slicer.util.getNode(
        module.PERFORMED_POINTS_NAME).GetNumberOfControlPoints()
    with open(LEDGER, encoding="utf-8") as stream:
        lines = [l for l in stream.read().splitlines() if l.strip()]
    result["ac003_ledger_lines"] = len(lines)

    # AC-004: cancel discards draft only
    interactor.SetEventPosition(int(dx), int(dy))
    widget.stampButton.setChecked(True)
    widget.onStamp(True)
    interactor.InvokeEvent(vtk.vtkCommand.LeftButtonPressEvent)
    slicer.app.processEvents()
    widget.onCancel()
    slicer.app.processEvents()
    try:
        slicer.util.getNode(module.DRAFT_CURVE_NAME)
        result["ac004_draft_removed"] = False
    except slicer.util.MRMLNodeNotFoundException:
        result["ac004_draft_removed"] = True
    with open(LEDGER, encoding="utf-8") as stream:
        lines = [l for l in stream.read().splitlines() if l.strip()]
    result["ac004_ledger_lines"] = len(lines)

    # command server end-to-end: typed protocol rotates the real camera
    import json as _json
    import socket
    import time as _time
    # SR-006: editing/view commands are gated on the target window being
    # foreground — bring Slicer forward first
    try:
        mw = slicer.util.mainWindow()
        if mw is not None:
            mw.showNormal()
            mw.raise_()
            mw.activateWindow()
            import ctypes as _ct
            _ct.windll.user32.SetForegroundWindow(int(mw.winId()))
            slicer.app.processEvents()
            _time.sleep(0.3)
    except Exception:  # noqa: BLE001
        pass
    camera_node = view.cameraNode()
    before = list(camera_node.GetCamera().GetPosition())
    logic = widget.logic
    logic.start_command_server(18944)
    try:
        stream = socket.create_connection(("127.0.0.1", 18944),
                                          timeout=3)
        stream.settimeout(0.2)

        def _rpc(obj):
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

        hello = _rpc({"cmd": "hello", "v": 1})
        session = hello["session"]
        seq = [0]

        def _cmd(name, params=None):
            seq[0] += 1
            return _rpc({
                "v": 1, "session": session, "seq": seq[0],
                "req": f"r{seq[0]}", "cmd": name,
                "ts": _time.time(), "params": params or {},
            })

        arm_response = _cmd("arm")
        result["arm_response"] = arm_response
        # rotate until the camera actually moved or attempts run out
        last_response = None
        for _ in range(20):
            last_response = _cmd("view_rotate", {"dx": 15.0, "dy": 0.0})
            if before != list(camera_node.GetCamera().GetPosition()):
                break
        result["rotate_response"] = last_response
        stream.close()
    finally:
        logic.stop_command_server()
    result["server_moved_camera"] = (
        before != list(camera_node.GetCamera().GetPosition()))

    widget.cleanup()
    ok = (
        result["module_loaded"]
        and result["widget_setup"]
        and result["ac001_draft_points"] == 33
        and abs(result["ac002_angle_deg"] - 60.0) < 1e-6
        and result["ac003_performed_points"] == 1
        and result["ac003_ledger_lines"] == 1
        and result["ac004_draft_removed"]
        and result["ac004_ledger_lines"] == 1
        and result["server_moved_camera"]
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
