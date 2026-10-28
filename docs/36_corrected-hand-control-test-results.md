# 修正版ハンド操作テスト結果

<!-- SOL-CURRENT-BEGIN -->
## 2026-10-11 不足分実装後の追加テスト結果（現在判定）

**計画全項目の検収は未完了。** 最新実装と対象版は[docs/39](39_completion-implementation-report.md)、実施計画は[docs/38](38_completion-implementation-plan.md)。下の旧257件・旧600秒結果はその時点の証拠として保持し、最新合格に読み替えない。

自己検証305件PASS（認識129／Slicer171／tools5）。実Slicer・合成球・試験台帳の観測も実装者による自己検証。実手合格・独立レビューとは区別する。

| 追加観測 | 結果 | 証跡 |
|---|---|---|
| 不足10メニュー・予定項目編集確定 | PASS | [結果JSON](../work/sol-history-menu-20261011/menu-results.json) |
| 終了再起動・手メニューで保存第1〜4版を比較 | PASS | [結果JSON](../work/sol-history-menu-20261011/plan-version-results.json) |
| 通常／拒否・計画・監査・構成変更 | PASS | [結果JSON](../work/sol-final-combined-20261011/tcp-results.json) |
| 継続保持／保持中版変更／独立確定 | PASS | [結果JSON](../work/sol-final-combined-20261011/hold-binding-results.json) |
| 描画ACK保留・保存失敗・保存後応答喪失 | PASS | [結果JSON](../work/sol-final-combined-20261011/fault-results.json) |
| 形状・世界変換・シーンからの対象喪失 | PASS | [結果JSON](../work/sol-final-combined-20261011/target-change-results.json) |
| 改変・部分行・重複・不正integrityの実Slicer読込拒否 | PASS | [結果JSON](../work/sol-final-combined-20261011/integrity-results.json) |
| 実Slicer終了再起動・元要求照会 | PASS | [結果JSON](../work/sol-final-combined-20261011/restart-results.json) |
| NTFS保存子プロセスの置換前後終了 | PASS | [結果JSON](../work/sol-storage-crash-20261011/results.json) |
| 実Slicer保存置換前で終了→再起動、旧1件・未保存req | PASS | [結果JSON](../work/sol-actual-slicer-crash-before-20261011/slicer-crash-results.json) |
| 実Slicer保存置換後で終了→再起動、新2件・保存req復元 | PASS | [結果JSON](../work/sol-actual-slicer-crash-after-20261011/slicer-crash-results.json) |
| カメラなし・実マウスUI配置／方向／保存／取消 | PASS | [結果JSON](../work/sol-final-native-mouse-layout-20261011/mouse-results.json) |
| 位置・方向を追加した独立確認の実Qt表示／No無保存 | PASS | [結果JSON](../work/sol-final-confirmation-ui-20261011/confirmation-results.json) |
| C開口回転と独立方向リセット600秒 | PASS | [結果JSON](../work/sol-final-rotation-20261011/rotation-results.json) |
| 最終版通常カメラ／接続600秒 | PASS | [結果JSON](../work/sol-source-frozen-normal-600-20261011/results.json) |
| 600秒後の通常仮C／版／寸法／カメラ／台帳の不変 | PASS | [結果JSON](../work/sol-final-normal-preservation-20261011.json) |
| 配布候補の現物・依存・構成照合 | PASS | [結果JSON](../work/sol-final-release-inventory-20261011.json) |

C方向は609.766秒・37周期・2006要求で成立。開口の中心／法線／寸法と独立リセット後の幾何を照合。取得段階は画像由来ランドマーク再生で、実Pixelの動く手ではない。通常接続は600.0779999999795秒、受付停止維持=True。先行600秒の鮮度17サンプルFAILと、それ以前の停止継続FAILを保持する。

カメラなしのマウス代替は12判定PASS。物理ボタン・表面クリック・ホイール・キーボード確認とUI Automation slider値設定を区別。表面の連続ドラッグ、手無効／遮蔽／カメラ断／通信断の全4条件と全ハンド同一操作列比較は未完了。確認文に中心・開口角／ベクトル・法線・進行方向を追加し、最終版実Qtで表示とNo無保存を検査した。

