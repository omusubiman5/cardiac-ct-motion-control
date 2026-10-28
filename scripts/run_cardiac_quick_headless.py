import json
import os

import slicer


SCRIPT = r"C:\Projects\Cardiac-CT-Motion-Control\scripts\run_cardiac_quick_segmentation.py"
STATUS = r"C:\Projects\Cardiac-CT-Motion-Control\artifacts\research\cardiac-segmentation-status.json"

exit_code = 1
try:
    exec(open(SCRIPT, encoding="utf-8").read(), globals())
    with open(STATUS, encoding="utf-8") as stream:
        exit_code = 0 if json.load(stream).get("state") == "completed" else 1
finally:
    slicer.util.exit(exit_code)
