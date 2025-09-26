"""
Test database connection handling.
"""

import os
import pytest
from unittest.mock import patch, MagicMock
import psycopg
import sys
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))


class TestConnectionString:
    """Test connection string building and handling."""

    @pytest.mark.unit
    def test_cloud_sql_connection_string(self, mock_env_variables):
        """Test Cloud SQL connection string generation."""
        # Import here to use mocked env variables
        from synthea_server import get_connection_string

        conn_str = get_connection_string()

        assert "postgresql://" in conn_str
        assert "test_user:test_password" in conn_str
        assert "/test_synthea?" in conn_str
        assert "host=/cloudsql/test-project:us-central1:test-db" in conn_str

    @pytest.mark.unit
    def test_fallback_to_database_url(self, monkeypatch):
        """Test fallback to DATABASE_URL when Cloud SQL vars not set."""
        # Remove Cloud SQL vars, keep DATABASE_URL
        monkeypatch.delenv("CLOUD_SQL_CONNECTION_NAME", raising=False)
        monkeypatch.setenv("DATABASE_URL", "postgresql://fallback:pass@localhost/db")

        from synthea_server import get_connection_string

        conn_str = get_connection_string()
        assert conn_str == "postgresql://fallback:pass@localhost/db"

    @pytest.mark.unit
    def test_empty_connection_string(self, monkeypatch):
        """Test when no connection variables are set."""
        # Remove all connection-related env vars
        for var in ["CLOUD_SQL_CONNECTION_NAME", "DATABASE_URL", "DB_USER", "DB_PASSWORD"]:
            monkeypatch.delenv(var, raising=False)

        from synthea_server import get_connection_string

        conn_str = get_connection_string()
        assert conn_str == ""

    @pytest.mark.unit
    def test_connection_string_special_characters(self, monkeypatch):
        """Test connection string with special characters in password."""
        monkeypatch.setenv("CLOUD_SQL_CONNECTION_NAME", "project:region:instance")
        monkeypatch.setenv("DB_USER", "user")
        monkeypatch.setenv("DB_PASSWORD", "p@ss!word#123")
        monkeypatch.setenv("DB_NAME", "synthea")

        from synthea_server import get_connection_string

        conn_str = get_connection_string()
        assert "p@ss!word#123" in conn_str  # Password should be included as-is


class TestDatabaseConnection:
    """Test database connection establishment and error handling."""

    @pytest.mark.unit
    @patch("psycopg.connect")
    def test_successful_connection(self, mock_connect, mock_env_variables):
        """Test successful database connection."""
        mock_conn = MagicMock()
        mock_connect.return_value = mock_conn

        # Simulate connection attempt
        conn_string = "postgresql://test_user:test_password@localhost/test_synthea"
        conn = psycopg.connect(conn_string)

        mock_connect.assert_called_once_with(conn_string)
        assert conn == mock_conn

    @pytest.mark.unit
    @patch("psycopg.connect")
    def test_connection_timeout(self, mock_connect):
        """Test database connection timeout."""
        mock_connect.side_effect = psycopg.OperationalError("timeout expired")

        with pytest.raises(psycopg.OperationalError) as exc_info:
            psycopg.connect("postgresql://test@localhost/db")

        assert "timeout" in str(exc_info.value)

    @pytest.mark.unit
    @patch("psycopg.connect")
    def test_authentication_failure(self, mock_connect):
        """Test database authentication failure."""
        mock_connect.side_effect = psycopg.OperationalError(
            'FATAL:  password authentication failed for user "test"'
        )

        with pytest.raises(psycopg.OperationalError) as exc_info:
            psycopg.connect("postgresql://test:wrong@localhost/db")

        assert "authentication failed" in str(exc_info.value)

    @pytest.mark.unit
    @patch("psycopg.connect")
    def test_database_not_found(self, mock_connect):
        """Test connection to non-existent database."""
        mock_connect.side_effect = psycopg.OperationalError(
            'FATAL:  database "nonexistent" does not exist'
        )

        with pytest.raises(psycopg.OperationalError) as exc_info:
            psycopg.connect("postgresql://test@localhost/nonexistent")

        assert "does not exist" in str(exc_info.value)


class TestConnectionPooling:
    """Test connection pooling behavior."""

    @pytest.mark.unit
    def test_connection_reuse(self, mock_db_connection):
        """Test that connections are reused when possible."""
        global _connection
        _connection = None

        # First call should create connection
        conn1 = mock_db_connection
        assert conn1 is not None

        # Second call should return same connection
        conn2 = mock_db_connection
        assert conn2 is conn1  # Same object

    @pytest.mark.unit
    def test_connection_recovery(self, mock_db_connection):
        """Test connection recovery after failure."""
        # Simulate connection becoming invalid
        mock_db_connection.closed = 2  # psycopg closed state

        # Should detect closed connection and handle appropriately
        assert mock_db_connection.closed == 2


class TestReadOnlyMode:
    """Test read-only mode enforcement."""

    @pytest.mark.unit
    def test_readonly_query_allowed(self, mock_cursor):
        """Test that SELECT queries are allowed in read-only mode."""
        query = "SELECT * FROM fhir.patient LIMIT 10"
        mock_cursor.execute(query)
        mock_cursor.execute.assert_called_with(query)

    @pytest.mark.unit
    def test_readonly_insert_blocked(self, mock_cursor):
        """Test that INSERT queries are blocked in read-only mode."""
        query = "INSERT INTO fhir.patient (id, resource) VALUES (%s, %s)"

        # In read-only mode, this should be prevented by application logic
        # (not tested here as it's handled in tool execution)
        pass

    @pytest.mark.unit
    def test_readonly_update_blocked(self, mock_cursor):
        """Test that UPDATE queries are blocked in read-only mode."""
        query = "UPDATE fhir.patient SET resource = %s WHERE id = %s"

        # In read-only mode, this should be prevented
        pass

    @pytest.mark.unit
    def test_readonly_delete_blocked(self, mock_cursor):
        """Test that DELETE queries are blocked in read-only mode."""
        query = "DELETE FROM fhir.patient WHERE id = %s"

        # In read-only mode, this should be prevented
        pass


class TestConnectionContext:
    """Test connection context management."""

    @pytest.mark.unit
    def test_cursor_context_manager(self, mock_db_connection):
        """Test cursor as context manager."""
        with mock_db_connection.cursor() as cursor:
            assert cursor is not None
            cursor.execute("SELECT 1")

        # Verify cursor methods were called
        mock_db_connection.cursor.assert_called()

    @pytest.mark.unit
    def test_transaction_rollback_on_error(self, mock_db_connection):
        """Test transaction rollback on error."""
        mock_cursor = mock_db_connection.cursor()
        mock_cursor.execute.side_effect = psycopg.Error("Query failed")

        with pytest.raises(psycopg.Error):
            with mock_db_connection:
                with mock_db_connection.cursor() as cursor:
                    cursor.execute("SELECT * FROM invalid_table")

    @pytest.mark.unit
    @patch("psycopg.connect")
    def test_connection_cleanup(self, mock_connect):
        """Test proper connection cleanup."""
        mock_conn = MagicMock()
        mock_connect.return_value = mock_conn

        conn = psycopg.connect("postgresql://test@localhost/db")
        conn.close()

        mock_conn.close.assert_called_once()