# 実地テスト結果 — FIELD-20261010-01

## 修正版追試（2026-10-11）

[テスト計画docs/35](35_corrected-hand-control-test-plan.md)に沿って実行し、[結果docs/36](36_corrected-hand-control-test-results.md)へ全証跡と未検収を記録。自己検証257件と合成モデル12条件は通過。実接続置換10/10、Pixel通常接続600.27秒で通信喪失0。受付中45サンプルを観測したため停止継続は不合格、意図は未確認。

実TCPの10分反復は11.64秒／72.89秒で前面条件に拒否され未達。開口回転・傾き・復元2周期、実Slicerの幾何とモード表示は限定条件で成立。C・カメラ・台帳の前後一致を確認し、通常Pixel認識と停止・凍結へ戻した。実手のグー誤認識や全通し、既知F-01〜09は今回の結果で閉じない。

## 追加是正：継続するグー→親指誤判定（2026-10-10）

本人の継続報告を受け、前回3条件全てに合致する「グーの側面に沿ってまっすぐ見える親指」を自作入力で再現。手首から指の付け根へ向かう軸に沿った突出量を追加し、付け根より指先方向へ出る親指と側面に置いた親指を区別。側面形と左右反転を追加し自己検証93件合格、認識アプリへ反映。実手解消は再確認待ち。

UI性能切分けでは入力実サイズ1280×720、手なし時約24〜26fps、推論約19〜21ms、定期照会約1〜4ms。画像縮小で認識している状況ではないが、この計測をグー認識の実手改善や統合前後の精度比較合格にしない。根拠はwork/recognition-pixel8a-20261010-193535.stdout.logの入力診断。

## 追加是正：グーの親指誤判定（2026-10-10）

最終自己検証91件。伸ばしかけた親指はUNKNOWNとして無作用にし、曖昧入力をグーとして仮C取消へ流さない試験を追加してから稼働反映した。以下の90件は中間確認数。

本人の誤判定・メニュー閉鎖不能を受け、距離単独の親指条件をIP関節伸展と手のひらからの分離を併用する条件へ変更。自作の曲がった親指入力がグーになること、メニュー戻り／閉鎖までを自己検証し認識側90件合格。古い親指の入力例も関節が伸びた形へ訂正。統合パネルの案内を下位一覧では「前のメニューへ戻る」、主一覧では「閉じる」へ更新し、稼働反映と案内テキストを確認した。認識ログへ画像なしの親指関節角度と比率を追加。本人の実手再検収は依頼中であり、自己検証を実手の合格と扱わない。

## 追加確認：単一Slicer UIへ集約（2026-10-10）

本人の実装指示により[計画と実装結果](31_unified-slicer-ui-plan.md)を作成。受付・メニュー・サイズ・必要時のカメラを固定ドックへ統合し、独立カメラ窓／最前面HUDを廃止。実窓一覧はSlicer本体1件。実マウスで開始・停止、一覧開と項目送り、サイズ設定展開・閉鎖を確認。カメラは実Qt表示部の非空Pixmap320×240到達を確認し、画像は保存していない。自己検証は認識84件、Slicer143件合格。長期運用、全実手操作・保存までの通し合格とはしない。Slicer実終了後のプロセス終了、新規起動、詳細マウス全機能の再試験は未実施。

## 追加確認：受付停止の可視化（2026-10-10）

本人の停止中・反応なし報告に対し、認識ログは手形検出あり・arm送信なし。「開いた手」表示だけでは連続保持の成立を証明できない。認識／開始保持0.0〜1.5秒／手数・信頼度／切断をパネルへ表示し、開始条件を変更せず診断可能にした。自己検証80件、既存Slicer上の実パネル表示を確認。認識アプリのみ再起動、Cとシーンを維持。本人がSlicerの前面維持を難しいと報告したため前面へ戻し、認識窓へ切り替えず確認する案内へ訂正。実手受付開始の成立は未確認。

## 追加確認：サイズ設定の閉じるボタン修正（2026-10-10）

本人が閉じないと報告。実Slicerコンソールでclicked(bool)のFalseが引数なしcloseへ渡されるValueErrorを観測し、Python関数経由へ修正。既存プロセスでUIのみ再読込し、ボタンシグナルの自己検証で閉鎖と寸法・仮C版不変を確認（work/size-dialog-close-check.json）。さらにComputer Useで表示中の「閉じる」を実クリックし、ダイアログ消失を画面とツリーで検収。ソース修正だけを実操作の成功と扱っていない。10mm設定を維持し、シーン再読込・台帳書込なし。

## 追加確認：Cサイズ設定の実画面・実形状（2026-10-10）

本人指定の直径10mmと、サイズ設定はマウスでよいという訂正を実装・稼働反映した。実設定画面で編集再開→現在仮Cへの適用→適用を実行し、次のCと現在仮Cが10mmであることを確認。表示中仮C33点の中心からの距離は約5mm、版1。証拠はwork/size-settings-live-result.jsonとdocs/30の設定画面画像。元モデルの寸法校正、設定ボタンからの再開閉の実クリック、実手による一連操作、C記録保存は別の検収対象。サイズ設定の成功を既知の監査・保存不合格の解消としない。

## 追加確認：承認画面案の一覧・階層メニュー（2026-10-10）

