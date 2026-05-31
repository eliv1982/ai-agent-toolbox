"""Tests for safe calculator tool."""

import pytest

from agent.tools import calculator_impl


def test_calculator_basic_operations():
    assert calculator_impl("2 + 3")["result"] == 5
    assert calculator_impl("10 - 4")["result"] == 6
    assert calculator_impl("6 * 7")["result"] == 42
    assert calculator_impl("20 / 4")["result"] == 5


def test_calculator_power_and_parentheses():
    assert calculator_impl("2 ** 3")["result"] == 8
    assert calculator_impl("(12500 * 0.2) + 390")["result"] == 2890


def test_calculator_rejects_unsafe_expression():
    result = calculator_impl("__import__('os').system('echo hi')")
    assert "error" in result


def test_calculator_division_by_zero():
    result = calculator_impl("10 / 0")
    assert "error" in result
