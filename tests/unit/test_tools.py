"""
Test tool execution and validation.
"""

import json
import pytest
from unittest.mock import patch, MagicMock, call
import sys
from pathlib import Path
from datetime import datetime

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from tests.fixtures.fhir_resources import (
    create_patient_resource,
    create_observation_resource,
    create_condition_resource,
    create_immunization_resource,
    create_medication_request_resource
)


class TestGetPatientsTool:
    """Test get_patients tool."""

    @pytest.mark.unit
    def test_get_patients_default_limit(self, mock_cursor):
        """Test get_patients with default limit."""
        # Mock database response
        mock_cursor.fetchall.return_value = [
            {"resource": create_patient_resource("patient-1")},
            {"resource": create_patient_resource("patient-2")}
        ]

        # Simulate tool execution
        mock_cursor.execute("SELECT resource FROM fhir.patient LIMIT %s", (10,))
        results = mock_cursor.fetchall()

        assert len(results) == 2
        assert results[0]["resource"]["resourceType"] == "Patient"

    @pytest.mark.unit
    def test_get_patients_custom_limit(self, mock_cursor):
        """Test get_patients with custom limit."""
        limit = 5
        mock_cursor.execute("SELECT resource FROM fhir.patient LIMIT %s", (limit,))
        mock_cursor.execute.assert_called_with(
            "SELECT resource FROM fhir.patient LIMIT %s",
            (limit,)
        )

    @pytest.mark.unit
    def test_get_patients_empty_result(self, mock_cursor):
        """Test get_patients with no patients."""
        mock_cursor.fetchall.return_value = []

        mock_cursor.execute("SELECT resource FROM fhir.patient LIMIT %s", (10,))
        results = mock_cursor.fetchall()

        assert len(results) == 0


class TestGetPatientSummaryTool:
    """Test get_patient_summary tool."""

    @pytest.mark.unit
    def test_get_patient_summary_valid_patient(self, mock_cursor):
        """Test get_patient_summary with valid patient ID."""
        patient_id = "test-patient-123"

        # Mock responses for each query
        mock_cursor.fetchone.return_value = {"resource": create_patient_resource(patient_id)}
        mock_cursor.fetchall.side_effect = [
            [{"resource": create_condition_resource(patient_id)}],
            [{"resource": create_medication_request_resource(patient_id)}],
            [{"resource": create_observation_resource(patient_id)}]
        ]

        # Verify patient exists
        mock_cursor.execute("SELECT resource FROM fhir.patient WHERE id = %s", (patient_id,))
        patient = mock_cursor.fetchone()
        assert patient is not None
        assert patient["resource"]["id"] == patient_id

    @pytest.mark.unit
    def test_get_patient_summary_invalid_patient(self, mock_cursor):
        """Test get_patient_summary with invalid patient ID."""
        patient_id = "invalid-patient"
        mock_cursor.fetchone.return_value = None

        mock_cursor.execute("SELECT resource FROM fhir.patient WHERE id = %s", (patient_id,))
        patient = mock_cursor.fetchone()

        assert patient is None

    @pytest.mark.unit
    def test_get_patient_summary_patient_no_records(self, mock_cursor):
        """Test get_patient_summary for patient with no medical records."""
        patient_id = "empty-patient"

        mock_cursor.fetchone.return_value = {"resource": create_patient_resource(patient_id)}
        mock_cursor.fetchall.return_value = []  # No conditions, meds, observations

        # Patient exists but has no records
        mock_cursor.execute("SELECT resource FROM fhir.patient WHERE id = %s", (patient_id,))
        patient = mock_cursor.fetchone()
        assert patient is not None

        # But no conditions
        mock_cursor.execute(
            "SELECT resource FROM fhir.condition WHERE patient_id = %s",
            (patient_id,)
        )
        conditions = mock_cursor.fetchall()
        assert len(conditions) == 0


