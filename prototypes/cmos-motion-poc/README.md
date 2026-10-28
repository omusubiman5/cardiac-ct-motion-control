# CMOS Motion PoC

USB接続CMOSカメラで片手を認識し、取得済み心臓3Dモデルの回転・パン・ズームに相当する入力を生成する非臨床PoC。

## 操作割り当て

### Slicer接続モード（`--slicer-connect`、手だけの操作経路）

| 手形 | 用途 | 種別 |
|---|---|---|
| I Love You（🤟、受付停止中に1.5s保持） | 受付開始（arm） | ホールド |
| I Love You（🤟、受付中） | 画面上メニュー表示 ／ 凍結中: 仮Cの編集復帰 | 離散 |
| 親指上げ | メニュー中: 前の項目 ／ メニュー外: C呼出（照準モードへ） | 離散 |
| 親指下げ | メニュー中: 次の項目・戻る ／ 仮Cあり: 仮配置を取消 | 離散 |
| 握りこぶし | 決定 ／ 照準中: 仮配置 ／ 仮Cあり: 確認画面へ ／ 確認画面: 確定実行 | 離散 |
| 指3本 | 仮Cあり: 方向を初期値へ ／ メニュー外: 視点を初期化 | 離散 |
| 指2本 | 操作なし（認識はされる） | 離散 |
| 開いた手を移動 | カメラ回転 | 連続 |
| 人差し指だけ | カメラパン ／ 照準・仮Cの位置移動 | 連続 |
| ピンチ | 連続ズーム ／ 仮Cあり: 開口方向の調整 | 連続 |

離散ジェスチャーは保持時間`gesture_hold_s`を満たした立上りで1回だけ発火し、
同じ手形は`gesture_hold_s`以上の解放後に再受付する。短い認識途切れでは再発火しない。
実手では各手形を1秒ほど保持し、同じ操作を繰り返す前に手を1秒ほど下げる。
Slicer前面では日本語の操作パネルが手形・モード・メニュー選択を表示する。
受付停止はメニューの`disarm`から行う。
Space/Q/Escはキーボード代替として残る。

### マウス中継／プレビューモード

| ジェスチャー | 操作 |
|---|---|
| 開いた手を移動 | 回転 |
| 人差し指だけを伸ばして移動 | パン |
| 親指と人差し指を合わせ、手を上下 | ズーム |
| Space | モーション入力の有効／無効 |
| Q / Esc | 終了 |

送り、戻し、再生、停止は実装していない。

## セットアップ

PowerShellでこのフォルダへ移動して実行する。

```powershell
.\setup.ps1
```

## プレビュー起動

実際のマウス入力は送らず、カメラ映像上に操作量を表示する。

```powershell
.\run.ps1
```

別のカメラ番号を使う場合:

```powershell
.\run.ps1 -CameraIndex 1
```

## 既存3Dビューアへ入力する場合

`config.example.json` を `config.local.json` などの名前でコピーする。

### A. マウス中継（Windows SendInput）

`allowed_target_exes` に許可する対象実行ファイルの絶対パスを列挙する
（ウィンドウタイトルの部分一致は使わない）。

```powershell
.\run.ps1 -Config .\config.local.json -EnableInput
```

前面ウィンドウのプロセスが許可リストと一致しない限り入力は抑止され、
仮想マウスボタンも解放される。リストが空では実入力を開始できない。

### B. Slicer直接接続（localhostコマンドプロトコル）

`prototypes/slicer-cstamp` の C Stamp モジュールで「受付開始」を押すと
`127.0.0.1:<port>`（既定18944）で型付きコマンドを受け付ける。
PoC側は `--slicer-connect` で送信する。

```powershell
.\run.ps1 -Config .\config.local.json -SlicerConnect
```

プロトコルは `slicer-cstamp/command_protocol.py` に定義する封筒形式
（版・セッションID・要求ID・連番・時刻・TTL）で、まず `hello` で
セッションを取得してから `arm` で受付開始する。受理コマンドは
許可リスト（視点・照準・仮配置・編集・確定・取消・計画・メニュー・
照会）のみ。未知コマンド・古い時刻・別セッション・連番逆行・
要求ID再送は全て拒否応答を返し何も実行しない。切断時は受付停止＋
DRAFT凍結（取消しない）。手の開始は開いた手の長押し、停止は
画面上メニューの `disarm` から行う。

## アーキテクチャ

- `hand_landmarker.py` — MediaPipe Tasks Hand Landmarker（既定）
  + Legacy `mp.solutions.hands` フォールバック（`recognizer: "legacy"`）。
  Tasksモデルは `models/hand_landmarker.task` にピン留め（SHA-256記録済み）。
- `safety_controller.py` — 唯一の出力ゲート。
  DISABLED→READY→TRACKING→EXECUTING。手なし・複数手・古いフレーム・
  未分類ジェスチャー・低信頼度は全て解放付きでREADYへ降格。
  カメラ断はFAULTラッチ（手動再アーム必須）。
- `motion_engine.py` — 決定論的ジェスチャー分類と操作量算出。
- `gesture_fsm.py` — 手形分類（OPEN_PALM/POINT/TWO/THREE/FIST/THUMB/
  PINCH/UNKNOWN）と離散エッジ・ホールド検出（`GestureLatch`/
  `HoldDetector`）。
- `zoom_engine.py` — 連続ズーム（不感帯・加速度制限・解放時減衰）。
- `target_guard.py` — 前面ウィンドウのプロセス実行パス照合。
- `mouse_relay.py` — SendInputマウス専用輸送（キーボードAPIなし）。
- `session_client.py` — 型付きコマンドプロトコルの封筒クライアント
  （hello/seq/req/ts、応答受領、輸送断でフェイルクローズ）。
- `op_controller.py` — 手形＋サーバ状態→コマンド写像。
  モード別の連続入力と離散ジェスチャーを結合。
- `slicer_bridge.py` — 旧来の視点3コマンド輸送（loopback限定）。
  新プロトコル経路ではsession_clientを使用。
- `input_bridge.py` — 旧pyautogui経路（タイトル部分一致）。新規実行経路では
  不使用。後方互換のため残置。

## テスト

```powershell
.\.venv\Scripts\python.exe -m pytest -q
```

## 現在の制約

- 片手のみを受け付ける。複数の手を検出した場合は入力しない。
- 指の上下関係による簡単な姿勢分類なので、手の大きな回転には弱い。
- カメラ映像は保存しない。
- 実カメラ、照明、手袋、対象3Dビューアでの調整は未実施。
- PoCであり臨床使用を意図しない。

