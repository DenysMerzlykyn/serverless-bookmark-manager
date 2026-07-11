variable "aws_region" {
  type    = string
  default = "eu-north-1"
}

variable "cors_allowed_origins" {
  description = "The deployed production frontend's origin(s)"
  type        = list(string)
  default     = []
}

variable "environment_variables" {
  description = "DATABASE_URL, JWT_SECRET_KEY, etc. for the prod Lambda function"
  type        = map(string)
  sensitive   = true
}
