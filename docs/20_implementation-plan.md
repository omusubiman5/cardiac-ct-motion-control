# 実装計画書

作成日: 2026-10-08
状態: 作業用（非臨床PoC。臨床使用の承認・主張ではない）

2026-10-09追記: 手入力が視点操作3種類に留まっている不足を補う計画は、[ハンドモーション操作を完結させる実装計画](23_hand-motion-completion-plan.md)を参照する。操作者がマウスやキーボードに触れずCスタンプ操作を完結することを主目的とし、本書のマウス先行実装は代替操作と基礎検証の位置づけとする。

## 目的

医師からの依頼に基づき、動作するものを作る。評価は医療従事者が行う。本計画は、術前Cスタンプ計画と術中実績ログを分離した3D Slicer上のオーバーレイ実装と、既存ハンドモーションPoCからの入力経路を、検証可能な順序で実装する手順を定める。

## OSSライブラリ選定結果

### 採用

**MediaPipe Tasks Hand Landmarker（VIDEOモード）＋ プロジェクト所有の決定論的IntentClassifier**

ADR-002の決定を再確認した。調査レポート（GitHub Repository Intelligence Ranking）の上位候補を本プロジェクトの制約に照合した結果、認識エンジンを差し替える根拠は見つからなかった。

| 候補 | レポート順位 | 不採用理由 |
|---|---|---|
| vladmandic/human | 1（88点） | TypeScript/JS専用。本プロジェクトはPython＋3D Slicer構成であり言語スタックが不合致 |
| mikhail-vlasenko/grlib | 2（79点） | 内部がLegacy `mp.solutions.hands`依存（ADR-002で廃止方針）。分類器は学習型MLで非決定論的、安全契約「曖昧時は何もしない」をコードで固定できない。特徴抽出・軌跡ベース動的ジェスチャー手法は参照価値あり |
| handtracking-io/yoha | 3（71点） | unmaintained宣言（2024-03以降更新なし） |
| jaredrhod/barehands | 4（76点） | AGPL-3.0、ブラウザUIフレームワーク。医療プロジェクトでのライセンス・構成上不適 |
| CalciferZh/minimal-hand | 5（73点） | 学術コード、MANOモデル要手配、訓練コード非公開、2021年更新停止 |
| tuhindutta/GestureForge | 6（75点） | 学習パイプライン工具であり実行時エンジンではない。将来のジェスチャー学習評価用として保留 |
| ahmetgunduz/Real-time-GesRec | 7（70点） | 2022年更新停止の学術コード |
| kinivi/hand-gesture-recognition-mediapipe | 8 | サンプルコード中心、ライブラリ化なし |

### 採用構成

```text
Pixel 9a / USBカメラ
  -> OpenCV DirectShow CameraSource（実装済み）
  -> MediaPipe Tasks Hand Landmarker VIDEOモード
       モデル資産: hand_landmarker.task（版・SHA-256固定・ローカル配置・実行時DL禁止）
  -> プロジェクト所有 決定論的IntentClassifier
       （21点ランドマーク -> ROTATE/PAN/ZOOM/NONE/AMBIGUOUS等の候補）
  -> ADR-001 SafetyController（フェイルクローズ状態機械）
  -> ADR-003 mouse_relay.py（INPUT_MOUSEのみ、TargetGuard付き）
  -> 3D Slicer 5.12.3（ADR-004）
```

既存環境: Python 3.12.10、OpenCV 4.11.0、MediaPipe 0.10.21、NumPy 1.26.4（`prototypes/cmos-motion-poc`、単体試験13件合格済み）

## 実装スコープ

### 対象表面の固定

非臨床Cライン試験の対象表面を **`CARTOmesh_1-OG`（CARTO心房EAM殻、9,957頂点）** に固定する。理由: Cスタンプの想定位置は左心房・肺静脈周辺であり、心臓全体外形（`Whole_Heart_Anatomy_Base`）は外表面のみで心腔内面を持たない。検証シーンは保存済み `artifacts/slicer/CARTO3_EA_Map_Demo.mrb` を使用する。

### 実装単位

#### 単位1: Slicer側Cスタンプモジュール（マウス操作）

3D SlicerのScripted Moduleとして実装。原モデル・原データを変更しない独立オーバーレイ。

