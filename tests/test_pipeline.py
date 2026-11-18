"""Тесты объединения результатов экстракторов."""

from __future__ import annotations

from ner_mcp.models import Entity
from ner_mcp.pipeline import extract_entities, merge_entities


def make(
    text: str,
    category: str,
    start: int,
    end: int,
    confidence: float = 1.0,
) -> Entity:
    return Entity(
        text=text,
        normal_form=text,
        category=category,  # type: ignore[arg-type]
        start_char=start,
        end_char=end,
        confidence=confidence,
    )


class TestMergeEntities:
    def test_keeps_non_overlapping(self) -> None:
        left = make("Иван", "PER", 0, 4)
        right = make("+79991234567", "PHONE", 10, 22)
        merged = merge_entities([left, right])
        assert [entity.text for entity in merged] == ["Иван", "+79991234567"]

    def test_prefers_regex_over_model(self) -> None:
        statistical = make("Москва", "LOC", 0, 6, confidence=0.9)
        deterministic = make("Москва", "ADDRESS", 0, 6)
        merged = merge_entities([statistical, deterministic])
        assert len(merged) == 1
        assert merged[0].category == "ADDRESS"

    def test_prefers_longer_span_within_same_priority(self) -> None:
        short = make("ул. Ленина", "ADDRESS", 0, 10)
        long = make("ул. Ленина, д. 5", "ADDRESS", 0, 18)
        merged = merge_entities([short, long])
        assert len(merged) == 1
        assert merged[0].text == "ул. Ленина, д. 5"

    def test_keeps_adjacent_entities(self) -> None:
        left = make("Иван", "PER", 0, 4)
        right = make("Петров", "PER", 5, 11)
        merged = merge_entities([left, right])
        assert len(merged) == 2

    def test_sorts_by_position(self) -> None:
        later = make("Москва", "LOC", 20, 26)
        earlier = make("Иван", "PER", 0, 4)
        merged = merge_entities([later, earlier])
        assert [entity.text for entity in merged] == ["Иван", "Москва"]


class TestExtractEntities:
    def test_combines_sources(self) -> None:
        text = "Иван Петров, телефон +7 (999) 123-45-67, почта ivan@example.ru."
        response = extract_entities(text)
        found = {entity.category for entity in response.entities}
        assert "PER" in found
        assert "PHONE" in found
        assert "EMAIL" in found

    def test_total_matches_list(self) -> None:
        text = "Иван Петров, почта ivan@example.ru."
        response = extract_entities(text)
        assert response.total_found == len(response.entities)

    def test_positions_point_to_source_text(self) -> None:
        text = "Иван Петров, почта ivan@example.ru."
        response = extract_entities(text)
        for entity in response.entities:
            assert text[entity.start_char : entity.end_char] == entity.text

    def test_no_duplicate_phones(self) -> None:
        text = "Звоните: +7 (999) 123-45-67."
        response = extract_entities(text)
        phones = [entity for entity in response.entities if entity.category == "PHONE"]
        assert len(phones) == 1

    def test_empty_text(self) -> None:
        response = extract_entities("")
        assert response.total_found == 0
        assert response.entities == []

    def test_entities_sorted(self) -> None:
        text = "Иван Петров, телефон +7 (999) 123-45-67, почта ivan@example.ru."
        response = extract_entities(text)
        starts = [entity.start_char for entity in response.entities]
        assert starts == sorted(starts)
