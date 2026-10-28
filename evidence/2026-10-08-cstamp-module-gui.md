# 検証証跡: Cスタンプモジュール・視点コマンド・モーション安全経路

日付: 2026-10-08
区分: 非臨床プロトタイプの検証記録。臨床性能・臨床使用の主張ではない。

## 実行環境

- 3D Slicer 5.12.3（Windows Stable）、実シーン `artifacts/slicer/CARTO3_EA_Map_Demo.mrb`（CARTO殻 19,909セル / 9,957頂点）
- Python venv `prototypes/cmos-motion-poc/.venv`

## 結果サマリ

| 検証 | 方法 | 結果 |
|---|---|---|
| cstamp単体試験 | `pytest tests` (slicer-cstamp) | 62件全合格 |
| PoC単体試験 | `pytest` (cmos-motion-poc) | 33件全合格 |
| モジュール論理・計画・コマンド | `Slicer.exe --no-main-window --python-script headless_module_verify.py` | `ok: true`（18項目） |
| GUI操作AC-001〜004＋実カメラ回転 | `Slicer.exe --python-script gui_verify.py`（メインウィンドウあり） | `ok: true` |

## GUI検証の明細（`artifacts/cstamp/gui_result.json`）

| AC | 操作 | 結果 |
|---|---|---|
| AC-001 | 実3Dビューのインタラクターへ左クリックを合成→CARTO表面にDRAFT生成 | 33点ドラフト作成 |
| AC-002 | 連続スライダーで開口角60°へ | `in_plane_angle = 60°` |
| AC-003 | 「確定」ボタン経路 | 台帳1行・確定点1件 |
| AC-004 | スタンプ→取消 | DRAFTノード消去・台帳1行のまま |
| 単位2 | TCP `{"cmd":"rotate"}` → 実vtkCamera | `server_moved_camera: true` |

## ヘッドレス検証の明細（`artifacts/cstamp/module_result.json`）

- モジュール読込・DRAFT/確定点/隠しC形状/再表示
- 台帳復元の冪等性（2回読込でも1点）
- `view_commands`：実vtkCameraへのrotate/zoom適用、不正コマンドは無効
- コマンドサーバ：`127.0.0.1`限定TCP受付
- PLANNED確定→計画読込→ゴースト表示→PERFORMED照合（`plan_match`追記、Δ位置・Δ法線）→計画消化でゴースト消去
- 計画外PERFORMEDは`matched:false`として記録（拒否ではなく記録）
- ウィジェット`setup()`構築成功

## 注意事項

- `--no-main-window` 実行時にSlicerHeart拡張が
  `layoutLogic`不在エラーを出すが、本モジュールとは無関係の拡張起動ノイズ。
- GUI検証は合成インタラクターイベントによる自動検証であり、
  人手のマウス操作による確認とは区別する。
- 実CMOSカメラ＋実手でのエンドツーエンド動作は未実施。
