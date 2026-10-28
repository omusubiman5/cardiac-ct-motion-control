import importlib.util,json,os,socket,threading,time,traceback,ctypes
from pathlib import Path
import slicer,qt
OUT=Path(__file__).parent
ROOT=Path(r'C:\Projects\Cardiac-CT-Motion-Control')
result={'input':'synthetic TCP, no hand and no editing commands','pid':os.getpid(),'responses':[]}
spec=importlib.util.spec_from_file_location('CStampModule',str(ROOT/'prototypes/slicer-cstamp/CStampModule.py'));module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
logic=module.CStampModuleLogic();logic.ledger_path=str(OUT/'tcp-unused-events.jsonl');logic.plan_registry_path=str(OUT/'tcp-unused-plans.jsonl');logic.start_command_server(18945)

def client():
 try:
  with socket.create_connection(('127.0.0.1',18945),3) as sock:
   sock.settimeout(3);stream=sock.makefile('rwb')
   def send(d):
    stream.write((json.dumps(d)+'\n').encode());stream.flush();r=json.loads(stream.readline());result['responses'].append({'command':d['cmd'],'response':r});return r
   hello=send({'cmd':'hello','v':1});session=hello['session']
   for i,(cmd,params) in enumerate([('status',{}),('view_rotate',{'dx':1,'dy':0}),('arm',{}),('status',{}),('disarm',{})],1):
    send({'cmd':cmd,'v':1,'session':session,'seq':i,'req':f'tcp-{i}','ts':time.time(),'params':params})
 except Exception: result['error']=traceback.format_exc()

def run():
 try:
  from ctypes import wintypes
  adv=ctypes.windll.advapi32;kernel=ctypes.windll.kernel32
  kernel.GetCurrentProcess.restype=wintypes.HANDLE
  adv.OpenProcessToken.argtypes=[wintypes.HANDLE,wintypes.DWORD,ctypes.POINTER(wintypes.HANDLE)]
  token=wintypes.HANDLE();elev=wintypes.DWORD();needed=wintypes.DWORD()
  if adv.OpenProcessToken(kernel.GetCurrentProcess(),8,ctypes.byref(token)):
   adv.GetTokenInformation(token,20,ctypes.byref(elev),ctypes.sizeof(elev),ctypes.byref(needed));result['process_token_elevated']=bool(elev.value);kernel.CloseHandle(token)
  t=threading.Thread(target=client);t.start();deadline=time.monotonic()+15
  while t.is_alive() and time.monotonic()<deadline: slicer.app.processEvents();time.sleep(.01)
  result['thread_finished']=not t.is_alive();result['armed_after']=logic.dispatcher.armed
  result['ledger_created']=Path(logic.ledger_path).exists()
  rs=result['responses'];result['ok']=len(rs)==6 and rs[0]['response']['ok'] and not rs[2]['response']['ok'] and rs[-1]['response']['ok'] and not result['armed_after'] and not result['ledger_created']
 except Exception: result['fatal']=traceback.format_exc()
 finally:
  (OUT/'tcp-result.json').write_text(json.dumps(result,indent=2),encoding='utf-8');logic.stop_command_server();slicer.util.exit(0)
qt.QTimer.singleShot(1500,run)
