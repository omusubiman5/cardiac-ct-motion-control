# ハンドジェスチャーイラストによる動作テスト結果

2026-10-12。本人指示「ハンドジェスチャーイラストで正常動作テストをして」に対応。

## 結果

**実運用と同じ左右反転ありでは7手形すべて20フレーム連続で期待した操作形に分類された。認識結果を使ったメニュー操作8判定も合格。左右反転なしを含む全14条件では12条件合格・2条件不合格。**

これは生成イラスト・自作試験器による自己検証。MediaPipeは実モデルで推論し、SafetyController／OperationControllerも実コードを使用した。Slicer通信だけはFakeClientであり、実Slicer画面が動いたという試験ではない。通常カメラ・Slicerには試験命令を送っていない。

## 入力と手順

- 入力：[メニュー図v2](images/hand-menu-guide-2026-10-12-v2.png)、[視点操作図](images/view-menu-test-guide-2026-10-12.png)。グー、開いた手、親指上・下、3本指、人差し指、つまみの7種類。
- 図全体では複数の手が写るため、各手の領域をメモリ内で切り出す。長辺390画素へ等倍比率で拡大縮小し、1280×720の白背景中央へ配置。位置・枠はJSONに記録。左右反転あり／なしを比較。切出し画像を患者や実手の画像と扱わない。
- MediaPipe 0.10.21、固定Gesture Recognizerモデル、VIDEOモード。各条件で認識器を新規作成し、同じ静止画像を50ms刻みの時刻で20回推論。計280フレームは280種類の独立した手のサンプルではない。
- 実モデル結果をoperation_shapeへ渡す。3本指とつまみは標準カテゴリNoneから既存規則で補完する経路。標準分類スコアと操作形を区別して記録。

## 認識結果

| 手形 | 左右反転なし | 左右反転あり |
|---|---:|---:|
| 開いた手 | 20/20 | 20/20 |
| 親指上 | 20/20 | 20/20 |
| 親指下 | 20/20 | 20/20 |
| 3本指 | 20/20 | 20/20 |
| 人差し指 | 0/20（手なし） | 20/20 |
| つまみ | 13/20、UNKNOWN 7 | 20/20 |
| グー | 20/20 | 20/20 |

この比率は同一イラストの反復結果であり、実手精度ではない。3本指は標準Noneの20フレームすべてをTHREEへ分類。つまみも標準Noneで、PINCHは独自の接触判定による。左右反転なしの人差し指は標準モデルの手検出段階で未検出。つまみの失敗は最終操作形がUNKNOWNであり、手検出なしではなかった。絵の切出し・大きさの影響もあり、実手の表裏・左右への一般化はしない。

## 操作連鎖の結果

左右反転ありの実推論結果を入力にし、仮Cあり・停止中を初期状態とするFakeClientへ接続した。形を期待値で置換していない。フレーム時刻は仮想時計、欠落は手なし入力として注入する。実アプリの撮影時間・TCP遅延・Qt描画は含まない。

| 確認 | 結果 |
|---|---|
| 開いた手の保持で受付開始 | PASS |
| 手下げ後、親指上でC編集メニューを開く | PASS |
| 親指下で選択を1項目下へ | PASS |
| 手下げ後、親指上で1項目上へ | PASS |
| グーでC編集から主メニューへ戻る | PASS |
| 手下げ後、もう一度グーで閉じる | PASS |
| 再度開いて主メニューへ戻り、3本指で視点操作を選択 | PASS |
| 上記経路で仮Cの取消・確定が送られない | PASS |

## 証跡と限界

- [試験器](../work/astra-investigation-20261011/test_current_illustrations.py)
- [入力画像hash・切出し範囲・判定内訳・操作経路JSON](../work/astra-investigation-20261011/current-illustration-results.json)
- [標準出力](../work/astra-investigation-20261011/current-illustration.stdout.txt)、[推論ログ](../work/astra-investigation-20261011/current-illustration.stderr.txt)
- 初回結果はcurrent-illustration-first-results.jsonへ保持。3本指による視点選択の確認を追加して再実行した。

この段階での未実施：実手の連続動作、動く画像による回転・パン・ズームの移動量検証、実Slicerでのメニュー／視点動作、通信タイムアウト再現。実Slicerのメニューについては下記追加試験で確認した。

製品ソース・モデル・閾値をこの試験結果に合わせて変更していない。片側のイラストを通すための閾値緩和は行っていない。

## 追加：実Slicer・実Qtパネルでのメニュー試験（2026-10-12）

本人の追問「で？」を受け、上記イラストの実MediaPipe推論結果を実Slicerへ接続して検証した。**C編集からグーで主メニューへ戻り、手なし区間を挟んでもう一度グーで閉じることを、実Qt表示と状態の両方で確認した。**

### 試験経路と対象

