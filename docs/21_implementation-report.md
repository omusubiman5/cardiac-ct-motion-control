# 実装報告書

## 現在の実装状態（2026-10-11）

**実装未完了。** [計画全項目の実装照合](37_implementation-plan-audit.md)を作成し、手操作入口10命令の不足、表示済み確定、安全処理の接続、共通マウス／入力所有権、計画・保存・監査等の契約不足を確認した。原要求74件・AC24件・H/X/V30件を個別対応付け。照合完了と実装完了を分ける。以下の過去の実装済み記載は各記録時点・記載範囲に限り、計画全体の完了を示さない。

日付: 2026-10-08（第2版）＋2026-10-09（第3版・ハンドモーション完結経路）
対象: `prototypes/slicer-cstamp`、`prototypes/cmos-motion-poc`
区分: 非臨床実装報告。臨床承認・性能合格・臨床使用の主張ではない。

## 2026-10-10 FIELD-20261010-01 テスト実行結果

[テスト結果MD](27_field-test-results.md)を作成。単体自己検証131件＋66件合格、実Slicer内の合成プローブ35項目（29述語合格・6不合格）、実TCPの開始停止・無効時回転拒否、カメラ30秒認識を実行した。カメラ番号0で806フレーム受信・手検出0件。PIXEL映像源の同一性・操作者の意図は未確認で、実手H試験を合格にはしていない。

再接続で結果照会消失、改変台帳の受理、独立監査確認前の追記、元イベントのメモリ属性変更、計画復元不成立、スキップ理由不一致、DRAFTメニューのbool.revision例外、取消後CANCELLED、署名非正常・SBOM5件不一致を結果書へ記録した。個々の検査範囲・生応答・再試行を証拠として保持。安全中止条件により実手の確定・計画・訂正は未実施。既存台帳・コード変更0を確認し、製品修正は行っていない。全体未合格。修正後のX再試験とPIXEL映像源確認を経てH試験へ進む。

## 2026-10-10 実地試験計画への接続

実手・利用者確認の実施手順は[実地テストプラン](26_field-test-plan.md)を参照。docs/03・05・23を根拠に、H-01〜12、X-01〜08、AC24件を手順・観測・中止条件へ展開した。コードを限定照合し、計画個別編集だけでなく反転／方向リセット／明示保存／順序変更の手メニュー到達、描画完了確認、代替マウス、監査の独立確認等を阻害・検証項目として記録した。今回の作業は計画作成と文書の自己検証のみで、既存の自動試験結果の再実行、実手試験、権限・署名の実証は行っていない。

## 2026-10-09 第3版: ハンドモーション完結経路（docs/23対応）

docs/23第2版の必須範囲のうち、コード層の実装と自動検証を実施した。
実手（H-01〜12）・利用者確認・単位10（署名/SBOM/配布）は未実施であり、
完了ゲートONI-004の段階2〜4は未達である。以下はその正直な内訳。

### 完了（実装済み・自動検証済み）

#### 共通契約 `slicer-cstamp/command_protocol.py`

| 項目 | 内容 | 検証 |
|---|---|---|
| 封筒 | 版・セッションID・要求ID・連番・時刻・TTL（既定2000ms） | 単体試験 |
| hello/セッション | 新規セッション発行、再接続でarmed非継承 | 単体＋実Slicer |
| 許可リスト | 未知コマンド・型違い・非JSONは全て拒否 | 単体＋実Slicer(`bogus_rejected`) |
| 古い操作 | `|now-ts|>ttl`拒否、連番逆行拒否 | 単体 |
| dedup | 同req再送は保存応答を返し再実行しない | 単体 |
| ARM/モード/レイヤーゲート | 非armed・モード不一致・DRAFT中レイヤー変更を拒否 | 単体 |
| 切断 | 受付停止＋DRAFT凍結（取消しない） | 単体 |
| query_result | 保存済み応答の読み取り専用照会、未知reqは拒否 | 実Slicer |

#### cstampコア拡張

