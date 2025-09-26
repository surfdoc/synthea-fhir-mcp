#!/usr/bin/env python3
"""
MCP Server for Cloud Run with SSE transport
Implements the Model Context Protocol for Synthea FHIR data
"""

import os
import json
import logging
from typing import Any, Optional, Dict
import uuid
import psycopg
from psycopg.rows import dict_row
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import StreamingResponse, JSONResponse
from pydantic import BaseModel, Field
import asyncio
from datetime import datetime

# Server version
SERVER_VERSION = "1.2.0"

# Import cloud detector for multi-cloud support
try:
    from cloud_detector import detect_cloud_provider, get_connection_string_for_provider
    MULTI_CLOUD_ENABLED = True
except ImportError:
    # If cloud_detector is not available, fall back to GCP-only mode
    MULTI_CLOUD_ENABLED = False

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger('synthea-mcp-server')

# Session management for SSE connections
sse_sessions: Dict[str, asyncio.Queue] = {}

app = FastAPI(title="Synthea FHIR MCP Server")

# Connection configuration
def get_connection_string():
    """Build connection string for Cloud SQL or other cloud providers"""

    # EXISTING GCP LOGIC - UNCHANGED TO MAINTAIN BACKWARD COMPATIBILITY
    if os.getenv("CLOUD_SQL_CONNECTION_NAME"):
        # Running on Cloud Run with Cloud SQL socket connection
        db_user = os.getenv("DB_USER", "synthea-user")
        db_password = os.getenv("DB_PASSWORD", "")
        db_name = os.getenv("DB_NAME", "synthea")
        cloud_sql_connection = os.getenv("CLOUD_SQL_CONNECTION_NAME")

        if not db_password:
            logger.warning("DB_PASSWORD not set, connection may fail")

        return (
            f"postgresql://{db_user}:{db_password}@/"
            f"{db_name}?host=/cloudsql/{cloud_sql_connection}"
        )

    # NEW: Multi-cloud support (only if cloud_detector is available)
    if MULTI_CLOUD_ENABLED:
        # Try to get connection string from cloud detector
        multi_cloud_conn = get_connection_string_for_provider()
        if multi_cloud_conn:  # Will be None for GCP (handled above)
            return multi_cloud_conn

    # EXISTING FALLBACK - UNCHANGED
    # Local development or direct connection
    return os.getenv("DATABASE_URL", "")

CONNECTION_STRING = get_connection_string()

# Log detected cloud provider at startup
if MULTI_CLOUD_ENABLED:
    from cloud_detector import detect_cloud_provider, get_cloud_specific_settings
    provider = detect_cloud_provider()
    settings = get_cloud_specific_settings(provider)
    logger.info(f"Cloud Provider: {provider.upper()}")
    if settings.get("warning"):
        logger.warning(settings["warning"])

def get_connection():
    """Get database connection"""
    if not CONNECTION_STRING:
        raise RuntimeError("No database connection configured")
    return psycopg.connect(CONNECTION_STRING, row_factory=dict_row)

# MCP Protocol Models
class MCPRequest(BaseModel):
    jsonrpc: str = "2.0"
    method: str
    params: dict = {}
    id: Optional[Any] = None

class MCPResponse(BaseModel):
    jsonrpc: str = "2.0"
    result: Optional[Any] = None
    error: Optional[dict] = None
    id: Optional[Any] = None

    model_config = {"exclude_none": True}

# MCP Prompts - provide context about FHIR schema
PROMPTS = [
    {
        "name": "fhir_schema_guide",
        "description": "Learn how to query the FHIR database with JSONB patterns",
        "arguments": [],
        "template": """# FHIR Database Schema Guide

## Database Structure
All FHIR resources are stored in PostgreSQL tables with a JSONB `resource` column containing the full FHIR resource.

### Tables Available:
- fhir.patient - Patient demographics
- fhir.observation - Vital signs, lab results
- fhir.condition - Diagnoses/conditions
- fhir.procedure - Medical procedures
- fhir.medication_request - Prescriptions
- fhir.encounter - Clinical visits
- fhir.immunization - Vaccinations
- fhir.allergy_intolerance - Allergies

## JSONB Query Patterns

### Basic Operators:
- `->` : Get JSON field (returns JSON)
- `->>` : Get JSON field as text
- `->0` : Get first array element
- `#>` : Get at path (returns JSON)
- `#>>` : Get at path as text

### Example Queries:

**Immunizations:**
```sql
SELECT patient_id,
       resource->'vaccineCode'->'coding'->0->>'display' as vaccine_name,
       resource->>'occurrenceDateTime' as date_given
FROM fhir.immunization
WHERE resource->'vaccineCode'->'coding'->0->>'display' ILIKE '%flu%'
```

**Conditions:**
```sql
SELECT patient_id,
       resource->'code'->'coding'->0->>'display' as condition_name
FROM fhir.condition
WHERE resource->'code'->'coding'->0->>'display' ILIKE '%diabetes%'
```

**Blood Pressure:**
```sql
SELECT patient_id,
       resource->'component'->0->'valueQuantity'->>'value' as systolic,
       resource->'component'->1->'valueQuantity'->>'value' as diastolic
FROM fhir.observation
WHERE resource->'code'->'coding'->0->>'code' = '85354-9'
```

## Tips:
- Use ILIKE for case-insensitive text search
- Arrays are 0-indexed (->0 for first element)
- Check multiple fields - data may be in 'text' or 'coding'
- Use DISTINCT when finding unique patients"""
    }
]

