# 証跡: ハンドモーション完結経路（docs/23第2版コード層）

日付: 2026-10-09
区分: 非臨床PoCの自己検証記録。臨床承認・性能合格・実手動作の証拠ではない。

## 実施した検証

### 単体試験

| 対象 | コマンド | 結果 |
|---|---|---|
| slicer-cstamp | `pytest tests`（PoC仮想環境Python） | 89件全合格 |
| cmos-motion-poc | `pytest tests`（同仮想環境） | 62件全合格 |

含まれる範囲: 封筒検証（版/session/seq/ts/TTL/型）、未知・非JSON拒否、req dedup、
ARM/モード/レイヤー/DRAFTゲート、切断時凍結、`move_draft`の方向不変・射影・
冪等性、`seed_draft`の`correction_of`引継ぎ、`PlanTracker.reorder/select`、
手形分類・エッジ/ホールドラッチ、op_controller写像、session_client応答・
輸送断フェイルクローズ（FakeServer結合）。

### Slicer実機検証（ヘッドレス）

- `headless_module_verify.py` → `artifacts/cstamp/module_result.json` 全項目 `ok:true`
- 新プロトコルで `hello`→`arm`→`status` 受理、`shell`等の非許可コマンド拒否

### Slicer実機検証（GUI、合成イベント）

- `gui_verify.py` → `artifacts/cstamp/gui_result.json` 全項目 `ok:true`
- TCP `view_rotate` が実3DビューのvtkCameraを移動（`server_moved_camera:true`）

### PoC↔実Slicer結合E2E

- `e2e_session_verify.py` → `artifacts/cstamp/e2e_result.json` 全項目 `ok:true`
- 確認列: hello→セッション→arm→status→mode遷移(aim)→aim(表面hit)→
  stamp(draft-0002)→mode遷移→move_draft/rotate_opening/tilt→reverse→
  reset_dir→commit(確定イベント)→別req重複commit拒否→query_result
  （未知req拒否・既知req応答返却）→menu_open/next/close→
  未知コマンド拒否→disarm

## 検証していないもの

- 実カメラ＋実手でのジェスチャー動作（H-01〜12）
- 注入試験X-01〜08
- 性能実測（遅延・誤作動率・認識成功率）
- 計画新規/版管理コマンド群（未実装）
- 署名・SBOM・配布監査（単位10）

## 安全確認

- プロトコルは許可リストのみ受理。shell/任意Python/ノード編集に到達する経路なし
- 切断時はdisarm＋DRAFT凍結（取消しない）
- 確定は明示コマンドのみ、PLANNED→PERFORMEDの自動変換なし
- 台帳は追加専用、訂正は`correction_of`の新イベントで上書きしない

## 追記（2026-10-10）: 残存実装項目の実装と検証

### 実装

- `PlanStore`（計画版管理）: create_plan / begin_revision / edit_item / add_item / delete_item / move_item / save_revision / cancel_revision。承認版不変・保存時差分記録
- 監査コマンド: select_reason / set_out_of_plan / revoke_event（取消監査行・元イベント不変）/ confirm_audit
- draft_revision版束縛: commitがexpected_revision不一致を拒否。台帳失敗時DRAFT保持（OP-011）
- reset_view: 初回利用時姿勢を基準にカメラのみ復元（採用・docs/01準拠）
- 前面ウィンドウ監視: Win32 PID照合をdispatcherゲートへ（SR-006）
- ホイール→連続ズーム変換: `op_controller.zoom_step` + `app.py`のwheelEvent
- tools: `generate_sbom.py`（SHA-256+pip freeze）、`audit_network.py`（非loopback走査）

### 検証結果

- 単体試験: slicer-cstamp 131件 / cmos-motion-poc 66件 全合格
- 実SlicerE2E: `artifacts/cstamp/e2e_result.json` `ok:true`。計画版管理・監査コマンド全受理・diff検出
- 前面ゲート: notepad前面時にview_rotate→`reject:target window is not foreground`、status/disarm受理（双方向実機確認）
- 通信監査: `audit_network.py` exit 0、非loopback 0件
- SBOM: `artifacts/sbom/sbom-20261010.json`（50ファイル・39依存）

### 残存

実手試験H-01〜12、X-06性能合格判定、コード署名、正式な最小権限/構成管理証明、画面メニューへの計画版管理項目追加は未実施。

## 追記2（2026-10-10）: メニュー項目化・署名・証明

### 実装

- 画面メニューへ`reset_view`/`plan_create`/`plan_rev_begin`/`plan_rev_save`/`plan_rev_cancel`/`out_of_plan`/`revoke_selected`/`audit_confirm`/`reason:*`/`commit`/`cancel_draft`を追加。commitは表示済みrev束縛
- `reason_candidates`登録候補のみ`select_reason`で受理（自由文字禁止）
- `revoke_event`/`confirm_audit`は`_selected_event_id`フォールバック（review選択→メニュー監査）
- `run.ps1`/`setup.ps1`へAuthenticode署名（自己署名証明書`CN=CStampPoC-Dev`、thumbprint `262148C323E1E38D27A5C331F73508CC2B0B4594`、証明書`artifacts/cstamp/cstamp-poc-dev.cer`）
- `docs/25_minimal-privilege-config-proof.md`でIT-004/IT-005を証明メモ化

### 検証結果

- 実SlicerE2E `e2e_result.json` `ok:true`——`menu_plan_rev_begin`/`menu_rev_begin_confirm`/`menu_plan_rev_save`/`menu_reason_revision`/`menu_revoke_selected`/`menu_audit_confirm_item`/`select_event`/`menu_reason_confirm`全true。メニューからrev begin実行・rev save項目出現・理由候補表示を確認
- 署名: `Get-AuthenticodeSignature`で両ps1に署名ブロック存在・証明書拇印一致。`UnknownError`は自己署名ルート未信頼のみ（ハッシュ不一致ではない）
- 権限照合: `admin|elevat|registry|HKLM|service|schtasks`該当なし

### 残存

実手試験H-01〜12、X-06性能合格判定、正式組織署名・ルート配布、実行時昇格監査、個別項目編集のメニュー化は未実施。
