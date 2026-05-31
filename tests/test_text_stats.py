"""Tests for text_stats tool."""

import pytest

from agent.tools import text_stats_impl


def test_text_stats_analyze_text():
    text = "Hello world\nSecond line"
    result = text_stats_impl("analyze_text", text=text)
    assert result["characters"] == len(text)
    assert result["words"] == 4
    assert result["lines"] == 2
    assert result["reading_time_minutes"] > 0


def test_text_stats_analyze_file(tmp_path, monkeypatch):
    files_dir = tmp_path / "files"
    files_dir.mkdir()
    sample = files_dir / "sample.txt"
    sample.write_text("one two three\nfour\nfive", encoding="utf-8")
    monkeypatch.setattr("agent.tools.FILES_DIR", files_dir)

    result = text_stats_impl("analyze_file", filename="sample.txt")
    assert "error" not in result
    assert result["characters"] > 0
    assert result["words"] > 0
    assert result["lines"] > 0
    assert result["words"] == 5
    assert result["lines"] == 3


def test_text_stats_analyze_file_multiline_content(tmp_path, monkeypatch):
    files_dir = tmp_path / "data" / "files"
    files_dir.mkdir(parents=True)
    demo = files_dir / "demo_summary.txt"
    demo.write_text(
        "Тезис 1: AI-агент использует tools.\n"
        "Тезис 2: Память сохраняется локально.\n"
        "Тезис 3: Файлы только в sandbox.\n",
        encoding="utf-8",
    )
    monkeypatch.setattr("agent.tools.FILES_DIR", files_dir)

    result = text_stats_impl("analyze_file", filename="demo_summary.txt")
    assert "error" not in result
    assert result["characters"] > 0
    assert result["words"] > 0
    assert result["lines"] >= 3


def test_text_stats_empty_text_returns_error():
    result = text_stats_impl("analyze_text", text="")
    assert "error" in result
    assert "непустой text" in result["error"]


def test_text_stats_whitespace_text_returns_error():
    result = text_stats_impl("analyze_text", text="   \n\t  ")
    assert "error" in result


def test_text_stats_missing_file(tmp_path, monkeypatch):
    monkeypatch.setattr("agent.tools.FILES_DIR", tmp_path)
    result = text_stats_impl("analyze_file", filename="missing.txt")
    assert "error" in result
