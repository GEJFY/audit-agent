# ═══════════════════════════════════════════════════════
# KMS モジュール - 暗号化キー管理
# ═══════════════════════════════════════════════════════

variable "app_name" { type = string }
variable "environment" { type = string }

locals {
  name_prefix = "${var.app_name}-${var.environment}"
}

data "aws_caller_identity" "current" {}

# ── マスター暗号化キー ─────────────────────────────────
resource "aws_kms_key" "main" {
  description             = "${local.name_prefix} encryption key"
  deletion_window_in_days = var.environment == "prod" ? 30 : 7
  enable_key_rotation     = true

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid    = "RootAccountFullAccess"
        Effect = "Allow"
        Principal = {
          AWS = "arn:aws:iam::${data.aws_caller_identity.current.account_id}:root"
        }
        Action   = "kms:*"
        Resource = "*"
      },
      {
        Sid    = "AllowECSTaskRole"
        Effect = "Allow"
        Principal = {
          AWS = "arn:aws:iam::${data.aws_caller_identity.current.account_id}:root"
        }
        Action = [
          "kms:Decrypt",
          "kms:DescribeKey",
          "kms:Encrypt",
          "kms:GenerateDataKey*",
          "kms:ReEncrypt*"
        ]
        Resource = "*"
      }
    ]
  })

  tags = { Name = "${local.name_prefix}-kms" }
}

resource "aws_kms_alias" "main" {
  name          = "alias/${local.name_prefix}"
  target_key_id = aws_kms_key.main.key_id
}

# ── 出力 ───────────────────────────────────────────────
output "key_arn" { value = aws_kms_key.main.arn }
output "key_id" { value = aws_kms_key.main.key_id }
output "alias_name" { value = aws_kms_alias.main.name }