本人指定の画面案に合わせた新UIを実装し、認識アプリへ反映した。詳細・描画証拠は[実装報告](29_hand-menu-ui-implementation.md)。自己検証79件合格、合成状態での実装ウィジェットの描画を確認。稼働アプリの自作HUDだけを取得し、編集一覧・停止中・仮Cありの実表示も確認した。新しい実手でのメニュー選択・配置・確定の通し試験は未実施。既知の保存・監査・状態遷移の不合格を、このUI更新で合格へ変更しない。

実施日：2026-10-10（JST）  
対象計画：[実地テストプラン第1版](26_field-test-plan.md)  
結果：**全体未合格。安全・保存・操作メニューに不合格があり、実手のC確定・計画・訂正試験を中止／保留した。**

## 追加確認：Pixel 8a接続後の視点操作不成立（2026-10-10）

- 本人報告「3Dスライサーが反応しない」に対し、USBカメラAndroid Webcamの親シリアルをPixel 8aのADBシリアルと照合。認識アプリの実ログで手1件の検出を確認したが、受理コマンド0件。カメラ接続だけを操作成功と扱えない。
- 実Slicerのhello/status応答で`armed=false, mode=review`を確認。視点操作には開始操作とviewモードが必要。認識アプリには受付無効でもローカル認識品質だけでEXECUTINGを表示し、初回の状態欄をNoneと出す不具合があった。
- `app.py`の表示／診断を修正：初回もクライアント保持のSlicer状態を表示し、受付無効／切断を優先表示。開始待ち説明、実際の手形、拒否理由をログに追加。hello拒否時は起動を失敗させる。FR-001とSR-001/002/006の安全ゲートを緩和していない。
- 実TCP確認1回目はモード変更がnot armed、回転がtarget window is not foregroundで拒否。`work/slicer-live-view-command-check.json`に保持。2回目はWin32の前面PIDをSlicer PID30896と照合してhello→arm→select_mode(view)→回転dx=1→逆回転dx=-1→disarmを実施し、全応答ok=true。`work/slicer-live-view-command-check-2.json`。これは自作入力による実ツールの受理確認であり、実手・目視の画面反映確認ではない。
- 関連単体33件合格、表示状態の合成自己検証合格。修正版認識アプリをPixel 8a番号1で再起動し、実ログ`disabled / armed=False / mode=view`を確認。Slicerを前面へ戻した。最新起動ログは`work/recognition-current-launch.json`。
- 実手での開始→回転はこの時点では本人の提示／観測待ち。全体未合格と既知の製品不合格は維持。無効時select_modeの拒否は現行ソースのPRE_ARM_COMMANDSとも整合する。先の調査でFOREGROUND_EXEMPTをPRE_ARM許可と取り違えた判断は訂正する。前面不要と受付不要は異なる。
- その後の実カメラ・実手ログで`armed=True, mode=view`へ移行し、受理コマンドが0から266件へ増加。PINCH/POINT/OPEN_PALMの検出時にも件数増加を観測（OPEN_PALM時241→260）。この間、モデルによる追加コマンド注入はしていない。実手→認識→Slicer受理までを確認した。画面の回転／パン／ズームの見た目と意図への一致は本人回答待ちで、Hケース合格とはしない。

## 追加確認：基本視点の本人確認と離散メニューの修正（2026-10-10）

