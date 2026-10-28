import json
import os
import time
import traceback

import slicer
import vtk

from MONAIAuto3DSeg import MONAIAuto3DSegLogic


PROJECT_DIR = r"C:\Projects\Cardiac-CT-Motion-Control"
INPUT_VOLUME = r"C:\Users\HOMEA\AppData\Local\slicer.org\Slicer\cache\SlicerIO\CTA-cardio.nrrd"
OUTPUT_SCENE = os.path.join(PROJECT_DIR, "artifacts", "slicer", "Whole_Heart_Anatomy_Base.mrb")
STATUS_FILE = os.path.join(PROJECT_DIR, "artifacts", "research", "cardiac-segmentation-status.json")
MODEL_ID = "cardiac-3mm-v2.0.0"


def write_status(state, **details):
    payload = {
        "state": state,
        "model": MODEL_ID,
        "input": INPUT_VOLUME,
        "outputScene": OUTPUT_SCENE,
        "time": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        **details,
    }
    os.makedirs(os.path.dirname(STATUS_FILE), exist_ok=True)
    with open(STATUS_FILE, "w", encoding="utf-8") as stream:
        json.dump(payload, stream, ensure_ascii=False, indent=2)


write_status("started")

try:
    slicer.mrmlScene.Clear(0)
    volume = slicer.util.loadVolume(INPUT_VOLUME)
    if volume is None:
        raise RuntimeError("CTACardio volume could not be loaded")

    output = slicer.mrmlScene.AddNewNodeByClass(
        "vtkMRMLSegmentationNode", "Whole heart anatomy (AI preview)"
    )
    logic = MONAIAuto3DSegLogic()
    logic.autoShow3D = True

    write_status("running-inference", volumeName=volume.GetName())
    result = logic.process(
        [volume],
        output,
        model=MODEL_ID,
        cpu=True,
        waitForCompletion=True,
    )

    segmentation = output.GetSegmentation()
    segment_ids = vtk.vtkStringArray()
    segmentation.GetSegmentIDs(segment_ids)
    all_segments = [
        (segment_ids.GetValue(index), segmentation.GetSegment(segment_ids.GetValue(index)).GetName())
        for index in range(segment_ids.GetNumberOfValues())
    ]
    heart_ids = [segment_id for segment_id, name in all_segments if name.casefold() == "heart"]
    if len(heart_ids) != 1:
        raise RuntimeError(f"Expected exactly one Heart segment, found: {all_segments}")

    heart_id = heart_ids[0]
    for segment_id, _ in all_segments:
        if segment_id != heart_id:
            segmentation.RemoveSegment(segment_id)

    output.CreateClosedSurfaceRepresentation()
    display = output.GetDisplayNode()
    display.SetVisibility(True)
    display.SetSegmentVisibility(heart_id, True)
    display.SetSegmentOpacity3D(heart_id, 1.0)
    segmentation.GetSegment(heart_id).SetColor(0.78, 0.18, 0.18)
    volume.SetDisplayVisibility(False)

    layout_manager = slicer.app.layoutManager()
    if layout_manager is not None:
        layout_manager.setLayout(slicer.vtkMRMLLayoutNode.SlicerLayoutOneUp3DView)
        slicer.util.resetThreeDViews()

    os.makedirs(os.path.dirname(OUTPUT_SCENE), exist_ok=True)
    if not slicer.util.saveScene(OUTPUT_SCENE):
        raise RuntimeError("Failed to save output scene")

    poly_data = output.GetClosedSurfaceInternalRepresentation(heart_id)
    write_status(
        "completed",
        segmentName="Heart",
        points=poly_data.GetNumberOfPoints() if poly_data else None,
        polygons=poly_data.GetNumberOfPolys() if poly_data else None,
        sceneBytes=os.path.getsize(OUTPUT_SCENE),
    )
except Exception as exc:
    write_status("failed", error=str(exc), traceback=traceback.format_exc())
    raise
