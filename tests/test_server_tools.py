import os
import sys
from pathlib import Path

# Ensure project root is on sys.path for imports
ROOT = str(Path(__file__).resolve().parents[1])
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)


def test_run_query_no_dsn():
    # Ensure no DSN is set
    os.environ.pop("POSTGRES_CONNECTION_STRING", None)
    import postgres_server

    # Simulate missing DSN explicitly
    postgres_server.CONNECTION_STRING = None

    from postgres_server import run_query, QueryInput

    res = run_query(QueryInput(sql="SELECT 1", row_limit=1, format="markdown"))
    assert isinstance(res, str)
    assert "POSTGRES_CONNECTION_STRING is not set" in res


def test_run_query_json_no_dsn():
    os.environ.pop("POSTGRES_CONNECTION_STRING", None)
    import postgres_server

    postgres_server.CONNECTION_STRING = None

    from postgres_server import run_query_json, QueryJSONInput

    res = run_query_json(QueryJSONInput(sql="SELECT 1", row_limit=1))
    assert isinstance(res, list)
    assert res == []


def test_resource_fallbacks_no_dsn():
    os.environ.pop("POSTGRES_CONNECTION_STRING", None)
    import postgres_server

    postgres_server.CONNECTION_STRING = None

    from postgres_server import list_table_resources, read_table_resource

    uris = list_table_resources(schema="public")
    assert uris == []

    rows = read_table_resource(schema="public", table="does_not_matter", row_limit=5)
    assert rows == []


def test_prompts_available():
    from postgres_server import (
        prompt_write_safe_select_tool,
        prompt_explain_plan_tips_tool,
    )

    sel = prompt_write_safe_select_tool()
    exp = prompt_explain_plan_tips_tool()

    assert isinstance(sel, str) and "SELECT" in sel.upper()
    assert isinstance(exp, str) and "EXPLAIN" in exp.upper()


def test_list_schemas_json_no_dsn():
    os.environ.pop("POSTGRES_CONNECTION_STRING", None)
    import postgres_server

    postgres_server.CONNECTION_STRING = None

    from postgres_server import list_schemas_json, ListSchemasInput

    res = list_schemas_json(ListSchemasInput())
    assert isinstance(res, list)
    assert res == []


def test_list_schemas_json_page_no_dsn():
    os.environ.pop("POSTGRES_CONNECTION_STRING", None)
    import postgres_server

    postgres_server.CONNECTION_STRING = None

    from postgres_server import list_schemas_json_page, ListSchemasPageInput

    res = list_schemas_json_page(ListSchemasPageInput())
    assert isinstance(res, dict)
    assert res.get("items") == []
    assert res.get("next_cursor") is None


def test_list_tables_json_no_dsn():
    os.environ.pop("POSTGRES_CONNECTION_STRING", None)
    import postgres_server

    postgres_server.CONNECTION_STRING = None

    from postgres_server import list_tables_json, ListTablesInput

    res = list_tables_json(ListTablesInput(db_schema="public"))
    assert isinstance(res, list)
    assert res == []


def test_list_tables_json_page_no_dsn():
    os.environ.pop("POSTGRES_CONNECTION_STRING", None)
    import postgres_server

    postgres_server.CONNECTION_STRING = None

    from postgres_server import list_tables_json_page, ListTablesPageInput

    res = list_tables_json_page(ListTablesPageInput(db_schema="public"))
    assert isinstance(res, dict)
    assert res.get("items") == []
    assert res.get("next_cursor") is None


def test_db_identity_no_dsn():
    os.environ.pop("POSTGRES_CONNECTION_STRING", None)
    import postgres_server

    postgres_server.CONNECTION_STRING = None

    from postgres_server import db_identity

    res = db_identity()
    assert isinstance(res, dict)
    assert res == {}
