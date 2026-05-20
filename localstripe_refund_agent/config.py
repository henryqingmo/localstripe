import os
from dataclasses import dataclass

from .errors import AgentConfigError

DEFAULT_MODEL = "claude-sonnet-4-6"
DEFAULT_MCP_URL = "http://127.0.0.1:8421/mcp/"


@dataclass(frozen=True)
class Settings:
    anthropic_api_key: str
    model: str
    mcp_url: str

    @classmethod
    def from_env(
        cls,
        *,
        model: str | None = None,
        mcp_url: str | None = None,
    ) -> "Settings":
        key = os.environ.get("ANTHROPIC_API_KEY", "")
        if not key:
            raise AgentConfigError("ANTHROPIC_API_KEY is not set")
        return cls(
            anthropic_api_key=key,
            model=model or os.environ.get("ANTHROPIC_MODEL", DEFAULT_MODEL),
            mcp_url=mcp_url or os.environ.get("MCP_URL", DEFAULT_MCP_URL),
        )
