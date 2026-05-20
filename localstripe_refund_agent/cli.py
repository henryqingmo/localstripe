import argparse
import asyncio
import json
import sys

from .agent import build_agent
from .config import Settings
from .errors import AgentConfigError, MCPUnreachableError
from .mcp_tools import load_mcp_tools


def main() -> None:
    p = argparse.ArgumentParser(
        prog="localstripe-refund-agent",
        description="LangGraph refund agent over the localstripe MCP server.",
    )
    p.add_argument("request", help="Natural-language refund request")
    p.add_argument("--model", default=None, help="Override ANTHROPIC_MODEL")
    p.add_argument("--mcp-url", default=None, help="Override MCP_URL")
    p.add_argument(
        "--quiet",
        action="store_true",
        help="Suppress intermediate tool-call output on stderr",
    )
    args = p.parse_args()

    try:
        settings = Settings.from_env(model=args.model, mcp_url=args.mcp_url)
    except AgentConfigError as e:
        print(f"config error: {e}", file=sys.stderr)
        sys.exit(2)

    try:
        asyncio.run(_run(settings, args.request, quiet=args.quiet))
    except MCPUnreachableError as e:
        print(f"MCP server unreachable: {e}", file=sys.stderr)
        sys.exit(3)
    except KeyboardInterrupt:
        sys.exit(130)
    except Exception as e:
        print(f"agent error: {e}", file=sys.stderr)
        sys.exit(1)


async def _run(settings: Settings, request: str, *, quiet: bool) -> None:
    async with load_mcp_tools(settings.mcp_url) as tools:
        agent = build_agent(tools, model=settings.model)
        final_text = ""
        async for event in agent.astream_events(
            {"messages": [{"role": "user", "content": request}]},
            version="v2",
        ):
            kind = event["event"]
            if not quiet and kind == "on_tool_start":
                inp = event["data"].get("input", {})
                print(f"  -> {event['name']}({_fmt(inp)})", file=sys.stderr)
            elif not quiet and kind == "on_tool_end":
                print(f"  <- {event['name']} ok", file=sys.stderr)
            elif kind == "on_chain_end" and event.get("name") == "LangGraph":
                msgs = event["data"]["output"].get("messages", [])
                if msgs:
                    final_text = _text(msgs[-1].content)
        sys.stdout.write(final_text.rstrip() + "\n")


def _fmt(args_dict: dict) -> str:
    s = json.dumps(args_dict, default=str)
    return s if len(s) <= 200 else s[:197] + "..."


def _text(content) -> str:
    # Anthropic content can be a string or a list of {type, text, ...} blocks.
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        return "".join(
            b.get("text", "")
            for b in content
            if isinstance(b, dict) and b.get("type") == "text"
        )
    return ""
