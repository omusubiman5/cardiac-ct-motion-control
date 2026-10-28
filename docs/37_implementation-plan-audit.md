# 計画全項目の実装照合

本書は修正前の照合結果。後続実装と現在の未完了項目は[docs/39](39_completion-implementation-report.md)を参照。過去の所見と証跡を保持する。

照合日：2026-10-11。本人指示「計画全項目の実装照合を進めてください」に対応する。

**照合結果：実装は未完了。** 主なコードがあることと、計画どおりの操作経路が完成していることを分けて照合した。未実装の手操作入口、未接続の安全処理、保存・監査の契約不足がある。「残りはテストだけ」ではない。

## 対象と判定方法

原要求docs/03、既存計画docs/20、不足分計画docs/23第2版、統合UI計画docs/31、修正計画docs/33を対象とする。要求正本を置き換える計画ではなく、現行ソースと成果物の照合結果である。

- 実装済み：対象範囲の処理と呼出経路がソースにある。実手・稼働版・性能の合格を意味しない。
- 一部実装：API／部品はあるが、入力→処理→表示／保存の経路か要求された契約が不足している。
- 未実装：指定された入口・処理・成果物を対象コードに確認できない。
- 確認不能／未検収：実行結果、環境、利用者の意図等を今回の静的照合では確定できない。未実装へ読み替えない。

自作の静的照合であり、独立レビューではない。37ソースのAST関数位置、SHA256、通信命令、ハンドメニュー、原要求74件、SBOMとの差を[機械抽出証跡](../work/20261011-implementation-audit-evidence.json)へ保存。[抽出スクリプト](../work/audit_implementation_20261011.py)。許可通信命令に対応するopハンドラーの欠落は0だが、次表の手操作・安全・永続化不足がある。関数名の一致だけでは合格にしていない。

今回はコード修正・アプリ操作・カメラ取得・TCP接続・仮C編集・台帳保存を行っていない。既存の実試験結果は[docs/36](36_corrected-hand-control-test-results.md)を参照し、今回の静的照合へ混ぜない。

## 確認した実装不足

