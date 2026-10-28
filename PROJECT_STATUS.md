# 担当Codex報告 — Cardiac CT Motion Control

## 2026-10-27 低スコア救済を全離散手形へ拡張 + 幾何値をstate公開 → `20261027-225651` 配布・起動

本人指摘「何回親指だけで修正するんだ」— 正しい。1手形ずつの対処ではなく体系的に修正。

**変更1（`standard_gesture.py`）**：モデルスコア < 0.65 時の幾何検証を**全離散手形**へ拡張：
- `Closed_Fist` → 幾何 FIST で受理
- `Thumb_Up` → 伸展親指・下向きでない（forward > -0.35）で受理（geo THUMB 完全一致も可）
- `Thumb_Down` → 指屈曲 + 親指伸展・後方（forward ≤ -0.35）で受理
- `ILoveYou` → 指パターン [index,pinky]=伸展・[middle,ring]=屈曲 で受理（`extended_fingers` 新設）
- `Victory` → 指パターン [index,middle]=伸展 で受理
- モデル判定と幾何が食い違う場合は従来どおり UNKNOWN — フェイルクローズ維持

**変更2（`gesture_fsm.py`）**：`extended_fingers()` 公開関数追加（classify_shapeと同一の指伸展判定を再利用）。

**変更3（`ui_bridge.py`）**：`thumb_geometry`（角度・長さ・外側・前方比率の実測値）をstateチャンネルへ公開 — 今後の親指系問題は実測値で即診断可能。

テスト：`test_standard_gesture.py` 34件パス（救済受理/拒否・上下方向分離・側面親指帯域を網羅）。`runtime.json` の `software_sha256`（3ファイル）を両ワークツリーで再固定 → SBOM再生成 → `20261027-225651` 署名全Valid → アクティベート → 起動：Slicer PID 76168・認識 PID 112948・connected=true。ショートカット更新済み。

残存：実手での全工程検収未了。今回の救済は「モデルのトップ判定＋幾何確認」の2重チェック — 低スコアかつ曖昧な手形は依然拒否（安全側）。

## 2026-10-27 左ドックのガイドを「今の状態／次の選択肢＋手形」形式へ改修 → `20261027-003100` 配布・起動

本人指示：「①いまの状態 ②次の選択肢（③ジェスチャー）」を左画面に出せ — ガイドがないから操作性が悪い。実測で凍結中にメニューが「この仮Cを確定する」を提示し続け（commit×8全拒否・resume_draft未送信）、画面には解除方法が出ていなかったことが裏付け。

**変更（`unified_hand_panel.py` のガイド生成）**：全状態を「【今】＋【次】」形式に統一し、**凍結案内をメニュー表示より優先**（従来はメニュー表示中に凍結案内が隠れていた）：
- 凍結中：`【今】仮Cが凍結中` → `【次】🤟：凍結を解除して編集へ（解除まで他の手形は効きません）`
- 確定確認ページ：`グー：確定実行　親指下：編集に戻る` を明示
- メニュー・照準・編集・停止・視点各状態も同形式で手形→動作を列挙

検証：パネルガイドの単体テスト対象外（表示のみ）・`runtime.json` の `slicer_software_sha256` 再固定（両ワークツリー）→ SBOM再生成 → `20261027-003100` 署名全Valid → アクティベート → 起動：Slicer PID 92884・認識 PID 66300・connected=true。ショートカット更新済み。

残存課題（動作側・別途）：凍結中にグーで確認ページを開ける行き止まり経路はコントローラ側で塞ぐべきか — ガイド表示で回避は可能だが、凍結中のグー・親指を無効化する実装変更は本人の判断を要する（拒否はサーバで安全側に働くため現状でもデータ損失はない）。

## 2026-10-26 低スコア親指/グーの幾何検証による救済 → `20261026-224140` 配布・起動

本人指摘「クリアな親指上げがスコア0.61-0.64で拒否されるならハンドジェスチャーではない」— 正しい。MediaPipe標準モデルはこのカメラ条件下でThumb_Upに0.6台前半のスコアしか出さず、設計上「グー・親指はモデルスコア≥0.65のみ受理」のため実用不能だった。

**変更（`standard_gesture.py`）**：モデルスコアがしきい値未満の場合、従来一律 `UNKNOWN` だったのを**決定論的ランドマーク幾何で検証し、同一手形が確認できた場合のみ受理**するよう変更：
- `Closed_Fist` 低スコア + 幾何 `FIST` → FIST受理
- `Thumb_Up` 低スコア + 幾何 `THUMB`（伸展・前方指向）→ THUMB受理
- `Thumb_Down` 低スコア + 指屈曲（幾何FIST/UNKNOWN）+ 親指伸展・**手首軸後方（forward_ratio≤−0.35）** → THUMB_DOWN受理（上げ下げの方向を幾何で分離）
- 不一致（モデルはグーと言うが指が出ている等）は従来どおりUNKNOWN — **フェイルクローズは維持**。ILoveYou/Victoryは引き続きモデルスコア必須

テスト：`test_standard_gesture.py` に8件追加（低スコア+幾何一致→受理、モデルと幾何不一致→拒否、親指下げ方向検証）→ cmos全体 **2,285件全パス**。`runtime.json` の `software_sha256`（standard_gesture.py）を両ワークツリーで再固定 → SBOM再生成 → リリース `20261026-224140` 署名全Valid → アクティベート → 起動：Slicer PID 109836・認識 PID 135916・connected=true。デスクトップ両ショートカット更新済み。

併せて `docs/59_c-stamp-operation-scenario-20261026.md` を作成（本人要求の操作シナリオ：各手形→画面変化→失敗分岐の全工程、メニュー中の人差し指=パンの落とし穴を明記）。

残存：実手での全工程検収未了（この版で親指・グーの受付帯域が広がったため、先の0.6台スコア問題は解消しているはず）。

## 2026-10-26 起動失敗の根本原因特定 → runtime.jsonへ `loss_grace_s` 追加し `20261026-180007` で復旧

認識が `connected` に到達せず起動器が readiness timeout で失敗し続けていた問題の根本原因を特定・解消。

**原因**：認識側はSlicer接続時に自コンフィグ（`config.public_dict()` 全項目）を hello で送信し、Slicer側 `runtime_contract.py` が署名済み `runtime.json` の `recognizer` ブロックと**完全一致**を要求する。認識喪失猶予の実装で追加した設定キー `loss_grace_s=1.5` がコードに存在するが `runtime.json` に未登録だったため hello が `recognizer actual configuration differs from prepared configuration` で拒否され、認識はエンドポイント登録前に exit 2 で即死。起動器はstderrを捨てるため「readiness timeout」しか見えず、盲目診断を強いられた。

**診断経緯**：起動器コピーに出力リダイレクトを追加し実行しても空（pythonのstderrがパイプバッファに残ったまま即死した可能性）→ 同一引数で手動実行して実エラーを取得 → `--prepare-configuration` で実マニフェストをダンプし署名 runtime.json と diff → 差分は `settings.loss_grace_s` の1キーのみ（カメラID・モデル・ソフトウェアhash・python/windows版は全一致）。

**対応**：`artifacts/cstamp/runtime.json` の `recognizer.settings` に `"loss_grace_s": 1.5` を追加（C:/A:両方）→ 実マニフェストとの完全一致を検証 → SBOM再生成（sbom-20261026.json）→ venv pythonで `prepare_completion_release.py` → 3ファイル署名全Valid → アクティベート → 起動：Slicer PID 32816・認識 PID 24480・**connected=true**・state鮮度0.14s。デスクトップ両ショートカットを `20261026-180007` へ更新（`$args` はPowerShell予約変数で代入不能のため失敗していた — 変数名変更で解消）。

**教訓**：
1. **recognizer settings に新キーを追加する実装変更は runtime.json の再生成を必須とする**（完全一致契約）。prepare_configurationでのdiff確認をリリース前手順に組み込むべき。
2. `start_completion_release.ps1` は認識の stdout/stderr を捨てる — 障害時は同一引数（`startup-*-recognizer.json` + `--slicer-connect --trial-log`）で手動実行すれば実エラーが見える。
3. Slicerの `--python-script` はkill直後の再起動で喪失しうる（SlicerApp-realが引数なしでspawnされる現象を観測。完全停止を確認してから起動すること）。

残存：実手での全工程検収（🤟→親指上→人差し指→グー→🤟解除→グー→グー確定・途中凍結含む）は本人実施が未了。稼働中：Slicer 32816・認識 24480・camera index 0 (Android Webcam)。

## 2026-10-25 カメラ表示なし → Pixelがadbモードに戻っていた（UVC関数名は `uvc` が正解）

本人報告「カメラが表示しない」。実測診断：認識・Slicer・プレビュー配信は全て正常だが `fault: camera read failed`（capture 1000msタイムアウト・fps 1.0）。デバイスマネージャで「Android Webcam」2件とも `Unknown`、adbでは `4A171JEKB04764 device`（**adbモードのままUVCを出していない**）。

対応：抜き差し後 `svc usb setFunctions webcam`・`webcam,adb` とも受理されるが `sys.usb.config` が `adb` のまま → **`uvc` で即切替成功**（この端末=Pixel 8a/akitaでは `webcam` は無効関数名。docs/22の記述は旧端末向け）。切替後も認識側は切替前のOpenCVハンドルを保持し自動復帰しないため、認識プロセスのみ再起動（Slicer無停止）→ `capture_ms 0.8・fps 25・手検出復帰` を確認。docs/22へ訂正記録済み。

復旧手順：① Pixel抜き差し ② `adb shell svc usb setFunctions uvc` ③ 認識プロセス再起動 ④ パネル「カメラを表示」OFF→ON（プレビュー要求は再起動で消える）。

## 2026-10-25 回転操作「甘い」原因を修正し署名リリース `20261025-183209` として配布・起動

本人報告「Cの回転操作が甘い」。コード精査で2つの実装上の損失を特定：

1. **デッドゾーンが遅い動きを全吸収**：`op_controller.py` のパー（view_rotate）とつまみ（rotate_opening）で、1フレームの移動量が `rotate_deadzone`(0.002) 未満だと回転を送信しないのに基準点（`_last_palm`/`_last_pinch_x`）は毎フレーム更新 → 30フレームで累計0.03動いても回転量ゼロ。微調整ほど無反応だった。**修正：基準点は送信した時のみ更新し、未満の移動は蓄積**（ジッターは正負相殺で発火しないためデッドゾーンの防振機能は維持）。
2. **サーバ側45°超過を丸ごと拒否**：`view_commands.py`(MAX_DELTA) と `CStampModule.py` の `op_rotate_opening`/`op_tilt` が |delta|>45° のコマンドをクランプせず拒否 → 速いフレームの動きが消失。**修正：±45°へクランプ**（`delta out of range` 拒否は非有限値のみに限定）。

設定値自体は据置：パー220°/norm・つまみ開口400°/norm・デッドゾーン0.002。`tilt_deg_per_norm` は手形割当なしの死に設定として残存（要別途判断）。

検証：cmos-motion-poc 2,277件・slicer-cstamp 187件（キャップ越え拒否テスト1件をクランプ仕様へ更新）全パス → `runtime.json` の3ファイルhash再固定（両ワークツリー）→ SBOM再生成 → リリース `20261025-183209` 生成・署名（全Valid）→ verify 6,386ファイル・エラー0・ソース25件一致 → アクティベート・起動：Slicer PID 21676・認識 PID 86924・connected=true。デスクトップ入口を `20261025-183209` へ更新。失敗一次ステージ `20261025-183021`（SBOM更新前に作成・inventory不一致で検証不合格）は破棄対象。

## 2026-10-25 エンドツーエンド・ドライランで全ジェスチャー経路を検証（26/26合格）→ 署名起動済み

本人要求「ドライランくらいしろ」に対し、実際の `OperationController`＋実 `SlicerSessionClient`＋実コマンドサーバ/ディスパッチャを使う全経路ドライラン `work/dryrun_full_flow.py` を作成・実行。

経緯（正直に記録）：初回実行は 26項目中13件失敗 — 「実装が動かない」という本人報告に対し、私が検証なしに修正を宣言していたことが数値で裏付けられた。失敗の内訳を全件追跡した結果、**本番コードの欠陥はゼロ**、全てドライランハーネス側のモデル誤りだった：
1. ジェスチャーラッチの安定時間 0.15s に対しドライランの保持時間 0.2s が境界不足 → エッジ不発（0.4sへ修正）
2. `recognition_lost` が呼ぶのは `ops.on_disconnect()`（実装の正式名）だがスタブがテスト用 `on_recognition_loss` を定義していたため凍結が起きなかった → 実装どおり `on_disconnect` で凍結・draft温存に修正
3. `commit sent` 判定が凍結中プローブの commit を誤カウント → 区間マーカで修正

修正後 **26/26 全合格**：hello/session → 🤟ホールドでarm（1回のみ）→ 🤟で主メニュー開・親指下末尾で閉 → 親指上でC呼出（select_mode aim 受理）→ 人差し指照準8回送信 → グーで仮配置stamp受理 → draft編集モード → recognition_lostで通知+サーバ凍結+凍結中commit拒否+draft温存 → コントローラがstatusで凍結検知 → 🤟で `resume_draft`（メニューを開かず直接編集復帰）→ グーで確認ページ（snapshot束縛）→ リリース後の2回目グーでcommit受理（rev=0束縛・サーバ確定）。

回帰確認：cmos-motion-poc 全テスト 2,277件、slicer-cstamp 全188件パス。本番ソースはリリース `20261025-175928` と一致（変更なし、ハーネスのみ修正）。

実機状態：稼働していた認識プロセスが終了していたため、署名起動器で `20261025-175928` を再起動 — Slicer PID 11776・認識 PID 92208・connected=true・armed=false・generation=1・コマンドサーバ 127.0.0.1:18944 listen・デモシーン読込済み。デスクトップ入口のショートカットを旧 `20261021-130141` から `20261025-175928` へ更新。

残存：実手での全工程検収（🤟→親指上→人差し指→グー→🤟解除→グー→グー）は本人の手形での実施が未了。

## 2026-10-25 凍結仮Cの解除を🤟へ変更し署名リリース `20261025-170134` として配布・起動

本人指示：「手術中にマウス解除は出来ない。解除にILOVEYOUにしろ」。docs/57の「凍結再開は手形の対象外・マウス経路」を本人権限で改訂。

実測経緯：stamp（仮配置）成功後に `recognition_lost` が発火し仮Cが凍結 → 2回目のグーの `commit` が「draft is frozen after recognition loss」で拒否されていた。確定操作自体は正常に送信されており、ブロッカーは凍結保護だった。

変更：
- `op_controller.py`：armed中のILOVEYOUエッジで `draft_frozen` なら `resume_draft` を送信してから従来どおり主メニューへ戻る（「開始に戻る」の意味を保ちつつ凍結解除を兼務。仮Cは破棄しない）。`draft_frozen` は既存のstatus応答反映で追跡済み。
- `unified_hand_panel.py`：凍結中ガイドを「I Love Youでメニューを開き…選択」（存在しないメニュー項目を指す旧表記）→「I Love You：凍結した仮Cの編集を再開」へ修正。
- `docs/57`：操作ツリー・意味表・仕様節の凍結再開を🤟へ改訂（マウス経路「仮C編集を再開」も併存）。
- テスト：`test_iloveyou_resume.py` に2件追加（凍結時resume_draft+menu_open送信、非凍結時はmenu_openのみ）。認識側 2,277件・Slicer側 188件 全パス。

リリース `20261025-170134`：venv pythonでSBOM+prepare（前回教訓反映）→ 署名全Valid → アクティベート → 起動。Slicer PID 52164・認識 PID 80796・connected・armed=false。verify：6,386ファイル・エラー0・ソース25件一致。`runtime.json` の recognizer.software_sha256（op_controller.py）と slicer_software_sha256（unified_hand_panel.py）を両ワークツリーで再固定済み。

**修正（同日続報）**：上記版で判明した操作経路の欠陥 — 凍結解除の🤟が主メニューを開くため、直後のグーが「確定確認を開く」ではなくメニュー項目選択（select_mode）を消費し、確定に辿り着けなかった（実測：仮配置→認識喪失凍結→🤟でresume_draft成功→メニュー開放→グーがselect_modeになる）。`op_controller.py` を修正：凍結仮C中の🤟は `resume_draft` のみ送信しメニューを開かず編集へ直接復帰（開いていたメニューは閉じる）。これで「仮置き→🤟解除→グー→グーで確定」が成立。テスト更新済み・61件パス。リリース `20261025-175928` として再生成・署名（全Valid）・アクティベート・起動：Slicer PID 17808・認識 PID 123252・connected。旧仮Cはプロセス再起動で消失（アクティベーションは停止状態必須のため凍結解除テスト中の仮Cを温存できない）。

## 2026-10-25 ゲート一括診断 `diagnose` コマンドを実装し署名リリース `20261025-162638` として配布・起動

本人選択「ゲート一括診断」に基づき実装。目的：どの安全/実行時ゲートが落ちているかを1回で可視化し、1ブロックずつ試行錯誤する必要をなくす。読み取り専用・非破壊で、既存ゲートは一切緩めていない。

変更（A:ワークツリー→C:へ同期、両方の `artifacts/cstamp/runtime.json` の `slicer_software_sha256` を3ファイル分更新）：

- `command_protocol.py`：`diagnose` を `PRE_ARM_COMMANDS`（=KNOWN_COMMANDS+FOREGROUND_EXEMPTに自動含有）へ追加。さらに runtime検証（wire `verify_runtime_request`／local `verify_runtime_local`）と入力owner照合の例外集合へ追加 — **契約不一致・owner不一致・非フォアグラウンド・disarm状態でも診断自体は必ず動く**設計（壊れたランタイムが自分のブロッカーを報告できるようにするため）。guard対象集合（`verify_action_target`・mode・draftゲート）は無関係で非該当。
- `CStampModule.py`：`op_diagnose` を新設。各チェックを個別try/exceptで評価し `{name, ok, detail}` の配列を返す — 1項目の例外が後続を潰さない。対象：storage/ledger、runtime_manifest、slicer_sources、slicer_version、target_registry_file、registry_matches_manifest、target_identity（登録行ごとに scene_id/model_name/model_sha256/transform_sha256/scene_sha256 のフィールド単位差分をdetailへ）、surface_node。`result.state` に armed/mode/layer/draft/input_owner/session/foreground を添付。mutatingハンドラは一切呼ばず dispatcher/aim/draft/ledger を変更しない。
- `unified_hand_panel.py`：左ドックに「ゲート診断」ボタン追加 → `dispatcher.dispatch_local('diagnose', input_method='mouse')` でプロセス内実行し、✓/✗各行＋state要約をQMessageBox詳細表示。認識セッション不要・マウスフォールバック経路。
- `tests/test_command_protocol.py`：4件追加 — disarm中実行・非変異、foreign owner不阻害、runtime不一致でもlocal/wire両経路で生きる、wire前景免除。25/25パス、slicer-cstamp全体188/188パス（退行なし）。

リリース：`generate_sbom.py`・`prepare_completion_release.py` は **venv pythonで実行が必須**（`runtime_file_inventory` が実行中インタプリタのdistributionsを列挙するため、システムpythonで実行するとrecognizer-runtimeが空になり起動器のpip inventoryで失敗 — 1度失敗ステージ 20261025-162512(269K)を作り破棄して再実行）。`20261025-162638` 生成・署名（全Valid）・アクティベート・起動：Slicer PID 8364・認識 PID 47764・connected=true・armed=false・generation=1。`verify_completion_release.py`：6,386ファイル・エラー0・Slicerソース25件一致。

注意：wire経路の `diagnose` もhello後の通常エンベロープ内で有効だが、現状の利用経路はパネルボタン（dispatch_local）のみ。認識側への送信機能は追加していない。対象identityゲートの「view操作へも適用」という過剰結合は未変更 — 診断で可視化した上で、view/target選択/target変更の3層分離は別途判断。

## 2026-10-25 対象登録を更新し署名リリース `20261025-160445` として再配布・起動（arm拒否を解消）

実測で判明：`arm`（🤟受付開始）が「target is unregistered, ambiguous, or changed」で拒否され、`armed=false` のままだったためパー回転等すべて無効だった。原因は `artifacts/slicer/CARTO3_EA_Map_Demo.mrb` が10/24 07:27に再保存され `scene_sha256` が変化したこと。メッシュhash（a78702d7…=CARTOmesh_1-OG, 9,957頂点）・transform hash・scene_id は登録と完全一致を実シーン観測で確認 — 同一承認対象のため `targets.json` の `scene_sha256` のみ実測値（402e8bcf…）へ更新し、`runtime.json` の `target_registry_sha256` を TargetRegistry 正規計算で再生成（2f301883…）。A:/C:両コピーを同期。

上記をdeployment_configurationへ反映した新リリース `20261025-160445` を生成・署名（catalog/activate/start 全てValid）・アクティベート・起動：Slicer PID 113380・認識 PID 118284・connected=true・armed=false・generation=1。共有状態の拒否理由に「対象登録を確認してください」が消失し、通常の「🤟を1.5秒保持して再開」案内のみになった。実手での受付開始→操作の最終検収は本人の手形で行う。

## 2026-10-25 新版署名リリース `20261025-143644` を作成・配布・起動（一意化ジェスチャー+新UIを含む版）

本人「当たり前、実装して」に基づき、一意化ジェスチャー+コンセプトUIを含む新署名リリースを作成した。