- 本人から「PAN、回転、ZOOMはOK」と実画面の操作成立を受領。基本3操作は本人確認済み。性能閾値やH-11全条件を満たしたという意味ではない。同時に親指・2本指・3本指・グーが反応しないとの不合格申告を受けた。
- 実ログにはthumb/two/three認識とmenu is closed拒否が存在。サーバのmenu_closeはokのみを返し、認識アプリがmenu_openを保持していた。以降menu_next/confirmを閉じたメニューへ送る不整合を確認した。
- op_controller.pyで成功したmenu_closeのペイロード省略に対応し、menu is closed拒否でも閉状態へ同期（自動再実行なし）。拒否されたcloseでは開状態を勝手に成功へ変えない。選択番号と最後のコマンドを保持し、app.pyで離散手形と選択中の1項目を表示。
- 3回帰試験を追加した自己検証：認識側69件合格。実Slicerへの自作手形入力でthumb→two→fist→thumb→threeを実行し、open→next(index1)→close→reopen→confirm(view)を全受理。記録work/live-menu-sync-result.json、試験コードwork/live_menu_sync_check.py。stamp/commitは送っていない。これは実手試験ではない。
- Pixel 8aで修正版アプリを再起動、Slicerを前面へ戻し、本人へ同じ順序の実手メニュー確認を依頼中。離散形は0.35秒保持で1回発火し、同形の連続選択は一度解除する必要がある。viewかつメニュー閉・DRAFTなしでは2/3/fistにC編集動作を割り当てていない。
- Slicer側ソースもDRAFTのbool.revision例外、next/prevの表示更新、closeのメニュー返却を修正。ただし起動中Slicerへこのファイル変更は未反映であり、DRAFT操作の解除／合格とはしない。既知の確定・監査・保存不合格は維持する。
- 本人の再試験は「まだ動かない」。実手ログではmenu_open/next(index1)/closeを観測したが、メニューの見やすさと切替成立は不合格。続く「handshapeは認識しているが画面操作ができない」を受け、分類閾値は変更していない。
- slicer_hud.pyを追加し、Slicer前面時のみ日本語の受付・モード・手形・選択項目を常時表示。読み取り専用、WS_EX_NOACTIVATE／TOPMOSTで前面を奪わない。実Windows観測でHUD visible=true、noactivate=true、topmost=true、前面PID30896を確認。本人も「パネルは見える」「パネルがあると解りやすくていい」と確認。ただし「C照準に切り替わらない」は未解消。HUDのみのPrintWindow取得は黒画面であり、その画像を表示検証成功とは扱わない。映像・シーンは取得していない。
- 実手の切替中にthumbが再検出されmenu_closeを受理、その後two/threeがメニュー閉状態で無操作となる経路を観測。親指をメニュー開始専用に変更し、開状態の親指では閉じない。閉じる操作は拳に統一。docs/23第75〜81行の試作割当て・反復抑止の範囲としてREADMEと本試験計画の操作表を更新。回帰試験追加で認識側70件合格（自己検証）。離散コマンド単位の受理／拒否ログも追加した。
- 最終修正版をPixel 8aで再起動。再接続に伴う受付停止を維持している。次の実手開始→親指→two→threeで照準モード切替、および拳による閉操作の本人確認は未完了。パネル表示の本人評価を離散操作の合格へ拡張しない。
- 開く専用への変更後、実手のmenu_open／menu_nextを受理し、メニューを維持。その後menu_confirmもok=trueを実観測（その時点の選択index3＝reset_view）。3本指の選択発行は確認したが、C照準への意図一致はまだ未確認。
- 15:04 JST、本人の「2メニューを開く ができない」に対して現在の実表示を確認。Slicerを前面にして自作テキストHUDだけをPrintWindow取得したところ、受付中／視点、メニュー2/12、選択C配置：照準モードと読めた。work/menu-panel-check.png。カメラ／シーンの画素は取得していない。同時刻の継続ログでもmenu=True,index=1。手順②③は現在状態上成立しており、開状態の親指が無操作なのは二重閉鎖を防ぐ仕様。本人へ現在地と次の④3本指選択を説明。画面モード変更の成立はまだ確認待ち。
- 続く本人添付画面は受付中／C照準・認識3本指・メニュー閉。実ログもmenu_confirm ok=true, mode=aim、draft=false。照準モードへの切替は実画面と応答で成立。仮Cなしの3本指は確定対象なしで無操作であり、切替とモデル編集を区別する。
- slicer_hud.pyのC照準表示を具体化し、照準の有効／表面外／未取得、仮Cの有無、人差し指で照準、2本指で仮配置、仮Cなしの3本指／拳は対象なしを表示。op_controller.pyはaim応答のvalidを表示用に保持、切断時に消去。自己検証71件合格。Pixel 8aアプリへ再起動で反映。既知C確定・保存等の不合格を解除しておらず、新たなC配置・確定試験は未実施。本人添付のカメラ部分は複製・外部送信していない。
- 本人の「どのジェスチャーにも反応しない」を受けて再確認。実ログ／自作HUDのみの実表示で、受付中／C照準・menu=True,index=0（視点操作選択）を確認。メニュー表示中は連続モデル操作を止める原計画第75行の動作が有効になっていた。Slicerを前面へ戻し、3本指で現在選択の視点操作を決定する1動作の実手確認を依頼。今回再起動・コマンド注入なし。復旧成立は本人確認と応答待ち。
- 次の本人添付では受付中／視点・番号と▶なしを確認し、ログも実手menu_confirm ok=true,mode=view,menu=False。メニュー閉と視点復帰は成立。ただし本人はメニュー状態を判別できないと報告。docs/28へ合成の閉／開比較画面と見分け方を追加した。今回の最新画像を開状態とは扱わない。本人添付画像の外部送信、アプリ再起動、追加の自作コマンド注入はしていない。基本操作全条件とC編集の未解消所見は維持。
- 解放1フレームで同じ形のラッチが再受付される問題を、短いNONEを挟んだ保持の回帰試験で固定。gesture_fsm.pyを変更し、同形の再受付にはgesture_hold_sと同じ時間（既定0.35秒）の解放を必要とする。別の離散形への安定切替は可能。原計画第80行の反復抑止に結び付け、旧単体3件の瞬間解放入力を十分な解放へ訂正。自己検証71件合格。Pixel 8aでこの版へ再起動済み。最終版の実手再検収は未完了。

## 実行した範囲と証拠

ユーザーの「テストプランを実行し、テスト結果MDを作成」の指示を根拠に、現行版を固定してG-00の準備確認、X試験の実行可能部分、実カメラ認識を実施した。正本はdocs/03・05・23・26、実装状態の参照はdocs/21。臨床試験ではない。

