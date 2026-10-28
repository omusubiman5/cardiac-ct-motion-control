"""Slicer-native preparation from the fixed non-clinical master demo, in a NEW process.

This does not inspect or automatically register an arbitrary currently open scene.
The allowed source is docs/20 §対象表面, not an AI-observed current model.
"""
import hashlib
import importlib.util
import json
import os
import traceback
from pathlib import Path
import slicer
ROOT=Path(__file__).resolve().parents[1]
OUT=Path(os.environ['CSTAMP_TEST_DIR']).resolve()
if not OUT.is_relative_to(ROOT/'work'):raise RuntimeError('preparation output must be isolated')
OUT.mkdir(parents=True,exist_ok=True)
try:
    scene=(ROOT/'artifacts/slicer/CARTO3_EA_Map_Demo.mrb').resolve()
    if not slicer.util.loadScene(str(scene)):raise RuntimeError('master non-clinical demo failed to load')
    spec=importlib.util.spec_from_file_location('CStampPreparation',ROOT/'prototypes/slicer-cstamp/CStampModule.py')
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    logic=module.CStampModuleLogic()
    logic.surface_node=slicer.util.getNode(module.DEFAULT_SURFACE_NAME)
    logic.scene_reference=str(scene)
    observed=logic._observe_target_identity()
    targets={'schema_version':1,'targets':[{'target_id':'docs20-carto-nonclinical-demo',
              **{k:observed[k] for k in ('scene_id','scene_sha256','model_name','model_sha256','transform_sha256')},
              'registration_reference':'docs/20_implementation-plan.md §対象表面; fixed non-clinical demo and CARTOmesh_1-OG'}]}
    for name,value in [('targets-candidate.json',targets),('observed-slicer.json',
                       {'slicer_version':str(slicer.app.applicationVersion),'software_sha256':module._LOADED_SOURCE_HASHES})]:
        with (OUT/name).open('x',encoding='utf-8') as stream:json.dump(value,stream,ensure_ascii=False,indent=2)
    (OUT/'ready.json').write_text(json.dumps({'pid':os.getpid(),'fixture':'fixed master demo observation only',
                                             'source_sha256':hashlib.sha256((ROOT/'prototypes/slicer-cstamp/CStampModule.py').read_bytes()).hexdigest()}),encoding='utf-8')
    slicer.util.mainWindow().setWindowTitle('CStamp SOL — MASTER DEMO PREPARATION ONLY')
except Exception:
    (OUT/'startup-error.txt').write_text(traceback.format_exc(),encoding='utf-8')