手順（全てローカル `C:\Projects\Cardiac-CT-Motion-Control` で実施）：
1. A:ワークツリーから `prototypes/`・`tools/`・`artifacts/cstamp`・`artifacts/slicer` をローカルへ複写（前節の新版起動と同一コピー）。
2. 旧リリースの `payload/recognizer-runtime` を `prototypes/cmos-motion-poc/.venv` として再利用（pyvenv.cfgのhome・commandが元来このパスを指していた＝事実上の元venv復元）。cv2/mediapipe import可を確認。
3. `generate_sbom.py` → `artifacts/sbom/sbom-20261025.json`（88ファイル・40依存）。
4. `prepare_completion_release.py --slicer-executable <Slicer.exe>` → `artifacts/releases/20261025-143644/` ステージング。
5. `CStampPoC-Dev (non-clinical)` 証明書（thumbprint 262148C3…、CurrentUser\My）で manifest.json.ps1・activate/start_completion_release.ps1 を署名（全てValid）。
6. `activate_completion_release.ps1` 実行 → `current-release.json` が新manifestを指し、`previous-release.json` へ旧ポインタ退避。
7. 署名起動器 `start_completion_release.ps1` で起動 → 全照合通過、Slicer PID 81712・認識 PID 24864・connected=true・armed=false・generation=1。
8. `verify_completion_release.py` 実行 → inventory_passed=true・6,386ファイルエラー0・runtime_source_passed=true（Slicer側25ファイル一致）。結果 `work/verify-20261025/result.json`。

稼働版の正式ジェスチャー割当（このリリースに同梱）：🤟=受付開始/ホーム、親指上=前項目・C呼出、親指下=次/仮C取消、グー=決定/仮配置/確定確認、3本指=初期値、パー=回転、人差し指=パン/照準/移動、つまみ=ズーム/開口方向、2本指=なし。

残存：`targets.json` の対象hash不一致は変わらず、照準→仮配置は対象登録再作成まで拒否される。実手での検収（🤟→メニュー→グー決定、親指上C呼出→照準→グー仮配置→つまみ開口→グー確定→親指下取消）は未実施。デスクトップ入口は旧リリースのパスを指す可能性あり（更新は未確認）。

## 2026-10-25 署名リリース20261021-130141をローカルコピーで起動成立（NAS直接起動はreadiness制限超過）

本人の起動要求に対し、署名リリースをNASパス(A:\)から起動する試行で3段階の障害を切り分け・解消した。

障害1：`powershell.exe`(5.1)での起動は `ProcessStartInfo.ArgumentList` がNullとなり起動器165行目で `InvokeMethodOnNull`。デスクトップ入口と同じ `pwsh.exe`(PS7)を使うことで解消。起動器はPS7前提と判明。

障害2：NAS(A:\/UNC)上のペイロードでは起動readiness制限に間に合わない。計測では cv2+mediapipe のimportだけで約46秒（ローカルでは数秒）。起動器の制限はSlicer 60秒（199行目）・認識30秒（245行目）。NAS初回はSlicerが約120秒、認識はエンドポイント記録まで辿り着けず両方ともタイムアウト。NAS上のファイルを編集せず、リリース一式(703.6MB/7146ファイル)を `C:\Projects\Cardiac-CT-Motion-Control\artifacts\releases\20261021-130141` へrobocopyし、ローカル `current-release.json` を作成してローカルパスで起動した。なお認識器のエンドポイントargvは `Path(sys.argv[0]).resolve()` でA:ドライブがUNC実体へ正規化され、起動器側のA:表記と文字列不一致になる問題も確認済み（UNC指定でも制限時間が同じく超過するため実害解消にはローカル化が必要だった）。

障害3：C:ワークスペースに `artifacts\slicer\CARTO3_EA_Map_Demo.mrb` が不在で `loadScene` がRuntimeError（`server_log.txt`で特定）。A:から `artifacts/slicer/` を複写して解消。

途中でペイロード `recognizer-runtime` のpip配布物6ファイル（`operations/build/`）が欠損しており、同梱の `pip-26.2.1` ホイールから復元した。復元後に起動器の全ハッシュ照合（manifest・SBOM・外部実行ファイル・deployment_configuration・components・runtime_dependencies・pip freeze突合）を全数通過しているため、復元内容は署名対象と一致している。

現在の稼働：Slicer PID 87000（コマンドサーバ 127.0.0.1:18944 listen、デモシーンC:から読込済み）、認識 PID 17236（connected=true・armed=false・generation=1）。起動器のreadiness全条件を通過した正規起動。

実行中リリースの正式ジェスチャー割当（ペイロード `op_controller.py` docstringから確認）：🤟ILOVEYOU 1.5秒保持=受付開始／親指=メニュー／2本指=次・仮配置／3本指=決定・確定／グー=メニュー閉・仮C取消／パー=回転（視点モード）／人差し指=パン・照準／つまみ=ズーム。10-21節の意味一意化はワークツリー上の未配布実装であり、この署名リリースには含まれない点に注意。

残存：旧来の `targets.json` 対象hash不一致は変わらず、照準→仮配置は対象登録再作成まで拒否され続ける。NAS側 `current-release.json` はUNC形式に書換済み（A:起動は制限時間の都合で実用不可のまま）。

追記（同日）：本人指摘「古いメニューに戻っている」は正しい — 署名リリースは10-21一意化・UI刷新の**前**の版。署名配布は未実施のまま。対応としてA:ワークツリーの `prototypes/`（新版ソース）と `artifacts/cstamp`・`artifacts/slicer` を `C:\Projects\Cardiac-CT-Motion-Control` へ複写し、旧プロセス停止後にローカルワークツリーから起動した。Slicer側・認識側ともにruntime.jsonの全hash照合を通過（新ソースのまま検証合格）、`status ok=True`・手検出動作中。実行中は一意化後の正式割当：🤟=受付開始/ホーム、親指上=前項目・C呼出、親指下=次/仮C取消、グー=決定/仮配置/確定確認、3本指=初期値、パー=回転、人差し指=パン/照準/移動、つまみ=ズーム/開口方向、2本指=なし。認識の実行環境はローカル複写済みの `recognizer-runtime`（署名済み依存一式、NAS遅延を回避）。これは署名リリース起動ではなく通常のワークツリー起動であり、新版の署名配布は依然として未実施。

## 2026-10-21 手形意味一意化：計画確定→実装→自己検証PASS（実手検収・署名配布は未実施）

実機観測で共有状態（mmap `Local\CardiacHandUI-v1-state`）を記録し、本人の「パーから親指上は操作できた。順番が固定されているから操作し難い」「ジェスチャーに重複した意味を持たせる設計がダメ」との指摘を確定した。認識・制御・メニュー経路は機能しており、問題は状態依存の多重割当（親指上=開く/前項目、2本指=次/仮配置/選択、3本指=決定/確定/訂正、グー=戻る/取消、パー=視点/開口/傾き、人差し指=パン/照準/移動/マーカー）と開始後の固定順序（FR-041/042の作業形限定準備移行）。

本人指示「ツリーを書き直し、これで実装計画書mdを作って実装して。完了後に実装報告書mdを作って」に基づき実装を完了した。計画 `docs/57_gesture-single-meaning-plan-20261021.md`、報告 `docs/58_gesture-single-meaning-implementation-report-20261021.md`。本人確定の最終ツリー：🤟=開始に戻る（停止中は受付開始＋主メニュー、受付中はどの枝からでも主メニュー）、親指上=上へ（メニュー前項目／メニュー外はC呼出）、親指下=下へ（メニュー次項目・末尾で戻る／仮C取消）、グー=決定（仮配置・項目実行・確定へ進む）、3本指=初期値（視点・仮C方向）、パー=視点回転、人差し指=指す（パン・照準・仮C位置）、つまみ=ズーム（仮C中は開口方向の限定割当）、2本指=なし。

変更：`op_controller.py`（意味一意マッピング・準備移行撤廃・安定点保持・手形切替直後の定住ウィンドウ・仮C中つまみ=開口方向・文脈に応じたselect_mode発行）、`hand_menu.py`（確認項目の手形表記）、`unified_hand_panel.py`・`slicer_hud.py`・`app.py`（案内・診断文言）、`docs/03`（FR-040〜043改訂）、`docs/45`（割当表・履歴保持）、試験群。認識・分類・通信プロトコル・サーバは未変更。

自己検証：cmos側2,275件＋slicer側184件すべてPASS。安定点保持（照準0.40,0.40→グーで0.40,0.40へ仮配置、切替ブレ0.70を反映しない）、確認画面経由の版・hash束縛commit、親指下取消→通常復帰、🤟ホーム（仮C保持）をアドホック連鎖でも確認。

**実手試行（進行中）**：runtime再構成で新ソースを起動し本人の実Pixel試行を開始（`work/realhand-trial-20261021/`、Slicer port 18944・認識器稼働中）。初回指摘2件を修正：①手メニューの不要枝（計画・記録・既存C訂正・停止）を剪定しマウス経路（詳細マウス操作タブ）へ移管、②メニュー表示中に連続操作を止める旧仕様でパーが無効だった問題を、ナビゲーションのみメニュー消費＋他手形は常時動作へ修正。**署名配布は未実施。**

現在地：計画どおりの実装と自己検証は完了。次の一手は本人の実Pixelで代表経路（🤟→メニュー→グー決定、親指上でC呼出→照準→グー仮配置→つまみ開口→グー確定→親指下取消）の検収と、検収後のruntime再構成→署名配布。自己検証を実手合格へ拡張しない。

## 2026-10-21 docs/55実装指示への再確認：実装・配布・起動は成立済み、実手🤟検収のみ残存

本人指示「docs/55を読み込んで実装し、実装報告書MDを作って」に対し、変更を加える前に現物を照合した。docs/55の実装は先行作業で完了しており、今回は照合のみでコード・設定・台帳・稼働プロセスの変更なし。

- 現行 `prototypes/` の変更対象ファイル（`op_controller.py` `fdb6ace1…`、`gesture_fsm.py` `7530da5b…`、`standard_gesture.py` `f32108c2…`、`unified_hand_panel.py` `ea29adb3…`）のSHA-256が署名済みrelease `20261021-130141` のmanifestと一致。`Shape.ILOVEYOU`、標準ILoveYou→開始、画面内作業形安定移行の実装が現物に存在することを確認。
- `artifacts/releases/current-release.json` は `20261021-130141` を指し、`previous-release.json` は `20261021-114744`。起動器・activation・catalog署名はAuthenticode `Valid`。
- 起動記録 `startup-1fcd9defcab5437c8e946dace5703829.json` は SlicerApp-real PID 112588 が `20261021-130141` ペイロードから port 18944・armed=false で起動したことを示す。稼働中プロセス（Slicer 49592／SlicerApp-real 112588／認識python 732・39260）も観測。
- 実装報告書 `docs/56_iloveyou-resume-implementation-report-20261021.md` は既存。自己検証2268＋21件PASSと配布記録を含む。

現在地：docs/55の実装範囲は完了済み。重複実装・報告書の新規作成は行わなかった。残存する検収は本人の実Pixel🤟→受付開始→画面内作業形への安定移行（手下げなし）のみ。自己検証と起動成立を実手合格へ拡張しない。

## 2026-10-21 実パー開始の成功を本人・通常ログで最終照合

本人の「成功！」を受領。修正版20261021-114744の通常命令ログで実Pixelフレーム71013→arm要求末尾002834→世代2／Slicer受理ok=trueを確認。先行ボタン操作（末尾000073、frame=null）とは別要求。共有状態もfresh、connected=true／armed=true／preparing=false／reason空／transport_drops=0。開始後のopen_palmフレーム71158→view_rotate要求末尾002864→カメラ変更→同一要求のVTK描画まで確認した。証跡 `work/session-fix-20261021/user-success.json`、詳細 `docs/54_hand-start-session-recovery-20261021.md`。

現在地：今回のパー開始不具合は実手で復旧を検収。照合のみで設定・プロセス・受付・シーンの変更なし。先行節の「実パー未確認」は当時の履歴として保持する。ハンド経路のC配置・方向調整・確定の全工程や長時間安定性まで完了した意味ではない。

## 2026-10-21 パー開始拒否のsession失効を修正・実アプリ引継ぎ後の開始を確認

本人画像はOpen_Palm／保持1.5秒を満たすが`no session; send hello first`。通常メタデータでも実Pixelフレーム892071からarm送信後、同理由でSlicer拒否、connected=trueのままと確認。マウスへの明示引継ぎでサーバsessionが失効する一方、認識クライアントがTCP継続を接続有効と扱う不一致が原因。前回のハンド返却は表示・停止しか検収しておらず、返却後の再開まで確認できていなかった点を訂正。

session_client.py 1ファイルで失効拒否時のcloseを追加。命令自動再送・自動armなし。次の既存statusが再helloする。修正前2条件FAIL→修正後は認識側2254件／プロトコル21件PASS（自己検証）。署名済みrelease20261021-114744をactivation・正式起動、6386配布ファイル／25Slicerソース照合エラー0。入口・catalog署名Valid。デスクトップ入口更新、保存済みC台帳hash不変・1件復元。

実画面でマウス引継ぎ→旧status1回拒否→connected=false→新helloで世代1→2／connected=trueを観測。ハンドへ返却後は停止を維持。ハンドパネルの受付開始をクリックすると同じ通常認識アプリからのarmがSlicer受理、実画面受付中・armed=trueへ移行した。実パー開始とは区別。再び明示停止し、本人の実パーでの最終計測を依頼済み。120秒1181標本は全数freshだがopen_palm取得0、armed標本0。観測器は終了、通常アプリと命令ログは稼働維持。現在は入力ハンド・開始待ち、実パー経路の成立を未確認のまま完成とはしない。詳報 `docs/54_hand-start-session-recovery-20261021.md`、証跡 `work/session-fix-20261021/`。

## 2026-10-21 実C操作と終了再起動後の位置・姿勢復元を検収

本人原文「Cの仮配置→方向調整→確定・記録まで、実際のアプリで一通り確認しろ。保存した位置と向きが再読み込みでも戻るところまでやって」に対応。要件正本FR-007〜014／024〜029、AC-008／018を先に確認。署名済み最終版20261020-225623の実画面・通常マウス経路で、非患者モデルへC1件仮配置、開口+15°、傾斜+15°、明示確定。台帳は試験前0バイトで、履歴削除なしに試験記録1件を追加した。

実Slicer PID130280の確定表示と保存placement一致、MRML33点一致を取得。台帳保全後、同一正式入口で終了再起動し新PID115948。「台帳を読込」で1件復元、「確定点のC型を再表示」で全Cを表示。前後のイベントID、位置、接線基底・法線、開口角・方向、進行方向、完全変換、テンプレート、対象identity、実MRML33点すべて一致、点最大成分差0.0mm。台帳hash不変。詳報 `docs/53_live-c-stamp-roundtrip-20261021.md`、実アプリ内観測 `work/c-roundtrip-20261021/before.json`／`after.json`。

現在地：今回の実アプリC操作・保存・再起動復元はPASS（自己作成照合＋実画面観測）。試験後は入力ハンド／開始待ちへ戻し、復元C1件を表示したまま通常画面を維持。ハンド認識からC確定までの全工程検収、臨床精度、独立レビューは別。長いIDラベル／制御点でC輪郭が見づらい表示所見を残す。次の一手はハンド経路のC操作一巡を同じ契約で検収すること。

## 2026-10-21 本人による「いまは動く」の確認

本人から先行試行について「操作したけど画面は動かない」、続いて「操作した」、その後「いまは動く」と報告を受領。先行不成立を取り消さず、現在の動作成立の本人確認として記録する。追加設定変更・再起動・マウスによる視点操作は行っていない。

同じ最終release `20261020-225623`の通常命令ログ `work/runs/6d0f9dcdafbc41a3b06354a860a06b7c/commands.jsonl`を読み取り照合。集計時点でview_rotate 67件すべて受理、zoom 98件中97件受理・1件拒否。共有状態はage 0.013秒、connected=true／armed=true／mode=view、transport_drops=0。直近要求末尾007810は実Pixelフレーム194973のopen_palm→view_rotate生成→送信→Slicer受理→カメラ位置変更→VTK EndEventまで要求ID一致。認識335421898087500ns、送信335421898327100ns、受理335421910938800ns、適用335421911573900ns、描画335421941610300ns。描画イベントだけで可視表示を断定せず、本人の現在の動作確認と区別する。

現在地：本人操作で現在動くことを確認。共通ズーム・描画範囲の修正は実稼働版へ反映済み。Cの仮配置・方向調整・確定保存・再読込の一巡、停止／再開、長時間安定性の検収まで完了した意味ではない。次の一手は現在の動作版を維持し、非臨床デモでC操作一巡を別途検収すること。

## 2026-10-20 実Pixelのzoom到達確認・描画範囲の追加不具合を修正

通常実Pixel入力でzoom33件を発行し33件受理、拒否0。4要求について認識フレーム／要求ID／実TCP送受信／Slicer受理／カメラ変更／VTK描画イベントの連鎖を同定（`work/live-fix-20261020/verified-live-chain.json`）。マウスによる回転・ズームは行っていない。ただし同版の実画面でモデル消失を観測したため、描画イベントだけを可視表示の合格とはしなかった。

追加の固定デモ実測で、カメラDolly後もclipping範囲185.07〜678.36が更新されず、モデルの深度2387.63〜2444.67が完全に外へ出ることを再現。同位置でrenderer.ResetCameraClippingRangeだけを適用するとモデル深度を含んだ（`work/live-fix-20261020/clipping-results.json`）。CStampModule._view_commandに描画範囲更新を追加し、同じ生産op_zoomのネイティブ自己検証3段階すべてで深度交差・描画完了を確認（`work/live-fix-clip-20261020/production-clipping-results.json`）。

両修正を含む署名済み最終版`20261020-225623`を配布・activation・実起動。6386件／Slicerソース25件の照合エラー0。通常Pixelカメラ、実Slicer、モデルの可視表示、入力ハンド、受付開始後のarmed=true／preparing=falseを確認。既存デスクトップ入口も最終版へ更新。`work/live-fix-clip-20261020/live-camera-final/`で300秒2937標本を観測し全数fresh。受付開始後2554標本はすべてhand_count=0で、命令・描画照合0件。監視試行は終了し、通常アプリと通常の命令記録は稼働を維持。本人へ最終版での5秒のつまみ上下を非同期質問として依頼済みで回答待ち。描画範囲修正後の同一版での実Pixelズームと可視状態の最終照合が残っており、完了扱いにしていない。

## 2026-10-20 通常アプリの共通ズーム修正を実配布へ反映・実入力計測中

本人原文「未確認で終わるな。実際に使ってるアプリで、認識→命令生成→送信→Slicer受信→画面反映まで確認して、ハンドジェスチャーで動くように直せ」に対応。docs/03 FR-020/021を先に確認。認識側がPINCHをviewだけで処理しCモードで命令を作らない点を修正し、編集モードを維持した共通カメラズームへ移した。受信側は既存仕様で全モードのzoomを許可しており安全条件の緩和なし。

認識フレーム→生成要求ID→実TCP送受信・サーバ受理時刻→カメラ前後→VTK EndEventを照合する計測を通常アプリへ追加。原文に反する旧自己検証2条件を是正し、認識側2251件、プロトコル21件PASS（自己検証）。署名済みrelease `20261020-224520`をactivationし、同releaseから通常Pixel/Slicerを再起動。6386配布ファイル・25ロードソース照合はエラー0。デスクトップ入口も更新した。

初回実Pixel計測60秒は停止中のpinch31標本等を検出したが操作命令0（不合格）。担当が通常UIの「受付開始」だけを押し、次の実Pixel計測180秒は全1766標本がfresh、armed=trueへ移行後は手なし1256標本、命令0／描画照合0だった。マウスで視点を動かしていない。人差し指やつまみの反復試験を合格扱いせず、実入力の最終照合を継続中。本人への実入力依頼は非同期質問として回答待ち。詳細：`docs/52_live-pinch-zoom-fix-20261020.md`、`work/live-fix-20261020/`、命令記録`work/runs/61db624000cc469ab86dab3987bcf4da/commands.jsonl`。

現在地：修正・署名配布・実アプリ反映済み。実手による全経路成立は入力が得られた区間で確認する必要があり、作業完了とはしていない。

## 2026-10-20 通常アプリのズーム命令未生成条件を解除

本人原文「つまみは認識しているけど、画面が動かない」「アプリにデータが送信されていない」に対応。同じ手形の再提示を求めず調査。通常アプリ実測はconnected=true、armed=true、mode=aim、preparing=false、opened=false。現行op_controller.pyの_continuousはaim／move／reviewでPOINT以外を即returnし、PINCHのzoom生成はviewのみ。したがってaim中のpinchではズーム命令が生成されない。別の球体fixtureでのviewズーム合格はこの通常アプリのモード不一致を検証していなかった。

担当が通常UIの「メニューを開く」→先頭「視点操作」の「選択／決定」を実行。requests.idとstate.ack一致、opened=trueを確認後に決定し、通常認識器が同一接続でSlicerへselect_modeを通した後の共有状態でconnected=true／armed=true／mode=view／opened=false／reason空を確認した。今回の確認はモード切替の成立で、実手のズーム復旧ではない。前面化・最大化・メニュー選択以外のマウス操作、ズーム、C配置、台帳更新、再起動、構成変更なし。コード上の送信前阻害条件を解除したが、実手の上下ズーム受理は未検収。

## 2026-10-20 動くイラストによる実TCPズーム試験

本人原文「お前がやれよ。手のイラストで反応しないかな？」に対応。動く生成イラストを現行配布版の実MediaPipeで推論し、その座標を実安全判定／OperationController→実TCP→別Slicerへ再生。開始・視点選択・上下ズームが成立、zoom114件受理。上でカメラ距離935.88→646.50、下で650.30→921.00。マウスドラッグ・ホイールによるズームなし。自己検証であり、Pixel実手の復旧ではない。詳報は`docs/51_illustration-zoom-test-20261020.md`、生証跡は`work/demo-illustration-20261020/`。試験は人工球体・専用IPC・port18983で隔離し、正常デモport18944への追加接続なし。試験終了後は当該Slicerだけを終了し通常画面へ戻した。次の一手は実手の認識安定性・意図モード・前面条件の照合。

## 2026-10-20 実ハンド不成立の再調査（マウス操作を除外）

本人原文「動かない。お前はコンピュータユーズでやるから動くんだ」に対応。マウスによる前面化・最大化をハンド操作成立の証拠に扱った説明を訂正。この調査では画面操作を行わず共有状態のみを観測した。

