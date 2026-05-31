"""Tests for unified tool catalog and capabilities response."""

from pathlib import Path

import pytest

from agent.agent import ask_agent
from agent.tool_catalog import (
    REQUIRED_FIELDS,
    TOOL_CATALOG,
    format_capabilities_ru,
    is_capabilities_query,
)


def test_tool_catalog_has_11_items():
    assert len(TOOL_CATALOG) == 11


def test_tool_catalog_names_are_unique():
    names = [item["name"] for item in TOOL_CATALOG]
    assert len(names) == len(set(names))


def test_tool_catalog_required_fields():
    for item in TOOL_CATALOG:
        for field in REQUIRED_FIELDS:
            assert field in item
            assert item[field]


def test_capabilities_response_contains_11_numbered_items():
    text = format_capabilities_ru()
    for number in range(1, 12):
        assert f"{number}." in text


def test_capabilities_response_uses_clean_titles():
    text = format_capabilities_ru()

    assert "Проверять курс криптовалют" in text
    assert "Получать курсы обычных валют" in text
    assert "Конвертировать единицы измерения" in text

    assert "Узнавание цен на криптовалюту" not in text
    assert "Конвертация валют и единиц измерения" not in text
    assert "фиатными валютами" not in text
    assert "фиатные валюты" not in text


@pytest.mark.parametrize(
    "user_input",
    [
        "Привет. Что ты умеешь?",
        "что умеешь",
        "какие у тебя инструменты",
        "help",
        "помощь",
    ],
)
def test_is_capabilities_query(user_input):
    assert is_capabilities_query(user_input) is True


def test_ask_agent_capabilities_shortcut_does_not_call_llm(monkeypatch, tmp_path):
    memory_file = tmp_path / "memory.json"
    monkeypatch.setattr("agent.agent.add_memory_entry", lambda **kwargs: None)
    monkeypatch.setattr(
        "agent.memory.DEFAULT_MEMORY_FILE",
        memory_file,
    )

    def fail_if_called(*_args, **_kwargs):
        raise AssertionError("LLM agent must not be called for capabilities query")

    monkeypatch.setattr("agent.agent.build_agent", fail_if_called)

    response = ask_agent("Привет. Что ты умеешь?")

    assert "Я локальный AI-агент с 11 инструментами" in response
    assert "Проверять курс криптовалют" in response
    assert "Получать курсы обычных валют" in response
    assert "Конвертировать единицы измерения" in response
