"""Извлечение контактной информации регулярными выражениями.

Модуль находит телефоны и адреса электронной почты. Телефоны приводятся
к каноническому виду ``+7XXXXXXXXXX``, почта — к нижнему регистру.
"""

from __future__ import annotations

import re

from .models import Entity

#: Телефон в международном или местном формате: +7/8, 10 цифр после кода страны.
PHONE_RE = re.compile(
    r"""
    (?<![\d+])
    (?:
        (?:\+7|8)            # код страны
        [\s\-()]*            # разделители
        \d{3}                # код оператора
        [\s\-()]*            # разделители
        \d{3}
        [\s\-]*              # разделители
        \d{2}
        [\s\-]*
        \d{2}
    )
    (?![\d])
    """,
    re.VERBOSE,
)

EMAIL_RE = re.compile(
    r"""
    (?<![\w.+-])
    [A-Za-z0-9._%+\-]+
    @
    [A-Za-z0-9.\-]+
    \.
    [A-Za-z]{2,}
    (?![\w\-])
    """,
    re.VERBOSE,
)

def normalize_phone(raw: str) -> str:
    """Привести телефон к виду ``+7XXXXXXXXXX``.

    Поддерживаются варианты с ``+7``, ``8``, скобками, пробелами и дефисами.
    """
    digits = "".join(char for char in raw if char.isdigit())
    if len(digits) == 11 and digits[0] in {"7", "8"}:
        return "+7" + digits[1:]
    if len(digits) == 10:
        return "+7" + digits
    return raw


def find_phones(text: str) -> list[Entity]:
    """Найти телефоны и вернуть их с нормализованным значением."""
    found: list[Entity] = []
    for match in PHONE_RE.finditer(text):
        raw = match.group(0)
        found.append(
            Entity(
                text=raw,
                normal_form=normalize_phone(raw),
                category="PHONE",
                start_char=match.start(),
                end_char=match.end(),
            )
        )
    return found


def find_emails(text: str) -> list[Entity]:
    """Найти адреса электронной почты."""
    return [
        Entity(
            text=match.group(0),
            normal_form=match.group(0).lower(),
            category="EMAIL",
            start_char=match.start(),
            end_char=match.end(),
        )
        for match in EMAIL_RE.finditer(text)
    ]


def find_contacts(text: str) -> list[Entity]:
    """Найти все поддерживаемые контактные данные."""
    return find_phones(text) + find_emails(text)
