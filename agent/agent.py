"""LangChain agent setup and ask interface."""

from __future__ import annotations

import logging
import os
from typing import Any

from dotenv import load_dotenv
from langchain_core.messages import HumanMessage
from langchain_openai import ChatOpenAI

from agent.logging_config import setup_logging
from agent.memory import add_memory_entry, summarize_memory_for_prompt
from agent.tool_catalog import (
    format_capabilities_ru,
    format_tool_catalog_for_prompt,
    is_capabilities_query,
)
from agent.tools import ALL_TOOLS

load_dotenv()
setup_logging()
logger = logging.getLogger("agent.core")

SYSTEM_PROMPT = """Ты локальный AI-агент-помощник.

Правила общения:
- Отвечай на русском, если пользователь пишет по-русски.
- Если данных недостаточно, задай уточняющий вопрос.
- Не выдумывай результаты внешних API — используй tools для актуальных данных.
- Кратко указывай, какой инструмент использовал, если это помогает пользователю.
- Если пользователь просит прочитать файл и посчитать статистику текста, вызывай text_stats
  с action="analyze_file" и filename (например demo_summary.txt). Не используй analyze_text
  с пустым text — это даст нулевую статистику. Достаточно одного вызова text_stats для файла.

На вопрос «Что ты умеешь?» перечисляй все 11 инструментов отдельными пунктами.
Не объединяй несколько инструментов в один общий пункт. Используй этот список:

{tool_catalog}

Краткая история диалога:
{memory_summary}
"""

_agent: Any = None


def _build_system_message() -> str:
    return SYSTEM_PROMPT.format(
        tool_catalog=format_tool_catalog_for_prompt(),
        memory_summary=summarize_memory_for_prompt(),
    )


def _build_llm() -> ChatOpenAI:
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError(
            "OPENAI_API_KEY не задан. Скопируйте .env.example в .env и добавьте API key."
        )
    model = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
    return ChatOpenAI(model=model, api_key=api_key, temperature=0)


def _extract_text(result: Any) -> str:
    if isinstance(result, str):
        return result
    if isinstance(result, dict):
        if "output" in result:
            return str(result["output"])
        if "messages" in result and result["messages"]:
            last = result["messages"][-1]
            if hasattr(last, "content"):
                return str(last.content)
            return str(last)
    if hasattr(result, "content"):
        return str(result.content)
    return str(result)


def build_agent():
    """Create LangChain agent with tool-calling support."""
    global _agent
    if _agent is not None:
        return _agent

    llm = _build_llm()
    system_message = _build_system_message()

    try:
        from langchain.agents import create_agent

        _agent = create_agent(
            model=llm,
            tools=ALL_TOOLS,
            system_prompt=system_message,
        )
        logger.info("Agent created via langchain.agents.create_agent")
        return _agent
    except ImportError:
        logger.warning("create_agent unavailable, using ReAct fallback")

    from langchain.agents import AgentExecutor, create_tool_calling_agent
    from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder

    prompt = ChatPromptTemplate.from_messages(
        [
            ("system", system_message),
            MessagesPlaceholder("chat_history", optional=True),
            ("human", "{input}"),
            MessagesPlaceholder("agent_scratchpad"),
        ]
    )
    tool_agent = create_tool_calling_agent(llm, ALL_TOOLS, prompt)
    _agent = AgentExecutor(
        agent=tool_agent,
        tools=ALL_TOOLS,
        verbose=False,
        handle_parsing_errors=True,
    )
    logger.info("Agent created via create_tool_calling_agent fallback")
    return _agent


def ask_agent(user_input: str) -> str:
    """Send user message to the agent and persist a memory entry."""
    logger.info("User input: %s", user_input)

    if is_capabilities_query(user_input):
        response = format_capabilities_ru()
        add_memory_entry(user_message=user_input, assistant_response=response)
        logger.info("Capabilities shortcut response (no LLM call)")
        return response

    agent = build_agent()

    try:
        if hasattr(agent, "invoke"):
            try:
                result = agent.invoke({"messages": [HumanMessage(content=user_input)]})
            except TypeError:
                result = agent.invoke({"input": user_input})
        else:
            result = agent(user_input)

        response = _extract_text(result).strip()
        if not response:
            response = "Не удалось получить ответ от агента."

        add_memory_entry(user_message=user_input, assistant_response=response)
        logger.info("Assistant response saved to memory")
        return response
    except Exception as exc:
        logger.exception("Agent error")
        error_text = f"Ошибка агента: {exc}"
        add_memory_entry(user_message=user_input, assistant_response=error_text)
        return error_text
