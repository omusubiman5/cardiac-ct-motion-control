"""Launch inside Slicer GUI: load the demo scene, instantiate the
C-stamp module widget, and start the loopback view-command server on
port 18944. Leaves Slicer running. Writes a ready marker file.

    Slicer.exe --python-script start_server_session.py

Not for clinical use.
"""
import importlib.util
import os
import json
import hashlib

import slicer

MODULE_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'CStampModule.py')
WORKSPACE = os.environ.get('CSTAMP_WORKSPACE_ROOT', r'C:\Projects\Cardiac-CT-Motion-Control')
SCENE = os.path.join(WORKSPACE, 'artifacts', 'slicer', 'CARTO3_EA_Map_Demo.mrb')
MARKER = os.path.join(WORKSPACE, 'artifacts', 'cstamp', 'server_ready.txt')
PORT = 18944

import traceback

LOG = os.path.join(WORKSPACE, 'artifacts', 'cstamp', 'server_log.txt')
os.makedirs(os.path.dirname(LOG), exist_ok=True)

with open(LOG, "w", encoding="utf-8") as stream:
    stream.write("script started\n")

try:
    spec = importlib.util.spec_from_file_location("CStampModule", MODULE_FILE)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    slicer.util.loadScene(SCENE)
    slicer.app.processEvents()

    widget = module.CStampModuleWidget()
    widget.logic.scene_reference = os.path.abspath(SCENE)
    widget.logic.start_command_server(PORT)
    # keep a reference so the widget/logic are not garbage-collected
    slicer.modules._cstamp_session = widget
    # All everyday controls are hosted in the main Slicer dock.
    widget.logic._unified_hand_panel.attach_mouse_widget(widget.parent)

    with open(MARKER, "w", encoding="utf-8") as stream:
        stream.write(f"port={PORT}\n")
    ready_path = os.environ.get('CSTAMP_STARTUP_READY')
    if ready_path:
        temporary = ready_path + '.tmp'
        with open(temporary,'w',encoding='utf-8') as stream:
            json.dump({'nonce':os.environ['CSTAMP_STARTUP_NONCE'],'pid':os.getpid(),
                       'port':PORT,'armed':False,'module_path':MODULE_FILE,
                       'module_sha256':hashlib.sha256(open(MODULE_FILE,'rb').read()).hexdigest()},stream)
        os.replace(temporary,ready_path)
    with open(LOG, "a", encoding="utf-8") as stream:
        stream.write("server listening\n")
    print(f"[cstamp] command server listening on 127.0.0.1:{PORT}")
except Exception:  # noqa: BLE001
    with open(LOG, "a", encoding="utf-8") as stream:
        stream.write(traceback.format_exc())