| 項目 | 内容 | 検証 |
|---|---|---|
| `move_draft` | アンカー移動＋uを新面へ射影（退化時は決定的面基底）。in_plane角・進行方向は不変 | 単体試験 |
| `seed_draft` | 既存配置から訂正用DRAFTを生成、commitに`correction_of`引継ぎ、元イベント不変 | 単体試験 |
| `PlanTracker.reorder/select` | 明示的順序変更・次予定指定。PLANNEDをPERFORMEDへ変換しない | 単体試験 |

#### CStampModule（単位1・5・6・7のSlicer側）

- ARM/DISARM・モード・レイヤー状態をディスパッチャが保持しパネルへ表示
- 照準マーカー`CStamp-AIM`（黄）、表面外では非表示＋配置不可応答
- ops: arm/disarm/status/select_mode/select_layer/view_rotate/view_pan/
  zoom/aim/stamp/move_draft/rotate_opening/tilt/reverse/reset_dir/commit/
  cancel/resume_draft/load_plan/select_plan_item/skip_plan/reorder_plan/
  select_event/show_c/begin_correction/save_session/load_session/
  menu_open/next/prev/confirm/close
- 画面上メニュー: モード切替・レイヤー切替・計画読込・スキップ・
  台帳復元・凍結解除・受付停止をmenu_confirm経由で実行
- スキップ/順序変更は`record_type`監査行を台帳へ追記（理由・時刻）
- 単一クライアント方針のQTcpServer、切断時`on_disconnect`で凍結

#### PoC側（単位3・4・5・6・8の入力経路）

| 項目 | 内容 |
|---|---|
| `gesture_fsm.py` | 手形分類: OPEN_PALM/POINT/TWO/THREE/FIST/THUMB/PINCH/UNKNOWN。`GestureLatch`（安定保持→エッジ1回→解放まで再発火なし）、`HoldDetector` |
| `session_client.py` | hello/seq/req/ts封筒クライアント、輸送断フェイルクローズ |
| `op_controller.py` | モード別連続入力（view/aim/move/rotate/tilt/review）＋離散ジェスチャー。親指=メニュー、2指=スタンプ/次へ/選択、3指=確定/実行/訂正、拳=取消。開いた手1.5s保持=受付開始。`zoom_step`でマウスホイール等の離散入力を同一連続比率ズームへ変換（FR-022）。確定は最後に表示したdraft revisionを束縛して送信（ONI-001） |
| `app.py` | `--slicer-connect`で新プロトコル経路。手のみの開始/メニュー/モード/確定/取消。無操作タイムアウトでdisarm送信。プレビュー窓のマウスホイール→`zoom`比率送信。プレビュー/マウス経路は従来通り |
| `config.py` | 保持時間・親指比・照準レート・回転専用感度/不感帯・ズーム連続比・ホイール比率・開口/傾斜感度（全て検証付き構成値） |

#### 追加分（計画版管理・監査・前面監視・基準視点）