# MCP Resources - provide access to reference data
RESOURCES = [
    {
        "uri": "fhir://schema/guide",
        "name": "FHIR Schema Guide",
        "description": "Complete guide to querying FHIR JSONB data",
        "mimeType": "text/plain"
    },
    {
        "uri": "fhir://code-systems",
        "name": "FHIR Code Systems",
        "description": "Common code systems used in FHIR data",
        "mimeType": "text/plain"
    }
]

# MCP Tool Definitions
TOOLS = [
    {
        "name": "query_fhir",
        "description": """Execute a read-only SQL query against the FHIR database.

IMPORTANT: All FHIR data is stored in JSONB columns. Use these patterns:
- Tables: fhir.patient, fhir.immunization, fhir.condition, fhir.observation, fhir.medication_request
- Access JSON: -> for JSON, ->> for text, ->0 for first array element
- Immunizations: resource->'vaccineCode'->'coding'->0->>'display' for vaccine name
- Search vaccines: WHERE resource->'vaccineCode'->'coding'->0->>'display' ILIKE '%flu%'
- Example: SELECT patient_id, resource->'vaccineCode'->'coding'->0->>'display' as vaccine FROM fhir.immunization WHERE resource->'vaccineCode'->'coding'->0->>'display' ILIKE '%influenza%'""",
        "inputSchema": {
            "type": "object",
            "properties": {
                "sql": {"type": "string", "description": "SQL query to execute"},
                "limit": {"type": "integer", "description": "Maximum rows to return", "default": 100}
            },
            "required": ["sql"]
        }
    },
    {
        "name": "get_patients",
        "description": "Get a list of patients",
        "inputSchema": {
            "type": "object",
            "properties": {
                "limit": {"type": "integer", "description": "Maximum patients to return", "default": 10}
            }
        }
    },
    {
        "name": "get_patient_summary",
        "description": "Get comprehensive summary for a specific patient",
        "inputSchema": {
            "type": "object",
            "properties": {
                "patient_id": {"type": "string", "description": "Patient ID"}
            },
            "required": ["patient_id"]
        }
    },
    {
        "name": "get_patient_conditions",
        "description": "Get all conditions for a patient",
        "inputSchema": {
            "type": "object",
            "properties": {
                "patient_id": {"type": "string", "description": "Patient ID"}
            },
            "required": ["patient_id"]
        }
    },
    {
        "name": "get_patient_medications",
        "description": "Get all medications for a patient",
        "inputSchema": {
            "type": "object",
            "properties": {
                "patient_id": {"type": "string", "description": "Patient ID"}
            },
            "required": ["patient_id"]
        }
    },
    {
        "name": "get_patient_observations",
        "description": "Get recent observations for a patient",
        "inputSchema": {
            "type": "object",
            "properties": {
                "patient_id": {"type": "string", "description": "Patient ID"},
                "limit": {"type": "integer", "description": "Maximum observations to return", "default": 20}
            },
            "required": ["patient_id"]
        }
    },
    {
        "name": "search_conditions",
        "description": "Search for patients with specific conditions",
        "inputSchema": {
            "type": "object",
            "properties": {
                "condition_code": {"type": "string", "description": "SNOMED CT code for condition"},
                "condition_text": {"type": "string", "description": "Text search for condition"}
            }
        }
    },
    {
        "name": "get_statistics",
        "description": "Get database statistics",
        "inputSchema": {
            "type": "object",
            "properties": {}
        }
    },
    {
        "name": "get_started",
        "description": "Get started with the FHIR database - learn the schema and query patterns",
        "inputSchema": {
            "type": "object",
            "properties": {}
        }
    },
    {
        "name": "search_immunizations",
        "description": "Search for immunizations/vaccines by type (e.g., flu, COVID, measles)",
        "inputSchema": {
            "type": "object",
            "properties": {
                "vaccine_type": {"type": "string", "description": "Type of vaccine to search for (e.g., 'flu', 'influenza', 'COVID', 'measles')"},
                "patient_id": {"type": "string", "description": "Optional: specific patient ID"}
            },
            "required": ["vaccine_type"]
        }
    },
    {
        "name": "get_patient_procedures",
        "description": "Get procedures performed for a patient",
        "inputSchema": {
            "type": "object",
            "properties": {
                "patient_id": {"type": "string", "description": "Patient ID"},
                "limit": {"type": "integer", "description": "Maximum procedures to return", "default": 20}
            },
            "required": ["patient_id"]
        }
    },
    {
        "name": "get_patient_encounters",
        "description": "Get clinical encounters/visits for a patient",
        "inputSchema": {
            "type": "object",
            "properties": {
                "patient_id": {"type": "string", "description": "Patient ID"},
                "limit": {"type": "integer", "description": "Maximum encounters to return", "default": 20}
            },
            "required": ["patient_id"]
        }
    },
    {
        "name": "get_patient_allergies",
        "description": "Get allergies and intolerances for a patient",
        "inputSchema": {
            "type": "object",
            "properties": {
                "patient_id": {"type": "string", "description": "Patient ID"}
            },
            "required": ["patient_id"]
        }
    },
    {
        "name": "search_procedures",
        "description": "Search for patients who had specific procedures",
        "inputSchema": {
            "type": "object",
            "properties": {
                "procedure_code": {"type": "string", "description": "CPT or SNOMED code for procedure"},
                "procedure_text": {"type": "string", "description": "Text search for procedure name"}
            }
        }
    }
]

