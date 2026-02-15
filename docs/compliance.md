# Compliance Framework

## Supported Frameworks

| Framework | Region | Description |
|-----------|--------|-------------|
| SOC 2 | Global | Trust Service Criteria |
| ISO 27001 | Global | ISMS (Information Security Management System) |
| J-SOX | JP | 日本版SOX法 (内部統制報告制度) |
| GDPR | EU | EU一般データ保護規則 |
| PDPA | SG/TH | 個人データ保護法 |
| PIPL | CN | 中国個人情報保護法 |

## Region-Framework Mapping

| Region | Frameworks |
|--------|-----------|
| JP (日本) | J-SOX, SOC2, ISO27001 |
| SG (シンガポール) | PDPA, SOC2, ISO27001 |
| HK (香港) | SOC2, ISO27001 |
| AU (オーストラリア) | SOC2, ISO27001 |
| TW (台湾) | SOC2, ISO27001 |
| KR (韓国) | SOC2, ISO27001 |
| TH (タイ) | PDPA, SOC2 |
| EU | GDPR, SOC2, ISO27001 |
| CN (中国) | PIPL, ISO27001 |

## Compliance Check

`ComplianceChecker` (`src/security/compliance.py`) が各フレームワークの準拠状況を自動チェック:

### SOC 2 チェック項目
- CC6.1: 論理・物理アクセス制御
- CC6.3: 暗号化（保存データ）
- CC7.2: システム監視
- CC7.3: 監査ログ
- CC8.1: 変更管理

### ISO 27001 チェック項目
- A.9: アクセス制御ポリシー
- A.10: 暗号化（保存時・転送時）
- A.12: 運用セキュリティ（ログ・監視）
- A.18: コンプライアンス（データ居住地）

### GDPR チェック項目
- Art.17: 削除権対応
- Art.30: 処理活動記録
- Art.32: セキュリティ措置
- Art.35: DPIA (データ保護影響評価)

### PDPA チェック項目
- S13: 同意管理
- S24: データ保護ポリシー
- S26D: データ侵害通知プロセス

### PIPL チェック項目
- Art.38: 越境データ移転評価
- Art.40: データローカライゼーション
- Art.52: 個人情報保護責任者

## API Usage

```bash
# コンプライアンス状況確認
GET /api/v1/compliance/status?region=JP

# コンプライアンスチェック実行
POST /api/v1/compliance/check
{"region": "JP", "tenant_id": "uuid"}
```

## Score Interpretation

| Score | Status | Meaning |
|-------|--------|---------|
| 80-100 | Compliant | 準拠 |
| 50-79 | Partial | 一部準拠 |
| 0-49 | Non-Compliant | 非準拠 |

## Data Residency

データ居住地要件のあるリージョン:
- **JP**: 日本国内でのデータ保管が推奨
- **AU**: オーストラリア国内でのデータ保管が必須
- **KR**: 韓国国内でのデータ保管が必須
- **CN**: 中国国内でのデータ保管・処理が必須（PIPL Art.40）

## Audit Trail

全エージェント操作は `AuditTrailService` により記録:
- エージェント名、アクション種別
- テナントID、プロジェクトID
- 入力/出力データ（ハッシュ化）
- タイムスタンプ、confidence score
