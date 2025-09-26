# System Architecture

This document provides a comprehensive overview of the Synthea FHIR MCP Server architecture, including system components, data flow, and deployment options.

## Table of Contents
- [System Overview](#system-overview)
- [Data Flow](#data-flow)
- [Component Details](#component-details)
- [Protocol Stack](#protocol-stack)
- [Multi-Cloud Deployment](#multi-cloud-deployment)
- [Security Architecture](#security-architecture)

## System Overview

The Synthea FHIR MCP Server enables Claude Desktop to query synthetic healthcare data through a standardized Model Context Protocol interface.

```mermaid
graph TB
    subgraph "User Interface Layer"
        USER[User]
        CD[Claude Desktop<br/>AI Assistant]
    end

    subgraph "Protocol Translation Layer"
        SG[Supergateway<br/>SSE→MCP Proxy]
    end

    subgraph "MCP Server Layer"
        MCP[MCP Server<br/>Python/FastMCP]
        TOOLS[FHIR Tools<br/>11 Specialized Functions]
        QUERY[Query Engine<br/>JSONB Processing]
    end

    subgraph "Data Layer"
        PG[(PostgreSQL Database)]
        FHIR[FHIR Resources<br/>Patients, Observations,<br/>Conditions, etc.]
    end

    USER -->|Natural Language| CD
    CD -->|MCP Protocol| SG
    SG -->|SSE Connection| MCP
    MCP --> TOOLS
    TOOLS --> QUERY
    QUERY -->|SQL/JSONB| PG
    PG --> FHIR

    style USER fill:#e3f2fd
    style CD fill:#e1f5fe
    style MCP fill:#fff3e0
    style PG fill:#f3e5f5
```

## Data Flow

Detailed sequence of how a medical query flows through the system:

```mermaid
sequenceDiagram
    participant User
    participant Claude Desktop
    participant Supergateway
    participant MCP Server
    participant Query Engine
    participant PostgreSQL

    User->>Claude Desktop: "Find patients with diabetes"
    activate Claude Desktop

    Claude Desktop->>Claude Desktop: Analyze query intent
    Claude Desktop->>Supergateway: Call search_conditions tool
    activate Supergateway

    Supergateway->>MCP Server: SSE: tool_call(search_conditions)
    activate MCP Server

    MCP Server->>Query Engine: Process FHIR query
    activate Query Engine

    Query Engine->>PostgreSQL: SELECT * FROM conditions<br/>WHERE data->>'code' LIKE '%diabetes%'
    activate PostgreSQL

    PostgreSQL-->>Query Engine: Return JSONB results
    deactivate PostgreSQL

    Query Engine-->>MCP Server: Format FHIR resources
    deactivate Query Engine

    MCP Server-->>Supergateway: Return patient list
    deactivate MCP Server

    Supergateway-->>Claude Desktop: Tool response
    deactivate Supergateway

    Claude Desktop->>Claude Desktop: Format natural language
    Claude Desktop-->>User: "I found 23 patients with diabetes..."
    deactivate Claude Desktop
```

## Component Details

### MCP Tools

The server provides 11 specialized FHIR query tools:

```mermaid
mindmap
  root((MCP Server))
    Patient Tools
      get_patients
      get_patient_summary
      get_patient_timeline
    Clinical Tools
      search_conditions
      get_patient_medications
      get_patient_procedures
      get_patient_encounters
    Prevention Tools
      search_immunizations
      get_patient_allergies
    System Tools
      get_started
      get_statistics
      query_fhir
```

### Database Schema

FHIR resources are stored as JSONB in PostgreSQL:

```mermaid
erDiagram
    patients ||--o{ observations : has
    patients ||--o{ conditions : has
    patients ||--o{ procedures : has
    patients ||--o{ medications : has
    patients ||--o{ immunizations : has
    patients ||--o{ encounters : has
    patients ||--o{ allergies : has

    patients {
        uuid id PK
        jsonb data
        timestamp created_at
        timestamp updated_at
    }

    observations {
        uuid id PK
        uuid patient_id FK
        jsonb data
        timestamp created_at
    }

    conditions {
        uuid id PK
        uuid patient_id FK
        jsonb data
        timestamp created_at
    }
```

## Protocol Stack

Communication protocols used in the system:

```mermaid
graph TB
    subgraph "Application Layer"
        NLP[Natural Language Processing]
        TOOL[Tool Selection Logic]
    end

    subgraph "MCP Layer"
        MCP_PROTO[MCP Protocol<br/>JSON-RPC 2.0]
        TOOLS_DEF[Tool Definitions]
        RESOURCES[Resource Schemas]
    end

    subgraph "Transport Layer"
        SSE[Server-Sent Events<br/>Streaming]
        HTTP[HTTP/HTTPS<br/>TLS 1.3]
    end

    subgraph "Data Layer"
        SQL[PostgreSQL Protocol]
        JSONB[JSONB Operations]
    end

    NLP --> MCP_PROTO
    TOOL --> TOOLS_DEF
    MCP_PROTO --> SSE
    SSE --> HTTP
    HTTP --> SQL
    SQL --> JSONB
```

## Multi-Cloud Deployment

### Production (Google Cloud Platform)

```mermaid
graph LR
    subgraph "Client"
        CD1[Claude Desktop]
    end

    subgraph "Google Cloud Platform"
        subgraph "Cloud Run"
            CR[Container<br/>MCP Server]
            PROXY[Cloud SQL Proxy]
        end

        subgraph "Cloud SQL"
            CS[(PostgreSQL<br/>Synthea Data)]
        end

        subgraph "Security"
            SM[Secret Manager]
            IAM[IAM Policies]
        end
    end

    CD1 -->|HTTPS/SSE| CR
    CR --> PROXY
    PROXY -->|Unix Socket| CS
    CR --> SM
    IAM --> CR

    style CD1 fill:#e1f5fe
    style CR fill:#fff3e0
    style CS fill:#f3e5f5
```

### Experimental Deployments

```mermaid
graph TB
    subgraph "AWS (Experimental)"
        CD2[Claude Desktop] -->|HTTPS| ALB[Application<br/>Load Balancer]
        ALB --> ECS[ECS Fargate<br/>MCP Container]
        ECS -->|SSL/TLS| RDS[(RDS<br/>PostgreSQL)]
        ECS -.->|Optional| SM2[Secrets Manager]
    end

    subgraph "Azure (Experimental)"
        CD3[Claude Desktop] -->|HTTPS| AG[Application<br/>Gateway]
        AG --> ACI[Container<br/>Instance]
        ACI -->|SSL/TLS| ADB[(Azure Database<br/>for PostgreSQL)]
        ACI -.->|Optional| KV[Key Vault]
    end

    subgraph "Local Development"
        CD4[Claude Desktop] -->|HTTP| LOCAL[Local Server<br/>localhost:8080]
        LOCAL --> DOCKER[Docker<br/>PostgreSQL]
    end

    style CD2 fill:#ffe0b2
    style CD3 fill:#e1bee7
    style CD4 fill:#c8e6c9
```

## Security Architecture

### Authentication & Authorization Flow

```mermaid
graph TD
    subgraph "Authentication"
        CD[Claude Desktop] -->|Config File| CREDS[MCP Server Config]
        CREDS --> VAL[Validate Connection]
    end

    subgraph "Authorization"
        VAL --> CHECK{Authorized?}
        CHECK -->|Yes| TOOLS[Enable Tools]
        CHECK -->|No| DENY[Connection Refused]
    end

    subgraph "Data Access"
        TOOLS --> RO[Read-Only Access]
        RO --> FILTER[Data Filtering]
        FILTER --> ANON[Synthetic Data Only]
    end

    subgraph "Transport Security"
        ANON --> TLS[TLS 1.3 Encryption]
        TLS --> RESPONSE[Secure Response]
    end

    style CD fill:#e1f5fe
    style TOOLS fill:#e8f5e9
    style DENY fill:#ffcdd2
    style TLS fill:#fff9c4
```

### Security Layers

```mermaid
graph LR
    subgraph "Network Security"
        FW[Firewall Rules]
        TLS[TLS/SSL]
        VPC[VPC Isolation]
    end

    subgraph "Application Security"
        AUTH[Authentication]
        AUTHZ[Authorization]
        VAL[Input Validation]
    end

    subgraph "Data Security"
        RO[Read-Only Access]
        SYNTH[Synthetic Data Only]
        LOG[Audit Logging]
    end

    FW --> AUTH
    TLS --> AUTHZ
    VPC --> VAL
    AUTH --> RO
    AUTHZ --> SYNTH
    VAL --> LOG
```

## Performance Considerations

### Query Optimization

```mermaid
graph TD
    subgraph "Query Pipeline"
        QUERY[User Query] --> PARSE[Parse Intent]
        PARSE --> SELECT{Select Tool}

        SELECT -->|Simple| DIRECT[Direct Query]
        SELECT -->|Complex| OPT[Query Optimizer]

        OPT --> INDEX[Use Indexes]
        INDEX --> CACHE[Check Cache]

        DIRECT --> EXEC[Execute SQL]
        CACHE --> EXEC

        EXEC --> FORMAT[Format Results]
        FORMAT --> RETURN[Return to User]
    end

    style QUERY fill:#e3f2fd
    style OPT fill:#fff3e0
    style CACHE fill:#e8f5e9
```

## Scalability

### Auto-scaling Architecture

```mermaid
graph TB
    subgraph "Load Balancing"
        LB[Load Balancer] --> CHECK{Traffic Level}
    end

    subgraph "Auto-scaling"
        CHECK -->|Low| MIN[Min Instances: 0]
        CHECK -->|Normal| NORMAL[Instances: 1-3]
        CHECK -->|High| MAX[Max Instances: 10]
    end

    subgraph "Database"
        MIN --> DB[(PostgreSQL<br/>Connection Pool)]
        NORMAL --> DB
        MAX --> DB
    end

    subgraph "Monitoring"
        DB --> METRICS[CloudWatch/<br/>Stackdriver]
        METRICS --> ALERT[Alerts]
    end
```

## Development Workflow

### Local Development Setup

```mermaid
graph LR
    subgraph "Development Environment"
        DEV[Developer] --> GIT[Git Clone]
        GIT --> VENV[Python venv]
        VENV --> DEPS[pip install]
        DEPS --> ENV[.env setup]
        ENV --> RUN[python server.py]
    end

    subgraph "Testing"
        RUN --> UNIT[Unit Tests]
        UNIT --> INT[Integration Tests]
        INT --> E2E[E2E Tests]
    end

    subgraph "Deployment"
        E2E --> BUILD[Docker Build]
        BUILD --> PUSH[Push to Registry]
        PUSH --> DEPLOY[Deploy to Cloud]
    end

    style DEV fill:#c8e6c9
    style RUN fill:#fff3e0
    style DEPLOY fill:#e1f5fe
```

## Data Generation Pipeline

### Synthea Data Flow

```mermaid
graph TD
    subgraph "Data Generation"
        JAVA[Java 11+] --> SYNTHEA[Synthea Engine]
        CONFIG[Configuration<br/>Properties] --> SYNTHEA
        SYNTHEA --> FHIR[FHIR Bundles]
    end

    subgraph "Data Processing"
        FHIR --> PARSE[Parse JSON]
        PARSE --> EXTRACT[Extract Resources]
        EXTRACT --> VALIDATE[Validate FHIR]
    end

    subgraph "Data Loading"
        VALIDATE --> TRANSFORM[Transform to JSONB]
        TRANSFORM --> INSERT[Insert to PostgreSQL]
        INSERT --> INDEX[Create Indexes]
    end

    subgraph "Result"
        INDEX --> READY[Ready for Queries]
    end

    style SYNTHEA fill:#fff3e0
    style TRANSFORM fill:#e8f5e9
    style READY fill:#c8e6c9
```

## Future Architecture Considerations

### Planned Enhancements

```mermaid
graph TD
    subgraph "Current State"
        CURRENT[Single Region<br/>Read-Only<br/>Synthetic Data]
    end

    subgraph "Phase 1: Enhanced Features"
        CURRENT --> P1[Multi-Region Support<br/>Caching Layer<br/>GraphQL API]
    end

    subgraph "Phase 2: Extended Capabilities"
        P1 --> P2[Real-time Updates<br/>WebSocket Support<br/>Batch Operations]
    end

    subgraph "Phase 3: Advanced Integration"
        P2 --> P3[HL7 FHIR R5<br/>CDS Hooks<br/>SMART on FHIR]
    end

    style CURRENT fill:#e8f5e9
    style P1 fill:#fff3e0
    style P2 fill:#ffe0b2
    style P3 fill:#e1bee7
```

## Resources

- [MCP Protocol Specification](https://github.com/modelcontextprotocol/specification)
- [FHIR R4 Documentation](https://hl7.org/fhir/R4/)
- [Synthea Patient Generator](https://github.com/synthetichealth/synthea)
- [Cloud Run Documentation](https://cloud.google.com/run/docs)
- [PostgreSQL JSONB Guide](https://www.postgresql.org/docs/current/datatype-json.html)