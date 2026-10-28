# Cardiac Motion Control

ハンドジェスチャーで3D Slicer上の心臓モデルを操作し、表面にC字の焼き印（C-stamp）を計画・確定する**非臨床プロトタイプ**です。

> ⚠️ 本ソフトウェアは研究・デモ専用です。診断・治療・手術計画などの臨床用途には使用できません。患者情報・DICOM・術中映像・音声は保存・外部送信しません。

## 概要

| 構成 | 役割 |
|---|---|
| 認識プロセス（`prototypes/cmos-motion-poc`） | UVCカメラ（Pixel等）→ MediaPipe手形認識 → ジェスチャー→コマンド変換 → Slicerへ送信 |
| Slicerモジュール（`prototypes/slicer-cstamp`） | コマンドサーバ（127.0.0.1:18944）→ ゲート検証 → 3Dビュー操作・C-stamp管理・監査記録 |
| リリース（`artifacts/releases/`） | 署名済み不変ペイロード。`current-release.json` が有効版を指す |

- 対象シーンは固定デモ `artifacts/slicer/CARTO3_EA_Map_Demo.mrb`（CARTOメッシュ、非臨床）
- 入力権はマウスがデフォルト所有。ハンド入力は `claim_input` で明示的に取得し、マウスへのフォールバックを常時保持

## 起動

デスクトップショートカット **「Cardiac Motion Control（最新）」** から起動（署名済みリリースの `start_completion_release.ps1` を実行）。

手動起動：

```powershell
powershell -ExecutionPolicy Bypass -File "<release>/start_completion_release.ps1" `
  -ReleaseRoot "<release>" `
  -SlicerExecutable "C:\Users\HOMEA\AppData\Local\slicer.org\3D Slicer 5.12.3\Slicer.exe" `
  -CameraIndex 0
```

起動時にペイロードhash・依存インベントリ・ランタイム設定の整合を検証し、Slicer・認識プロセスを立ち上げて `connected=True` を確認します。

## 手形操作（1手形1意味）

| 手形 | 動作 |
|---|---|
| 🤟 I Love You | 停止中: 1.5秒保持で受付開始 ／ 受付中: メニュー表示 ／ 凍結中: 編集復帰 |
| 親指上げ | メニュー: 前の項目 ／ メニュー外: C呼出（照準モード） |
| 親指下げ | メニュー: 次の項目・戻る ／ 仮Cあり: 取消 |
| グー | 決定 ／ 照準中: 仮配置 ／ 仮Cあり: 確認画面 ／ 確認画面: 確定実行 |
| 3本指 | 仮C: 方向初期化 ／ メニュー外: 視点リセット |
| 開いた手 | 視点回転 |
| 人差し指 | パン／照準移動／仮C移動 |
| つまみ | ズーム／仮Cの開口方向調整 |
| 2本指・手なし・不明・複数手・低信頼 | 無操作（フェイルクローズ） |

### C確定の流れ

`🤟(1.5s)` → `親指上`（C呼出）→ `人差し指`（照準）→ `グー`（仮配置）→ 調整 → `グー`（確認画面）→ **手を開いてもう一度グー**（確定）

詳細は `docs/59_c-stamp-operation-scenario-20261026.md` を参照。

## 安全設計

- **フェイルクローズ**: 認識不可・低信頼・複数手は全て無操作。モデルのトップ判定と独立幾何検証の2重チェック
- **明示確認**: 確定は確認画面＋グーの再提示エッジが必須（握りっぱなしでは発火しない）
- **displayed束縛**: commitは画面に表示した draft_id/rev/hash を束縛し、陳腐スナップショットをサーバが拒否（ONI-001）
- **凍結**: 認識喪失が猶予期間を超えると仮Cを凍結。解除は🤟（resume_draft）または取消のみ
- **サーバゲート**: session所有・seq単調・req重複排除・タイムスタンプ窓・前面検査・対象同一性・runtime manifest hash
- **監査**: 全コマンドを `work/runs/*/commands.jsonl`、確定イベントを `artifacts/cstamp/events-*.jsonl`（append-only・integrity hash）へ記録
- **完全性**: リリースは署名済みカタログ＋manifest hashで検証。改変コードでは起動・握手しない

## 認識の補足

MediaPipe手形スコアが閾値（0.65）未満でも、モデルのトップ判定と一致する決定論的ランドマーク幾何が確認できれば受理します（実カメラでのスコア分布対策）。モデルと幾何が食い違う場合は従来どおり拒否。

## リリース手順

```bash
# 1. artifacts/cstamp/runtime.json の software_sha256 を変更ファイル分だけ再固定
# 2. SBOM再生成
python tools/generate_sbom.py
# 3. ステージング（プロジェクトvenvのpythonで実行すること）
prototypes/cmos-motion-poc/.venv/Scripts/python.exe tools/prepare_completion_release.py \
  --slicer-executable "C:/Users/HOMEA/AppData/Local/slicer.org/3D Slicer 5.12.3/Slicer.exe"
# 4. activate/start/entry-point3点を CStampPoC-Dev 証明書で署名
# 5. 全プロセス停止 → activate_completion_release.ps1 → start_completion_release.ps1
```

## テスト

```bash
cd prototypes/cmos-motion-poc && python -m pytest tests   # 2293件
```

## ディレクトリ

```
prototypes/cmos-motion-poc/   認識プロセス（app.py / gesture_fsm / standard_gesture / op_controller …）
prototypes/slicer-cstamp/     Slicerモジュール（CStampModule.py / unified_hand_panel.py / cstamp/ …）
artifacts/cstamp/             runtime設定・対象レジストリ・監査イベント
artifacts/releases/           署名済みリリースと current-release.json
artifacts/slicer/             デモシーン（MRB）
tools/                        リリース・検証スクリプト
docs/                         仕様・計画・運用記録（docs/59 = 操作シナリオ）
PROJECT_STATUS.md             作業履歴と既知事項
```

## 既知の制約

- 凍結中にグーを出すと確認ページが開くがcommitは拒否される（ガイドで🤟解除を案内）
- 凍結状態のクライアント反映は最大約1秒遅延
- マウス等ローカル操作の拒否はcommands.jsonlに記録されない
- 前提: Windows・PowerShell 5.1・Slicer 5.12.3・Python 3.12（venv同梱）・カメラindex 0（PixelはUVCモード `adb shell svc usb setFunctions uvc`）
