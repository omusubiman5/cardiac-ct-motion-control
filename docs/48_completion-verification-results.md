# 完成判定の検証結果（2026-10-12）

## 完成指示後の追加検査・現在の判定

2026-10-12、docs/38 Q01〜08／docs/47に基づき実施。**階層戻り・配布プロセス判定の実装修正は完了、プロジェクト全体の完成は未達**。本人の実手参加は「後で参加する」と回答済みで保留している。以下は自己検証と実ツール観測の結果であり、独立受入や実手検収に置き換えない。

| 対応 | 最新の結果 | 証拠と判定の限界 |
|---|---|---|
| K02／P01〜02 | 修正後PASS | 台帳選択の明示保存→別PIDで起動復元、不正設定拒否を実Slicerで確認済み。`work/storage-restart-verification`、`work/storage-normal-startup-result.json`。下の初回FAILは履歴として保持 |
| K03／Q01・04・07 | 認識2245、tools Python21、配布predicate98件PASS | 追加戻り5件、試行表5件を含む。別AI追加レビュー6条件PASS。Slicer側は直前の184件成功後ソース変更なし。今回184件を再実行したとは数えない |
| K04／Q03 | Qt編集遅延・順序逆転2ケース45項目PASS | `work/completion-native-ui-20261012/qt-edit-delay-results.json`。実TCP・Qt callback・描画ACK・保存。旧確認0保存、新版再確認後各1保存。保持時計は人工で実手時間性能ではない |
| K05／Q06 | 通常600.094秒・2993観測PASS | `work/completion-normal-final-monitor-20261012/results.json`。全数fresh・connected・停止、drop0、初回欠落0、最大age0.491秒／往復2.719ms。認識率・実手操作の合格ではない |
| K06／Q01 | 5選択ページの階層戻り、20状態・22項目PASS | `work/completion-menu-qt-20261012/qt-menu-back-results.json`。OperationControllerから実TCP・隔離共有状態・実Qt表示。初期ページsetupは直接設定、FIST戻りはupdate経由。編集／保存0 |
| K06／Q02 | 実マウス列と分類後合成手入力列、15段階・68項目一致、保存比較8項目PASS | `work/completion-audit-20261012/hand-mouse-comparison-results.md`。実表面ドラッグ・方向／傾斜スライダー・wheel等を確認。3行の入力モードは同一比較対象外と明示。実手認識・全H/V・全喪失列は未実施 |
| K06／Q08 | 受付停止／実TCP切断の引継ぎ部分、2ケース283項目PASS | `work/completion-handover-20261012/loss-handover-results.json`。実UIでmouseへ引継ぎ→開口編集→hand返却。旧手要求0作用・返却後停止凍結・各1.203秒自然再開0、armのみ編集拒否、resume後に成立。保存0。物理遮蔽／カメラ断とX-02の全操作列は未完了 |
| K07／Q05・07 | 現在版候補の整合性PASS、署名後検収は未実施 | `artifacts/releases/20261012-143600`、6386ファイル、現行88ソース差分0、認識21・Slicer25ソース束縛PASS。3対象NotSigned。`work/completion-audit-20261012/release-final-summary.json`。未署名候補は未有効化 |
| K07／Q05 | 実トークン／通信メタデータを6回・34.730秒観測 | `work/active-normal-environment-corrected-r2.json`。Slicer30896・認識launcher81264／実体90380を全回捕捉、非昇格、読取エラー0、TCP loopback／UDP0。短時間通信と保存先の完全監査、署名版の一般ユーザー全機能検収は未完了 |
| K08／Q06・08 | 通常環境保全PASS | `work/completion-audit-20261012/normal-final-probe.json`で台帳4本・視点不変、5mm・停止・仮Cなし・現行runtime受入。試験PID28948／20788終了、通常30896のみ。`fixture-cleanup.json`、`handover-fixture-cleanup.json`。通常実画面の停止・仮Cなし・メニュー閉も確認 |

通常と最終候補のruntime canonical SHA256は`3618a9d279e370b3e05658a2ff572e9166dbb67bdee9cf908c70e98b71452815`。通常Slicerを追加起動せず、認識器のみ更新した。旧台帳2本は原本保持、新台帳2本は各0byte。カメラ画像・患者画像は保存していない。

### 未実施条件と先行失敗の扱い

- 実手H12/V10・元480明確形＋不明形・親指下補助80試行・切替等240試行・操作性／意図／疲労は未実施。元試行を減らさず、`current-trial-matrix.json`の実測欄を空欄に保った。本人が参加できる時に実施する。
- 原文docs/23 X-02は4喪失条件それぞれの配置→移動→連続傾斜→開口→確定と取消を要求する。今回2条件の引継ぎ・開口編集部分が通っても全列完了としない。
- 正規署名者による署名、署名後の実起動／停止更新／rollback、完全な通信／保存先監査、別検収者の受入は残る。ローカル署名候補0件、Security監査ログ取得は現権限で不可。信頼変更・未署名拒否の迂回はしていない。
- 初回認識回帰はcwd誤り、次はsandbox内で途中停止。再試験2245件成功までのログを保持した。最初のマウス確定クリックは保存0で、実成功の別phaseと区別した。
- Qt遅延試験の3先行試行と引継ぎ初回75秒入力待ちtimeoutを保全。引継ぎ再試行の段階外hand返却信号1回も記録し、採用ケースへ加算していない。詳細はdocs/39最新節と`work/completion-audit-20261012/loss-handover-plan.md`。

