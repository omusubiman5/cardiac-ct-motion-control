# 3D Slicer日本語メニュー構成

更新日: 2026-08-29  
対象: 3D Slicer 5.12.3 Windows Stable  
用途: 非臨床PoC

## 適用済み構成

- Slicer本体: `C:\Users\HOMEA\AppData\Local\slicer.org\3D Slicer 5.12.3`
- 公式日本語翻訳: `bin\translations\Slicer_ja.qm`
- プロジェクト補完翻訳: `bin\translations\CardiacCTMotionControl_ja.qm`
- 言語設定: `ja_JP`
- 国際化設定: 有効

公式日本語翻訳は、`Slicer/SlicerLanguageTranslations`の`Slicer_ja.ts`から、Slicer同梱の`lrelease.exe`で生成した。プロジェクト補完翻訳は、組み込みメニュー監査で英語だけの表示として残った次の2項目を補う。

|英語原文|日本語表示|
|---|---|
|`Capture/Restore`|`キャプチャ／復元`|
|`About %1`|`%1 について`|

## 検証結果

通常の全モジュール読込条件で`tools/audit_slicer_japanese.py`を実行した。

- 言語設定: `ja_JP`
- 列挙した組み込みメニュー項目: 88
- 英語だけで表示されたメニュー項目: 0
- プロセス終了コード: 0
- 標準エラー: なし

これは、現在導入されているSlicer 5.12.3の組み込みメニューツリーについての結果である。全ダイアログ、全ツールチップ、全モジュール本文、将来追加する拡張機能まで100%日本語であることは意味しない。追加拡張は個別に同じ監査を行う。

## 再構成

1. 公式`Slicer_ja.ts`を取得し、出所コミットとSHA-256を記録する。
2. Slicer同梱の`bin\lrelease.exe`で`Slicer_ja.qm`を生成する。
3. `localization/ja/CardiacCTMotionControl_ja.ts`を同じ方法でコンパイルする。
4. 生成した2つの`.qm`を、Slicerが返す`translationFolders()[0]`へ配置する。
5. Slicer内で`tools/configure_slicer_japanese.py`を実行する。
6. 再起動後、`tools/audit_slicer_japanese.py`でメニューを監査する。

## ロールバック

SlicerのPythonコンソールで次を実行し、再起動する。

```python
slicer.app.userSettings().setValue("language", "en_US")
slicer.util.restart()
```

必要なら、プロジェクト補完翻訳`CardiacCTMotionControl_ja.qm`だけを翻訳フォルダー外へ退避する。公式日本語ファイルとSlicer本体は変更しない。

## 安全境界

- 表示言語の変更だけであり、医用画像、治療装置、患者情報を変更しない。
- 日本語表示は臨床承認、医学的妥当性、操作安全性を証明しない。
- 医学用語は臨床責任者のレビュー前に確定用語と扱わない。

## 参照

- [SlicerLanguageTranslations](https://github.com/Slicer/SlicerLanguageTranslations)
- [SlicerLanguagePacks](https://github.com/Slicer/SlicerLanguagePacks)
- [3D Slicer I18N](https://github.com/Slicer/Slicer/wiki/I18N)
