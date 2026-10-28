---
artifact: adr
version: "1.0"
created: 2026-08-28
status: accepted
---

# ADR-003: Windowsマウス専用relay

## Status

Accepted（非臨床PoCに限定。臨床使用の承認ではない）

**Date:** 2026-08-28  
**Deciders:** ユーザー、開発担当

## Context

PixelとMediaPipe Tasksは、映像から手ランドマークと動作候補を生成するが、Windows上の3Dビューアへマウスイベントを送信しない。したがって、ADR-001の`SafetyController`で許可された型付き操作をWindowsマウスイベントへ変換するrelayが必須である。

目的はキーボードショートカットの代替ではない。術者の手の移動を、既存3Dビューアで通常マウスが行うドラッグとホイールへ対応させることである。既存`input_bridge.py`はPyAutoGUIでマウス操作を実行しているが、ファイル名が汎用入力を示し、キーボード操作を排除する境界が型と実装で固定されていない。

## Decision

私たちは、`prototypes/cmos-motion-poc/mouse_relay.py`を必須コンポーネントとして設ける。relayは`MotionAction`だけを受け取り、Windowsの`SendInput`へ`INPUT_MOUSE`イベントだけを渡す。`INPUT_KEYBOARD`、仮想キー、文字列、ホットキー、アプリ起動、ウィンドウ切替のAPIを実装しない。

操作対応は次に限定する。

| MotionAction | Mouse relay output |
|---|---|
| `ROTATE(dx, dy)` | 設定済み回転ボタンを保持し、相対マウス移動`dx,dy` |
| `PAN(dx, dy)` | 設定済みパンボタンを保持し、相対マウス移動`dx,dy` |
| `ZOOM(amount)` | 保持ボタンを解放し、垂直ホイール`amount × WHEEL_DELTA` |
| `None/NONE/AMBIGUOUS` | 保持ボタンを解放し、新規イベントなし |

relayは操作対象を選ばず、フォーカスを変更しない。各出力直前に`TargetGuard`が前面`HWND`と承認済みプロセスID／実行ファイルIDの一致を確認する。一致しない場合はボタンを解放してイベントを拒否する。タイトル部分一致だけでは許可しない。

起動時の既定は`PreviewMouseRelay`とする。`--enable-input`、手動アーミング、ADR-001の`EXECUTING`、`TargetGuard`一致がすべて成立した場合だけ`WindowsMouseRelay`を使用する。relayの終了、例外、対象逸脱、認識喪失では`release_all()`を必ず実行する。

## Consequences

### Positive

- 手の連続移動を、3Dビューアが既に持つマウスドラッグ操作として再現できる。
- キーボード操作をコード構造から排除し、任意コマンドへ拡張される経路を閉じられる。
- 認識・安全判定とWindows固有入力を分離でき、Preview relayと実relayを同じ契約で試験できる。
- PyAutoGUIの汎用APIへ依存せず、実際に送る`MOUSEINPUT`フラグを許可リスト化できる。

### Negative

- Win32 `ctypes`構造体と`SendInput`エラー処理の実装・試験が必要になる。
- `SendInput`はUIPIにより、relayより高い整合性レベルのアプリへ入力できない。
- 相対マウス移動はWindowsのポインター速度・加速設定の影響を受けるため、構成固定と実測が必要になる。

### Neutral

- 通常の物理マウス、フットスイッチ、助手操作は残す。
- relayは3Dデータを変更せず、既存ビューアの表示視点操作だけを模倣する。

## Alternatives Considered

### キーボードrelay

回転・パン・ズームをキーへ割り当てる方式。手の連続量を表現しにくく、任意キー入力への拡張リスクがあるため採用しない。

### PyAutoGUIを汎用入力bridgeとして維持する

PoC実装は短いが、キーボード、スクリーンショット、汎用GUI操作まで同じ依存関係が提供する。マウス限定境界を強制しにくいため、WindowsMouseRelayの内部実装には採用しない。

### 対象ビューア固有API

利用可能なら入力注入より確実な可能性があるが、対象ビューアとAPIが未確定である。後に正式APIが確認された場合は`OutputPort`の別実装として評価する。

## References

- `docs/14_adr-001-fail-closed-motion-controller.md`
- `docs/15_adr-002-google-vision-stack.md`
- `docs/03_system-requirements.md`
- [Microsoft SendInput](https://learn.microsoft.com/en-us/windows/win32/api/winuser/nf-winuser-sendinput)
- [Microsoft MOUSEINPUT](https://learn.microsoft.com/en-us/windows/win32/api/winuser/ns-winuser-mouseinput)
- [Microsoft GetForegroundWindow](https://learn.microsoft.com/en-us/windows/win32/api/winuser/nf-winuser-getforegroundwindow)