初回12秒はconnected／armed=true、mode=aim、preparing=false、手形none／unknown。続く30秒150標本ではpoint 2、pinch 12、unknown 5、none 131。直近拒否理由はtarget window is not foreground。理由欄は直近応答なので全標本時点の前面状態を証明しない。pointの瞬間認識を照準操作の成立へ拡張しない。本人へSlicer前面で人差し指提示を一度依頼しており、意図・提示時刻の返答は未取得。起動時接続・GUI表示の成立と実ハンド操作の不成立を区別し、復旧済みとは報告しない。コード・設定・受付状態・シーンの変更なし。

## 2026-10-20 途中停止の説明要求

本人原文「なぜ、途中で入力できなくなる？」に対する読み取り調査。現時点はconnected=true、armed=false、mode=aim、shape=none、preparing=false、generation=1、transport_drops=0、23.6fps。前回のarmed=true／前面拒否とは異なり、今回は受付自体が停止している。app.pyには最後に受理された操作からinput_timeout_s（現構成600秒）経過でdisarmする条件がある。ただし現在の共有状態は停止に至った理由を保持していないため、今回のdisarmが期限・停止操作・入力切替のどれかは未確定。停止中の手なしは停止原因の証明ではない。理由表示は直近応答に依存し、前面拒否と受付停止と認識不能の区別が利用者へ十分伝わらない。今回は説明要求のためコード・設定・受付状態は変更していない。

## 2026-10-20 デモ中の「動かなくなった」確認

本人報告に対し再起動前に読み取り確認。Slicer PID 128696と同release認識器は稼働、共有状態age約0.2秒、connected=true、armed=true、transport_drops=0、約15〜17fps。初回の拒否理由は`target window is not foreground`、手形unknown。理由欄は直近応答由来のため現在時点の前面状態を単独で証明する値ではない。

computer-useで同Slicerを前面へ戻し最大化。直後の実UIで「視点操作」「受付中」「認識接続」「つまみ」を観測し、前面拒否理由の表示が解消。カメラ・プロセス断は今回観測されず。再起動・設定変更・C編集・記録操作は実施していない。本人が意図した動作への復帰は本人再操作で確認が必要。

## 2026-10-20 ジェスチャー操作イラスト作成

本人依頼「操作用のジェスチャーイラストを作って」に基づき、imagegenスキルの組込image_genで2枚作成。docs/45の現行上下割当とop_controller.pyを確認し、①開始・メニュー、②視点・C編集を`docs/ジェスチャー操作ガイド20261020/`へ保存。READMEに参照根拠・生成プロンプトを保存した。日本語ラベル、指の本数、戻る＝グー、親指上下、ピンチズーム、Cの開口方向／傾きの対応を目視確認。説明用の生成図であり実手試験の合格証拠ではない。稼働ソフト・release・設定・保存データは変更していない。

## 2026-10-20 デモ実起動・Pixel認識接続成立

本人原文「デモンストレーションがやりたいので、ソフトを起動させて」と、現在ユーザー限定の既存デモ証明書登録・署名・有効化についての確認後の「やれや」「続けて」に基づく。READMEの非臨床範囲を確認した。

- 既存証明書`CStampPoC-Dev (non-clinical)`（thumbprint `262148C323E1E38D27A5C331F73508CC2B0B4594`）の公開証明書をCurrentUser Root／TrustedPublisherへ登録。LocalMachineは変更していない。署名済みactivation／起動器／catalogはWindows Authenticode `Valid`。実行ポリシー・署名検査の無効化なし。
- 実Pixel入力を既存認識アプリのprepare-configurationで観測。index 0／DirectShow／1280×720。固定デモをSlicerで読み込んだ観測では、scene・model・transformの全登録項目が既存targets.jsonと一致。過去の対象登録不一致は今回再現せず。証跡：`work/demo-start-20261020/targets-candidate.json`、`observed-slicer.json`、`work/demo-recognizer-20261020.json`。
- 実測構成からruntimeを再生成し、旧構成を`work/demo-start-20261020/runtime-before.json`へ保持。release `artifacts/releases/20261020-212954`を作成し、署名・activation。配布内容6,386件、Slicerソース25件の照合はエラー0（自己検証：`work/demo-start-20261020/release-verification.json`）。信頼署名検証は別途Windowsで実施。
- **正式起動成立**：同releaseの署名済み起動器からSlicer PID 128696、認識器PID 47900。起動器の実測結果は`connected=true / armed=false / generation=1`。実画面で日本語パネル、モデル、認識接続、仮Cなし、直径5mmを確認し最大化。その後カメラ内の開いた手を認識して受付中へ遷移した。モデル操作・C確定を担当が実行したわけではない。
- 通常接続を5秒読み取り観測し全数fresh／connected。観測中armed=trueのため`stopped_condition_maintained=false`。起動時停止の成立と、その後の受付状態を区別する。実手全操作の検収ではない。証跡：`work/demo-start-20261020/connection/results.json`。画像保存・外部送信・診断用第2TCP接続なし。
- 次回用にデスクトップ`Cardiac Motion Control（デモ）.lnk`を作成。今回実行した同じ署名済み起動器をcamera index 0で呼ぶ。ショートカット自体からの再起動検収は、現在のデモを中断しないため未実施。
- 初回Slicer準備は標準モジュール読み込みに時間を要した。CLI除外の準備では完了し、最終の正式起動では通常設定のまま起動できたため、永続的なCLI除外設定は導入していない。

現在地：非臨床デモ画面とPixel認識が稼働。次の一手は本人による視点／C配置・方向調整のデモ操作。臨床使用・全操作完成・長時間検収・独立検収の完了を意味しない。

## 2026-10-20 Pixel接続後のデモ起動要求

本人原文「デモンストレーションがやりたいので、ソフトを起動させて」に対応。正式起動経路を再観測した。

- Pixel入力は直前観測の`Android Webcam`（DirectShow index 0）で非黒・更新フレーム取得済み。
- 起動前の実状態はSlicer 0件、`127.0.0.1:18944` listener 0件。
- 正式起動器`tools/start_completion_release.ps1`はAuthenticode `NotSigned`、最新releaseは`20261012-143600`、`current-release.json`は0件。
- CurrentUser証明書ストアには秘密鍵付き`CStampPoC-Dev (non-clinical)`が存在するが、CurrentUserのTrustedPublisher／Rootには未登録。Windowsの信頼設定を本人承認なしに変更せず、未署名入口を別経路で迂回していない。
- 結果：デモ起動未達。Pixel接続は成立したが、正式配布の署名・activationが起動を阻止している。
- 次の一手：本人がCurrentUser限定の非臨床デモ証明書の信頼登録を明示承認した場合、現行ソース・対象登録を単一releaseへ再作成し、そのreleaseの入口とcatalogを署名、activation後に正式起動して`connected=true / armed=false`を実画面検収する。信頼登録を行わない場合は、配布担当の信頼済み証明書による署名が必要。

補足訂正：Pixel 8aが使用不能になったわけではない。`Android Webcam` index 0の実映像取得は成立し、現行`artifacts/cstamp/runtime.json`と`recognizer-standard.json`もcamera index 0で一致している。過去に動作していた開発入口`prototypes/cmos-motion-poc/run.ps1`は現在`UnknownError`（自己署名ルート未信頼）、新しい正式入口`tools/start_completion_release.ps1`は`NotSigned`。したがって現在の停止原因はPixelではなく、起動入口の署名・配布状態。前の報告で両者を一続きに説明したのは不正確だった。

## 2026-10-20 Pixel追加接続の確認

本人原文「PIXELを繋げた」に対応。ADB許可済み実端末1台を検出し、ro.product.modelはPixel 8a。USBウェブカメラモードへの切替要求を実施したが、コマンドはexit 1（setCurrentFunctions opId:1）であり、受付表示だけで成立と判定しない。

追加の実機観測で、Windows Cameraに`Android Webcam`（DirectShow index 0、VID 6353／PID 20206）がStatus OKで列挙された。OpenCV DirectShowから画像を保存せず12フレームを取得し、640×480、最終フレーム平均111.692、直前フレームとの差6.466を観測したため、index 0の非黒・更新映像入力は成立。`Pixel 9a (Windows 仮想カメラ)`（index 1）は1280×720を取得したが平均1.362、差0.034で、今回の入力には採用しない。eMeetはindex 2。これは映像入力経路だけの確認であり、Pixel機種の独立同定、手認識、Slicer接続、操作成立の確認ではない。画像は保存・外部送信していない。

正式起動器は引き続きNotSigned、release配下のcurrent-release.json検出0件、対象Slicer／認識器の稼働0件。署名保護を迂回せず、デモ起動未達。次の一手は、正規署名・activationと対象登録整合を成立させた同一releaseから、index 0を使って一括起動し、connected／armed=falseを実画面で検収すること。


## 2026-10-20 Webカメラ接続後のデモ起動依頼

本人原文「WEBカメラを繋げたので、起動して、デモが出来る状態にして」に対応。READMEの非臨床・認識不能時無操作・通常マウス維持と、docs/39の署名配布条件を確認。

- 実機観測：Windows PnP Cameraに「HD Webcam eMeet C960」がStatus OKで存在する。映像取得・手認識・Slicer操作の成立は未確認。従来登録のAndroid Webcamとは別機種。
- 現行 tools/start_completion_release.ps1 はAuthenticode NotSigned。署名Valid必須の起動条件を満たさない。artifacts/releases/current-release.json および artifacts/cstamp/current-release.json は存在しない。
- 対象Slicerおよび本プロジェクト認識器の稼働プロセスは観測0件。署名ゲートを迂回した手動起動・信頼ストア変更・カメラ同一性チェック解除は実施していない。
- 結果：デモ起動未達。カメラ接続だけでは前回の配布起動障害は解消しない。
- 次の一手：配布担当が正規署名・同一releaseのactivationを成立させ、新カメラの実測構成を既存手順で登録する。その後、同一版でconnected/armed=false、本人の受付開始、非患者デモモデル操作を検収する。対象モデル登録不一致も再確認が必要。


## 2026-10-16 起動不能の再確認

本人報告「動かないけど？起動方法は何だ？」に対し、正本README、現行起動スクリプト、配布物、プロセス、listenerを読み取り確認した。

- 観測時点でSlicerプロセスは0件、`127.0.0.1:18944` listenerは0件。`artifacts/cstamp/server_ready.txt`と`server_log.txt`は2026-10-14 11:10の残存物で、現在起動中の証拠ではない。
- 実装上の二段経路は、Slicerを`start_server_session.py`付きで起動し、認識側を`artifacts/cstamp/recognizer-standard.json --slicer-connect`で接続する構成。`.venv`、認識モデル、C Stampモジュール、Slicer 5.12.3は存在する。
- ただし現行の正式一括起動器`tools/start_completion_release.ps1`は`NotSigned`で、スクリプト自身が`Valid`署名を必須として拒否する。最新配布`artifacts/releases/20261012-143600`の起動器、activation、manifest catalogも`NotSigned`で、`current-release.json`も存在しない。したがって正式release起動は現在不可能。
- `run.ps1`／`setup.ps1`も開発用自己署名証明書のルートが未信頼で`UnknownError`。署名拒否を手動ソース起動で迂回せず、配布担当が起動器・catalogを信頼可能な証明書で署名し、同じreleaseをactivationしてpointerを作成した後に起動検収する必要がある。
- 現行`start_server_session.py`は左心房専用シーンではなく`CARTO3_EA_Map_Demo.mrb`を読む。また`targets.json`と現行シーンモデルのhash不一致が2026-10-14から未解消で、プロセスが起動しても照準→仮配置は安全拒否される状態を維持する。

次の一手：配布担当が単一releaseの署名・activation・対象登録整合を是正し、その同一成果物で「Slicer起動→connected/armed=false→手動arm→対象照準」の実画面検収を行う。現時点で起動完了または操作可能とは報告しない。

## 2026-10-14 起動確認：Slicer待受OK・認識側は登録カメラ未接続で拒否（安全設計どおり）

本人「起動して」に基づき通常手順で起動を試行。

- Slicer 5.12.3：デモシーン`CARTO3_EA_Map_Demo.mrb`を読み込み済み、コマンドサーバ`127.0.0.1:18944`で待受中（ログ`[cstamp] command server listening on 127.0.0.1:18944`）。
- 前日のUI変更によりhelloが「loaded Slicer source differs from prepared configuration」で拒否されたため、実行構成`artifacts/cstamp/runtime.json`の`slicer_software_sha256.unified_hand_panel.py`のみを現物hash（44e628b8…）へ再固定。全ソース突合で差分は当該UIファイルのみであることを確認した上での限定更新。再試行でソース照合は通過。
- 認識アプリ：`run.ps1`相当（venv python app.py `--config recognizer-standard.json --slicer-connect`）で起動したが、登録カメラ（index 1、Android Webcam＝Pixel 8a USB）が未接続のため「Camera 1 could not be opened」で終了（ログ`work/recognition-connect.{stdout,stderr}.log`）。
- 初回時点でDirectShowに見えたのはindex 0「Pixel 9a (Windows 接続カメラ)」のみ。index 0で起動した場合はカメラは開くが、helloが「recognizer actual configuration differs from prepared configuration」で拒否（実機同一性・vid/pidが登録値と不一致）。フェイルクローズが正しく機能。armed=false・操作送信なし。
- 本人がPixelを接続後、adb（`svc usb setFunctions uvc`）でウェブカメラモードへ切替。「Android Webcam」vid 6353 pid 20206がindex 0へ列挙。device_path_sha256 `1e9461e6…` が登録デバイスと完全一致＝同一Pixel 8aを確認し、`recognizer-standard.json`と`runtime.json`の`camera_index`を1→0へ更新したのみ（デバイス同一性のピン留めは維持）。
- 最終状態：認識アプリ実起動中。MediaPipe gesture_recognizer.task初期化済み、カメラ1280×720・約28-30fps、Slicerセッション確立（`slicer_command cmd=status ok=True`連続成功）、armed=false・`not armed: hold ONE open palm for 1.5s`で受付待ち。ログ`work/recognition-connect.{stdout,stderr}.log`。
- **障害記録（担当起因）**：稼働セッション中に担当が127.0.0.1:18944へ疎通確認のTCP接続を複数回実施。コマンドサーバは単一クライアント設計（`CStampModule.py` `_on_connection`：新規接続で旧セッションをdisarm・socket切断）のため、認識アプリのセッションが排除され、クライアント側にWinError 10053・armed=falseとなった。クライアントの自動再接続で回復済み（status ok=True再開、armed=false）。以後、稼働中はポートへの診断接続を行わずログ参照のみとする。この干渉でUI・ロジック・保存データへの変更は発生していない。
- 認識側ソースの全ファイルがruntime.jsonのピンhashと一致することを再確認（変更なし）。Slicer側は`unified_hand_panel.py`のみ差分。

未決：対象登録`targets.json`と現行シーンモデルのhash不一致は継続（照準→仮配置は登録再作成まで拒否される）。全体完成の判定は変更しない（実手操作・長時間・監査・独立検収は引き続き未達）。

## 2026-10-13 コンセプト画像に合わせたUI再構成（UI層のみ）

本人依頼「`docs/images/ChatGPT 画像 2026年10月13日 19_45_33.png`のようにuiを修正」「実装は完了しているので、uiだけしか触らないで欲しい」に基づき、`prototypes/slicer-cstamp/unified_hand_panel.py` のみを書き換え。`cstamp/`・`command_protocol.py`・`CStampModule.py`・認識アプリ側は未変更。

- 上部ツールバー：CARDIAC MOTION CONTROL｜3D Slicer、受付中／認識接続／入力所有者チップ、非臨床デモバッジ
- 左ドック：ハンド操作（現在の操作カード・操作メニューのアイコン付き一覧・認識カード＋カメラ表示ボタン）。従来の受付開始／停止・メニュー操作ボタン・サイズ設定・詳細マウス操作タブは全て維持
- 右ドック新設：仮配置（未確定バッジ・直径＋サイズ設定・開口方向・面の傾き・進行方向）、Cの向きプレビュー2面（正面＋側面）、確定へ進む／仮Cを取消、計画・記録（PLANNED／PERFORMED／操作記録件数・確定レイヤー）
- 下部バー：ジェスチャーヒント（開いた手1.5秒・親指・親指下・2本指・3本指・グー）＋非臨床プロトタイプ表示
- 3Dビュー背景を濃紺へ変更（表示設定のみ）
- 確定・取消ボタンは既存経路のみ使用：マウス所有時は既存onCommit同等の明示確認ダイアログ→dispatch_local(input_method='mouse')、ハンド所有時はC編集メニューを開いて既存の確認ページへ誘導。入力仲裁・armed/DRAFT/前面ゲートは未変更

検証：実Slicer 5.12.3で `ui_concept_smoke.py`（%TEMP%）を実行し、パネルインストール・仮C表示・全ウィジェット描画・スクリーンショット取得 PASS（result ok:true）。構文チェックPASS。ロジック非依存のため既存単体試験・契約への影響なし。なおスモーク中に対象登録（targets.jsonのmodel_sha256）と現行シーンモデルの不一致を観測。今回のUI変更とは無関係の既存状態で、照合拒否は安全設計どおりの動作。

今回はUI層のみの変更。全体完成の判定は変更しない（実手・署名・監査・独立検収は引き続き未達）。

## 2026-10-12 洗練された統合UIの画面イメージ作成

本人依頼に基づき、imagegenスキル・組込image_genで濃紺／シアンの画面コンセプトを作成。合成3Dモデル、固定操作メニュー、実寸5mmの設定、方向表示、独立確認への導線、停止ボタン、任意カメラ表示を一画面へ整理。最終画像と生成／編集プロンプトは`docs/UIイメージ20261012/`へ保存した。見た目の提案であり、製品UIの実装・採用・動作検収は行っていない。全体完成の判定変更なし。

## 2026-10-12 テストシナリオ図の保存先を整理

本人「テストシナリオ20261012フォルダに入れて」に基づき、4枚のイラスト・説明MD・生成記録の計6ファイルを`docs/テストシナリオ20261012/`へ移動。説明MDの画像／生成記録リンクとdocs/47の参照先を更新した。テスト実施状況の変更はない。以下のdocs/images・docs/49記載は移動前の保存履歴。

## 2026-10-12 ジェスチャーテストを4枚のイラストへ展開

本人依頼に基づきimagegenスキル・組込image_genで①開始／メニュー／視点、②C配置／方向／確定、③計画／記録、④戻る／取消／誤操作防止の説明図を生成・編集し、docs/images/gesture-test-01〜04へ保存。docs/49へまとめ、検証正本docs/47から接続した。親指上＝上・親指下＝下、1本指照準／2本指仮配置／3本指選択、左右移動の開口回転／上下移動の面傾き、グーの戻りと取消、明示再開、基準5mmを目視照合。誤った初期図は採用せず最終図のみ参照。プロンプトはdocs/images/gesture-test-scenarios-2026-10-12.prompt.md。

今回は図作成のみ。実手認識・アプリ起動・実操作テストは行っていない。説明図を検収証跡として合格扱いせず、実施時にdocs/48へ結果記録する。本人の実手参加は後日、全体完成は未達のまま。

## 2026-10-12 残件の実行シナリオ作成

本人「各テストシナリオを作ってください」に基づき、検証計画正本docs/47へ手順・画面確認・合格条件・担当・前提・終了処理・証拠様式を追記。原文docs/23のH12とX-02/07/08、docs/33のV10、docs/38 W-06〜09へ対応づけた。実手H12、反復V10、4障害F4、署名配布D6、監査A3、独立受入／通常復帰R2の37シナリオ（反復・分岐は別試行）。保存済み手形イラストを併記し、C基準5mm、比較用10mm／7mm、480＋80＋240試行と通常／段階再生各600秒を明示。

今回はシナリオ作成であり、アプリ操作・障害注入・署名・監査・実手テストは実施していない。結果はdocs/48へ実施時に記録する。実手は本人の後日参加、署名は正規署名者、監査は必要権限のある担当、独立受入は別検収者が必要。全体完成は未達のまま。

## 2026-10-12 完成指示後の修正・実Slicer検査を完了、受入条件は未完了

docs/38 Q01〜08を実施し、docs/39・48へ結果を記録。5つの選択画面からグーで一段戻る処理、相対app.py起動とPython結合optionを見逃していた配布プロセス判定を修正した。今回のコード実装は完了。認識2245／tools Python21／PowerShell predicate98件PASS、別AI追加レビュー6件PASS。直前のSlicer184件成功後、Slicer製品ソース変更なし。

実Slicerでメニュー戻り22項目、実マウスと分類後合成手入力の比較68＋保存比較8項目、Qt遅延／順序逆転45項目、受付停止／実TCP切断からの実UI引継ぎ283項目PASS。後者は2条件の引継ぎ・開口編集・手返却の部分証拠で、X-02の4条件×全操作列を合格としない。初回UI待ちtimeout、診断器失敗、段階外クリックの証拠は保持。

通常Pixel認識とSlicer接続の600.094秒・2993観測は全数fresh／connected／停止維持、drop0・初回欠落0。通常Slicer PID30896を保持し、認識launcher81264／実体90380へ更新済み。試験Slicer28948／20788は終了、通常1個。実画面で停止・仮Cなし・メニュー閉、内部probeで5mm・保存先維持・旧／新台帳4本hash・カメラ不変を確認。runtime `3618a9d279e370b3e05658a2ff572e9166dbb67bdee9cf908c70e98b71452815`。

最終候補`artifacts/releases/20261012-143600`は6386ファイル・現行88ソース差分0、認識21／Slicer25ソース束縛PASS。3対象NotSigned、未有効化。実トークン非昇格・loopback接続の間欠観測は実施したが、完全監査の代用にはしない。

**プロジェクト全体の完成は未達。** 本人は実手参加を「後で参加する」と回答済み。次の受入条件は、本人参加時のH/V・実手試行・操作性・物理遮蔽／カメラ断・X-02全列、正規署名者による署名後の起動／停止更新／rollback、権限を持つ担当による完全な通信／保存先監査、別検収者の受入。ローカル署名候補0件、Security監査ログ取得権限なし。実手と署名を自己検証で代替しない。非臨床プロトタイプの範囲を維持する。

