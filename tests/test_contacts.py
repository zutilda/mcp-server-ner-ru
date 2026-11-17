"""Тесты извлечения контактных данных."""

from __future__ import annotations

import pytest

from ner_mcp.contacts import (
    find_contacts,
    find_emails,
    find_phones,
    normalize_phone,
)


class TestPhoneNormalization:
    @pytest.mark.parametrize(
        ("raw", "expected"),
        [
            ("8 (999) 123-45-67", "+79991234567"),
            ("+7 999 123 45 67", "+79991234567"),
            ("+7(999)123-45-67", "+79991234567"),
            ("8-999-123-45-67", "+79991234567"),
            ("89991234567", "+79991234567"),
            ("+79991234567", "+79991234567"),
        ],
    )
    def test_normalizes_to_canonical_form(self, raw: str, expected: str) -> None:
        assert normalize_phone(raw) == expected

    def test_returns_input_when_length_is_unexpected(self) -> None:
        assert normalize_phone("12345") == "12345"


class TestPhoneExtraction:
    def test_finds_phone_with_separators(self) -> None:
        text = "Звоните: 8 (999) 123-45-67, будни."
        found = find_phones(text)
        assert len(found) == 1
        assert found[0].normal_form == "+79991234567"
        assert text[found[0].start_char : found[0].end_char] == "8 (999) 123-45-67"

    def test_finds_phone_glued_to_word(self) -> None:
        found = find_phones("тел.+79991234567")
        assert len(found) == 1
        assert found[0].normal_form == "+79991234567"

    def test_ignores_short_numbers(self) -> None:
        assert find_phones("Заказ 12345 готов") == []

    def test_ignores_inn_like_sequences(self) -> None:
        assert find_phones("ИНН 7707083893") == []


class TestEmailExtraction:
    def test_finds_email(self) -> None:
        text = "Пишите на ivan.petrov@example.ru, пожалуйста"
        found = find_emails(text)
        assert len(found) == 1
        assert found[0].text == "ivan.petrov@example.ru"
        assert found[0].normal_form == "ivan.petrov@example.ru"
        assert text[found[0].start_char : found[0].end_char] == "ivan.petrov@example.ru"

    def test_lowercases_normal_form(self) -> None:
        found = find_emails("Ivan.Petrov@Example.RU")
        assert found[0].normal_form == "ivan.petrov@example.ru"

    def test_ignores_broken_email(self) -> None:
        assert find_emails("почта ivan@example") == []


class TestCombinedExtraction:
    def test_finds_all_contact_types(self) -> None:
        text = "Иван Петров, тел. 8 (999) 123-45-67, почта ivan@example.ru."
        categories = {entity.category for entity in find_contacts(text)}
        assert categories == {"PHONE", "EMAIL"}

    def test_entities_are_within_text_bounds(self) -> None:
        text = "Почта ivan@example.ru и телефон +79991234567"
        for entity in find_contacts(text):
            assert 0 <= entity.start_char < entity.end_char <= len(text)
