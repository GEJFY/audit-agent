# ═══════════════════════════════════════════════════════
# Redis モジュール - ElastiCache Redis 7
# ═══════════════════════════════════════════════════════

variable "app_name" { type = string }
variable "environment" { type = string }
variable "vpc_id" { type = string }
variable "private_subnet_ids" { type = list(string) }
variable "cache_security_group_id" { type = string }

variable "node_type" {
  type = map(string)
  default = {
    dev     = "cache.t4g.micro"
    staging = "cache.t4g.small"
    prod    = "cache.r6g.large"
  }
}

locals {
  name_prefix = "${var.app_name}-${var.environment}"
}

# ── サブネットグループ ─────────────────────────────────
resource "aws_elasticache_subnet_group" "main" {
  name       = "${local.name_prefix}-redis-subnet"
  subnet_ids = var.private_subnet_ids
}

# ── パラメータグループ ─────────────────────────────────
resource "aws_elasticache_parameter_group" "main" {
  name   = "${local.name_prefix}-redis7"
  family = "redis7"

  parameter {
    name  = "maxmemory-policy"
    value = "allkeys-lru"
  }
}

# ── Redisレプリケーショングループ ──────────────────────
resource "aws_elasticache_replication_group" "main" {
  replication_group_id = "${local.name_prefix}-redis"
  description          = "${local.name_prefix} Redis cluster"

  engine               = "redis"
  engine_version       = "7.1"
  node_type            = var.node_type[var.environment]
  num_cache_clusters   = var.environment == "prod" ? 3 : 1
  parameter_group_name = aws_elasticache_parameter_group.main.name

  subnet_group_name  = aws_elasticache_subnet_group.main.name
  security_group_ids = [var.cache_security_group_id]

  at_rest_encryption_enabled = true
  transit_encryption_enabled = true

  automatic_failover_enabled = var.environment == "prod"
  multi_az_enabled           = var.environment == "prod"

  snapshot_retention_limit = var.environment == "prod" ? 7 : 1
  snapshot_window          = "03:00-04:00"
  maintenance_window       = "sun:04:00-sun:05:00"

  tags = { Name = "${local.name_prefix}-redis" }
}

# ── 出力 ───────────────────────────────────────────────
output "endpoint" {
  value = aws_elasticache_replication_group.main.primary_endpoint_address
}

output "connection_url" {
  value     = "rediss://${aws_elasticache_replication_group.main.primary_endpoint_address}:6379/0"
  sensitive = true
}
