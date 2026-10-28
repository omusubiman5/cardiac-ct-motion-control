# SOL追加調査報告書

追補：[重点調査docs/43](43_focused-motion-investigation-report.md)。合成グーの傾きによる親指誤判定とメニュー無反応の連鎖を再現。実手原因の確定、統合前後の悪化原因、過去17件の根本原因は未確定。今回の未検収項目を合格へ変更するものではない。

2026-10-11。[追加調査依頼書docs/41](41_sol-additional-investigation-request.md)のI-01〜09に基づく。修正実装計画は今回作成していない。

## 結論と実施範囲

追加調査で、状態鮮度異常を起こし得る同期待ちの構造、配布の別パス認識漏れ、試験runnerの終了判定不足、報告件数の固定記載を確認した。一方、古い表示版の確定拒否は実Qtの隔離試験でも機能した。全てを製品コード不具合として作り直す根拠はない。

I-01〜09に調査結果と未取得情報を記録した。ただし、**全調査項目の実機／実手検収が完了したという意味ではない**。過去17件の鮮度FAILの根本原因、全通信順序条件、手／マウス全列・4喪失条件、実手のグー誤認識、完全通信・保存先監査、署名後配布は未確定／未実施の範囲を残す。

実施したこと：原文・実装・既存JSONの照合、実コードを用いた隔離自己検証、合成シーンの実Slicer／Qt／保存観測、実プロセスのOS接続表とTokenElevationの読取。患者・カメラ画像を保存していない。製品ソース、通常仮C、台帳、署名設定への修正・反映はしていない。

## 対象版と証跡

- 原文：README、docs/03 FR-001〜006とC操作要求、docs/23 AC-007・H/X・完了ゲート、docs/33 V-01〜10。追加の調査条件はdocs/41、既存実装の依頼正本はdocs/38。
- CStampModule SHA256は`85155948c34abbc640b0eb24fb6462d078cca3d321fef138a11a7b20e05c7e1e`で先行報告と一致。対象ソース・runtime.json・旧plans.jsonlの開始／終了hashは[開始記録](../work/sol-investigation-20261011-additional/source-baseline.json)と[Qt試験後の終了照合](../work/sol-investigation-20261011-additional/post-qt-preservation.json)に保存。一致=True。終了時の通常共有状態も受付停止・接続中。
- 配布候補は`artifacts/releases/20261011-181915`。manifest hashは`e07b96b73dcf54e69e2c805e553b94e6d431bf311e7011acdbef0a2c3d235981`。[構成読取](../work/sol-investigation-20261011-additional/release-contract-observation.json)。今回6383ファイルの照合を再実行したわけではない。
- 診断器は`work/sol-investigation-20261011-additional/`に限定。`investigate.py`と`metadata.py`は通常ポート・カメラへ接続しない。`qt_probe.py`は既存合成bootstrapを実行した後、所有fixtureのQt threadに400ms待ちと版変更を追加する。製品ソースは変更しない。この注入はタイミングを意図的に変えており通常運転の性能測定ではない。
- 通常Slicerは実測PID30896。認識側はlauncher52916と実Python22620。開始時共有状態の読取はarmed=False／connected=True。Qt fixtureは別PID28404・専用18979で1個だけ起動し、終了後のOS照会は通常Slicer30896のみ。通常アプリへの操作要求やUI入力は発行していない。通常シーンの全幾何を今回再採取したという主張はしない。

## I-01 状態鮮度17件の切り分け

**原要求：** docs/03 FR-003/004、docs/33 V-07、docs/38 W-04/07。質問は、認識／通信／UI更新／観測のどこが止まったか。

既存2993サンプルを再集計した。先行FAILの17件は415.875〜419.079秒で連続し、elapsed/freshを除く診断値は全て同じ1種類。connected=Falseは0件。全観測の読取間隔は約0.187〜0.204秒で、観測器自身がこの間に長く停止したという説明を支持しない。最終2993件はfresh異常0件。[集計](../work/sol-investigation-20261011-additional/freshness-existing.json)。この事実だけでは発行側停止と壁時計の異常を区別できない。

