data "archive_file" "placeholder" {
  type        = "zip"
  source_dir  = "${path.module}/placeholder"
  output_path = "${path.module}/.placeholder-${var.environment}.zip"
}

# Created explicitly (rather than letting Lambda auto-create it on first
# invoke) so retention can be bounded and its exact ARN referenced below -
# without this, AWS's default is "never expire" and the only alternative
# for scoping the IAM policy would be a wildcard.
#
# Accepted trade-off (see ARCHITECTURE.md): AWS-managed encryption is fine here; a customer KMS key costs ~$1/mo, which this project deliberately avoids (see ARCHITECTURE.md's Security model)
# Accepted trade-off (see ARCHITECTURE.md): 14-day retention is a deliberate cost control for a portfolio project's low-value logs, not an oversight - see log_retention_days in variables.tf
resource "aws_cloudwatch_log_group" "this" {
  name              = "/aws/lambda/${var.project_name}-${var.environment}"
  retention_in_days = var.log_retention_days
}

resource "aws_iam_role" "lambda_execution" {
  name = "${var.project_name}-${var.environment}-execution"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect    = "Allow"
      Principal = { Service = "lambda.amazonaws.com" }
      Action    = "sts:AssumeRole"
    }]
  })
}

# Least-privilege: scoped to this function's own log group only, not
# logs:* on all resources.
resource "aws_iam_role_policy" "lambda_logging" {
  name = "logging"
  role = aws_iam_role.lambda_execution.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect   = "Allow"
      Action   = ["logs:CreateLogStream", "logs:PutLogEvents"]
      Resource = "${aws_cloudwatch_log_group.this.arn}:*"
    }]
  })
}

# X-Ray has its own always-free tier (100k traces/month) - a portfolio
# project's traffic will never come close, so this is free observability,
# not a trade-off. logs:*/xray:* wildcards aren't needed: X-Ray only
# supports resource="*" for these actions (no per-trace ARNs to scope to).
resource "aws_iam_role_policy" "lambda_xray" {
  name = "xray-tracing"
  role = aws_iam_role.lambda_execution.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect   = "Allow"
      Action   = ["xray:PutTraceSegments", "xray:PutTelemetryRecords"]
      Resource = "*"
    }]
  })
}

# Accepted trade-off (see ARCHITECTURE.md): Code-signing (AWS Signer) needs a signing-profile/job setup with marginal benefit for a single-maintainer project; GitHub Actions OIDC already gives strong deploy provenance (only that pipeline can update this function)
# Accepted trade-off (see ARCHITECTURE.md): DLQ is for async (Event) invocations; this function is invoked synchronously via its Function URL, so there's no async failure path to redirect
# Accepted trade-off (see ARCHITECTURE.md): Same reasoning as the log group above - AWS-managed encryption, not a customer KMS key, to avoid the ~$1/mo cost
# Accepted trade-off (see ARCHITECTURE.md): VPC placement would need a NAT Gateway for this function's internet egress (it calls Neon Postgres over the public internet) - NAT Gateways aren't free-tier and directly contradict this project's permanently-free-tier constraint
resource "aws_lambda_function" "this" {
  function_name = "${var.project_name}-${var.environment}"
  role          = aws_iam_role.lambda_execution.arn

  filename         = data.archive_file.placeholder.output_path
  source_code_hash = data.archive_file.placeholder.output_base64sha256
  handler          = "handler.handler"
  runtime          = "python3.12"
  timeout          = var.lambda_timeout
  memory_size      = var.lambda_memory_size
  publish          = true

  reserved_concurrent_executions = var.reserved_concurrent_executions

  tracing_config {
    mode = "Active"
  }

  environment {
    variables = var.environment_variables
  }

  # Terraform provisions the function; CI/CD (deploy-dev.yml/deploy-prod.yml,
  # not yet built) owns what code actually runs on it via
  # `aws lambda update-function-code` + publishing new versions. Without
  # this, a future `terraform apply` would revert the real app back to this
  # placeholder.
  lifecycle {
    ignore_changes = [filename, source_code_hash, handler, publish]
  }

  depends_on = [aws_cloudwatch_log_group.this, aws_iam_role_policy.lambda_logging, aws_iam_role_policy.lambda_xray]
}

# CI/CD repoints this on every deploy/rollback; the Function URL below
# invokes through it rather than through $LATEST directly.
#
# ignore_changes on function_version means Terraform will never revert a
# CI-driven rollback - but it also means Terraform's *own* changes never
# move the alias forward. A terraform apply that edits function config
# (env vars, memory, etc.) publishes a new version same as any other
# change, but "live" stays frozen on whatever version it already pointed
# to until something explicitly repoints it. Hit this directly: an env
# var change applied cleanly but the fix wasn't actually live until
# `aws lambda update-alias --function-version <n>` was run by hand. Once
# the deploy workflow exists it'll own repointing on every code deploy;
# until then, any Terraform-only apply that changes function config needs
# that same manual step afterward.
resource "aws_lambda_alias" "live" {
  name             = "live"
  function_name    = aws_lambda_function.this.function_name
  function_version = aws_lambda_function.this.version

  lifecycle {
    ignore_changes = [function_version]
  }
}

# Accepted trade-off (see ARCHITECTURE.md's Security model): the SPA calls this directly and can't do SigV4 signing, so auth=NONE is required; access control is enforced in the FastAPI JWT layer instead
#
# Deliberately no `cors` block here: FastAPI's own CORSMiddleware (configured
# via the CORS_ALLOWED_ORIGINS environment variable, see environment_variables)
# is the single owner of CORS for this app. If both the Function URL's CORS
# feature and the app's own middleware added Access-Control-Allow-Origin,
# the response would carry it twice - which browsers reject outright, not
# just warn about. The app needs its own CORS handling regardless (there's
# no Function URL in front of it during local development), so that's the
# one place it's configured.
resource "aws_lambda_function_url" "this" {
  function_name      = aws_lambda_function.this.function_name
  qualifier          = aws_lambda_alias.live.name
  authorization_type = "NONE" # public - see ARCHITECTURE.md's Security model
}
