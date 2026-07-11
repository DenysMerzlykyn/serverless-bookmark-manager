output "function_name" {
  value = aws_lambda_function.this.function_name
}

output "function_arn" {
  value = aws_lambda_function.this.arn
}

output "function_url" {
  value = aws_lambda_function_url.this.function_url
}

output "execution_role_arn" {
  value = aws_iam_role.lambda_execution.arn
}
