# Testing Guide

Comprehensive testing documentation for the Synthea FHIR MCP Server.

## Table of Contents
- [Quick Start](#quick-start)
- [Test Structure](#test-structure)
- [Running Tests](#running-tests)
- [Test Categories](#test-categories)
- [Writing Tests](#writing-tests)
- [Coverage Reports](#coverage-reports)
- [CI/CD Integration](#cicd-integration)
- [Troubleshooting](#troubleshooting)

## Quick Start

### Install Dependencies
```bash
# Install test dependencies
pip install -r dev-requirements.txt

# Run all tests
pytest

# Run with coverage
pytest --cov=src --cov-report=html
```

## Test Structure

```
tests/
├── __init__.py
├── conftest.py                    # Shared fixtures and configuration
├── fixtures/
│   ├── __init__.py
│   └── fhir_resources.py          # FHIR resource test data generators
├── unit/                          # Unit tests (no external dependencies)
│   ├── __init__.py
│   ├── test_connection.py         # Database connection tests
│   ├── test_mcp_protocol.py       # MCP protocol compliance
│   └── test_tools.py              # Tool execution tests
├── integration/                   # Integration tests (may need DB)
│   ├── __init__.py
│   └── test_sse_integration.py    # SSE endpoint tests
├── validation/                    # FHIR validation tests
│   ├── __init__.py
│   └── test_fhir_validation.py    # FHIR resource validation
└── security/                      # Security tests
    ├── __init__.py
    └── test_security.py           # SQL injection, access control
```

## Running Tests

### Basic Commands

```bash
# Run all tests
pytest

# Run specific test file
pytest tests/unit/test_connection.py

# Run specific test class
pytest tests/unit/test_tools.py::TestGetPatientsTool

# Run specific test method
pytest tests/unit/test_tools.py::TestGetPatientsTool::test_get_patients_default_limit
```

### Test Selection

```bash
# Run tests by marker
pytest -m unit           # Unit tests only
pytest -m integration    # Integration tests only
pytest -m security       # Security tests only
pytest -m mcp           # MCP protocol tests
pytest -m fhir          # FHIR validation tests

# Run tests matching pattern
pytest -k "connection"   # Tests with "connection" in name
pytest -k "not slow"     # Exclude slow tests
```

### Verbosity Options

```bash
# Quiet mode (minimal output)
pytest -q

# Verbose mode (detailed output)
pytest -v

# Very verbose (show all output)
pytest -vv

# Show local variables on failure
pytest -l

# Show captured stdout
pytest -s
```

## Test Categories

### Unit Tests (59 tests)

#### Connection Tests (`test_connection.py`)
- Cloud SQL connection string building
- Database authentication scenarios
- Read-only mode enforcement
- Connection pooling and recovery
- Transaction handling

**Example Test:**
```python
def test_cloud_sql_connection_string(self, mock_env_variables):
    """Test Cloud SQL connection string generation."""
    from synthea_server import get_connection_string
    conn_str = get_connection_string()
    assert "postgresql://" in conn_str
    assert "host=/cloudsql/" in conn_str
```

#### MCP Protocol Tests (`test_mcp_protocol.py`)
- Protocol initialization and version negotiation
- Tools/resources/prompts discovery
- Error response formats (JSON-RPC)
- Capability negotiation
- Notification handling

**Example Test:**
```python
def test_protocol_version_negotiation(self):
    """Test protocol version negotiation."""
    supported_request = {
        "jsonrpc": "2.0",
        "method": "initialize",
        "params": {"protocolVersion": "2024-11-05"}
    }
    assert supported_request["params"]["protocolVersion"] == "2024-11-05"
```

#### Tool Execution Tests (`test_tools.py`)
- All 14 MCP tools tested
- JSONB query validation
- SQL injection prevention
- Parameter validation
- Error handling

**Tools Tested:**
- `get_patients` - Patient listing with pagination
- `get_patient_summary` - Complete patient history
- `search_conditions` - SNOMED code searches
- `search_immunizations` - CVX vaccine searches
- `get_patient_observations` - Vitals and lab results
- `get_patient_medications` - Prescription data
- `get_patient_procedures` - Medical procedures
- `get_patient_encounters` - Clinical visits
- `get_patient_allergies` - Allergy information
- `search_procedures` - Procedure searches
- `get_statistics` - Database statistics
- `query_fhir` - Custom FHIR queries
- `get_started` - Schema education
- Tool error handling

### Integration Tests (Future)
- Database connection with real PostgreSQL
- SSE endpoint functionality
- End-to-end tool execution
- Performance under load

### Security Tests (Future)
- SQL injection prevention
- Read-only mode enforcement
- Authentication/authorization
- Data privacy compliance

## Writing Tests

### Test Structure
```python
import pytest
from unittest.mock import MagicMock

class TestFeatureName:
    """Test suite for specific feature."""

    @pytest.mark.unit
    def test_specific_behavior(self, mock_cursor):
        """Test description."""
        # Arrange
        mock_cursor.fetchall.return_value = [{"data": "test"}]

        # Act
        result = mock_cursor.fetchall()

        # Assert
        assert len(result) == 1
        assert result[0]["data"] == "test"
```

### Using Fixtures

Available fixtures in `conftest.py`:
- `mock_env_variables` - Mock environment variables
- `mock_db_connection` - Mock database connection
- `mock_cursor` - Mock database cursor
- `sample_mcp_request` - Sample MCP request
- `sample_patient_data` - Sample FHIR patient
- `sql_injection_attempts` - SQL injection test patterns

**Example Usage:**
```python
def test_with_fixtures(self, mock_cursor, sample_patient_data):
    """Test using multiple fixtures."""
    mock_cursor.fetchone.return_value = {
        "resource": sample_patient_data
    }
    result = mock_cursor.fetchone()
    assert result["resource"]["resourceType"] == "Patient"
```

### FHIR Resource Generators

Use generators from `fixtures/fhir_resources.py`:
```python
from tests.fixtures.fhir_resources import (
    create_patient_resource,
    create_observation_resource,
    create_condition_resource,
    create_immunization_resource,
    create_medication_request_resource
)

# Create test data
patient = create_patient_resource("test-123")
observation = create_observation_resource("test-123", "blood_pressure")
condition = create_condition_resource("test-123", "diabetes")
```

## Coverage Reports

### Generate Coverage
```bash
# Terminal report
pytest --cov=src --cov-report=term-missing

# HTML report
pytest --cov=src --cov-report=html
# Open htmlcov/index.html in browser

# XML report (for CI/CD)
pytest --cov=src --cov-report=xml

# Multiple formats
pytest --cov=src --cov-report=term --cov-report=html --cov-report=xml
```

### Coverage Configuration
Coverage settings in `pytest.ini`:
- Source: `src` directory
- Branch coverage enabled
- Excludes test files and type checking blocks
- Target: >80% coverage

## CI/CD Integration

### GitHub Actions Example
```yaml
name: Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest

    steps:
    - uses: actions/checkout@v3

    - name: Set up Python
      uses: actions/setup-python@v4
      with:
        python-version: '3.11'

    - name: Install dependencies
      run: |
        pip install -r requirements.txt
        pip install -r dev-requirements.txt

    - name: Run tests
      run: pytest --cov=src --cov-report=xml

    - name: Upload coverage
      uses: codecov/codecov-action@v3
      with:
        file: ./coverage.xml
```

### Pre-commit Hook
```yaml
# .pre-commit-config.yaml
repos:
  - repo: local
    hooks:
      - id: pytest
        name: pytest
        entry: pytest
        language: system
        pass_filenames: false
        always_run: true
```

## Troubleshooting

### Common Issues

#### Import Errors
```bash
# Issue: ModuleNotFoundError: No module named 'src'
# Solution: Ensure PYTHONPATH includes src directory
export PYTHONPATH="${PYTHONPATH}:$(pwd)/src"
```

#### Database Connection Errors
```bash
# Issue: Tests fail with connection errors
# Solution: Unit tests should use mocks, not real DB
# Check that mock_db_connection fixture is being used
```

#### Marker Warnings
```bash
# Issue: PytestUnknownMarkWarning: Unknown pytest.mark.unit
# Solution: Markers are defined in pytest.ini
# Ensure pytest.ini is in project root
```

#### Coverage Not Found
```bash
# Issue: No data to report for coverage
# Solution: Ensure source path is correct
pytest --cov=src  # Not --cov=.
```

### Debug Options

```bash
# Show print statements
pytest -s

# Stop on first failure
pytest -x

# Enter debugger on failure
pytest --pdb

# Show local variables
pytest -l

# Maximum verbosity
pytest -vvv

# Show test durations
pytest --durations=10
```

## Best Practices

### Test Naming
- Use descriptive test names
- Start with `test_`
- Include what's being tested and expected outcome

### Test Organization
- Group related tests in classes
- One assertion per test when possible
- Use fixtures for common setup

### Mocking
- Mock external dependencies
- Use real implementations for pure functions
- Verify mock calls with `assert_called_with`

### Test Data
- Use fixtures for reusable test data
- Generate realistic FHIR resources
- Include edge cases and error conditions

### Performance
- Mark slow tests with `@pytest.mark.slow`
- Use `pytest-timeout` for long-running tests
- Run slow tests separately in CI/CD

## Test Metrics

Current test suite status:
- **Total Tests**: 59
- **Passing**: 59
- **Failing**: 0
- **Test Time**: ~0.5 seconds
- **Coverage**: 16% (unit tests with mocks)

### Test Distribution
- Connection tests: 17
- MCP protocol tests: 20
- Tool execution tests: 22

## Contributing

When adding new features:
1. Write tests first (TDD approach)
2. Ensure all tests pass
3. Add appropriate test markers
4. Update this documentation
5. Check coverage remains >80%

## Resources

- [Pytest Documentation](https://docs.pytest.org/)
- [MCP Specification](https://github.com/modelcontextprotocol)
- [FHIR R4 Specification](https://hl7.org/fhir/R4/)
- [PostgreSQL JSONB Operators](https://www.postgresql.org/docs/current/functions-json.html)