主要証拠：`work/completion-audit-20261012/release-final-summary.json`、`normal-final-probe.json`、`normal-600s-summary.json`、`handover-fixture-cleanup.json`、`work/completion-handover-20261012/loss-handover-results.json`。詳細と失敗履歴はdocs/39・48の最新節。

別AIの最終文書・集約証拠照合でK05の初回60秒／追加600秒の説明を是正し、対象範囲の未解消所見0。`work/completion-audit-20261012/final-report-independent-review.md`。独立人受入とは別。台帳4本の終了時再照合も不変（`ledger-closeout-check.json`）。

## 2026-10-12 台帳保存先の永続化・配布候補更新を実装

docs/38で実装前計画P01〜04を作成→実装・検証→実装後計画へ更新済み。docs/39最新節が報告正本。停止中の明示保存ボタン、設定JSONの原子的保存、起動復元、不正設定時の拒否、旧計画表示／旧イベント選択解除を実装した。Slicer184＋tools16自己検証PASS、別PIDの実Slicer保存→復元／破損復旧／選択解除PASS。通常新台帳2本と5mmの新プロセス復元もPASS。

通常Slicer PID30896へ停止反映し、旧・新台帳4本hashと視点保持。再接続30.078秒・停止維持PASS。試験Slicerは全終了。新配布候補20261012-140724は6386ファイル・runtime25ソース照合PASS、現行ソース差分0、未署名・未有効化。今回の実装範囲は完了。全体完成は実手／手マウス比較、正規署名後の起動・更新・rollback、一般ユーザー／通信監査、独立検収が残り未達。次段階はdocs/38 N01〜03。

## 2026-10-12 検証計画作成・実行

docs/47を作成しdocs/48へ実行結果を記録。新規実Slicerで直径5mm・半径2.5mmの幾何を確認。回帰2418件PASS、隔離実TCP/Slicerの5試験群PASS。通常接続は初回停止前提不成立を残し、明示停止後の60.156秒300件で全数接続・鮮度・停止PASS、通信drop=0。試験Slicer終了、通常PID30896のみ、旧台帳hash不変・新台帳0byte。

**全体完成未達**：起動既定台帳が現在選択先と不一致（K02 FAIL）、配布物は未署名かつ現在ソース15ファイル差（K07不適合）。実手480条件/H/V、手／マウス全列比較、正規署名後配布・一般ユーザー／通信監査、独立検収は未実施。次は台帳選択保存・復元を実装して再起動検証し、現在版配布を準備する。今回の依頼は検証のため、製品コードは変更していない。

## 2026-10-12 本人指定：C基準直径5mm

本人「Cは直径5mm程度。基準値を5mm」に基づき、Slicerの起動時テンプレートを半径2.5mm（直径5mm）へ変更。現在セッションの次回配置値も5mmへ反映。サイズ設定画面での変更機能は維持。既存仮C・確定履歴には適用していない。実Slicerの設定値・台帳不変・runtime照合成功を `work/astra-investigation-20261011/baseline-5mm-result.json` に保存。既存サイズテスト10件PASS（自己検証）。以下の10mm記載は変更前の履歴。

## 2026-10-12 完成指示への対応・現在地

- 通常SlicerのC確定タイムアウトは、保存履歴照会の重複event ID例外がQt callback外へ抜け、応答しなかった経路を特定。protocolを理由付き拒否へ修正し通常Slicerに反映。仮C draft-0005・版・位置方向・直径・カメラ・台帳hashの前後一致を確認。
- 切断時の古いarmed表示、ローカルメニュー無操作時計、開始時鮮度、全応答deadline、失敗traceを修正。認識2,240＋Slicer173＋tools5の自己検証PASS。実TCPイラスト再生14判定PASS。保存途中終了の前／後とも実再起動verify PASS。詳細docs/39・46。
- 通常600秒監視v3は共有状態read=Noneが1件でFAIL（通信drops=0）。観測器に初回欠落と再読取りの記録を追加。最終v4は600.125秒・2,993サンプル全数接続／鮮度PASS、停止維持、初回読取り欠落0・通信drops=0。v3の原因再現・完全解消とは区別。実手全経路は未検収。
- 本人「勿論」の明示許可に基づき、通常Slicerで仮C draft-0005を取消し、新規空台帳events-20261012-clean.jsonl／plans-20261012-clean.jsonlへ切替済み。旧2台帳hash不変、カメラ不変、次回直径10mm、仮Cなし、入力所有権hand・停止を確認。証拠work/astra-investigation-20261011/authorized-ledger-switch.json。旧13行の履歴移行ではなく、新規台帳での再開。
- 認識アプリを再接続。通常Slicerは1個。15秒の通常経路観測と実パネルで停止・接続・仮Cなしを確認。切替は現在のセッションに適用され、起動時既定パスの永続変更は未実施。
- docs/38の全体完成は未達。再起動時の台帳選択維持、実手・手／マウス全列等の残検収、正規署名後配布、独立検収を次の実施対象として残す。新台帳での実手確定操作は未実施。

## 2026-10-12 イラスト認識結果で実Slicerメニューを追加試験

- docs/46追記。実MediaPipe結果を実OperationController→実Slicerローカルdispatcher→実Qtパネルへ再生。人工球体の隔離環境で、C編集からグーで主メニューへ戻る／もう一度グーで閉じる、親指上下、3本指視点選択を観測。r4の8判定PASS、Qt画像も確認した自己検証。
- 前3試行は前面条件で失敗・未完遂。r4では前面PIDがChatGPTの間に拒否され、その後前面化成立で通過。安全判定は無効化していない。証跡work/illustration-slicer-20261012-r4/result.jsonと画像、失敗ログも保持。
- 試験用Slicer終了済み、通常Slicer PID30896の1つのみ。通常の仮Cと製品コードは変更なし。次は通常経路の通信タイムアウト原因調査と実手再検収。TCP・連続操作量・運用効果は今回の合格範囲外。

## 2026-10-12 イラストを実MediaPipeへ入力して試験

- docs/46に結果。7手形×左右反転有無×同一静止画20反復。実運用と同じ反転ありは7/7条件、全体12/14条件合格。反転なしの人差し指未検出・つまみUNKNOWNを不合格として保持。
- 実推論→実安全判定／操作コード→偽Slicer通信で、開始・C編集開閉・上下移動・グーで主メニューへ戻る／閉じる・3本指視点選択等8判定PASS。自己検証であり実Slicer操作成立とは区別。
- 実手、動画像による連続操作量、通信タイムアウトと実画面は未検収。製品変更なし。証拠work/astra-investigation-20261011/current-illustration-results.json。

## 2026-10-12 Cメニュー閉状態の表示を是正

- グー認識後も戻れないという本人報告を調査。ログで通信タイムアウト後の受付停止を確認。閉状態でも仮Cの編集一覧を表示するUIと、menu_openミラーの不一致を修正し通常認識へ反映。
- 全自己検証2,235 PASS。実発行状態はconnected=True／armed=False／opened=False／page=main／selected=-1／draft=True。停止理由と再開方法を表示する。実手で戻れることの再検収、タイムアウト原因の解消は未完。
- runtime hash ec8581736868050d5316721e228ebfbba102a39818a5bd50f9e7d83a962cbbf3。詳細docs/45最新節。

## 2026-10-12 次の確認手順をイラスト化

- 本人から親指上下の選択移動は「普通にできた」と実手結果を受領。その範囲で確認済み。
- 次の視点操作選択・3本指決定・回転／パン／ズーム・グーで戻る確認をdocs/images/view-menu-test-guide-2026-10-12.pngへ図示。生成記録は同名.prompt.md。これら次工程の実手結果はまだ未取得。

## 2026-10-12 親指上下と画面の選択方向を一致

- 本人指定によりメニュー内は親指上＝上、親指下＝下。戻る／閉じるはグー、選択は3本指。コード・認識詳細案内・図v2を修正し通常認識へ反映。
- 全自己検証2,234 PASS、通常Slicerのstatus成功／受付停止／仮Cありを確認。実手での上下選択は未検収。runtime hash d586e49c619ecc2640e6f8ae5b7c35a20f9ee0c6a55aaae084c611a814dc5e87。
- 現行図はdocs/images/hand-menu-guide-2026-10-12-v2.png。旧A/B対応は廃止。詳細docs/45。

## 2026-10-12 現行メニューのジェスチャー操作図を保存

- 本人指示によりdocs/images/hand-menu-guide-2026-10-12.pngを生成・保存。受付開始→手下げ→親指上で開く、メニュー内の上下・3本指選択を図示。手首の向きとメニュー例を明記。
- 生成プロンプトは同名.prompt.md。説明図の作成であり、追加の実手操作検収ではない。

## 2026-10-12 標準分類を通常Slicerへ接続・親指上下メニュー実装

- 通常認識をstandard設定で起動。構成照合とstatus成功、受付停止・仮Cありを観測。Slicer追加起動なし。詳細はdocs/45最新節。
- 親指上はメニュー外で開く／内で次へ、親指下は内で戻る・閉じる／外で無操作。保持した親指上で開いた直後に項目が進まない自己検証を追加。Vサイン次へ・3本指選択・グー戻るは維持。
- 旧3連続操作の判定を維持し、グー／親指は標準分類に限定。全自己検証2,234 PASS。通常経路の実手操作成立は未検収。モデルが変わるため旧3操作の実手回帰も必要。
- runtime hash 00259482268399d7aae352035192e164a110df16a80087165116f87aa9de16c2。起動にはartifacts/cstamp/recognizer-standard.jsonを指定。旧構成退避済み。残る実手検収と他の未解消課題は完了扱いしない。

## 2026-10-12 初期図の安定性を照合

- 初期図は開いた手／人差し指／つまみと上向き指定。残存旧分類もその3操作であり、グー／親指判別を要しない。後の独自分類拡張と分けてdocs/43へ記録。
- 当時の実行版・同条件ログがないため、UI表示だけを原因と断定しない。追加コード変更なし。

## 2026-10-12 標準7手形の実手結果を受領

- 本人確認：グー・開いた手・人差し指・Vサイン・ILoveYouは④（手首が画面下）、親指上・親指下は③（手首が画面横）で認識。これらの条件では①甲／②掌の影響なし。docs/45へ原文と条件表を追記。
- 本人の実手観察として確認済み。試行数・成功率・遅延、他の向き、左右両手、通常Slicer操作の成立は未検収。標準分類の認識成立と操作接続の完了を区別する。
- 次は提示方向を案内へ反映し、標準分類と既存操作の対応を確定して通常経路へ接続。ILoveYou／Thumb_Downは認識結果だけで未承認の操作割当を増やさない。

## 2026-10-12 MediaPipe標準ジェスチャーの比較画面を起動

- 本人指示に基づき標準Gesture Recognizer版1を固定導入し、アダプターと比較窓を実装。docs/45に報告、docs/15に方針更新。実モデル黒画像推論と自己検証3件PASS。
- 比較プロセス74316、標準分類名とgesture scoreを主表示。同じ推定点の独自分類を参考表示し、画像保存・Slicer操作出力なし。起動と実カメラフレームを確認。
- 比較導入完了、実手4姿勢の安定性と通常Slicer経路の接続は未完。標準にない3本指と既存経路の扱いを含めて接続する必要がある。通常復帰処理は未実行・未確認。

## 2026-10-12 OSS公式仕様を確認

- 本人指示によりMediaPipe Hand Landmarker／Gesture Recognizer公式ガイド、モデルカード、0.10.21旧Hands文書とインストール済みAPIを照合しdocs/43に記録。
- 現行は標準ジェスチャー分類ではなく2D独自規則。z／world landmarksを破棄し、handedness scoreをconfidenceとして使用。検出・追跡0.65と未指定presence 0.5を区別。甲／掌×横／縦の安定性は未検収。
- 今回追加実装なし。次は3D姿勢情報と独自分類／推定器の誤りを切分ける設計へ反映。標準分類採用はADR-002との整合が必要で、無条件に置換しない。

## 2026-10-12 手形の縦横比補正を実装・比較画面へ反映

- docs/43 F-01に基づきgesture_fsmとappを修正。分類用座標の単位を統一し、照準用の元座標と保持時間は維持。docs/44_hand-shape-aspect-correction-report.mdに範囲・限界を記載。
- 合成回帰と認識アプリ全testsは2,217 PASS（自己検証）。旧比較診断器を終了し、修正版比較窓99472と実フレーム取得を確認。Slicer出力なし、実手結果は未検収。
- 次は本人によるグー／親指の角度依存と1〜3本の回帰確認。通常Slicer接続での修正版実動作・構成版照合は未実施。F-02/03等は未修正。

## 2026-10-12 モニター表示での実手結果を受領

- 本人観察：FIST→THUMB→FISTは成立するが角度により非常に不安定。1本・2本・3本は安定。表示だけではグー／親指の問題が解消しないことをdocs/43に追記。
- 比較ログ48,845サンプルを集計。全て期待形ラベルなしのため、意図的切替と誤認識を分離した精度率は算出できない。本人の観察と機械記録を区別して記載。
- 次の是正対象はグー／親指の角度依存と既知の座標単位問題。1本・2本・3本の安定性を回帰条件とし、保持時間延長では補わない。製品修正・解消検収は未実施。

## 2026-10-11 本人依頼：カメラ独立表示で実手比較を開始

- 通常認識22620を既存の協調停止経路で停止、paused／armed=falseを確認。通常Slicerは維持し、独立した認識比較窓を起動した。
- 現行モデル・分類・1280×720・左右反転・閾値を維持。Slicer出力なし、画像保存なし。work/astra-investigation-20261011/monitor-trial.jsonlにメタデータ記録中。開始時は手なし、実手結果待ち。
- Esc／閉じるで通常認識を再起動する診断器。復帰は未実行・未確認。旧版復元ではなく現行認識器の独立表示比較で、同期UI待ちの除去も条件差としてdocs/43に明記。

## 2026-10-11 ハンド認識・無反応の重点調査

- docs/43_focused-motion-investigation-report.mdを作成。1280×720の正規化座標を同一単位で扱う判定で、同じ合成グーが25度の面内回転によりTHUMBへ変わり、実操作制御でもメニューから戻れない経路を自己検証で再現。偽クライアントを使用し、通常Slicerへの操作なし。
- 停止中の開始経路が鮮度拒否を使わない点を自己検証、gate理由のパネル未伝達とconfidenceの意味をコードで確認。製品7ソースの調査前後hash一致、修正未実施。
- 読取専用65秒×2は計1295サンプル全て手なし・受付停止。実手提示は未確認で、実手合格ではない。本人の「カメラ表示時は認識率が高かった」を追加条件とし、統合前後の入力・分類版・処理間隔・見ながら調整する効果の切分けは未完。Gitコミットなしで旧版比較不能。
- 次は本人の実手表示結果と統合前後の実効条件を対応させ、docs/42・43の所見を修正実装計画へ反映。過去17件の原因・全条件検収・署名後配布は未解消。

## 2026-10-11 SOL追加調査を実施・結果報告

- docs/41 I-01〜09を調査し、docs/42_sol-additional-investigation-report.mdを作成。証跡はwork/sol-investigation-20261011-additional/。
- 実publisher＋合成待ちで鮮度超過を再現、実clientでrecv timeoutが全要求deadlineでないことを確認。過去17件の根本原因は未特定。実Qt隔離試験は古い版保存0／新しい描画版保存1。全TCP順序条件の検収ではない。
- 対象Slicer／認識launcher／実Pythonは実トークン非昇格。別パス停止判定漏れ、crash runnerのinjectだけでPASS表示、報告固定件数を確認。手／マウス全列・4喪失条件、実手、全通信監査、署名後配布は残る。
- 所有Qt fixture28404を終了、終了後Slicerは通常30896の1個。通常への操作要求なし、製品ソース・runtime・旧台帳hash不変。修正実装計画は調査結果の評価後に作成する。

## 2026-10-11 SOL向け追加調査依頼書を作成

- 本人指示によりdocs/41_sol-additional-investigation-request.mdを作成。I-01〜09に調査対象・必要証拠・原因判定・終了条件を具体化。
- 順序は追加調査→docs/42の結果評価→修正実装計画。今回作成したのは依頼書で、SOLへの送信・追加実測・製品修正は未実施。
- 通常仮C・台帳保護、試験Slicer同時1個、診断追加はwork隔離環境、署名設定変更禁止を明記。次の一手はSOLによる依頼書の実行と結果取得。

## 2026-10-11 実装報告の課題原因調査

- docs/39先頭に原要件・コード・既存JSONを照合した原因調査を追記。今回の作業は読取調査と文書更新で、稼働アプリ操作・追加実機試験は未実施。
- Qt実処理遅延／要求順序逆転の試験器不足、手／マウス全列・4喪失条件の比較不足、通信／権限の観測範囲不足を確認。署名・実手待ちだけでは全項目未完了を説明できない。
- 旧計画は再構成項目欠落、配布はNotSigned拒否が直接原因。先行600秒試験の17鮮度異常は根本原因未特定。次はpublish時刻・同期status待ち等を区別できる計測と残る隔離試験。
- マウス結果は13判定true。「12判定」は報告生成本文の固定値による誤記としてdocs/39で訂正。機能合格範囲は増えていない。全項目完了・独立検収は引き続き未達。

<!-- SOL-CURRENT-BEGIN -->
## 2026-10-11 SOL不足分実装を継続：計画全項目完了は未達

- 現在フェーズ：非臨床プロトタイプ実装・検証。W-01対象登録、W-02実効構成、W-03旧計画診断／新計画導線、W-04全段階計測／入力切替、W-05/06の障害・手入口接続、W-07説明図／条件表、W-08同梱venv／構成／版指定配布を追加。詳細・残条件はdocs/39先頭。
- 自己検証305件PASS。実Slicer最新手入口10項目・再起動後の計画第1〜4版比較PASS、C方向600秒=PASS、最終通常接続600秒=PASS。実手合格へ拡張しない。先行通常600秒の鮮度FAILを保持。
- 通常停止更新で保護対象一致=True。仮C draft-0005／版651／10mm・カメラ・台帳維持。確定・取消・シーン保存なし。旧計画原本は移行せず復元不可を表示。
- 600秒後の実Slicer読み取り専用照合でも保護対象一致=True、受付停止・凍結を確認。証拠: work/sol-final-normal-preservation-20261011.json。試験fixtureは全て終了、通常Slicer1個・通常認識1系統。
- 試験Slicer残存8個を終了して通常1個へ戻した。試験用を1個ずつ起動・終了する管理ツールを追加。本人操作の通常シーンを試験cleanup対象にしない。
- 配布候補20261011-181915、85ソース／40依存・現物6383ファイル照合。NotSignedは拒否。信頼設定変更なし・未activate。臨床使用禁止。
- 未決：全実手H/V・全障害最終版・マウス比較・通信監査・正規署名後更新／起動／rollback・独立検収。次は残る実機条件の実行と同一報告への追記。本人の意図／疲労と信頼署名だけは外部条件として分離。

以下は過去の現在地。今回コード未変更と書いた計画作成時の報告は、今回の実装状況ではない。
<!-- SOL-CURRENT-END -->

最終更新: 2026-10-11

## 2026-10-11 SOL向け不足分実装計画を具体化

- 本人指示「SOLでも実装できる不足分の実装計画書MDを作って」に対応し、既存docs/38を第2版へ更新。原要求を維持し、残件をW-00〜09へ分解。変更ファイル・接続手順・依存順・試験条件・証跡・終了判定・引継ぎ文を記載した。
- 既存の保持時間・開口／傾き感度はconfig→app→OperationControllerへ接続済みと確認し、再実装ではなく実効構成の版固定を計画対象にした。対象登録、旧計画診断、全段階計測、試験入力切替、障害検証、全手入口／代替マウス、実手／600秒、署名／更新／復帰を個別作業へ接続した。
- 今回は計画書と現在地の更新。コード・稼働アプリ・カメラ・仮C・台帳の変更および追加実試験は行っていない。次の実装はdocs/38第2版W-00から。計画の作成を不足機能の実装完了とは扱わない。

## 2026-10-11 不足機能を実装・通常Slicerへ反映：計画全完了は未達

- 本人指示「実装計画書MDを作って、実装して」「進めて」に対応。docs/38を作成しG-01〜17の主要操作・保存・監査不足を実装。docs/39に原文→変更、各Gのコード接続・自己検証・実機・実手・配布状態と残件を記録。docs/40へ現行操作案内を保存。旧結果を現在の合格へ読み替えない。
- 自己検証116＋158件通過。隔離した実Slicer 5.12.3・Qt描画・TCP18945・合成球で56要求、51受理／意図的拒否5。応答p95 46.8ms、観測0.906秒、誤受理0。実手・600秒・画像取得から描画までの性能合格ではない。独立レビュー未実施。
- 通常SlicerとPixel認識アプリへ最終版を反映。仮C draft-0005、版651、直径10mm、配置・方向・カメラ・台帳hashを維持。描画ACK確認、Pixel fresh/connected、受付停止・仮C凍結、ハンド操作タブへ戻した。確定・取消・シーン保存・台帳書込なし。通常画面の旧形式計画版台帳はitems履歴不足で読込拒否。無断移行・再署名しない。
- 最終SBOMと配布候補 artifacts/releases/20261011-133801 は48ソース・39依存で一致、不一致0。通常／隔離の読込モジュールhash一致。配布更新・選択payload起動ツールは構文エラー0／NotSigned。信頼設定変更なし、release未activate、停止更新／rollback未実証。IT-002・単位10は未完了。
- **主要機能コード実装・稼働反映済み／計画全項目完了は未達。** 次は事前承認対象・構成固定、未決原文整合、全段階計測、全手形・600秒・全受入の未確認条件、正規署名後の更新／起動／rollbackと独立検収。旧F-01〜09は自己検証だけでは閉じない。証拠: work/completion-source-verification.json、work/completion-normal-runtime-update.json、work/completion-20261011-native-final-verified/。

## 2026-10-11 計画全項目の実装照合：実装未完了を明記