# MCP Request Handlers
async def handle_initialize(params: dict, request_id: Any):
    """Handle MCP initialization"""
    # Use a supported protocol version
    # supergateway doesn't support 2025-06-18 yet, so use 2024-11-05
    client_version = params.get("protocolVersion", "2024-11-05")
    if client_version == "2025-06-18":
        client_version = "2024-11-05"  # Downgrade to supported version

    return MCPResponse(
        id=request_id,
        result={
            "protocolVersion": client_version,  # Return supported version
            "capabilities": {
                "tools": {},
                "resources": {},
                "prompts": {}
            },
            "serverInfo": {
                "name": "synthea-fhir-mcp",
                "version": "1.0.0",
                "description": "MCP server for Synthea FHIR synthetic patient data"
            }
        }
    )

async def handle_list_tools(params: dict, request_id: Any):
    """List available tools"""
    return MCPResponse(
        id=request_id,
        result={"tools": TOOLS}
    )

async def handle_list_prompts(params: dict, request_id: Any):
    """List available prompts"""
    return MCPResponse(
        id=request_id,
        result={"prompts": PROMPTS}
    )

async def handle_get_prompt(params: dict, request_id: Any):
    """Get a specific prompt"""
    prompt_name = params.get("name")
    arguments = params.get("arguments", {})

    for prompt in PROMPTS:
        if prompt["name"] == prompt_name:
            # For now, just return the template as-is
            # In a real implementation, you'd substitute arguments
            return MCPResponse(
                id=request_id,
                result={
                    "messages": [
                        {
                            "role": "user",
                            "content": {
                                "type": "text",
                                "text": prompt["template"]
                            }
                        }
                    ]
                }
            )

    return MCPResponse(
        id=request_id,
        error={"code": -32602, "message": f"Unknown prompt: {prompt_name}"}
    )

async def handle_list_resources(params: dict, request_id: Any):
    """List available resources"""
    return MCPResponse(
        id=request_id,
        result={"resources": RESOURCES}
    )

async def handle_read_resource(params: dict, request_id: Any):
    """Read a specific resource"""
    uri = params.get("uri")

    if uri == "fhir://schema/guide":
        content = PROMPTS[0]["template"]  # Reuse the schema guide content
    elif uri == "fhir://code-systems":
        content = """# FHIR Code Systems Reference

## Common Code Systems:
- **SNOMED CT**: Conditions/diagnoses (e.g., '44054006' = Diabetes Type 2)
- **LOINC**: Lab tests & observations (e.g., '85354-9' = Blood Pressure)
- **RxNorm**: Medications (e.g., '6809' = Metformin)
- **CVX**: Vaccines (e.g., '140' = Influenza vaccine)
- **CPT**: Procedures

## Usage:
These codes are typically found in:
- resource->'code'->'coding'->0->>'code'
- resource->'code'->'coding'->0->>'system'
- resource->'code'->'coding'->0->>'display'"""
    else:
        return MCPResponse(
            id=request_id,
            error={"code": -32602, "message": f"Unknown resource: {uri}"}
        )

    return MCPResponse(
        id=request_id,
        result={
            "contents": [
                {
                    "uri": uri,
                    "mimeType": "text/plain",
                    "text": content
                }
            ]
        }
    )

