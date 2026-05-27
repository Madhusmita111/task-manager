terraform {
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}

provider "aws" {
  region = var.region
}

# ECR Repositories for all 3 microservices
resource "aws_ecr_repository" "api_repo" {
  name                 = "task-manager-api"
  image_tag_mutability = "MUTABLE"
  force_delete         = true
}

resource "aws_ecr_repository" "producer_repo" {
  name                 = "task-manager-producer"
  image_tag_mutability = "MUTABLE"
  force_delete         = true
}

resource "aws_ecr_repository" "processor_repo" {
  name                 = "task-manager-processor"
  image_tag_mutability = "MUTABLE"
  force_delete         = true
}
