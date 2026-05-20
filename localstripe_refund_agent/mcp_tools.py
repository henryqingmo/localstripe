from contextlib import asynccontextmanager

from langchain_mcp_adapters.client import MultiServerMCPClient

from .errors import MCPUnreachableError


@asynccontextmanager
async def load_mcp_tools(mcp_url: str):
    """Yield LangChain tools backed by a running localstripe-mcp server."""
    client = MultiServerMCPClient(
        {
            "localstripe": {
                "url": mcp_url,
                "transport": "streamable_http",
            }
        }
    )
    try:
        tools = await client.get_tools()
    except Exception as e:
        raise MCPUnreachableError(
            f"could not load MCP tools from {mcp_url}: {e}"
        ) from e
    if not tools:
        raise MCPUnreachableError(f"MCP server at {mcp_url} advertised no tools")
    yield tools
