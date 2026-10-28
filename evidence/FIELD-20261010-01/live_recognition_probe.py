import sys,time,json,collections
from pathlib import Path
ROOT=Path(r'C:\Projects\Cardiac-CT-Motion-Control')
sys.path.insert(0,str(ROOT/'prototypes/cmos-motion-poc'))
import cv2
from hand_landmarker import TasksHandRecognizer
from gesture_fsm import classify_shape
out=Path(__file__).parent
cap=cv2.VideoCapture(0,cv2.CAP_DSHOW);recognizer=None
counts=collections.Counter();shapes=collections.Counter();samples=[];frames=0
start=time.monotonic();last=0;result={'camera_index':0,'source_identity':'index0; physical Pixel attribution not independently proven','no_control_connection':True,'no_image_saved':True}
try:
 recognizer=TasksHandRecognizer(str(ROOT/'prototypes/cmos-motion-poc/models/hand_landmarker.task'),min_detection_confidence=.65,min_tracking_confidence=.65)
 while time.monotonic()-start<30:
  ok,frame=cap.read()
  if not ok: result['read_error']=True;break
  frame=cv2.flip(frame,1)
  now=time.monotonic();obs=recognizer.recognize(cv2.cvtColor(frame,cv2.COLOR_BGR2RGB),now)
  frames+=1;counts[str(obs.hand_count)]+=1
  shape=classify_shape(obs.landmarks,.055,.45).value if obs.landmarks else 'NONE'
  shapes[shape]+=1
  if now-last>=1:
   samples.append({'elapsed_s':round(now-start,2),'hands':obs.hand_count,'shape':shape,'confidence':round(obs.confidence,3)})
   print(json.dumps(samples[-1]),flush=True);last=now
except Exception as e: result['error']=repr(e)
finally:
 cap.release()
 if recognizer: recognizer.close()
 result.update({'frames':frames,'duration_s':time.monotonic()-start,'hand_count_frames':dict(counts),'shape_frames':dict(shapes),'samples':samples,'intended_gesture_trial_labels':None,'recognition_accuracy':'not calculated; no synchronized operator intent labels'})
 (out/'live-recognition.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
 print(json.dumps({k:v for k,v in result.items() if k!='samples'}),flush=True)
