# 最小権限・構成管理・署名の証明メモ（IT-002/004/005）

作成日: 2026-10-10
対象: 非臨床プロトタイプ（`prototypes/slicer-cstamp`, `prototypes/cmos-motion-poc`）。
臨床環境への適合証明ではない。実機での権限昇格監査・正式SBOM承認は未実施。

## IT-004 最小権限動作

### 主張

本PoCは標準ユーザー権限で起動・動作する。管理者権限を要求する操作をコード内に持たない。

### 根拠（実コード照合）

| 項目 | 実測 |
|---|---|
| 管理者権限必須API | `grep -rn "admin|elevat|registry|HKLM|service|schtasks" prototypes/ tools/` で該当なし |
| ネットワーク | 待受は `127.0.0.1:18944` のみ（`tools/audit_network.py` exit 0、非loopback 0件）。ループバック待受はWindowsファイアウォール例外を要求しない |
| サービス/タスク/レジストリ | 登録コードなし |
| インストール | `setup.ps1`はローカル`.venv`作成とpipのみ。システムPython・共有コンポーネントへ書き込まない |
| 実行ポリシー | `run.ps1`は署名済みだが、bypassを要求しない設計（呼び出し側のポリシーに従う） |

### 残存制約

- これはコード照合による証明であり、実行時の権限昇格が発生しないことの外部監査（プロセス監視ログ等）は未実施。
- 3D Slicer本体の権限要件は対象外（Slicer配布元の要件に従う）。

## IT-005 構成管理

### 主張

実行に必要な構成値・モデル・コードの版を固定し、改変を検出可能にする。

### 根拠

| 項目 | 実装 |
|---|---|
| 構成値 | `config.example.json`＋`config.py`の範囲・型検証。不正値は起動を拒否（フェイルクローズ） |
| 認識モデル | `models/hand_landmarker.task`をSHA-256 `fbc2a30080c3c557093b5ddfc334698132eb341044ccee322ccf8bcf3607cde1`でピン留め（`models/README.md`記録。実行時DLなし・欠損時はexit 6で停止） |
| ファイル完全性 | `tools/generate_sbom.py`が配布物50ファイルのSHA-256マニフェスト＋依存39件を`artifacts/sbom/`へ生成 |
| 台帳 | `events.jsonl`/`plans.jsonl`は追記のみ。各イベントにintegrity hash |

## IT-002 署名＋SBOM

### 実施済み

- `run.ps1`/`setup.ps1`へ自己署名証明書`CN=CStampPoC-Dev (non-clinical)`（thumbprint `262148C323E1E38D27A5C331F73508CC2B0B4594`）でAuthenticode署名を付与。証明書は`artifacts/cstamp/cstamp-poc-dev.cer`に保存。
- SBOM: `artifacts/sbom/sbom-20261010.json`（SHA-256マニフェスト＋pip freeze）。

### 制約（正直な記録）

- `Get-AuthenticodeSignature`は`UnknownError`を返す。これはハッシュ不一致ではなく、自己署名ルートがユーザーの信頼済みルートストアへ未登録のため（GUI同意が必要で非対話では入れられなかった）。署名ブロックはファイル内に存在し、証明書拇印は一致する。
- Pythonソース・`.py`はAuthenticode対象外のため署名していない。完全性はSBOMのSHA-256で担保する。
- 正式配布では組織のコード署名証明書（HSM/KMS管理）への差替えと、ルート証明書の配布手順が必要。