実装経路は`app.py`の主ループでcapture.read→鏡像反転→推論→分類／controller更新→`RecognizerUI.publish`。publishは同じ呼出経路で同期`ops._send('status')`を待ち、その後に壁時計ts付き状態を書き込む。`session_client.py`のsocket timeoutは個々のrecv待ちの制限であり、要求全体の絶対deadlineではない。

追加自己検証：

| 条件 | 実測結果 | 証跡 |
|---|---|---|
| 実publisher＋合成status待ち2.3秒 | 待ち中は状態不変、age=2.102秒でfresh=False、完了後fresh=True。正常対照publish約0.113ms | [publisher実験](../work/sol-investigation-20261011-additional/publisher-delay-experiment.json) |
| 実client._roundtrip＋隔離socketpairの小刻み応答 | recv timeout0.2秒でも応答完了1.106秒、例外なし。全要求の時間制限ではないことを確認 | [socket実験](../work/sol-investigation-20261011-additional/socket-deadline-experiment.json) |
| 実Qtの400ms停止 | heartbeat最大間隔536.212ms。所有fixtureだけで実event loop停止を観測 | [Qt実験](../work/sol-investigation-20261011-additional/qt-fixture/qt-probe-results.json) |

**判定：** 同期status待ちがUI状態の鮮度を悪化させる機序は自己検証で支持された。個々のrecv timeoutを全要求の上限と扱えないことは確定。過去17件の直接原因は未特定。通常Slicer多重起動、capture停止、推論停止、壁時計変化が原因だったという因果は未実証。

**修正要否／候補：** 観測器の記録補完は必要。全要求deadlineとUI発行の通信待ち分離は検討候補だが、正常経路・停止条件への影響を評価してから計画化する。`app.py:330`は既に前回の`ui_status_ms`をinput_diagnosticsへ載せる。先行観測器がこれを保存していないため、「status時間を計測するコードが全くない」とは言えない。新設より既存計測の保存・連番・新旧の対応付けを優先する。

**未取得：** 先行runの生ts/age、各段階の同時刻、Qt heartbeat・プロセス負荷。失われた履歴は復元不能。次の最小実験は発行連番・単調／壁時刻・capture/推論/status終了・Qt heartbeatを同じ要求へ対応付ける診断。通常600秒の再実行だけでは原因を識別できない。

## I-02 実Qt遅延と表示版確定

**原要求：** docs/23表示版束縛・X-01/03、docs/38 W-05。既存render-holdはACK関数を無操作へ置換するため実Qt停止ではない。

実経路は、`_CommandServer._read`で受信行→dispatcherのsession/seq/TTL/所有権等の照合→op編集→`_update_draft_curve`でMRML点更新とsnapshot要求→VTK EndEventで現在draft/rev/実点を照合しACK→`op_commit`の`_require_displayed`→保存lock→原子台帳。このQt受信処理は同期呼出しであり、単一TCP内のバイト順そのものが自動で逆転する構造ではない。

今回の実Slicer試験は、所有合成球に直接APIで仮Cを作り、rev0の描画要求→Qt thread400ms待ち→同じcallback中にrev1編集→古いACK／確定を試行→実描画→新しい版確定とした。UI/hand/TCP envelopeを通した検収ではなく、実Qt／描画／保存を用いた自己検証である。

- 古いACK受理=False、古い確定拒否=True（display not acknowledged or save in progress）。保存増分0件。
- 実Render EndEvent後のrev1表示を確定し、保存1件、stored_revision=1。
- headlessの実DisplayContractでも旧ACK拒否、旧確認拒否、新確認受理を再確認。[契約実験](../work/sol-investigation-20261011-additional/display-contract-experiment.json)。

**判定：** この版変更・遅延経路では保護が成立し、修正すべき製品不具合を再現しなかった。先行「ACK保留のみ」から、実Qtを止めた追加証拠を取得した。

