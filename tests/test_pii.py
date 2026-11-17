"""Тесты извлечения персональных данных."""

from __future__ import annotations

import pytest

from ner_mcp.pii import (
    find_addresses,
    find_birthdates,
    find_cards,
    find_inn,
    find_passports,
    find_snils,
)


class TestPassport:
    def test_finds_passport_with_context(self) -> None:
        text = "Паспорт 4512 345678 выдан ОВД"
        found = find_passports(text)
        assert len(found) == 1
        assert found[0].normal_form == "4512345678"
        assert found[0].confidence == 1.0

    def test_requires_context(self) -> None:
        # Без слова «паспорт» рядом 10 цифр неотличимы от телефона или счёта,
        # поэтому совпадение отбрасывается, а не помечается низкой достоверностью.
        assert find_passports("Номер 4512 345678 в базе") == []

    def test_ignores_phone_like_sequence(self) -> None:
        assert find_passports("8 999 123 45 67") == []


class TestInn:
    def test_finds_valid_legal_entity_inn(self) -> None:
        found = find_inn("ИНН 7707083893")
        assert len(found) == 1
        assert found[0].category == "INN"

    def test_finds_valid_person_inn(self) -> None:
        found = find_inn("ИНН 500100732259")
        assert len(found) == 1

    def test_rejects_broken_checksum(self) -> None:
        assert find_inn("ИНН 7707083894") == []


class TestSnils:
    def test_finds_valid_snils_with_separators(self) -> None:
        found = find_snils("СНИЛС 112-233-445 95")
        assert len(found) == 1
        assert found[0].normal_form == "11223344595"

    def test_rejects_broken_checksum(self) -> None:
        assert find_snils("СНИЛС 112-233-445 96") == []


class TestCards:
    def test_finds_bank_card(self) -> None:
        found = find_cards("Карта 4111 1111 1111 1111")
        assert len(found) == 1
        assert found[0].category == "CARD"

    def test_finds_oms_policy_by_context(self) -> None:
        found = find_cards("Полис ОМС 4111111111111111")
        assert len(found) == 1
        assert found[0].category == "OMS"

    def test_rejects_broken_luhn(self) -> None:
        assert find_cards("Карта 4111 1111 1111 1112") == []


class TestBirthdate:
    def test_finds_birthdate_with_context(self) -> None:
        found = find_birthdates("Дата рождения: 12.03.1985")
        assert len(found) == 1
        assert found[0].text == "12.03.1985"

    def test_finds_textual_birthdate(self) -> None:
        found = find_birthdates("родился 12 марта 1985 года")
        assert len(found) == 1

    def test_ignores_date_without_context(self) -> None:
        assert find_birthdates("Встреча 12.03.1985") == []


class TestAddress:
    def test_finds_city_street_house(self) -> None:
        found = find_addresses("Адрес: г. Москва, ул. Ленина, д. 5, кв. 12")
        assert len(found) == 1
        assert "Москва" in found[0].text

    def test_finds_street_only(self) -> None:
        found = find_addresses("Живу на ул. Пушкина")
        assert len(found) == 1