| 項目 | 内容 | 検証 |
|---|---|---|
| `cstamp/plan_revision.py` `PlanStore` | 計画の版管理。`create_plan`/`begin_revision`/`edit_item`/`add_item`/`delete_item`/`move_item`/`save_revision`/`cancel_revision`。編集は作業コピーのみ、保存で新版＋差分（added/removed/changed/order_changed）記録。承認済み版は不変（FR-034） | 単体試験11件 |
| 監査コマンド | `select_reason`（理由区分の保留）、`set_out_of_plan`（次確定を計画外宣言）、`revoke_event`（取消監査行、元イベント不変）、`confirm_audit`（監査確認記録） | 実SlicerE2Eで受理確認 |
| `draft_revision`版束縛 | DRAFTの編集ごとにrevision増加。`commit`は`expected_revision`不一致を拒否し、確定イベントへ`draft_revision`を記録。台帳失敗時はDRAFT保持（OP-011） | 単体試験3件 |
| `reset_view` | 初回利用時のカメラ姿勢を基準として復元（カメラのみ、Cデータ不変）。docs/01/10の基準視点を採用と決定 | 実SlicerE2Eで受理確認 |
| 前面ウィンドウ監視 | `foreground_ok`（Win32 GetForegroundWindow→PID照合、非ブロッキング）をディスパッチャゲートへ組込み。Slicerが前面でない間は編集・視点・計画コマンドを全て拒否。status/disarm/menu/queryは常時受理（SR-006） | 実機で双方向確認（別窓前面時reject「target window is not foreground」、Slicer前面時受理） |
| `tools/generate_sbom.py` | 配布物のSHA-256マニフェスト＋pip freeze（IT-002のハッシュ/SBOM部分。署名は未実施） | `artifacts/sbom/sbom-20261010.json`生成（50ファイル・39依存） |
| `tools/audit_network.py` | 静的通信監査。socket/urllib/requests/Qt networkを走査し非loopbackがあれば失敗（X-08/IT-001） | 非loopback 0件を実測（exit 0） |

#### 実機検証結果（第3版追加分を含む）

- Slicerヘッドレス: `module_result.json`全項目`ok:true`
- Slicer GUI: `gui_result.json`全項目`ok:true`。`view_rotate`が実3Dカメラを移動
- PoC↔実Slicer: `e2e_result.json` `ok:true`——hello→arm→aim→stamp→move/rotate/tilt→commit→重複commit拒否→query_result→reset_view→create_plan→begin_revision→edit_item→save_revision（diff検出）→select_reason→revoke_event→confirm_audit→menu→disarm、未知コマンド拒否
- 前面ゲート実機: 別窓前面時に`view_rotate`拒否・status/disarm受理を確認
- 単体試験: slicer-cstamp 131件、cmos-motion-poc 66件、全合格

### 実装済み・未検証

| 項目 | 状態 |
|---|---|
| 実カメラ＋実手での全ジェスチャー動作 | 分類器・ラッチは合成ランドマーク試験済み。実手H-01〜12は未実施 |
| 手だけの通し操作（計画の最低限シナリオ） | プロトコル経路はE2E済みだが実手の実操作は未実施 |
| メニューconfirm→各コマンドの組合せ全網羅 | menu_confirm→dispatch_local＋新項目（rev begin/save・理由選択・監査）はe2eで実Slicer実行確認。個別パラメータを要する項目編集（edit/add/delete/move_item）はメニュー非対象 |
| select_event/begin_correctionの実経路 | select_eventは実Slicer経路で確認済（e2e）。選択精度閾値（15mm）の実調整とbegin_correctionの実経路は未 |
| 回転操作性の改善効果 | 回転専用不感帯・感度分離は実装済み。利用者評価未実施 |
| 前面ゲートと通常マウス操作の併用影響 | ゲートはwireコマンドのみを対象。マウスUIはゲートを通らないため影響なしだが、実画面での併用確認は未実施 |

#### 追加分2（メニュー項目化・署名・最小権限証明）

| 項目 | 内容 | 検証 |
|---|---|---|
| 画面メニュー拡張 | `_menu_items`に`reset_view`/`plan_create`/`plan_rev_begin`/`plan_rev_save`/`plan_rev_cancel`/`out_of_plan`/`revoke_selected`/`audit_confirm`/`reason:*`/`commit`/`cancel_draft`を追加。commitは表示済みdraft revisionを束縛 | e2e `menu_plan_rev_begin`/`menu_rev_begin_confirm`/`menu_plan_rev_save`/`menu_reason_*`/`menu_revoke_selected`/`menu_audit_confirm_item` 全true |
| 理由区分カタログ | `reason_candidates`を準備時登録値として保持。`select_reason`は未登録区分を拒否（docs/23「自由文字を前提にしない」） | e2e `select_reason`/`menu_reason_confirm` |
| 選択イベントの監査フォールバック | `revoke_event`/`confirm_audit`は`_selected_event_id`を既定対象に採用（reviewモードで選択→メニューから監査操作） | e2e `select_event`+メニュー項目出現 |
| コード署名 | `run.ps1`/`setup.ps1`へ自己署名証明書`CN=CStampPoC-Dev (non-clinical)`でAuthenticode署名。証明書`artifacts/cstamp/cstamp-poc-dev.cer`、thumbprint `262148C3...4594` | `Get-AuthenticodeSignature`で署名者拇印一致。`UnknownError`は未信頼ルートのみ（ハッシュ不一致ではない） |
| 最小権限・構成管理証明 | `docs/25_minimal-privilege-config-proof.md`。権限必須APIゼロの静的照合・loopback限定・venv局所・構成値検証・モデルSHA-256を証明メモ化 | 文書＋audit_network exit 0 |

