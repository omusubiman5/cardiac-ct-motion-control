# 心臓全体の非臨床3D基準モデル作成

実施日: 2026-08-29

## FACT

- Slicer標準`CTACardio`は心臓を含む胸部CTAであり、完成済みの心臓単独モデルではない。公式`CTACardio.mrb`を展開すると、CTボリューム2件だけで、モデル／セグメンテーションは含まれていなかった。
- SlicerHeart公式CARTO 3サンプルは心房電気解剖学マップの殻と測定点であり、一般的な心臓全体の解剖モデルではない。
- 3D Slicer 5.12.3へ`MONAIAuto3DSeg` revision `9cdf2df`と依存`PyTorch` revision `74f8216`を導入した。
- `MONAIAuto3DSeg`の`Cardiac TS2 - quick`はTotalSegmentatorV2由来、CC BY 4.0、3mm低解像度プレビュー用で、公式サンプル入力として`CTACardio`を指定している。
- ローカルCPU推論で`cardiac-3mm-v2.0.0`を公式`CTA-cardio.nrrd`へ適用した。推論ログは12/12完了、推論56.88秒、全処理87.66秒を記録した。
- 出力16構造から`heart`だけを残し、表示名を`Heart`へ正規化した。閉曲面は66,702点、133,408ポリゴン。
- 3D Slicer実ウィンドウで、胸部、骨、配線、CARTO測定点を含まない心臓全体の外形を単独3D表示し、目視確認した。
- シーンを`artifacts/slicer/Whole_Heart_Anatomy_Base.mrb`へ保存した。68,355,897 bytes、SHA-256 `1842DBBB6CD559B33FB57147B017CB674837AEF7459E167965003639ACEF05D1`。
- 検証画像を`artifacts/slicer/Whole_Heart_Anatomy_Base.png`へ保存した。91,038 bytes、SHA-256 `D85C60AA80BAD9492528D5825E5E3D7FAB9C3C090ED4F5EBD3C3BCE4695727B0`。

## DIFFERENCE

|候補|実物確認結果|採否|
|---|---|---|
|CARTO 3公式サンプル|心房EAM殻＋959測定点|EAM検証用に保持。心臓全体の基準には不採用|
|CTACardioの直接ボリュームレンダリング|胸部、体表、骨、配線が混在|心臓単独モデルとして不採用|
|Cardiac TS2 quickの`heart`|心臓全体の外形を単独閉曲面化|非臨床の解剖基準として採用|

## LIMITATION

- これは3mm低解像度のAI推定外形であり、患者固有解剖、心腔別モデル、左房内面、電気解剖学マップ、焼灼病変、伝導ブロック、治療成功を表さない。
- Cラインを臨床上どの心腔・面・座標へ配置するかは未定義。モデル上へ線を描けることと、医学的に正しい焼灼計画であることを混同しない。
- 非臨床プロトタイプ専用。臨床判断、治療、患者データには使用しない。

## RESULT

`Cardiac TS2 - quick`から心臓単独外形を生成・保存・再読込・実画面表示できることはSUPPORTED。これを心臓全体の非臨床オリエンテーション基準とし、CARTO 3シーンはEAMレイヤー検証用として別に保持する。

## NEXT DECISION

次の一手は、どの解剖表面を非臨床Cライン試験の対象にするかをプロジェクト仕様で固定すること。固定後、そのモデルを変更しない独立MarkupレイヤーとしてCライン1本の作成・削除・保存・再読込を検証する。

## 公式資料

- `https://github.com/lassoan/SlicerMONAIAuto3DSeg`
- `https://github.com/lassoan/SlicerMONAIAuto3DSeg/blob/main/MONAIAuto3DSeg/Resources/Models.json`
- `https://github.com/Slicer/Slicer/blob/main/Modules/Scripted/SampleData/SampleData.py`
