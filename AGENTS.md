# Repository Guidelines

These guidelines help contributors work effectively on the PostgreSQL MCP server in this repo.

## Project Structure & Module Organization
- Root module: `postgres_server.py` — FastMCP server exposing PostgreSQL tools.
- Config: `.env` (optional), `smithery.yaml` (publishing metadata).
- Packaging/infra: `requirements.txt`, `Dockerfile`.
- Docs: `README.md`, this `AGENTS.md`.
- No dedicated `src/` or `tests/` directories yet; keep server logic cohesive and small, or start a `src/` layout if adding modules.

## Build, Test, and Development Commands
- Create env: `python -m venv .venv && source .venv/bin/activate`
- Install deps: `pip install -r requirements.txt`
- Run server (no DB): `python postgres_server.py`
- Run with DB: `POSTGRES_CONNECTION_STRING="postgresql://user:pass@host:5432/db" python postgres_server.py`
- Docker build/run: `docker build -t mcp-postgres .` then `docker run -e POSTGRES_CONNECTION_STRING=... -p 8000:8000 mcp-postgres`

## Coding Style & Naming Conventions
- Python 3.10+, 4-space indentation, PEP 8.
- Use type hints (as in current code) and concise docstrings.
- Functions/variables: `snake_case`; classes: `PascalCase`; MCP tool names: short `snake_case`.
- Logging: use the existing `logger` instance; prefer informative, non-PII messages.
- Optional formatting/linting: `black` and `ruff` (not enforced in repo). Example: `pip install black ruff && ruff check . && black .`.

## Testing Guidelines
- There is no test suite yet. Prefer adding `pytest` with tests under `tests/` named `test_*.py`.
- For DB behaviors, use a disposable PostgreSQL instance or mock `psycopg2` connections.
- Minimum smoke test: start server without DSN, verify each tool returns the friendly “connection string is not set” message.

## Typed Tools & Resources
- Preferred tools: `run_query(QueryInput)` and `run_query_json(QueryJSONInput)` with validated inputs (via Pydantic) and `row_limit` safeguards.
- Legacy tools `query`/`query_json` remain for backward compatibility.
- Table resources: `table://{schema}/{table}` (best-effort registration), with fallback tools `list_table_resources` and `read_table_resource`.
- Prompts available as MCP prompts and tools: `write_safe_select`, `explain_plan_tips`.

## Tests
- Test deps: `dev-requirements.txt` (`pytest`, `pytest-cov`).
- Layout: `tests/test_server_tools.py` includes no-DSN smoke tests and prompt checks.
- Run: `pytest -q`. Ensure runtime deps installed from `requirements.txt`.

## Commit & Pull Request Guidelines
- Commit style: conventional commits preferred (`feat:`, `fix:`, `chore:`, `docs:`). Keep subjects imperative and concise.
- PRs should include: purpose & scope, before/after behavior, example commands/queries, and any config changes (`POSTGRES_CONNECTION_STRING`, Docker, `mcp.json`).
- When adding tools, document them in `README.md` (name, args, example) and ensure safe output formatting.
- Never commit secrets. `.env`, `.venv`, and credentials are ignored by `.gitignore`.

## Security & Configuration Tips
- Pass DB credentials via `POSTGRES_CONNECTION_STRING` env var; avoid hardcoding.
- Prefer least-privilege DB users and SSL options (e.g., add `?sslmode=require`).
- The server runs without a DSN for inspection; database-backed tools should fail gracefully (maintain this behavior).
