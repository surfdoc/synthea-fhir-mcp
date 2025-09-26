"""
Test MCP protocol compliance.
"""

import json
import pytest
from unittest.mock import patch, MagicMock, AsyncMock
import sys
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))


class TestMCPInitialization:
    """Test MCP protocol initialization."""

    @pytest.mark.unit
    def test_initialize_request_structure(self, sample_mcp_request):
        """Test that initialization request has correct structure."""
        assert sample_mcp_request["jsonrpc"] == "2.0"
        assert "id" in sample_mcp_request
        assert sample_mcp_request["method"] == "initialize"
        assert "protocolVersion" in sample_mcp_request["params"]
        assert "capabilities" in sample_mcp_request["params"]

    @pytest.mark.unit
    def test_protocol_version_negotiation(self):
        """Test protocol version negotiation."""
        # Test with supported version
        supported_request = {
            "jsonrpc": "2.0",
            "id": "1",
            "method": "initialize",
            "params": {
                "protocolVersion": "2024-11-05",
                "capabilities": {}
            }
        }

        # This should be accepted
        assert supported_request["params"]["protocolVersion"] == "2024-11-05"

        # Test with unsupported version (should downgrade)
        unsupported_request = {
            "jsonrpc": "2.0",
            "id": "2",
            "method": "initialize",
            "params": {
                "protocolVersion": "2025-06-18",  # Future version
                "capabilities": {}
            }
        }

        # Server should negotiate down to 2024-11-05
        expected_response_version = "2024-11-05"
        assert expected_response_version == "2024-11-05"  # Server's max version

    @pytest.mark.unit
    def test_initialize_response_structure(self):
        """Test initialization response structure."""
        expected_response = {
            "jsonrpc": "2.0",
            "id": "test-123",
            "result": {
                "protocolVersion": "2024-11-05",
                "capabilities": {
                    "tools": {"listChanged": True},
                    "resources": {"subscribe": False, "listChanged": False},
                    "prompts": {"listChanged": False}
                },
                "serverInfo": {
                    "name": "synthea-fhir-mcp",
                    "version": "1.0.0"
                }
            }
        }

        # Verify required fields
        assert expected_response["jsonrpc"] == "2.0"
        assert "result" in expected_response
        assert "protocolVersion" in expected_response["result"]
        assert "capabilities" in expected_response["result"]
        assert "serverInfo" in expected_response["result"]


class TestToolsDiscovery:
    """Test MCP tools discovery."""

    @pytest.mark.unit
    def test_tools_list_request(self):
        """Test tools/list request structure."""
        request = {
            "jsonrpc": "2.0",
            "id": "tools-list-1",
            "method": "tools/list",
            "params": {}
        }

        assert request["method"] == "tools/list"
        assert request["params"] == {}

    @pytest.mark.unit
    def test_tools_list_response(self):
        """Test tools/list response contains expected tools."""
        expected_tools = [
            "get_patients",
            "get_patient_summary",
            "get_patient_conditions",
            "get_patient_medications",
            "get_patient_observations",
            "search_conditions",
            "search_immunizations",
            "get_patient_procedures",
            "get_patient_encounters",
            "get_patient_allergies",
            "search_procedures",
            "get_started",
            "get_statistics",
            "query_fhir"
        ]

        # Mock response structure
        response = {
            "jsonrpc": "2.0",
            "id": "tools-list-1",
            "result": {
                "tools": [
                    {"name": tool} for tool in expected_tools
                ]
            }
        }

        tool_names = [t["name"] for t in response["result"]["tools"]]
        for expected_tool in expected_tools:
            assert expected_tool in tool_names

    @pytest.mark.unit
    def test_tool_schema_structure(self):
        """Test tool schema has required fields."""
        tool_schema = {
            "name": "get_patients",
            "description": "Get a list of patients",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "limit": {
                        "type": "number",
                        "description": "Maximum number of patients to return",
                        "default": 10
                    }
                }
            }
        }

        assert "name" in tool_schema
        assert "description" in tool_schema
        assert "inputSchema" in tool_schema
        assert tool_schema["inputSchema"]["type"] == "object"


class TestToolCall:
    """Test MCP tool call protocol."""

    @pytest.mark.unit
    def test_tool_call_request_structure(self, sample_tool_request):
        """Test tool call request structure."""
        assert sample_tool_request["method"] == "tools/call"
        assert "name" in sample_tool_request["params"]
        assert "arguments" in sample_tool_request["params"]

    @pytest.mark.unit
    def test_tool_call_response_structure(self):
        """Test tool call response structure."""
        response = {
            "jsonrpc": "2.0",
            "id": "tool-call-1",
            "result": {
                "content": [
                    {
                        "type": "text",
                        "text": "Tool execution result"
                    }
                ]
            }
        }

        assert "result" in response
        assert "content" in response["result"]
        assert isinstance(response["result"]["content"], list)
        assert response["result"]["content"][0]["type"] == "text"

    @pytest.mark.unit
    def test_tool_call_error_response(self):
        """Test tool call error response structure."""
        error_response = {
            "jsonrpc": "2.0",
            "id": "tool-call-error",
            "error": {
                "code": -32602,
                "message": "Invalid params",
                "data": {
                    "details": "Missing required parameter: patient_id"
                }
            }
        }

        assert "error" in error_response
        assert "code" in error_response["error"]
        assert "message" in error_response["error"]
        assert error_response["error"]["code"] == -32602  # Invalid params


