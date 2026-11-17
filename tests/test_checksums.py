"""Тесты контрольных сумм на заведомо корректных и некорректных значениях."""

from __future__ import annotations

import pytest

from ner_mcp.checksums import (
    digits_only,
    valid_card,
    valid_inn,
    valid_luhn,
    valid_oms,
    valid_snils,
)


class TestDigitsOnly:
    def test_strips_formatting(self) -> None:
        assert digits_only("7707 083 893") == [7, 7, 0, 7, 0, 8, 3, 8, 9, 3]

    def test_empty(self) -> None:
        assert digits_only("") == []


class TestInn:
    @pytest.mark.parametrize(
        "value",
        [
            "7707083893",  # 10 digits, valid
            "500100732259",  # 12 digits, valid
            "500 100 732 259",  # same with spaces
        ],
    )
    def test_valid(self, value: str) -> None:
        assert valid_inn(value) is True

    @pytest.mark.parametrize("value", ["7707083894", "500100732258", "123", ""])
    def test_invalid(self, value: str) -> None:
        assert valid_inn(value) is False


class TestSnils:
    @pytest.mark.parametrize("value", ["112-233-445 95", "11223344595"])
    def test_valid(self, value: str) -> None:
        assert valid_snils(value) is True

    @pytest.mark.parametrize("value", ["112-233-445 94", "112233445", ""])
    def test_invalid(self, value: str) -> None:
        assert valid_snils(value) is False

    def test_small_numbers_are_not_checked(self) -> None:
        # Up to 001-001-998 the control rule does not apply.
        assert valid_snils("001-001-998 00") is True


class TestOms:
    def test_valid(self) -> None:
        assert valid_oms("6014359000000928") is True

    def test_wrong_length(self) -> None:
        assert valid_oms("601435900000092") is False

    def test_broken_checksum(self) -> None:
        assert valid_oms("6014359000000929") is False


class TestCard:
    @pytest.mark.parametrize("value", ["4111111111111111", "5555555555554444"])
    def test_valid(self, value: str) -> None:
        assert valid_card(value) is True

    def test_invalid_checksum(self) -> None:
        assert valid_card("4111111111111112") is False

    def test_too_short(self) -> None:
        assert valid_card("41111111111") is False

    def test_luhn_accepts_sixteen_digits(self) -> None:
        assert valid_luhn("6014359000000928") is True