async def handle_call_tool(params: dict, request_id: Any):
    """Execute a tool"""
    tool_name = params.get("name")
    arguments = params.get("arguments", {})

    try:
        conn = get_connection()

        if tool_name == "query_fhir":
            sql = arguments.get("sql", "").strip()
            limit = arguments.get("limit", 100)

            # Safety check
            if not sql.upper().startswith(('SELECT', 'WITH')):
                return MCPResponse(
                    id=request_id,
                    error={"code": -32602, "message": "Only SELECT queries allowed"}
                )

            # Add LIMIT if not present
            if 'LIMIT' not in sql.upper():
                sql = f"{sql} LIMIT {limit}"

            with conn.cursor() as cur:
                cur.execute(sql)
                results = cur.fetchall()

            conn.close()
            return MCPResponse(
                id=request_id,
                result={
                    "content": [
                        {
                            "type": "text",
                            "text": json.dumps({"results": results, "count": len(results)}, default=str)
                        }
                    ]
                }
            )

        elif tool_name == "get_patients":
            limit = arguments.get("limit", 10)
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT
                        id as patient_id,
                        resource->>'birthDate' as birth_date,
                        resource->'name'->0->'given'->0 as first_name,
                        resource->'name'->0->>'family' as last_name,
                        resource->>'gender' as gender
                    FROM fhir.patient
                    LIMIT %s
                """, (limit,))
                results = cur.fetchall()

            conn.close()
            return MCPResponse(
                id=request_id,
                result={
                    "content": [
                        {
                            "type": "text",
                            "text": json.dumps({"patients": results, "count": len(results)}, default=str)
                        }
                    ]
                }
            )

        elif tool_name == "get_patient_summary":
            patient_id = arguments.get("patient_id")
            summary = {}

            with conn.cursor() as cur:
                # Get patient info
                cur.execute("SELECT resource FROM fhir.patient WHERE id = %s", (patient_id,))
                patient = cur.fetchone()
                if patient:
                    summary['patient'] = patient['resource']

                # Get conditions
                cur.execute("""
                    SELECT resource FROM fhir.condition
                    WHERE patient_id = %s
                    LIMIT 20
                """, (patient_id,))
                summary['conditions'] = [r['resource'] for r in cur.fetchall()]

                # Get medications
                cur.execute("""
                    SELECT resource FROM fhir.medication_request
                    WHERE patient_id = %s
                    LIMIT 20
                """, (patient_id,))
                summary['medications'] = [r['resource'] for r in cur.fetchall()]

                # Get recent observations
                cur.execute("""
                    SELECT resource FROM fhir.observation
                    WHERE patient_id = %s
                    LIMIT 20
                """, (patient_id,))
                summary['observations'] = [r['resource'] for r in cur.fetchall()]

            conn.close()
            return MCPResponse(
                id=request_id,
                result={
                    "content": [
                        {
                            "type": "text",
                            "text": json.dumps(summary, default=str)
                        }
                    ]
                }
            )

        elif tool_name == "get_patient_conditions":
            patient_id = arguments.get("patient_id")
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT
                        resource->>'id' as condition_id,
                        resource->'code'->'coding'->0->>'display' as condition_name,
                        resource->'code'->'coding'->0->>'code' as snomed_code,
                        resource->>'onsetDateTime' as onset_date,
                        resource->'clinicalStatus'->'coding'->0->>'code' as status
                    FROM fhir.condition
                    WHERE patient_id = %s
                """, (patient_id,))
                results = cur.fetchall()

            conn.close()
            return MCPResponse(
                id=request_id,
                result={
                    "content": [
                        {
                            "type": "text",
                            "text": json.dumps({"conditions": results, "count": len(results)}, default=str)
                        }
                    ]
                }
            )

        elif tool_name == "get_patient_medications":
            patient_id = arguments.get("patient_id")
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT
                        resource->>'id' as medication_id,
                        resource->'medicationCodeableConcept'->'text' as medication_name,
                        resource->'medicationCodeableConcept'->'coding'->0->>'code' as rxnorm_code,
                        resource->>'authoredOn' as prescribed_date,
                        resource->>'status' as status
                    FROM fhir.medication_request
                    WHERE patient_id = %s
                """, (patient_id,))
                results = cur.fetchall()

            conn.close()
            return MCPResponse(
                id=request_id,
                result={
                    "content": [
                        {
                            "type": "text",
                            "text": json.dumps({"medications": results, "count": len(results)}, default=str)
                        }
                    ]
                }
            )

        elif tool_name == "get_patient_observations":
            patient_id = arguments.get("patient_id")
            limit = arguments.get("limit", 20)
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT
                        resource->>'id' as observation_id,
                        resource->'code'->'coding'->0->>'display' as observation_type,
                        resource->'valueQuantity'->>'value' as value,
                        resource->'valueQuantity'->>'unit' as unit,
                        resource->>'effectiveDateTime' as date
                    FROM fhir.observation
                    WHERE patient_id = %s
                    ORDER BY resource->>'effectiveDateTime' DESC
                    LIMIT %s
                """, (patient_id, limit))
                results = cur.fetchall()

            conn.close()
            return MCPResponse(
                id=request_id,
                result={
                    "content": [
                        {
                            "type": "text",
                            "text": json.dumps({"observations": results, "count": len(results)}, default=str)
                        }
                    ]
                }
            )

        elif tool_name == "search_conditions":
            condition_code = arguments.get("condition_code")
            condition_text = arguments.get("condition_text")

            with conn.cursor() as cur:
                if condition_code:
                    cur.execute("""
                        SELECT DISTINCT
                            patient_id,
                            resource->'code'->'coding'->0->>'display' as condition_name,
                            resource->'code'->'coding'->0->>'code' as snomed_code
                        FROM fhir.condition
                        WHERE resource->'code'->'coding'->0->>'code' = %s
                        LIMIT 20
                    """, (condition_code,))
                elif condition_text:
                    cur.execute("""
                        SELECT DISTINCT
                            patient_id,
                            resource->'code'->'coding'->0->>'display' as condition_name,
                            resource->'code'->'coding'->0->>'code' as snomed_code
                        FROM fhir.condition
                        WHERE resource->'code'->'coding'->0->>'display' ILIKE %s
                        LIMIT 20
                    """, (f'%{condition_text}%',))
                else:
                    results = []

                results = cur.fetchall()

            conn.close()
            return MCPResponse(
                id=request_id,
                result={
                    "content": [
                        {
                            "type": "text",
                            "text": json.dumps({"patients": results, "count": len(results)}, default=str)
                        }
                    ]
                }
            )

        elif tool_name == "search_immunizations":
            vaccine_type = arguments.get("vaccine_type", "")
            patient_id = arguments.get("patient_id")

            with conn.cursor() as cur:
                if patient_id:
                    cur.execute("""
                        SELECT
                            patient_id,
                            resource->>'id' as immunization_id,
                            resource->'vaccineCode'->'coding'->0->>'display' as vaccine_name,
                            resource->'vaccineCode'->'coding'->0->>'code' as cvx_code,
                            resource->>'occurrenceDateTime' as date_given,
                            resource->>'status' as status
                        FROM fhir.immunization
                        WHERE patient_id = %s
                          AND (resource->'vaccineCode'->'coding'->0->>'display' ILIKE %s
                               OR resource->'vaccineCode'->'text'::text ILIKE %s)
                        ORDER BY resource->>'occurrenceDateTime' DESC
                    """, (patient_id, f'%{vaccine_type}%', f'%{vaccine_type}%'))
                else:
                    cur.execute("""
                        SELECT
                            patient_id,
                            resource->'vaccineCode'->'coding'->0->>'display' as vaccine_name,
                            resource->'vaccineCode'->'coding'->0->>'code' as cvx_code,
                            resource->>'occurrenceDateTime' as date_given,
                            COUNT(*) OVER() as total_count
                        FROM fhir.immunization
                        WHERE resource->'vaccineCode'->'coding'->0->>'display' ILIKE %s
                           OR resource->'vaccineCode'->'text'::text ILIKE %s
                        ORDER BY resource->>'occurrenceDateTime' DESC
                        LIMIT 100
                    """, (f'%{vaccine_type}%', f'%{vaccine_type}%'))

                results = cur.fetchall()

            conn.close()
            return MCPResponse(
                id=request_id,
                result={
                    "content": [
                        {
                            "type": "text",
                            "text": json.dumps({"immunizations": results, "count": len(results)}, default=str)
                        }
                    ]
                }
            )

        elif tool_name == "get_patient_procedures":
            patient_id = arguments.get("patient_id")
            limit = arguments.get("limit", 20)
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT
                        resource->>'id' as procedure_id,
                        resource->'code'->'coding'->0->>'display' as procedure_name,
                        resource->'code'->'coding'->0->>'code' as procedure_code,
                        resource->>'performedDateTime' as performed_date,
                        resource->>'status' as status
                    FROM fhir.procedure
                    WHERE patient_id = %s
                    ORDER BY resource->>'performedDateTime' DESC
                    LIMIT %s
                """, (patient_id, limit))
                results = cur.fetchall()

            conn.close()
            return MCPResponse(
                id=request_id,
                result={
                    "content": [
                        {
                            "type": "text",
                            "text": json.dumps({"procedures": results, "count": len(results)}, default=str)
                        }
                    ]
                }
            )

        elif tool_name == "get_patient_encounters":
            patient_id = arguments.get("patient_id")
            limit = arguments.get("limit", 20)
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT
                        resource->>'id' as encounter_id,
                        resource->'type'->0->'coding'->0->>'display' as encounter_type,
                        resource->'period'->>'start' as start_date,
                        resource->'period'->>'end' as end_date,
                        resource->'serviceProvider'->>'display' as provider,
                        resource->>'status' as status,
                        resource->'class'->>'display' as encounter_class
                    FROM fhir.encounter
                    WHERE patient_id = %s
                    ORDER BY resource->'period'->>'start' DESC
                    LIMIT %s
                """, (patient_id, limit))
                results = cur.fetchall()

            conn.close()
            return MCPResponse(
                id=request_id,
                result={
                    "content": [
                        {
                            "type": "text",
                            "text": json.dumps({"encounters": results, "count": len(results)}, default=str)
                        }
                    ]
                }
            )

        elif tool_name == "get_patient_allergies":
            patient_id = arguments.get("patient_id")
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT
                        resource->>'id' as allergy_id,
                        resource->'code'->'coding'->0->>'display' as allergy_name,
                        resource->'code'->'coding'->0->>'code' as snomed_code,
                        resource->>'type' as allergy_type,
                        resource->>'category'->0 as category,
                        resource->>'criticality' as criticality,
                        resource->'reaction'->0->'manifestation'->0->'coding'->0->>'display' as reaction,
                        resource->>'recordedDate' as recorded_date
                    FROM fhir.allergy_intolerance
                    WHERE patient_id = %s
                """, (patient_id,))
                results = cur.fetchall()

            conn.close()
            return MCPResponse(
                id=request_id,
                result={
                    "content": [
                        {
                            "type": "text",
                            "text": json.dumps({"allergies": results, "count": len(results)}, default=str)
                        }
                    ]
                }
            )

        elif tool_name == "search_procedures":
            procedure_code = arguments.get("procedure_code")
            procedure_text = arguments.get("procedure_text")

            with conn.cursor() as cur:
                if procedure_code:
                    cur.execute("""
                        SELECT DISTINCT
                            patient_id,
                            resource->'code'->'coding'->0->>'display' as procedure_name,
                            resource->'code'->'coding'->0->>'code' as procedure_code,
                            resource->>'performedDateTime' as performed_date
                        FROM fhir.procedure
                        WHERE resource->'code'->'coding'->0->>'code' = %s
                        ORDER BY resource->>'performedDateTime' DESC
                        LIMIT 20
                    """, (procedure_code,))
                elif procedure_text:
                    cur.execute("""
                        SELECT DISTINCT
                            patient_id,
                            resource->'code'->'coding'->0->>'display' as procedure_name,
                            resource->'code'->'coding'->0->>'code' as procedure_code,
                            resource->>'performedDateTime' as performed_date
                        FROM fhir.procedure
                        WHERE resource->'code'->'coding'->0->>'display' ILIKE %s
                        ORDER BY resource->>'performedDateTime' DESC
                        LIMIT 20
                    """, (f'%{procedure_text}%',))
                else:
                    results = []

                results = cur.fetchall() if procedure_code or procedure_text else []

            conn.close()
            return MCPResponse(
                id=request_id,
                result={
                    "content": [
                        {
                            "type": "text",
                            "text": json.dumps({"procedures": results, "count": len(results)}, default=str)
                        }
                    ]
                }
            )

        elif tool_name == "get_started":
            # Return comprehensive getting started guide
            guide = """# FHIR Database Quick Start Guide

