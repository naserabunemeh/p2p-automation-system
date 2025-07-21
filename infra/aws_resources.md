# AWS Resources Architecture

## Overview

This document outlines the AWS architecture for the ERP-Lite Procure-to-Pay (P2P) Automation System. The system is designed to be scalable, secure, and cost-effective while providing enterprise-grade functionality.

## Architecture Diagram

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   API Gateway   │────│   Lambda/ECS    │────│    DynamoDB     │
│   (REST API)    │    │   (FastAPI)     │    │   (Database)    │
└─────────────────┘    └─────────────────┘    └─────────────────┘
         │                       │                       │
         │                       │                       │
         ▼                       ▼                       ▼
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   CloudFront    │    │       S3        │    │   CloudWatch    │
│    (CDN)        │    │   (Storage)     │    │  (Monitoring)   │
└─────────────────┘    └─────────────────┘    └─────────────────┘
```

## Core AWS Services

### 1. Compute Services

#### Amazon ECS (Elastic Container Service)
- **Purpose**: Container orchestration for FastAPI application
- **Configuration**: 
  - Fargate launch type for serverless containers
  - Auto-scaling based on CPU/memory utilization
  - Load balancer integration
- **Estimated Cost**: $30-100/month depending on usage

#### AWS Lambda (Alternative)
- **Purpose**: Serverless compute for API endpoints
- **Configuration**: Python 3.9+ runtime
- **Use Case**: For lower traffic scenarios
- **Estimated Cost**: $0-20/month for development

### 2. Database Services

#### Amazon DynamoDB
- **Purpose**: Primary database for all P2P entities
- **Tables**:
  - `p2p_vendors` - Vendor information
  - `p2p_purchase_orders` - Purchase order data
  - `p2p_invoices` - Invoice records
  - `p2p_payments` - Payment transactions
- **Configuration**: 
  - On-demand billing mode for variable workloads
  - Global Secondary Indexes (GSI) for query optimization
  - Point-in-time recovery enabled
- **Estimated Cost**: $10-50/month

**Table Schemas:**

```python
# Vendors Table
{
  "id": "string",           # Partition Key
  "name": "string",
  "email": "string",
  "phone": "string",
  "address": "string", 
  "tax_id": "string",
  "payment_terms": "string",
  "status": "string",
  "created_at": "timestamp",
  "updated_at": "timestamp"
}

# Purchase Orders Table
{
  "id": "string",           # Partition Key
  "vendor_id": "string",    # GSI Partition Key
  "po_number": "string",
  "description": "string",
  "line_items": "list",
  "total_amount": "number",
  "status": "string",
  "requested_by": "string",
  "approved_by": "string",
  "delivery_date": "timestamp",
  "created_at": "timestamp",
  "updated_at": "timestamp"
}

# Invoices Table
{
  "id": "string",           # Partition Key
  "vendor_id": "string",    # GSI Partition Key
  "po_id": "string",        # GSI Partition Key
  "invoice_number": "string",
  "invoice_date": "timestamp",
  "due_date": "timestamp",
  "line_items": "list",
  "subtotal": "number",
  "tax_amount": "number",
  "total_amount": "number",
  "status": "string",
  "approved_by": "string",
  "notes": "string",
  "created_at": "timestamp",
  "updated_at": "timestamp"
}

