---
artifact: adr
version: "1.0"
created: 2026-08-28
status: accepted
---

# ADR-002: PixelとMediaPipe Tasksによる認識基盤

## 2026-10-12 本人指示による方針更新

本人原文「MediaPipe標準のジェスチャー分類を使わないと安定しない」を受け、グー／親指は標準Gesture Recognizerの採用へ方針変更。まず操作出力なしの実カメラ比較へ実装し、標準分類名とgesture scoreを表示する。以下の標準分類不採用の決定は当初の設計履歴であり、今回の方針を妨げる承認条件としない。同期VIDEO、ローカル固定モデル、曖昧時無作用、通常操作手段の維持は継続。正常な1〜3本の回帰と標準にない3本指の扱い、分類スコアから操作への判定条件を検証してから通常制御へ接続する。比較導入と通常操作への反映を混同しない。

## Status

Accepted（非臨床PoCに限定。臨床使用の承認ではない）

**Date:** 2026-08-28  
**Deciders:** ユーザー、開発担当（安全・IT・臨床関係者の承認は未取得）

## Context

Pixel 9aはWindows 11の接続カメラとして有効化され、OpenCV DirectShowの`camera_index=0`から1280×720フレームを取得できた。既存PoCはGoogle MediaPipeのLegacy Hands APIを使用しているが、公式リポジトリはLegacy Solutionsをサポート終了・as-is提供としている。

入力機器と認識器を同じGoogle系に寄せることで、Pixelのカメラ品質とMediaPipeの手ランドマーク認識を利用できる。ただし、Pixel映像をWindowsアプリへ渡す経路はMicrosoftの接続カメラ機能であり、Windowsへの表示操作出力もGoogle製品ではない。「Googleシリーズで揃える」の対象は、センサー端末と視覚認識の中核に限定する必要がある。

## Decision

私たちは、PoCの標準視覚認識構成として次を採用する。

```text
Google Pixel 9a camera
  -> Microsoft Windows Connected Camera
  -> OpenCV DirectShow CameraSource（薄い取得アダプター）
  -> Google MediaPipe Tasks Hand Landmarker / VIDEO mode
  -> project-owned deterministic IntentClassifier
  -> ADR-001 SafetyController
  -> PreviewPort または承認済みWindowsViewControlPort
```

認識APIは`mp.solutions.hands`から`mediapipe.tasks.python.vision.HandLandmarker`へ移行する。実行モードは、同一制御ループ内で結果とフレーム時刻を対応付けられる同期`VIDEO`モードを使用する。非同期`LIVE_STREAM`モードは、結果の遅延・順序・廃棄を追加設計するまで採用しない。

Googleの標準Gesture Recognizerが返すカテゴリを直接操作へ割り当てない。Hand Landmarkerの21点ランドマークを入力に、プロジェクト所有の決定論的`IntentClassifier`が`ROTATE/PAN/ZOOM/NONE/AMBIGUOUS`候補を生成する。これにより、許可操作と曖昧時無入力をコードとテストで固定する。

`hand_landmarker.task`は実行時にダウンロードせず、承認した版をローカル資産として固定し、出所、バージョン、SHA-256、ライセンスをSBOMと構成記録へ残す。映像は保存しない。MediaPipeの通信挙動はIT-001に対するネットワーク監査が完了するまで未確認とし、PoC実行時は不要な外向き通信を許可しない。

## Consequences

### Positive

- Pixelから手ランドマークまでの主要視覚系をGoogleの現行MediaPipe Tasksへ統一できる。
- 21点ランドマークと時刻を明示した契約により、認識器と安全制御を独立試験できる。
- 同期VIDEOモードにより、非同期コールバック由来の古い結果を出力する危険を避けられる。
- CameraSourceを交換可能に保つため、PixelからUSBカメラへ変更しても認識・安全設計を維持できる。

### Negative

- Legacy HandsからTasks APIへのアダプター実装と回帰試験が必要になる。
- モデル資産の取得、ハッシュ固定、SBOM、ライセンス、ネットワーク監査が必要になる。
- Windows接続カメラとOpenCV/DirectShowはGoogle製ではなく、完全な単一ベンダースタックにはならない。
- Pixel接続状態やPhone Link更新が映像入力の可用性へ影響する。

### Neutral

- PixelのIMU、加速度、ジャイロ、端末側モーションAPIはこの決定に含めない。
- ジェスチャー閾値、安定時間、性能合格値はこのADRでは決定しない。

### Model Choice

| Consequence | This decision |
|-------------|---------------|
| **Build, buy, or prompt** | Google提供のローカル実行用`hand_landmarker.task`を利用する。独自学習は評価データと承認済み学習手順がなく、クラウドAPIはIT-001とオフライン要求に合わないため選ばない。 |
| **What is now coupled to it** | 21点ランドマーク順序、handedness、MediaPipe Tasks Python API、モデル入力仕様、評価データ、遅延予算。 |
| **Operating cost accepted** | PC上のローカルCPU負荷とモデル配布・構成管理。許容上限は性能要求確定後に測定する。 |
| **Reversal cost** | `HandRecognizer`アダプターと認識回帰試験の差替え。IntentClassifier以降は21点観測契約を維持できれば変更不要。 |
| **What would reopen this** | 合意済み照明・手袋・距離条件で認識率または遅延要求を満たさない、必要なオフライン／無通信条件を保証できない、または対応Python/Windows構成が維持できない場合。 |

## Alternatives Considered

### MediaPipe Legacy Handsを継続する

既存コード変更は最小だが、公式サポート終了後のLegacy APIへ設計を固定するため採用しない。

### MediaPipe Gesture Recognizerのカテゴリを直接操作へ割り当てる

実装は短くなるが、必要な`PINCH`などの操作候補、曖昧判定、プロジェクト固有の許可リストを標準カテゴリだけで保証できない。Landmarker出力を決定論的に分類する方式を選ぶ。

### Pixel端末内で認識してイベントだけを送信する

Google系でより統一できるが、Androidアプリ、通信認証、再接続、時刻同期、端末配布が追加される。現PoCの最小経路では採用せず、必要性が証拠化された場合に別ADRで評価する。

## References

- `docs/14_adr-001-fail-closed-motion-controller.md`
- `docs/10_motion-app-user-needs.md`
- `docs/12_motion-app-execution-policy.md`
- [MediaPipe official repository](https://github.com/google-ai-edge/mediapipe)
- [MediaPipe official Hand Landmarker Python implementation](https://github.com/google-ai-edge/mediapipe/blob/master/mediapipe/tasks/python/vision/hand_landmarker.py)
- [MediaPipe official samples](https://github.com/google-ai-edge/mediapipe-samples)
- [Microsoft: Use your mobile device's camera](https://support.microsoft.com/en-US/Windows/Apps/PhoneLink/use-your-mobile-device-s-camera)
