# Multi-Cloud Deployment Support

This document describes the multi-cloud capabilities of the Synthea FHIR MCP Server.

## Overview

The Synthea FHIR MCP Server is designed to work across multiple cloud platforms while maintaining full backward compatibility with existing Google Cloud Platform deployments.

## Current Status

| Cloud Provider | Status | Testing | Production Ready | Documentation |
|---------------|--------|---------|------------------|---------------|
| **Google Cloud Platform** | ✅ **Production** | Fully Tested | Yes | [GCP Guide](../deploy/gcp/README.md) |
| **Amazon Web Services** | ⚠️ Experimental | Not Tested | No | [AWS Guide](../deploy/aws/README.md) |
| **Microsoft Azure** | ⚠️ Experimental | Not Tested | No | [Azure Guide](../deploy/azure/README.md) |
| **Local/Docker** | ✅ Supported | Tested | Yes | [Development Guide](DEVELOPMENT.md) |

## Architecture

The multi-cloud architecture uses a provider detection system that maintains backward compatibility:

```python
# Connection flow
1. Check for GCP (CLOUD_SQL_CONNECTION_NAME) - existing logic unchanged
2. Check for AWS (AWS_RDS_ENDPOINT)
3. Check for Azure (AZURE_POSTGRES_HOST)
4. Fall back to DATABASE_URL (local/generic)
```

## No Breaking Changes

**Important**: The multi-cloud implementation introduces NO breaking changes:
- Existing GCP deployments continue to work exactly as before
- The original connection logic for Cloud SQL remains unchanged
- New cloud providers are detected only if GCP environment variables are not present
- All new code is additive, not replacing existing functionality

## Cloud Provider Detection

The system automatically detects the cloud provider based on environment variables:

### Google Cloud Platform
```env
CLOUD_SQL_CONNECTION_NAME=project:region:instance
DB_USER=username
DB_PASSWORD=password
DB_NAME=synthea
```

### AWS (Experimental)
```env
AWS_RDS_ENDPOINT=your-db.region.rds.amazonaws.com
AWS_RDS_PORT=5432
DB_USER=username
DB_PASSWORD=password
DB_NAME=synthea
```

### Azure (Experimental)
```env
AZURE_POSTGRES_HOST=your-server.postgres.database.azure.com
AZURE_POSTGRES_PORT=5432
DB_USER=username
DB_PASSWORD=password
DB_NAME=synthea
```

### Local/Generic
```env
DATABASE_URL=postgresql://user:pass@host:port/database
```

## Implementation Details

### Cloud Detector Module

The `src/cloud_detector.py` module provides:
- Automatic cloud provider detection
- Provider-specific connection string builders
- Cloud-specific configuration and recommendations
- Warning messages for untested providers

### Modified Server Code

The `src/synthea_server.py` includes:
- Optional import of cloud detector (graceful fallback if not available)
- Provider detection at startup with appropriate warnings
- Connection string routing based on detected provider

### Directory Structure

```
deploy/
├── aws/                    # AWS deployment (EXPERIMENTAL)
│   ├── README.md          # Detailed AWS guide with warnings
│   ├── .env.aws.example
│   └── task-definition.json
├── azure/                  # Azure deployment (EXPERIMENTAL)
│   ├── README.md          # Detailed Azure guide with warnings
│   └── .env.azure.example
└── gcp/                    # GCP deployment (PRODUCTION READY)
    ├── README.md          # Production guide
    └── deploy.sh          # Automated deployment script
```

## Security Considerations

### Production (GCP)
- ✅ Tested security configurations
- ✅ Cloud SQL Proxy for secure connections
- ✅ Secret Manager integration
- ✅ VPC and firewall rules documented

### Experimental (AWS/Azure)
- ⚠️ Security configurations are theoretical
- ⚠️ Not tested in production environments
- ⚠️ Users must implement proper security measures
- ⚠️ Follow cloud provider best practices

## Contributing

We welcome community contributions to test and improve multi-cloud support!

### How to Help

1. **Test AWS/Azure Deployments**
   - Follow the experimental deployment guides
   - Document any issues or required changes
   - Share your configuration and results

2. **Submit Feedback**
   - Open issues for problems encountered
   - Suggest improvements to deployment guides
   - Share successful deployment configurations

3. **Contribute Code**
   - Fix issues in cloud detection
   - Improve connection string builders
   - Add cloud-specific features

### Testing Checklist

If you test AWS or Azure deployment, please verify:

- [ ] Container builds and runs successfully
- [ ] Database connection works
- [ ] All MCP tools function correctly
- [ ] SSE endpoint responds properly
- [ ] Claude Desktop can connect and query data
- [ ] Performance is acceptable
- [ ] Security configurations are appropriate

## Migration Guide

### From GCP to Other Clouds

**Note**: Since AWS/Azure are untested, migration is not recommended for production.

If you want to experiment:

1. Export data from Cloud SQL
2. Import to target cloud database
3. Update environment variables
4. Deploy using experimental guides
5. Test thoroughly before any production use

### Maintaining GCP Deployment

No changes needed! Your existing GCP deployment will continue to work exactly as it does today.

## Roadmap

### Phase 1 (Complete) ✅
- Multi-cloud architecture without breaking changes
- AWS and Azure experimental support
- Documentation and deployment guides

### Phase 2 (Community Driven) 🚧
- Community testing of AWS deployment
- Community testing of Azure deployment
- Gathering feedback and issues

### Phase 3 (Future) 📅
- Incorporate community feedback
- Fix identified issues
- Mark clouds as "tested" when validated
- Add cloud-specific optimizations

## FAQ

### Will this break my existing GCP deployment?
No. The multi-cloud support is purely additive. Existing GCP deployments are unchanged.

### Can I use AWS/Azure in production?
Not recommended. These deployments are experimental and untested.

### How can I help test AWS/Azure?
Follow the deployment guides and report your experience via GitHub issues.

### What if the cloud detector module fails?
The system falls back to GCP-only mode, maintaining backward compatibility.

### Are there performance differences between clouds?
Unknown for AWS/Azure as they haven't been tested. GCP performance is proven.

## Support

### Production Support (GCP)
- Full support via GitHub issues
- Tested configurations
- Known performance characteristics

### Experimental Support (AWS/Azure)
- Community-driven support
- No guarantees or warranties
- Use at your own risk

## Resources

- [GCP Deployment (Production)](../deploy/gcp/README.md)
- [AWS Deployment (Experimental)](../deploy/aws/README.md)
- [Azure Deployment (Experimental)](../deploy/azure/README.md)
- [Development Guide](DEVELOPMENT.md)
- [Main README](../README.md)