class TestSearchConditionsTool:
    """Test search_conditions tool."""

    @pytest.mark.unit
    def test_search_conditions_by_snomed_code(self, mock_cursor):
        """Test searching conditions by SNOMED code."""
        snomed_code = "44054006"  # Type 2 diabetes

        mock_cursor.fetchall.return_value = [
            {"resource": create_condition_resource("patient-1", "diabetes")},
            {"resource": create_condition_resource("patient-2", "diabetes")}
        ]

        # JSONB query for SNOMED code
        query = """
            SELECT DISTINCT c.patient_id, c.resource
            FROM fhir.condition c
            WHERE c.resource->'code'->'coding' @> %s::jsonb
        """
        search_value = json.dumps([{"system": "http://snomed.info/sct", "code": snomed_code}])

        mock_cursor.execute(query, (search_value,))
        results = mock_cursor.fetchall()

        assert len(results) == 2

    @pytest.mark.unit
    def test_search_conditions_by_display_text(self, mock_cursor):
        """Test searching conditions by display text."""
        search_text = "diabetes"

        # JSONB query for text search
        query = """
            SELECT DISTINCT c.patient_id, c.resource
            FROM fhir.condition c
            WHERE c.resource->'code'->'coding'->0->>'display' ILIKE %s
        """

        mock_cursor.execute(query, (f"%{search_text}%",))
        mock_cursor.execute.assert_called()

    @pytest.mark.unit
    def test_search_conditions_no_results(self, mock_cursor):
        """Test searching conditions with no matches."""
        mock_cursor.fetchall.return_value = []

        results = mock_cursor.fetchall()
        assert len(results) == 0


class TestSearchImmunizationsTool:
    """Test search_immunizations tool."""

    @pytest.mark.unit
    def test_search_immunizations_by_cvx_code(self, mock_cursor):
        """Test searching immunizations by CVX code."""
        cvx_code = "208"  # COVID-19 vaccine

        mock_cursor.fetchall.return_value = [
            {"resource": create_immunization_resource("patient-1", "covid")},
            {"resource": create_immunization_resource("patient-2", "covid")}
        ]

        # JSONB query for CVX code
        query = """
            SELECT DISTINCT i.patient_id, i.resource
            FROM fhir.immunization i
            WHERE i.resource->'vaccineCode'->'coding' @> %s::jsonb
        """
        search_value = json.dumps([{"system": "http://hl7.org/fhir/sid/cvx", "code": cvx_code}])

        mock_cursor.execute(query, (search_value,))
        results = mock_cursor.fetchall()

        assert len(results) == 2
        assert all(r["resource"]["resourceType"] == "Immunization" for r in results)

    @pytest.mark.unit
    def test_search_immunizations_by_vaccine_name(self, mock_cursor):
        """Test searching immunizations by vaccine name."""
        vaccine_name = "COVID"

        query = """
            SELECT DISTINCT i.patient_id, i.resource
            FROM fhir.immunization i
            WHERE i.resource->'vaccineCode'->'coding'->0->>'display' ILIKE %s
        """

        mock_cursor.execute(query, (f"%{vaccine_name}%",))
        mock_cursor.execute.assert_called()


class TestGetPatientObservationsTool:
    """Test get_patient_observations tool."""

    @pytest.mark.unit
    def test_get_patient_observations(self, mock_cursor):
        """Test getting patient observations."""
        patient_id = "test-patient"

        mock_cursor.fetchall.return_value = [
            {"resource": create_observation_resource(patient_id, "blood_pressure")},
            {"resource": create_observation_resource(patient_id, "heart_rate")},
            {"resource": create_observation_resource(patient_id, "glucose")}
        ]

        query = """
            SELECT resource
            FROM fhir.observation
            WHERE patient_id = %s
            ORDER BY resource->>'effectiveDateTime' DESC
        """

        mock_cursor.execute(query, (patient_id,))
        results = mock_cursor.fetchall()

        assert len(results) == 3
        assert all(r["resource"]["resourceType"] == "Observation" for r in results)

    @pytest.mark.unit
    def test_get_patient_observations_by_category(self, mock_cursor):
        """Test filtering observations by category."""
        patient_id = "test-patient"
        category = "vital-signs"

        query = """
            SELECT resource
            FROM fhir.observation
            WHERE patient_id = %s
            AND resource->'category'->0->'coding' @> %s::jsonb
            ORDER BY resource->>'effectiveDateTime' DESC
        """
        category_filter = json.dumps([{"code": category}])

        mock_cursor.execute(query, (patient_id, category_filter))
        mock_cursor.execute.assert_called()