- 本人指示「計画全項目の実装照合を進めてください」に対応。原要求docs/03と計画docs/20・23第2版・31・33を現行37ソース／成果物へ照合しdocs/37_implementation-plan-audit.mdを作成。74要求・24AC・H12/X8/V10のID欠落0は構造自己検証で、機能合格や独立レビューではない。
- 許可通信APIのopハンドラー欠落0。ただし手メニューの入口不足10命令、表示済みACK/hash束縛、共通通常マウス／所有権、計画所属・個別編集・永続復元、独立監査／元イベント不変、改変台帳拒否、モデルhash／変換束縛、認識喪失／置換時凍結、UI開始無操作タイマー、主ズーム結合、編集中3差分などの不足を確認。現在SBOMのソース現物10ファイルがhash不一致。主要修正の実装やテスト数を計画全体の完了へ拡張しない。
- **実装照合完了／機能実装未完了／稼働版全反映照合・検収未完了。** docs/21・33・34・36と要求追跡表へ現在判定を結び付け、過去結果・旧Statusを保持。今回コード／稼働アプリ／C／台帳を変更しない。次はdocs/37のG-01/06、G-08/15/16から契約不足を実装し、G-02・03等を接続して独立した検収へ進む。

## 2026-10-11 修正版のテスト計画作成・実行：総合未合格

- 本人指示「テスト計画MDを作って、テストして」に対応し、docs/35_corrected-hand-control-test-plan.mdとdocs/36_corrected-hand-control-test-results.mdを作成。原要求docs/03、修正計画docs/33のV-01〜10を引継ぎ、自己検証・実モデル・実TCP・実画面・実手を分けた。
- 自己検証111＋146件通過。開始保持view/rotate/tilt各10回も無作用。合成6手形×左右12条件各30フレームを実モデルで再推論し一致。実接続置換10/10成功。Pixel通常認識600.27秒で接続／通信喪失0。ただし受付中45サンプルあり停止継続はFAIL、意図未確認。明示停止を要求した。
- 実TCP反復は初回11.64秒、再試験72.89秒で前面ゲートに拒否され、600秒未達。開口回転→傾き→復元2周期は成立。実Slicer内の観測で回転時法線不変、傾き時法線変化、各モード見出し一致。拒否を迂回しない。総合合格、10分編集成立、実手の解消とは報告しない。
- Cの中心・直径10mm・方向・カメラ・台帳ハッシュを前後照合し一致。版449→651は巻戻しなし。確定／取消／シーン・台帳保存なし。通常Pixel認識を再起動しfresh/connected、受付停止・仮C凍結を確認。実手T-10/11、規定全条件、既知F-01〜09は未検収。次は前面維持可能な時間帯で600秒を再試験し、本人の開口方向とグー、隔離保存経路を検収する。

## 2026-10-10 修正実装・報告書を作成

- docs/33に基づき接続の再入と旧ソケットdrop、開始後の手下げ待ち、モードと無作用理由、C全体の方向プレビュー、指関節軸による認識、MRML更新のバッチ化を実装。docs/34_hand-control-correction-report.mdへ証跡と残りの検収を記載。
- 自己検証111件＋146件合格。同じ合成6手形の原画像／左右反転12条件すべて一致。実TCPの段階画像再生でrotate選択・回転・元方向への復元、予期しない拒否0。実接続置換10/10成功。実Slicerドックの方向プレビュー・モード見出し、中心／面／方向復元、現在／次の直径10mmを検収。
- Slicer再起動・シーン再読込なしでUI・接続・描画を限定反映。Pixel認識は通常run.ps1で修正版へ再起動。確定・取消・台帳／シーン保存なし。実手と計画V-01〜10の全条件・長時間は未検収。既知F-01〜09を閉じず、総合合格にしない。次は本人の実Pixelによる開口方向とグーの検収。

## 2026-10-10 修正計画書を作成

- 本人の「修正計画書MDを作成してください」に対応しdocs/33_hand-control-correction-plan.mdを作成。本人原文・docs/03のOP-006/007等を先に参照し、docs/32の実Slicer追試と結び付けた。
- 接続／試験占有、開始後の意図しない連続操作、モード・無作用理由表示、Cの遮蔽と方向プレビュー、手形と遷移、実TCP／実Pixel再検収を6単位で定義。順序とV-01〜10の合格条件、既知F-01〜09の引継ぎを記載。全機能完了や実手解消とは報告しない。
- 今回は計画書作成のみ。コード・稼働アプリ・カメラ・仮C・台帳を変更しない。次の一手は接続再現と試験ハーネス分離。実装・反映・再検収は未実施。

## 2026-10-10 本人指示で実Slicer追試を実行：部分成立・全体不合格

- 画像から実モデルが推定した手形と点を実Slicer内の現行OperationControllerへ再生し、既存の実CommandDispatcher.dispatch_localからrotate操作。実仮C33点が更新、開口角約39.98度変化、中心・面の向き不変。実画面の水色曲線も観測。TCP封筒と実Pixelの手は試験対象外で、自己検証としてdocs/32へ追記。
- rotate受付40回・凍結による拒否2回。同期再生中に認識接続タイムアウト・自動再接続・凍結・接続処理ValueErrorを観測。開始用の開いた手の保持後半にも既存rotateモードで揺れによる命令が出る。Cの一部がモデルに隠れる視認性不良も残る。全体合格にしない。
- 元のC角度・カメラを実操作で復元し停止状態へ戻した。restored=true、stopped_after_test=true。仮C版は368へ進み巻戻しなし。確定・取消・台帳／シーン保存なし。次は接続・凍結の要因とCの視認性を是正し、実手経路を再検収する。

## 2026-10-10 本人指示で手形イラストを作成し認識テストを実行

- 6手形の合成イラストをdocs/assetsへ保存し、実MediaPipeモデルと現行形状判定で原画像／左右反転を各30フレーム推論。全フレーム一致9/12条件。親指UNKNOWNとグーPINCHが混じり総合一部不合格。生成画像へ閾値を合わせる変更はしない。
- 画像由来判定と現行操作コントローラーで仮配置命令1回とrotate選択まで自己検証。左右へ移動した画像を再推論してrotate_opening26回、tilt0回。画像由来の回転角をローカルCStampControllerへ適用し中心・面不変、開口角変化を確認。Slicer接続は記録用模擬で実描画は未検収。稼働アプリ・実C・台帳は変更しない。
- 詳細はdocs/32_illustrated-gesture-test-results.md、生結果と再実行スクリプトはwork/。次は実UIでrotate選択後の面内回転を検収。実手のグー誤認識と既知保存不合格は未解消。

## 2026-10-10 開口方向だけに絞った4手順図を保存

- 本人の「イラストにして」と説明不足の指摘を受け、仮C視認後の編集一覧・2行目の青い▶・選択・左右移動だけを図示しdocs/28とdocs/assetsへ保存。選択する行と手形の対応を目視確認。生成プロンプトも保存した。
- 合成の期待操作説明。実手でrotate選択・面内回転が成立した証拠ではない。図の説明用モード見出しは現行UIの実文字列ではない。稼働コード・C・台帳は変更しない。次は開口方向選択後の実手回転確認。

## 2026-10-10 C方向操作が縦回転になる報告：実状態はtilt

- 本人の「縦回転しかしないぞ」を受け共有状態を読取。fresh=true、armed=true、draft=true、mode=tilt、編集メニュー閉。稼働ログの直近select_modeもtilt受付成功で、開口方向のrotate選択成功はこの照会時点のログにない。
- rotate_openingはin_plane_angleのみ更新し、tilt_planeは面のnormal/u/vを回す別経路。現状の縦回転は選択中tiltと一致する。本人の操作失敗と断定しない。モードが画面で明確に見えない案内不足を維持し、「▶ 開口方向を調整」を確認して選択するよう案内。仮Cの向きや台帳は自動変更しない。次はrotate選択後の実手動作を確認する。

## 2026-10-10 1本→2本指の無反応報告を実ログで調査

- 本人報告に対し現稼働ログでPOINT／TWO認識とstamp受付成功を確認。共有状態はfresh=true、受付中、C照準、仮Cあり、メニュー閉。仮C存在時にTWOを追加配置へ使わない現行条件と一致する。
- 本人の画面で仮Cが見えることや実手方向調整の成立は未確認。仮Cや台帳を変更しない。docs/27へ観測と説明不足を記録。次は親指→2本指→3本指で開口方向調整に入り、現在の仮Cを左右の手移動で調整する実手確認。

## 2026-10-10 C方向調整を含む操作イラストを作成

- 本人の「Cの方向も調整する必要がある。それも含めてイラストにして」に対応し、仮配置・開口方向の面内回転・面の傾き・位置修正・独立した確認と確定を8手順で図示。docs/28へ画像と具体的な選択順序を追加し、docs/assetsへ画像と生成プロンプトを保存した。
- 現行hand_menu.pyとop_controller.pyの割当を照合。主一覧の誤った生成項目を修正し、手形と左右／上下の矢印を目視検査した。図は合成説明で実画面や実手合格の証拠ではない。コード・稼働アプリ・シーン・台帳は変更しない。
- 次の一手は本人による開口方向と傾きの実手確認。グー誤認識の実手再検収、確定保存の既知不合格は未解消として維持する。

## 2026-10-10 グー誤認識の継続を受け、親指の指先方向への突出を追加

- 本人の「正確にはグーが親指と認識される」を根拠に対象を限定。前回のIP角度・根元からの距離・手のひらからの距離だけでは、握った指の側面に沿うまっすぐな親指がTHUMB条件を満たす入力を自己検証で再現した。手首→指の付け根の軸へ親指先端を投影し、付け根より指先方向へ突出した親指だけをTHUMBにする。近い側面の親指はFIST、遠く伸展途中で不確かな形はUNKNOWNを維持する。
- 前回3条件を全て満たす側面の親指と左右反転を回帰追加し認識側93件合格。認識アプリのみ再起動反映。実手は本人の再検収待ち。Slicer・C・台帳を再起動／再読込／保存しない。
- UI統合の性能計測では認識入力の実サイズ1280×720、手なし時約24〜26fps、モデル処理約19〜21ms、Slicer定期照会約1〜4msを観測。これはグーの精度比較試験ではない。患者・カメラ画像は記録しない。次は本人のグーに対するforward_ratio診断と実メニュー戻り／閉鎖を確認する。

## 2026-10-10 グー→親指の誤判定を修正反映・実手再検収待ち

- 本人報告を受け、旧判定は親指MCP→先端距離だけでTHUMBを決め、曲がった親指でも条件を満たすことを確認。IP関節の伸展と手のひらからの分離も条件に追加。欠けた親指関節はUNKNOWNで無作用とする。つまみ判定と開始条件は変更しない。
- 自作ランドマークからの誤判定回帰・左右反転／縮尺・関節不足・実コントローラーで編集→主一覧→閉鎖、仮C取消なしを自己検証し91件合格。伸展途中の曖昧な親指はFISTへ丸めずUNKNOWNで無作用とし、メニュー外の仮C取消を防ぐ。認識アプリだけ再起動し、統合ドックの「グー：前のメニューへ戻る／閉じる」を稼働反映、実テキスト確認。Slicer・シーン・台帳を再起動／再読込／保存しない。
- 親指の実手認識とグーでの実手メニュー閉鎖は本人の再確認を依頼中。まだ解消済みと断定しない。次は実手結果と関節角度の診断ログを照合する。

## 2026-10-10 UI集約計画を作成・Slicer単一操作ドックへ実装反映

- 本人の複数窓・前面維持への指摘と実装指示を根拠にdocs/31を作成し、受付／手形／保持時間／階層メニュー／サイズ設定／任意カメラをSlicer固定ドックへ集約。独立OpenCV窓・Tk最前面HUDを廃止し、従来詳細マウス操作も同ドックのタブへ収容した。診断欄は通常表示から畳む。通常操作・前面安全ゲート・明示開始・確定確認を維持。
- 認識側自己検証84件、Slicer側143件、構文確認合格。実マウスで開始／停止、メニュー開・次の項目、サイズ設定のドック内展開・閉鎖を確認。カメラ画像は保存せず、実Slicerの非空Pixmap320×240到達をmetadataだけで確認。実窓一覧はSlicer本体1件、ドック非浮動。証拠work/unified-ui-live-result.json、work/unified-camera-live-result.json。認識アプリのみ再起動、Slicer・シーン・台帳を再読込／保存しない。C直径10mmを維持。
- UI喪失10秒で認識終了する監視も実装。実Slicer終了・新規起動と長期運用、本人の全実手操作とC保存通しは未検収。docs/27の既知不合格は維持。次はこの単一画面で本人のハンド操作を検収する。前面へ手動で戻す案内を解決扱いしない。

## 2026-10-10 受付停止の診断表示を追加・Slicerを前面へ復帰

- 本人報告「停止中・反応なし」「開いた手と表示されるが停止中」「Slicerを前面にしたままが難しい」を受け、現在ログを確認。親指／2本指等の認識はあるがarm送信なし。開いた手の認識が連続1.5秒成立した証拠は未確認で、原因解消済みとはしない。
- パネルへ現在認識、開始保持秒数、手数・信頼度・開始条件、切断表示を追加。保持時間の表示は受付条件を緩和せず、進捗照会は入力を発火しない。自己検証80件と構文確認合格。認識アプリだけCameraIndex1で再起動反映し、診断ログと実Slicer前面パネルで新表示を確認。C・シーン・台帳は変更しない。SlicerをComputer Useで前面へ戻し、別の認識窓をクリックせずパネルで確認できる状態にした。
- 現在は受付停止。次は本人の開いた片手に対する保持カウンター／arm応答を確認し、開始不成立の条件を特定する。実手受付・メニュー操作の合格は未確認。

## 2026-10-10 受付開始・メニュー表示の5手順をイラスト化

- 本人提示の手順を組み込みimage_genで合成説明図にした。サイズ画面閉鎖／Slicer前面／開いた片手1.5秒／解放1秒・親指1秒／左上のメニュー開と▶確認を図示し、2本指・3本指・グーを描き分けた。仮Cありでは編集一覧になることを明示。docs/assets/hand-menu-startup-guide-v1.pngと同prompt.md、docs/28へ追加。実操作の合格証跡ではない。次は本人によるメニュー開表示の確認。

## 2026-10-10 サイズ設定の閉じるボタン不具合を実画面で修正確認

- 本人の「閉じるを押しても閉じない」を受け、実Slicerコンソールの `ValueError: Called close() -> bool with wrong number of arguments: (False,)` を確認。PythonQtのclicked(bool)を引数なしcloseへ直接接続した実装不具合。size_settings.pyを引数を吸収するPython関数経由へ修正。
- 既存SlicerへサイズUIのみ再読込。実Qtシグナル自己検証は閉鎖成立・寸法／仮C版不変（work/size-dialog-close-check.json）。その後Computer Useの実マウスクリックで「閉じる」を押し、画面とアクセシビリティツリーからダイアログが消えたことを確認。シーン再読込・再起動・台帳書込なし。次は受付開始後の実手メニュー操作。既知の保存等の不合格は維持。

## 2026-10-10 C直径10mmの実適用・サイズUI稼働反映完了

- 本人の再開指示に従い、Computer Useで既存Slicerの標準スクリプト実行を使用しサイズ関連メソッド・マウス設定画面を限定反映。初回のコンソール入力は残存空白によりIndentationErrorで未実行、確認後にファイル実行へ切り替えた。Slicer再起動・シーン再読込・台帳保存を行わず、現在の仮Cを維持した。
- 実設定画面の直径10mmを検収。仮Cが20mmで凍結中だったため、設定画面で編集再開→現在の仮Cにも適用→適用を明示操作し、成功表示を確認。work/size-settings-live-result.jsonは次／仮Cとも直径10mm、表示された仮C33点の半径約5mm、版1。寸法設定と仮Cの描画成立を確認した。元モデルの実寸校正、ハンド操作の成立、確定保存まで合格とはしない。
- 認識アプリのパネル下部のマウス用サイズ設定ボタンと、Slicerウィジェット側の同ボタンを反映。確認画面を開く前にstatusで最新仮C版を取得するよう修正し、認識側79件合格。Slicer側143件＋独立Qt自己検証合格は前回から維持。設定ダイアログだけをdocs/assets/c-size-settings-live-v1.pngへ取得。詳細はdocs/30。次の一手は本人による設定ボタンの再開閉と実手操作の検収。既知C保存・監査等の不合格は維持。

## 2026-10-10 Cサイズのmm数値設定を実装（稼働反映待ち）

- 本人のサイズ設定追加・直径10mm指定・サイズはハンド不要の訂正に従い、マウス用サイズ設定ダイアログとパネルの設定ボタンを実装。根拠・仕様はdocs/30。旧コードの半径10＝直径20を確認し、新しいSlicer初期値を直径10mmとした。モデルの実スケール検収は別で、見た目の全原因を断定しない。
- 次のCと現在仮Cの寸法を分離。現在仮Cへの適用は明示チェック、位置・方向を維持して版更新、凍結は明示再開。確定イベントに寸法・テンプレート定義を保存し、再読込は保存形状点を使用する。既存台帳を変更しない。
- 自己検証143件合格と構文チェック合格。Computer UseでSlicerを特定し、画像なしでコンソールを確認したが、クリックはcoordinate input geometry is unavailableで失敗。対象再取得と公式表示ショートカットでも入力フォーカスは確認できず、本人に>>>入力行のクリックを依頼中。既存Slicer・シーンを再起動せず、実寸設定適用済みとは報告しない。次は入力先確認後、既存セッションへ限定反映し、実ダイアログ・設定値を検収する。

## 2026-10-10 承認画面案の階層メニューを実装・稼働反映

- 本人の「このイメージ図で作って」を受け、docs/assets/hand-menu-design-v1.pngに合わせ、主5項目／C編集／計画・記録／独立確定確認を実装。青い選択カード・▶、開閉と受付表示、ジェスチャー案内、長い一覧の表示送りを追加。手入力による編集再開・主メニューへ戻る経路を維持。根拠は本人の画面案指定とdocs/23の操作メニュー要件。詳細はdocs/29。
- 自己検証79件合格。実装Tkウィジェットの合成主メニュー・編集・確定確認を描画取得して検収。稼働するPixel 8a認識アプリへ通常の署名付きrun.ps1で再起動反映し、認識継続を実ログで確認。Slicerは再起動せず、実パネルのみを取得して新しい編集一覧／停止中／仮Cありの表示を確認した。カメラ／患者シーンは取得しない。
- 実手で新UIの全操作が成立したとは報告しない。現在の仮Cは再接続で凍結し得るため、明示受付開始とメニューの編集再開を案内。未知版の確定は拒否。既知のC保存・監査等の製品不合格は維持し、次の一手は新メニューの実手での選択・戻り・閉じるの検収。

## 2026-10-10 メニュー構成の画面案を先に提示

- 本人の「まず、どういうメニューにしたいか、するのか？イメージを作ってくれ」に従い、追加の実装・再起動を行わず設計案の画像を作成する。主一覧を視点操作／C焼き印／既存Cの選択・訂正／計画・記録／操作停止に整理し、Cの仮配置後は編集一覧へ切り替える案。X印・認印は表示例なので追加しない。
- 選択行の強調、開閉表示、ジェスチャー案内、確定専用確認画面を図示する。階層化と確定確認画面は今後の変更案であり、現行実装の成立や既知所見の解決として扱わない。画像は合成UIで、実シーン・カメラ画像を外部送信しない。

## 2026-10-10 操作パネルを一覧メニューへ変更

- 本人の「パネルにメニューを表示」「X印・認印は例え」を反映。docs/23の小さな操作メニュー・選択先表示要件に結び付け、slicer_hud.pyでSlicerが返す全項目を順序どおり一覧表示。X印・認印は追加しない。C照準項目を「C焼き印（照準・仮配置）」と表示する。
- 開閉を「メニュー：開／閉」で明示し、開状態の選択行だけに▶を付ける。閉状態では直近取得した一覧を案内表示し、親指で開く。起動直後の一覧未取得時は取得案内を表示。高さを項目数に合わせる。受付・前面判定・サーバー操作は変更しない。
- 自己検証：認識側71件合格、一覧順序・選択行1件・閉状態カーソルなしを確認。初回のプロジェクトルート実行はimport失敗、正規の認識アプリディレクトリから再実行で合格。認識アプリのみ再起動して反映、Slicerは再起動しない。実手での新UI検収は未実施、既知のC編集・保存等の不合格は維持。

## 2026-10-10 メニューの見分け方を画面イメージで説明

- 本人の「どれがメニューを開いているかわからない。説明不足。画面イメージとかで説明を入れてくれ」を受け、最新添付を確認。今回は受付中／視点、番号・▶なしでメニュー閉。実ログもmenu_confirm ok=true／menu=False／mode=viewで視点への復帰を確認。以前の開状態の説明とは時点を区別した。
- docs/28へ閉／開の画面イメージ比較と見分け方の表を追加。常時表示パネルと選択メニューを区別し、番号・▶の有無、親指の文言が操作案内であること、開中のモデル停止を説明。合成図docs/assets/hand-menu-screen-states-v1.pngと生成プロンプトを保存。本人画像、モデル、カメラ映像は生成サービスへ送っていない。
- 今回アプリ再起動・操作割当て変更・モデル操作はしていない。次の一手は図で現在状態を確認し、メニュー開閉の実手再検収。視点復帰を全操作・C編集の合格へ拡張せず、既知製品不合格は維持。

## 2026-10-10 全操作無反応申告と開メニューの実確認

- 本人の全ジェスチャー無反応申告に対し、現在ログと自作HUDの実表示を再確認。受付中／C照準、menu=True,index=0、視点操作が選択されていた。メニュー表示中の連続モデル操作停止（原計画第75行）が働く状態。受付停止とは区別した。
- アプリは再起動せず、Slicerを前面へ戻して、現在選択中の視点操作を3本指で決定する1動作の確認を依頼。次の一手はmenu_confirm応答と本人の視点復帰確認、その後基本操作の再確認。まだ操作復旧済みとは扱わない。

