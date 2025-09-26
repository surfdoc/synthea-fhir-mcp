# Attribution

## Original Work

This project was originally forked from the [mcp-postgres](https://github.com/modelcontextprotocol/servers/tree/main/src/postgres) server created by the Model Context Protocol team.

The original PostgreSQL MCP server provided:
- Generic PostgreSQL database exploration
- Schema and table introspection
- Foreign key relationship discovery
- Multiple transport protocol support (stdio, SSE, HTTP)
- FastMCP framework integration

## Our Adaptations

We've adapted and specialized this codebase specifically for healthcare data, creating a Synthea FHIR MCP server with:

- **Healthcare Focus**: Specialized tools for FHIR resources (patients, conditions, medications, immunizations, etc.)
- **JSONB Optimization**: Query patterns optimized for FHIR's JSONB storage format
- **Cloud Deployment**: Google Cloud Run deployment for beta testing
- **Synthea Integration**: Pre-configured for Synthea synthetic patient data
- **Claude Desktop**: Streamlined integration via SSE/supergateway

## Acknowledgments

Special thanks to:
- The **Model Context Protocol team** for creating the excellent foundation and MCP specification
- The **Synthea team** for providing realistic synthetic patient data
- The **FHIR community** for healthcare data standards

## License

This adapted work maintains the MIT License from the original project.

---

*If you're looking for a generic PostgreSQL MCP server, please check out the [original mcp-postgres](https://github.com/modelcontextprotocol/servers/tree/main/src/postgres) implementation.*