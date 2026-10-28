# ジェスチャーテスト図・生成記録

2026-10-12。imagegenスキル、組込image_gen使用。参照正本：docs/47・40。図は説明用でありテスト結果ではない。

最終4枚はdocs/テストシナリオ20261012に保存。初期生成と不採用編集版は生成先に保持し、計画MDは最終版だけ参照する。配置に3本指や親指を使うように見えた計画図は不採用とし、③は工程概要図として再生成した。配置・編集の手形は②へ参照する。

- gesture-test-01-start-view-2026-10-12.png：C:\Users\HOMEA\.codex\generated_images\01a12073-ab9e-7bb0-84f3-a42f422e5752\exec-523d3aac-ba39-4bea-a9ec-5b403983822b.png
- gesture-test-02-cstamp-2026-10-12.png：C:\Users\HOMEA\.codex\generated_images\01a12073-ab9e-7bb0-84f3-a42f422e5752\exec-fef3cf5f-7600-4ed6-bfc6-5d8fe480d7c7.png
- gesture-test-03-plan-record-2026-10-12.png：C:\Users\HOMEA\.codex\generated_images\01a12073-ab9e-7bb0-84f3-a42f422e5752\exec-14a6b783-85d3-4e16-905e-80a2945d69fc.png
- gesture-test-04-safety-back-2026-10-12.png：C:\Users\HOMEA\.codex\generated_images\01a12073-ab9e-7bb0-84f3-a42f422e5752\exec-34edb8c3-8650-4182-82ab-e70d0b0ccb5a.png

## 初期生成プロンプト

### 1

```text
Use case scientific-educational. Make a polished Japanese illustrated test instruction poster, landscape 1536x1024 or larger, navy headings, white background, pastel cards, large legible Japanese sans serif. Every numbered panel pairs anatomically accurate large hand illustrations with a simplified dark Slicer sidebar and synthetic sphere showing expected response. Exactly five digits per hand. Three-finger gesture is INDEX/MIDDLE/RING extended, thumb and little folded; NOT ILoveYou. Thumb UP moves selector UP, thumb DOWN moves it DOWN, wrist from SIDE. Other gestures wrist from BOTTOM. Index only / V / pinch / fist distinct. Hand only main path, no mouse except specified size setting/restart/injection. This is explanatory illustration, not test evidence. Footer verbatim 「説明図・テスト未実施｜非臨床デモ｜基準直径5mm」. Timing strip 「開始1.5秒｜離散操作約0.5秒｜操作の間は手を1秒下げる」. No invented gesture, pushing hand against screen, clinical claim, real patient model.
Title 「① 開始・メニュー・視点のテスト」. Six panels, 3 columns x2rows.
1 「受付開始」 OPEN PALM1.5sec then handlowered, UI 「停止中 → 受付中」, caption 「開始だけでは動かない」.
2 「メニューを開く」 THUMB UP, sidebar 「メニュー：開」 and 「▶ 視点操作」「C焼き印」「計画・記録」, highlight OPEN and selector.
3 「上下・決定」 separate UP thumb/up arrow 「親指上＝上」, DOWN thumb/down arrow 「親指下＝下」, then accurate THREE fingers 「3本指＝選択」.
4 「回転」 after view mode selection, OPEN PALM up/down/left/right arrows, sphere rotates, 「開いた手を上下左右」, UI 「現在の操作：視点操作」.
5 「パン・ズーム」 split: INDEX ONLY up/down/left/right sphere translates; PINCH thumb/index touching, WHOLE HAND vertical up 「拡大」 down 「縮小」, 「つまんだまま手全体を上下」. Never fingertips separating.
6 「停止」 open menu 「▶ 操作を停止」 THREE fingers select; UI 「停止中」, sphere static, 「停止後は手を動かしても無作用」.
Small ref 「H-01・V-01｜受付・メニュー・視点・停止を画面で確認」.
```

### 2

