# AWS Deployment Guide (EXPERIMENTAL - UNTESTED)

⚠️ **WARNING: This deployment method is EXPERIMENTAL and has NOT been tested in production.**

This guide provides theoretical steps for deploying the Synthea FHIR MCP Server on AWS. Community testing and feedback are welcome.

## Status: EXPERIMENTAL

- **Testing Status**: ❌ Not tested
- **Production Ready**: ❌ No
- **Community Feedback**: Needed

If you successfully deploy on AWS, please open an issue to share your experience!

## Architecture

```mermaid
graph LR
    subgraph "Client"
        CD[Claude Desktop<br/>SSE Client]
    end

    subgraph "Amazon Web Services"
        subgraph "ECS/Fargate"
            ALB[Application<br/>Load Balancer]
            ECS[MCP Server<br/>Container]
        end

        subgraph "RDS"
            RDS[(PostgreSQL<br/>Synthea FHIR)]
        end

        subgraph "Security"
            SM[Secrets Manager<br/>Credentials]
            SG[Security Groups]
        end
    end

    CD -->|HTTPS/SSE| ALB
    ALB --> ECS
    ECS -->|SSL/TLS| RDS
    ECS -.->|Credentials| SM
    SG -->|Network Rules| ECS

    style CD fill:#e1f5fe
    style ECS fill:#ffe0b2
    style RDS fill:#f3e5f5
    style SM fill:#e8f5e9
    style SG fill:#fff9c4
```

## Prerequisites

- AWS Account with appropriate permissions
- AWS CLI configured
- Docker installed locally
- PostgreSQL database (RDS recommended)

## Database Setup (RDS PostgreSQL)

1. Create an RDS PostgreSQL instance:
```bash
aws rds create-db-instance \
  --db-instance-identifier synthea-fhir-db \
  --db-instance-class db.t3.micro \
  --engine postgres \
  --engine-version 13.7 \
  --master-username postgres \
  --master-user-password YOUR_PASSWORD \
  --allocated-storage 20 \
  --vpc-security-group-ids sg-xxxxxx \
  --publicly-accessible
```

2. Note the endpoint after creation:
```bash
aws rds describe-db-instances \
  --db-instance-identifier synthea-fhir-db \
  --query 'DBInstances[0].Endpoint.Address'
```

## Deployment Options

### Option 1: AWS App Runner (Simplest)

1. Build and push to ECR:
```bash
# Create ECR repository
aws ecr create-repository --repository-name synthea-mcp

# Get login token
aws ecr get-login-password --region us-east-1 | docker login --username AWS --password-stdin $ACCOUNT_ID.dkr.ecr.us-east-1.amazonaws.com

# Build and tag
docker build -t synthea-mcp .
docker tag synthea-mcp:latest $ACCOUNT_ID.dkr.ecr.us-east-1.amazonaws.com/synthea-mcp:latest

# Push
docker push $ACCOUNT_ID.dkr.ecr.us-east-1.amazonaws.com/synthea-mcp:latest
```

2. Create App Runner service via console or CLI with environment variables:
- `AWS_RDS_ENDPOINT`: Your RDS endpoint
- `DB_USER`: postgres
- `DB_PASSWORD`: Your password
- `DB_NAME`: synthea

### Option 2: ECS with Fargate

Use the provided `task-definition.json`:

```bash
# Register task definition
aws ecs register-task-definition --cli-input-json file://task-definition.json

# Create service
aws ecs create-service \
  --cluster default \
  --service-name synthea-mcp \
  --task-definition synthea-mcp:1 \
  --desired-count 1 \
  --launch-type FARGATE \
  --network-configuration "awsvpcConfiguration={subnets=[subnet-xxx],securityGroups=[sg-xxx],assignPublicIp=ENABLED}"
```

### Option 3: Elastic Beanstalk

1. Create `Dockerrun.aws.json`:
```json
{
  "AWSEBDockerrunVersion": "1",
  "Image": {
    "Name": "$ACCOUNT_ID.dkr.ecr.us-east-1.amazonaws.com/synthea-mcp:latest"
  },
  "Ports": [
    {
      "ContainerPort": 8080,
      "HostPort": 8080
    }
  ]
}
```

2. Deploy:
```bash
eb init -p docker synthea-mcp
eb create synthea-env
eb setenv AWS_RDS_ENDPOINT=xxx DB_USER=xxx DB_PASSWORD=xxx
```

## Environment Variables

Required environment variables for AWS deployment:

```env
# AWS RDS Configuration
AWS_RDS_ENDPOINT=your-db.xxx.rds.amazonaws.com
AWS_RDS_PORT=5432
DB_USER=postgres
DB_PASSWORD=your_secure_password
DB_NAME=synthea

# Optional
AWS_RDS_SSL=true  # Enable SSL (recommended)
AWS_RDS_USE_IAM=false  # IAM auth (not yet implemented)
```

## Security Considerations

⚠️ **IMPORTANT**: Since this is untested, pay special attention to:

1. **Network Security**:
   - Configure Security Groups properly
   - Use VPC endpoints for private connectivity
   - Enable SSL for RDS connections

2. **Secrets Management**:
   - Use AWS Secrets Manager for passwords
   - Use IAM roles instead of keys where possible

3. **Access Control**:
   - Implement proper IAM policies
   - Consider using AWS WAF if exposing publicly

## Load Test Data

After deployment, load Synthea data:

```bash
# Connect to your container/instance
# Run the data generation and loading scripts
python scripts/generate_synthea_data.py
python scripts/load_synthea_data.py --synthea-dir synthea/output
```

## Monitoring

Set up CloudWatch monitoring:
- Container/instance metrics
- RDS metrics
- Application logs

## Cost Estimates

Approximate monthly costs (varies by region and usage):
- RDS db.t3.micro: ~$15
- App Runner: ~$5-50 depending on usage
- ECS Fargate: ~$10-50 depending on usage
- Data transfer: Variable

## Troubleshooting

Common issues (theoretical):

1. **Connection timeouts**: Check security groups
2. **Authentication failures**: Verify RDS credentials
3. **SSL errors**: Ensure RDS SSL certificates are trusted

## Contributing

**We need your help!** If you deploy this on AWS:

1. Test the deployment
2. Document any issues or changes needed
3. Open an issue or PR with your findings
4. Help us mark this as "tested" once verified

## Disclaimer

This AWS deployment guide is provided as-is without warranty. It has NOT been tested in production. Use at your own risk and ensure proper security measures are in place.