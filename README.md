# Cloud Computing TP - Fast Track Delivery

This repository contains the Terraform code for our "TP2: Fast Track Delivery" project. This code deploys a 100% serverless architecture on AWS, which replaces our previous EC2-based monolithic application.

## Target Architecture

We are building the following event-driven, serverless architecture:

![Architecture Diagram](./architecture-diagram.jpg)

## Prerequisites

Before you begin, ensure you have the following tools installed and configured:

1.  **Terraform:** [Install Guide](https://learn.hashicorp.com/tutorials/terraform/install-cli)
2.  **AWS CLI:** [Install Guide](https://docs.aws.amazon.com/cli/latest/userguide/cli-chap-install.html)
3.  **AWS Credentials:** Your AWS CLI must be configured with valid credentials (`aws configure`).
4. Verify the credentials are valid:
```bash
aws sts get-caller-identity
```

## Project Structure

The infrastructure is organized into logical modules:

* `/modules/network`: Creates the VPC, Subnets, and VPC Endpoints for private connectivity.
* `/modules/database`: Deploys the DynamoDB Single-Table for all our data.
* `/modules/backend`: Deploys Cognito, API Gateway, all Lambda functions, and their IAM Roles.
* `/modules/events`: Creates the SNS topic and SQS queue for asynchronous notifications.
* `/modules/frontend`: Creates the S3 bucket configured for static website hosting (no CloudFront).

## How to Deploy

Follow these steps to deploy the infrastructure to your AWS account.

### 1. Deploy infraestructre

Download the AWS provider and any modules.

```bash
# Initalize terraform
terraform init

# See what is about to be created
terraform plan

# Create AWS architecture
terraform apply
```
Write `yes` when asked

### 2. Verify deployment

```bash
# See outputs
terraform output

# Test API
curl $(terraform output -raw api_endpoint)/packages
```

### 3. Destroy deployment
```bash
# Empty S3 buckets
aws s3 rm s3://fast-track-delivery-serverless-images-bucket --recursive
aws s3 rm s3://fast-track-delivery-serverless-frontend-bucket --recursive

# Destroy all
terraform destroy
```
Write `yes` when asked