| ID | 計画との不一致 | 現行ソースの根拠・必要な実装 |
|---|---|---|
| G-01 | 表示済みスナップショットを原子的に確定できない | CStampModule.op_commit、state_machine.commit、OperationController._open_confirmationは内部revを使う。displayed_revision・描画完了ACK・表示ハッシュ／draft_id束縛・保存中ロックがない。docs/23 ONI-001の契約が不足 |
| G-02 | 通常マウス全操作と共通引継ぎが未完成 | CStampModuleWidget._adjust/onCommit等はlogicへ直接呼出し。共通dispatcher／版検査を通さない。表面ドラッグMOVE、連続傾斜、手停止・遅延要求失効を伴う入力所有権の引継ぎがない。サイズマウス操作の本人許可はこの不足を免除しない |
| G-03 | 手操作の入口が10命令で不足 | hand_menu.MAIN/EDIT/RECORDSとOperationController._panel_selectにreverse、reset_dir、select_plan_item、reorder_plan、edit/delete/add/move_plan_item、save_session、query_resultの入口がない。Slicer側APIがあっても手だけで完結しない。旧サーバーメニューにもこれらの入口はない |
| G-04 | 計画作成・新版と予定仮配置／永続復元が未接続 | op_create_planは空itemsと既定creatorで作成。手で作成者・計画ID・複数計画を選ぶ導線なし。PLANNEDのcommitとPlanStore所属項目の接続、create時の全items永続化、registryからPlanStoreを復元する経路がない |
| G-05 | 監査の独立確認と元イベント不変が未実装 | op_revoke_eventは選択だけでappendし、_committed[event_id]['revoked']を書き換える。op_confirm_auditは後から別記録を追加するだけ。取消監査をpendingに保持し独立確認時だけ追加する契約に未対応 |
| G-06 | 改変拒否と途中終了回復が未接続 | EventLedger.verify_integrityは存在するが__init__/load_ledger/load_planで使用しない。JSONL append+fsyncはあるが部分行・確定索引との原子回復がない。ハッシュ付与と読込拒否を混同できない |
| G-07 | 許可シーン・表面のハッシュ／変換束縛が不足 | _refreshはsurfaceComboを代入、_surfaceはポリゴン有無を確認するだけ。モデル／変換変更の検知→照準無効化・凍結がない。commit.sceneはモデル名／RASを持つがシーン・モデルハッシュ、列ID、時刻源等の要求項目が不足 |
| G-08 | 認識喪失→凍結→明示再開の実カメラ経路が未接続 | app.pyのSlicer分岐はgate不許可をShape.NONEへ置換する。手復帰で再びgate.allowedになるとops.updateへ入る。認識喪失時にサーバーDRAFTを凍結する通知がなく、on_recognition_loss部品は切断／disarmでだけ呼ばれる。基準点リセットはあるが、明示再開の代替ではない |
| G-09 | 確認画面・診断状態の表示契約が不足 | unified_hand_panelは受付・モード・仮C・案内・reasonを表示するが確認対象draft_id/rev/座標/傾き/表示ハッシュを表示しない。認識側SafetyControllerの異常状態・停止ゲート理由を共有していない。メニュー開でも現在モードを表示し、計画第3節の選択待ち見出しを完全には実装しない |
| G-10 | スムーズズーム部品がSlicer主経路へ未接続 | zoom_engine.SmoothZoomは存在するがOperationControllerのview PINCHはフレーム差分ratio、op_zoomはcamera.Dolly。加減速・速度・累積倍率の上下限を主経路で実行しない。1命令のratio制限は累積倍率制限ではない |
| G-11 | 理由・対象・版の束縛が不足 | _panel_select(skip_plan)がreason='operator'を固定。op_reorder_planは理由を保存しない。計画外commitは宣言flagを保存するが選択理由を実績へ結び付けない。計画／監査変更要求に対象版・ハッシュの検査がない |
| G-12 | 接続診断と試験モードの完成が不足 | _CommandServerにソケット識別・接続世代・drop順序・各応答／GUI時間を記録する実装なし。MRMLバッチ更新と別プロセス段階再生はある。カメラ停止／再生／復帰は手順・スクリプトで分離しており、単一試験モードによる排他管理・入力元切替の制御はない |
| G-13 | 全手順・図・測定成果物が未完了 | docs/28に新プレビューと方向専用図はあるが旧図を現行UI忠実図として同期した証跡なし。H-01〜12、全条件V試験、端から端の遅延・誤操作率／時・環境別成功率・復旧／代替時間の完成記録なし。10分編集はdocs/36で未達 |
| G-14 | 最終版の署名・SBOM・更新／復帰契約が未完了 | 現SBOM対象の.py/PS現物10ファイルが記載ハッシュと不一致。署名正常の最終配布証跡なし。停止時更新・旧版復帰・受付中更新拒否を一体管理する実装／検収なし。旧署名FAILを今回のコード変更で解消済みにしない |
| G-15 | 接続置換のDRAFT凍結が未接続 | _on_connectionは旧dropを無作用にして新ソケットへ置換。_helloはarmed=false、on_session_resetはメニュー等をリセットするだけでDRAFTを凍結しない。既存DRAFTが未凍結なら置換だけで凍結する経路がない。切断時freezeの存在だけで置換時freezeを実装済みにできない |
| G-16 | 受付ボタン開始の無操作タイマー起点が不足 | app.pyはunified_ui.poll(ops)の応答をlast_accepted_atへ反映しない。初期NoneならUI arm後、操作が受理されるまでタイムアウト条件が成立しない。_send(status)とUI操作・手操作を区別した最終安全操作時刻が必要 |
| G-17 | 編集中の予定との差分表示・選択予定への束縛が未完成 | status_textは確定後_last_matchの位置／法線差だけ表示し、DRAFT対active予定の位置・姿勢・開口3差分を更新表示しない。record_performedは未実施候補の最近傍で対応付け、選択active予定IDを確定へ束縛しない。差分計算の部品があるだけではFR-037/039の操作列が完成しない |

G-01/02/04〜11/15/16は計画契約へのソース不一致。実際の全条件での発生頻度や運用影響は未検収。G-13の試験未実施は機能未実装とは別である。

## docs/20：4実装単位

| 単位 | 実装判定 | 根拠／残り |
|---|---|---|
| 1 Cスタンプ | 一部実装 | cstampの仮配置・方向・確定・台帳・レイヤーはある。G-01/02/04〜07 |
| 2 視点接続 | 一部実装 | typed view_commands／TargetGuardはある。SMOOTH_ZOOM主経路G-10 |
| 3 手認識 | 一部実装 | TasksHandRecognizer、決定論形状、SafetyController、typed commandはある。認識喪失の凍結G-08 |
| 4 計画追従 | 一部実装 | PlanTracker、差分、単一ゴーストはある。G-03/04/11 |

## docs/23：10実装単位

| 単位 | 実装判定 | 照合結果 |
|---|---|---|
| 1 起動とパネル | 実装済み（コード） | start_server_session、start_command_server、固定dockの設置と初期受付無効あり。新規起動の実検収は別途未完了 |
| 2 共通契約・結果応答 | 一部実装 | 型・req/seq/ts/session/TTL・応答あり。G-01/02/07/15、再接続時_seen消去で永続QUERY_RESULTなし |
| 3 開始停止・モード | 一部実装 | 非接触arm・stop/menu・準備状態あり。G-08/16、実測による閾値固定は未検収 |
| 4 照準・配置 | 一部実装 | raycast→aim→stamp、無効面／既存DRAFT拒否あり。G-07 |
| 5 編集 | 一部実装 | move/rotate/tilt/reverse/resetコア、方向輸送あり。手入口G-03、通常マウス・版G-01/02、再開G-08 |
| 6 確定・取消 | 一部実装 | revision・同一DRAFT抑止・保存成功後COMMITTED・保存失敗DRAFT・cancel→IDLEはソースにある。G-01/05/06/07。旧稼働F-08はsourceのIDLEだけで閉じない |
| 7 計画・レビュー・監査 | 一部実装 | PlanStore/PlanTracker、再表示／訂正seedあり。G-03〜06/11 |
| 8 回転・ズーム | 一部実装 | 分離感度・deadzone、camera軸回転あり。G-10、視点方式比較・疲労・使用感は未検収 |
| 9 説明・全経路検証 | 一部実装 | docs/28、手形合成モデル／実TCPハーネスあり。G-13、実手H全件・全要求受入は未完了 |
| 10 構成・通信・配布 | 一部実装 | config固定・モデル／manifest／SBOM・配布PSはある。G-14、IT全適合は未検収 |

