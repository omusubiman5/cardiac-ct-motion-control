"""Explicit synthetic test fixture. No normal scene, camera, IPC dock or ledger."""
import hashlib
import importlib.util
import json
import os
import platform
import sys
import traceback
from pathlib import Path
import qt
import slicer
import vtk
from vtk.util.numpy_support import vtk_to_numpy

ROOT=Path(__file__).resolve().parents[1]
OUT=Path(os.environ['CSTAMP_TEST_DIR']).resolve()
PORT=int(os.environ['CSTAMP_TEST_PORT'])
if not OUT.is_relative_to(ROOT/'work') or PORT==18944:
    raise RuntimeError('test directory and port must be isolated from normal operation')
OUT.mkdir(parents=True,exist_ok=True)
try:
    module_path=ROOT/'prototypes/slicer-cstamp/CStampModule.py'
    spec=importlib.util.spec_from_file_location('CStampSyntheticFixture',module_path)
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    module.DEFAULT_LEDGER_PATH=str(OUT/'events.jsonl')
    module.DEFAULT_PLAN_REGISTRY_PATH=str(OUT/'plans.jsonl')
    if os.environ.get('CSTAMP_TEST_RESTART')=='1':
        slicer.mrmlScene.AddNewNodeByClass('vtkMRMLModelNode','node-ID-shift-only')
    sphere=vtk.vtkSphereSource();sphere.SetRadius(50);sphere.SetThetaResolution(40);sphere.SetPhiResolution(40);sphere.Update()
    model=slicer.mrmlScene.AddNewNodeByClass('vtkMRMLModelNode',module.DEFAULT_SURFACE_NAME)
    model.SetAndObservePolyData(sphere.GetOutput());model.CreateDefaultDisplayNodes()
    from cstamp.contracts import digest
    from cstamp.target_registry import TargetRegistry
    from cstamp.runtime_contract import RuntimePolicy
    shape_hash=hashlib.sha256()
    for array in (sphere.GetOutput().GetPoints().GetData(),sphere.GetOutput().GetPolys().GetData()):
        shape_hash.update(vtk_to_numpy(array).tobytes())
    matrix=[[float(i==j) for j in range(4)] for i in range(4)]
    targets={'schema_version':1,'targets':[{'target_id':'synthetic-sphere','scene_id':'nonclinical-demo',
             'model_name':module.DEFAULT_SURFACE_NAME,'model_sha256':shape_hash.hexdigest(),
             'transform_sha256':digest(matrix),'registration_reference':'explicit synthetic self-verification fixture; not user target approval'}]}
    (OUT/'targets.json').write_text(json.dumps(targets),encoding='utf-8')
    actual={'settings':{'input_source':'synthetic API self-verification'},
            'camera':{'index':0,'width':1280,'height':720,'backend':'SYNTHETIC','device_path_sha256':'d'*64},
            'model_sha256':'0'*64,'software_sha256':{'test_fixture':hashlib.sha256(Path(__file__).read_bytes()).hexdigest()},
            'python_version':platform.python_version(),'windows_version':platform.platform()}
    policy={'schema_version':1,'recognizer':actual,'slicer_version':str(slicer.app.applicationVersion),
            'slicer_software_sha256':module._LOADED_SOURCE_HASHES,
            'target_registry_sha256':TargetRegistry(targets).sha256}
    RuntimePolicy(policy)
    (OUT/'runtime.json').write_text(json.dumps(policy),encoding='utf-8')
    os.environ['CSTAMP_TARGET_REGISTRY']=str(OUT/'targets.json')
    os.environ['CSTAMP_RUNTIME_MANIFEST']=str(OUT/'runtime.json')
    widget=module.CStampModuleWidget()
    logic=widget.logic
    logic.surface_node=model
    logic.dispatcher=module.CommandDispatcher(logic)
    server=module._CommandServer(PORT,logic.dispatcher)
    logic._command_server=server
    # File-driven fault injection exists ONLY in this isolated synthetic fixture.
    originals={'ack':logic.display_contract.acknowledge,'append':module.EventLedger.append,
               'handle':logic.dispatcher.handle_line,'replace':os.replace}
    last_control=[None]
    original_poly=vtk.vtkPolyData();original_poly.DeepCopy(model.GetPolyData())
    original_parent=model.GetTransformNodeID()
    def control():
        path=OUT/'fault-control.json'
        if not path.exists():return
        value=json.loads(path.read_text(encoding='utf-8'))
        if value.get('id')==last_control[0]:return
        last_control[0]=value.get('id');kind=value.get('kind')
        if kind=='save-failure':
            def fail(*args,**kwargs):raise OSError('injected isolated persistence failure')
            module.EventLedger.append=fail
        elif kind in {'crash-before-replace','crash-after-replace'}:
            def crash_replace(source,destination):
                if Path(destination).resolve() == OUT/'events.jsonl':
                    (OUT/'crash-stage.json').write_text(json.dumps({'kind':kind,'pid':os.getpid(),
                        'request_id':getattr(logic,'_request_context',{}).get('req'),
                        'source_sha256':hashlib.sha256(module_path.read_bytes()).hexdigest()}),encoding='utf-8')
                    if kind=='crash-before-replace':os._exit(77)
                    originals['replace'](source,destination)
                    os._exit(78)
                return originals['replace'](source,destination)
            os.replace=crash_replace
        elif kind=='render-hold':logic.display_contract.acknowledge=lambda *args,**kwargs:None
        elif kind=='drop-commit-response':
            def drop(raw):
                response=originals['handle'](raw)
                if json.loads(raw).get('cmd')=='commit' and response.get('ok'):
                    for socket in list(server._sockets):socket.abort()
                return response
            logic.dispatcher.handle_line=drop
        elif kind=='model-shape-change':
            point=model.GetPolyData().GetPoint(0)
            model.GetPolyData().GetPoints().SetPoint(0,point[0]+1,point[1],point[2])
            model.GetPolyData().GetPoints().Modified();model.GetPolyData().Modified()
        elif kind=='model-transform-change':
            transform=slicer.mrmlScene.AddNewNodeByClass('vtkMRMLLinearTransformNode','synthetic-transform-fault')
            matrix=vtk.vtkMatrix4x4();matrix.Identity();matrix.SetElement(0,3,1)
            transform.SetMatrixTransformToParent(matrix);model.SetAndObserveTransformNodeID(transform.GetID())
        elif kind=='model-remove':slicer.mrmlScene.RemoveNode(model)
        elif kind=='restore':
            os.replace=originals['replace']
            module.EventLedger.append=originals['append']
            logic.display_contract.acknowledge=originals['ack']
            logic.dispatcher.handle_line=originals['handle']
            if model.GetScene() is None:slicer.mrmlScene.AddNode(model)
            model.GetPolyData().DeepCopy(original_poly);model.SetAndObserveTransformNodeID(original_parent)
            logic._three_d_view().scheduleRender()
        else:raise ValueError('unknown isolated fault injection')
        (OUT/'fault-ack.json').write_text(json.dumps({'id':value['id'],'kind':kind}),encoding='utf-8')
    fault_timer=qt.QTimer();fault_timer.timeout.connect(control);fault_timer.start(25)
    view=logic._three_d_view();view.resetCamera();view.forceRender()
    title='CStamp SOL — SYNTHETIC ONLY — '+OUT.name
    slicer.util.mainWindow().setWindowTitle(title)
    dock=qt.QDockWidget('Synthetic test controls',slicer.util.mainWindow())
    dock.setWidget(widget.parent);slicer.util.mainWindow().addDockWidget(qt.Qt.LeftDockWidgetArea,dock)
    widget.parent.show();dock.show()
    slicer.util.mainWindow().show();slicer.util.mainWindow().raise_();slicer.util.mainWindow().activateWindow()
    (OUT/'ready.json').write_text(json.dumps({'pid':os.getpid(),'port':PORT,'title':title,
         'runtime_manifest':actual,'fixture':'synthetic sphere only','source_sha256':hashlib.sha256(module_path.read_bytes()).hexdigest()}),encoding='utf-8')
    if os.environ.get('CSTAMP_TEST_MOUSE_OBSERVER')=='1':
        # Observation-only setup. Native UI actions still perform every operation.
        for name in ('PanelDockWidget','ErrorLogDockWidget','PythonConsoleDockWidget'):
            existing=slicer.util.mainWindow().findChild(qt.QDockWidget,name)
            if existing is not None:existing.hide()
        observer=Path(__file__).with_name('observe_fixture_mouse.py')
        exec(compile(observer.read_text(encoding='utf-8'),str(observer),'exec'),globals())
except Exception:
    (OUT/'startup-error.txt').write_text(traceback.format_exc(),encoding='utf-8')
