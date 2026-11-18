"""Обратимое обезличивание текста плейсхолдерами.

Модуль заменяет найденные сущности маркерами на латинице и возвращает карту
соответствий. Карта остаётся у вызывающей стороны: если она не уходит во
внешнюю модель, ответ можно восстановить в исходном виде.

Плейсхолдер собирается из префикса категории и порядкового номера:
``NAME_1``, ``PASSPORT_1``, ``INN_1``. Нумерация отдельная для каждой
категории, поэтому по маркеру сразу видно, что именно было скрыто.
"""

from __future__ import annotations

import re

from .models import Entity, MappingEntry, RedactResponse, RestoreResponse
from .pipeline import extract_entities

#: Префикс плейсхолдера для каждой поддерживаемой категории.
_PLACEHOLDER_PREFIX: dict[str, str] = {
    "PER": "NAME",
    "LOC": "LOCATION",
    "ORG": "ORG",
    "PHONE": "PHONE",
    "EMAIL": "EMAIL",
    "PASSPORT": "PASSPORT",
    "INN": "INN",
    "SNILS": "SNILS",
    "OMS": "OMS",
    "CARD": "CARD",
    "ADDRESS": "ADDRESS",
    "BIRTHDATE": "BIRTHDATE",
}

#: Маркер плейсхолдера в тексте, например ``NAME_1``.
PLACEHOLDER_RE = re.compile(r"(?<![A-Z_])[A-Z][A-Z_]*_\d+(?![A-Z_])")


def redact_text(text: str, entities: list[Entity] | None = None) -> RedactResponse:
    """Заменить сущности плейсхолдерами и вернуть карту соответствий.

    Одинаковые сущности получают один и тот же маркер: «Иван Петров» и
    «Ивану Петрову» — это одно лицо, поэтому обезличивание даёт один
    ``NAME_1``, а не два разных. Ключом служит нормальная форма, а не
    поверхностная: иначе модель увидела бы в тексте двух разных людей.
    Сущности передаются слева направо, поэтому замена выполняется с конца —
    иначе сдвинулись бы позиции ещё не обработанных совпадений.

    Обратная подстановка возвращает форму первого упоминания, поэтому
    дословное восстановление гарантировано только для текста, где сущность
    встречается в одной форме.
    """
    if entities is None:
        entities = extract_entities(text).entities

    counters: dict[str, int] = {}
    placeholders: dict[tuple[str, str], str] = {}
    mapping: list[MappingEntry] = []
    replacements: list[tuple[int, int, str]] = []

    for entity in entities:
        key = (entity.category, entity.normal_form or entity.text)
        placeholder = placeholders.get(key)
        if placeholder is None:
            prefix = _PLACEHOLDER_PREFIX[entity.category]
            counters[prefix] = counters.get(prefix, 0) + 1
            placeholder = f"{prefix}_{counters[prefix]}"
            placeholders[key] = placeholder
            mapping.append(
                MappingEntry(
                    placeholder=placeholder,
                    value=entity.text,
                    category=entity.category,
                )
            )
        replacements.append((entity.start_char, entity.end_char, placeholder))

    redacted = text
    for start, end, placeholder in sorted(
        replacements, key=lambda item: item[0], reverse=True
    ):
        redacted = redacted[:start] + placeholder + redacted[end:]

    return RedactResponse(
        redacted_text=redacted,
        mapping=mapping,
        total_replaced=len(replacements),
    )


def restore_text(text: str, mapping: list[MappingEntry]) -> RestoreResponse:
    """Вернуть исходные значения на места плейсхолдеров.

    В ответе отдельно перечисляются плейсхолдеры из карты, которых нет
    в тексте, и маркеры в тексте, которых нет в карте. Так вызывающая
    сторона видит, что модель выбросила или придумала.
    """
    restored = text
    total = 0
    for entry in mapping:
        count = restored.count(entry.placeholder)
        if count:
            restored = restored.replace(entry.placeholder, entry.value)
            total += count

    known = {entry.placeholder for entry in mapping}
    missing = [
        entry.placeholder for entry in mapping if entry.placeholder not in text
    ]
    unknown = sorted(
        {match.group(0) for match in PLACEHOLDER_RE.finditer(restored)} - known
    )

    return RestoreResponse(
        restored_text=restored,
        total_replaced=total,
        missing=missing,
        unknown=unknown,
    )