**修正要否／候補：** まず試験器追加。表示契約の作り直しは不要との暫定判定。`tools/completion_fault_test.py`・bootstrapの試験条件拡張が候補。

**未取得：** TCP受信と異なる接続世代、遅延編集が確定より後に実行される列、確認中の計画／理由／監査対象変更の全組合せ。今回の直接API試験にはsession/req束縛の合格主張を付けない。次はdispatcherを通す遅延・世代変更列で保存版を照合する。

## I-03 手／マウスの経路と4喪失条件

**原要求：** docs/23 AC-007/X-02、docs/33 V-10、docs/38 W-06。ASTから[操作実装対応表](../work/sol-investigation-20261011-additional/operation-source-map.json)を採取。構文上の接続は動作合格ではない。

| 操作群 | 手経路 | マウス経路／共通処理 | 調査判定 |
|---|---|---|---|
| 開始・停止・再開 | controllerの保持／準備、typed arm/disarm/resume_draft | handoverボタン→claim_input→arm、凍結仮Cならresume_draft | 接続あり。操作列の意味比較が必要 |
| 配置・表面移動 | aim/stamp/move_draft | VTK click／MouseMove／release→同じdispatcher | 連続ドラッグコードあり、実ドラッグ成立は未検収 |
| 開口・傾き・反転・リセット | 編集メニュー→rotate_opening/tilt/reverse/reset_dir | ボタン／slider→同じ命令 | 接続あり。全喪失条件との組合せは未検収 |
| 確認・確定・取消 | 確認snapshot→commit/cancel | Qt Yes/No→同じdisplay identity/hash、cancel | 基本実画面証拠あり。全条件比較なし |
| 計画作成・新版・項目編集／追加／削除／並替 | RECORDS→選択値束縛→typed命令 | mouseAction／mouseChoice→onMouseAction→同じop | 入口あり。全操作列を通した同等性未検証 |
| 計画版・理由・作成者・保存先 | 動的選択ページ | 動的comboとparams構築 | 選択値が正しい対象へ束縛される全組合せは未検証 |
| 記録選択・再表示・訂正・撤回・監査 | review／recordsメニュー | review_pick／選択操作→同じop | 基本入口あり。監査・理由変更中の比較が不足 |
| 保存／読込・前要求照会・視点 | typed commands | UI選択／通常カメラ操作 | 接続あり。全項目意味比較が不足 |

マウス所有権取得はsessionを失効し、手要求は所有権で拒否する設計。`onMouseHandover`はclaimだけでなくarmと凍結仮Cのresumeも一つのボタン操作で実行する。これを「所有権だけを変えて後は無操作」と説明すると実装と食い違う。今回この複合操作が原要求違反かを断定せず、利用者に見える再開意図と説明の照合を残す。

**判定：** 表面ドラッグは未実装ではなく実UI検証不足。全列／4条件の不足は[既存結果の再集計](../work/sol-investigation-20261011-additional/coverage-metadata.json)で確定。遮蔽、手無効、カメラ断、通信断を今回実運転で作っていないため、4条件成立は未取得。

**修正要否／候補：** 操作全列・4条件・引継ぎ後の古い手要求の比較試験が必要。構文上の入口があることを理由に全実装完了としない。差が出た処理だけ修正対象へ進める。主候補はWidgetのhandover/onMouseActionとop_controller、入力所有権の試験器。

**比較規則：** 時刻・試験ごとの生成ID・入力手段は対応表で正規化可。対象、順序、状態遷移、世界座標、方向、版/hash、理由、監査リンク、保存件数は除外不可。次の実機比較に適用する規則であり、今回比較成功の主張ではない。

## I-04 グー／親指と実手記録

**原要求：** docs/33 V-05/06/10、docs/23 SR-001/002。`gesture_fsm.classify_shape`は2D landmarkの指軸、親指角145°、length_ratio、outside_ratio、forward_ratioで分類し、曖昧領域はUNKNOWN。鏡像反転は`app.py`で推論前に実施する。分類自体はhandednessの左右ラベルを使わず2D幾何で判定する。側面／遮蔽で2D投影が変わるため、左右反転の有無だけで実手精度を説明できない。

