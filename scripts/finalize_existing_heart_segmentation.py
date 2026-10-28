import json
import os
import time
import traceback

import slicer
import vtk


PROJECT_DIR = r"C:\Projects\Cardiac-CT-Motion-Control"
OUTPUT_SCENE = os.path.join(PROJECT_DIR, "artifacts", "slicer", "Whole_Heart_Anatomy_Base.mrb")
STATUS_FILE = os.path.join(PROJECT_DIR, "artifacts", "research", "cardiac-segmentation-status.json")


def write_status(state, **details):
    with open(STATUS_FILE, "w", encoding="utf-8") as stream:
        json.dump(
            {
                "state": state,
                "model": "cardiac-3mm-v2.0.0",
                "outputScene": OUTPUT_SCENE,
                "time": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
                **details,
            },
            stream,
            ensure_ascii=False,
            indent=2,
        )


try:
    output = slicer.util.getNode("Whole heart anatomy (AI preview)")
    segmentation = output.GetSegmentation()
    segment_ids = vtk.vtkStringArray()
    segmentation.GetSegmentIDs(segment_ids)
    all_segments = [
        (segment_ids.GetValue(index), segmentation.GetSegment(segment_ids.GetValue(index)).GetName())
        for index in range(segment_ids.GetNumberOfValues())
    ]
    heart_ids = [segment_id for segment_id, name in all_segments if name.casefold() == "heart"]
    if len(heart_ids) != 1:
        raise RuntimeError(f"Expected exactly one heart segment, found: {all_segments}")

    heart_id = heart_ids[0]
    for segment_id, _ in all_segments:
        if segment_id != heart_id:
            segmentation.RemoveSegment(segment_id)

    heart = segmentation.GetSegment(heart_id)
    heart.SetName("Heart")
    heart.SetColor(0.78, 0.18, 0.18)
    output.CreateClosedSurfaceRepresentation()
    display = output.GetDisplayNode()
    display.SetVisibility(True)
    display.SetSegmentVisibility(heart_id, True)
    display.SetSegmentOpacity3D(heart_id, 1.0)

    for volume in slicer.util.getNodesByClass("vtkMRMLScalarVolumeNode"):
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
        sourceSegmentId=heart_id,
        sourceSegmentCount=len(all_segments),
        points=poly_data.GetNumberOfPoints() if poly_data else None,
        polygons=poly_data.GetNumberOfPolys() if poly_data else None,
        sceneBytes=os.path.getsize(OUTPUT_SCENE),
    )
except Exception as exc:
    write_status("failed-finalization", error=str(exc), traceback=traceback.format_exc())
    raise
