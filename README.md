# Synthea FHIR MCP Server

A specialized [Model Context Protocol (MCP)](https://github.com/modelcontextprotocol) server for querying Synthea-generated FHIR healthcare data through Claude Desktop.

## 🏥 What is This?

This MCP server provides Claude Desktop with the ability to query a PostgreSQL database containing synthetic patient data in FHIR format. The data is generated using [Synthea](https://github.com/synthetichealth/synthea) and includes:

- 117 synthetic patients
- 79,013 observations (vital signs, lab results)
- 22,216 procedures
- 9,200 clinical encounters
- 6,792 medication requests
- 4,554 medical conditions
- 1,623 immunization records
- 88 allergy records

All data is **synthetic** - no real patient information is stored or accessible.

## 🏗️ Architecture

```mermaid
graph LR
    subgraph "Client"
        CD[Claude Desktop<br/>LLM Client]
    end

    subgraph "Connection Layer"
        SG[Supergateway<br/>npx proxy]
    end

    subgraph "MCP Server"
        MCP[MCP Server<br/>Cloud Run/Local]
        TOOLS[["🛠️ FHIR Tools<br/>━━━━━━━━━<br/>get_patients<br/>search_conditions<br/>get_medications<br/>get_statistics<br/>+ 7 more"]]
    end

    subgraph "Database"
        PG[(PostgreSQL<br/>Synthea FHIR Data<br/>117 patients<br/>120K+ records)]
    end

    CD -->|SSE Protocol| SG
    SG -->|MCP Protocol| MCP
    MCP --> TOOLS
    MCP -->|SQL/JSONB| PG

    style CD fill:#e1f5fe
    style MCP fill:#fff3e0
    style PG fill:#f3e5f5
    style TOOLS fill:#e8f5e9
```

## 🚀 Quick Start for Beta Testers

Add this configuration to your Claude Desktop settings:

**macOS**: `~/Library/Application Support/Claude/claude_desktop_config.json`
**Windows**: `%APPDATA%\Claude\claude_desktop_config.json`

```json
{
  "mcpServers": {
    "synthea-fhir": {
      "command": "npx",
      "args": [
        "-y",
        "supergateway",
        "--sse",
        "https://synthea-mcp-1095016408887.us-central1.run.app/sse"
      ]
    }
  }
}
```

Restart Claude Desktop and you're ready to query healthcare data!

## 📊 Example Queries

Once connected, ask Claude:

### Getting Started
- **"Run the get_started tool"** - Learn about the database structure (do this first!)

### Basic Queries
- "Show me statistics about the FHIR database"
- "List 10 patients with their demographics"

### Clinical Queries
- "Find patients with Type 2 Diabetes"
- "Which patients received COVID-19 vaccinations?"
- "Show me patients taking lisinopril or losartan"

### Patient-Specific
- "Get full medical history for patient 229a1e6d-1714-f0cd-8253-a8729632291e"
- "What medications is patient 59844213-b884-17cb-59e9-c07a73a06f41 taking?"

## 🛠️ Available Tools

- `get_started` - Learn the FHIR database structure
- `get_patients` - List patients
- `get_patient_summary` - Complete patient medical history
- `search_conditions` - Find patients by diagnosis
- `search_immunizations` - Find vaccination records
- `get_patient_medications` - List patient medications
- `get_patient_procedures` - List medical procedures
- `get_patient_encounters` - List clinical visits
- `get_patient_allergies` - List allergies
- `query_fhir` - Execute custom FHIR queries
- `get_statistics` - Database statistics

## 💻 Local Development

### Prerequisites
- Python 3.10+
- PostgreSQL with Synthea data
- Docker (optional)

### Setup

1. Clone the repository:
```bash
git clone https://github.com/surfdoc/mcp-postgres-to-synthea-fhir-mcp.git
cd mcp-postgres-to-synthea-fhir-mcp
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Configure environment:
```bash
cp .env.example .env
# Edit .env with your database credentials
```

4. Run locally:
```bash
python src/synthea_server.py
```

### Generating and Loading Synthea Data

#### Prerequisites
- Java 11+ (required for Synthea)
- Python 3.8+
- PostgreSQL database

#### Quick Start
```bash
# Generate 100 synthetic patients (requires Java 11+)
./scripts/generate_synthea_data.sh

# Or with custom options
./scripts/generate_synthea_data.sh 500 California 12345
```

#### Advanced Generation
```bash
# Generate with specific options
python scripts/generate_synthea_data.py \
  --population 200 \
  --state Massachusetts \
  --city Boston \
  --seed 42 \
  --modules diabetes covid19

# Use custom Synthea configuration
python scripts/generate_synthea_data.py \
  --config scripts/synthea_config.properties \
  --population 1000
```

#### Loading Data into PostgreSQL
```bash
# Set database connection
export DATABASE_URL="postgresql://user:pass@localhost:5432/synthea"

# Create schema and load data
python scripts/load_synthea_data.py \
  --synthea-dir synthea/output \
  --create-schema
```

The generation process creates FHIR bundles containing:
- Patient demographics
- Observations (vitals, lab results)
- Conditions (diagnoses)
- Procedures
- MedicationRequests (prescriptions)
- Immunizations
- Encounters (clinical visits)
- AllergyIntolerances

## 🐳 Docker Deployment

```bash
# Build
docker build -t synthea-fhir-mcp .

# Run
docker run -e DATABASE_URL="postgresql://..." -p 8080:8080 synthea-fhir-mcp
```

## ☁️ Cloud Deployment

### Deployment Status by Cloud Provider

| Cloud Provider | Status | Testing | Documentation |
|---------------|--------|---------|---------------|
| **Google Cloud Platform** | ✅ **Production Ready** | Fully Tested | [GCP Guide](deploy/gcp/README.md) |
| **Amazon Web Services** | ⚠️ **Experimental** | Not Tested | [AWS Guide](deploy/aws/README.md) |
| **Microsoft Azure** | ⚠️ **Experimental** | Not Tested | [Azure Guide](deploy/azure/README.md) |

> **Note:** Only Google Cloud Platform deployment has been tested in production. AWS and Azure deployments are experimental and provided for community testing. See [Multi-Cloud Support](docs/MULTI_CLOUD.md) for details.

### Quick Deploy to GCP (Production Ready)

```bash
cd deploy/gcp
cp ../../.env.example .env
# Edit .env with your Cloud SQL credentials
./deploy.sh
```

### Environment Variables
- **GCP**: `CLOUD_SQL_CONNECTION_NAME`, `DB_USER`, `DB_PASSWORD`, `DB_NAME`
- **AWS** (Experimental): `AWS_RDS_ENDPOINT`, `AWS_RDS_PORT`, `DB_USER`, `DB_PASSWORD`, `DB_NAME`
- **Azure** (Experimental): `AZURE_POSTGRES_HOST`, `AZURE_POSTGRES_PORT`, `DB_USER`, `DB_PASSWORD`, `DB_NAME`

See [Deployment Guide](docs/DEPLOYMENT.md) for detailed instructions.

## 📚 Documentation

- [System Architecture](docs/ARCHITECTURE.md) - Detailed architecture diagrams and technical overview
- [Beta Setup Guide](docs/BETA_SETUP.md) - Detailed setup instructions
- [FHIR Schema Guide](docs/FHIR_SCHEMA_GUIDE.md) - Understanding FHIR JSONB queries
- [Development Guide](docs/DEVELOPMENT.md) - Contributing and development
- [Deployment Guide](docs/DEPLOYMENT.md) - Cloud deployment instructions
- [Multi-Cloud Support](docs/MULTI_CLOUD.md) - AWS and Azure deployment (experimental)
- [Testing Guide](docs/TESTING.md) - Comprehensive testing documentation

## 🔒 Security & Privacy

- ✅ All data is synthetic (generated by Synthea)
- ✅ No real patient information
- ✅ Read-only database access
- ✅ Secure HTTPS connection

## 🤝 Contributing

Contributions are welcome! Please see our [Development Guide](docs/DEVELOPMENT.md) for details.

## 📄 License

MIT License - see [LICENSE](LICENSE) file

## 🙏 Acknowledgments

See [ATTRIBUTION.md](ATTRIBUTION.md) for acknowledgments and credits.

---

Made with ❤️ for healthcare data exploration