- `prototypes/slicer-cstamp/` に配置
- 状態機械: `IDLE` -> `DRAFT` -> `COMMITTED` / `CANCELLED`（`docs/03`準拠）
- 照準: マウス位置から許可表面（CARTOmesh_1-OG）との交点を取得し配置可否を表示（`AIM_SURFACE`）
- `STAMP_DRAFT`: 交点にCテンプレートを仮配置。同入力からの多重生成を抑止
- `ROTATE_OPENING` / `TILT_PLANE` / `REVERSE_PATH` / `RESET_DIRECTION`: アンカー固定の方向調整
- `COMMIT_DRAFT`: 明示確定で確定ログ1件を生成（同一DRAFT IDからの2件生成を禁止）
- `CANCEL_DRAFT`: DRAFTのみ破棄
- 確定イベント: イベントID、順序、時刻、座標系、テンプレート版・ハッシュ、アンカー座標、配置面基底、開口・進行方向、完全変換、C全体形状を保持（FR-014、FR-024〜030）
- 保存先: モデルと分離したJSONイベント台帳（シーンの`mrmlScene`ではなく独立ファイルへエクスポート）
- `PLANNED`/`PERFORMED`レイヤー分離、点表示とC型表示の切替（同一イベントID参照）

#### 単位2: 視点操作のSlicer接続

- 既存`mouse_relay.py`の`ROTATE/PAN/ZOOM`をSlicerの3Dビューへ接続
- Slicerの3Dビューは既定で左ドラッグ=回転、中ドラッグ=パン、ホイール=ズーム
- `SMOOTH_ZOOM`の連続コマンド化（FR-016〜023）、デッドゾーン・平滑化・速度上限・解放時停止
- `TargetGuard`: Slicer実行ファイル＋ウィンドウ一致を厳格化（タイトル部分一致の廃止、SR-006/R-004対応）

#### 単位3: ハンドモーション経路

- MediaPipe Tasks Hand Landmarkerへのアダプター実装（Legacy Handsから移行）
- 決定論的IntentClassifier（開いた手=回転、指1本=パン、ピンチ=ズームの既存割当を21点ランドマークで再実装）
- ADR-001 SafetyControllerの状態機械実装（DISABLED/READY/TRACKING/EXECUTING/FAULT）
- 手数≠1、観測欠落、古いフレーム、曖昧時は無出力
- ハンドモーションとマウスは同一コマンド契約（FR-013）

#### 単位4: 計画追従ビュー（単位1の後）

- `PLANNED`レイヤーへの予定Cスタンプ配置・版管理
- 次の予定1件のゴースト表示、DRAFTとの位置・姿勢・開口方向差表示（FR-036〜040）

## 検証順序

| 順序 | 内容 | 対応受入条件 |
|---|---|---|
| 1 | マウスでスタンプ→確定→取消 | AC-001, AC-003, AC-004 |
| 2 | 方向のみ調整、重複確定抑止、スタンプ重複抑止 | AC-002, AC-005, AC-010 |
| 3 | 照準の配置可否切替 | AC-009 |
| 4 | 開口方向の単調調整とアンカー不変 | AC-011 |
| 5 | ズーム単調性・停止・DRAFT中の不変性 | AC-012, AC-013 |
| 6 | 両段階からの取消 | AC-014 |
| 7 | 点表示切替、C再表示、複数イベント、保存再読込 | AC-015〜AC-018 |
| 8 | ハンドモーションとマウスの同等性、異常時無変更 | AC-006, AC-007, AC-008 |
| 9 | PLANNED/PERFORMED識別、計画追従 | AC-019〜AC-024 |

## ファイル構成（案）

```text
prototypes/
├─ cmos-motion-poc/          既存（認識・変換・relay。Tasks移行をここで実施）
└─ slicer-cstamp/            新規（Slicer側オーバーレイ）
   ├─ CStampModule.py        Scripted Module本体
   ├─ cstamp/
   │  ├─ state_machine.py    IDLE/DRAFT/COMMITTED/CANCELLED
   │  ├─ template.py         Cテンプレート定義・版・ハッシュ
   │  ├─ ledger.py           JSONイベント台帳（読み取り専用再構成）
   │  └─ surface_aim.py      表面交点・配置可否
   └─ tests/                 Slicer外で実行可能な単体試験
```

## 安全境界（作業中の遵守事項）

- 実患者データ・CT/DICOM・手術映像・音声を保存・外部送信しない
- 認識不能・曖昧・複数人・遮蔽・対象外・異常時は何もしない
- 確定はスタンプ/調整と別の独立した明示操作
- 元CT/3Dモデル/既存確定ログを変更しない（オーバーレイのみ）
- 通常マウス・フットスイッチ・助手操作を残す
- 本実装は非臨床検証物であり、臨床使用・臨床性能の主張をしない

## 既知の未決事項（実装を止めない範囲で記録）

- 確定操作の具体ジェスチャー割当（実測後に固定）
- 数値合格基準（ズーム平滑度、遅延等は非臨床実測後に決定）
- モデル資産`hand_landmarker.task`の取得・SHA-256・SBOM登録
- Gitの初期コミットが未作成（実装着手時に基盤コミットを作る）
- PLANNEDレイヤーの承認者・訂正責任は臨床側の定義待ち（実装はデータ構造のみ先行）