| 層 | 今回の結果 | 解釈 |
|---|---|---|
| 既存単体試験の再実行 | Slicer側131件、認識側66件合格（合計197件） | 合成入力／自作期待値による自己検証。実手・全要求合格ではない |
| 実Slicer GUI内・合成入力 | 最終プローブ35項目：PASS 29、FAIL 6。その後DRAFTメニュー生成で製品例外 | 自作試験を実Slicerのロジック／MRML／カメラで観測。実手や通常マウス入力ではない。個別述語合格をAC全条件合格へ拡張しない |
| 実TCP結合 | loopbackの別ポート18945で6応答。hello→status→無効時回転拒否→arm→status→disarmが成立 | 実QTcpServer＋socket。視点変更・確定・実手のTCP通し試験はここには含まない |
| 実カメラ認識 | 番号0、1280×720。約30秒、806フレームすべて手0件・NONE | 映像は受信。PIXEL映像の同一性、操作者の意図、ジェスチャー成功率は未確認 |
| 署名／SBOM | run.ps1・setup.ps1は未信頼ルートで検証非正常。SBOM50ファイル中5ファイルが現物不一致 | IT-002未達。信頼設定を変更していない |
| 権限／通信 | 試験用SlicerのTokenElevation=false。静的通信監査exit 0 | 当該Slicerの非昇格は実観測。全プロセス権限、継続的外向き通信、更新復帰の全試験は未実施 |
| 実手H-01〜12 | 全ケース未合格・未実施／阻害 | 安全不合格とカメラ同一性未確認により、C操作の実手試験を続行しない |

対象のSHA-256、試験計画と原要求の版、保存先は[manifest.json](../evidence/FIELD-20261010-01/manifest.json)。生成した試験コードも証拠フォルダーに保存した。モデルはその場で生成した半径30mmの球（RASの非患者合成形状）。既存のCARTOデモ・患者画像は読み込まない。

既存のSlicerセッションPID30896にはコマンドを送信せず、別Slicerプロセスと試験専用台帳を使用した。[保存前後比較](../evidence/FIELD-20261010-01/preservation-check.json)で製品コードと既存events/plans/resultファイルの変更0を確認した。台帳削除、証明書信頼追加、権限変更は行っていない。

## 再現した不合格と対応

| ID | 原要求／計画 | 入力・期待 | 実観測 | 判定・次の対応 |
|---|---|---|---|---|
| F-01 | docs/23表示版確定契約、X-01、H-12 | 保存済み要求を切断→hello→arm後に結果照会。永続結果を読み取り専用で取得 | `unknown request id`。台帳には保存済みだが要求結果は再接続で消える | FAIL。実装担当が要求IDと保存イベントの永続索引・復旧照会を実装しX-01再試験 |
| F-02 | FR-030、X-05 | 保存イベントのアンカーだけ+100mm、integrityは元値。読込拒否を期待 | 改変コピーから1件復元、例外なし | FAIL。読込時ハッシュ・モデル／座標整合を検証し、不一致を無作用で拒否 |
| F-03 | docs/26 H-09、docs/23独立監査確認 | 対象・理由選択→取消準備→独立確認前は監査増分0 | `revoke_event`だけで`event_revoked`を追記。confirm_audit前の台帳が1→2行 | FAIL（合成入力）。準備と確定を別遷移にし、表示対象・理由と独立確認を束縛 |
| F-04 | 元イベント不変、FR-015/030、X-05 | 元イベント全フィールド不変を比較 | `_committed[event_id]['revoked']`がfalse→trueに変化。永続元行は不変 | 自己検証FAIL。永続上書きとは報告しない。元イベントと取消の派生状態を分離し、ハッシュ検証対象の不変範囲を明確化して再試験 |
| F-05 | FR-033/034、X-05、H-05 | 計画作成・新版保存後、同じ登録保存先を新ロジックへ設定し復元 | 計画台帳2行に対して新PlanStoreの登録IDは空。復元経路を確認できない | FAIL（プローブの復元条件）。実装担当が計画登録台帳の明示読込と全項目再現を用意し、終了再起動の試験で検収 |
| F-06 | FR-040、AC-023、H-07 | 理由visibilityを選びスキップ。選択理由が保存されること | 台帳のreasonはoperator | FAIL（現行メニュー相当の合成呼出し）。選択理由をスキップ確定へ束縛。理由取り違えと残留を再試験 |
| F-07 | 主操作メニュー、H-02/10/11、B-07 | DRAFTありでメニュー項目を取得 | `AttributeError: 'bool' object has no attribute 'revision'`。`has_draft()`のboolから`draft.revision`を参照 | 製品例外、FAIL。DRAFT実体と有無判定を修正し、実画面のメニュー表示→選択→確定／取消／再開を再試験 |
| F-08 | AC-014、H-02a | 仮配置取消後IDLEを期待 | 取消プローブのstateはCANCELLED。仮配置は消え、台帳は不変 | AC-014のIDLE条件未達。別の終了遷移が必要なら手経路を含めて明示し検証。AC-004の部分合格をAC-014合格へ拡張しない |
| F-09 | IT-002、X-07 | 現物とSBOMの全ハッシュ一致、正常な署名検証 | CStampModule.py、slicer-cstamp/README.md、e2e_session_verify.py、run.ps1、setup.ps1の5件不一致。両PS署名は未信頼ルート | FAIL。配布担当が最終現物の署名・検証・SBOM生成順序を整え再照合。本試験では設定変更や再署名をしない |

F-01〜06の生応答・件数は[最終実Slicerプローブ](../evidence/FIELD-20261010-01/slicer-attempt3/slicer-probe.json)、F-07は同ファイルのfatal_error、F-08はAC-004-cancelのobserved.state。F-09は[署名結果](../evidence/FIELD-20261010-01/signatures.json)と[SBOM照合](../evidence/FIELD-20261010-01/sbom-check.json)。修正担当は未記名の実装／配布担当役割であり、本人への作業依頼や修正完了を意味しない。