分類→valid_obs→gate→OperationControllerの保持／解放→メニュー→typed要求→Slicer拒否という切分け点を確認。thumb_geometryの数値は取得されるが、`recognition_detail`の表示は手数／信頼度が主体。コマンドtrial-logは要求中心で、480提示に正解意図・認識・無作用・再試行を一対一で対応付ける実手試験runnerではない。

H/V22件と480件は全NOT RUN、不明／遷移0行。生成器にはexpected_intent・actual_responseの空欄があるが、`create_completion_trial_matrix.py`は表作成のみ。中断／再試行・意図の入力と認識サンプルを対応付ける運転導線は、調査対象のappと生成器では確認できなかった。

**判定：** 実手受入の記録・運転準備不足。現在のグー→親指を今回実手で観測していないため原因未特定。閾値を直ちに緩める根拠はない。

**修正要否／候補：** 最小実手診断の記録導線を準備し、利用者意図・親指4指標・分類・保持・発行命令・拒否を結ぶ。実手の提示が必要。試験開始前に担当がツール起動／表示／記録を準備し、グー→手下げ→親指→手下げの短い比較で再現を取る。今回その運転導線の製品実装や実手測定はしていない。全480試行は別の本受入。

## I-05 旧計画の復元可能範囲

**原要求：** docs/23 X-05/FR-034、docs/38 W-03。原本hashは`eeb1fefa5ecd770e0a59f8e74a92d0b9e00ef608bd79c8c30152dadcf9393821`で一致。[行別調査](../work/sol-investigation-20261011-additional/old-plan-investigation.json)にidentity／keys／欠落を保存した。

旧plan_created／plan_revision行にitems・created_ts・approval等が欠けている。現行PlanStore.restoreは保存版ごとのitemsと順序を使い、integrityだけではこの欠落を補えない。plan_idとversion等の識別値は読めるが、過去の幾何・承認状態を確定できない。

当該旧plan IDに限定し、workのsol-/completion-ディレクトリー内plans.jsonlを検索した。同じ旧IDを含む候補は0ファイル。[限定バックアップ検索](../work/sol-investigation-20261011-additional/scoped-plan-backup-search.json)。PC全域や別プロジェクトの全探索ではない。

**判定：** 調査範囲の原記録から復元不能。旧保存形式の不足が確定。読み込めない原因を現行読込機能だけの不具合とは扱わない。

**修正要否／候補：** 過去値を創作する移行は不要／不可。診断表示と新規台帳準備の導線は別途実UI確認。プロジェクト外の正当なバックアップの有無は未取得で、保管担当の確認が必要。

## I-06 プロセス管理・試験終了判定・UI入力先

**原要求：** docs/38 W-05/09の隔離・cleanup。既存runnerは排他lock、既存fixture拒否、ready前失敗時の起動時刻＋script照合、例外時finally終了を持つ。closeツールはready PID・script・作成時刻を照合する。これらは通常Slicerを終了対象にしない。

追加で見つけた不足：`run_completion_fixture.ps1`のcrash_before/crash_afterは`completion_slicer_crash_test.py --stage inject`だけを実行し、共通末尾で「Test passed」を出す。injectは終了直後の台帳を確認するが、**再起動と--stage verifyをrunner自身は実行しない**。過去の別PID再起動結果JSONは有効な別証拠であり、現runner単体のPASSを再起動検収と読むのは誤り。

今回のQt診断runnerは既存管理のlock／単独起動／finally所有PID終了をwork内で適用した。正常終了後はSlicer1個。起動失敗・強制中断・全cleanup障害を今回は注入していない。

UI入力不成立と座標drag誤入力は既存結果で確認した。物理ドラッグをslider値設定の成功で置換できない。過去8個全ての起動履歴は今回再構成できず、既存管理を通らない起動経路の履歴は未確定。