- 入力は[実推論結果](../work/astra-investigation-20261011/illustration-real-poses.json)の手形・ランドマークを再生。期待する手形で置き換えていない。
- 実OperationController → 実CommandDispatcher.dispatch_local → 実CStampModule／実UnifiedHandPanel。50msのQtタイマーと実時間を使用。通信はプロセス内呼出しであり、TCPやカメラの取り込みは含まない。
- 別Slicerの人工球体と仮Cで実施。IPC名、ポート18981、台帳・構成をwork内に隔離。仮Cの作成だけは試験準備としてaim／stampを直接発行したため、焼き印配置ジェスチャーの合格とは扱わない。
- 検査器と入力を自作した自己検証である。ただし表示は偽物のUIではなく、実Slicer内のQtウィジェットを取得して目視確認した。デスクトップ全体の画面撮影、実手操作、独立レビューではない。

| 実施操作 | 実Slicer・パネルで観測した結果 |
|---|---|
| 開いた手の保持 | armed=True、受付中 |
| 親指上で開く | C編集メニュー：開、先頭選択 |
| 親指下 | 選択番号0→1 |
| 親指上 | 選択番号1→0 |
| グー | C編集→主メニュー、開状態を維持 |
| 手なし区間後にもう一度グー | メニュー：閉、選択番号−1 |
| 再度開いて戻り、3本指 | mode=aim→view、メニューを閉じる |
| 確定・取消の誤発行 | commit／cancelとも0件 |

最終試行r4の8自動判定は全PASS、error=null。受付開始は状態スナップショットでも確認。パネル画像でC編集一覧→主メニュー一覧への切替、閉状態の選択解除と操作ボタン無効化を確認した。

### 失敗試行も保持

最初の試行はaimで「target window is not foreground」により拒否。r2・r3は前面取得待ちで終了し、合格ではない。r2・r3のview_selected=Trueは初期mode=viewを読んだ試験器の不備なので無効。r4ではselect_view段階を実行したスナップショットがあることを必須に修正した。

r4の前面待ち中はOSの前面PID=46088（ChatGPT）、試験PID=58408、foreground_ok=Falseを記録した。その後、通常のウィンドウ前面化が成立して安全判定を通り、試験を完遂した。前面判定の無効化・固定True化は行っていない。以前の失敗を製品の認識不良とは断定しない。

### 証跡・残課題

- [試験器](../work/astra-investigation-20261011/slicer_illustration_probe.py)
- [実行結果・命令・Qt表示文字列](../work/illustration-slicer-20261012-r4/result.json)、[試験構成](../work/illustration-slicer-20261012-r4/ready.json)
- 画面：[C編集](../work/illustration-slicer-20261012-r4/open_edit.png) → [グーで主メニュー](../work/illustration-slicer-20261012-r4/back_main.png) → [もう一度グーで閉じる](../work/illustration-slicer-20261012-r4/close.png)、[視点選択後](../work/illustration-slicer-20261012-r4/select_view.png)
- 失敗証跡：work/illustration-slicer-20261012、同-r2、同-r3のresult.json。

試験用Slicerは各試行終了時に終了。最終確認で通常Slicer PID30896の1プロセスのみ。通常シーン・仮Cへの試験命令は送らず、製品コードは変更していない。

**残る未確認は、通常アプリのカメラ→認識→TCP→Slicerという全経路での実手再検収、通信タイムアウトの原因、回転・パン・ズームの移動量。** 今回の実メニュー動作成立を、通常経路の不具合完全解消とは報告しない。

## 2026-10-12 完成指示後のTCP・障害試験

上記残件を継続。タイムアウトの直接原因として、通常Slicerログのcommit前保存履歴照会での未捕捉例外（duplicate event identity）を特定した。修正内容・通常台帳の非破壊診断・反映前後一致はdocs/39の2026-10-12節を参照。

### 確認済み自己検証

- 認識側2,240 PASS、Slicer側173 PASS、tools側5 PASS。各出力はwork/astra-investigation-20261011/completion-transport-tests.txt、completion-slicer-tests.txt、completion-tools-tests.txt。合計2,418件は自作試験を含み、実手や独立検収の件数ではない。
- 断片的な応答で要求全体の期限が延長されないこと、切断時のarmed解除、結果不明のreq記録、メニュー操作の無操作時計更新と保持継続時の非更新、古い・未来・非有限時刻拒否、台帳例外からの拒否応答を検査した。
- 別配布パスの停止判定は、2スクリプト×4入力の8判定PASS（release-filter-regression.json）。これはargvの自己検証であり、署名後実配布の起動ではない。

### 失敗・未完遂を含む実試験履歴

1. `work/illustration-tcp-20261012`：実TCPでメニュー開閉・上下・視点選択、600.687秒のstatus継続は成功し、transport_drops=0。最後の再接続assertは失敗し、総合passed=False。試験中に製品ソースを変更しており版照合拒否が考えられるが、hello拒否応答の詳細を保存していないため、その理由の確定証跡はない。最終版の合格には流用しない。
2. `work/illustration-tcp-final-20261012`：メニュー、回転・パン・ズーム、60.25秒のstatus継続、実Qt1.5秒停止による約1秒timeout・ローカル受付停止、再接続後の停止・仮C凍結は成功。台帳の検査入力を作る際に旧integrity値を含めてハッシュ計算したため、想定の重複IDより先にintegrity検査が拒否。拒否応答37.72ms・通信継続は観測したが、重複IDの試験条件不成立により総合passed=False。試験器を修正し再実行する。
3. 通常監視`work/completion-normal-20261012`と`work/completion-normal-v2-20261012`は、追加修正・停止反映により中断した。600秒合格ではない。最新版のv3監視を別ディレクトリで開始した。

