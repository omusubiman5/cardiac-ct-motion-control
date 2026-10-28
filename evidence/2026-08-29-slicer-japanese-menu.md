# 3D Slicer日本語メニュー検証証跡

日付: 2026-08-29  
対象: 3D Slicer 5.12.3 Windows Stable

## 導入

- 公式インストーラー: `Slicer-5.12.3-win-amd64.exe`
- サイズ: `268819256` bytes
- 公式SHA-512との照合: 一致
- インストール終了コード: `0`
- 導入先: `C:\Users\HOMEA\AppData\Local\slicer.org\3D Slicer 5.12.3`

## 翻訳資産

- `SlicerLanguageTranslations` commit: `38c858a51b42a73473f3c81af773597447ca06f3`
- 公式`Slicer_ja.ts` SHA-256: `d9026f45a5fd743b4a9209c326e15124aa8af2ec17a1f4e6e9f559e13a3a561f`
- 生成`Slicer_ja.qm` SHA-256: `4cb3bcd017800441b42762350373d891296df265006c1fd7d2b42b919aa9e90c`
- 補完`CardiacCTMotionControl_ja.ts` SHA-256: `5362124f4191ae337f6fb44be232d451e32559243dc1b749f12bc31d60d83eea`
- 生成`CardiacCTMotionControl_ja.qm` SHA-256: `f8268e41bef410431d2c619dcb8e5a4e96b81482e32fe320ebca5dc6f1f4872c`
- コンパイラー: Slicer 5.12.3同梱`bin\lrelease.exe`

## 観測

公式`Slicer_ja.ts`のアクティブメッセージ5,849件のうち、5,721件は翻訳済み、128件は空または`unfinished`だった。公式翻訳を設定した後、通常のSlicerメニューツリーを列挙すると88項目中2項目が英語だけで残った。

補完翻訳で`Capture/Restore`と`About %1`を追加後、全モジュールを通常読込して再監査した。

```json
{"language":"ja_JP","menuEntryCount":88,"asciiOnlyEntryCount":0,"asciiOnlyEntries":[]}
```

- 終了コード: `0`
- 標準エラー: 空
- 結果分類: `SUPPORTED`

## 限界

- 確認対象は現在の組み込みメニュー88項目。
- 全ダイアログ、説明文、ツールチップ、CLI、追加拡張の完全翻訳は未確認。
- ASCII-only検出は監査の第一段階であり、誤訳や医学用語の妥当性を評価しない。

## 通常表示による確認

2026-08-29、3D Slicer 5.12.3を非表示オプションなしで通常起動した。Windows上の実ウィンドウ`3D Slicer 5.12.3`を取得し、画面とUI Automationツリーの両方で次を確認した。

- メニューバー: `ファイル (F)`、`編集 (E)`、`ビュー`、`ヘルプ (H)`
- ようこそ画面: `データの追加`、`DICOMデータの追加`、`拡張機能のインストール`、`サンプルデータのダウンロード`などが日本語表示
- 通常の3D／スライスビューが表示され、起動後もプロセスを開いたままにした
- 起動時の非臨床使用注意ダイアログ本文は英語のまま残る。これはメニューではないため、今回の「組み込みメニュー日本語化」完了判定には含めない

初回UI操作で「今後表示しない」チェックを誤ってオンにしたが、直後の画面観測で検出し、オフへ戻してから`OK`を押した。最終状態では注意ダイアログは次回も表示される。

## 参照

- `docs/19_3d-slicer-japanese-localization.md`
- `tools/configure_slicer_japanese.py`
- `tools/audit_slicer_japanese.py`
- `localization/ja/CardiacCTMotionControl_ja.ts`
