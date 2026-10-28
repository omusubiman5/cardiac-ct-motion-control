---
artifact: adr
version: "1.0"
created: 2026-08-29
status: accepted
---

# ADR-004: 3D Slicerを非臨床PoCの標準3D環境とする

## Status

Accepted（公式サンプルを使う非臨床PoCに限定。臨床使用の承認ではない）

**Date:** 2026-08-29  
**Deciders:** ユーザー、開発担当（臨床・医療安全・IT・法規の承認は未取得）

## Context

本プロジェクトは、術前CT由来の心臓3Dモデル上での焼灼計画、術中の焼灼操作ログ、計画対実績レビュー、ハンドモーション操作を検証する必要がある。エンジニアリング資源は限られており、表示、セグメンテーション、座標管理、拡張機構をゼロから構築することは目的に対して過大である。

3D Slicerは医療画像の可視化・処理・セグメンテーション・位置合わせ・解析を行うフリーかつオープンソースのプラットフォームである。公式の`Sample Data`モジュールはテスト用データをネットワーク取得でき、公式資料には`CTACardio`、`CTCardioSeq`、`CTPCardioSeq`およびwhole-heart cardiac CT segmentation用サンプルが記載されている。

## Decision

3D Slicerを、本プロジェクトの非臨床PoCにおける標準3D環境として積極利用する。

最初のローカル検証対象は、2026-08-29時点の公式Windows安定版`5.12.3`とする。取得時には公式ダウンロードページ掲載のSHA-512と照合する。Preview版は最初の検証へ混ぜない。

最初の構成は次に限定する。

```text
公式3D Slicer 5.12.3 Windows安定版（配布物SHA-512を照合）
  -> 出所・ライセンス・ハッシュを記録した公式心臓系Sample Data
  -> Slicer標準の表示／セグメンテーション／Markups
  -> 原画像・原モデルとは別の計画オーバーレイ
  -> 原画像・計画とは別の操作ログオーバーレイ
  -> ADR-003 Windowsマウスrelayによる回転・パン・ズーム
```

PoCでは実患者CT／DICOMを使用しない。Sample Dataの取得は再現可能な準備作業として扱い、データ名、URLまたはSlicer内識別子、提供元、ライセンス、ファイルハッシュ、取得日を証跡へ記録する。

原CT／ボリュームと生成した心臓モデルを入力資料として不変に保つ。計画線・点と焼灼操作ログは別ノード／別レイヤーにし、色、名称、凡例、エクスポート先を分離する。操作ログを実病変像、完全ブロック、治療成功の証明として表示しない。

AIは、Slicer拡張の設計、コード生成、テスト、文書化、証跡管理を支援するエンジニアリング資源として利用する。臨床判断、安全承認、ログ確定責任は人間の権限として残す。

## Consequences

### Positive

- 医療3D画像の基本機能を再実装せず、本来の計画・ログ・ハンドモーション検証へ資源を集中できる。
- 公式サンプルにより、患者情報なしで反復可能な試験を開始できる。
- Python、MRML、Markups、拡張機構を使い、原データとオーバーレイを分離できる。
- Windowsマウスrelayを実際の3D環境へ接続して検証できる。

### Negative

- Slicer本体、拡張機能、サンプルデータの版・ライセンス・ハッシュ管理が必要になる。
- Slicerの操作仕様や拡張API更新に追従する必要がある。
- サンプルデータで成立した結果を、患者データや臨床性能へ一般化できない。

### Safety boundary

- 臨床使用しない。
- 焼灼装置、カテーテル、マッピング装置、患者監視、治療パラメーターを操作しない。
- 実患者情報、CT／DICOM、手術映像、音声をリポジトリまたは外部サービスへ保存・送信しない。
- 認識不能時は何もせず、通常のマウス、フットスイッチ、助手操作を残す。

## First falsifiable test

公式安定版を固定し、公式心臓系Sample Dataを1件だけ取得する。そのデータをSlicerで表示し、物理マウスによる回転・パン・ズームができ、原データを変更せずに計画用Markupsを別ノードへ追加・削除できることを確認する。

この試験が成立しなければ、Slicerを標準PoC環境とする判断を再検討する。成立しても臨床適合性は証明されない。

## References

- `docs/17_project-purpose-and-problem.md`
- `docs/16_adr-003-windows-mouse-relay.md`
- [3D Slicer official](https://www.slicer.org/)
- [3D Slicer downloads](https://download.slicer.org/)
- [3D Slicer Sample Data module](https://slicer.readthedocs.io/en/latest/user_guide/modules/sampledata.html)
- [3D Slicer Volume Rendering](https://slicer.readthedocs.io/en/latest/user_guide/modules/volumerendering.html)
- [3D Slicer Training](https://www.slicer.org/wiki/Documentation/Nightly/Training)
- `evidence/2026-08-29-slicer-platform-review.md`