## ✅ Database Contains:
- 117 synthetic patients from Synthea
- 79,013 observations (vitals, labs)
- 22,216 procedures
- 9,200 encounters
- 6,792 medications
- 4,554 conditions
- 1,623 immunizations
- 88 allergies

## 🗂️ Table Structure:
All data is in JSONB format in the 'resource' column:
- fhir.patient
- fhir.observation
- fhir.condition
- fhir.procedure
- fhir.medication_request
- fhir.encounter
- fhir.immunization
- fhir.allergy_intolerance

## 🔧 JSONB Query Operators:
- -> : Get JSON field (returns JSON)
- ->> : Get JSON field as text
- ->0 : Get first array element
- ILIKE : Case-insensitive search

## 📋 Example Queries:

### Find flu vaccines:
```sql
SELECT patient_id,
       resource->'vaccineCode'->'coding'->0->>'display' as vaccine
FROM fhir.immunization
WHERE resource->'vaccineCode'->'coding'->0->>'display' ILIKE '%flu%'
```

### Find diabetic patients:
```sql
SELECT DISTINCT patient_id
FROM fhir.condition
WHERE resource->'code'->'coding'->0->>'display' ILIKE '%diabetes%'
```

### Get blood pressure:
```sql
SELECT patient_id,
       resource->'component'->0->'valueQuantity'->>'value' as systolic,
       resource->'component'->1->'valueQuantity'->>'value' as diastolic
FROM fhir.observation
WHERE resource->'code'->'coding'->0->>'code' = '85354-9'
```

