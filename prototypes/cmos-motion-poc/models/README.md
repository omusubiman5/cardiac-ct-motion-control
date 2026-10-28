# Pinned model assets

## Standard gesture comparison (2026-10-12)

- `gesture_recognizer.task`: official float16 version 1, 8,373,440 bytes.
- Source: https://storage.googleapis.com/mediapipe-models/gesture_recognizer/gesture_recognizer/float16/1/gesture_recognizer.task
- Canonical SHA-256: `97952348cf6a6a4915c2ea1496b4b37ebabc50cbbf80571435643c455f2b0482`.
- Downloaded at setup for local standard-gesture comparison; no runtime download. Not activated in the normal Slicer dispatcher.

| File | Source | SHA-256 |
|------|--------|---------|
| `hand_landmarker.task` | MediaPipe Tasks model (float16, v1) — `https://storage.googleapis.com/mediapipe-models/hand_landmarker/hand_landmarker/float16/1/hand_landmarker.task` | `fbc2a30080c3c557093b5ddfc334698132eb341044ccee322ccf8bcf3607cde1` |

- 7,819,105 bytes. Fetched once at setup; never downloaded at runtime.
- `TasksHandRecognizer` requires this file. If absent the app exits with
  a clear error (exit code 6) instead of silently falling back.
- To re-pin a different model revision, replace the file and record the
  new SHA-256 here.
