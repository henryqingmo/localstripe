class AgentConfigError(Exception):
    """Raised when required configuration is missing or invalid."""


class MCPUnreachableError(Exception):
    """Raised when the MCP server cannot be reached or returns no tools."""