DRAFTメニューの例外と破損台帳受理を確認したため、実操作者による確定・訂正へ進めなかった。故障診断はそれぞれ別の試験用ロジック・台帳で行い、実手ケースの合格として扱っていない。製品修正は本作業に含めていない。

## 操作・保存で成立した部分

実Slicerで黄照準の表面交点、33点DRAFT、同一DRAFTへの再スタンプ拒否、曲面上位置移動、表面外での位置維持、開口回転・傾斜・反転・方向リセット、DRAFT中ズームでC不変を観測した。これらは合成コマンドの成立であり、反転／リセットの手メニュー到達は未実装のまま。

古い時刻・別セッション・不正コマンド・DRAFT中レイヤー変更・不正回転量を拒否した。古いrevisionでの確定も拒否した。専用書込失敗点では未確定DRAFTを保持し、復旧後の確定で1件保存。同一DRAFT再確定は拒否。同一セッションの結果照会は再保存しなかった。

3件の独立ID・順序付きイベント、点からC表示、同じ台帳から3件復元、2回目読込増分0を観測した。ただしモデルハッシュ等の全保存項目・描画完了版・全訂正履歴・終了再起動まで検証していない。AC-003/008/015〜018の全面合格ではない。計画新版のdiff応答は得られたが、永続復元は不合格。

[合成3Dビューのレンダリング](../evidence/FIELD-20261010-01/slicer-attempt3/synthetic-render.png)も採取・目視自己確認した。これは非患者合成画面であり、PIXEL映像・操作者の写真・フル操作パネルのスクリーンショットではない。

## 実カメラ・実手の記録

本人申告：PIXELを接続済み。実機観測：カメラ番号0で1280×720のフレーム受信、番号1/2は開けない。[カメラプローブ](../evidence/FIELD-20261010-01/camera-probe.json)。Windowsの候補に`Windows Virtual Camera Device`、`Android Composite ADB Interface`、BluetoothのPixel 9aを確認したが、映像源とPIXELの同一性は証明できていない。

手形を順に提示する30秒の案内を出して、制御接続なしの認識器で806フレームを処理した。結果は手0件806フレーム・NONE806フレーム。[認識集計](../evidence/FIELD-20261010-01/live-recognition.json)。カメラ画像・ランドマーク座標は保存していない。

操作者が実際に提示した時刻・手形の同期記録がなく、USBウェブカメラ設定の確認も結果作成時点では未回答。手認識不能の原因、PIXEL故障、認識成功率0%を断定しない。受信フレームは映像保存なしでメモリ上だけ処理した。

## H/Xの全体実施状態

| ケース | 状態 | 実施範囲／残り |
|---|---|---|
| G-00 | BLOCKED | 専用モデル・台帳・版は準備。PIXEL同一性、手によるメニュー表示、安全条件が未達 |
| H-01 | NOT RUN | 手による開始・停止と実画面操作は未実施。カメラ認識だけ実施 |
| H-02a/b | BLOCKED | 手メニュー例外F-07、表示完了ACK B-01。合成ロジック部分のみ |
| H-03 | BLOCKED | 明示保存・表示選択の手経路、精度全項目未検証。合成3件復元のみ |
| H-04 | BLOCKED | 実手なし。作成者区分選択・計画所属の実手経路未検証 |
| H-05 | BLOCKED | 個別計画編集の手メニューなし、計画永続復元F-05 |
| H-06 | BLOCKED | 実手なし、表示版同期未達 |
| H-07 | BLOCKED | 順序変更の手経路なし、理由不一致F-06 |
| H-08 | NOT RUN | 実手による計画外記録・レビュー未実施 |
| H-09 | BLOCKED | 独立確認の合成診断でF-03/04、実手は中止 |
| H-10 | BLOCKED | 切断時凍結は合成で観測。遮蔽・複数手・復帰の実手試験は未実施 |
| H-11 | BLOCKED | DRAFTメニュー例外。保持から画面遷移する実手試験未実施 |
| H-12 | BLOCKED | 再接続照会F-01、照会の手メニューなし。書込失敗は合成で観測 |
| X-01 | FAIL／部分実施 | 古いrevision・保存失敗・同一セッション照会成立、再接続照会不合格。描画遅延・保存途中終了等は未実施 |
| X-02 | BLOCKED | 通常マウス全操作UI・共通引継ぎ未検証。実マウス試験なし |
| X-03 | 部分実施 | 不正コマンド等の拒否を観測。設定変更・全モデル変換・無操作タイムアウトの実機注入は未実施 |
| X-04 | 部分実施 | 実Slicerパラメーター操作成立。連続ズーム速度・加減速全仕様、実手比較未実施 |
| X-05 | FAIL／部分実施 | 改変受理、元イベントのメモリ状態変更、計画復元不成立。正常3件復元は成立 |
| X-06 | 測定のみ／未完了 | 30秒の認識処理件数のみ。各手形10試行、環境別5試行、30分無操作監視、端から端遅延、疲労・操作性は未実施 |
| X-07 | FAIL | 署名非正常、SBOM5件不一致 |
| X-08 | 部分実施 | 静的監査、実TCP、当該プロセス非昇格を観測。連続通信監視・生成物全監査・更新復帰は未実施 |

