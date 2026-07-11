def handler(event, context):
    """Placeholder only - Terraform needs a valid deployment package to
    create the function at all. The real FastAPI/Mangum app is deployed
    over this by CI/CD (see deploy-dev.yml/deploy-prod.yml), which is why
    the aws_lambda_function resource ignores changes to its code/handler
    after creation - Terraform provisions the function, CI/CD owns what
    code actually runs on it.
    """
    return {
        "statusCode": 200,
        "body": "placeholder - real app deployed via CI/CD, not yet deployed",
    }