## 💡 Tips:
- Use search_* tools for common queries
- Use query_fhir for custom SQL
- Data may be in 'text' or 'coding' fields
- Always check both locations!"""

            return MCPResponse(
                id=request_id,
                result={
                    "content": [
                        {
                            "type": "text",
                            "text": guide
                        }
                    ]
                }
            )

        elif tool_name == "get_statistics":
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT 'patient' as resource_type, COUNT(*) as count FROM fhir.patient
                    UNION ALL SELECT 'observation', COUNT(*) FROM fhir.observation
                    UNION ALL SELECT 'condition', COUNT(*) FROM fhir.condition
                    UNION ALL SELECT 'procedure', COUNT(*) FROM fhir.procedure
                    UNION ALL SELECT 'medication_request', COUNT(*) FROM fhir.medication_request
                    UNION ALL SELECT 'allergy_intolerance', COUNT(*) FROM fhir.allergy_intolerance
                    UNION ALL SELECT 'immunization', COUNT(*) FROM fhir.immunization
                    UNION ALL SELECT 'encounter', COUNT(*) FROM fhir.encounter
                    ORDER BY count DESC
                """)
                results = cur.fetchall()

            conn.close()
            return MCPResponse(
                id=request_id,
                result={
                    "content": [
                        {
                            "type": "text",
                            "text": json.dumps({"statistics": results}, default=str)
                        }
                    ]
                }
            )

        else:
            return MCPResponse(
                id=request_id,
                error={"code": -32601, "message": f"Unknown tool: {tool_name}"}
            )

    except Exception as e:
        logger.error(f"Error executing tool {tool_name}: {e}")
        return MCPResponse(
            id=request_id,
            error={"code": -32603, "message": str(e)}
        )