## AC24件の結果索引

| AC | 判定（全条件） | 今回の観測／不足 |
|---|---|---|
| AC-001 | 部分確認 | 合成照準からDRAFT1件33点・保存0。実手未実施 |
| AC-002 | 部分確認 | 合成開口回転でアンカー不変・保存0。全方向／実手未実施 |
| AC-003 | BLOCKED | 内部revision確定1件。表示完了版一致は未証明 |
| AC-004 | 部分確認 | 合成取消でDRAFTなし・既存台帳不変。実手未実施 |
| AC-005 | 部分確認 | 同一DRAFT再確定拒否。全再送・手保持経路未実施 |
| AC-006 | BLOCKED | 切断凍結のみ。実遮蔽・曖昧・複数手未実施 |
| AC-007 | BLOCKED | 実手対通常マウス同列未実施 |
| AC-008 | 部分確認 | 同じ合成台帳3件復元。全精度・同じシーン終了再起動未実施 |
| AC-009 | 部分確認 | 中央の有効交点を合成で確認。実手の表面外→内未実施 |
| AC-010 | 部分確認 | 再スタンプ拒否。実手保持未実施 |
| AC-011 | 部分確認 | 合成開口変更時アンカー不変。単調連続列と全許容誤差未完了 |
| AC-012 | NOT RUN | 実手の拡大→解放→縮小とドリフト未測定 |
| AC-013 | 部分確認 | 合成ズームでDRAFT同一。実手未実施 |
| AC-014 | FAIL（観測部分） | 取消後CANCELLED。要求のIDLE未到達 |
| AC-015 | 部分確認 | 点と保存C全形状は存在。全保存フィールド照合未完了 |
| AC-016 | 部分確認 | C再表示が可視化。全数値比較・実手選択未実施 |
| AC-017 | 部分確認 | 合成3独立ID・orderを保存。各点の手選択未実施 |
| AC-018 | BLOCKED | 訂正・取消監査・計画を含む終了再読込未実施。関連保存に所見あり |
| AC-019 | NOT RUN | 予定／実績の同一画面での実手識別未実施 |
| AC-020 | NOT RUN | 実手追従ゴースト未実施 |
| AC-021 | NOT RUN | 全3差分の実手更新未実施 |
| AC-022 | BLOCKED | 表示版同期未達・実手なし |
| AC-023 | FAIL（合成部分） | 選択visibilityが保存operatorに置換 |
| AC-024 | NOT RUN | 実手計画外記録未実施 |

## 実行上の修正と証拠保持

認識側pytestをリポジトリ直下から実行した最初の試行は`ModuleNotFoundError: config`で収集エラー。プロトタイプの作業ディレクトリで再実行し66件合格。最初の失敗ログ/XMLも保持した。

Slicer初回プローブは前面ゲートfalseのためG-00だけで終了し、ゲートを迂回しなかった。第2試行は独自の試験ウィンドウを前面にして実施したが、移動先を表面外にしていた検査入力とPERFORMED台帳を計画読込に渡した検査入力の誤りがあった。第3試行で有効交点を選び、PLANNEDの専用合成fixtureへ直した。これらは製品不合格と混同せず、試行1〜3を残した。第3試行末尾のDRAFTメニュー例外は製品側の例外である。

全試験用Slicerはスクリプト末尾で終了。カメラprobeも解放済み。既存Slicerは維持。独立レビューは今回実施していない。設定保存、合成自己検証、実Slicer観測、実手操作成立、継続運用効果を区別し、運用是正済みとは報告しない。

## 次の一手

実装担当がF-01/02/07を優先修正し、表示版同期・元イベント不変・監査確認・理由・計画復元を是正する。専用版でX再試験を行い、中止条件の所見が解消してからPIXEL映像源を確認してG-00→H-01→H-11→H-10へ進む。手を動かせることだけで安全阻害を解除しない。正式署名／SBOM整合は配布担当が別に再検収する。

## 最終実Slicerプローブの生結果索引

自作プローブの限定述語であり、PASSを原要求全条件のPASSと読まない。

