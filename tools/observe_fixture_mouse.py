"""Run natively in the isolated Slicer console. Read metadata only; never invoke operations."""
import hashlib,json,os,time
from pathlib import Path
import qt
from cstamp.state_machine import _placement_dict
from cstamp.ledger import EventLedger
root=Path(__file__).resolve().parents[1] if '__file__' in globals() else Path(r'C:\Projects\Cardiac-CT-Motion-Control')
# The synthetic bootstrap supplies OUT, PORT, logic and model in its native console.
out=Path(OUT).resolve()
assert out.is_relative_to(root/'work') and PORT!=18944
ready=json.loads((out/'ready.json').read_text(encoding='utf-8'))
assert ready['pid']==os.getpid() and ready['port']==PORT
mouse_rows=[]
mouse_seen_phase=[None]
def observe_mouse_phase():
    phase_path=out/'mouse-stage.txt'
    if not phase_path.exists():return
    phase=phase_path.read_text(encoding='utf-8-sig').strip()
    if phase==mouse_seen_phase[0]:return
    mouse_seen_phase[0]=phase
    draft=logic.controller.draft
    camera=logic._three_d_view().cameraNode().GetCamera()
    ledger=out/'events.jsonl'
    row={'phase':phase,'observed_ns':time.perf_counter_ns(),
         'draft_id':draft.draft_id if draft else None,'revision':draft.revision if draft else None,
         'placement':_placement_dict(draft.placement) if draft else None,
         'diameter_mm':logic.controller.draft_template.radius*2 if draft else None,
         'owner':logic.dispatcher.input_owner,'armed':logic.dispatcher.armed,'mode':logic.dispatcher.mode,
         'frozen':logic.controller.frozen,'displayed':logic.display_contract.displayed,
         'camera':{'position':camera.GetPosition(),'focal':camera.GetFocalPoint(),'up':camera.GetViewUp(),
                   'parallel':camera.GetParallelProjection(),'scale':camera.GetParallelScale(),'angle':camera.GetViewAngle()},
         'ledger_sha256':hashlib.sha256(ledger.read_bytes()).hexdigest() if ledger.exists() else None,
         'ledger_rows':len(EventLedger(ledger).events()),'model_node_id':model.GetID(),
         'restart_node_shift':bool(slicer.util.getNodes('node-ID-shift-only')),
         'camera_image_saved':False,'input':'native mouse UI actions; observer never dispatches operations'}
    mouse_rows.append(row)
    temporary=out/'mouse-observations.tmp'
    temporary.write_text(json.dumps(mouse_rows,ensure_ascii=False,indent=2),encoding='utf-8')
    temporary.replace(out/'mouse-observations.json')
    if phase=='complete':mouse_observer_timer.stop()
mouse_observer_timer=qt.QTimer()
mouse_observer_timer.timeout.connect(observe_mouse_phase)
mouse_observer_timer.start(100)
print('[synthetic mouse] metadata observer ready; no control was dispatched')
