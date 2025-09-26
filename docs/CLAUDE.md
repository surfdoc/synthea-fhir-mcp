# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Repository Overview

This is a Model Context Protocol (MCP) server that provides Claude Desktop with the ability to query Synthea-generated FHIR healthcare data from a PostgreSQL database. The server exposes FHIR query tools through an SSE (Server-Sent Events) transport layer and supports multi-cloud deployment.

## Common Development Commands

### Testing
```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=src --cov-report=term-missing

# Run specific test categories
pytest -m unit        # Unit tests only
pytest -m integration # Integration tests
pytest -m security    # Security tests
pytest -m fhir       # FHIR validation tests

# Run a single test file
pytest tests/unit/test_synthea_server.py

# Run with verbose output
pytest -v
```

### Code Quality
```bash
# Format code with black
black --line-length=120 src/ tests/

# Run linting
flake8 --max-line-length=120 src/ tests/

# Type checking
mypy src/
```

### Local Development
```bash
# Install dependencies
pip install -r requirements.txt
pip install -r dev-requirements.txt  # For testing

# Run the server locally
python src/synthea_server.py

# Run with custom database connection
DATABASE_URL="postgresql://user:pass@localhost:5432/synthea" python src/synthea_server.py
```

### Docker Operations
```bash
# Build the Docker image
docker build -t synthea-fhir-mcp .

# Run with environment variables
docker run -e DATABASE_URL="postgresql://..." -p 8080:8080 synthea-fhir-mcp
```

### Deployment (GCP)
```bash
# Deploy to Google Cloud Run
cd deploy/gcp
cp ../../.env.example .env
# Edit .env with Cloud SQL credentials
./deploy.sh
```

### Data Generation
```bash
# Generate synthetic patient data (requires Java 11+)
./scripts/generate_synthea_data.sh 100

# Generate with custom options
python scripts/generate_synthea_data.py \
  --population 200 \
  --state Massachusetts \
  --seed 42

# Load data into PostgreSQL
python scripts/load_synthea_data.py \
  --synthea-dir synthea/output \
  --create-schema
```

## Architecture and Code Structure

### Multi-Layer Architecture

1. **Transport Layer** (`src/synthea_server.py`)
   - FastAPI server handling SSE connections
   - MCP protocol implementation over Server-Sent Events
   - Session management for multiple Claude Desktop connections
   - Health check and statistics endpoints

2. **Cloud Abstraction Layer** (`src/cloud_detector.py`)
   - Auto-detects cloud provider (GCP, AWS, Azure)
   - Builds provider-specific database connection strings
   - Handles cloud-specific authentication patterns

3. **FHIR Query Layer** (tools in `synthea_server.py`)
   - 11 specialized FHIR query tools
   - PostgreSQL JSONB queries for FHIR resources
   - Patient-centric data access patterns

### Key Design Patterns

- **Connection Pooling**: Uses psycopg connection pools for efficient database access
- **Async/Await**: Fully asynchronous request handling for SSE streams
- **JSONB Queries**: Leverages PostgreSQL's JSONB operators for efficient FHIR resource querying
- **Tool-Based Architecture**: Each FHIR operation is a distinct MCP tool with typed parameters

### Database Schema

The PostgreSQL database uses a single `fhir_resources` table with:
- `id`: UUID primary key
- `resource_type`: FHIR resource type (Patient, Observation, etc.)
- `resource`: JSONB column containing full FHIR resource
- Indexes on resource_type and common JSONB paths for performance

### MCP Protocol Implementation

The server implements MCP over SSE with:
- Tool discovery via `tools/list` endpoint
- Tool execution with typed parameters and validation
- Structured error responses following MCP spec
- Session-based message routing for concurrent connections

## Testing Strategy

### Test Organization
- `tests/unit/`: Pure unit tests with mocked dependencies
- `tests/integration/`: Tests requiring database or network
- `tests/security/`: Security validation tests
- `tests/validation/`: FHIR resource validation
- `tests/fixtures/`: Sample FHIR data for testing

### Test Database
Integration tests use `pytest-postgresql` to spin up temporary PostgreSQL instances with the FHIR schema automatically created.

## Environment Configuration

### Required Environment Variables
- `DATABASE_URL` or cloud-specific variables:
  - **GCP**: `CLOUD_SQL_CONNECTION_NAME`, `DB_USER`, `DB_PASSWORD`, `DB_NAME`
  - **AWS**: `AWS_RDS_ENDPOINT`, `AWS_RDS_PORT`, `DB_USER`, `DB_PASSWORD`, `DB_NAME`
  - **Azure**: `AZURE_POSTGRES_HOST`, `AZURE_POSTGRES_PORT`, `DB_USER`, `DB_PASSWORD`, `DB_NAME`

### Port Configuration
- Default: 8080 (Cloud Run standard)
- Override with `PORT` environment variable

## Security Considerations

- All patient data is synthetic (Synthea-generated)
- Read-only database access enforced
- No PHI/PII handling - synthetic data only
- SQL injection prevention through parameterized queries
- Input validation on all MCP tool parameters

## FHIR Query Patterns

The codebase uses PostgreSQL JSONB operators extensively:
- `->`: Extract JSON object field
- `->>`: Extract JSON object field as text
- `@>`: Contains operator for searching nested structures
- `jsonb_array_elements()`: Expand JSONB arrays for searching

Example pattern used throughout:
```sql
SELECT resource FROM fhir_resources
WHERE resource_type = 'Condition'
AND resource->'code'->'coding' @> '[{"code": "44054006"}]'::jsonb
```

## Multi-Cloud Support

The server auto-detects and configures for:
- **Google Cloud Platform**: Cloud SQL with Unix socket connections
- **Amazon Web Services**: RDS with IAM authentication support
- **Microsoft Azure**: PostgreSQL Flexible Server

Cloud detection happens automatically at startup via environment variable patterns.