# SSE endpoints for supergateway compatibility
@app.get("/sse")
async def sse_connection():
    """GET endpoint to establish SSE connection for supergateway"""
    session_id = str(uuid.uuid4())
    message_queue = asyncio.Queue()
    sse_sessions[session_id] = message_queue

    async def event_generator():
        try:
            # Send initial endpoint event as required by MCP SSE protocol
            yield f"event: endpoint\ndata: /messages?session_id={session_id}\n\n"
            logger.info(f"SSE session {session_id} established")

            # Keep connection alive and forward messages from queue
            while True:
                try:
                    # Wait for messages with timeout to send keepalive
                    message = await asyncio.wait_for(message_queue.get(), timeout=30.0)
                    if message is None:  # Shutdown signal
                        break
                    yield f"data: {json.dumps(message)}\n\n"
                except asyncio.TimeoutError:
                    # Send keepalive comment
                    yield f": keepalive\n\n"
        finally:
            # Clean up session
            if session_id in sse_sessions:
                del sse_sessions[session_id]
            logger.info(f"SSE session {session_id} closed")

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
            "Access-Control-Allow-Origin": "*"
        }
    )

@app.post("/messages")
async def messages_endpoint(mcp_request: MCPRequest, session_id: str):
    """POST endpoint for MCP protocol messages"""

    # Check if session exists
    if session_id not in sse_sessions:
        logger.error(f"Invalid session ID: {session_id}")
        return JSONResponse(
            status_code=400,
            content={"error": "Invalid session ID"}
        )

    try:
        logger.info(f"Processing {mcp_request.method} for session {session_id}")

        # Route to appropriate handler
        if mcp_request.method == "initialize":
            response = await handle_initialize(mcp_request.params, mcp_request.id)
        elif mcp_request.method == "tools/list":
            response = await handle_list_tools(mcp_request.params, mcp_request.id)
        elif mcp_request.method == "tools/call":
            response = await handle_call_tool(mcp_request.params, mcp_request.id)
        elif mcp_request.method == "prompts/list":
            response = await handle_list_prompts(mcp_request.params, mcp_request.id)
        elif mcp_request.method == "prompts/get":
            response = await handle_get_prompt(mcp_request.params, mcp_request.id)
        elif mcp_request.method == "resources/list":
            response = await handle_list_resources(mcp_request.params, mcp_request.id)
        elif mcp_request.method == "resources/read":
            response = await handle_read_resource(mcp_request.params, mcp_request.id)
        else:
            response = MCPResponse(
                id=mcp_request.id,
                error={"code": -32601, "message": f"Method not found: {mcp_request.method}"}
            )

        # Convert response to dict and send to SSE queue
        response_dict = json.loads(response.model_dump_json(exclude_none=True))

        # Send response through SSE channel
        message_queue = sse_sessions[session_id]
        await message_queue.put(response_dict)

        # Also return response directly
        return response_dict

    except Exception as e:
        logger.error(f"Error processing MCP request: {e}")
        error_response = MCPResponse(
            id=mcp_request.id,
            error={"code": -32700, "message": str(e)}
        )
        error_dict = json.loads(error_response.model_dump_json(exclude_none=True))

        # Send error through SSE if possible
        if session_id in sse_sessions:
            await sse_sessions[session_id].put(error_dict)

        return error_dict