| プローブ | 述語結果 | 実観測 |
|---|---|---|
| G-00-synthetic-scene | PASS | {"cells": 7936, "scene": "synthetic sphere", "ledger": "C:\\Projects\\Cardiac-CT-Motion-Control\\evidence\\FIELD-20261010-01\\slicer-attempt3\\events.jsonl", "startup_armed": false} |
| X-03-arm | PASS | {"ok": true, "req": "probe-2", "state": {"armed": true, "mode": "view", "layer": "PERFORMED", "draft": false}, "result": {"text": "状態: IDLE\n手入力: 受付中 / モード: view / レイヤー: PERFORMED", "state": "IDLE", "frozen": false, "aim_valid": false, "layer": "PERFORMED", "plan": null}} |
| X-04-real-camera-rotate | PASS | {"reply": {"ok": true, "req": "probe-3", "state": {"armed": true, "mode": "view", "layer": "PERFORMED", "draft": false}}, "before": [0.6641105538949006, 767.3935230231609, 0.09640809879737589], "after": [134.71092167110282, 752.7172428667506, 67.63282864823053]} |
| AC-009-synthetic-aim | PASS | {"ok": true, "req": "probe-5", "state": {"armed": true, "mode": "aim", "layer": "PERFORMED", "draft": false}, "result": {"valid": true, "point": [7.085264793687461, 28.916175301096814, 3.33155983077123]}} |
| AC-001-synthetic-stamp | PASS | {"reply": {"ok": true, "req": "probe-6", "state": {"armed": true, "mode": "aim", "layer": "PERFORMED", "draft": true}, "draft_id": "draft-0001"}, "points": 33, "rows": 0} |
| AC-010-repeat-stamp | PASS | {"ok": false, "req": "probe-7", "state": {"armed": true, "mode": "aim", "layer": "PERFORMED", "draft": true}, "reason": "draft already exists"} |
| X-03-bogus | PASS | {"ok": false, "reason": "unknown command", "state": {"armed": true, "mode": "aim", "layer": "PERFORMED", "draft": true}} |
| X-03-select_layer | PASS | {"ok": false, "req": "probe-9", "state": {"armed": true, "mode": "aim", "layer": "PERFORMED", "draft": true}, "reason": "layer change forbidden during draft"} |
| X-03-view_rotate | PASS | {"ok": false, "req": "probe-10", "state": {"armed": true, "mode": "aim", "layer": "PERFORMED", "draft": true}, "reason": "invalid view command"} |
| X-03-stale-time | PASS | {"ok": false, "reason": "stale command", "state": {"armed": true, "mode": "aim", "layer": "PERFORMED", "draft": true}} |
| X-03-other-session | PASS | {"ok": false, "reason": "wrong session", "state": {"armed": true, "mode": "aim", "layer": "PERFORMED", "draft": true}} |
| X-04-move | PASS | {"before": [7.085264793687461, 28.916175301096814, 3.33155983077123], "after": [5.0425943921646095, 29.348302315852578, 3.3377589311552036], "reply": {"ok": true, "req": "probe-14", "state": {"armed": true, "mode": "move", "layer": "PERFORMED", "draft": true}, "result": {"rev": 1}, "draft_id": "draft-0001"}} |
| X-04-off-surface | PASS | {"ok": false, "req": "probe-15", "state": {"armed": true, "mode": "move", "layer": "PERFORMED", "draft": true}, "reason": "off-surface; draft unchanged"} |
| AC-002-opening | PASS | {"ok": true, "req": "probe-17", "state": {"armed": true, "mode": "rotate", "layer": "PERFORMED", "draft": true}, "result": {"rev": 2}} |
| X-01-stale-revision | PASS | {"ok": false, "req": "probe-18", "state": {"armed": true, "mode": "rotate", "layer": "PERFORMED", "draft": true}, "reason": "draft changed since display (shown rev 1, current rev 2)"} |
| X-04-tilt | PASS | {"ok": true, "req": "probe-20", "state": {"armed": true, "mode": "tilt", "layer": "PERFORMED", "draft": true}, "result": {"rev": 3}} |
| X-04-reverse-API | PASS | {"ok": true, "req": "probe-21", "state": {"armed": true, "mode": "tilt", "layer": "PERFORMED", "draft": true}, "result": {"rev": 4}} |
| X-04-reset-API | PASS | {"ok": true, "req": "probe-22", "state": {"armed": true, "mode": "tilt", "layer": "PERFORMED", "draft": true}, "result": {"rev": 5}} |
| AC-013-camera-only | PASS | {"ok": true, "req": "probe-24", "state": {"armed": true, "mode": "view", "layer": "PERFORMED", "draft": true}} |
| OP-011-write-failure | PASS | {"ok": false, "req": "probe-25", "state": {"armed": true, "mode": "view", "layer": "PERFORMED", "draft": true}, "reason": "rejected: [WinError 183] 既に存在するファイルを作成することはできません。: 'C:\\\\Projects\\\\Cardiac-CT-Motion-Control\\\\evidence\\\\FIELD-20261010-01\\\\slicer-attempt3\\\\not-a-directory'"} |
| AC-003-internal-revision-only | PASS | {"reply": {"ok": true, "req": "probe-26", "state": {"armed": true, "mode": "view", "layer": "PERFORMED", "draft": false}, "result": {"draft_revision": 5}, "event_id": "c35ce5b7583445cf95bba53c96d48dbe"}, "display_completion_proved": false} |
| AC-005-repeat-commit | PASS | {"ok": false, "req": "probe-27", "state": {"armed": true, "mode": "view", "layer": "PERFORMED", "draft": false}, "reason": "no active draft"} |
| X-01-query-same-session | PASS | {"ok": true, "req": "probe-28", "state": {"armed": true, "mode": "view", "layer": "PERFORMED", "draft": false}, "result": {"response": {"ok": true, "req": "probe-26", "state": {"armed": true, "mode": "view", "layer": "PERFORMED", "draft": false}, "result": {"draft_revision": 5}, "event_id": "c35ce5b7583445cf95bba53c96d48dbe"}}} |
| AC-017-three-records | PASS | {"count": 3, "orders": [0, 1, 2]} |
| AC-016-redisplay | PASS | {"ok": true, "event_id": "c35ce5b7583445cf95bba53c96d48dbe"} |
| AC-004-cancel | PASS | {"reply": {"ok": true, "req": "probe-44", "state": {"armed": true, "mode": "aim", "layer": "PERFORMED", "draft": false}}, "state": "IDLE"} |
| SR-008-disconnect-freeze | PASS | {"ok": false, "reason": "no session; send hello first", "state": {}} |
| X-01-query-after-reconnect | FAIL | {"ok": false, "req": "probe-2", "state": {"armed": true, "mode": "aim", "layer": "PERFORMED", "draft": true}, "reason": "unknown request id"} |
| AC-008-reload-synthetic | PASS | {"restored": 3, "ids": ["c35ce5b7583445cf95bba53c96d48dbe", "69e64d6b151b49c09781aad0d21abbc2", "8c43dfe5d45042609ee80de341ccbdfb"]} |
| X-05-corrupt-ledger-rejection | FAIL | {"restored": 1, "rejected": false} |
| X-05-original-in-memory-immutable | FAIL | {"before_revoked": false, "after_revoked": true, "reply": {"ok": true, "result": {"revoked": "a54a078b676d4d778a1e71b2cbc1fb36"}}} |
| H-09-synthetic-confirmation-order | FAIL | {"rows_before_confirm_audit": 2, "types": [null, "event_revoked"]} |
| X-05-plan-version-diff | PASS | {"ok": true, "result": {"plan_id": "field-plan", "version": 2, "diff": {"added": [], "removed": [], "changed": ["a54a078b676d4d778a1e71b2cbc1fb36"], "order_changed": false}}} |
| X-05-plan-registry-reload | FAIL | {"fresh_plan_ids": [], "persisted_rows": 2} |
| H-07-synthetic-selected-reason | FAIL | {"record_type": "plan_skip", "planned_event_id": "c35ce5b7583445cf95bba53c96d48dbe", "reason": "operator", "event_id": "1131f7954ad24af59eba6500e473baa5", "order": 0, "committed_at": "2026-10-10T02:10:04.037879+00:00", "integrity": "320f06938b87f6a16eabed54284c48fd6892f44d765139d180d478475db44059"} |
# 2026-10-10 1本指から2本指への切替が反応しないという本人報告