**判定／修正候補：** crash runnerのinject／再起動verifyと終了表示の区別は修正必要。プロセス管理そのものは既存対策＋未試験条件が残る。UIは座標依存を減らし入力直前の実対象・結果確認を試験側へ追加する。製品UI不具合とは別分類。

## I-07 対象プロセス権限・通信／保存先

**原要求：** docs/23 IT-001/004・X-08。今回は実対象TokenElevationをOpenProcess(PROCESS_QUERY_LIMITED_INFORMATION)／OpenProcessToken(TOKEN_QUERY)で読み、設定変更なしで採取した。[実トークン結果](../work/sol-investigation-20261011-additional/target-token-observation.json)。

Slicer30896、認識launcher52916、実Python22620の3件とも読取成功・token_elevated=False。先行の観測者自身の非管理者判定から、一段進んで実対象の非昇格を確認した。ただし権限の全内容や一般ユーザー全機能の検収ではない。

[OS接続表スナップショット](../work/sol-investigation-20261011-additional/process-observation.json)では対象の外部Established TCPは0。間欠照会であり短時間TCP、UDP宛先／payload、ファイル書込先の全履歴は取得していない。

**判定／修正要否：** 非管理者稼働の証拠不足は対象トークン分を補えた。通信・保存先の完全監査は未達。製品の外部送信を検出したという結論はない。

**残る情報・手段：** TCP/UDP接続先のevent-based OS tracing、対象PIDのファイル書込先eventが必要。候補はWindows ETW／既存の管理監査ツールだが、イベントの有効化権限・PID識別・payload非収集・欠落数を事前確認する必要がある。今回この採取環境は構成せず、権限昇格もしていない。既存ソース照合や単発接続表だけでX-08を閉じない。

## I-08 配布・署名以外の不足

**原要求：** docs/23 X-07/08、docs/38 W-08。外側の起動／更新scriptとmanifest catalogの署名を入口で検証し、catalogがmanifest hashを束縛する。payload内scriptを後から署名し直す方式ではなく、外側署名とdetached catalogで固定payloadを束縛するため、現契約は署名でpayload hashが変わる循環を避けている。署名対象・順序は候補manifestへ記録済み。

署名実観測は起動script、更新script、catalog全てNotSigned。[署名読取](../work/sol-investigation-20261011-additional/signature-observation.json)。確認したdocs/38・prepareコードに具体的な正規署名者／承認証明書の識別はなく未指定。秘密情報の探索・変更はしていない。

| 追加所見 | 根拠・判定 | 修正／検証候補 |
|---|---|---|
| 別パス認識／再生の停止判定漏れ | 両PS1はPython argvに`Cardiac-CT-Motion-Control.*(app.py|replay)`を要求。合成argvの`C:\Distribution\payload\cmos-motion-poc\app.py`／replay.pyは一致=False。docs/38は別パス入力も検査対象。[フィルター実験](../work/sol-investigation-20261011-additional/release-process-filter-experiment.json)。現在の候補の配置場所ではなく、別パス条件への実装不足 | scriptとプロセス実体／lease／選択payloadに基づく識別へ改善。別場所の無関係Pythonを全部止める方式は不可 |
| 起動readyの証拠粒度不足 | endpoint constructorは接続確認値なしにphase=normalを書き、起動PS1はphase/作成時刻/argvだけを判定してarmed=Falseを固定出力。[constructor実験](../work/sol-investigation-20261011-additional/startup-readiness-experiment.json)。ただしapp.pyはconstructorより前にhello成功を要求するので、**初回接続を全く確認しないという解釈は誤り** | 起動時helloの証拠と、その後もalive/connected/armed=Falseであるreadyを区別しnonce/PIDへ束縛。実際の誤成功は今回未再現 |
| 更新と起動の検査範囲差 | activateはcomponent/SBOMを検査するがruntime_dependencies/config/externalは起動側で検査。壊れた依存をactivate時点で必ず拒否する仕組みではない | activationとstartupの成功定義を明記し、依存差を含む署名後試験。直ちに誤った稼働が始まるという意味ではない |
| 起動失敗のpointer復帰 | startup catchは所有child終了のみ。previous pointerの自動復帰はなく、activate -Rollbackが別操作 | 自動復帰必須とは原文から断定しない。既存正常pointer保護と手動rollbackの失敗時状態を実測し、説明と実装を一致させる |