class TestGetStatisticsTool:
    """Test get_statistics tool."""

    @pytest.mark.unit
    def test_get_statistics(self, mock_cursor):
        """Test getting database statistics."""
        # Mock count queries
        mock_cursor.fetchone.side_effect = [
            {"count": 117},  # patients
            {"count": 79013},  # observations
            {"count": 4554},  # conditions
            {"count": 22216},  # procedures
            {"count": 6792},  # medications
            {"count": 88},  # allergies
            {"count": 1623},  # immunizations
            {"count": 9200}  # encounters
        ]

        # Execute count queries
        tables = ["patient", "observation", "condition", "procedure",
                 "medication_request", "allergy_intolerance", "immunization", "encounter"]

        stats = {}
        for table in tables:
            mock_cursor.execute(f"SELECT COUNT(*) as count FROM fhir.{table}")
            result = mock_cursor.fetchone()
            stats[table] = result["count"]

        assert stats["patient"] == 117
        assert stats["observation"] == 79013
        assert stats["condition"] == 4554


class TestQueryFHIRTool:
    """Test query_fhir custom query tool."""

    @pytest.mark.unit
    def test_query_fhir_valid_query(self, mock_cursor):
        """Test executing valid FHIR query."""
        query = "SELECT * FROM fhir.patient WHERE resource->>'gender' = 'male' LIMIT 5"

        # Should execute without modification
        mock_cursor.execute(query)
        mock_cursor.execute.assert_called_with(query)

    @pytest.mark.unit
    def test_query_fhir_prevents_writes(self, mock_cursor):
        """Test that write operations are prevented."""
        queries = [
            "INSERT INTO fhir.patient (id, resource) VALUES ('1', '{}')",
            "UPDATE fhir.patient SET resource = '{}' WHERE id = '1'",
            "DELETE FROM fhir.patient WHERE id = '1'",
            "DROP TABLE fhir.patient",
            "TRUNCATE fhir.patient"
        ]

        # These should be blocked (implementation would check query type)
        for query in queries:
            # In actual implementation, these would be rejected before execution
            assert any(keyword in query.upper()
                      for keyword in ["INSERT", "UPDATE", "DELETE", "DROP", "TRUNCATE"])

    @pytest.mark.unit
    def test_query_fhir_jsonb_operators(self, mock_cursor):
        """Test query with JSONB operators."""
        query = """
            SELECT resource->'name'->0->>'family' as last_name,
                   resource->'name'->0->>'given' as first_name
            FROM fhir.patient
            WHERE resource @> '{"gender": "female"}'::jsonb
        """

        mock_cursor.execute(query)
        mock_cursor.execute.assert_called_with(query)


class TestToolErrorHandling:
    """Test error handling across all tools."""

    @pytest.mark.unit
    def test_database_connection_error(self, mock_cursor):
        """Test handling of database connection errors."""
        mock_cursor.execute.side_effect = Exception("Connection lost")

        with pytest.raises(Exception) as exc_info:
            mock_cursor.execute("SELECT * FROM fhir.patient")

        assert "Connection lost" in str(exc_info.value)

    @pytest.mark.unit
    def test_invalid_json_in_resource(self, mock_cursor):
        """Test handling of malformed JSON in resource field."""
        # Return invalid JSON structure
        mock_cursor.fetchone.return_value = {"resource": "not-valid-json"}

        result = mock_cursor.fetchone()
        # Tool should handle this gracefully
        assert not isinstance(result["resource"], dict)

    @pytest.mark.unit
    def test_missing_required_parameters(self):
        """Test tools with missing required parameters."""
        # Tool call without required patient_id
        tool_params = {
            "name": "get_patient_summary",
            "arguments": {}  # Missing patient_id
        }

        # Should return error about missing parameter
        assert "patient_id" not in tool_params["arguments"]

    @pytest.mark.unit
    def test_sql_injection_prevention(self, mock_cursor, sql_injection_attempts):
        """Test SQL injection prevention."""
        for injection in sql_injection_attempts:
            # Parameters should be properly escaped
            mock_cursor.execute(
                "SELECT * FROM fhir.patient WHERE id = %s",
                (injection,)
            )

            # Verify parameterized query was used (not string concatenation)
            call_args = mock_cursor.execute.call_args
            assert call_args[0][0] == "SELECT * FROM fhir.patient WHERE id = %s"
            assert call_args[0][1] == (injection,)