# ═══════════════════════════════════════════════════════
# audit-agent Terraform ルート設定
# ═══════════════════════════════════════════════════════

terraform {
  required_version = ">= 1.6.0"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }

  # リモートステート（環境別に設定）
  backend "s3" {}
}

provider "aws" {
  region = var.aws_region

  default_tags {
    tags = {
      Project     = "audit-agent"
      Environment = var.environment
      ManagedBy   = "terraform"
    }
  }
}

# ── 変数 ───────────────────────────────────────────────
variable "environment" {
  description = "デプロイ環境 (dev/staging/prod)"
  type        = string
}

variable "aws_region" {
  description = "AWSリージョン"
  type        = string
  default     = "ap-northeast-1"
}

variable "app_name" {
  description = "アプリケーション名"
  type        = string
  default     = "audit-agent"
}

# ── モジュール ─────────────────────────────────────────

module "vpc" {
  source = "./modules/vpc"

  app_name    = var.app_name
  environment = var.environment
  aws_region  = var.aws_region
}

module "kms" {
  source = "./modules/kms"

  app_name    = var.app_name
  environment = var.environment
}

module "s3" {
  source = "./modules/s3"

  app_name    = var.app_name
  environment = var.environment
  kms_key_arn = module.kms.key_arn
}

module "rds" {
  source = "./modules/rds"

  app_name            = var.app_name
  environment         = var.environment
  vpc_id              = module.vpc.vpc_id
  private_subnet_ids  = module.vpc.private_subnet_ids
  db_security_group_id = module.vpc.db_security_group_id
  kms_key_arn         = module.kms.key_arn
}

module "redis" {
  source = "./modules/redis"

  app_name              = var.app_name
  environment           = var.environment
  vpc_id                = module.vpc.vpc_id
  private_subnet_ids    = module.vpc.private_subnet_ids
  cache_security_group_id = module.vpc.cache_security_group_id
}

module "ecs" {
  source = "./modules/ecs"

  app_name           = var.app_name
  environment        = var.environment
  aws_region         = var.aws_region
  vpc_id             = module.vpc.vpc_id
  public_subnet_ids  = module.vpc.public_subnet_ids
  private_subnet_ids = module.vpc.private_subnet_ids
  app_security_group_id = module.vpc.app_security_group_id
  alb_security_group_id = module.vpc.alb_security_group_id
  database_url       = module.rds.connection_url
  redis_url          = module.redis.connection_url
  s3_bucket_name     = module.s3.bucket_name
  kms_key_arn        = module.kms.key_arn
}

# ── 出力 ───────────────────────────────────────────────
output "alb_dns_name" {
  description = "ALB DNS名"
  value       = module.ecs.alb_dns_name
}

output "rds_endpoint" {
  description = "RDSエンドポイント"
  value       = module.rds.endpoint
  sensitive   = true
}

output "redis_endpoint" {
  description = "Redisエンドポイント"
  value       = module.redis.endpoint
  sensitive   = true
}

output "s3_bucket" {
  description = "証跡S3バケット"
  value       = module.s3.bucket_name
}