### 再照合で具体化した13作業

| 作業 | 実装判定 | 根拠 |
|---|---|---|
| 無操作タイムアウト／安全停止 | 一部 | app.input_timeout_s、G-08/16 |
| 設定・割当固定 | 一部 | config.AppConfigと起動時読込。opening/tilt倍率やlatch等はOperationController既定値で構成版へ全値を束縛しない |
| モデル・表面照合 | 一部 | _surfaceとraycastのみ、G-07 |
| 初期方向・リセット | 一部 | orthonormal_basis、initial_placement、reset_direction。手入口G-03 |
| DRAFT中の視点 | 実装済み（コード） | 主menu→view、draft保持、protocolはview操作を許可。手の実検収は別 |
| 保存全項目・精度 | 一部 | template/placement/shape_points/transform保存、G-06/07。全フィールド誤差契約の受入未完了 |
| 計画作成・新版 | 一部 | PlanStore、G-03/04/11 |
| 計画追従・対応付け | 一部 | PlanTracker/_update_ghost/record_performed、G-03/11/17。確定後の差分計算はあるが編集中の3差分更新表示はない |
| 確定記録取消・訂正 | 一部 | seed_draft/correction_ofはある。G-05/11 |
| 結果取りこぼし | 一部 | 同一セッションの_seen照会のみ。G-01/03/06 |
| 基準視点 | 一部 | reset_viewと手records入口あり。用途原文との採否決定の根拠・登録ID選択は確認不能 |
| 性能・使いやすさ | 一部／未検収 | input_diagnosticsはある。G-13、PR-001〜04の完成測定なし |
| 通信・配布 | 一部／未検収 | loopback・memory previewあり、G-14、継続通信監査は未完了 |

### 第2版の追加契約

| 契約 | 実装判定 | 不足 |
|---|---|---|
| 表示済みDRAFT原子確定：版、描画完了、ハッシュ、保持無効化、保存ロック、永続照会、途中終了回復 | 一部 | revisionと保持中再版比較はある。G-01/06、永続照会・表示ACK未実装 |
| 代替マウス／入力所有権：全編集、共通dispatcher、手停止、遅延失効、明示復帰 | 一部 | 通常UI残存だけ。G-02 |
| 計画作成／新版／個別選択・編集・削除／保存 | 一部 | APIあり、手個別入口と所属・復元G-03/04 |
| 理由／順序／スキップ／計画外 | 一部 | reason部品あり、G-03/11 |
| 訂正／撤回／独立監査 | 一部 | G-05 |
| 登録ID保存／読込／結果照会 | 一部 | 単一事前パスとloadあり、手save/query入口なし、改変／モデル照合G-03/06/07 |

## docs/31：統合UI全項目

| 項目 | 実装判定 | ソース照合 |
|---|---|---|
| 固定dock、受付・形状・保持・menu・reason | 実装済み（コード） | UnifiedHandPanel.__init__/refresh |
| カメラ既定非表示・同dock・メモリのみ | 実装済み（コード） | RecognizerUI.preview=false、MemoryChannel、toggle_preview |
| Slicerモードの独立OpenCV/Tk窓廃止 | 実装済み（コード） | app出力分岐。非Slicerモードの表示は対象外 |
| サイズ同dock・10mm・次／仮C区別 | 実装済み（コード） | show_size、size_settings、set_diameter_mm。確定済みCには書かない |
| 同dock開始停止・手開始・共通代替menu | 一部 | poll→opsで同typed path。全通常マウス契約はG-02、確定独立の版はG-01 |
| 詳細マウスtabに収容 | 実装済み（収容） | attach_mouse_widget。全代替操作完成とは別 |
| 古い状態停止表示・前面gate保持 | 実装済み（コード） | refresh freshness、foreground_ok。異常理由の完全表示はG-09 |
| 手順1 共有memory世代／CRC／容量／単一方向 | 実装済み（コード） | MemoryChannel.write/read。多プロセス排他はG-12 |
| 手順2 状態共有・期限ID・許可要求 | 実装済み（コード） | publish、poll、valid_request |
| 手順3 Qtとサイズ／明示preview | 実装済み（コード） | UnifiedHandPanel |
| 手順4 起動設置・既存状態維持 | 実装済み（コード・限定反映記録） | start_command_server/start_server_session、既存反映work/install_corrections_live.py。新規起動検収は未完了 |
| 手順5 破損／二重／単一dock検証 | 一部実施 | test_ui_bridge・docs/31実Qt記録あり。全実手・新規起動・長期は未検収 |