別AIの最終文書・集約証拠照合は`work/completion-audit-20261012/final-report-independent-review.md`。K05の60秒／600秒の関係を修正後、対象範囲の未解消所見0。独立受入とは区別する。終了時の台帳4本hash再照合も不変（`ledger-closeout-check.json`）。

## 以下は初回検証と先行修正の履歴

実装後追跡：docs/38 P01〜04によりK02の台帳選択維持を実装し、新規実Slicerプロセスの保存→復元、通常設定の読取復元までPASS。K07の現行版差分は新候補20261012-140724で0、runtime対応25ソース・6386ファイル照合PASS。ただし未署名・未有効化のため署名後検収は残る。証拠はdocs/39最新節。以下の表は実装前の検証結果として保持する。

検証計画： [docs/47](47_completion-verification-plan.md)。要求・実装計画正本はdocs/03・23・33・38。本人最新指定のC基準直径5mmを使用。**全体完成は未達**。試験コード・期待値は自己作成であり、実Slicer使用部分も独立検収とは異なる。

| ID | 判定 | 実施結果・証跡 |
|---|---|---|
| K01 | PASS（今回の範囲） | 新規実Slicer PID84912で直径5mm、点半径2.4999999999999996〜2.5mm。通常Slicerでも次回直径5mm。寸法変更・既存C保持の回帰を含めて成功。work/verification-20261012-suite/dimension-probe.json、normal-probe.json |
| K02 | FAIL | 通常選択先はevents-20261012-clean.jsonl／plans-20261012-clean.jsonlだが、起動時既定値はevents.jsonl／plans.jsonlのまま。初期化が既定値を使用し、起動scriptに選択復元処理がないことを照合。通常Slicerそのものの再起動は行っていない。work/verification-20261012-normal-probe.json |
| K03 | PASS | 認識2240、Slicer173、tools5、合計2418件成功。work/verification-20261012-{recognizer,slicer,tools}.txt。初回はルートディレクトリで一括実行したため5件のimport収集エラー。これは実行手順不備で、ログverification-20261012-pytest.txtを保持。各プロジェクトのcwdで再実行した |
| K04 | PASS（自動suite範囲） | 実Slicer・実TCP・人工球体でnative 60要求、hold-binding、fault、integrity、target-changeの5試験群passed=true。work/verification-20261012-suite/*results.json。通常台帳へ試験記録を書いていない。直接TCP・合成入力の自己検証であり、実手／実マウス全列比較ではない |
| K05 | 再試験PASS（60秒範囲） | 初回60.156秒300サンプルで接続fresh=true・通信drop=0。しかし開始時からarmed=true（300件すべて）、shape=none。停止維持条件は不成立。自動試験は開始操作を送っていないが、観測前に開始された意図・実手状態は未確認。停止前提を確認しなかった試験手順不備として記録。実Slicer dispatcherのdisarm成功後の再試験は60.156秒300サンプル全数fresh・connected・停止維持、通信drop=0、最大状態age 0.230秒、最大往復2.145ms。work/verification-20261012-normal-stopped/results.json |
| K06 | 未実施 | 本人の実手H/V・480明確形＋不明形・手／マウス全列比較・操作性評価は未取得。実手確認の可否を質問済み。静止画や合成入力で代替合格にしない。今回の60秒監視は600秒要件の代用ではない |
| K07 | 不適合／署名後実行は未実施 | 最新保存配布物20261011-181915を読取検証し6383ファイルの整合性PASS。ただしactivate/start/manifest catalogは全てNotSigned。現在ソースと15ファイルの差分を確認した。旧配布物の整合性は現在版との一致を意味しない。work/verification-20261012-release-inventory.json、signatures.json、release-current.json。信頼変更や署名拒否の迂回は行っていない |
| K08 | 終了状態確認、独立検収未実施 | 試験Slicer PID84912はrunner finallyで終了し、通常PID30896の1個のみ。旧2台帳hashは切替前と同じ。新台帳2ファイルは各0byte、通常仮Cなし。実パネルで停止・仮Cなしを確認。独立検収は未実施 |

## 版と保全

通常runtime SHA256：`aaef1e632e98f4d258fee307f0b1568b96442d7059dc5eb71fb2b04cb5f22e17`。新プロセスのCStampModuleソース（UTF-8/LF正規化）SHA256：`0f549d56f49aa5d7035342dc10edb3659a8c3053a4e62dd31ead86b3b6f06b35`。認識アプリと通常Slicerは実際に起動して接続を観測した。カメラ画像・患者画像は保存していない。

## 次に閉じる条件

1. 台帳選択を停止中に保存・復元する実装と、再起動を通した検証。既存原本保持、仮C残存中の切替禁止を維持する。
2. 現在ソースを含む配布版の再作成・正規署名後の起動／更新／rollback・一般ユーザー／通信監査。
3. docs/38 W-06/07の実手・代替マウス比較と未消化の全条件、独立検収。今回のsuite成功だけでこれらを完了にしない。
