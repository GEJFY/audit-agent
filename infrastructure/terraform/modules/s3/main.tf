# ═══════════════════════════════════════════════════════
# S3 モジュール - 証跡ストレージ
# ═══════════════════════════════════════════════════════

variable "app_name" { type = string }
variable "environment" { type = string }
variable "kms_key_arn" { type = string }

locals {
  name_prefix = "${var.app_name}-${var.environment}"
}

data "aws_caller_identity" "current" {}

# ── 証跡バケット ───────────────────────────────────────
resource "aws_s3_bucket" "evidence" {
  bucket = "${local.name_prefix}-evidence-${data.aws_caller_identity.current.account_id}"

  tags = { Name = "${local.name_prefix}-evidence" }
}

resource "aws_s3_bucket_versioning" "evidence" {
  bucket = aws_s3_bucket.evidence.id
  versioning_configuration {
    status = "Enabled"
  }
}

resource "aws_s3_bucket_server_side_encryption_configuration" "evidence" {
  bucket = aws_s3_bucket.evidence.id

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm     = "aws:kms"
      kms_master_key_id = var.kms_key_arn
    }
    bucket_key_enabled = true
  }
}

resource "aws_s3_bucket_public_access_block" "evidence" {
  bucket = aws_s3_bucket.evidence.id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

resource "aws_s3_bucket_lifecycle_configuration" "evidence" {
  bucket = aws_s3_bucket.evidence.id

  rule {
    id     = "transition-to-ia"
    status = "Enabled"

    transition {
      days          = 90
      storage_class = "STANDARD_IA"
    }

    transition {
      days          = 365
      storage_class = "GLACIER"
    }

    # 監査証跡は7年保持（J-SOX要件）
    expiration {
      days = 2555
    }
  }
}

# バケットポリシー: HTTPS強制
resource "aws_s3_bucket_policy" "evidence" {
  bucket = aws_s3_bucket.evidence.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid       = "DenyNonSSL"
        Effect    = "Deny"
        Principal = "*"
        Action    = "s3:*"
        Resource = [
          aws_s3_bucket.evidence.arn,
          "${aws_s3_bucket.evidence.arn}/*"
        ]
        Condition = {
          Bool = { "aws:SecureTransport" = "false" }
        }
      }
    ]
  })
}

# ── 出力 ───────────────────────────────────────────────
output "bucket_name" { value = aws_s3_bucket.evidence.id }
output "bucket_arn" { value = aws_s3_bucket.evidence.arn }
