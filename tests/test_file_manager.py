"""Tests for file_manager sandbox behavior."""

import pytest

from agent.tools import file_manager_impl


@pytest.fixture
def sandbox(tmp_path, monkeypatch):
    monkeypatch.setattr("agent.tools.FILES_DIR", tmp_path)
    return tmp_path


def test_file_manager_list_empty(sandbox):
    result = file_manager_impl("list")
    assert result["action"] == "list"
    assert result["files"] == []


def test_file_manager_write_read_append(sandbox):
    write_result = file_manager_impl("write", "notes.txt", "hello")
    assert write_result["status"] == "ok"

    read_result = file_manager_impl("read", "notes.txt")
    assert read_result["content"] == "hello"

    append_result = file_manager_impl("append", "notes.txt", " world")
    assert append_result["status"] == "ok"

    read_again = file_manager_impl("read", "notes.txt")
    assert read_again["content"] == "hello world"


def test_file_manager_blocks_path_traversal(sandbox):
    result = file_manager_impl("read", "../secret.txt")
    assert "error" in result


def test_file_manager_missing_file(sandbox):
    result = file_manager_impl("read", "missing.txt")
    assert "error" in result