本人報告「１本から２本が反応しない」を、人差し指の照準から2本指で仮配置する経路として調査。稼働ログ `work/recognition-pixel8a-20261010-193836.stdout.log` にPOINTとTWOの認識、`stamp ok=True` を確認した。共有メモリの読取時点はfresh=true、armed=true、draft=true、mode=aim、opened=false。現在は仮Cが既に存在し、op_controller.pyはaimかつdraft=falseの場合だけTWOからstampを送るため、再提示しても追加配置しない。

これは認識・サーバー受付・現在状態の観測。本人が見ている仮Cの位置や表示の視認性、今回の報告に対応する切替の全フレーム、実手での方向調整成立は未確認。「操作成功」と一括判定しない。仮Cを勝手に取消・確定・再配置せず、親指でC編集を開き「開口方向を調整」へ進む手順を案内する。仮配置済みの状態で2本指が無作用になる理由が画面案内に不足している点を残す。

# 2026-10-10 合成手形画像による実モデルの自己検証

本人指示で6種類の手形を生成し、現行MediaPipeモデルへ実入力した。[詳細結果](32_illustrated-gesture-test-results.md)。原画像／左右反転12条件中9条件が全フレーム一致。親指にUNKNOWN計7フレーム、原画像のグーにPINCH1フレームが混じるため一部不合格。画像からの推定結果で現行操作コントローラーを通し、模擬接続へstamp1回、select_mode:rotateを記録。左右へ動かした画像からrotate_opening26回・tilt0回。画像由来の合計角度をローカルC形状処理へ適用し、中心・面不変、開口角変化を確認した。

合成画像・記録用模擬接続・ローカル形状の自己検証。実カメラや実Slicer描画の検収ではない。本人が観測する縦回転やグー誤認識の解消済みとはしない。稼働仮C・台帳を変更しない。

# 2026-10-10 実Slicer追試：画像由来の開口方向回転を実行

本人指示で実Slicerの既存仮Cへ、合成画像から実モデルが推定したShape・ランドマークを現行OperationControllerに再生し、実CommandDispatcher.dispatch_localから操作した。開口角約39.98度変化、中心・面不変、実MRML33点更新、水色曲線の実描画を確認。自己検証であり実Pixelの本人手形の検収ではない。

受付40回・凍結拒否2回。同期再生中の接続タイムアウト／再接続・凍結・ValueErrorと、Cがモデルに一部隠れる視認性不良を観測し全体不合格。元の角度・カメラを復元し受付停止。仮C版は368へ進んだ。確定・取消・台帳／シーン保存なし。詳細と実物証跡は[追試結果](32_illustrated-gesture-test-results.md)。

# 2026-10-10 修正実装・実TCP再検証

[修正報告書](34_hand-control-correction-report.md)。接続の二重除去、開始時の意図しない連続入力、モード表示、C方向プレビュー、指関節方向による認識を修正。自己検証111＋146件合格。同じ合成画像は12/12条件一致。実TCPの段階再生ではrotate選択・回転・復元が成立し予期しない拒否0。実接続置換10/10成功。実ドックの方向プレビューと直径10mm、元の中心・面・方向の復元を確認した。

実手と規定の長時間・全条件の試験は未完了。既知F-01〜09は維持。3Dの遮蔽は方向プレビューで確認を補助し、実位置を変更して見えるようにしたものではない。確定・取消・台帳／シーン保存は実行しない。

