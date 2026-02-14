# ═══════════════════════════════════════════════════════
# audit-agent 本番環境
# ═══════════════════════════════════════════════════════

terraform {
  backend "s3" {
    bucket         = "audit-agent-terraform-state"
    key            = "prod/terraform.tfstate"
    region         = "ap-northeast-1"
    encrypt        = true
    dynamodb_table = "audit-agent-terraform-lock"
  }
}

module "audit_agent" {
  source = "../../"

  environment = "prod"
  aws_region  = "ap-northeast-1"
  app_name    = "audit-agent"
}

output "alb_dns_name" { value = module.audit_agent.alb_dns_name }
output "s3_bucket" { value = module.audit_agent.s3_bucket }
