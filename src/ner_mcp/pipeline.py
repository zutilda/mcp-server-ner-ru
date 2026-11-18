"""Объединение результатов всех экстракторов в один ответ.

Три источника работают независимо: регулярные выражения для контактов,
регулярные выражения с проверкой контрольных сумм для персональных данных
и нейросетевая модель для персон, локаций и организаций. Их совпадения
пересекаются: телефон одновременно попадает в контакты и в ПДн, а организация
может быть частью адреса. Модуль разрешает пересечения детерминированно.

Правило приоритета: проверенное регуляркой важнее предсказания модели.
Внутри одного приоритета выигрывает более длинное совпадение — оно содержит
больше контекста и лучше подходит для обезличивания.
"""

from __future__ import annotations

from .contacts import find_contacts
from .models import Entity, ExtractResponse
from .ner import extract_named_entities
from .pii import find_pii

#: Категории, которые статистическая модель не выдаёт.
_STATISTICAL_CATEGORIES: frozenset[str] = frozenset({"PER", "LOC", "ORG"})


def _priority(entity: Entity) -> int:
    """Вернуть приоритет источника: 2 — регулярка, 1 — модель."""
    return 1 if entity.category in _STATISTICAL_CATEGORIES else 2


def _overlaps(left: Entity, right: Entity) -> bool:
    """Проверить, пересекаются ли позиции двух сущностей."""
    return left.start_char < right.end_char and right.start_char < left.end_char


def merge_entities(entities: list[Entity]) -> list[Entity]:
    """Убрать пересекающиеся сущности и отсортировать результат.

    Сортировка перед отбором идёт по убыванию приоритета и длины, поэтому
    из пересекающейся пары остаётся детерминированное и более полное
    совпадение. Итоговый список сортируется по позиции в тексте.
    """
    ordered = sorted(
        entities,
        key=lambda entity: (
            -_priority(entity),
            -(entity.end_char - entity.start_char),
            entity.start_char,
        ),
    )

    kept: list[Entity] = []
    for entity in ordered:
        if any(_overlaps(entity, accepted) for accepted in kept):
            continue
        kept.append(entity)

    return sorted(kept, key=lambda entity: (entity.start_char, entity.end_char))


def extract_entities(text: str) -> ExtractResponse:
    """Извлечь все поддерживаемые сущности из текста.

    Источники объединяются, пересечения разрешаются в пользу проверенных
    регуляркой совпадений. Пустой текст даёт пустой ответ.
    """
    candidates = find_contacts(text) + find_pii(text) + extract_named_entities(text)
    merged = merge_entities(candidates)
    return ExtractResponse(total_found=len(merged), entities=merged)
