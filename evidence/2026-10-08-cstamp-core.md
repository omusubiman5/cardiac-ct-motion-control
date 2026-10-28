# Cスタンプ・コア実装の検証記録（非臨床）

日付: 2026-10-08
対象: `prototypes/slicer-cstamp`

## 範囲

- 純粋Pythonコア（`cstamp`）の合成入力単体試験
- 保存済み非臨床シーン `artifacts/slicer/CARTO3_EA_Map_Demo.mrb` の `CARTOmesh_1-OG`（19,909セル）に対するヘッドレス検証

## 単体試験

- 実行: `<cmos-motion-poc>\.venv\Scripts\python.exe -m pytest -q`（`prototypes/slicer-cstamp`）
- 結果: **31件すべて合格**（0.25秒）
- 内容: スタンプ1件（AC-001）、方向のみ調整（AC-002/011）、確定1件（AC-003）、取消（AC-004/014）、重複確定1件（AC-005）、認識喪失凍結・再開・取消（OP-013/SR-008）、進行反転（OP-008）、方向リセット（OP-009）、台帳順序・完全性・改変検出・再読込（AC-017/018）、C再構成（AC-015/016）、表面交差の可否（AC-009相当）

## ヘッドレス検証

- 実行: `Slicer.exe --no-main-window --python-script prototypes/slicer-cstamp/headless_verify.py`
- 結果ファイル: `artifacts/cstamp/headless_result.json`
- 台帳: `artifacts/cstamp/headless_events.jsonl`（確定イベント1件）
- 確認事項:
  - `vtkCellLocator.IntersectWithLine`で実メッシュへ交差成功（`intersected: true`）
  - `stamp -> DRAFT -> rotate 15° -> commit -> COMMITTED -> cancel -> IDLE` の遷移成立
  - 確定イベントに `transform_3x4`、33点の`shape_points`、整合性ハッシュを保持（`integrity_ok: true`）
  - 同一`draft-0001`への重複確定は`deduplicated`で追記なし（`event_count: 1`）

## 成立しない主張

- 画面上の見た目、連続ドラッグ調整、`PLANNED`レイヤー、ハンドモーション入力は未検証
- マウス／モーション同等性（AC-007）、対象ウィンドウ制限、実カメラ入力は未検証
- 臨床的位置精度・治療成立を示すものではない
