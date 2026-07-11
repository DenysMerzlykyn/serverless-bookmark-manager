terraform {
  required_version = ">= 1.13"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 6.0"
    }
    tls = {
      source  = "hashicorp/tls"
      version = "~> 4.0"
    }
  }

  # Local state for now - see envs/*/main.tf for the same note on migrating
  # to Terraform Cloud. This stack holds account-wide singletons (the OIDC
  # provider can only exist once per account), so it's applied separately
  # from envs/dev and envs/prod.
}

provider "aws" {
  region = var.aws_region

  default_tags {
    tags = {
      Project   = "serverless-bookmark-manager"
      ManagedBy = "terraform"
    }
  }
}

data "aws_caller_identity" "current" {}

locals {
  project_name = "bookmarks-api"

  # Constructed from the naming convention shared with the lambda_api
  # module rather than a cross-stack state read: envs/dev and envs/prod are
  # separate Terraform states, but Lambda ARNs are fully deterministic
  # before the function exists, so the IAM policy can reference them
  # directly.
  lambda_function_arns = [
    for env in ["dev", "prod"] :
    "arn:aws:lambda:${var.aws_region}:${data.aws_caller_identity.current.account_id}:function:${local.project_name}-${env}"
  ]
}

module "github_oidc" {
  source = "../modules/github_oidc"

  github_repo          = var.github_repo
  lambda_function_arns = local.lambda_function_arns
}
