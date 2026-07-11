variable "aws_region" {
  type    = string
  default = "eu-north-1"
}

variable "github_repo" {
  description = "GitHub repo allowed to assume the deploy role, as \"owner/repo\""
  type        = string
  default     = "DenysMerzlykyn/serverless-bookmark-manager"
}