# Standard HTTP endpoint for MCP
@app.post("/mcp", response_model_exclude_none=True)
async def mcp_endpoint(mcp_request: MCPRequest):
    """Standard HTTP endpoint for MCP protocol"""

    # Route to appropriate handler
    if mcp_request.method == "initialize":
        response = await handle_initialize(mcp_request.params, mcp_request.id)
    elif mcp_request.method == "tools/list":
        response = await handle_list_tools(mcp_request.params, mcp_request.id)
    elif mcp_request.method == "tools/call":
        response = await handle_call_tool(mcp_request.params, mcp_request.id)
    elif mcp_request.method == "prompts/list":
        response = await handle_list_prompts(mcp_request.params, mcp_request.id)
    elif mcp_request.method == "prompts/get":
        response = await handle_get_prompt(mcp_request.params, mcp_request.id)
    elif mcp_request.method == "resources/list":
        response = await handle_list_resources(mcp_request.params, mcp_request.id)
    elif mcp_request.method == "resources/read":
        response = await handle_read_resource(mcp_request.params, mcp_request.id)
    else:
        response = MCPResponse(
            id=mcp_request.id,
            error={"code": -32601, "message": f"Method not found: {mcp_request.method}"}
        )

    # Return as dict with None values excluded
    return json.loads(response.model_dump_json(exclude_none=True))

# Health check endpoints
@app.get("/")
async def root():
    """Root endpoint for health checks"""
    return {
        "status": "healthy",
        "service": "Synthea FHIR MCP Server",
        "version": SERVER_VERSION,
        "protocol": "MCP",
        "endpoints": {
            "mcp": "/mcp",
            "sse": "/sse",
            "health": "/health"
        }
    }

@app.get("/health")
async def health_check():
    """Health check with database connection test"""
    try:
        conn = get_connection()
        with conn.cursor() as cur:
            cur.execute("SELECT COUNT(*) as count FROM fhir.patient")
            result = cur.fetchone()
        conn.close()
        return {
            "status": "healthy",
            "version": SERVER_VERSION,
            "database": "connected",
            "patient_count": result['count'] if result else 0,
            "mcp_ready": True
        }
    except Exception as e:
        return {
            "status": "error",
            "message": str(e),
            "mcp_ready": False
        }

if __name__ == "__main__":
    import uvicorn
    logger.info(f"Starting Synthea FHIR MCP Server v{SERVER_VERSION}")
    port = int(os.getenv("PORT", "8080"))
    uvicorn.run(app, host="0.0.0.0", port=port, log_level="info")