## docs/33：修正仕様の全項目

| 項目 | 実装判定 | 根拠／不足 |
|---|---|---|
| A-1 稼働版・ソース、socket世代・drop順・応答・GUI時間 | 一部 | ソースSHA／稼働反映記録あり。G-12、現プロセス全関数版の一致は確認不能 |
| A-2 replace/drop/close再入、最後の切断停止凍結 | 一部 | _CommandServer再入保護済み、on_disconnectあり。置換時freeze G-15 |
| A-3 MRMLまとめ・描画・status/動作応答の計測 | 一部 | StartModify/EndModify済み、status_msあり。全応答／GUI遅延G-12 |
| A-4 Qtを塞がない段階試験、中断停止復元 | 実装済み（ハーネス） | work/test_long_tcp_20261011.py、finally disarm/close/net記録。前面拒否で復元できない場合は失敗を残す。全状態自動復元保証はない |
| A-5 通常／再生入力切替・排他・接続1本・停止復帰 | 一部 | docs/35手順と実施、単一socketあり。G-12/15 |
| B-1 OPEN_PALM開始はarmだけ | 実装済み（コード） | update非armed分岐、preparing |
| B-2 UI開始も準備状態 | 実装済み（コード） | poll→_send arm |
| B-3 手下げまで操作抑止・実手なし条件 | 実装済み（コード） | preparing、hand_absent |
| B-4 認識／モード／再開で基準点リセット | 実装済み（コード） | shape変化・_send・on_transport_lost→_reset_continuous |
| B-5 最初のフレームは基準だけ、deadzone実測 | 一部 | baselineあり、定数deadzone .002と低速蓄積あり。距離・時間の実測で値決定は未完了 |
| B-6 停止・凍結・不明・複数手0、明示再開 | 一部 | 品質gate／server frozen拒否あり。認識喪失のfreeze G-08、置換G-15 |
| C-1 全9状態見出し・次動作 | 一部 | 状態別guideあり。確認対象詳細／選択待ち見出しG-09 |
| C-2 仮CありTWO無作用理由 | 実装済み（コード） | ops.notice、publish.reason |
| C-3 照準／保持／切替／停止／前面／凍結／通信理由 | 一部 | reasonと形状詳細あり。認識Safety gateの理由・FAULT共有G-09 |
| C-4 同画面復帰、別カメラ前面不要 | 一部 | 単一dock、arm/resumeあり。前面外の専用回復導線は一般reason表示のみ |
| C-5 サーバー成功後のモード、拒否時保持、古い表示排除 | 実装済み（コード） | response.state、_state/client.last_state、freshness |
| C-6 手順入口・8手順図・方向専用図の同期 | 一部 | docs/28追記とpreviewあり。G-13 |
| D-1 実templateとangleでC全体・中心・mm・角度 | 一部 | preview_points／refresh_direction。切れ目と直径・角度は描画するが、計画記載の中心位置記号はない |
| D-2 配置面正面図・3D位置と区別 | 実装済み（コード） | QLabelの注記 |
| D-3 ラベル／制御点で切れ目を隠さない表示 | 一部 | labels false、MRMLバッチ済み。制御点サイズ・全曲面の見え方未検収 |
| D-4 遮蔽補助・深度／浮かせ検証、位置寸法を変更しない | 実装済み（位置を変えないpreview方式）／任意描画は未実装 | depth補助は計画で検証後採否の任意条件、必須未実装とは数えない。レンダラー評価は未検収 |
| D-5 表示だけで中心・面・寸法・版・台帳不変、視点自動変更なし | 実装済み（コード） | previewは読取・QPainterのみ。全角度／サイズ検収は未完了 |
| E-1 関節／掌でグー・親指・つまみ分離 | 実装済み（コード） | classify_shape/thumb_geometry |
| E-2 縮尺・傾きの局所軸、曖昧UNKNOWN | 実装済み（コード） | 指MCP→PIP、欠損／非有限／退化拒否 |
| E-3 保持揺れ・独立次操作・全遷移 | 一部 | GestureLatchあり。別離散shapeの保持だけでも次操作を発火し、画面遷移後「全shape解放必須」の汎用gateはない。実手遷移試験未検収 |
| E-4 グー戻り・メニュー外取消・無断仕様変更なし | 実装済み（コード）／実手未検収 | panel_menu.backとFIST cancel。曖昧握りUNKNOWN。実手の誤取消0は未検収 |
| F-1 合成・模擬・local・TCP・Pixelを区別して実行 | 一部実施 | docs/32/34/36。実Pixel全手形は未検収 |
| F-2 TCP封筒・前面・再接続、入力混在禁止 | 一部 | ハーネスは実client、手順は分離。G-12/15 |
| F-3 既存C復元・版巻戻しなし・試験保存先 | 一部実施 | docs/36前後一致。既存Cの確定なし。隔離保存全経路未実施 |
| F-4 docs・状態・全検収結果更新 | 一部 | docs/35/36・PROJECT_STATUSはある。全V/H/X検収未完了、旧計画の状態文は本照合で明示訂正 |

