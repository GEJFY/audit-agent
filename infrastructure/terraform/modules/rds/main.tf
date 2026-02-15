# ═══════════════════════════════════════════════════════
# RDS モジュール - PostgreSQL 16 + pgvector
# ═══════════════════════════════════════════════════════

variable "app_name" { type = string }
variable "environment" { type = string }
variable "vpc_id" { type = string }
variable "private_subnet_ids" { type = list(string) }
variable "db_security_group_id" { type = string }
variable "kms_key_arn" { type = string }

variable "instance_class" {
  type = map(string)
  default = {
    dev     = "db.t4g.micro"
    staging = "db.t4g.small"
    prod    = "db.r6g.large"
  }
}

variable "allocated_storage" {
  type = map(number)
  default = {
    dev     = 20
    staging = 50
    prod    = 100
  }
}

locals {
  name_prefix = "${var.app_name}-${var.environment}"
}

# ── サブネットグループ ─────────────────────────────────
resource "aws_db_subnet_group" "main" {
  name       = "${local.name_prefix}-db-subnet"
  subnet_ids = var.private_subnet_ids
  tags       = { Name = "${local.name_prefix}-db-subnet" }
}

# ── パラメータグループ（pgvector有効化） ───────────────
resource "aws_db_parameter_group" "main" {
  name   = "${local.name_prefix}-pg16"
  family = "postgres16"

  parameter {
    name  = "shared_preload_libraries"
    value = "pg_stat_statements"
  }

  parameter {
    name  = "log_min_duration_statement"
    value = var.environment == "prod" ? "1000" : "500"
  }

  tags = { Name = "${local.name_prefix}-pg16-params" }
}

# ── RDSインスタンス ────────────────────────────────────
resource "aws_db_instance" "main" {
  identifier = "${local.name_prefix}-postgres"

  engine         = "postgres"
  engine_version = "16.4"
  instance_class = var.instance_class[var.environment]

  allocated_storage     = var.allocated_storage[var.environment]
  max_allocated_storage = var.allocated_storage[var.environment] * 2
  storage_type          = "gp3"
  storage_encrypted     = true
  kms_key_id            = var.kms_key_arn

  db_name  = "audit_agent"
  username = "audit_admin"
  manage_master_user_password = true

  db_subnet_group_name   = aws_db_subnet_group.main.name
  vpc_security_group_ids = [var.db_security_group_id]
  parameter_group_name   = aws_db_parameter_group.main.name

  multi_az            = var.environment == "prod"
  publicly_accessible = false

  backup_retention_period = var.environment == "prod" ? 35 : 7
  backup_window           = "03:00-04:00"
  maintenance_window      = "sun:04:00-sun:05:00"

  deletion_protection       = var.environment == "prod"
  skip_final_snapshot       = var.environment != "prod"
  final_snapshot_identifier = var.environment == "prod" ? "${local.name_prefix}-final-snapshot" : null

  performance_insights_enabled    = var.environment != "dev"
  performance_insights_kms_key_id = var.environment != "dev" ? var.kms_key_arn : null

  enabled_cloudwatch_logs_exports = ["postgresql", "upgrade"]

  tags = { Name = "${local.name_prefix}-postgres" }
}

# ── 出力 ───────────────────────────────────────────────
output "endpoint" {
  value = aws_db_instance.main.endpoint
}

output "connection_url" {
  value     = "postgresql+asyncpg://audit_admin@${aws_db_instance.main.endpoint}/audit_agent"
  sensitive = true
}

output "instance_id" {
  value = aws_db_instance.main.id
}
