---
artifact: adr
version: "1.0"
created: 2026-08-28
status: draft
---

# ADR-001: フェイルクローズ型モーションコントローラー境界

## Status

Proposed

**Date:** 2026-08-28  
**Deciders:** 未定（臨床責任者、医療安全、臨床工学、IT、開発のレビューが必要）

## Context

本プロジェクトは非臨床PoCであり、許可操作は取得済み心臓3Dモデルの回転、パン、ズーム、基準視点復帰候補、モーション入力の有効／無効に限る。起動時、認識不能、複数人、遮蔽、通信断、センサー異常、対象外ウィンドウでは何もしないことが要求されている。

既存PoCはOpenCV、MediaPipe Legacy Hands、PyAutoGUIを使い、映像取得、簡易姿勢分類、移動量変換、出力を実装している。しかし、状態は`enabled`真偽値が中心で、フレーム鮮度、異常ラッチ、再接続後の再アーミング、プロセス単位の対象固定、抑止理由の構造化が設計されていない。現在の対象判定は前面ウィンドウタイトルの部分一致であり、SR-006/R-004を満たす根拠として不十分である。

Pixel 9aはWindows接続カメラとしてDirectShowから1280×720フレームを取得できた。これは映像入力の成立を示すが、Pixel固有モーション機能、ジェスチャー設計、安全制御、出力方式の妥当性を示さない。また、公式MediaPipe資料ではLegacy Solutionsのサポート終了とTasks APIの利用メトリクス送信が記載されており、認識実装を交換可能にし、IT-001に対するネットワーク監査が必要である。

## Decision

私たちは、モーションコントローラーを単一プロセス内の分離されたパイプラインとして構成し、唯一の出力許可判断を`SafetyController`へ集約する設計を提案する。認識器または動作変換器からWindows入力APIを直接呼ぶことを禁止する。

```text
CameraSource
  -> Frame(timestamp, source_health)
  -> HandRecognizer
  -> Observation(hand_count, landmarks, confidence, timestamp)
  -> IntentClassifier
  -> IntentCandidate(kind, confidence, stability)
  -> MotionMapper
  -> ProposedAction(kind, dx/dy/amount)
  -> SafetyController(state, target, freshness, allowlist)
  -> OutputPort(Preview | WindowsViewControl)
  -> EventSink（非映像ログ）
```

### コンポーネント責務

| Component | Responsibility | Must not do |
|---|---|---|
| `CameraSource` | フレーム、単調増加時刻、入力健全性を返す | 映像保存、ジェスチャー判定 |
| `HandRecognizer` | 手数、ランドマーク、信頼度を返す | 操作種別決定、OS入力 |
| `IntentClassifier` | 許可候補または`NONE/AMBIGUOUS`を返す | 動作量生成、OS入力 |
| `MotionMapper` | 平滑化、デッドゾーン、速度制限後の候補量を返す | 出力許可判断 |
| `SafetyController` | 状態遷移、鮮度、単一手、対象、許可リストを一括評価 | 任意コマンド生成 |
| `OutputPort` | 型付き許可操作だけをプレビューまたは実行する | 対象選択、独自再試行 |
| `EventSink` | 状態、候補、量、許可／抑止理由を記録する | 映像、患者情報、画面画像の保存 |

### 状態機械

| State | Entry | Output |
|---|---|---|
| `DISABLED` | 起動、手動無効化、正常終了 | 常に禁止、保持入力を解放 |
| `READY` | 手動アーミング成功 | 禁止。単一手と安定観測を待つ |
| `TRACKING` | 単一手・許可候補・鮮度が連続して成立 | 初期基準を設定し、まだ出力しない |
| `EXECUTING` | 安定条件とデッドゾーン超過が成立 | SafetyControllerが許可した型付き操作だけ出力 |
| `FAULT` | カメラ異常、古いフレーム、出力例外、状態不整合 | 即時解放して禁止。自動復帰せず手動再アーミング必須 |