## 2026-10-10 C照準切替の実画面確認と操作案内の具体化

- 本人添付の画面で受付中／C照準、実ログでmenu_confirm ok=true／mode=aim／draft=falseを確認。手でのモード切替は成立。仮Cがない状態の3本指に確定動作がないことと、モデル編集がまだ未成立であることを区別して説明した。
- 日本語パネルに照準の有効／表面外／未取得、仮Cなし、具体的な照準・仮配置操作と対象なしの理由を表示するよう修正。自己検証71件合格、Pixel 8aアプリへ反映済み。再起動後は再受付開始が必要。本人画像の映像部分は複製・外部送信していない。
- 次の一手は照準有効と仮C表示の実手確認。Cの配置・確定の実試験は今回未実施、既知のC確定・監査・保存不合格とSlicer側ソース稼働反映は未完了。

## 2026-10-10 15:04 JST 手順②の実表示確認

- 本人の「2メニューを開く ができない」を受け、現在ログと自作テキストパネルのみの画像を照合。実表示は受付中／視点、メニュー2/12、C配置：照準モード選択。ログもmenu=True,index=1。既に②③の状態になっており、開状態では親指を再検出しても閉じない仕様を説明した。カメラ／シーン画像は取得していない。
- 証拠work/menu-panel-check.png、最新起動ログ。次の一手は④3本指1秒保持でC照準への切替を実手検収すること。今回プロセス再起動・コマンド注入は行っていない。

## 2026-10-10 実手メニューテストのイラスト化

- 本人の「テストストリーがわからない。やることをイラストにして」に従い、docs/28とdocs/assets/hand-menu-test-story-v1.pngを作成。開始→親指で開く→2指で照準選択→3指で決定→親指で再開→拳で閉じるの6段階を、手形・保持時間・成功時表示で対応付けた。毎回1秒解放、Slicer前面・Pixel 8a・操作パネル確認を明示。
- 組込みimage_genで合成イラストを生成し、文字・手形・期待表示を画像で確認。カメラ映像・患者情報は使用していない。生成プロンプトも資産フォルダーに保存。図は試験手順であり操作成功の証拠ではない。
- 次の一手はこの図での実手再確認。離散操作の最終版受入・拳の閉操作、Slicer側ソース反映、既知C確定等の不合格は未完了のまま維持。

## 2026-10-10 操作パネル追加と親指の反復閉抑止

- 本人の「handshapeは認識しているが画面操作ができない」に対し分類閾値を変更せず、Slicer前面でも読める日本語メニューパネルslicer_hud.pyを実装。状態のみを表示し映像／シーンは扱わない。Win32実観測で可視・非アクティブ・最前面、Slicer前面PIDを確認。本人もパネルの表示と分かりやすさを確認した。
- 本人のC照準切替試験は不合格。実ログで切替中の親指再検出→menu_close→two/three無操作を観測し、親指を開く専用、拳を閉じる操作へ統一。試作割当てと操作表を更新。認識側70件自己検証合格。離散コマンド毎の応答ログを追加し、Pixel 8aで修正版を再起動済み。
- 実手でのモード切替・拳の閉操作は再確認待ち。パネルの見やすさを操作成功とは扱わない。証拠・限界はdocs/27追加節。次の一手は開いた手で再受付開始→親指メニュー→2本指で照準選択→3本指で決定の実手確認。Slicer側ソース変更の稼働反映とC確定関連の既知不合格は未解消。
- 続く実手でmenu_confirmも受理（選択はindex3のreset_view）。短い認識途切れで同形が再発火するFSMを修正し、既定0.35秒の解放後だけ同形を再受付する。原計画第80行に対応。認識側71件自己検証合格、Pixel 8aの起動アプリへ反映済み。最終版の照準切替と拳の実手受入は未完了。

## 2026-10-10 離散ジェスチャーのメニュー同期修正

- 本人がPAN・回転・ZOOMの実動作を確認。親指・2本指・3本指・グーは不合格申告。実ログで離散形認識とmenu is closed拒否を確認し、menu_closeの成功応答にmenuがない場合にクライアントが開状態を保持する不具合を修正した。
- 認識側69件の自己検証合格。実Slicerへ自作手形を入力して開く→次→グーで閉じる→再度開く→3本指でview選択の全受理を確認。実手ではない。修正版アプリはPixel 8aで起動中、Slicer前面、本人の実手再確認待ち。証拠・手順はdocs/27追加節。
- Slicer側ソースのDRAFTメニュー／表示／close応答も修正したが稼働Slicerへの反映は未実施。C配置・確定・監査の不合格は解除していない。次の一手は離散メニューの実手確認、次いでデータを保持したSlicer更新とC操作再検収。
- 前の調査での「無効時select_mode拒否が現行PRE_ARMと異なる」は取り違え。現行PRE_ARMでも拒否される。docs/27を訂正し、実応答は保持した。

## 2026-10-10 Slicer無反応の追加調査と診断表示修正

- 本人報告を受け、Pixel 8aの実ログで手検出あり／受理送信0件、実Slicer応答で受付無効・reviewモードを確認。カメラ接続成功を実手操作成功へ拡張しない。
- app.pyを修正し、Slicerの実受付状態を優先表示、初回None表示を除去、開始待ち・手形・拒否理由を診断へ追加。FR-001、SR-001/002/006を維持。関連33件および合成表示自己検証合格。
- 1回目実TCPは受付／前面ゲート拒否。2回目は前面PID照合後、arm→viewモード→回転1度／逆回転→disarmを実Slicerが受理した。これは自作入力の実ツール観測で、実手や目視確認ではない。証拠と稼働版差異はdocs/27追加節に記録。
- Pixel 8a番号1の修正版アプリへ再起動、disabled／armed=False／mode=viewを実ログで確認し、Slicerを前面へ戻した。本人に片手の開いた手2秒保持→左右移動の通し確認を依頼中。次の一手はその実手入力の受理と本人の画面変化確認。現段階で操作復旧完了とは報告しない。
- 続く実手ログでarmed=Trueへ移行、受理件数266件を観測。POINT/PINCH/OPEN_PALM時の件数増加を確認し、実手→Slicer受理まで成立。追加の自作コマンド注入なし。画面変化・意図一致は本人回答待ち。実手Hケースの全面合格や既知製品不合格解消は未認定。

## 2026-10-10 指定端末Pixel 8aへ接続変更

- 本人の「それを接続した」をUSB端末Pixel 8aの指定として扱い、ADBでUSB機能がadbのみであること、DeviceAsWebcamの存在を確認。svc usb setFunctions uvcを実行し、WindowsへのAndroid Webcam追加を実観測した。切替コマンドのexit1単体を成功証拠とせず、追加カメラのUSB親シリアル4A171JEKB04764を切替前のPixel_8aのADBシリアルと一致照合した。
- 以前の認識プロセスのみ停止し、既存run.ps1 -CameraIndex 1 -SlicerConnectで再起動。実プロセスPID13148、ウィンドウCardiac 3D Motion PoC、継続フレームready、127.0.0.1:18944 Establishedを確認。Pixel 9a仮想カメラの番号0から、Pixel 8a USBカメラの番号1へ接続を変更済み。アプリは起動継続。
- 証拠はwork/pixel-camera-connection-check.jsonおよびwork/recognition-current-launch.jsonが示す診断ログ。手0件・送信0件、実手操作は未確認。映像・音声は保存していない。docs/27の不合格は維持。次の一手はPixel 8aカメラへ手を提示して実手検出を確認すること。

## 2026-10-10 PIXELカメラ接続先の確認

- 本人の「PIXELを接続したのか？」「しろよ」を受け、Windows DirectShowの映像デバイス一覧を実取得。映像デバイスは「Pixel 9a (Windows 仮想カメラ)」1台。既存認識アプリPID34756は既定dshow・番号0で動作しており、そのPixel仮想カメラが接続先であることを確認した。既に接続済みのため再起動は行っていない。
- 認識ウィンドウ「Cardiac 3D Motion PoC」、継続フレーム診断、Slicerの127.0.0.1:18944へEstablishedを再確認。手0件・送信0件。映像内容・実手操作成立は未確認で、映像・音声は保存していない。確認記録はwork/pixel-camera-connection-check.json。
- USB ADBでは別名「Pixel_8a」を取得した。Windowsカメラ名のPixel 9aとの同一性は未確認であり、USB Pixel 8aをカメラとして接続したとは報告しない。次の一手は認識画面で希望端末の映像と実手検出を確認すること。docs/27の製品不合格・実手未合格は維持する。

## 2026-10-10 本人指示による認識アプリ起動

- 本人の「起動させろよ」に従い、既存Slicer PID30896／loopback18944待受を確認して、run.ps1 -CameraIndex 0 -SlicerConnectを標準実行ポリシーで起動した。認識実プロセスPID34756、親venvランチャPID5512、PowerShell PID44452。
- 実ツールでMainWindowTitle「Cardiac 3D Motion PoC」とウィンドウハンドルを確認。MediaPipe初期化ログ、継続的フレーム診断、認識プロセスから127.0.0.1:18944のESTABLISHEDを確認した。ログ参照はwork/recognition-current-launch.json。実画面の内容や手操作成立を確認したものではない。
- 起動後ログはhands=0、gesture=none、sent_total=0。ARMを送信しておらず、操作受付の有効化・C確定は実施していない。PIXEL映像同一性・実手検出は未確認。既知不合格はdocs/27のまま維持。
- 署名信頼・実行ポリシーは変更せず、実行拒否もなかった。映像・音声は保存しない。アプリは使用のため起動を継続。次の一手は映像源と実手認識の確認、C操作試験の前に既知安全所見の修正・再検収。

## 2026-10-10 テストプラン実行と結果MD

- 本人指示「テストプランを実行し、テスト結果MDを作成」をdocs/26第1版に結び付け、FIELD-20261010-01を実行。正本結果は`docs/27_field-test-results.md`、証拠は`evidence/FIELD-20261010-01/`。現行製品版のSHA-256を固定した。
- 自己検証はSlicer131件＋認識66件合格。認識側初回は作業ディレクトリ由来の収集エラー、再実行ログも保持。実Slicerの合成プローブ35項目で29述語PASS・6FAIL、その後DRAFTメニューで製品例外。実TCPのhello/status/無効時回転拒否/arm/disarmは成立。自作試験と実手を区別した。
- 不合格所見：再接続照会消失、改変台帳受理、監査確認順、元イベントメモリ属性変更、計画復元不成立、理由不一致、DRAFTメニュー例外、取消後CANCELLED。全要求適合ではない。署名検証非正常、SBOM現物5件不一致も実測した。
- PIXEL接続の本人申告後、カメラ番号0から1280×720を受信し約30秒・806フレーム認識。手検出0件。WindowsではADBと仮想カメラを確認したが映像源同一性・実手提示は未確認。映像・ランドマーク・音声は保存しない。安全中止条件のため実手C確定・計画・訂正試験は保留、Hケース全体未合格。
- 当該試験Slicerの非昇格実行を観測。静的通信監査exit0は継続的実行時監査とは別。既存コード／台帳／既存結果ハッシュ変更0。今回製品修正、署名／権限設定変更、独立レビューは行っていない。
- 現在地：テスト実行・不合格報告、全体未完了。次の一手は実装担当によるF-01/02/07優先修正と残り所見解消、専用版でX再試験。その後PIXELのウェブカメラ映像を確認しG-00→H-01→H-11→H-10へ進む。臨床使用・性能合格は未承認のまま。

## 2026-10-10 実地テストプラン作成

- ユーザー指定の`docs/21_implementation-report.md`第3版・追加分2を読み、原要求`docs/03`、検証方針`docs/05`、既存計画`docs/23`へ照合して`docs/26_field-test-plan.md`を作成した。既存H/X-IDを継承し、要件正本は変更していない。
- 実カメラ・手の準備、操作早見表、H-01〜12、X-01〜08、AC24件、故障時中止、観測と結果票、環境・性能測定を具体化。主操作は手のみ、通常マウスは代替試験として分離した。
- 報告と限定コード読取から、表示完了ACK、計画個別編集、反転／方向リセット／明示保存／順序変更等の手到達、代替マウス、監査確認順、理由選択を阻害・要確認事項として残した。実画面の不具合確定ではない。自己署名・静的通信監査を実運用適合と認定していない。
- 文書の構造自己検証でAC24件、H12系統、X8系統と参照リンクを確認。今回実手・実画面試験、試験プロセス起動、製品コード変更、署名／権限設定変更は未実施。独立レビューも今回追加していない。
- 現在地：実地試験の計画整備。次の一手：対象版と試験専用保存先を固定し、G-00準備確認→H-01開始停止→H-11基本保持→H-10停止復旧から実施。既知の阻害範囲は修正と再検収後に進む。臨床使用・臨床精度・性能閾値・本人識別等の未決事項は維持する。

## 2026-10-10 残存未実装項目の実装（計画版管理・監査・前面監視・ズーム・SBOM）

- ユーザー指示「未実装を実装しろよ」に対し、`docs/23`第2版の残存コード項目を実装した。完了判定ONI-004の段階2〜4は依然未達のため**全体完了ではない**。
- **計画版管理**: `cstamp/plan_revision.py`（`PlanStore`）を新設。`create_plan`/`begin_plan_revision`/`edit_plan_item`/`add_plan_item`/`delete_plan_item`/`move_plan_item`/`save_plan_revision`/`cancel_plan_revision`/`plan_diff`。編集は作業コピー、保存で新版＋差分記録、承認版不変。永続は`plans.jsonl`追記型。
- **監査コマンド**: `select_reason`（理由保留）、`set_out_of_plan`（次確定を計画外宣言）、`revoke_event`（元イベント不変の取消監査行追記）、`confirm_audit`（確認記録）。全てプロトコル経路で受理確認済み。
- **draft_revision版束縛**: DRAFT編集ごとにrevision増加、`commit`は`expected_revision`不一致を拒否、確定イベントへ`draft_revision`記録。台帳失敗時はDRAFT維持（OP-011）。単体試験で検証。
- **reset_view採用**: 初回利用時のカメラ姿勢を基準として復元する操作として実装（カメラのみ、Cデータ不変）。docs/01・docs/10との整合を確認し採用と記録。
- **前面ウィンドウ監視**: Win32 `GetForegroundWindow`→PID照合（非ブロッキング）をディスパッチャゲートへ組込み。実機で双方向確認——notepad前面時に`view_rotate`拒否（`target window is not foreground`）、status/disarm/menuは許可。
- **ホイール→連続ズーム**: `op_controller.zoom_step`＋プレビュー窓`wheelEvent`で離散入力を連続比率ズームへ変換（FR-022）。確定時は直近draft_revisionを束縛送信（ONI-001）。
- **単位10の可能範囲**: `tools/generate_sbom.py`（SHA-256マニフェスト＋pip freeze、`artifacts/sbom/sbom-20261010.json` 50ファイル・39依存）、`tools/audit_network.py`（静的走査、非loopback 0件）を実装。
- **検証**: 単体 slicer-cstamp 131件・cmos-motion-poc 66件全合格。実SlicerE2E `e2e_result.json` `ok:true`（計画版管理・監査・reset_view・メニュー・shell拒否・disarmを含む全経路）。
- **追加分2（同日）**: 画面メニューへ計画版管理（rev begin/save/cancel）・監査（revoke_selected/audit_confirm）・理由区分（登録候補のみ受理）・reset_view・out_of_plan・commit/cancelを項目化。e2eでメニューconfirm→dispatch_local実行を確認（menu_plan_rev_*・menu_reason_*・menu_revoke_selected等全true）。`select_reason`は登録候補以外を拒否。`revoke_event`/`confirm_audit`は`_selected_event_id`をフォールバック対象に採用（reviewモード選択→メニュー監査）。
- **署名**: `run.ps1`/`setup.ps1`へ自己署名証明書`CN=CStampPoC-Dev`でAuthenticode署名付与（thumbprint `262148C3...4594`、証明書`artifacts/cstamp/cstamp-poc-dev.cer`）。`UnknownError`は未信頼ルートのみ。正式組織証明書への差替えは運用課題。
- **証明メモ**: `docs/25_minimal-privilege-config-proof.md`でIT-004（権限必須APIゼロ・loopback限定・venv局所）とIT-005（構成値検証・モデルSHA-256ピン・SBOM）を文書化。
- **残存未実施**: 実手試験H-01〜12、X-06性能合格判定、正式組織署名・ルート配布、実行時昇格監査、個別項目編集（edit/add/delete/move_item）のメニュー化（複雑パラメータのためプロトコル経路のみ）。
- 次の一手: H-01〜12の実手試験。

## 2026-10-09 ハンドモーション完結経路の実装と実Slicer結合検証

- `docs/23`第2版の必須範囲のうち、コード層の実装を実施した。完了判定はONI-004の段階2〜4（実手H-01〜12、利用者確認、署名等）が未実施のため**全体完了ではない**。
- **共通契約** `command_protocol.py`: hello/セッション、封筒（版・session・req・seq・ts・TTL2000ms）、許可リストのみ受理、古い操作・連番逆行拒否、req dedup、ARM/モード/レイヤー/DRAFT状態ゲート、query_result、切断時DRAFT凍結（取消しない）。
- **コア拡張**: `move_draft`（アンカー移動＋u射影、方向不変）、`seed_draft`（訂正DRAFT＋`correction_of`引継ぎ）、`PlanTracker.reorder/select`。
- **CStampModule**: ARM/モード/レイヤー状態表示、黄照準マーカー、stamp/move/rotate/tilt/reverse/reset/commit/cancel/resumeの全ops、計画読込/スキップ/順序変更/照合、台帳保存/復元、選択→読み取り専用C再構成、begin_correction、画面メニュー（menu_open/next/prev/confirm/close→dispatch_local）。単一クライアント・loopback限定。
- **PoC側**: `gesture_fsm.py`（7手形＋エッジ/ホールドラッチ）、`session_client.py`（封筒クライアント）、`op_controller.py`（モード別連続入力＋離散ジェスチャー写像。親指=メニュー、2指=スタンプ等、3指=確定、拳=取消、開いた手1.5s保持=受付開始）、`app.py`に`--slicer-connect`新経路統合。回転専用感度・不感帯、連続ズーム比率送信を追加。
- **実機検証**: ヘッドレス`module_result.json`全項目ok、GUI`gui_result.json`全項目ok（view_rotateが実カメラ移動）。PoC→実SlicerのE2E `e2e_result.json`全項目ok（hello→arm→aim→stamp→move/rotate/tilt→commit→重複commit拒否→query→menu→disarm）。単体試験 slicer-cstamp 89件、cmos-motion-poc 62件すべて合格。
- **未実装**: 計画新規・版管理コマンド群（CREATE_PLAN等）、SELECT_REASON等の明示コマンド、draft_revision/版束縛確定、代替マウスの同一経路・ホイールズーム、Slicer側前面監視、X-01〜08注入試験、H-01〜12実手試験、単位10（署名/SBOM/配布）、性能実測。
- 次の一手: H-01〜12の実手試験（開始→モード→照準→スタンプ→調整→確定→取消→訂正→復旧）とX注入試験の実施、その後未実装コマンド群の追加。

## 2026-10-09 実装計画書第2版と再レビュー完了

- 最新正本は`docs/23_hand-motion-completion-plan.md`第2版。原要求74件とAC24件を個別行で実装単位・試験へ対応付け、手だけの操作完結を計画・訂正・保存読込・復旧まで拡張した。H-01〜12の実手シナリオとX-01〜08の共通試験、担当役割・決定期限・未決時の扱いを具体化した。
- ONI-001〜004に対し、表示済みDRAFT版と確定スナップショットの一致／競合処理、代替マウスの移動・連続傾斜、拡張機能の実手受入、IT-002署名必須の完了ゲートを追加した。手の主操作にマウスを必須としない。
- 文書構造の自己検証：FR40・OP13・SR12・IT5・PR4・AC24の個別行、20試験IDの参照を確認し未定義参照0。これは製品試験ではない。
- 別Codexの鬼教官担当が原文と第2版を再照合し、4指摘すべてを計画上解消、確認範囲で追加の具体的欠落なしと判定。証拠は`docs/24_oni-review-hand-motion-plan.md`末尾。Utility Pm Critic等のレビュー技能は使用していない。人間・臨床の独立監査ではない。
- 現在フェーズは不足分の実装計画整備完了。今回製品コード変更・実手試験・署名は未実施。人物識別、臨床精度・性能基準、訂正権限・承認等の未決事項は維持。次の一手は単位1〜2の操作パネルと表示版を含む共通契約の実装、その後単位3〜7の手入力接続と個別証拠更新。

## 2026-10-09 鬼教官役による独立文書レビュー

- ユーザーの明示指示で計画作成者と別のCodex担当を召喚し、`docs/23`を原要求・利用者指示へ照合した。Utility Pm Criticの適用はユーザー指摘後に取り下げ、同スキルを使わず実施した。
- 結果は修正必要、P1が1件・P2が3件。確定するDRAFTの表示済み版と内部値の同期、代替マウスの不足経路、計画・訂正・異常再開を含む実手の個別受入試験、IT-002署名要件と完了条件の整合を指摘。報告は`docs/24_oni-review-hand-motion-plan.md`。
- 前回の「原要求に対して計画上の未対応項目なし」は意味的網羅の主張として撤回する。74要求と24ACのID欠番がないことは自己検証したが、具体的実装作業と受入条件の不足がないことは立証していなかった。
- 今回は独立担当による文書レビューと報告記録のみ。臨床・人間の独立監査ではなく、計画・製品コード・試験結果の修正は行っていない。次の一手はONI-001〜004を計画の具体的作業・受入条件へ反映し、再レビューすること。

## 2026-10-09 実装計画の漏れ再照合