実Slicer保存置換前終了は旧1件・未保存req、置換後終了は新2件・保存reqを別PID再起動後に確認。原子保存子プロセス試験とは別の追加証拠である。実Qtの遅延／順序逆転など指定全障害、実手H12/V10・480明確形／不明形、本人の意図・疲労・使用感、正規署名後の更新／復帰、独立検収は残す。

通常保護対象一致=True、600秒後の実Slicer照合でも一致=True。仮C draft-0005／版651／10mm、配置・カメラ・台帳を維持して反映。通常用は1個、追加試験fixtureは1個ずつ終了。カメラ画像・患者データは試験保存しない。

以下は先行試験時点の記録。下の旧判定や未実施欄を現在判定と取り違えず、上の対象版別結果・残条件を参照する。
<!-- SOL-CURRENT-END -->

実施日：2026-10-11。対象：[修正報告書](34_hand-control-correction-report.md)の稼働版。依頼：本人の「テスト計画MDを作って、テストして」。計画：[docs/35](35_corrected-hand-control-test-plan.md)。原要求：[docs/03](03_system-requirements.md)、修正合格条件：[docs/33](33_hand-control-correction-plan.md)第6節。

## 判定

2026-10-11追加：[全項目の実装照合](37_implementation-plan-audit.md)で機能／安全／保存経路の未実装・未接続も確認。**実装未完了・検収未完了**を分けて扱う。以下の試験結果だけから「残りはテストのみ」と判断しない。

**総合不合格／未検収あり。** 自己検証、合成画像の実モデル推論、通常接続の10分観測、実TCP操作と実Slicer幾何の照合、接続置換を実施した。停止継続は不合格。実TCPの10分反復は前面ゲートによる拒否で未達。実手の意図・距離・照明・左右条件、隔離Slicerでの確定保存通しは未検収。既知F-01〜09は今回の通過件数を理由に閉じない。

## 実施条件と証跡

実際に起動中のSlicer 5.12.3とPixel 8aのCameraIndex 1を確認。認識入力1280×720、観測時約25fps。既存仮C draft-0005、試験前revision 449、現在／次のC直径10mm。台帳内容やカメラ画像は出力せず、台帳はハッシュだけを照合する。

対象ソース7ファイルのSHA256：[tested-source-sha256.json](../work/20261011-tested-source-sha256.json)。幾何とカメラの試験前メタデータ：[slicer-before.json](../work/20261011-slicer-before.json)。合成画像とモデルのSHA256は認識生結果に記載。途中でSlicer・シーンを再起動／再読込していない。

## 実施結果

| ID | 結果 | 実施層・観測 |
|---|---|---|
| T-00 | PASS | 実ウィンドウ、共有状態、Pixel入力メタデータとソース版を確認 |
| T-01 | PASS（自己検証） | 認識・制御111件通過。追加でview/rotate/tilt各10回、開始保持中の移動命令0。模擬接続・合成点であり実手30回ではない |
| T-02 | PASS（自己検証）、実Slicer全条件未検収 | Slicerコア・プロトコル等146件通過。既知F-01〜09の実ツール再検収を代替しない |
| T-03 | PASS（合成画像・実モデル） | 6手形×原画像／左右反転12条件、各30フレームすべて一致。静止画反復360フレームは360人／360種類の実手ではない |
| T-04/05 | 限定条件PASS、各10回は未達 | 実TCPで開口回転→傾き→復元2周期成立。受理された回転100命令・傾き102命令。実Slicerの回転中は法線・中心不変、角度が変化。傾き中は法線が変化。両モードの実ラベル一致を観測。命令数を独立提示回数に換算しない |
| T-06 | 置換10回PASS、他条件未検収 | 実TCPで旧→新接続を10回置換し、新接続のstatus応答／接続正常・停止を全件確認。遅延drop等の実Qt全条件10回は今回未実施 |
| T-07 | 接続観測PASS、停止継続FAIL | 600.27秒、600サンプル、接続・fresh喪失0、通信／カメラ喪失ログ0。受付中45サンプル、手形あり17サンプル。途中で明示停止を要求した。受付変化の意図は未確認で、自動誤開始とは断定しない |
| T-08 | FAIL（600秒未達） | 第1試行11.64秒、第2試行72.89秒で「target window is not foreground」により停止。各試行1件の拒否。第2試行は2周期完了。remaining_deltasは両試行とも回転／傾き0。ゲートは迂回せず、第三試行を強行しない |
| T-09 | 基本描画／前後照合PASS、全表示条件未検収 | 実ドックで方向プレビューあり、両モード見出し一致。試験後の中心・直径10mm・方向・カメラ・台帳一致。サイズ変更値や正面／斜め／側面全条件を今回試験したとはしない |
| T-10/11 | 未検収 | 本人の実手、規定距離・傾き・照明・左右、隔離Slicerの保存通しは今回未実施 |

