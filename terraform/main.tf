provider "aws" {
  region = "ap-south-1"
}

resource "aws_ecr_repository" "api_repo" {
  name = "api-repo"
}

resource "aws_ecs_cluster" "main" {
  name = "order-pipeline-cluster"
}