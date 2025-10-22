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

* `/modules/dynamodb`: Defines the reusable module that creates DynamoDB databases according to the parameters set in the main configuration.
* `/modules/lambda-api`: Creates Lambda functions for the API backend.
* `/modules/s3-bucket`: Defines the reusable module that creates S3 buckets for static file storage according to the parameters set in the main configuration.

## How to Deploy

Follow these steps to deploy the infrastructure to your AWS account.

### 1. Deploy infraestructre

Create the backend that is assigned to each lambda function.

Run `python .\script.py` to create the zip files for each lambda function.

Download the AWS provider and any modules.

```bash
# Initalize terraform
terraform init

# See what is about to be created
terraform plan -var-file="dev.tfvars" -out=tfplan 

# Create AWS architecture
terraform apply -auto-approve tfplan

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
