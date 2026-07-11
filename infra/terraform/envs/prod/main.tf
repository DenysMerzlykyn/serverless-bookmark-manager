terraform {
  required_version = ">= 1.13"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 6.0"
    }
    archive = {
      source  = "hashicorp/archive"
      version = "~> 2.0"
    }
  }

  # Local state for now - migrates to a Terraform Cloud workspace once that
  # account exists (see ARCHITECTURE.md's IaC section for why TFC over
  # S3+DynamoDB). Tracked as a known gap, not an oversight.
}

provider "aws" {
  region = var.aws_region

  default_tags {
    tags = {
      Project     = "serverless-bookmark-manager"
      Environment = "prod"
      ManagedBy   = "terraform"
    }
  }
}

module "lambda_api" {
  source = "../../modules/lambda_api"

  environment           = "prod"
  aws_region            = var.aws_region
  cors_allowed_origins  = var.cors_allowed_origins
  environment_variables = var.environment_variables
}