第3節9状態はC-1、モード・拒否・古い状態はC-3/5、図・手順はC-6、サイズ例外はdocs/31へ対応。第5節の順序1〜5はA→B→C/D→E→Fへ対応している。これらの順序条件を通過済みとはしない。

## 完了状態と是正順序

**実装照合は完了。機能実装は未完了。稼働版への全反映照合と受入検収は未完了。** 全項目を列挙したことは、実装や受入の合格ではない。今回未解決の事項を「テストだけ」と報告した過去の説明は訂正する。

次の実装優先順は、G-01/06（表示済み確定と保存回復）、G-08/15/16（喪失・置換・無操作停止）、G-02（代替／入力所有権）、G-03/04/05/11（全手入口・計画・監査）、G-07/09/10/12（対象・表示・ズーム・診断）、G-13/14（検収・配布）。これは今回の不足の順序整理で、原要求の変更や実装完了宣言ではない。

以降に、原要求74件とAC24件、H/X/Vの全件索引を添付する。機械的なID網羅確認と、意味のコード照合を分けて扱う。

## 原要求74件：個別のコード照合

原文はdocs/03の記載行を示す。以下の「実装済み」は静的コードの対象範囲で、実手・性能・稼働版合格を含まない。

| ID（原文行） | 実装状態 | 根拠／不足 |
|---|---|---|
| FR-001（22） | 実装済み（コード） | OperationController.update/preparing、G-16は無操作解除の別不足 |
| FR-002（23） | 一部 | KNOWN_COMMANDS/typed dispatcherあり。原要求の許可範囲とreset_view等の採否は未整理 |
| FR-003（24） | 一部 | UnifiedHandPanel／input_diagnostics。G-09/12/13 |
| FR-004（25） | 一部 | UnifiedHandPanel／input_diagnostics。G-09/12/13 |
| FR-005（26） | 一部 | 通常UIはあるが共通契約・全操作・所有権G-02 |
| FR-006（27） | 一部 | AppConfig固定読込あり。全割当・パラメーター版束縛は未完 |
| FR-007（51） | 一部 | op_aim/op_stamp・単一DRAFTあり。対象束縛G-07 |
| FR-008（52） | 一部 | 位置／方向コアあり。反転／リセット手入口と方向表示G-03/09 |
| FR-009（53） | 実装済み（コード） | 独立MRMLノードとdraft replace。元モデル／確定レコードへ編集は書かない |
| FR-010（54） | 一部 | state_machine.commitあり。表示済み原子確定／回復G-01/06 |
| FR-011（55） | 実装済み（コード） | cancel→IDLE、仮Cと計画／操作記録の色・ノード・ラベル分離 |
| FR-012（56） | 実装済み（コード） | cancel→IDLE、仮Cと計画／操作記録の色・ノード・ラベル分離 |
| FR-013（57） | 一部 | 通常UIはあるが共通契約・全操作・所有権G-02 |
| FR-014（58） | 一部 | placement/shape/template保存あり。シーン／モデルhash・列ID・時刻源G-07 |
| FR-015（59） | 一部 | 追加監査・correction_ofあり。G-05 |
| FR-016（103） | 一部 | SmoothZoom部品が主Slicer経路に未接続G-10 |
| FR-017（104） | 一部 | SmoothZoom部品が主Slicer経路に未接続G-10 |
| FR-018（105） | 一部 | SmoothZoom部品が主Slicer経路に未接続G-10 |
| FR-019（106） | 実装済み（コード） | フレーム入力なしでズーム送信なし、cameraだけ変更、DRAFT→viewと復帰あり。全実手未検収 |
| FR-020（107） | 実装済み（コード） | フレーム入力なしでズーム送信なし、cameraだけ変更、DRAFT→viewと復帰あり。全実手未検収 |
| FR-021（108） | 実装済み（コード） | フレーム入力なしでズーム送信なし、cameraだけ変更、DRAFT→viewと復帰あり。全実手未検収 |
| FR-022（109） | 一部 | SmoothZoom部品が主Slicer経路に未接続G-10 |
| FR-023（110） | 未完了（受入基準） | G-13。数値の正式合格値を確認できない、未実装機能とは別 |
| FR-024（114） | 実装済み（コード） | state_machine.commit／shape_points、同event_idの点と曲線、reshape/select_event、JSONL append |
| FR-025（115） | 実装済み（コード） | state_machine.commit／shape_points、同event_idの点と曲線、reshape/select_event、JSONL append |
| FR-026（116） | 実装済み（コード） | state_machine.commit／shape_points、同event_idの点と曲線、reshape/select_event、JSONL append |
| FR-027（117） | 実装済み（コード） | state_machine.commit／shape_points、同event_idの点と曲線、reshape/select_event、JSONL append |
| FR-028（118） | 一部 | JSON内部精度保持・既存単体比較あり。固定全項目許容誤差／再読込受入未完 |
| FR-029（119） | 文書に明記 | README／docs/03／docs/23。臨床精度の完了とはしない |
| FR-030（120） | 一部 | integrity付与とcorrection_ofあり、読込検証G-06 |
| FR-031（126） | 一部 | PLANNED／PlanStoreあり、計画所属・個別手編集・永続復元G-03/04 |
| FR-032（127） | 実装済み（コード） | _replace_draft_curve_with_committed/_points_nodeで色・レイヤー・ラベル分離 |
| FR-033（128） | 一部 | PLANNED／PlanStoreあり、計画所属・個別手編集・永続復元G-03/04 |
| FR-034（129） | 一部 | PLANNED／PlanStoreあり、計画所属・個別手編集・永続復元G-03/04 |
| FR-035（130） | 一部 | PlanTracker状態あり。共通レビュー表示・関係復元G-04/17 |
| FR-036（131） | 実装済み（コード） | _update_ghostは単一currentを読取描画し、DRAFTへの移動／確定呼出しなし |
| FR-037（132） | 未実装（主画面の実時間3差分） | G-17。確定後の差分部品だけ |
| FR-038（133） | 実装済み（コード） | _update_ghostは単一currentを読取描画し、DRAFTへの移動／確定呼出しなし |
| FR-039（134） | 一部 | plan_match別イベント保存あり。選択active対象／実績本体への束縛G-17 |
| FR-040（135） | 一部 | skip/reorder/out_of_plan APIあり。手入口・理由束縛G-03/11 |
| IT-001（200） | 実装済み（静的構成）／運用未検収 | loopback＋ローカルモデル＋memory preview。連続外向き通信監査は未完了 |
| IT-002（201） | 一部 | 構成／SBOM／配布PSあり、最終現物の署名・hash一致／停止更新復帰G-14 |
| IT-003（202） | 一部 | 構成／SBOM／配布PSあり、最終現物の署名・hash一致／停止更新復帰G-14 |
| IT-004（203） | 構成あり／現環境未検収 | docs/25・一般ユーザー手順あり。この照合で現プロセス権限を再検査していない |
| IT-005（204） | 一部 | 構成／SBOM／配布PSあり、最終現物の署名・hash一致／停止更新復帰G-14 |
| OP-001（75） | 実装済み（コード） | raycast／aim有効拒否／DRAFT重複拒否、GestureLatch |
| OP-002（76） | 実装済み（コード） | camera-only、rotate_opening角だけ、tilt_plane別モード。docs/36限定実TCP観測あり |
| OP-003（80） | 実装済み（コード） | raycast／aim有効拒否／DRAFT重複拒否、GestureLatch |
| OP-004（81） | 一部 | orthonormal_basisとinitial_placementあり。完全な構成版束縛・初期姿勢の表示G-09 |
| OP-005（82） | 実装済み（コード） | raycast／aim有効拒否／DRAFT重複拒否、GestureLatch |
| OP-006（86） | 実装済み（コード） | camera-only、rotate_opening角だけ、tilt_plane別モード。docs/36限定実TCP観測あり |
| OP-007（87） | 実装済み（コード） | camera-only、rotate_opening角だけ、tilt_plane別モード。docs/36限定実TCP観測あり |
| OP-008（88） | 一部 | reverse_path/reset_direction APIあり、手入口G-03 |
| OP-009（89） | 一部 | reverse_path/reset_direction APIあり、手入口G-03 |
| OP-010（93） | 一部 | 内部rev確定はある。表示済みACK・hashG-01 |
| OP-011（94） | 実装済み（コード） | 保存成功後state変更、失敗時DRAFT、cancel→IDLE。稼働全条件未検収 |
| OP-012（98） | 実装済み（コード） | 保存成功後state変更、失敗時DRAFT、cancel→IDLE。稼働全条件未検収 |
| OP-013（99） | 一部 | freeze/resume部品あり、実カメラ喪失通知G-08 |
| PR-001（208） | 未完了（測定／基準） | inputメタデータ／合成静止画のみ。要求単位の性能測定G-13 |
| PR-002（209） | 未完了（測定／基準） | inputメタデータ／合成静止画のみ。要求単位の性能測定G-13 |
| PR-003（210） | 未完了（測定／基準） | inputメタデータ／合成静止画のみ。要求単位の性能測定G-13 |
| PR-004（211） | 未完了（測定／基準） | inputメタデータ／合成静止画のみ。要求単位の性能測定G-13 |
| SR-001（191） | 実装済み（コード） | classify_shape UNKNOWN、SafetyController intent_valid、typed output／INPUT_MOUSE限定 |
| SR-002（192） | 実装済み（コード） | classify_shape UNKNOWN、SafetyController intent_valid、typed output／INPUT_MOUSE限定 |
| SR-003（193） | 一部 | 品質gate／切断停止はある。認識喪失freeze、置換G-08/15 |
| SR-004（194） | 一部 | deadzone・単コマンド上限あり。速度／ズーム累積制限G-10 |
| SR-005（195） | 実装済み（コード） | classify_shape UNKNOWN、SafetyController intent_valid、typed output／INPUT_MOUSE限定 |
| SR-006（196） | 実装済み（コード） | foreground_ok／TargetGuard。実TCP前面拒否はdocs/36に記録 |
| SR-007（151） | 一部 | 品質gate／切断停止はある。認識喪失freeze、置換G-08/15 |
| SR-008（152） | 一部 | 品質gate／切断停止はある。認識喪失freeze、置換G-08/15 |
| SR-009（153） | 一部 | 確認ページとTHREE再提示あり。全shape解放・表示版・実測値G-01、E-3 |
| SR-010（154） | 一部 | req／draft重複抑止あり。永続索引／途中終了G-01/06 |
| SR-011（155） | 一部 | loopback／許可操作あり。シーン／表面の厳格束縛G-07 |
| SR-012（156） | 実装済み（コード・文書） | 仮C未確定、計画／操作記録のラベル、非臨床注記 |