T-01/02の257件はPythonの自己検証。追加の開始保持30回も同じ自己検証で、独立レビューではない。

T-03の入力：[認識生結果](../work/20261011-illustrated-recognition.json)、[推定点の再生入力](../work/20261011-illustrated-recognition.replay.json)、[開始保持30回](../work/20261011-start-hold-30.json)。左右・上下へ画像を50px移動して再推論し、各方向40/40フレームOPEN_PALM：[移動入力](../work/20261011-movement-replay.json)。これは実カメラ映像ではない。

T-07：[通常認識10分の全メタデータ](../work/20261011-camera-600s-result.json)。停止継続のFAILを接続PASSへ混ぜて総合PASSとはしない。

T-04/05/08：[第1試行の拒否](../work/20261011-long-tcp-attempt1-result.json)、[第2試行の命令全件](../work/20261011-long-tcp-result.json)、[実Slicer幾何・ラベル観測の集計](../work/20261011-slicer-geometry-summary.json)。Qtタイマーで2584サンプルを読み取り、同一モード中の版更新を回転55サンプル／傾き55サンプルで観測。回転中の法線差0、全変更サンプルの中心差0、両モードの角度／法線変化と見出しを確認。全観測時間には通常認識、試験待機、切断期間も含むため、2584サンプルを10分編集成立とは報告しない。

再生は実OperationController・SlicerSessionClient・TCP・サーバーの版／受付／凍結／前面条件を通す。ただしapp.pyのカメラ取得・品質評価・実手の判定経路全部を通した試験ではない。手下げは試験入力で明示したShape.NONE。各周期の復元命令とresume_draftは試験スクリプトから明示送信した。

T-06：[実接続置換10回](../work/20261011-connections-result.json)。通常カメラ入力と同時には接続しなかった。認識不能入力や受付開始の安全条件を緩める変更も行っていない。

## 終了状態と残りの検収

反復試験終了後に[前後照合結果](../work/20261011-slicer-restore-result.json)を作成。仮C ID不変、中心差0、法線／基底の差は最大7.13×10⁻¹⁶、角度差6.11×10⁻¹⁶rad。直径10mm、カメラ、台帳SHA256一致。版449→651は実編集による進行で巻き戻していない。確定・取消・シーン／台帳保存なし。読み取りQtタイマーは停止済み。

通常run.ps1でPixel認識を再起動し、[終了状態](../work/20261011-recognition-restored.json)でfresh/connected=true、armed=false、draft=true、frozen=true、1280×720、24.4fpsを確認。試験用TCPは閉じ、通常認識1系統へ戻した。これらは確認時点の状態で、停止状態の永続保証ではない。

実手T-10/11、V-02/05/08/09/10の全条件、V-07の遅延drop等の実Qt反復、Slicer新規起動と長期運用は未検収として残す。次に本人の開口方向操作とグー戻りを確認し、隔離デモ／試験用台帳で確定・取消・既知保存不合格を再試験する。
