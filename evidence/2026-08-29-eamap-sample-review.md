# 右側完成イメージに対するEAMサンプル再評価

実施日: 2026-08-29

## FACT

- ユーザーが示した右側画像は、CARTO 3DマッピングおよびEnSite 3Dマッピングの表示例である。
- 表示には心房の3D表面、電気解剖学的カラーマップ、焼灼点状のタグ、計画またはブロックラインが含まれる。
- 読込済み`CTACardio`は生のCTAボリュームであり、3断面画像は表示できるが、EAM表面、LAT等のスカラー値、焼灼点タグ、計画線を含まない。
- SlicerHeartの公式`EA Map Reader`はNavX、CARTO 3、RHYTHMIAの電気解剖学マップを読み込む実験的モジュールである。
- SlicerHeart公式資料が案内するCARTO 3サンプル`Carto3_EA_map.zip`を一時領域へ取得した。
- ZIP内容は`1-OG.mesh`と`EA_map_car.txt`の2ファイルであり、サイズは737,848 bytes、SHA-256は`26ecb532bcb90970871b9624cc53d3cf964cb2bde26658b087b642d17de694d4`だった。
- SlicerHeart revision `917f132`と依存拡張（SlicerIGT `cea41ad`、MarkupsToModel `0be6421`、SlicerIGSIO `f3d85ff`）を3D Slicer 5.12.3へ導入した。
- 初回再起動ではWindowsのアプリケーション制御ポリシーが`qSlicerKretzFileReaderModule.dll`と`qSlicerVolumeReconstructionModule.dll`を遮断した。Windows側の安全機能は変更せず、検証対象をSlicerHeartの`qt-scripted-modules`だけに限定して正常起動を確認した。元設定は`Slicer-34627.ini.before-eamap`へ退避した。
- 公式EAMapReader revision `917f132`には、CARTO 3経路で順に再現する3つの実装不整合があった。(1) UI名`importCarto3RadioButton`に対してコードが`importCartoRadioButton`を参照、(2) `qt`未import、(3) 点データの分割式`[ \t]*`が空文字へ一致。各失敗を観測後、ローカル導入物の該当箇所だけを修正した。元Pythonファイルは`EAMapReader.py.before-carto-fix`へ退避した。
- 修正版をSlicer実行環境で再読込し、`CARTOmesh_1-OG`（9,957 vertices、19,909 triangles）と`CARTOpoints_1-OG`（959 control points）を生成した。3D面を灰色、測定点を赤で実ウィンドウ表示し、点数959をSlicer内部で再確認した。
- 公式サンプルの`.mesh`には表面スカラー配列が0件だった。一方、959点にはBipolar、Unipolar、LATが説明属性として読み込まれる。したがって「3D面＋測定点」は再現済みだが、右側画像のようなLAT／電位の面カラーマップや焼灼実績点、計画線はこのサンプルだけでは再現されない。
- 検証済み表示を`artifacts/slicer/CARTO3_EA_Map_Demo.mrb`（1,112,443 bytes、SHA-256 `55dfeb86ef2aa3cc35bdf2f031033968bc01691d33b6dfebff59c883046631be`）へ保存し、Slicer画面上で`scene_saved True`を確認した。MRB内部に`CARTOmesh_1-OG.vtk`と`CARTOpoints_1-OG.mrk.json`が収載されていることも確認した。公式非患者サンプルだけを含む非臨床デモである。
- 修正後`EAMapReader.py`を同梱`PythonSlicer.exe -m py_compile`で検査し、終了コード0を確認した。

## DIFFERENCE

|レイヤー|CTACardio|右側の完成イメージ|
|---|---|---|
|元画像|CTAボリューム|任意。CTは位置合わせ用に併用可能|
|操作対象|2D断面／ボリューム|左房等の3D電気解剖学的表面|
|電気情報|なし|LAT／電位等の表面スカラー|
|計画線|なし|独立した線レイヤー|
|実施ログ|なし|独立した点タグ／イベント台帳|

## HYPOTHESIS

右側の操作イメージを非臨床PoCで再現する最小基盤は、`SlicerHeart EA Map Reader + CARTO 3形式`である。公式サンプルは3D面と測定点の入力・表示試験には使えるが、面カラーマップ、焼灼実績点、計画線の完成見本には不足する。`CTACardio`は将来のCT解剖との位置合わせ検証に使えるが、最初の操作画面の主データにはしない。

## PREDICTION / FALSIFIER

- 観測: 3D表面と959測定点は作成された。測定点のBipolar／Unipolar／LAT属性は読めたが、表面スカラー配列は0件だった。
- 判定: 「EA Map ReaderでCARTO 3面と測定点を構成できる」はSUPPORTED。「公式サンプルだけで右側画像の面カラーマップまで再現できる」はFALSIFIED。

## NEXT DECISION

次の独立実験は、保存済み非臨床シーン上へ原モデルを変更しない`計画Cライン`レイヤーを1本だけ追加し、通常マウスで作成・表示・削除・保存・再読込できることを確認する。術中実績ログとハンドモーション入力は混ぜない。

## 公式資料

- `https://github.com/SlicerHeart/SlicerHeart/blob/master/Docs/EAMapReader.md`
- `https://github.com/SlicerHeart/SlicerHeart/blob/master/README.md`
- `https://github.com/SlicerHeart/SlicerHeart/releases/download/TestingData/Carto3_EA_map.zip`
