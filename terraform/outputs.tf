output "ecr_api_url" {
  description = "ECR URL for the API service"
  value       = aws_ecr_repository.api_repo.repository_url
}

output "ecr_producer_url" {
  description = "ECR URL for the Producer service"
  value       = aws_ecr_repository.producer_repo.repository_url
}

output "ecr_processor_url" {
  description = "ECR URL for the Processor service"
  value       = aws_ecr_repository.processor_repo.repository_url
}

output "eks_cluster_name" {
  description = "EKS Cluster name"
  value       = aws_eks_cluster.cluster.name
}

output "eks_cluster_endpoint" {
  description = "EKS Cluster API endpoint"
  value       = aws_eks_cluster.cluster.endpoint
}