```text
Use case scientific-educational. Make a polished Japanese illustrated test instruction poster, landscape 1536x1024 or larger, navy headings, white background, pastel cards, large legible Japanese sans serif. Every numbered panel pairs anatomically accurate large hand illustrations with a simplified dark Slicer sidebar and synthetic sphere showing expected response. Exactly five digits per hand. Three-finger gesture is INDEX/MIDDLE/RING extended, thumb and little folded; NOT ILoveYou. Thumb UP moves selector UP, thumb DOWN moves it DOWN, wrist from SIDE. Other gestures wrist from BOTTOM. Index only / V / pinch / fist distinct. Hand only main path, no mouse except specified size setting/restart/injection. This is explanatory illustration, not test evidence. Footer verbatim 「説明図・テスト未実施｜非臨床デモ｜基準直径5mm」. Timing strip 「開始1.5秒｜離散操作約0.5秒｜操作の間は手を1秒下げる」. No invented gesture, pushing hand against screen, clinical claim, real patient model.
Title 「② C配置・方向・確定のテスト」. Eight panels, 4columns x2rows. Top strip 「モード変更後は親指上でメニューを開き直す」.
1 「照準を選ぶ」 THUMB UP opensmenu, thumb上下 choose 「C焼き印」, THREE select, UI 「現在の操作：照準」.
2 「1本指で照準」 INDEX ONLY cyan cursor on sphere 「照準：有効」, outside redX 「表面外は無効」.
3 「2本指で仮配置」 V index/middle, cyanC on sphere, dimension5mm, UI 「仮Cあり・未確定」, 「まだ保存されない」.
4 「位置を調整」 reopen menu select thismode, INDEX ONLY moves on sphere, sameC follows, 「同じ仮Cを表面上で動かす」.
5 「開口方向」 select 「開口方向を調整」, OPEN PALM LEFT/RIGHT only, cutgap of C ROTATES IN ITS PLANE around fixedcenter; sphere and normalfixed. 「左右：切れ目だけ面内回転」. NO vertical tilt here.
6 「面の傾き」 select 「傾きを調整」, OPEN PALM UP/DOWN, 3D Cplane tilts, normalchanges, center5mmfixed. 「上下：Cを載せる面を傾ける」. Visually distinct from5.
7 「確認画面」 select 「確定へ進む」 via THREE, UI 「対象・仮C ID・版・5mm・方向」, 「この段階は保存0件」; handlowered.
8 「新しい3本指で確定」 hand lowered→fresh THREE, cyanC becomes redcommitteddot, UI 「保存成功：1件」, 「手を下げてから決定」.
Small ref 「H-02・V-02〜04・09〜10」. Do not mix fistcancel in this path.
```

### 3

```text
Use case scientific-educational. Make a polished Japanese illustrated test instruction poster, landscape 1536x1024 or larger, navy headings, white background, pastel cards, large legible Japanese sans serif. Every numbered panel pairs anatomically accurate large hand illustrations with a simplified dark Slicer sidebar and synthetic sphere showing expected response. Exactly five digits per hand. Three-finger gesture is INDEX/MIDDLE/RING extended, thumb and little folded; NOT ILoveYou. Thumb UP moves selector UP, thumb DOWN moves it DOWN, wrist from SIDE. Other gestures wrist from BOTTOM. Index only / V / pinch / fist distinct. Hand only main path, no mouse except specified size setting/restart/injection. This is explanatory illustration, not test evidence. Footer verbatim 「説明図・テスト未実施｜非臨床デモ｜基準直径5mm」. Timing strip 「開始1.5秒｜離散操作約0.5秒｜操作の間は手を1秒下げる」. No invented gesture, pushing hand against screen, clinical claim, real patient model.
Title 「③ 計画・記録のテスト」. Six workflow cards,3columns x2rows. Each repeats gesture key thumbup open / thumbupdown navigate / threeindexmiddlering select. Header 「親指上：メニュー｜親指上下：項目移動｜3本指：選択｜グー：一段戻る」. Illustrate sequence not just text.
1 「新規計画」 UI 計画・記録/PLANNED, 2planned cyanCs, 「新規計画 → 区分選択 → 予定を配置 → 保存」, expected 「実績は増えない」, H-04.
2 「計画を訂正」 locked旧版 and新版, add/delete/move/rotate icons, 「追加・削除・移動・方向 → 新版保存」, 「旧版は変わらない」, H-05.
3 「予定に合わせる」 ghostoutlineC anddraft, differencearrows, 「次予定 → 仮配置 → 位置・方向調整 → 明示確定」, 「ゴースト1件・実績1件」, H-06. No autosnap.
4 「順序・スキップ・計画外」 reorderedlist, skippeditem, separate outofplanC, 「対象選択 → 理由 → 明示実行」, 「理由を記録／計画外は独立確定」, H-07・08.
5 「記録の撤回・訂正」 oldeventlocked linksnewaudit, confirmation and THREE hand release/re-present, 「確定点 → 理由 → 独立確認」, 「元記録は上書きしない」, H-09.
6 「保存・読込・再表示」 3numbereddots→3Coutlines reconstructed, 「3件確定 → C再表示 → 保存 → 再起動 → 読込」, 「3件の位置・方向・順序を再現」, small 「再起動は担当者」, H-03.
```

