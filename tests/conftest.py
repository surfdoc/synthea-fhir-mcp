"""
Shared fixtures and configuration for all tests.
"""

import json
import os
from unittest.mock import Mock, AsyncMock, MagicMock
from typing import Dict, Any, List

import pytest
import psycopg
from faker import Faker

# Import fixtures from subdirectories
from tests.fixtures.fhir_resources import *

fake = Faker()


@pytest.fixture
def mock_env_variables(monkeypatch):
    """Mock environment variables for testing."""
    test_env = {
        "CLOUD_SQL_CONNECTION_NAME": "test-project:us-central1:test-db",
        "DB_USER": "test_user",
        "DB_PASSWORD": "test_password",
        "DB_NAME": "test_synthea",
        "DATABASE_URL": "postgresql://test_user:test_password@localhost:5432/test_synthea",
        "PORT": "8080"
    }
    for key, value in test_env.items():
        monkeypatch.setenv(key, value)
    return test_env


@pytest.fixture
def mock_db_connection():
    """Mock database connection."""
    mock_conn = MagicMock(spec=psycopg.Connection)
    mock_cursor = MagicMock()

    # Setup cursor behavior
    mock_cursor.__enter__ = MagicMock(return_value=mock_cursor)
    mock_cursor.__exit__ = MagicMock(return_value=None)
    mock_cursor.fetchone = MagicMock(return_value=None)
    mock_cursor.fetchall = MagicMock(return_value=[])

    mock_conn.cursor.return_value = mock_cursor
    mock_conn.__enter__ = MagicMock(return_value=mock_conn)
    mock_conn.__exit__ = MagicMock(return_value=None)

    return mock_conn


@pytest.fixture
def mock_cursor(mock_db_connection):
    """Get mock cursor from mock connection."""
    return mock_db_connection.cursor()


@pytest.fixture
def sample_mcp_request():
    """Sample MCP protocol request."""
    return {
        "jsonrpc": "2.0",
        "id": "test-id-123",
        "method": "initialize",
        "params": {
            "protocolVersion": "2024-11-05",
            "capabilities": {
                "tools": {"listChanged": True}
            },
            "clientInfo": {
                "name": "test-client",
                "version": "1.0.0"
            }
        }
    }


@pytest.fixture
def sample_tool_request():
    """Sample tool call request."""
    return {
        "jsonrpc": "2.0",
        "id": "tool-call-456",
        "method": "tools/call",
        "params": {
            "name": "get_patients",
            "arguments": {
                "limit": 10
            }
        }
    }


@pytest.fixture
def sample_patient_data():
    """Sample FHIR patient resource."""
    return {
        "resourceType": "Patient",
        "id": fake.uuid4(),
        "identifier": [
            {
                "system": "urn:oid:2.16.840.1.113883.4.3.25",
                "value": fake.ssn()
            }
        ],
        "name": [
            {
                "family": fake.last_name(),
                "given": [fake.first_name()],
                "use": "official"
            }
        ],
        "birthDate": fake.date_of_birth().isoformat(),
        "gender": fake.random_element(["male", "female"]),
        "address": [
            {
                "line": [fake.street_address()],
                "city": fake.city(),
                "state": fake.state_abbr(),
                "postalCode": fake.zipcode(),
                "country": "US"
            }
        ]
    }


@pytest.fixture
def sample_observation_data():
    """Sample FHIR observation resource."""
    return {
        "resourceType": "Observation",
        "id": fake.uuid4(),
        "status": "final",
        "category": [
            {
                "coding": [
                    {
                        "system": "http://terminology.hl7.org/CodeSystem/observation-category",
                        "code": "vital-signs",
                        "display": "Vital Signs"
                    }
                ]
            }
        ],
        "code": {
            "coding": [
                {
                    "system": "http://loinc.org",
                    "code": "8867-4",
                    "display": "Heart rate"
                }
            ]
        },
        "subject": {
            "reference": f"Patient/{fake.uuid4()}"
        },
        "effectiveDateTime": fake.date_time().isoformat(),
        "valueQuantity": {
            "value": fake.random_int(60, 100),
            "unit": "beats/min",
            "system": "http://unitsofmeasure.org",
            "code": "/min"
        }
    }


@pytest.fixture
def sample_condition_data():
    """Sample FHIR condition resource."""
    return {
        "resourceType": "Condition",
        "id": fake.uuid4(),
        "clinicalStatus": {
            "coding": [
                {
                    "system": "http://terminology.hl7.org/CodeSystem/condition-clinical",
                    "code": "active"
                }
            ]
        },
        "verificationStatus": {
            "coding": [
                {
                    "system": "http://terminology.hl7.org/CodeSystem/condition-ver-status",
                    "code": "confirmed"
                }
            ]
        },
        "code": {
            "coding": [
                {
                    "system": "http://snomed.info/sct",
                    "code": "44054006",
                    "display": "Type 2 diabetes mellitus"
                }
            ]
        },
        "subject": {
            "reference": f"Patient/{fake.uuid4()}"
        },
        "onsetDateTime": fake.date_time().isoformat()
    }


@pytest.fixture
def sample_immunization_data():
    """Sample FHIR immunization resource."""
    return {
        "resourceType": "Immunization",
        "id": fake.uuid4(),
        "status": "completed",
        "vaccineCode": {
            "coding": [
                {
                    "system": "http://hl7.org/fhir/sid/cvx",
                    "code": "208",
                    "display": "COVID-19 vaccine, mRNA"
                }
            ]
        },
        "patient": {
            "reference": f"Patient/{fake.uuid4()}"
        },
        "occurrenceDateTime": fake.date_time().isoformat(),
        "primarySource": True
    }


@pytest.fixture
def mock_sse_client():
    """Mock SSE client for testing."""
    client = AsyncMock()
    client.send = AsyncMock()
    client.close = AsyncMock()
    return client


@pytest.fixture
def connection_string_variations():
    """Various connection string formats for testing."""
    return [
        "postgresql://user:pass@localhost:5432/db",
        "postgresql://user:pass@/db?host=/cloudsql/project:region:instance",
        "host=localhost port=5432 dbname=db user=user password=pass",
        ""  # Empty string
    ]


@pytest.fixture
def sql_injection_attempts():
    """Common SQL injection patterns for security testing."""
    return [
        "'; DROP TABLE fhir.patient; --",
        "1' OR '1'='1",
        "admin'--",
        "' UNION SELECT * FROM fhir.patient --",
        "1; DELETE FROM fhir.patient WHERE 1=1; --",
        "' OR 1=1 --",
        "'; EXEC xp_cmdshell('net user'); --"
    ]


@pytest.fixture(autouse=True)
def reset_singletons():
    """Reset any singleton instances between tests."""
    # Add any singleton resets here if needed
    yield


@pytest.fixture
def async_mock_cursor():
    """Async mock cursor for database operations."""
    cursor = AsyncMock()
    cursor.execute = AsyncMock()
    cursor.fetchone = AsyncMock(return_value=None)
    cursor.fetchall = AsyncMock(return_value=[])
    cursor.fetchmany = AsyncMock(return_value=[])
    return cursor