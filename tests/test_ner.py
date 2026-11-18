"""Тесты нейросетевого извлечения именованных сущностей."""

from __future__ import annotations

from ner_mcp.ner import extract_named_entities


def categories(text: str) -> set[str]:
    return {entity.category for entity in extract_named_entities(text)}


class TestPersons:
    def test_finds_person(self) -> None:
        found = extract_named_entities("Иван Петров пришёл на встречу.")
        persons = [entity for entity in found if entity.category == "PER"]
        assert persons, "персона не найдена"
        assert "Иван" in persons[0].normal_form

    def test_normalizes_inflected_person(self) -> None:
        found = extract_named_entities("Письмо от Ивана Петрова.")
        persons = [entity for entity in found if entity.category == "PER"]
        assert persons
        assert persons[0].normal_form == "Иван Петров"


class TestLocations:
    def test_finds_location(self) -> None:
        found = extract_named_entities("Он живёт в Москве.")
        locations = [entity for entity in found if entity.category == "LOC"]
        assert locations
        assert locations[0].normal_form == "Москва"


class TestOrganizations:
    def test_finds_organization(self) -> None:
        found = extract_named_entities("Сотрудник Газпрома сообщил новость.")
        organizations = [entity for entity in found if entity.category == "ORG"]
        assert organizations

    def test_normalizes_organization_with_syntax(self) -> None:
        found = extract_named_entities(
            "Документ подписан Министерством иностранных дел России."
        )
        organizations = [entity for entity in found if entity.category == "ORG"]
        assert organizations
        assert "иностранные дела" not in organizations[0].normal_form
        assert "иностранных дел" in organizations[0].normal_form


class TestPositions:
    def test_end_char_is_exclusive(self) -> None:
        text = "Иван Петров пришёл."
        found = extract_named_entities(text)
        assert found
        entity = found[0]
        assert text[entity.start_char : entity.end_char] == entity.text

    def test_confidence_below_one(self) -> None:
        found = extract_named_entities("Иван Петров пришёл.")
        assert found
        assert all(entity.confidence < 1.0 for entity in found)


class TestEmpty:
    def test_empty_text(self) -> None:
        assert extract_named_entities("") == []

    def test_whitespace_only(self) -> None:
        assert extract_named_entities("   \n\t ") == []

    def test_text_without_entities(self) -> None:
        assert categories("сегодня хорошая погода") == set()
