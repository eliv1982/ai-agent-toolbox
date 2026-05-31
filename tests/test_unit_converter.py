"""Tests for unit_converter tool."""

import pytest

from agent.tools import unit_converter_impl


@pytest.mark.parametrize(
    ("value", "conversion_type", "expected"),
    [
        (1, "km_to_miles", 0.621371),
        (1, "miles_to_km", 1.609344),
        (1, "kg_to_lb", 2.20462),
        (2.20462, "lb_to_kg", 1.0),
        (0, "c_to_f", 32),
        (32, "f_to_c", 0.0),
        (2.54, "cm_to_inches", 1.0),
        (1, "inches_to_cm", 2.54),
    ],
)
def test_unit_converter(value, conversion_type, expected):
    result = unit_converter_impl(value, conversion_type)
    assert abs(result["result"] - expected) < 0.01


def test_unit_converter_invalid_type():
    result = unit_converter_impl(10, "invalid_type")
    assert "error" in result
