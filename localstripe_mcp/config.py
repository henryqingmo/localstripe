import os
from dataclasses import dataclass


@dataclass(frozen=True)
class Settings:
    base_url: str
    api_key: str
    host: str
    port: int
    transport: str

    @classmethod
    def from_env(cls) -> "Settings":
        return cls(
            base_url=os.environ.get("LOCALSTRIPE_URL", "http://localhost:8420"),
            api_key=os.environ.get("LOCALSTRIPE_API_KEY", "sk_test_12345"),
            host=os.environ.get("MCP_HOST", "127.0.0.1"),
            port=int(os.environ.get("MCP_PORT", "8421")),
            transport=os.environ.get("MCP_TRANSPORT", "streamable-http"),
        )
