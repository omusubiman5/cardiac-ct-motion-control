"""Self-authored synthetic probes in actual Slicer, no patient data."""
import importlib.util,json,math,os,time,traceback,hashlib,copy,threading,socket
from pathlib import Path
import slicer,vtk,qt
OUT=Path(__file__).resolve().parent
ROOT=OUT.parents[1]
results={"input":"synthetic; not real-hand acceptance", "pid":os.getpid(),"tests":[]}
spec=importlib.util.spec_from_file_location('CStampModule',str(ROOT/'prototypes/slicer-cstamp/CStampModule.py'))
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)

def save():
    (OUT/'slicer-probe.json').write_text(json.dumps(results,ensure_ascii=False,indent=2,default=str),encoding='utf-8')
def record(ident,passed,observed):
    results['tests'].append({'id':ident,'status':'PASS' if passed else 'FAIL','observed':observed});save()
def rows(path):
    return [json.loads(l) for l in Path(path).read_text(encoding='utf-8').splitlines()] if Path(path).is_file() else []
def snapshot(logic):
    draft=logic.controller.draft
    return {'state':logic.controller.state.value,'frozen':logic.controller.frozen,'draft':str(draft),'ledger':rows(logic.ledger_path)}

def run():
  try:
    slicer.mrmlScene.Clear(0)
    slicer.app.layoutManager().setLayout(slicer.vtkMRMLLayoutNode.SlicerLayoutOneUp3DView)
    sphere=vtk.vtkSphereSource();sphere.SetRadius(30);sphere.SetThetaResolution(64);sphere.SetPhiResolution(64);sphere.Update()
    model=slicer.modules.models.logic().AddModel(sphere.GetOutput());model.SetName('FIELD-SyntheticSphere-RAS-mm')
    model.GetDisplayNode().SetColor(.75,.8,.9)
    view=slicer.app.layoutManager().threeDWidget(0).threeDView();view.resetCamera();view.forceRender();slicer.app.processEvents()
    logic=m.CStampModuleLogic();logic.surface_node=model
    logic.ledger_path=str(OUT/'events.jsonl');logic.plan_registry_path=str(OUT/'plans.jsonl')
    logic.start_command_server(18945)
    disp=logic.dispatcher
    session=disp.handle_line(json.dumps({'cmd':'hello','v':1}))['session']
    seq=0
    def command(cmd,params=None,**kw):
      nonlocal seq
      seq+=1
      data={'v':1,'session':session,'seq':seq,'req':f'probe-{seq}','ts':time.time(),'cmd':cmd,'params':params or {}}
      data.update(kw)
      return disp.handle_line(json.dumps(data))
    window=slicer.util.mainWindow();window.activateWindow();window.raise_();slicer.app.processEvents()
    results['foreground_ok']=logic.foreground_ok();results['slicer_version']=slicer.app.applicationVersion
    record('G-00-synthetic-scene',model.GetPolyData().GetNumberOfCells()>0,{'cells':model.GetPolyData().GetNumberOfCells(),'scene':'synthetic sphere','ledger':logic.ledger_path,'startup_armed':disp.armed})
    if not logic.foreground_ok():
      results['transport_blocker']='actual foreground gate rejected; no override';save();return
    record('X-03-arm',command('arm')['ok'],command('status'))
    camera=view.cameraNode().GetCamera();before=list(camera.GetPosition())
    rr=command('view_rotate',{'dx':10,'dy':5});view.forceRender()
    record('X-04-real-camera-rotate',rr['ok'] and before!=list(camera.GetPosition()),{'reply':rr,'before':before,'after':list(camera.GetPosition())})
    command('select_mode',{'mode':'aim'})
    rr=command('aim',{'nx':.5,'ny':.5})
    record('AC-009-synthetic-aim',rr.get('result',{}).get('valid') is True and not logic.has_draft(),rr)
    def stamp():
      command('select_mode',{'mode':'aim'});command('aim',{'nx':.5,'ny':.5});return command('stamp')
    rr=command('stamp');n=slicer.util.getNode(m.DRAFT_CURVE_NAME).GetNumberOfControlPoints()
    record('AC-001-synthetic-stamp',rr['ok'] and n==33 and len(rows(logic.ledger_path))==0,{'reply':rr,'points':n,'rows':len(rows(logic.ledger_path))})
    baseline=snapshot(logic);rr=command('stamp')
    record('AC-010-repeat-stamp',not rr['ok'] and snapshot(logic)==baseline,rr)
    for cmd,params in [('bogus',{}),('select_layer',{'layer':'PLANNED'}),('view_rotate',{'dx':'bad','dy':0})]:
      baseline=snapshot(logic);rr=command(cmd,params);record('X-03-'+cmd,not rr['ok'] and snapshot(logic)==baseline,rr)
    baseline=snapshot(logic);rr=command('commit',{},ts=time.time()-10);record('X-03-stale-time',not rr['ok'] and snapshot(logic)==baseline,rr)
    baseline=snapshot(logic);rr=command('commit',{},session='other');record('X-03-other-session',not rr['ok'] and snapshot(logic)==baseline,rr)
    command('select_mode',{'mode':'move'});before=logic.controller.draft.placement.anchor
    rr=command('move_draft',{'nx':.55,'ny':.5});after=logic.controller.draft.placement.anchor
    record('X-04-move',rr['ok'] and before!=after,{'before':before,'after':after,'reply':rr})
    baseline=snapshot(logic);rr=command('move_draft',{'nx':0,'ny':0});record('X-04-off-surface',not rr['ok'] and snapshot(logic)==baseline,rr)
    command('select_mode',{'mode':'rotate'});before=logic.controller.draft.placement.anchor
    stale_rev=logic.controller.draft.revision;rr=command('rotate_opening',{'delta_deg':10})
    record('AC-002-opening',rr['ok'] and logic.controller.draft.placement.anchor==before and not rows(logic.ledger_path),rr)
    baseline=snapshot(logic);rr=command('commit',{'rev':stale_rev});record('X-01-stale-revision',not rr['ok'] and snapshot(logic)==baseline,rr)
    command('select_mode',{'mode':'tilt'});before=logic.controller.draft.placement.anchor
    rr=command('tilt',{'delta_deg':5});record('X-04-tilt',rr['ok'] and logic.controller.draft.placement.anchor==before,rr)
    rr=command('reverse');record('X-04-reverse-API',rr['ok'],rr)
    rr=command('reset_dir');record('X-04-reset-API',rr['ok'],rr)
    before=logic.controller.draft;command('select_mode',{'mode':'view'});rr=command('zoom',{'ratio':1.1})
    record('AC-013-camera-only',rr['ok'] and logic.controller.draft==before and not rows(logic.ledger_path),rr)
    # Failure injection confined to a new test path. Existing shared permissions unchanged.
    original_path=logic.ledger_path
    (OUT/'not-a-directory').write_text('failure injection',encoding='utf-8')
    logic.ledger_path=str(OUT/'not-a-directory'/'events.jsonl');before=logic.controller.draft
    rr=command('commit',{'rev':before.revision})
    record('OP-011-write-failure',not rr['ok'] and logic.controller.draft==before and not rows(original_path),rr)
    logic.ledger_path=original_path
    rev=logic.controller.draft.revision;rr=command('commit',{'rev':rev});event_id=rr.get('event_id');commit_req=f'probe-{seq}'
    record('AC-003-internal-revision-only',rr['ok'] and len(rows(original_path))==1,{'reply':rr,'display_completion_proved':False})
    rr=command('commit',{'rev':rev});record('AC-005-repeat-commit',not rr['ok'] and len(rows(original_path))==1,rr)
    rr=command('query_result',{'req':commit_req});record('X-01-query-same-session',rr['ok'] and len(rows(original_path))==1,rr)
    # Additional records, use synthetic inputs only.
    for i in range(2):
      stamp();command('select_mode',{'mode':'rotate'});command('rotate_opening',{'delta_deg':5*(i+1)});command('commit',{'rev':logic.controller.draft.revision})
    events=rows(original_path);record('AC-017-three-records',len(events)==3 and len({e['event_id'] for e in events})==3,{'count':len(events),'orders':[e['order'] for e in events]})
    rr=logic.op_show_c({'event_id':event_id});record('AC-016-redisplay',rr['ok'] and logic._shape_node(event_id).GetDisplayVisibility(),rr)
    # Keep a rendered image of this synthetic scene only, no camera pixels.
    view.forceRender();w=vtk.vtkWindowToImageFilter();w.SetInput(view.renderWindow());w.Update()
    writer=vtk.vtkPNGWriter();writer.SetFileName(str(OUT/'synthetic-render.png'));writer.SetInputConnection(w.GetOutputPort());writer.Write()
    stamp();draft=logic.controller.draft;before_count=len(events);rr=command('cancel')
    record('AC-004-cancel',rr['ok'] and not logic.has_draft() and len(rows(original_path))==before_count,{'reply':rr,'state':logic.controller.state.value})
    stamp();before=logic.controller.draft;disp.on_disconnect();rr=command('rotate_opening',{'delta_deg':1})
    record('SR-008-disconnect-freeze',logic.controller.frozen and before==logic.controller.draft and not rr['ok'],rr)
    # Reconnect query must be durable per docs/23, explicitly observe actual behavior.
    session=disp.handle_line(json.dumps({'cmd':'hello','v':1}))['session'];seq=0;command('arm')
    rr=command('query_result',{'req':commit_req});record('X-01-query-after-reconnect',rr['ok'],rr)
    command('resume_draft');command('cancel')
    # Full ledger read-back and corruption behavior in a fresh scene.
    logic2=m.CStampModuleLogic();logic2.ledger_path=original_path
    slicer.mrmlScene.RemoveNode(slicer.util.getNode(m.PERFORMED_POINTS_NAME))
    for e in events:
      slicer.mrmlScene.RemoveNode(logic._shape_node(e['event_id']))
    restored=logic2.load_ledger(original_path);record('AC-008-reload-synthetic',restored==3 and logic2.load_ledger(original_path)==0,{'restored':restored,'ids':list(logic2._committed)})
    corrupt=copy.deepcopy(events[0]);corrupt['placement']['anchor'][0]+=100
    bad_path=OUT/'corrupt-events.jsonl';bad_path.write_text(json.dumps(corrupt)+'\n',encoding='utf-8')
    slicer.mrmlScene.Clear(0)
    badlogic=m.CStampModuleLogic()
    try: count=badlogic.load_ledger(str(bad_path));observed={'restored':count,'rejected':False}
    except Exception as exc: observed={'rejected':True,'error':repr(exc)}
    record('X-05-corrupt-ledger-rejection',observed['rejected'],observed)
    # New isolated ledger per case to avoid violating stop rule after discovered defects.
    audit=m.CStampModuleLogic();audit.ledger_path=str(OUT/'audit-events.jsonl');audit.plan_registry_path=str(OUT/'audit-plans.jsonl')
    audit.stamp_on_surface((0.,0.,30.),(0.,0.,1.),model)
    ev=audit.commit(audit.ledger_path);original=copy.deepcopy(ev)
    audit.op_select_reason({'reason':'visibility'});audit._selected_event_id=ev['event_id']
    rr=audit.op_revoke_event({});audit_rows=rows(audit.ledger_path)
    record('X-05-original-in-memory-immutable',audit._committed[ev['event_id']]==original,{'before_revoked':original['revoked'],'after_revoked':audit._committed[ev['event_id']]['revoked'],'reply':rr})
    record('H-09-synthetic-confirmation-order',len(audit_rows)==1,{'rows_before_confirm_audit':len(audit_rows),'types':[e.get('record_type') for e in audit_rows]})
    # Plan snapshot persistence and reason selection.
    plan=m.CStampModuleLogic();plan.ledger_path=str(OUT/'plan-events.jsonl');plan.plan_registry_path=str(OUT/'revision-events.jsonl')
    rr=plan.op_create_plan({'plan_id':'field-plan','items':[original],'creator':'test-operator'})
    plan.op_begin_plan_revision({'plan_id':'field-plan'})
    changed=copy.deepcopy(original['placement']);changed['anchor'][0]+=2
    plan.op_edit_plan_item({'plan_id':'field-plan','item_id':original['event_id'],'patch':{'placement':changed}})
    rr=plan.op_save_plan_revision({'plan_id':'field-plan'})
    record('X-05-plan-version-diff',rr['ok'] and bool(rr.get('result',{}).get('diff')),rr)
    fresh=m.CStampModuleLogic();fresh.plan_registry_path=plan.plan_registry_path
    record('X-05-plan-registry-reload',bool(fresh._plan_store.plans),{'fresh_plan_ids':list(fresh._plan_store.plans),'persisted_rows':len(rows(plan.plan_registry_path))})
    plan.plan_path=original_path;plan.load_plan(original_path)
    plan.op_select_reason({'reason':'visibility'});rr=plan.op_skip_plan({'reason':'operator'})
    skips=rows(plan.ledger_path);record('H-07-synthetic-selected-reason',skips[-1].get('reason')=='visibility',skips[-1])
    # Output actual menu inventory, not an assertion that hands can reach it.
    results['menu_no_draft']=[x['label'] for x in plan._menu_items()]
    results['menu_draft']=[x['label'] for x in logic._menu_items()]
    results['event_fields']=sorted(original);results['scene_fields']=original.get('scene')
    results['full_hand_acceptance']='NOT RUN'
    logic.stop_command_server()
  except Exception:
    results['fatal_error']=traceback.format_exc()
  finally:
    save();slicer.util.exit(0 if not results.get('fatal_error') else 1)
qt.QTimer.singleShot(2500,run)
