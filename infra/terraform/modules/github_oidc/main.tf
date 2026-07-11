terraform {
  required_providers {
    aws = { source = "hashicorp/aws" }
    tls = { source = "hashicorp/tls" }
  }
}

data "tls_certificate" "github" {
  url = "https://token.actions.githubusercontent.com/.well-known/openid-configuration"
}

resource "aws_iam_openid_connect_provider" "github" {
  url             = "https://token.actions.githubusercontent.com"
  client_id_list  = ["sts.amazonaws.com"]
  thumbprint_list = [data.tls_certificate.github.certificates[0].sha1_fingerprint]
}

resource "aws_iam_role" "github_actions" {
  name = var.role_name

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect    = "Allow"
      Principal = { Federated = aws_iam_openid_connect_provider.github.arn }
      Action    = "sts:AssumeRoleWithWebIdentity"
      Condition = {
        StringEquals = {
          "token.actions.githubusercontent.com:aud" = "sts.amazonaws.com"
        }
        # Restricts to this repo only - any branch/tag/PR from it. Could be
        # tightened further to e.g. "repo:${var.github_repo}:ref:refs/heads/main"
        # once the deploy workflows are split by trigger, but that's not
        # built yet.
        StringLike = {
          "token.actions.githubusercontent.com:sub" = "repo:${var.github_repo}:*"
        }
      }
    }]
  })
}

# Scoped to exactly what the deploy workflows need on the two Lambda
# functions - not lambda:* and not Resource "*".
resource "aws_iam_role_policy" "deploy" {
  name = "deploy-lambda"
  role = aws_iam_role.github_actions.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect = "Allow"
      Action = [
        "lambda:UpdateFunctionCode",
        "lambda:PublishVersion",
        "lambda:UpdateAlias",
        "lambda:GetFunction",
        "lambda:GetAlias",
      ]
      Resource = var.lambda_function_arns
    }]
  })
}