- ユーザーの「これでもれはないな？」に対し、`docs/03`のFR40件・SR12件・IT5件・PR4件・OP13件とAC24件、`docs/01`の安全状態・基準視点を、補足計画`docs/23`へ再照合した。
- 作業具体化が不足していた計画メタデータと版差分、確定記録取消・訂正、無操作解除、設定固定、モデル／表面同一性、DRAFT中視点切替、保存全項目・精度、返信喪失時結果照会、性能測定、通信・構成・配布管理を追記した。実装単位10を追加し、原要求網羅対応表を設けた。
- 基準視点復帰はdocs/01・docs/10と現行FR-002の列挙に差があるため、採否整合を明示的な作業・未決事項として記録した。人物識別・臨床性能・権限・承認等も未決として維持する。
- これは文書自己照合とID割当ての自己検証であり、独立監査・実装・実機試験の完了ではない。次の一手は対応表を使って実装単位ごとに着手し、結果を要求追跡へ反映すること。

## 2026-10-09 編集操作の計画範囲の再確認

- ユーザーから編集操作が計画に含まれていないのではないかとの指摘を受領。初期計画`docs/20`は方向調整と入力共通契約を記載する一方、配置後位置変更と各C操作の手入力接続を具体的な作業へ分解できていなかった。
- 最新補足計画`docs/23`では、単位4が照準・仮配置、単位5が位置・開口方向・連続傾斜・反転・リセット、単位6が独立確定・取消として明記されていることを確認した。「編集操作未実装」は実装状態を指し、最新計画の対象外を意味しない。先の説明でこの区別を十分伝えなかった。
- 今回は計画内容の再確認のみで、製品コード変更は行っていない。手だけで一連のC操作を完結する計画の完了条件を維持する。

## 2026-10-09 追加ジェスチャー候補の一覧図

- ユーザー依頼により、既存3形状（開いた手、人差し指、ピンチ）と追加4候補（親指のみ、2指、3指、握りこぶし）、モード別の照準・位置・開口方向・傾斜操作を一覧図にした。`docs/images/hand-gesture-candidates-2026-10-09.png`へ保存し、実装計画から参照した。
- built-in imagegenで生成し、図の文字と手の形を目視で自己確認。実装済みと未実装候補を明記した。追加操作を実機で使えると主張せず、ジェスチャー認識コードの変更・実測は行っていない。
- 次の一手は`docs/23`の実装順序に沿う接続と、候補形状・モード割当ての実手評価。

## 2026-10-09 不足分のハンドモーション実装計画

- ユーザー訂正「マウスが使えるならハンドモーションいらない」を受け、操作者がマウス・キーボードに触れずCスタンプ操作を完結することを主目的とした。通常マウス等は既存安全原則の代替経路として維持する。
- 依頼に従い`docs/23_hand-motion-completion-plan.md`を作成し、`docs/20_implementation-plan.md`から参照を追加した。根拠は`docs/03`のFR-001/003/008/013/015〜040、TASK・OP・SR・AC、および利用者の操作報告。不足と原要求、変更先、実装順序、受入条件を対応付けた。
- 計画は非接触開始停止、モード選択、照準、仮配置、配置後位置移動、連続方向調整、独立確定・取消、計画／実績・レビュー・訂正、回転改善、連続ズーム結合、Slicer受理応答と安全ゲートを含む。追加ジェスチャーは未固定の試作案と明記した。
- 今回はMarkdown計画書の作成・内容確認のみ。製品コード変更、実機試験、承認は行っていない。次の一手は計画単位1〜2の起動・操作パネル提供と共通コマンド／結果応答の実装。その後、手だけのCスタンプ操作を単位3〜6で完結させる。

## 2026-10-09 実操作確認とCスタンプ入力の要求漏れ

- 利用者からパン・ズームは問題なく、回転は操作しにくいとの実操作報告を受領。利用者確認として記録し、独立観測・数値性能検証とは区別する。
- `docs/03`のFR-008、FR-013、T-001〜T-005、AC-007を現行コードへ照合。手入力輸送は視点操作3種類だけで、照準、Cスタンプ仮配置、配置後位置調整、C方向調整、明示確定、取消へ未接続。配置後位置移動はコア公開操作自体も見当たらない。要求全体の完成とは扱わない。
- Slicer側のスタンプ・方向・確定・取消・計画等の機能は存在するが、起動スクリプトはウィジェット生成のみで、操作パネル表示の明示処理も欠ける。利用者が実際に操作パネルを使用できていることは未確認。
- 根拠と不足を`docs/21_implementation-report.md`冒頭へ訂正記録した。次の一手は操作パネルを利用者へ提供し、FR-013の入力共通契約へCスタンプ操作一式を接続すること。確定を独立した明示操作とし、仮配置だけでログ生成しない安全要求を維持する。回転操作性も利用者報告に沿って改善対象とする。

## 2026-10-09 認識するがSlicer無反応の調査

- 利用者の画面表示回答はDISABLED。Slicer PID24888のloopbackポート18944のLISTENを実ツールで確認した。操作無効状態ではジェスチャー分類だけが表示され、コマンド送信されないことを現行コードに照合した。
- `app.py`へ1秒間隔の非映像診断ログ（状態、モード、手数、分類、観測経過時間、抑止理由、出力量、輸送送信件数）を追加した。既存自己検証33件合格。送信件数は輸送上の送信成功数であり、Slicer適用成功数とは扱わない。
- 認識アプリをPID16884で再起動し、実ログでhands=1、gesture=rotate、state=disabled、gate=disabled、sent_total=0を観測した。カメラ画面選択後にSpaceで明示有効化する手順を案内した。映像保存・外部送信は行っていない。
- 次の一手は有効化後の送信と実Slicer視点反応の確認。無反応の操作無効状態は特定したが、実手から視点変更までの成立は未確認。
- 続く実ログで利用者の明示有効化後にREADY→EXECUTING、hands=1、gesture=pan、`sent: pan`を観測し、輸送送信件数109件とSlicer側TCP ESTABLISHEDを確認した。画面の視点反応は利用者確認待ちであり、送信成立から適用成立を推定しない。

## 2026-10-09 ハンドジェスチャー操作図

- 利用者から「アクションは認識しているが種類がわからない」と報告を受領。実装`motion_engine.py`の分類規則と移動量変換に合わせ、回転・パン・ズームの操作早見表をbuilt-in imagegenで生成し、`docs/images/hand-gesture-guide-2026-10-09.png`へ保存した。
- 図は、開いた手＋上下左右移動＝回転、人差し指のみ伸ばした手＋上下左右移動＝パン、親指と人差し指のピンチ保持＋手全体の上移動＝拡大／下移動＝縮小、カメラ画面選択＋Space＝開始停止、Q/Esc＝終了を示す。生成図の文字と手の形は目視で自己確認した。患者画像・カメラ映像は使用していない。
- 次の一手は図を参照した利用者の操作確認。利用者の認識成立報告と、独立した実機結合・性能検証は区別する。

## 2026-10-09 認識アプリとSlicer受付の起動

- ユーザー指示により認識アプリを実際に起動した。最終起動は`app.py --camera-index 1 --slicer-connect`、PID 15336。プロセス継続とMediaPipe/TensorFlow Lite初期化ログを確認した。ログは`work/recognition-connect.{stdout,stderr}.log`。映像保存は行っていない。
- Slicerを`start_server_session.py`で起動し、PID 24888の`SlicerApp-real`、スクリプトログの`server listening`、`127.0.0.1:18944`のLISTENを確認した。
- 起動時はモーション無効。利用者がカメラプレビューを選択してSpaceで有効化する。今回の確認はプロセス・初期化ログ・待受までで、画面表示内容、利用者の実手認識、視点移動成立は未確認。次の一手は利用者の片手による操作確認。

## 2026-10-09 操作方法の案内

- ユーザーから開発・カメラ接続完了、操作方法不明との報告を受領。`run.ps1`、`app.py`、`CStampModule.py`、`slicer_bridge.py`の現行コードから起動引数と操作を確認した。実機操作・動作の再検証は今回行っていない。
- Slicer側で視点操作ポート18944の受付を開始し、PoCを`-CameraIndex 1 -SlicerConnect`で起動する。カメラプレビュー画面を選択してSpaceで有効化し、開いた手の移動＝回転、人差し指のみの移動＝パン、親指と人差し指のピンチ＋上下移動＝ズーム。Spaceで無効化、Q/Escで終了。
- 現行モーション輸送はrotate/pan/zoomのみ。CスタンプはSlicer側の通常マウスで「照準→スタンプ（仮配置）」→対象表面クリック→方向調整→「確定（操作記録）」／「取消」を使用する。確定レイヤーでPLANNED/PERFORMEDを選ぶ。
- 次の一手はこの手順による利用者の操作確認。開発完了との報告を、実手結合検証や臨床承認の証拠として置き換えない。

## 2026-10-09 ドキュメント読込と現在地の整理

- ユーザー依頼により、README、正式憲章の本文・表、`docs/01`〜`22`、`registers/`の5台帳、監査報告、プロトタイプREADME、主要検証証跡を読んだ。既存の`artifacts/cstamp/{gui,module}_result.json`も照合した。今回は文書・保存済み結果の確認のみで、試験再実行、実画面観測、カメラ操作、製品コード変更は行っていない。
- 目的は、術前計画と術者の明示操作による実績記録を独立レイヤーで対応付け、非接触操作を検証すること。`docs/03`の仮配置→方向調整→独立した明示確定／取消、C全体の再構成可能な保存、PLANNED/PERFORMED分離を要求として理解した。操作記録は実焼灼病変や治療成功を証明しない。
- 現在地はDiscovery／非臨床プロトタイプ開発。10月8日の記録には自己検証の単体試験（cstamp 62件、PoC 33件）、実Slicer上のヘッドレス検証、合成イベントによるGUI検証がある。10月9日20:23:48の追記ではPixel実映像入力がindex1で成立した記録がある。実手→認識→安全制御→TCP→Slicerの結合動作と性能は引き続き未検証。
- 文書上の不一致として、正式憲章第2節のスライス送り・戻し許可と現行スコープの禁止、slicer-cstamp READMEの旧制約と`docs/21`の実装報告、担当報告内の旧カメラ状態と最新追記、台帳の旧要求件数・追跡範囲を確認した。要求適合は原文から判断し、実装報告だけで要求承認やゲート通過を推定しない。
- 安全上の未決事項は操作者識別、清潔域でのアーミング、性能基準、座標登録・訂正責任、関係者承認、リスク評価と要求追跡。臨床使用禁止、認識不能時の無操作、通常操作の維持、患者情報の非保存・非送信を継続する。Beadsは本人指示に従い使用しない。
- 次の一手は、実機検証時にカメラindex1の入力成立を再確認し、保存しないプレビューで実手認識・異常時無出力を確認してから、Slicerへの視点操作結合を段階的に検証すること。これは次工程の整理であり、今回の読込依頼で実機操作を実施したものではない。

## 2026-10-09 Pixel実カメラ経路の確認と依頼発行

- camera index 0（Windows Virtual Camera Device）はOpenCVで開けるが全フレーム黒（mean=0、差分0）であり、実映像は来ていないと訂正。前回「1フレーム取得」の報告は黒フレームの可能性があり、実映像確認としては無効。
- Pixel 9aはUSB接続済みだがADBは`unauthorized`（端末側許可待ち）。カメラ経路はUSB接続だけでは有効化されず、USB webcamモードかWindows接続カメラの明示的有効化が必要。
- 物理操作を伴うため依頼文を`docs/22_request-pixel-camera-setup.md`へ発行した。完了判定は「mean>0かつdiff>0」。
- Slicerコマンドサーバは`127.0.0.1:18944`で待受継続中（プロセス7496）。実カメラが生き次第、`--slicer-connect`で端から端の実機結合を検証する。

## 2026-10-08 実装単位1〜4の実装とGUI検証

- **単位1（Slicer Cスタンプ）**: `cstamp`コア＋`CStampModule.py`を実装し、メインウィンドウ付きSlicerで実インタラクター経路を検証した（`gui_verify.py`）。AC-001（照準クリック→33点DRAFT）、AC-002（連続開口角スライダー60°）、AC-003（確定→台帳1行＋確定点）、AC-004（取消→DRAFT消去・台帳不変）を`gui_result.json` `ok:true`で確認。
- **単位2（視点操作接続）**: `view_commands.py`（rotate/pan/zoom限定・JSON行・フェイルクローズ解析）とSlicer側`127.0.0.1`限定QTcpServerを実装。実ウィンドウでTCPコマンドがvtkCameraを動かすことを確認（`server_moved_camera:true`）。PoC側は`SlicerCommandBridge`＋`--slicer-connect`で送信。単体試験24件合格。
- **単位3（ハンドモーション安全経路）**: `SafetyController`（DISABLED→READY→TRACKING→EXECUTING、全異常で解放付き降格、FAULTラッチ）、`StrictTargetGuard`（前面プロセス実行パス完全一致、タイトル一致廃止）、`SmoothZoom`（不感帯・加速度制限・解放減衰）、`TasksHandRecognizer`（Tasks Hand Landmarker VIDEO、ピン留めモデルSHA-256記録）を実装し`app.py`へ統合した。単体試験込みPoC計33件全合格。
- **単位4（PLANNEDレイヤー・計画追従）**: `PlanTracker`（順序・最近接照合・許容差・スキップ・計画外）を実装。ヘッドレス実機検証で、PLANNED確定→計画点層分離、計画読込→緑ゴースト表示、PERFORMED照合→`plan_match`台帳追記（Δ位置・Δ法線・Δ面内角）、計画消化でゴースト消去、計画外PERFORMEDは`matched:false`記録を確認（`module_result.json` `ok:true`）。
- **結果**: cstamp試験62件、PoC試験33件すべて合格。証跡は`evidence/2026-10-08-cstamp-module-gui.md`、`artifacts/cstamp/{module,gui}_result.json`。
- **残存**: 実CMOSカメラ＋実手での結合動作、連続傾斜ドラッグ、`correction_of`訂正UI、性能実測。`input_bridge.py`（pyautogui・タイトル一致）は新規経路では不使用の後方互換残置。GUI検証は合成インタラクターイベントであり、人手操作とは区別する。

## 2026-10-08 実装計画書の作成とライブラリ再選定

- ユーザー指示により、動作するものの実装を最優先とし、評価は医療従事者が行う方針を確認した。依頼元は医師。
- ハンドモーション認識OSSの再調査結果（GitHub Repository Intelligence Ranking）を受領し、プロジェクト制約に照合した。1位のvladmandic/humanはTypeScript専用で言語スタック不合致、2位のgrlibはLegacy `mp.solutions.hands`依存かつ学習型分類器で非決定論的、yohaはunmaintained、barehandsはAGPL、その他は学術コードまたは更新停止のため、いずれも不採用とした。
- ADR-002の構成（MediaPipe Tasks Hand Landmarker VIDEOモード＋プロジェクト所有の決定論的IntentClassifier）を再確認して採用とした。変更根拠はなかった。
- `docs/20_implementation-plan.md`を作成した。対象表面を`CARTOmesh_1-OG`（CARTO心房EAM殻）に固定し、実装単位を「Slicer側Cスタンプモジュール（マウス先行）」「視点操作のSlicer接続」「ハンドモーション経路」「計画追従ビュー」の4単位に分け、検証順序をAC-001〜AC-024へ対応付けた。
- 本計画は実装手順の記録であり、要求の変更、臨床承認、性能合格の主張ではない。

## 2026-10-08 実装報告書の発行

- 完了・実装済み未検証・未実装を明確に分離した実装報告書を`docs/21_implementation-report.md`として発行した。

## 2026-10-08 Cスタンプ・コア実装（単位1の一部）

- `prototypes/slicer-cstamp/`に、Slicer非依存の純粋Pythonコア`cstamp`とScripted Module `CStampModule.py`を新規実装した。`IDLE`/`DRAFT`/`COMMITTED`/`CANCELLED`状態機械、決定的配置面基底、Cテンプレート版・SHA-256、追加専用JSONL台帳（順序・改変検出ハッシュ）、認識喪失時の凍結を含む。
- 単体試験31件すべて合格（AC-001〜005、009〜011、014〜018、OP-008/009/013の論理条件）。実メッシュ`CARTOmesh_1-OG`へのヘッドレス検証で、光線交差→スタンプ→15°回転→確定→取消が成立し、台帳1件・重複確定排除・整合性ハッシュを確認した。証跡は`evidence/2026-10-08-cstamp-core.md`。
- **未完了**: `CStampModule.py`の実GUI読込・ボタン操作・照準クリック・Markups表示は未検証（ヘッドレス検証はコアとVTK APIのみ）。方向調整は固定15°刻みで連続調整なし。確定点再表示は同一会話内のみ。`PLANNED`レイヤー、計画追従、SMOOTH_ZOOM連続化、ハンドモーション経路（MediaPipe Tasks移行・SafetyController・TargetGuard厳格化）は未着手。

## 2026-08-29 Cスタンプ操作・計画要件の合意反映

- ユーザー追加目的として、左心房／肺静脈周辺を戦略シミュレーションとして表示し、予定Cスタンプを事前配置する`PLANNED`レイヤーと、術中の`PERFORMED`実績レイヤーを分離して要求化した。
- 計画追従操作として、次の予定Cスタンプのゴースト表示、現在の仮配置との位置・姿勢・開口方向差、確定時の予定ID対応付け、予定スキップ、順序変更、計画外実績を要求化した。計画表示から実績を自動移動・自動確定しない。
- AIによる必要箇所・個数・配置の決定は、ユーザー提示の将来アイデアであり合意済みベースライン要求ではないと訂正した。`FC-001`〜`FC-007`へ分離し、受入試験IDは付与していない。
- ユーザー訂正により、右側参考画像の各点はC型焼き印1回分の表示であり、複数のCスタンプを繰り返し蓄積するものとして要求を更新した。点への変換は表示方法だけで、確定データはC全体の形状、位置、姿勢、方向を保持する。
- 確定イベントへ、座標系、Cテンプレート版・ハッシュ、アンカー座標、配置面基底、開口・進行方向、完全変換、確定時C形状、順序、訂正関係、改変検出情報を保持する要求を追加した。点からCを読み取り専用で再構成し、保存・再読込後の一致をAC-015〜AC-018で検証する。
- 「正確」を、保存値を忠実に再現するデータ完全性と、実カテーテル位置に対する臨床的位置精度へ分離した。データ完全性の合格だけでは臨床的位置精度または治療成立を証明しない。
- ユーザー提示の5 TASK（未配置、スタンプ、C方向調整、確定・記録、取消）ごとに、入力非依存の論理操作、連続／離散、完了条件、データ作用を定義した。具体的なハンドジェスチャー割当ては実測前のため未固定とした。
- 拡大・縮小は共通の連続`SMOOTH_ZOOM`として、デッドゾーン、平滑化、加減速・速度・倍率制限、解放／認識喪失時停止を要求化した。ズームはカメラだけを変更し、Cスタンプの座標、形状、方向、ログを変更しない。
- AC-009〜AC-014として、照準、スタンプ重複防止、位置を変えない方向調整、ズームの単調性・停止・データ不変、両段階からの取消を追加した。数値の滑らかさ合格値は非臨床実測後に決定する。
- ユーザー合意に基づき、Cスタンプ操作を「スタンプで仮配置 → 位置・方向調整 → 独立した明示確定で正式な操作ログ生成」として`docs/03_system-requirements.md`へ要求化した。スタンプだけでは確定ログを生成せず、確定前は取消可能とした。
- Cの方向を、配置面の向き、面内回転、開口方向、必要時の始点から終点への進行方向に分離した。仮配置と確定記録は視覚・データ上で区別し、元CT／DICOM、心臓3Dモデル、既存確定ログを変更しない。
- ハンドモーションと通常マウスは同一コマンド契約を使い、認識不能・曖昧・複数人・遮蔽・対象喪失・通信異常時は状態もログも変更しない。確定はスタンプ／調整とは別の明示操作とし、重複入力からの二重記録を禁止した。
- AC-001〜AC-008として、仮配置時0件、確定時ちょうど1件、取消時0件、方向のみの単一変数試験、異常時無変更、マウス／モーション同等性、保存・再読込を最小受入条件にした。これは要件合意であり、実装・試験合格・臨床承認ではない。

## 2026-08-29 プロジェクト・パーパスの明文化

- 長期目的を、(1) 術前CT由来の心臓3Dモデル上で行う焼灼計画シミュレーション、(2) 手技中に術者が確認して残す焼灼操作ログ、(3) 計画と操作ログの術後比較、(4) 手技と記録を並行するためのハンドモーションUI、として`README.md`および`docs/17_project-purpose-and-problem.md`へ記録した。これは目的と問題定義の保存であり、臨床要求の承認、実装完了、臨床使用許可ではない。
- 「計画焼灼線／点」「焼灼操作ログ」「実際に形成された組織病変の画像」を別概念として固定した。操作ログは、組織病変の形成、伝導ブロック、治療成功を証明しない。
- ユーザー提供画像2点を画面上で確認した。ユーザー報告ではWeb取得画像であり、元URL、著作権、ライセンス、配布条件、患者情報の取扱いが不明なため、画像ファイル自体はリポジトリへ複製していない。
- 実焼灼病変の画像化費用が約30万円であること、東京とその他地域に利用格差があること、保険適用外となる場合があることは、解決すべき背景としてユーザー報告を保存した。ただし、費用内訳、制度、地域別利用可能性の独立確認は未実施であり、確認済み事実とは扱わない。
- ユーザー判断に基づき、3D Slicerを公式サンプルデータ使用の非臨床PoC標準環境としてADR-004でAcceptedとした。公式資料で心臓系サンプルの存在を確認し、最初のWindows検証対象を公式安定版`5.12.3`へ固定した。実際に使用する心臓データ、拡張機能、配布物のローカルハッシュ照合、導入、動作確認は未完了であり、臨床採用ではない。
- AIとOSSを、従来不足していた要求整理・設計・実装・試験・証跡作成のエンジニアリング資源として投入する意義をパーパスへ追加した。AIは臨床判断、医療安全、法規判断を代替しない。
- 現行の安全境界は元CT／DICOMおよび心臓3Dモデルの変更を許可していない。新しい操作ログは、原データを変更しない分離されたオーバーレイ／イベント台帳として成立するかを先に設計審査する。

## 2026-08-29 3D Slicer導入・日本語メニュー化

