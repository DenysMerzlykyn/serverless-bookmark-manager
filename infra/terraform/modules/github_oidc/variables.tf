variable "github_repo" {
  description = "GitHub repo allowed to assume this role, as \"owner/repo\""
  type        = string
}

variable "role_name" {
  type    = string
  default = "github-actions-deploy"
}

variable "lambda_function_arns" {
  description = "ARNs of the Lambda functions this role may update/publish/repoint. Constructed from the naming convention shared with the lambda_api module rather than a cross-stack state read, since these functions live in separate Terraform states (envs/dev, envs/prod)."
  type        = list(string)
}