### 4

```text
Use case scientific-educational. Make a polished Japanese illustrated test instruction poster, landscape 1536x1024 or larger, navy headings, white background, pastel cards, large legible Japanese sans serif. Every numbered panel pairs anatomically accurate large hand illustrations with a simplified dark Slicer sidebar and synthetic sphere showing expected response. Exactly five digits per hand. Three-finger gesture is INDEX/MIDDLE/RING extended, thumb and little folded; NOT ILoveYou. Thumb UP moves selector UP, thumb DOWN moves it DOWN, wrist from SIDE. Other gestures wrist from BOTTOM. Index only / V / pinch / fist distinct. Hand only main path, no mouse except specified size setting/restart/injection. This is explanatory illustration, not test evidence. Footer verbatim 「説明図・テスト未実施｜非臨床デモ｜基準直径5mm」. Timing strip 「開始1.5秒｜離散操作約0.5秒｜操作の間は手を1秒下げる」. No invented gesture, pushing hand against screen, clinical claim, real patient model.
Title 「④ 戻る・取消・誤操作防止のテスト」. Six panels,3columns x2rows.
1 「グーで一段戻る」 accurateFIST between UIchain 「確認 → C編集 → 主メニュー → 閉」, releasegapicons betweeneach. 「毎回、手を下げて出し直す」; secondshortchain 「計画の一覧 → 計画・記録 → 主メニュー → 閉」, 「保持だけで多段移動しない」, H-11.
2 「閉じた後のグーは取消」 boldamberstate 「メニュー：閉／仮Cあり」 plus freshFIST, cyanC disappears but redcommitteddotsstay. 「取消を試す時だけ新しく提示」, UI 「仮Cなし・保存0件」, H-02. Strongly distinguishfrom1.
3 「保持・途中形」 THREE held in確認 no-save, then lower→freshTHREE oneevent. 「保持の続きで確定しない」. Partlyfoldedhand 「UNKNOWN＝無作用」, V-05・06/H-11.
4 「遮蔽・複数手・対象喪失」 handcovered /2hands /focusotherapp, cyanC frozen, UI 「停止／凍結」, 「Cの位置・方向・記録は変わらない」, H-10.
5 「復帰だけでは再開しない」 handreturns Cstillfrozen→OPEN PALM1.5→lower→thumbmenu select 「凍結した仮Cの編集を再開」 withTHREE. 「受付開始 → 手下げ → 編集を再開」, 「明示再開後だけ編集」, H-10/V-07.
6 「保存失敗・返信不明」 UI 「未確定／結果不明」 draftkept, menu 「結果照会」 THREE select, oldeventIDsingleledgerrow, 「障害の注入・解除は担当者」「照会で重複保存しない」, H-12.
Extra bottom strip 「反復：元480提示＋補助80＋240｜接続：通常操作600秒・段階再生600秒」.
```

## 第1回編集

### 1

```text
Edit this Japanese test poster precisely. Preserve layout/panels 2,3,4,5,6 except these changes: top right has 「手のジェスチャーだけで3Dビューアを操作する練習です」 acceptable. Panel1 handlowering illustration is okay but explicitly means REMOVE hand from camera, caption 「手をカメラの外へ1秒下げる」. All three-finger hands must have exactly index/middle/RING extended, little+thumb folded. Keep footer instructionillustration untested. No other changes.
```

### 2

