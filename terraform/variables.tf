# =============================================================================
# RISKCAST Infrastructure - Variables
# =============================================================================

# =============================================================================
# GENERAL
# =============================================================================

variable "project_name" {
  description = "Project name used for resource naming"
  type        = string
  default     = "riskcast"
}

variable "environment" {
  description = "Environment name (development, staging, production)"
  type        = string
  
  validation {
    condition     = contains(["development", "staging", "production"], var.environment)
    error_message = "Environment must be one of: development, staging, production."
  }
}

variable "aws_region" {
  description = "AWS region"
  type        = string
  default     = "us-east-1"
}

# =============================================================================
# VPC
# =============================================================================

variable "vpc_cidr" {
  description = "CIDR block for VPC"
  type        = string
  default     = "10.0.0.0/16"
}

variable "private_subnet_cidrs" {
  description = "CIDR blocks for private subnets"
  type        = list(string)
  default     = ["10.0.1.0/24", "10.0.2.0/24", "10.0.3.0/24"]
}

variable "public_subnet_cidrs" {
  description = "CIDR blocks for public subnets"
  type        = list(string)
  default     = ["10.0.101.0/24", "10.0.102.0/24", "10.0.103.0/24"]
}

# =============================================================================
# EKS
# =============================================================================

variable "kubernetes_version" {
  description = "Kubernetes version for EKS cluster"
  type        = string
  default     = "1.28"
}

variable "app_node_instance_types" {
  description = "Instance types for application node group"
  type        = list(string)
  default     = ["t3.large", "t3.xlarge"]
}

variable "app_node_min_size" {
  description = "Minimum number of application nodes"
  type        = number
  default     = 3
}

variable "app_node_max_size" {
  description = "Maximum number of application nodes"
  type        = number
  default     = 20
}

variable "app_node_desired_size" {
  description = "Desired number of application nodes"
  type        = number
  default     = 3
}

# =============================================================================
# RDS (PostgreSQL)
# =============================================================================

variable "db_instance_class" {
  description = "RDS instance class"
  type        = string
  default     = "db.t3.medium"
}

variable "db_allocated_storage" {
  description = "Allocated storage for RDS (GB)"
  type        = number
  default     = 20
}

variable "db_max_allocated_storage" {
  description = "Maximum allocated storage for RDS auto-scaling (GB)"
  type        = number
  default     = 100
}

# =============================================================================
# ELASTICACHE (Redis)
# =============================================================================

variable "redis_node_type" {
  description = "ElastiCache node type"
  type        = string
  default     = "cache.t3.medium"
}

# =============================================================================
# ENVIRONMENT-SPECIFIC DEFAULTS
# =============================================================================

locals {
  # Production-specific overrides
  prod_overrides = {
    app_node_instance_types = ["m5.large", "m5.xlarge"]
    app_node_min_size       = 3
    app_node_max_size       = 50
    app_node_desired_size   = 5
    db_instance_class       = "db.r6g.large"
    db_allocated_storage    = 100
    db_max_allocated_storage = 500
    redis_node_type         = "cache.r6g.large"
  }
  
  # Staging-specific overrides
  staging_overrides = {
    app_node_instance_types = ["t3.medium", "t3.large"]
    app_node_min_size       = 2
    app_node_max_size       = 10
    app_node_desired_size   = 2
    db_instance_class       = "db.t3.medium"
    db_allocated_storage    = 50
    db_max_allocated_storage = 200
    redis_node_type         = "cache.t3.medium"
  }
  
  # Development-specific overrides
  dev_overrides = {
    app_node_instance_types = ["t3.small", "t3.medium"]
    app_node_min_size       = 1
    app_node_max_size       = 5
    app_node_desired_size   = 1
    db_instance_class       = "db.t3.micro"
    db_allocated_storage    = 20
    db_max_allocated_storage = 50
    redis_node_type         = "cache.t3.micro"
  }
}