## AC24件：実装依存と検収を分離

全ACの要求条件を満たす受入は未完了。下表は対応コードの有無／不足であり、受入PASS表ではない。原文の前提・合格条件はdocs/03の各行。

| ID（原文行） | 対応実装と不足 | 受入状態 |
|---|---|---|
| AC-001（162） | 仮配置処理あり、対象束縛G-07 | 全条件未検収、既存部分結果はdocs/27/36 |
| AC-002（163） | 面内回転／傾きあり、実TCP限定確認 | 全条件未検収、既存部分結果はdocs/27/36 |
| AC-003（164） | 表示済み原子確定G-01 | 全条件未検収、既存部分結果はdocs/27/36 |
| AC-004（165） | cancel→IDLEコードあり | 全条件未検収、既存部分結果はdocs/27/36 |
| AC-005（166） | 重複処理あり、永続回復G-01/06 | 全条件未検収、既存部分結果はdocs/27/36 |
| AC-006（167） | 認識喪失／置換G-08/15 | 全条件未検収、既存部分結果はdocs/27/36 |
| AC-007（168） | 通常マウス共通全操作G-02 | 全条件未検収、既存部分結果はdocs/27/36 |
| AC-008（169） | 読込の改変／モデル照合G-06/07 | 全条件未検収、既存部分結果はdocs/27/36 |
| AC-009（170） | raycast可否あり | 全条件未検収、既存部分結果はdocs/27/36 |
| AC-010（171） | 単一DRAFT拒否あり | 全条件未検収、既存部分結果はdocs/27/36 |
| AC-011（172） | 面内回転あり、全単調／誤差受入未検収 | 全条件未検収、既存部分結果はdocs/27/36 |
| AC-012（173） | SmoothZoom主経路G-10 | 全条件未検収、既存部分結果はdocs/27/36 |
| AC-013（174） | camera-only zoomコードあり | 全条件未検収、既存部分結果はdocs/27/36 |
| AC-014（175） | sourceはIDLE。旧稼働F-08を解消としない | 全条件未検収、既存部分結果はdocs/27/36 |
| AC-015（176） | C全形状あり、全メタデータG-07 | 全条件未検収、既存部分結果はdocs/27/36 |
| AC-016（177） | 同IDの読取再表示あり | 全条件未検収、既存部分結果はdocs/27/36 |
| AC-017（178） | 独立ID／order追加あり、途中終了G-06 | 全条件未検収、既存部分結果はdocs/27/36 |
| AC-018（179） | 計画／監査含む復元G-04/05/06 | 全条件未検収、既存部分結果はdocs/27/36 |
| AC-019（180） | レイヤー色／ラベルあり、実手未検収 | 全条件未検収、既存部分結果はdocs/27/36 |
| AC-020（181） | 単一ghostあり、手select_plan_item G-03 | 全条件未検収、既存部分結果はdocs/27/36 |
| AC-021（182） | 編集中3差分表示G-17 | 全条件未検収、既存部分結果はdocs/27/36 |
| AC-022（183） | 選択予定／表示版G-01/17 | 全条件未検収、既存部分結果はdocs/27/36 |
| AC-023（184） | skip理由固定G-11 | 全条件未検収、既存部分結果はdocs/27/36 |
| AC-024（185） | 宣言flagあり、理由とレビューG-11/17 | 全条件未検収、既存部分結果はdocs/27/36 |