```text
Edit this poster preserving all eight panels and style. Important correction: panel6 paragraph currently incorrectly says choose 開口方向. Replace it with exact 「『傾きを調整』を選び、開いた手全体を上下に移動する」. Draw front-facing open palm in panel6 with STRAIGHT up/down TRANSLATION arrows, ghosthand higher/lower same orientation. Do NOT show turning hand palmup/down. Keep 3DCplane tilting as consequence. Panel5 replace left/right palmturning with ONE front-facing open hand and straight horizontal double-arrow +ghost positions, text exact 「開いた手全体を左右に移動」, 「切れ目だけが面内回転」. Do NOT show wrist twist. Panel1 simplify menu to only 「メニュー：開」「▶ C焼き印」 (a main menu, do not put edit commands on same menu). Show both actual thumbUP and thumbDOWN for selection, not onlyUP pointing near opposite labels. Panel4 fix false caption saying centerunchanged: position adjustment CHANGES center. Caption 「中心は移動／直径5mmは保持」. Panel8 committedred dot remainscorrect. Keep actual3finger index/middle/ring. Maintain all timing,5mm,footer.
```

### 3

```text
Edit this Japanese six-card testposter. Preserve title,6card purposes,testrefs,footer. Correct misleading action gestures: placement NEVER uses threefinger; placement is INDEX aim→release→V (index/middle) draft. In cards1/3 where caption says3本指で予定を配置 or3本指仮配置 replace with accurate INDEX+V pair and caption 「1本指で照準→2本指で仮配置」. Orientation/position adjustment is actualmotion not repeated3finger: card3 next step should show INDEX movement plus OPEN PALM LEFT/RIGHT and UP/DOWN, caption 「位置・方向を調整」; threefinger remainsonlymenuselection/independentconfirmation.
Make all planned/draft C objects cyan C SHAPES with cut gap (not solid blue dots), committedperformance remains reddots/Creconstructed. Header show separate thumbUP and thumbDOWN anatomically (notUPthumb beside both arrows) with exact 「親指上＝上」「親指下＝下」.
Remove fabricated menu entries such as reasoninput and fake authorC1/C2; generic sidebar 「メニュー：開」「計画・記録」「▶ 選択項目」 is enough; section captions conveyactualtask. No pretendapplicationexactfullmenus.
Card5 replace3本指×3回 misleading with 「対象・理由を選択→手を下げる→独立確認」 and ONE3finger forconfirm. No fabricatedOKdialog.
Card6 laststep split: monitorrestart caption 「再起動は担当者」 then thumbmenu/3finger 「読込は手で選択」, do not label読込asマウス操作. Readonlyreconstructed3Cs with1,2,3. Saveentry selection3fingeracceptable. Keep expectedcounts/oldversionunchanged/reasons. No clinicalclaims.
```

### 4

```text
Edit this poster preserve6panels except precisecorrections. Remove top-right slogan claiming safe accurate medicaldiagnostics; replace 「実手テストの確認手順」 ONLY.
Panel3 unknown icon currentlylooks2.5fingers possiblyvalid3: instead hand partly covered by cloth, label 「不明・遮蔽：意図しない操作0」; unknownhandnotnovelgesture.
Panel5 fourthstep currentlywrong thumb caption 「親指で選択」. Replace with 「親指上でメニューを開く → 親指上下で『凍結した仮Cの編集を再開』を選ぶ → 手を下げて3本指で決定」. Draw both thumbUP/DOWN fromwristSIDE, and correct3fingers. Keep openpalm1.5sec start,lower1sec, frozenCuntilresume.
Panel6 resulttable wronglysays unknownsaved0withdefiniteeventID. Replace with two clearlydistinctsmallresultboxes: 「保存失敗：未確定・仮C維持」 and 「返信不明：照会で結果を確認」. Below 「保存済みなら元のイベントID／照会で追加保存0件」. Never assertunknown0save, automaticretry, or guaranteed1record ifnotyetconfirmed.
Panel2 should show one cyan draft Cbefore and redcommitteddots, draftCdisappears, oldreddotsunchanged. Keep clearメニュー閉/仮Cあり and newFISTcancel semantics. Keep panel1 singleback+release and footer unteseed5mm.
```

## 追加修正

### 図2

```text
Change ONLY panel1 thumb-down caption: it currently wrongly says 「親指下（戻る）」. EXACT correction is 「親指下（選択を下へ）」. Keep thumbUP caption 「親指上（メニューを開く）」. Thumb-down never performs BACK; fistdoesback. No other changes. Keep all8panels unchanged.
```

### 図3