実TCP試験器は`work/astra-investigation-20261011/slicer_tcp_illustration_probe.py`。Qt GUIスレッドをクライアントの同期待ちで占有しないよう、TCPクライアントと操作コードはワーカースレッド、パネル・MRML観測はQtスレッドで実行した。カメラ推論結果の再生と、その座標へ合成移動を加えた自己検証である。動画像からの実推論・実手精度を測ったとは扱わない。

### 最新の実TCP試験結果

`work/illustration-tcp-final-r2-20261012/result.json`は14判定すべてPASS、error=null。重複IDを持つ検証可能な試験行を注入し、`保存履歴を検証できません: duplicate event identity` が47.97msで返り、接続を維持した。メニュー・合成移動による実カメラ変化・60.547秒の連続status・Qt1.5秒停止時の約1秒timeout・再接続後armed=False／draft=True／frozen=Trueを確認。

この試行のcommitは、不整合台帳に対する拒否試験の1件だけ。確定成功・取消は0。通常台帳へは送っていない。実Qtパネル画像は同ディレクトリのopen_edit.png、back_main.png、closed.png、view.png。back_main.pngではグー認識と主メニューへの実表示切替を目視確認した。

### 保存途中終了→実再起動の検証

- 置換前終了：`work/completion-crash-before-r3-20261012/slicer-crash-results.json` PASS。旧1件を復元、終了時reqの保存結果なし、台帳hash不変。
- 置換後終了：`work/completion-crash-after-20261012/slicer-crash-results.json` PASS。新2件を復元、終了時reqの保存結果あり、台帳hash不変。
- どちらも新PIDの実Slicerでverifyまで実行し、試験Slicerを終了した。注入だけの成功をPASSにしない。
- before初回は前面化が成立せずaim拒否、r2は再起動後の前面条件不足でload_session拒否。結果を保持し、r3で再起動時の前面準備待機を追加して再実行した。安全判定の無効化なし。

### 通常600秒監視v3の不合格

`work/completion-normal-v3-20261012/results.json`：600.125秒、2,993サンプル。579.875秒時点に共有状態read=Noneが1回あり、接続・鮮度の全数条件はFAIL。他2,992件は接続・鮮度を満たし、最大age約0.32秒、最大RTT約141.57ms、transport_drops=0。read=Noneを通信切断が発生した証拠とは扱わないが、合格にも書き換えない。

観測器を修正し、初回read=Noneを記録した上で1ms間隔・最大3回の新規読取りを行う。過去値の再利用、tsの更新、失敗サンプルの削除はしない。再取得後にも読めない／切断／鮮度条件外なら従来同様FAIL。v4を別試行として実施中。

### 通常600秒監視v4（最終実施結果）

[結果JSON](../work/completion-normal-v4-20261012/results.json)：**600.125秒、2,993サンプルすべて接続・鮮度PASS、停止状態維持PASS**。初回読取り欠落0、再読取り0、最終読取り不能0、transport_drops=0、最大age 0.254秒、最大RTT 32.93ms。今回再読取りは発生していないので、v3の欠落原因を再現・解消した証明とはしない。

これは実Pixelカメラ・通常認識・実TCPの接続監視。実手提示の指示、意図ラベル、操作感の検収を含まない。映像保存なし、監視のための第2TCP接続なし。通常Slicerの実画面も確認し、停止中・仮Cあり・メニュー閉・主メニュー一覧を観測した。UI Automationの文字列に古い見出しが残ったため、その部分は実画面ピクセルで照合した。

終了時は通常Slicer PID30896の1つのみ。通常台帳2ファイルのhashは読取診断時と一致。新規空台帳は準備済み・未切替。**旧台帳復旧、本人の実手再検収、docs/38の残条件を含む全体完成は未達**。
# 2026-10-12 追記：本人許可による通常台帳切替

本人「勿論」を現在の仮C取消し・新台帳切替の明示許可として実行。通常Slicer PID30896の既存dispatcherで5コマンド成功。draft-0005を取消し、準備UI経路でevents-20261012-clean.jsonl／plans-20261012-clean.jsonlを有効化。旧2台帳SHA256・カメラの前後一致、新台帳0行、次回直径10mm、停止・hand所有権を確認。証跡：`work/astra-investigation-20261011/authorized-ledger-switch.json`。

Pixel認識アプリを再接続し、`work/completion-clean-ledger-connection-20261012/results.json`に15秒の通常経路観測を保存。実パネルで「停止中」「仮Cなし」「メニュー：閉」を観測。Slicerプロセスは1個。この操作は実アプリ上で成立したが、前後照合コードと期待値は自己作成。新台帳への実手C確定、再起動後の保存先維持、独立検収の代用とはしない。旧履歴は移行せず原本保持。

