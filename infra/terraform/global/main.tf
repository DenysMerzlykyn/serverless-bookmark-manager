terraform {
  required_version = ">= 1.13"

  cloud {
    organization = "denys-bookmarks"
    workspaces {
      name = "serverless-bookmark-manager-global"
    }
  }

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

  # This stack holds account-wide singletons (the OIDC provider can only
  # exist once per account), so it's applied separately from envs/dev and
  # envs/prod - each has its own Terraform Cloud workspace/state.
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
  #
  # Each function needs BOTH the bare ARN (actions like UpdateFunctionCode
  # target the unqualified function) and a ":*" wildcard ARN (actions like
  # GetFunctionUrlConfig/GetAlias made with --qualifier live are checked by
  # IAM against the alias-qualified ARN, e.g. "...function:name:live", which
  # does not string-match the bare ARN at all).
  lambda_base_arns = [
    for env in ["dev", "prod"] :
    "arn:aws:lambda:${var.aws_region}:${data.aws_caller_identity.current.account_id}:function:${local.project_name}-${env}"
  ]
  lambda_function_arns = flatten([
    for arn in local.lambda_base_arns : [arn, "${arn}:*"]
  ])
}

module "github_oidc" {
  source = "../modules/github_oidc"

  github_repo          = var.github_repo
  lambda_function_arns = local.lambda_function_arns
}
