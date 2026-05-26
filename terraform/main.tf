provider "aws" {
  region = "ap-south-1"
}

resource "aws_ecr_repository" "api_repo" {
  name = "api-repo"
}

resource "aws_eks_cluster" "main" {
  name     = "order-pipeline-cluster"
  role_arn = aws_iam_role.eks_role.arn

  vpc_config {
    subnet_ids = ["subnet-xxxx", "subnet-yyyy"]
  }
}