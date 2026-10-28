# Slicer C-Stamp PoC

3D Slicer上で、Cスタンプの仮配置・方向調整・確定・取消を行う非臨床プロトタイプ。操作経路は通常マウスと、型付きコマンドプロトコル経由のハンドモーション入力の2系統。`docs/03`の状態機械（`IDLE`/`DRAFT`/`COMMITTED`/`CANCELLED`）に従い、確定イベントを原データと分離したJSONL台帳へ保存する。臨床使用を意図しない。

## 構成

- `cstamp/` — 3D Slicerに依存しない純粋Pythonコア
  - `state_machine.py` — Cスタンプ状態機械（スタンプ・方向調整・`move_draft`配置後移動・確定・取消・認識喪失時凍結・`seed_draft`訂正・`draft_revision`版束縛確定）
  - `template.py` — Cテンプレート（半径・開口角・分割数）とSHA-256
  - `placement.py` — アンカー・配置面基底・面内回転・開口方向・進行方向・3x4変換
  - `ledger.py` — 追加専用JSONLイベント台帳（順序・改変検出ハッシュ）
  - `surface_aim.py` — 純粋Pythonの光線三角形交差（テスト用）
  - `plan.py` — `PlanTracker`（計画順序・照合・スキップ・順序変更・計画外記録）
  - `plan_revision.py` — `PlanStore`（計画版管理。create/begin_revision/edit/add/delete/move_item/save/cancel・承認版不変・差分記録）
  - `geometry.py` — ベクトル・回転・決定的配置面基底
- `command_protocol.py` — 型付きコマンド封筒の検証・ディスパッチャ（hello/seq/req/ts/TTL、dedup、ARM/モード/レイヤー/DRAFTゲート、切断時凍結）。許可リスト外の入力は全て無効
- `CStampModule.py` — 3D Slicer Scripted Module（UI・MRML表示・loopback限定コマンドサーバ）
- `tests/` — Slicer外で実行可能な単体試験
- `headless_verify.py` / `headless_module_verify.py` / `gui_verify.py` — 実メッシュ・実ウィンドウ検証

## 操作

### マウス（操作パネル）

1. 検証シーン `artifacts/slicer/CARTO3_EA_Map_Demo.mrb` を開く。
2. 対象表面に `CARTOmesh_1-OG` を選択。
3. 「照準→スタンプ」後に3Dビューで表面をクリックすると`DRAFT`が1件仮配置される。
4. 開口角スライダー（連続）・「傾斜 ±15°」「進行反転」「方向リセット」で方向調整（アンカー不変）。
5. 「確定」で確定ログ1件と確定点（赤）を生成。「取消」で仮配置を破棄。

### ハンドモーション（`127.0.0.1`限定コマンドサーバ経由）

`start_server_session.py`でシーン読込とサーバ（既定`18944`）を起動し、`cmos-motion-poc`を`--slicer-connect`で接続する。開いた手1.5秒保持で受付開始。モード（view/aim/move/rotate/tilt/review）内でジェスチャーが連続入力、親指＝メニュー、2指＝スタンプ等、3指＝確定、拳＝取消。手なし・複数手・曖昧入力は無操作、切断はdisarm＋DRAFT凍結。詳細は`cmos-motion-poc/README.md`。

## データ境界

- 元CT／モデル／既存確定ログを変更しない。表示はオーバーレイだけ。
- 確定点は簡略表示であり、イベント本体はC全体の形状・位置・姿勢・方向を保持する。選択した確定点から読み取り専用でC全体を再構成できる。
- 台帳は既定で `artifacts/cstamp/events.jsonl`。追記のみで上書きしない。訂正は`correction_of`を持つ新イベントとして記録する。
- `PLANNED`（緑）と`PERFORMED`（赤）レイヤーを分離。計画の自動確定化はしない。

## テスト

```powershell
<venv>\python.exe -m pytest -q
```

単体試験131件。Slicer実機検証:

```powershell
Slicer.exe --no-main-window --python-script headless_module_verify.py   # ヘッドレス
Slicer.exe --python-script gui_verify.py                                # GUI（合成イベント）
```

## 現在の制約

- 実手での全操作検証（H-01〜12）は未実施。ジェスチャー分類は合成ランドマーク試験のみ。
- 計画版管理（create_plan/begin_plan_revision/edit_plan_item/delete_plan_item/move_plan_item/save_plan_revision等）と監査コマンド（select_reason/set_out_of_plan/revoke_event/confirm_audit）はプロトコル経路で実装・E2E検証済み。画面上メニュー項目化は未実装。
- 傾斜の連続ドラッグは未実装（連続調整はプロトコル経由の`tilt`）。
- 実操作性能値（遅延・認識率）は未計測。
- 前面ウィンドウ監視（Slicerが前面でない間は編集・視点コマンドを拒否）は実装済み・実機双方向確認済み。