### 未実装（docs/23第2版の残存範囲）

| 項目 | 計画内位置 |
|---|---|
| H-01〜H-12の実手試験 | 検証段階（実手が必要） |
| X-06の性能合格判定 | 遅延計測コードは実装済（dispatch p50/p95を出力）だが合格値未合意のため判定しない |
| 正式なコード署名（組織証明書） | 自己署名は付与済み。正式証明書・ルート配布は運用課題（docs/25記録） |
| 実行時の権限昇格監査 | 静的照合で権限必須APIゼロを証明したが、実行時プロセス監視の外部監査は未実施（docs/25記録） |
| 描画完了確認の明示ACK | draft_revision束縛は実装済。「表示が完了した」の確認はサーバ側同期適用のため省略形。描画パイプライン分離時は要追加 |
| edit_plan_item/add_plan_item/delete_plan_item/move_plan_itemの画面メニュー項目 | コマンドとrev begin/save/cancelはメニュー経路で実行可能。個別項目編集は複雑なパラメータを要しプロトコル経路のみ |

### 実手検証に向けた操作列（Space/マウス不要の想定経路）

開いた手を1.5s保持→受付中（VIEW）→開いた手/人差し指/ピンチで視点
→親指でメニュー→2指で`mode_aim`へ→3指で確定（モード=AIM）→指先で照準
→2指でスタンプ→親指メニュー→`mode_move/rotate/tilt`へ遷移→手の移動で調整
→3指で確定→…→親指メニュー→`disarm`で受付停止。

## 2026-10-09 要求照合による未完成範囲の訂正

（注: 本節は第3版の実施時点以前の状況を記録したもの。表の「不足」列の多くは上記第3版でコード層に実装されたが、実手検証までは完了としない。）

利用者による実操作でパンとズームの成立、回転の操作しにくさが報告された。以下は`docs/03_system-requirements.md`のFR-008、FR-013、T-001〜T-005、AC-007と現行コードの照合結果である。機能単位の検証成功を、ハンドモーションによる全操作の完成とは扱わない。

| 要求される操作 | 現行実装の到達範囲 | 不足 |
|---|---|---|
| 回転・パン・ズーム | モーション輸送は3種類を送信。パン・ズームは利用者確認済み | 回転の操作性改善。数値性能は未評価 |
| 照準とCスタンプ仮配置 | Slicer側のマウス表面クリック経路 | 手による照準移動とSTAMP_DRAFTの接続なし |
| 仮配置位置調整 | 初回照準位置への配置のみ。controllerに位置移動の公開操作なし | FR-008/FR-013の配置後位置調整 |
| C方向調整 | マウスによる開口スライダー、固定15度傾斜、進行反転、リセット | 手入力接続なし。傾斜は連続操作なし |
| 明示確定・取消 | Slicerのボタンと台帳コア | COMMIT_DRAFT/CANCEL_DRAFTの手入力接続なし |
| 計画・実績操作 | レイヤー選択、台帳復元、ゴースト・照合等のSlicer側機能 | ハンドモーションによる計画操作の接続なし |
| 操作パネルの提供 | start_server_session.pyはウィジェットを生成・保持する | 起動スクリプトにモジュール登録またはパネル表示の明示処理がなく、利用者に操作パネルが見えている証拠なし |