## H-01〜12／X-01〜08／V-01〜10：全件索引

試験計画の未実施を機能未実装と同一視しない。コード不足の依存と実施不足を併記する。

| ID | 実装依存・現在地 |
|---|---|
| H-01 | 開始／視点／照準APIあり。G-08/10/16、実手未検収 |
| H-02 | 編集・取消APIあり。反転／reset入口G-03、確定G-01、実手未検収 |
| H-03 | 3件台帳／再表示部品あり。手save/query G-03、読込G-06/07 |
| H-04 | PLANNED配置あり。作成者／所属G-04 |
| H-05 | PlanStore新版部品あり。個別手編集／復元G-03/04 |
| H-06 | ghost・確定後差分あり。編集中差分／選択束縛G-17 |
| H-07 | skip/reorder APIあり。手順序入口・理由G-03/11 |
| H-08 | 計画外宣言あり。理由／レビューG-11/17 |
| H-09 | revoke/correction部品あり。独立監査／元不変G-05 |
| H-10 | freeze/resume部品あり。実カメラ喪失／置換G-08/15 |
| H-11 | 確認ページ／latchあり。全解放・表示版G-01、E-3 |
| H-12 | 保存失敗DRAFT／session内queryあり。永続照会／手入口G-01/03/06 |
| X-01 | revision・req・fsync部分あり。表示ACK／原子回復G-01/06 |
| X-02 | 通常UIあり。共通全操作／引継ぎG-02 |
| X-03 | 型／TTL／前面／品質gateあり。対象／freeze／UI無操作G-07/08/15/16 |
| X-04 | 方向コア／SmoothZoom部品あり。主ズーム接続G-10、実手受入未完 |
| X-05 | 保存／PlanStore部品あり。改変／復元／元不変G-04/05/06/07 |
| X-06 | input_diagnosticsあり、完成した性能測定G-13なし |
| X-07 | 署名／SBOM成果物あり。最終版不一致G-14 |
| X-08 | loopback／memoryあり。連続監査／更新復帰G-14未完 |
| V-01 | 開始準備コード・模擬30回あり、全実ツール／実手未検収 |
| V-02 | aim/stampコードあり、4条件各10回／実手未検収。G-07 |
| V-03 | rotate実TCP2周期あり、左右各10回／実手未達 |
| V-04 | tilt分離実TCP2周期あり、各10回／実手未達 |
| V-05 | classifier改修・合成12条件あり、全距離／傾き／実手未検収 |
| V-06 | latchあり、全shape解放E-3と実手未検収 |
| V-07 | 置換10回／通常600秒接続観測あり、編集600秒未達。置換freeze G-15 |
| V-08 | preview実描画と元幾何一致あり、全角度／変更値未検収 |
| V-09 | 確定／cancel部品あり、G-01/05/06、隔離全試験未完 |
| V-10 | 基本APIあり、手入口不足G-03等、実手通し未検収 |

