# 3D Slicer PoC基盤調査証跡

日付: 2026-08-29  
対象: 非臨床PoC用3D環境と公式サンプルデータ

## 確認済み事実

1. 3D Slicer公式ダウンロードページは、3D Slicerを医療画像データの解析・理解のためのfree and open-source platformとして説明している。
2. 同ページで、2026-08-29時点のStable Releaseは`5.12.3`、Windowsビルド日は2026-07-23と表示された。
3. 公式Sample Dataドキュメントは、テスト用データをネットワーク経由で取得し、最近使用したデータをキャッシュすると説明している。
4. 公式資料には心臓系サンプルとして`CTACardio`、`CTCardioSeq`、`CTPCardioSeq`およびwhole-heart cardiac CT segmentation用サンプルが記載されている。
5. PowerShellの`Get-Command Slicer`／`Get-Command Slicer.exe`および一般的なローカル導入先の読み取り確認では、このPC上のSlicer実行ファイルまたは導入ディレクトリを検出しなかった。

## 未確認

- 公式5.12.3配布物の実ダウンロード、ローカルSHA-512照合、インストール、起動。
- 5.12.3のSample Data画面に表示される心臓データ名と、各データの実ファイルハッシュ・ライセンス・保存場所。
- Markups別レイヤー、原データ不変性、Windowsマウスrelayとの接続。
- SlicerHeartその他の拡張機能の必要性。
- 臨床適合性。今回の確認は臨床使用を支持しない。

## 次の最小検証

公式Windows安定版`5.12.3`だけを導入し、公式SHA-512照合後に起動できることを確認する。心臓サンプル取得や拡張機能追加は同じ検証へ混ぜない。

## 情報源

- [3D Slicer download](https://download.slicer.org/)
- [3D Slicer Sample Data module](https://slicer.readthedocs.io/en/latest/user_guide/modules/sampledata.html)
- [3D Slicer Volume Rendering](https://slicer.readthedocs.io/en/latest/user_guide/modules/volumerendering.html)
- [3D Slicer Training](https://www.slicer.org/wiki/Documentation/Nightly/Training)
- [3D Slicer Commercial Use](https://www.slicer.org/commercial-use.html)
