import cv2,json,time
from pathlib import Path
results=[]
for index in range(3):
 t=time.monotonic();cap=cv2.VideoCapture(index,cv2.CAP_DSHOW)
 opened=cap.isOpened();ok=False;shape=None
 if opened:
  ok,frame=cap.read()
  if ok: shape=list(frame.shape)
 cap.release()
 results.append({'index':index,'backend':'dshow','opened':opened,'frame_received':bool(ok),'shape':shape,'elapsed_s':time.monotonic()-t})
Path(__file__).with_name('camera-probe.json').write_text(json.dumps(results,indent=2),encoding='utf-8')
print(json.dumps(results))
