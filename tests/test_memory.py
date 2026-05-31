"""Tests for memory persistence."""

from pathlib import Path

import pytest

from agent.memory import add_memory_entry, clear_memory, load_memory, summarize_memory_for_prompt


@pytest.fixture
def memory_file(tmp_path) -> Path:
    return tmp_path / "memory.json"


def test_add_and_list_memory(memory_file):
    add_memory_entry("Hi", "Hello!", memory_file=memory_file)
    entries = load_memory(memory_file)
    assert len(entries) == 1
    assert entries[0]["user_message"] == "Hi"
    assert entries[0]["assistant_response"] == "Hello!"


def test_clear_memory(memory_file):
    add_memory_entry("One", "Two", memory_file=memory_file)
    clear_memory(memory_file)
    assert load_memory(memory_file) == []


def test_summarize_memory_for_prompt(memory_file):
    add_memory_entry("Question", "Answer", memory_file=memory_file)
    summary = summarize_memory_for_prompt(memory_file=memory_file)
    assert "Question" in summary
    assert "Answer" in summary
