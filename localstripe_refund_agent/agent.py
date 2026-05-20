from langchain_anthropic import ChatAnthropic
from langgraph.prebuilt import create_react_agent

from .prompt import SYSTEM_PROMPT


def build_agent(tools, *, model: str):
    """Build a LangGraph ReAct agent driven by Anthropic Claude."""
    llm = ChatAnthropic(model=model, temperature=0)
    return create_react_agent(llm, tools=tools, prompt=SYSTEM_PROMPT)