- 公式Windows Stable 5.12.3インストーラーを取得し、公式SHA-512一致を確認後に導入した。インストール終了コードは0。
- 公式`SlicerLanguageTranslations`の日本語翻訳をSlicer同梱`lrelease.exe`でコンパイルし、言語設定を`ja_JP`へ変更した。
- 公式翻訳適用後の組み込みメニュー88項目では、英語だけの表示が`Capture/Restore`と`About 3D Slicer`の2項目残った。プロジェクト補完翻訳を追加後、通常の全モジュール読込条件で再監査し、英語だけのメニュー項目は0件、終了コード0、標準エラーなしとなった。
- この結果は組み込みメニューの日本語化であり、全ダイアログ、ツールチップ、説明文、CLI、将来追加する拡張機能、医学用語の妥当性までは保証しない。証跡は`evidence/2026-08-29-slicer-japanese-menu.md`。
- 3D Slicerを通常表示で起動し、実ウィンドウ上で日本語メニューバーと日本語のようこそ画面を確認した。アプリはユーザー確認用に開いたままとした。起動時の非臨床使用注意ダイアログ本文は英語であり、メニュー以外のUI日本語化は未完了。

## 2026-08-29 公式心臓サンプルの読込確認

- 3D Slicer 5.12.3内蔵の`Sample Data`から、最初の心臓基準データを静的CTAの`CTACardio` 1件へ固定した。拡張機能や他サンプルを同じ検証へ混ぜていない。
- `CTA-cardio.nrrd` 61.1 MBを取得し、Slicer画面ログの`チェックサムOK`と`ロードが完了しました`、データモジュールの`CTACardio`ノード、横断・冠状・矢状3断面の表示を実ウィンドウで確認した。3D Slicerは開いたままとした。
- ローカルファイルの実測SHA-256 `3b0d4eb1a7d8ebb0c5a89cc0504640f76a030b4e869e33ff34c564c3d3b88ad2`は、Slicer公式`SampleData.py`の期待値と一致した。証跡は`evidence/2026-08-29-slicer-ctacardio-sample.md`。
- サンプル単体の再配布ライセンスは今回確認した公式定義から確定できなかったため、データ本体はリポジトリへ複製せず、Slicer管理下のローカルキャッシュだけに保持した。
- この結果はデータ取得・同一性・表示成立の確認であり、心臓セグメンテーション、焼灼計画、座標登録、操作ログ、臨床妥当性を確認したものではない。

## 2026-08-29 右側完成イメージに基づくサンプル再選定

- ユーザーが示した右側の完成イメージは、生CTの3断面ではなく、CARTO／EnSite型の3D電気解剖学マップであると整理した。必要な表示は、心房3D表面、LAT／電位等の表面値、計画線、焼灼点状の実績タグの分離レイヤーである。
- `CTACardio`は公式データ取得・表示の基礎試験には有効だが、右側完成イメージを直接説明する主サンプルとしては不適切と再分類した。将来のCT解剖との位置合わせ候補として保持する。
- SlicerHeart公式`EA Map Reader`がNavX、CARTO 3、RHYTHMIAの電気解剖学マップを扱い、公式CARTO 3テストデータを提供していることを確認した。
- 公式`Carto3_EA_map.zip`を一時領域へ取得し、`1-OG.mesh`と`EA_map_car.txt`を確認した。ZIPの実測SHA-256は`26ecb532bcb90970871b9624cc53d3cf964cb2bde26658b087b642d17de694d4`。
- SlicerHeart revision `917f132`を導入した。Windowsアプリケーション制御が一部同梱DLLを遮断したため、安全機能は変更せず、EA Map Readerを含むPythonモジュールだけを有効にした。公式CARTO 3経路で実行時に確認したUI名不一致、`qt`未import、点分割式の3不整合をローカル導入物で局所修正した。
- 修正版EA Map Readerで`CARTOmesh_1-OG`（9,957 vertices／19,909 triangles）と`CARTOpoints_1-OG`（959点）を生成し、灰色面＋赤点としてSlicer実画面で確認した。検証済み非患者シーンは`artifacts/slicer/CARTO3_EA_Map_Demo.mrb`へ保存した。
- この公式サンプルは点ごとのBipolar／Unipolar／LAT属性を含むが、面スカラー配列は0件である。右側画像のLAT／電位カラーマップ、焼灼実績点、計画線は未実装であり、別レイヤーとして段階検証する。証跡は`evidence/2026-08-29-eamap-sample-review.md`。

## 2026-08-29 心臓全体の非臨床3D基準モデル

- CARTO 3公式サンプルは心房EAM殻、`CTACardio`直接表示は胸部CTAであり、どちらも「普通の心臓全体モデル」ではないことを実物確認して再分類した。
- `MONAIAuto3DSeg` revision `9cdf2df`と`PyTorch` revision `74f8216`を導入し、CC BY 4.0の`Cardiac TS2 - quick`（`cardiac-3mm-v2.0.0`）を公式`CTA-cardio.nrrd`へローカルCPU実行した。推論ログは12/12完了、推論56.88秒、全処理87.66秒。
- 出力から`Heart`単独の閉曲面（66,702点／133,408ポリゴン）を作成し、胸部・骨・配線・EAM点を含まない心臓全体外形としてSlicer実ウィンドウで確認した。
- 検証済みシーンは`artifacts/slicer/Whole_Heart_Anatomy_Base.mrb`（68,355,897 bytes、SHA-256 `1842dbbb6cd559b33fb57147b017cb674837aef7459e167965003639acef05d1`）、検証画像は`artifacts/slicer/Whole_Heart_Anatomy_Base.png`。証跡は`evidence/2026-08-29-whole-heart-anatomy-base.md`。
- これは3mm低解像度AI推定外形の非臨床オリエンテーション基準であり、患者固有解剖、心腔別内面、EAM、焼灼病変、治療成功を表さない。CARTO 3シーンはEAMレイヤー検証用として別に保持する。

## 2026-08-28 モーションPoC再検証

- 固定済み仮想環境（Python 3.12.10、OpenCV 4.11.0、MediaPipe 0.10.21、NumPy 1.26.4）で、合成ランドマーク／設定の既存単体試験8件とマウスrelay契約試験5件を実行し、13件すべて成功した（0.05秒）。既存の回転・パン・ズーム変換ロジックと、マウスドラッグ／ホイール／対象拒否時解放のrelay契約は現在の環境で再現している。試験では実マウスイベントを送信していない。
- 初回確認では`camera_index=0`をDirectShow、Microsoft Media Foundationのいずれでも開けず、Windows PnPのCamera／Imageクラスも0件だった。Windows 11の「モバイル デバイス」で必須の「クロス デバイス エクスペリエンス ホスト」を導入し、Pixel 9aの「接続されているカメラとして使用する」がオンであることを確認した後、同じ`camera_index=0`をDirectShowで開き、1280×720の実フレーム1枚を取得できた。フレームは保存していない。PnPのCamera／Imageクラス一覧は引き続き0件であり、接続カメラは通常のPnP列挙とは異なる経路でDirectShowへ公開されている。
- カメラ未接続状態でアプリをプレビューモード起動すると、Windows入力を送らず、理由を表示して終了コード4で安全に停止した。
- カメラ入力成立だけを根拠に実映像認識へ進める判断は撤回し、先に解決方針とADRを作成した。ADR-002のGoogle系視覚認識構成とADR-003のWindowsマウス専用relayは非臨床PoCに限ってAccepted。`TargetGuard`実装と`mouse_relay.py`のアプリ結線は、新しい目的に対する記録イベント、データ源、座標系、安全境界を確認するまで次工程候補として保留する。キーボード出力は実装しない。ADR-001の安全制御設計と臨床使用は未承認のままとする。

## 監査結論

- 現在フェーズは **Discovery / 非臨床プロトタイプ準備**。M-001の終了条件（臨床ニーズ・安全境界・関係者の承認）は未達であり、PoC完了、要求検証完了、模擬手術評価へは移行していない。
- 臨床使用は禁止。患者情報、実患者CT/DICOM、手術映像、生音声を保存・外部送信しない。
- 現在実装済みの許可対象は、取得済み心臓3Dモデルの回転、パン、ズーム、基準視点への復帰、モーション入力の有効／無効に限定する。Cラインの仮配置・調整・確定・取消・計画レイヤーは非臨床コードとして実装・検証済みだが、臨床上の操作ログとして成立させる条件は未承認であり、元データを変更しない分離オーバーレイ／イベント台帳のままとする。
- 治療機器、生命維持装置、投薬、アラーム、患者監視、任意OS操作、スライス／動画の送り・戻し・再生・停止は対象外。
- 認識不能・曖昧・複数人・遮蔽・通信断・センサー異常時は何もしない。通常のマウス、フットスイッチ、助手操作を常に残す。

## 確認済み証拠

- `README.md`、`00_Project_Charter.docx`、`docs/01`〜`12`、`registers/`、`evidence/`を2026-08-22に確認した。
- PoCの合成ランドマーク／設定単体試験を `prototypes/cmos-motion-poc` 直下で再実行し、**8件すべて成功**（0.03秒）。実行環境と試験対象ハッシュは `evidence/2026-08-22-unit-test.md` に記録した。実カメラ、照明、手袋、複数人、対象3Dビューアでの試験証拠ではない。
- 2026-08-28、Pixel 9aのWindows接続カメラ設定を有効状態で確認し、OpenCV 4.11.0のDirectShow経由で`camera_index=0`を開いて1280×720フレームを1枚取得した（保存なし）。これは入力経路の確認であり、手ランドマーク認識、ジェスチャー判定、Windows入力送信、対象3Dビューア操作の検証ではない。
- 2026-08-28、正本の要求・安全文書、既存PoC、指定された`C:\Users\HOMEA\Documents\Downloads\motion`の調査資料、MediaPipe/OpenCV/PyAutoGUI/Microsoftの公式情報を再確認し、解決方針とADR-001をDraft/Proposedで作成した。提案は、Pixelを交換可能な映像入力に限定し、認識・変換・安全判定・出力を分離して、唯一の出力許可判断をフェイルクローズ型`SafetyController`へ集約するもの。関係者未登録・未承認のため、設計確定または実装開始とは扱わない。
- 2026-08-28、ユーザー提案「Googleシリーズで揃える」を技術選択として`docs/15_adr-002-google-vision-stack.md`へ記録し、非臨床PoCに限ってAcceptedとした。標準PoCはPixel 9a＋MediaPipe Tasks Hand Landmarker VIDEOモードとし、OpenCV/DirectShowを薄いWindows映像取得アダプター、独自分類器とADR-001 SafetyControllerを安全境界とする。Legacy Hands、標準Gesture Recognizerの直接操作割当て、Pixel端末内認識は採用しない。モデル資産の版・SHA-256・SBOMとネットワーク監査は未完了であり、臨床使用または性能合格を主張しない。
- 2026-08-28、Windowsマウス専用relayを`docs/16_adr-003-windows-mouse-relay.md`で非臨床PoC向けAcceptedとし、`prototypes/cmos-motion-poc/mouse_relay.py`を追加した。Win32 `SendInput`の`INPUT_MOUSE`だけを実装し、キーボード・文字列・ホットキーAPIは持たない。偽transportによる5契約試験で、回転ドラッグ、パンのボタン切替、ズーム前解放、対象拒否時解放、プレビュー無出力を確認した。実マウス注入と対象3Dビューア接続は未実施。
- `evidence/`には単体試験記録が1件あるが、実環境の匿名化済み試験ログ、スクリーンショット、レビュー記録、構成全体のハッシュ、SBOMは未収載。
- Gitリポジトリは存在するが、現在の`master`にはコミットがなく、コミット履歴による版・変更の追跡はまだできない。
- project-local Beadsは既存`server` backend、DB `ctmc`、SQL `127.0.0.1:53544`として再確認した。既存設定のまま起動、strict read-only ping、停止、同一設定での再起動を実証し、前後ともissue 6件・ID集合SHA-256 `1f6f7c40b89ba0a1688a7aaa9ac54d94376daa7efa39f8b88bd629df7f10554e`で一致した。非loopback listenerは0、最終停止後のSQL/API listenerも0。証跡は`evidence/beads-runtime/BEADS-RUNTIME-REVALIDATION-20260823.md`。
- PM recovery Issue `pmp-25l.8.3`で、保存済み`server_stopped` event 1件を消費した。同一DB/port/configのloopback-only復旧でstrict read-only pingと同一6 IDs/hashを再確認し、exact PID停止後は対象process・SQL/API listenerとも0。event replayは既存`.8.3`一件へdedupeされ、外部gateがないためuser Inbox追加は0。証跡は`evidence/beads-runtime/BEADS-EVENT-RECOVERY-20260823.md`。横断PMが証拠を受理し、`.8.3`はclose済み。
- PM read-only HTML reference `pmp-25l.8.4`は、既存の単一集約経路へ追加した。親MDが宣言する4 childと4 cardsは同じID集合で、ready 0 / in-progress 1 / blocked 0 / completed 3、last evidenceは`.8.3`、server stateは`.8.2/.8.3`を根拠に`verified-stopped`。関連15 testsとboard validatorはPASS。第二dashboard、Beads writeback、臨床製品コード変更はなく、close権限は横断PMへ返却する。

## 未完了項目

1. 関係者台帳は、臨床責任者、医療安全、臨床工学、IT、法規、開発の必須担当を含め全員未登録。
2. A-001〜A-006はすべてOpenで、担当・期限・証拠が未設定。
3. 監査で具体化した上位ニーズ、アーミング、操作者識別、憲章訂正、実環境試験、全要求追跡をA-007〜A-012へDraft登録した。いずれも担当・期限・承認は未設定であり、完了扱いしない。
4. R-001〜R-007はすべてOpen。重大度、発生確率、担当、残留リスクが未評価。
5. ユーザーニーズは未承認で、操作者、対象ビューア／Windows構成、手術室条件、代替操作への許容切替時間が未確定。
6. 性能合格基準（誤作動率、認識成功率、最大遅延、復旧・切替時間）は未確定。開発者単独では決定しない。
7. 要求追跡表は6要求のみで、全件Draft、設計コンポーネント・試験結果が未記入。`docs/03_system-requirements.md`へ追加したCライン操作要求とAC-001〜AC-008を含む全件の双方向追跡は未実施。
8. 正式憲章はスライス送り・戻しを許可操作に含む一方、後続の正式文書は対象外としている。臨床・安全の承認前に憲章を訂正し、承認記録を残す必要がある。
9. Pixel 9aからの実カメラ入力経路は1フレーム取得まで確認済みだが、実環境での手認識、照明・手袋・複数人、故障注入、対象外ウィンドウ、代替操作切替、模擬手術の検証は未実施。
10. 署名、SBOM、構成固定、脆弱性対応、更新・ロールバックの証拠は未作成。
11. 薬機法上の該当性、PMDA相談の要否・時期、院内審査経路は未決定。
12. Cラインの仮配置、方向調整、明示確定、取消、確定ログとの境界は要求化した。一方、対象不整脈・解剖、術中ログの臨床的成立条件、データ源、座標登録、訂正責任、保存範囲、実焼灼病変像との照合方法は未確定。
13. 約30万円という費用、保険適用、地域格差に関する一次資料は未確認。
14. 3D Slicer 5.12.3の導入、組み込みメニュー日本語化、公式`CTACardio`、心臓全体外形、SlicerHeart EA Map Reader、公式CARTO 3面＋959測定点の表示確認は完了。計画Cライン、焼灼実績ログ、面カラーマップ、医学用語レビュー、各拡張モジュール本文の日本語監査は未実施。

## 安全上の主要リスク

- 意図しないジェスチャー、術者以外や複数人の動作、連続誤入力による不適切な表示操作。
- 認識不能、遅延、センサー切断・再接続による必要画像確認の遅延。
- 対象外アプリへの入力、汎用Windows操作への到達、設定改変・なりすまし。
- 通常操作への切替時間と安全な無効化が未測定。
- 手動またはモーション入力による操作ログを、実焼灼病変や治療成功と誤認する危険。
- 術前CT座標、3Dマッピング座標、カテーテル位置、表示座標の登録誤差により、記録位置が臨床上の実施位置と一致しない危険。
- 危害分析と残留リスク受容が未実施のため、現時点で臨床安全性を主張できない。

## 次のマイルストーン

**M-001 Discovery完了**を次のゲートとする。次の順序で進める。

1. 心臓全体外形とCARTO心房EAM殻を混同せず、非臨床Cライン試験の対象表面を仕様で1つに固定する。固定後、`docs/03_system-requirements.md`のAC-001〜AC-004に従い、通常マウスで仮配置、方向調整、確定、取消を1操作ずつ実装・検証する。
2. 臨床責任者と現行ワークフロー担当者が、焼灼操作ログの1イベントを何で成立させるか、そのデータ源、座標系、訂正責任を定義する。患者情報は取得しない。
3. 必須関係者を指名し、責任、期限、承認権限を台帳へ登録する。
4. 正式憲章の許可操作を後続文書と一致させ、臨床責任者・医療安全の承認を得る。
5. 患者情報を取得せず、現行ワークフロー、操作者、対象ビューア／Windows、手術室条件、代替操作を確認する。
6. R-001〜R-007および操作ログ固有リスクの重大度、確率、コントロール、検証方法、担当、残留リスクを関係部門と評価する。
7. 合意済みユーザーニーズとリスクから、全要求を試験ケースへ双方向に追跡する。
8. M-001承認後に限り、合成・非患者データによるM-002卓上PoC評価計画へ進む。

## 現在のブロッカー

- 必須関係者と承認者が未定。
- 正式憲章と最新スコープの不一致が未解消。
- リスク評価、性能合格基準、要求トレーサビリティ、検証証跡が未完成。
- UI上の確定操作は定義したが、それを臨床上の焼灼操作ログとして成立させる条件、データ源、座標登録、訂正責任は未定義。
- 右側画像相当の面カラーマップ用データ、計画Cライン、焼灼実績タグは未実装。公式CARTO 3サンプルは面スカラー配列を含まないため、カラーマップの入力仕様を別途決める必要がある。

## Pixelカメラ経路の実測確認 2026-10-09 20:19:24 +09:00
- ADB devices: 対象端末はdevice（許可済み）。
- svc usb setFunctions webcamを実行。exit code 1、出力setCurrentFunctions opId:1。有効化成立は確認できていない。
- OpenCV DSHOW: index0 read成功、mean=0.0、diff=0.0。index1/2はread失敗。実映像未成立、未完了。
- 次工程: Pixel通知のUSB設定でウェブカメラを選択した後、PC側でmean/diff再検証。映像保存・外部送信なし。


## Pixel実映像経路成立 2026-10-09 20:23:48 +09:00
- ADBから実端末設定のUSB→ウェブカメラを選択し、実プレビューの前面カメラへ切替。
- OpenCV DSHOW index1: mean=130.3058865017361、0.7秒差分=0.670107421875。実映像入力の指定完了条件を満たした。index0はmean=2.5732573784722224、diff=0で対象にしない。
- cmos-motion-pocはカメラindex1を指定して使用。Slicer結合・手認識は別工程で未実施。
- 映像ファイル保存・外部送信なし。前回の端末タップを本人だけに求めた案内は訂正。ADB許可済みなら端末UI操作はPCから実行可能だった。



## 2026-10-28 release 20261028-142746（鬼教官レビュー後の確定候補）

- 独立レビュー: 安全骨格健全（BLOCKERなし）。修正した指摘: Thumb_Up救済に4指屈曲条件追加（開いた手の誤受理を閉塞）/ Thumb_Down救済を4指屈曲+下方向必須に厳格化 / ILoveYou救済に親指伸展条件追加 / 非パネル直接commit死に経路を削除 / 死にフラグpreparing撤去 / README・overlay legendの手形表を現行割当に訂正（旧「グー=取消」は危険方向の誤り）/ 凍結ガイド文言を実動作に修正。
- 起動スクリプトPS5.1非互換（ArgumentList）を修正し再署名。startは -CameraIndex 0 必須。
- 検証: pytest 2293件全パス / 署名3点 Valid / 起動確認 Slicer 64052・認識 99020・connected / ペイロード=ソースhash一致。
- 実機確認済み経路: arm→C呼出→照準→仮置き→確認画面→release→グー→commit OK（events-20261012-clean.jsonl PERFORMED記録）。
- 未解決（既知・非ブロック）: 凍結中グーで確認ページが開きcommit拒否となる行き止まり（ガイドで誘導済み）/ frozen mirror最大~1s遅延 / dispatch_localの拒否はcommands.jsonlに載らない / recognition_lost凍結範囲がOP-013より狭い / MediaPipe 0.65閾値と実カメラ分布の乖離（救済で実用化済みだが要継続観測）。


## 2026-10-28 C:\ 廃止に伴う A:\ への完全移行 — release 20261028-180434 起動確認

- gitリポジトリを A:\ へ移行（GitHub: github.com/omusubiman5/cardiac-ct-motion-control public）。正本の registers/evidence/docs全履歴・研究物も取り込み push済み。
- パス依存設定をA:化: targets.json scene_id、storage-selection.json。runtime.json を A:バイトで software_sha256 + target_registry_sha256 再固定。
- target_registry_sha256 は canonical_hash(パース済JSON) 必須 — バイナリhashでは不一致になる（修正済み 9f16ddc2）。
- ネットワーク共有特有の2障害を修正: (a) session timeout 1.0s→10.0s（Slicer側rehashがSMBで1s超）(b) 起動 readiness 30s→180s + エンドポイント argv は UNC解決されるためポインタをUNC形式で保持すること。
- venv を A:\...\.venv へコピー（動作確認済）。release 20261028-180434: 署名3点Valid・アクティベート・起動 Slicer 41208・認識 64632・connected=True・A:MRB読込確認。
- デスクトップショートカット2点をA:リリースへ更新済み。
- 起動時 -ReleaseRoot はUNC形式必須（drive letter形式は argv比較で不一致になる）。
- 残課題: C:\ 側の残骸削除は本人判断。work/・.venv/・releases/はgit管理外（再生成可能）。
