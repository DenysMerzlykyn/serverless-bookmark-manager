variable "environment" {
  description = "Environment name - used in resource names and tags"
  type        = string

  validation {
    condition     = contains(["dev", "prod"], var.environment)
    error_message = "environment must be \"dev\" or \"prod\"."
  }
}

variable "project_name" {
  description = "Short project slug used in resource names"
  type        = string
  default     = "bookmarks-api"
}

variable "aws_region" {
  description = "AWS region to deploy into"
  type        = string
}

variable "reserved_concurrent_executions" {
  description = "Caps simultaneous executions. The Function URL is public (auth=NONE - see ARCHITECTURE.md's Security model), so this bounds the blast-radius cost/account-concurrency-exhaustion risk of abuse traffic rather than relying on a WAF, which isn't free. Defaults to null (unmanaged/shared pool): a brand-new AWS account's account-wide concurrency limit starts at 10, and AWS requires at least 10 to stay unreserved - there's no room to reserve any amount until that limit is raised (AWS does this automatically over time, or it can be requested). Revisit once the account limit increases."
  type        = number
  default     = null
}

variable "lambda_timeout" {
  type    = number
  default = 10
}

variable "lambda_memory_size" {
  type    = number
  default = 256
}

variable "log_retention_days" {
  description = "Bounds CloudWatch Logs storage cost - AWS's default for a log group is to never expire."
  type        = number
  default     = 14
}

variable "environment_variables" {
  description = "Lambda environment variables (DATABASE_URL, JWT_SECRET_KEY, etc.). Supplied by the calling env config from a gitignored *.tfvars file or CI secrets - never hardcoded here."
  type        = map(string)
  sensitive   = true
}