`slicer_bridge.py`とSlicerのコマンド受付はrotate/pan/zoomのみ。よってFR-013とAC-007の全操作同等性は未達であり、要求全体として「開発完了」とは判定できない。具体的なスタンプ・確定ジェスチャーは原要求でも未固定で、確定はスタンプ／調整とは独立した明示操作とするSR-009を維持する必要がある。

## 完了（実装済み・検証済み）

### Cスタンプ中核（`prototypes/slicer-cstamp/cstamp`）

| 項目 | 内容 | 検証 |
|---|---|---|
| 状態機械 | `IDLE`/`DRAFT`/`COMMITTED`/`CANCELLED`、許可遷移のみ受理 | 単体試験＋実メッシュで遷移確認 |
| スタンプ | 許可表面の照準点へ`DRAFT`を1件生成。既存DRAFT中は拒否 | AC-001/010相当、実メッシュ(19,909セル)交差確認 |
| 方向調整 | 面内回転・傾斜・進行反転・リセット。アンカー不変 | AC-002/011相当 |
| 明示確定 | 確定ログちょうど1件、重複確定は追記なし | AC-003/005相当、`deduplicated`確認 |
| 取消 | 仮配置のみ破棄、確定ログ不変 | AC-004/014相当 |
| 認識喪失凍結 | 凍結中は調整・確定を拒否 | OP-013/SR-008相当 |
| 確定イベント保存 | ID・順序・時刻・座標系・テンプレート版/SHA-256・配置面・33点形状・完全性ハッシュ | FR-014/024/027/030相当 |
| C再構成 | 保存イベントから`placement`→C形状再現 | AC-015/016/018相当 |
| 表面照準 | 光線-三角形交差＋`vtkCellLocator` | AC-009相当 |
| 計画追跡 | `PlanTracker`：順序保持・最近接照合・許容差判定・スキップ・計画外記録 | 単体試験12件 |

### Slicerモジュール（`CStampModule.py`）— 実Slicer上のヘッドレス検証済み

| 項目 | 結果 |
|---|---|
| モジュール読込 | `module_loaded: true` |
| DRAFT曲線作成 | 33点のMarkupsカーブ |
| 連続開口角 | `rotate_to(45°)` 適用確認 |
| 確定→確定点＋隠しC形状 | `performed_points:1`/`shape_hidden:true` |
| 確定点→C再表示 | `reshape_visible: true` |
| 台帳復元 | `restored:1`、2回目読込で重複なし（冪等） |
| 取消→ノード除去 | `cancel_removed: true` |
| PLANNED確定 | `planned_layer:"PLANNED"`、計画用点リストへ分離 |
| 計画読込→ゴースト | `ghost_visible: true`（緑・不透明度0.45） |
| PERFORMED照合 | `plan_match`レコード追記、`matched:true`、Δ位置・Δ法線記録 |
| ゴースト消去 | 全計画消化で`ghost_cleared: true` |
| 計画外PERFORMED | `matched:false`で記録（計画外は拒否でなく記録） |
| ウィジェット構築 | `setup()`成功、ステータス描画確認 |

証跡: `artifacts/cstamp/module_result.json`（`ok:true`）、`headless_module_verify.py`

### Slicer GUI実機検証（`gui_verify.py`、メインウィンドウあり・合成インタラクターイベント）

| AC | 操作 | 結果 |
|---|---|---|
| AC-001 | 実3Dビューのインタラクターへ左クリック合成→CARTO表面にDRAFT | 33点ドラフト作成 |
| AC-002 | 連続スライダーで開口角60° | `in_plane_angle=60°` |
| AC-003 | 「確定」ボタン経路 | 台帳ちょうど1行・確定点1件 |
| AC-004 | スタンプ→取消 | DRAFT消去・台帳1行のまま |
| 単位2 | TCP `{"cmd":"rotate"}`→実3DビューのvtkCamera | `server_moved_camera:true` |

