# 依頼: Pixel 9aカメラ入力経路の有効化

日付: 2026-10-09
依頼元: Cardiac-CT-Motion-Control 担当（Devin）
依頼先: Codex担当 / 端末物理操作が可能な者
区分: 非臨床プロトタイプの実機検証準備

## 目的

`prototypes/cmos-motion-poc` のハンドモーション入力にPixel 9aの実カメラ映像を使う。
カメラ経路が生きていることを**黒フレームでなく実映像（フレーム間差分>0、輝度>0）で確認**するところまで。

## 現状（確認済み）

- Pixel 9aはUSB接続済み。PnPに`Android Composite ADB Interface`と`ADB Interface`が出ている
- `adb devices`で`58311JEBF16314 unauthorized`——USBデバッグ許可ダイアログが端末上で未承認
- `camera_index=0`（`Windows Virtual Camera Device`）はOpenCVで開けるが、**全フレーム黒**（mean=0.0、0.7秒差分=0.0）。仮想カメラは起きているがPixelから映像が来ていない
- BluetoothでもPixel 9aは接続中（A2DP/Hands-Free）。WPD側は`Unknown`
- CDPSvc（Cross Device）サービスは稼働中
- Windows設定の`ms-settings:mobiledevices`を開いた

## 依頼内容（どちらか一方で成立すればよい）

### 経路A: USBウェブカメラモード（推奨・確実）

1. Pixel側でUSBデバッグ許可ダイアログを承認（`unauthorized`→`device`に変わること）
2. 承認後、PC側から実行:
   ```
   adb shell svc usb setFunctions webcam
   ```
   （またはPixelの通知「USB経由の充電」→「ウェブカメラ」選択）
3. PixelがUVCカメラとしてWindowsに再列挙されることを確認

### 経路B: Windows接続カメラ経由

1. Windows: 設定→Bluetoothとデバイス→モバイルデバイス→Pixel 9aをリンク済みにし「カメラとして使用」をオン
2. Pixel側: クイック設定または通知でカメラ共有を許可・有効化
3. `Windows Virtual Camera Device`に実映像が流れることを確認

## 検証方法（完了判定）

```powershell
cd C:\Projects\Cardiac-CT-Motion-Control\prototypes\cmos-motion-poc
.\.venv\Scripts\python.exe -c "import cv2,time,numpy as np; c=cv2.VideoCapture(0,cv2.CAP_DSHOW); ok,f1=c.read(); time.sleep(0.7); ok2,f2=c.read(); c.release(); print('mean',f1.mean(),'diff',float(np.abs(f1.astype(np.int16)-f2.astype(np.int16)).mean()))"
```

合格条件: `mean > 0` かつ `diff > 0`（実映像が流れている）。`mean=0`は不合格。

## 完了後の連絡

このドキュメントへ結果を追記するか、`PROJECT_STATUS.md`に記録。
その後、担当は`--slicer-connect`の実機結合試験（手→認識→TCP→Slicerカメラ）へ進む。

## 備考

- ADB非承認なら経路Aは端末タップが必須（AIにはできない）
- USB接続だけで映像は来ない。モバイルデバイス連携またはUSB webcamモードの明示的有効化が必要
- カメラ映像の保存・外部送信はしない（プロジェクト安全境界）

## Pixelカメラ経路の実測確認 2026-10-09 20:19:24 +09:00
- ADB devices: 対象端末はdevice（許可済み）。
- svc usb setFunctions webcamを実行。exit code 1、出力setCurrentFunctions opId:1。有効化成立は確認できていない。
- OpenCV DSHOW: index0 read成功、mean=0.0、diff=0.0。index1/2はread失敗。実映像未成立、未完了。
- 次工程: Pixel通知のUSB設定でウェブカメラを選択した後、PC側でmean/diff再検証。映像保存・外部送信なし。


## Pixel実映像経路成立 2026-10-09 20:23:48 +09:00
- ADBから実端末設定のUSB→ウェブカメラを選択し、実プレビューの前面カメラへ切替。
- OpenCV DSHOW index1: mean=130.3058865017361、0.7秒差分=0.670107421875。実映像入力の指定完了条件を満たした。index0はmean=2.5732573784722224、diff=0で対象にしない。

## Pixel 8a (akita) 実測訂正 2026-10-25
- `svc usb setFunctions webcam`・`webcam,adb` はいずれも `setCurrentFunctions opId:1` を返すが `sys.usb.config` が `adb` のまま変わらず、デバイスマネージャの「Android Webcam」も `Unknown` のまま（受理されるが切り替わらない）。
- **この端末で有効な関数名は `uvc`**：`adb shell svc usb setFunctions uvc` で即座に再列挙され「Android Webcam」が OK になった。切替後 adb は `unauthorized` になるが UVC には adb 不要。
- カメラハンドルは切替前に OpenCV が掴んでいるため、**UVC切替後は認識プロセス(app.py)の再起動が必要**（read失敗連続で `return 5` するが、10回未満で留まるケースもあり自動復帰しない）。
- 復旧手順（実測済み）: ① Pixel を抜き差し ② `adb shell svc usb setFunctions uvc` ③ 認識プロセス再起動 ④ Slicerパネル「カメラを表示」トグル OFF→ON（プレビュー要求は認識側で消費済みのため再送が必要）。
- cmos-motion-pocはカメラindex1を指定して使用。Slicer結合・手認識は別工程で未実施。
- 映像ファイル保存・外部送信なし。前回の端末タップを本人だけに求めた案内は訂正。ADB許可済みなら端末UI操作はPCから実行可能だった。

