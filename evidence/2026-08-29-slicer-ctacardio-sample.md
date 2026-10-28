# 3D Slicer CTACardio公式サンプル読込証跡

実施日: 2026-08-29  
対象環境: Windows / 3D Slicer Stable 5.12.3  
用途: 非臨床プロトタイプの表示基準データ

## Fact Lock

- 3D Slicer本体の`Sample Data`画面に`CTACardio`、`CTP Cardio Sequence`、`CT Cardio Sequence`が表示された。
- 最小検証として静的CTAボリューム`CTACardio`だけを選択した。拡張機能は追加していない。
- Slicerは61.1 MBの`CTA-cardio.nrrd`を取得し、画面ログに`チェックサムOK`、`ロードが完了しました`を表示した。
- データモジュールのシーンツリーに`CTACardio`ノードが1件表示された。
- 横断・冠状・矢状の3断面で画像が表示された。
- 実患者データ、患者情報、手術画像、音声は使用・保存していない。

## Evidence Ledger

| ID | 証拠 | 観測方法 | 結果 |
|---|---|---|---|
| E01 | Slicer本体に`CTACardio`ボタンが存在 | 実ウィンドウのSample Data画面 | 確認 |
| E02 | 取得とSlicer内チェックサム検証 | Slicer画面ログ | 61.1 MB取得、チェックサムOK |
| E03 | シーンへのロード | Slicer画面ログとデータモジュール | `CTACardio`ノードを確認 |
| E04 | 画像表示 | 実ウィンドウ | 3断面すべて表示 |
| E05 | ローカルファイルハッシュ | PowerShell `Get-FileHash -Algorithm SHA256` | 公式期待値と一致 |

## ファイル同一性

- 公式データ名: `CTA-cardio.nrrd`
- Slicerノード名: `CTACardio`
- ローカル保存先: `C:\Users\HOMEA\AppData\Local\slicer.org\Slicer\cache\SlicerIO\CTA-cardio.nrrd`
- サイズ: 64,043,308 bytes
- 期待SHA-256: `3b0d4eb1a7d8ebb0c5a89cc0504640f76a030b4e869e33ff34c564c3d3b88ad2`
- 実測SHA-256: `3b0d4eb1a7d8ebb0c5a89cc0504640f76a030b4e869e33ff34c564c3d3b88ad2`
- 判定: 一致

## 出所

- 3D Slicer本体の公式`SampleData.py`に、`CTACardio`、ファイル名、SHA-256付き取得先が定義されている。
- 取得URL: `https://github.com/Slicer/SlicerTestingData/releases/download/SHA256/3b0d4eb1a7d8ebb0c5a89cc0504640f76a030b4e869e33ff34c564c3d3b88ad2`
- ソース定義: `https://github.com/Slicer/Slicer/blob/main/Modules/Scripted/SampleData/SampleData.py`

## Result Classification

**SUPPORTED**

仮説「3D Slicer 5.12.3内蔵の`CTACardio`を公式ハッシュ一致の状態で取得し、ローカルシーンへ表示できる」は支持された。

これはサンプルの取得・同一性・表示成立の確認であり、次を証明しない。

- 心腔、血管、焼灼部位等のセグメンテーション精度
- 術前CTと術中座標の登録精度
- 焼灼操作ログまたは実焼灼病変の可視化
- 臨床妥当性、医療安全性、治療結果

## データ取扱い判断

サンプル単体の再配布ライセンスを今回確認した公式定義から確定できなかったため、データ本体はプロジェクトリポジトリへ複製しない。Slicer管理下のローカルキャッシュだけに保持し、本証跡には出所、保存先、サイズ、ハッシュのみを記録する。

## 次の一手

原CTを変更せず、別のMarkupsノードを1件作成できることを非臨床で確認する。焼灼計画線の意味、座標系、訂正責任は臨床責任者の定義前に確定扱いしない。