ジェスチャー変更、認識喪失、手数が1以外、対象ウィンドウ不一致では保持入力を解放し、`READY`へ戻す。カメラ再接続だけで`EXECUTING`へ復帰してはならない。安定時間、信頼度、鮮度、性能上限の数値は未決定であり、設定既定値を合格基準として扱わない。

### 安全不変条件

1. `real_input_enabled AND manually_armed AND state == EXECUTING AND target_exact_match`でない限り、実出力は0件である。
2. どの例外経路でも、保持中の仮想マウスボタンを解放する。
3. `hand_count != 1`、観測欠落、古いフレーム、`NONE/AMBIGUOUS`では新規出力しない。
4. 出力型は`ROTATE`、`PAN`、`ZOOM`、承認後の`RESET_VIEW`だけで、任意キー文字列を保持しない。
5. 対象判定はウィンドウタイトル部分一致だけに依存せず、承認済み実行ファイルIDとウィンドウIDを実行直前に確認する。
6. 映像、画面、患者情報を永続化しない。ログは非映像の数値・状態・理由コードに限定する。
7. Pixel/USBカメラの切替は`CameraSource`だけに影響し、認識・安全・出力規則を変更しない。

## Consequences

### Positive

- Pixel接続カメラとUSBカメラを、制御ロジックを変えずに比較できる。
- 誤認識と出力許可を別々に試験でき、要求・リスク・テストの追跡が可能になる。
- 出力層を`Preview`へ差し替えた状態で、実Windows入力なしに大部分を検証できる。
- 異常・認識喪失・対象逸脱の全経路で、同じ解放処理と抑止理由を適用できる。

### Negative

- 現在の小規模PoCよりクラスと契約試験が増える。
- プロセス／ウィンドウの厳密な対象固定は、対象ビューアごとのアダプター実装を必要とする。
- MediaPipe Legacy HandsからTasks APIまたは別認識器への移行可否を別途評価する必要がある。

### Neutral

- Pixel接続カメラは開発時のCameraSource候補であり、最終カメラ選定または臨床使用の承認を意味しない。
- 現行のジェスチャー割当ては提案のままであり、ユーザビリティ検証後に変わり得る。

## Alternatives Considered

### 既存PoCをそのまま拡張する

実装量は少ないが、`enabled`真偽値、タイトル部分一致、認識から出力までの密結合が残る。安全条件を一箇所で証明できないため採用しない。

### Pixel側で認識し、モーションイベントをPCへ送る

映像をPCへ渡さず端末側で処理できる可能性がある一方、Androidアプリ、通信プロトコル、認証、再接続、時刻同期、端末構成管理が新たに必要になる。現在の要求はローカルPCとカメラによるPoCであり、別ADRなしには採用しない。

### 完成済み仮想マウスOSSを流用する

MediaPipe/OpenCVの参考実装としては有用だが、多くはクリック、任意キー、汎用カーソル操作を含む。許可リストとフェイルクローズ状態を満たす保証がなく、製品コードの転用は行わない。アルゴリズムを参照する場合はライセンスとコード来歴を個別に記録する。

## References

- `README.md`
- `docs/01_scope-and-safety-boundary.md`
- `docs/03_system-requirements.md`
- `docs/10_motion-app-user-needs.md`
- `docs/11_motion-app-correction-policy.md`
- `docs/12_motion-app-execution-policy.md`
- `registers/risk-register.csv`
- `C:\Users\HOMEA\Documents\Downloads\motion\心臓3Dモデル_ジェスチャー視点操作_技術調査.md`
- [MediaPipe official repository](https://github.com/google-ai-edge/mediapipe)
- [OpenCV official repository](https://github.com/opencv/opencv)
- [PyAutoGUI official repository](https://github.com/asweigart/pyautogui)
- [Microsoft: Use your mobile device's camera](https://support.microsoft.com/en-US/Windows/Apps/PhoneLink/use-your-mobile-device-s-camera)
- `docs/15_adr-002-google-vision-stack.md`
- `docs/16_adr-003-windows-mouse-relay.md`