# Payments Table
{
  "id": "string",           # Partition Key
  "invoice_id": "string",   # GSI Partition Key
  "vendor_id": "string",    # GSI Partition Key
  "payment_amount": "number",
  "payment_method": "string",
  "payment_date": "timestamp",
  "reference_number": "string",
  "status": "string",
  "processed_by": "string",
  "notes": "string",
  "created_at": "timestamp",
  "updated_at": "timestamp"
}
```

### 3. Storage Services

#### Amazon S3
- **Purpose**: File storage for XML/JSON exports, documents, and backups
- **Buckets**:
  - `p2p-automation-payments` - Payment XML/JSON files
  - `p2p-automation-documents` - Invoice PDFs, contracts
  - `p2p-automation-backups` - Database backups
- **Configuration**:
  - Versioning enabled
  - Server-side encryption (SSE-S3)
  - Lifecycle policies for cost optimization
- **Estimated Cost**: $5-20/month

### 4. API Services

#### Amazon API Gateway
- **Purpose**: RESTful API management and routing
- **Features**:
  - Request/response transformation
  - Rate limiting and throttling
  - API key management
  - CORS configuration
- **Estimated Cost**: $3-15/month

### 5. Security Services

#### AWS IAM (Identity and Access Management)
- **Purpose**: Access control and permissions
- **Components**:
  - Service roles for ECS/Lambda
  - User policies for admin access
  - Cross-service permissions

#### AWS KMS (Key Management Service)
- **Purpose**: Encryption key management
- **Use Cases**:
  - DynamoDB encryption at rest
  - S3 bucket encryption
  - Application secrets encryption

### 6. Monitoring and Logging

#### Amazon CloudWatch
- **Purpose**: Application monitoring and alerting
- **Features**:
  - Application logs centralization
  - Custom metrics tracking
  - Alarm configuration
  - Dashboard creation
- **Estimated Cost**: $5-25/month

#### AWS X-Ray (Optional)
- **Purpose**: Distributed tracing and performance analysis
- **Use Case**: API performance monitoring
- **Estimated Cost**: $2-10/month

## Environment Setup

### Development Environment
- **Compute**: AWS Lambda with minimal configuration
- **Database**: DynamoDB with on-demand billing
- **Storage**: Single S3 bucket with basic configuration
- **Estimated Monthly Cost**: $20-40

### Production Environment
- **Compute**: ECS Fargate with auto-scaling
- **Database**: DynamoDB with provisioned capacity
- **Storage**: Multiple S3 buckets with advanced features
- **Monitoring**: Full CloudWatch and X-Ray implementation
- **Estimated Monthly Cost**: $100-300

## Deployment Strategy

### Infrastructure as Code (IaC)
- **Tool**: AWS CloudFormation or Terraform
- **Benefits**: Version control, repeatability, rollback capability
- **Files**: 
  - `cloudformation/p2p-infrastructure.yaml`
  - `terraform/main.tf` (alternative)

### CI/CD Pipeline
- **Tool**: AWS CodePipeline + CodeBuild
- **Stages**:
  1. Source (GitHub integration)
  2. Build (Docker image creation)
  3. Test (Automated testing)
  4. Deploy (ECS service update)

### Container Strategy
- **Registry**: Amazon ECR (Elastic Container Registry)
- **Base Image**: Python 3.9-slim
- **Security**: Image vulnerability scanning enabled

## Security Considerations

### Network Security
- **VPC**: Dedicated Virtual Private Cloud
- **Subnets**: Private subnets for compute resources
- **Security Groups**: Restrictive ingress/egress rules
- **NAT Gateway**: Outbound internet access for private resources

### Data Security
- **Encryption at Rest**: All data encrypted using AWS KMS
- **Encryption in Transit**: TLS 1.2+ for all communications
- **Access Logs**: S3 access logging enabled
- **Database Security**: DynamoDB point-in-time recovery

### Application Security
- **Authentication**: JWT token-based authentication
- **Authorization**: Role-based access control (RBAC)
- **Input Validation**: Comprehensive request validation
- **Rate Limiting**: API Gateway throttling policies

## Scalability Considerations

### Auto-Scaling
- **ECS**: CPU and memory-based scaling policies
- **DynamoDB**: Auto-scaling for read/write capacity
- **Load Balancing**: Application Load Balancer (ALB)

### Performance Optimization
- **Caching**: ElastiCache for frequently accessed data
- **CDN**: CloudFront for static content delivery
- **Database**: GSI optimization for query performance

## Disaster Recovery

### Backup Strategy
- **DynamoDB**: Point-in-time recovery (PITR)
- **S3**: Cross-region replication for critical data
- **Application**: Multi-AZ deployment

### Recovery Plan
- **RTO** (Recovery Time Objective): 4 hours
- **RPO** (Recovery Point Objective): 1 hour
- **Process**: Documented runbooks and automated recovery scripts

## Cost Optimization

### Right-Sizing
- **Regular Reviews**: Monthly cost analysis
- **Reserved Instances**: For predictable workloads
- **Spot Instances**: For non-critical batch processing

### Resource Management
- **Lifecycle Policies**: S3 storage class transitions
- **Unused Resources**: Automated cleanup scripts
- **Monitoring**: Cost alerts and budgets

## Next Steps

### Phase 1: MVP Deployment
1. Setup basic DynamoDB tables
2. Deploy FastAPI application to Lambda
3. Configure API Gateway
4. Basic S3 bucket for file storage

### Phase 2: Production Ready
1. Migrate to ECS Fargate
2. Implement comprehensive monitoring
3. Setup CI/CD pipeline
4. Configure multi-environment support

### Phase 3: Enterprise Features
1. Advanced security features
2. Multi-region deployment
3. Enhanced monitoring and alerting
4. Workday API integration

## Resource Estimation Summary

| Component | Development | Production |
|-----------|-------------|------------|
| Compute | $10-20 | $50-100 |
| Database | $5-15 | $25-75 |
| Storage | $2-5 | $10-25 |
| Networking | $3-8 | $15-30 |
| Monitoring | $2-5 | $10-20 |
| **Total** | **$22-53** | **$110-250** |

*Costs are monthly estimates in USD and may vary based on actual usage patterns.* 