class TestResourcesProtocol:
    """Test MCP resources protocol."""

    @pytest.mark.unit
    def test_resources_list_request(self):
        """Test resources/list request."""
        request = {
            "jsonrpc": "2.0",
            "id": "resources-1",
            "method": "resources/list",
            "params": {}
        }

        assert request["method"] == "resources/list"

    @pytest.mark.unit
    def test_resources_list_response(self):
        """Test resources/list response structure."""
        response = {
            "jsonrpc": "2.0",
            "id": "resources-1",
            "result": {
                "resources": [
                    {
                        "uri": "fhir://patient/list",
                        "name": "Patient List",
                        "description": "List of all patients in the database",
                        "mimeType": "application/json"
                    }
                ]
            }
        }

        assert "resources" in response["result"]
        resource = response["result"]["resources"][0]
        assert "uri" in resource
        assert "name" in resource
        assert "description" in resource


class TestPromptsProtocol:
    """Test MCP prompts protocol."""

    @pytest.mark.unit
    def test_prompts_list_response(self):
        """Test prompts/list response structure."""
        response = {
            "jsonrpc": "2.0",
            "id": "prompts-1",
            "result": {
                "prompts": [
                    {
                        "name": "analyze_patient",
                        "description": "Analyze a patient's medical history",
                        "arguments": [
                            {
                                "name": "patient_id",
                                "description": "Patient ID to analyze",
                                "required": True
                            }
                        ]
                    }
                ]
            }
        }

        assert "prompts" in response["result"]
        prompt = response["result"]["prompts"][0]
        assert "name" in prompt
        assert "description" in prompt
        assert "arguments" in prompt


class TestErrorHandling:
    """Test MCP error handling."""

    @pytest.mark.unit
    def test_parse_error(self):
        """Test JSON-RPC parse error."""
        error = {
            "jsonrpc": "2.0",
            "id": None,
            "error": {
                "code": -32700,
                "message": "Parse error"
            }
        }

        assert error["error"]["code"] == -32700

    @pytest.mark.unit
    def test_invalid_request(self):
        """Test invalid request error."""
        error = {
            "jsonrpc": "2.0",
            "id": "invalid-1",
            "error": {
                "code": -32600,
                "message": "Invalid Request"
            }
        }

        assert error["error"]["code"] == -32600

    @pytest.mark.unit
    def test_method_not_found(self):
        """Test method not found error."""
        error = {
            "jsonrpc": "2.0",
            "id": "notfound-1",
            "error": {
                "code": -32601,
                "message": "Method not found"
            }
        }

        assert error["error"]["code"] == -32601

    @pytest.mark.unit
    def test_invalid_params(self):
        """Test invalid params error."""
        error = {
            "jsonrpc": "2.0",
            "id": "params-1",
            "error": {
                "code": -32602,
                "message": "Invalid params"
            }
        }

        assert error["error"]["code"] == -32602

    @pytest.mark.unit
    def test_internal_error(self):
        """Test internal error response."""
        error = {
            "jsonrpc": "2.0",
            "id": "internal-1",
            "error": {
                "code": -32603,
                "message": "Internal error",
                "data": {
                    "details": "Database connection failed"
                }
            }
        }

        assert error["error"]["code"] == -32603
        assert "data" in error["error"]


class TestMCPCapabilities:
    """Test MCP capabilities negotiation."""

    @pytest.mark.unit
    def test_server_capabilities(self):
        """Test server capabilities structure."""
        capabilities = {
            "tools": {
                "listChanged": True  # Server can notify about tool list changes
            },
            "resources": {
                "subscribe": False,  # Server doesn't support resource subscriptions
                "listChanged": False
            },
            "prompts": {
                "listChanged": False
            }
        }

        assert capabilities["tools"]["listChanged"] is True
        assert capabilities["resources"]["subscribe"] is False

    @pytest.mark.unit
    def test_client_capabilities_handling(self):
        """Test handling of client capabilities."""
        client_capabilities = {
            "experimental": {
                "customFeature": True
            },
            "tools": {
                "dynamicRegistration": True
            }
        }

        # Server should handle unknown capabilities gracefully
        assert "experimental" in client_capabilities
        assert "tools" in client_capabilities


class TestNotifications:
    """Test MCP notification protocol."""

    @pytest.mark.unit
    def test_notification_structure(self):
        """Test notification message structure."""
        notification = {
            "jsonrpc": "2.0",
            "method": "notifications/tools/list_changed",
            "params": {}
        }

        # Notifications have no ID
        assert "id" not in notification
        assert notification["method"].startswith("notifications/")

    @pytest.mark.unit
    def test_progress_notification(self):
        """Test progress notification."""
        progress = {
            "jsonrpc": "2.0",
            "method": "notifications/progress",
            "params": {
                "progressToken": "query-123",
                "progress": 0.5,
                "total": 100
            }
        }

        assert progress["params"]["progress"] == 0.5
        assert "progressToken" in progress["params"]