```text
Make ONLY these exact hand corrections. In card1 below label「1本指で照準→2本指で仮配置」 the first illustrated hand is incorrectly THUMBS UP. Replace it with INDEX FINGER ONLY pointing UP, wrist from bottom, thumb folded sideways across palm and middle/ring/little folded; keep nextVsign. In card3 below same label also replace firstTHUMBUP with INDEX ONLY wristbottom. In card3 「位置・方向を調整」 currentlythumbUP onleft: replace with INDEX ONLY pointing UP, wristbottom and straightmotionarrow; keep openpalm movement next. Card4 labeled親指上下 currentlyonlyupthumb besidearrows: draw up AND down thumb correctly, or keep one upthumb with title 「親指上／下」 and downthumbsmall. Do not change any text/otherpanel/shape. Threefinger is index/middle/ring. No thumbup used asindex.
```

### 図4

```text
Only geometry correction, preservealltextandhands. Cyan uncommitteddraftcurrentlydrawnasdot must instead be cyan C SHAPE WITH VISIBLE OPEN GAP in allstateinsets where 仮C mentioned: panel1helddraft, panel2beforecancel, panel3confirmhelddraft, panels4/5 frozenandstart states. Redcommitteddots remainreddots; panel2aftercancel onlyreddots, cyanCdraftabsent. SameCcenterorientationbefore/afterfrozen. Do not redrawhands/text.
```

## 図③の再生成（最終採用）

```text
Create a NEW Japanese illustrated test poster, landscape1536x1024, large navytitle 「③ 計画・記録のテスト」, whitebackground6pastelcards3columns2rows. Professional clear educationalstyle. Use cases H-03〜09. This is explanatorynot screenshot. Header gesturekey: accurate side-wrist THUMB UP 「メニューを開く／上へ」; THUMB DOWN 「下へ」; THREE INDEX/MIDDLE/RING fingers extended with little+thumbfolded 「項目を選択」; FIST 「一段戻る」. EXACTLY five digits. Show these FOURhands only in header. DO NOT DRAW HANDS INSIDE THE SIX CARDS. Inside cards show synthetic sphere, clearly open cyan C shapes, labels/state examples and process arrows. This prevents implying menu selection3fingers is placement gesture. Subheader exact 「配置・位置・方向の手の動きは②を使用。3本指はメニュー選択と独立確認。」 Each card has one generic little darksidebar 「メニュー：開」「計画・記録」, labelsareMOCK examples.
1 「新規計画 H-04」. Process 「新規計画 → 区分選択 → 予定を配置・編集 → 保存」. Sphere2cyanplannedCs, PLANNEDtag, expected 「実績は増えない」.
2 「計画改訂 H-05」 process 「追加・削除・移動・方向変更 → 新版保存 → 旧新版を比較」, lockedoldversion vsnewversion with4differencedrawings. 「旧版は変わらない」.
3 「予定追従 H-06」 process 「次予定 → 仮配置 → 位置・方向を調整 → 独立確定」. singleghostoutlineC andsingledraftC convergebyMANUALadjustment toperformedredpoint. 「ゴースト1件・実績1件」「自動吸着しない」.
4 「順序・スキップ・計画外 H-07・08」 process 「対象 → 理由 → 明示実行」; orderedlist withskipmarker and separateoutofplanC. 「理由を記録」「計画外のCは別に独立確定」.
5 「記録撤回・訂正 H-09」 process 「確定点を選択 → 理由 → 手を下げる → 独立確認」; oldeventlocked links newauditrow; correctionbranchnewdraftC→independentconfirmation. 「元記録は上書きしない」.
6 「保存・再読込 H-03」 process 「3件確定 → C再表示 → 保存 → 再起動 → 手で読込」, three red numbered points before, three cyanCs numbered1/2/3after atsameplaces. 「再起動は担当者」「位置・方向・順序を再現」.
Footer 「説明図・テスト未実施｜非臨床デモ｜基準直径5mm」 and 「選択の間は手を1秒下げる」. DO NOT depict thumb up as index, nor multiple3fingers for placement. NO hands in cards, headerhands only. No clinical claims, logos, mouse-basedload, invented author/reason values.
```

## 目視照合

親指上下と選択方向、人差し指／2本指／3本指、開始1.5秒と操作間1秒、左右移動の開口回転と上下移動の傾き、位置変更時の中心移動、確認0保存／独立確定1保存、グーの階層戻り／閉状態の取消、自然再開禁止、保存失敗／返信不明の区別を照合した。UIは模式図・項目抜粋。実UI全文や認識結果の証明ではない。