証跡: `artifacts/cstamp/gui_result.json`（`ok:true`）。
注意: 合成インタラクターイベントによる自動検証であり、人手のマウス操作とは区別する。

### 視点操作コマンド経路（単位2）

| 項目 | 結果 |
|---|---|
| `view_commands.py` | rotate/pan/zoom のみ受理。キー入力・シェル・型違い・範囲外は全て無効（フェイルクローズ）。単体試験19件 |
| Slicer側受付 | `127.0.0.1:<port>`限定`QTcpServer`。TCP行を受理してvtkCameraへ適用（`camera_rotated`/`camera_zoomed`/`server_accepted`） |
| PoC側送信 | `SlicerCommandBridge`（loopback強制）。MotionAction→JSON行変換・接続失敗時フェイルクローズ。単体試験5件 |

### ハンドモーション安全経路（`prototypes/cmos-motion-poc`）

| 項目 | 結果 |
|---|---|
| `SafetyController` | DISABLED→READY→TRACKING→EXECUTING。手なし/複数手/古いフレーム/未分類ジェスチャー/低信頼度→解放付きREADY降格。カメラ断→FAULTラッチ（手動再アーム必須）。単体試験込み |
| `StrictTargetGuard` | 前面HWND→PID→プロセス実行パスの完全一致。タイトル部分一致は不使用。単体試験 |
| `SmoothZoom` | 不感帯・加速度制限・速度上限・解放時減衰・比率クランプ。単体試験（残留速度ゼロ収束確認） |
| `TasksHandRecognizer` | MediaPipe Tasks Hand Landmarker(VIDEO)。ピン留めモデル`models/hand_landmarker.task`(SHA-256記録)。合成フレームでインスタンス化・推論確認（hand_count=0で正しく無出力） |
| `app.py`統合 | 認識器選択(tasks/legacy)、コントローラゲート、`--enable-input`(mouse)/`--slicer-connect`(slicer)/preview、`input_timeout_s`自動解除、Spaceアーム/解除 |
| テスト | PoC計33件全合格 |

## 実装済み・未検証

| 項目 | 状態 | 未検証の理由 |
|---|---|---|
| 実カメラ＋実手認識 | Tasks認識器は合成フレームで動作確認 | 実CMOSカメラ・実手でのランタイム未実施 |
| PoC→Slicer実結合（手→認識→TCP→カメラ） | サーバ側のカメラ移動はGUI検証済み、ブリッジ送信は試験サーバで検証済み | PoC実プロセスからの送信→Slicer実受け取りの端から端の動作は未確認 |
| SmoothZoom→Slicer連続ズーム | エンジン単体検証済み | 現ブリッジは離散wheel相当の比率送信。連続比率経路への統合は未接続 |
| 人手のマウス操作でのGUI検証 | 合成インタラクターイベントでAC-001〜004確認済み | 人手操作による確認は別途実施する |

## 未実装

| 項目 | 対応要求 |
|---|---|
| 傾斜の連続ドラッグ（スライダーは面内角のみ、傾斜は15°ボタン） | OP-007連続性 |
| `correction_of`訂正チェーンのUI（フィールドは台帳に存在） | FR-029相当 |
| 実操作性能値（遅延・fps・認識率の計測） | 性能目標未設定 |
| 術者同一性の証明（「片手=権限者」の担保は設計外、既知の制限として継続） | 監査済課題 |
| Spaceキーアーム（無菌野動機との不整合、既知の設計制限） | 監査済課題 |

## 次の検証対象（順序）

1. 実CMOSカメラ＋実手で`--slicer-connect`を実行し、手→認識→SafetyController→TCP→Slicer実カメラの端から端を確認（単位2/3の実機結合）
2. 計画ファイル作成→読込→ゴースト→PERFORMED→照合Δの実画面確認（AC-019〜024のUIレベル、合成照準クリック併用可）
3. 傾斜の連続ドラッグ化と`correction_of`訂正UIの実装
