"""Тесты обратимого обезличивания текста."""

from __future__ import annotations

from ner_mcp.models import MappingEntry
from ner_mcp.redaction import PLACEHOLDER_RE, redact_text, restore_text


class TestRedact:
    def test_replaces_person_with_latin_placeholder(self) -> None:
        response = redact_text("Клиент Иван Петров оформил заказ.")
        assert "NAME_1" in response.redacted_text
        assert "Иван" not in response.redacted_text

    def test_placeholder_is_latin(self) -> None:
        response = redact_text("Позвоните Ивану Петрову.")
        markers = PLACEHOLDER_RE.findall(response.redacted_text)
        assert markers
        assert all(marker.isascii() for marker in markers)

    def test_replaces_phone(self) -> None:
        response = redact_text("Телефон: +7 (999) 123-45-67.")
        assert "PHONE_1" in response.redacted_text
        assert "123-45-67" not in response.redacted_text

    def test_replaces_passport_with_context(self) -> None:
        response = redact_text("Паспорт 45 06 123456 выдан отделом.")
        assert "PASSPORT_1" in response.redacted_text
        assert "123456" not in response.redacted_text

    def test_same_entity_gets_same_placeholder(self) -> None:
        response = redact_text("Иван Петров написал Ивану Петрову.")
        assert response.redacted_text == "NAME_1 написал NAME_1."
        assert response.total_replaced == 2
        assert len(response.mapping) == 1
        assert response.mapping[0].value == "Иван Петров"

    def test_different_entities_get_different_placeholders(self) -> None:
        response = redact_text("Иван Петров и Пётр Сидоров пришли.")
        placeholders = {entry.placeholder for entry in response.mapping}
        assert placeholders == {"NAME_1", "NAME_2"}

    def test_mapping_holds_original_values(self) -> None:
        response = redact_text("Клиент Иван Петров оформил заказ.")
        values = [entry.value for entry in response.mapping]
        assert "Иван Петров" in values

    def test_numbering_is_per_category(self) -> None:
        response = redact_text("Иван Петров, почта ivan@example.ru.")
        placeholders = {entry.placeholder for entry in response.mapping}
        assert "NAME_1" in placeholders
        assert "EMAIL_1" in placeholders

    def test_empty_text(self) -> None:
        response = redact_text("")
        assert response.redacted_text == ""
        assert response.mapping == []
        assert response.total_replaced == 0


class TestRestore:
    def test_roundtrip(self) -> None:
        source = "Клиент Иван Петров, телефон +7 (999) 123-45-67."
        redacted = redact_text(source)
        restored = restore_text(redacted.redacted_text, redacted.mapping)
        assert restored.restored_text == source
        assert restored.missing == []
        assert restored.unknown == []

    def test_reports_missing_placeholder(self) -> None:
        mapping = [
            MappingEntry(placeholder="NAME_1", value="Иван Петров", category="PER"),
            MappingEntry(placeholder="PHONE_1", value="+79991234567", category="PHONE"),
        ]
        response = restore_text("Клиент NAME_1 оформил заказ.", mapping)
        assert response.missing == ["PHONE_1"]

    def test_reports_unknown_marker(self) -> None:
        mapping = [
            MappingEntry(placeholder="NAME_1", value="Иван Петров", category="PER")
        ]
        response = restore_text("Клиент NAME_1 из ORG_7.", mapping)
        assert response.unknown == ["ORG_7"]

    def test_counts_every_occurrence(self) -> None:
        mapping = [
            MappingEntry(placeholder="NAME_1", value="Иван Петров", category="PER")
        ]
        response = restore_text("NAME_1 и снова NAME_1.", mapping)
        assert response.total_replaced == 2
        assert response.restored_text == "Иван Петров и снова Иван Петров."

    def test_empty_mapping_keeps_text(self) -> None:
        response = restore_text("Текст без маркеров.", [])
        assert response.restored_text == "Текст без маркеров."
        assert response.total_replaced == 0