**判定：** 署名待ち以外にも、別パス停止判定の修正とready契約の検証補強が必要。正規署名後に停止更新→選択版起動→版照合→停止→rollback→旧版起動を試す必要がある。今回は署名を迂回せず、実配布を起動／activateしていない。

## I-09 件数・版・未解消Fと報告生成

**原要求：** docs/23完了ゲート、docs/38 W-09、AGENTSの証拠区分。要求追跡CSVは98行。行数は要求合格ではない。

マウス結果のchecksは13件、false0件。報告生成器の本文に12を固定記載していたためdocs/39・36と不一致。これは件数の転記不具合であり、実機検査の増加ではない。`section()`はSOL-CURRENTの中身を置換するため、同ブロック内の手追記は再生成で失われる。ブロック外の追加調査節は削除されないが、生成された現在判定が前に挿入されるので表示順も変わる。

| F | 既存証拠から維持できる範囲 | 修正計画の前に残る具体情報 |
|---|---|---|
| F-01 | 永続照会・保存後切断、今回の実Qt旧版拒否 | 通信世代・全順序列と実手復旧 |
| F-02 | 部分行・改変・重複・不正integrityの拒否 | 原文に列挙した不正ファイル条件の網羅対応 |
| F-03 | pending監査と独立confirm_audit | 実手での独立確認と対象変更中の拒否 |
| F-04 | 元イベント不変・派生記録の個別証拠 | 訂正／撤回／復元の全保存項目比較 |
| F-05 | 新形式の保存版1〜4復元・比較 | 全計画／監査列、旧データの正当な外部バックアップ有無 |
| F-06 | 理由の対象／版／項目束縛の実装 | 理由変更／残留／対象変更の全列と実手 |
| F-07 | 10入口の合成メニュー再生 | 全通し実手とマウス同等性 |
| F-08 | cancel→IDLE、台帳不変の個別証拠 | スタンプ直後／編集後の実手取消 |
| F-09 | 配布現物照合・NotSigned拒否 | 今回の別パス所見、正規署名・配布往復 |

**判定／修正候補：** 文書生成はJSONから件数・版・実施範囲を取得し、重要な追加所見を生成元へ接続する修正が必要。過去f094/59cc版の結果を最終851版の全経路合格に拡張しない。独立検収の実物は未取得で、この調査も実装担当の自己検証を含む。

## 修正実装計画へ渡す材料

| 分類 | 今回得られた材料 | 次の扱い |
|---|---|---|
| 製品／配布コードの具体的不足 | 別パス入力の停止判定、readyの現在状態証拠不足 | 原文条件に結び付けて変更対象を具体化可能。署名なしの読取所見と署名後の実測を分離 |
| 原因未特定・構造上の候補 | 同期status待ち、要求全体deadline不在 | 過去FAILの断定を避け、計測補完と制御方式評価を別工程化 |
| 試験器の不足 | 全順序条件、4喪失条件／全列比較、crash runnerのverify未接続、実手runner | 製品を作り直す前に該当試験を実行できる形へ補う |
| 文書生成の不具合 | 12固定値／実際13、現在節の手追記置換 | 動的件数と所見保持の修正対象として具体化可能 |
| 修復不能・外部条件 | 旧items履歴欠落、正規署名者未指定、本人意図／実手、独立検収 | 所属する項目だけに依存を限定。他の実装・試験の停止理由にしない |

依頼書の「全Iに結果または未取得理由」は満たした。修正計画に必要な材料は増えたが、全原因確定は未達。残る未取得を計画上の追加計測／検証へ明示すれば計画化できる。今回は結果評価に渡すまでとし、製品コード修正・通常反映・修正計画作成は行っていない。