## 照合範囲の網羅確認

docs/20の4単位、docs/23の10単位・13追加作業・第2版追加契約・74要求・24AC・H12/X8、docs/31の7完了条件・5手順、docs/33のA〜F細目・9状態・V10を上表に割り当てた。docs/23の決定事項は、手形／座標／保存／基準視点／署名／性能・権限・臨床の6種を各該当行に引継いだ。臨床責任・承認・本人認証等は未決であり実装照合で解消しない。

74要求＋24AC＋30シナリオのID欠落0をスクリプトで確認した。これはIDの構造自己検証で、意味の独立レビューや機能完成ではない。ソース行とSHAは機械抽出JSONを正確な参照点にする。


## 主なソース参照点

- [hand_menu.py:HandMenu](C:/Projects/Cardiac-CT-Motion-Control/prototypes/cmos-motion-poc/hand_menu.py:40)
- [op_controller.py:_panel_select](C:/Projects/Cardiac-CT-Motion-Control/prototypes/cmos-motion-poc/op_controller.py:276)
- [command_protocol.py:_hello](C:/Projects/Cardiac-CT-Motion-Control/prototypes/slicer-cstamp/command_protocol.py:156)
- [CStampModule.py:op_commit](C:/Projects/Cardiac-CT-Motion-Control/prototypes/slicer-cstamp/CStampModule.py:1041)
- [CStampModule.py:op_revoke_event](C:/Projects/Cardiac-CT-Motion-Control/prototypes/slicer-cstamp/CStampModule.py:1277)
- [CStampModule.py:_on_connection](C:/Projects/Cardiac-CT-Motion-Control/prototypes/slicer-cstamp/CStampModule.py:1699)
- [ledger.py:verify_integrity](C:/Projects/Cardiac-CT-Motion-Control/prototypes/slicer-cstamp/cstamp/ledger.py:70)
- [state_machine.py:commit](C:/Projects/Cardiac-CT-Motion-Control/prototypes/slicer-cstamp/cstamp/state_machine.py:230)
- [unified_hand_panel.py:refresh](C:/Projects/Cardiac-CT-Motion-Control/prototypes/slicer-cstamp/unified_hand_panel.py:162)
