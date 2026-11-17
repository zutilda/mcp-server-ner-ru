"""Извлечение персональных данных по российскому законодательству.

Модуль покрывает идентификаторы, которые проверяются детерминированно:
паспорт РФ, ИНН, СНИЛС, полис ОМС, банковскую карту. Дополнительно — дату
рождения и адрес, которые распознаются по контекстным шаблонам и поэтому
помечаются пониженной достоверностью.

Каждый числовой идентификатор проверяется по контрольной сумме: без этого
любая последовательность цифр подходила бы под шаблон и обезличивание
портило бы обычный текст.
"""

from __future__ import annotations

import re

from .checksums import valid_card, valid_inn, valid_oms, valid_snils
from .models import Entity

#: Окно слева от совпадения, в котором ищется контекстное слово.
CONTEXT_WINDOW = 40

PASSPORT_RE = re.compile(
    r"""
    (?<![\d])
    \d{2}\s?\d{2}          # серия, иногда через пробел
    [\s\-]*
    \d{6}                  # номер
    (?![\d])
    """,
    re.VERBOSE,
)

INN_RE = re.compile(r"(?<![\d])\d{10}(?:\d{2})?(?![\d])")

SNILS_RE = re.compile(
    r"""
    (?<![\d])
    \d{3}[\s\-]?\d{3}[\s\-]?\d{3}[\s\-]?\d{2}
    (?![\d])
    """,
    re.VERBOSE,
)

CARD_RE = re.compile(
    r"""
    (?<![\d])
    (?:\d{4}[\s\-]?){3}\d{1,7}
    (?![\d])
    """,
    re.VERBOSE,
)

DATE_RE = re.compile(
    r"""
    (?<![\d])
    (?:
        \d{2}[.\-/]\d{2}[.\-/]\d{4}
        |
        \d{1,2}\s+
        (?:января|февраля|марта|апреля|мая|июня|июля|августа|сентября|октября|ноября|декабря)
        \s+\d{4}
    )
    (?![\d])
    """,
    re.VERBOSE | re.IGNORECASE,
)

ADDRESS_RE = re.compile(
    r"""
    (?<![\w])
    (?:
        (?:г\.|город)\s*[А-ЯЁ][а-яё\-]+
        |
        (?:ул\.|улица)\s*[А-ЯЁ][а-яё\-]+
        |
        (?:пр-т|просп\.|проспект)\s*[А-ЯЁ][а-яё\-]+
    )
    (?:[^.;!?\n]{0,80}?
        (?:д\.|дом)\s*\d+[А-Яа-я]?
        (?:[^.;!?\n]{0,40}?(?:кв\.|квартира)\s*\d+)?
    )?
    """,
    re.VERBOSE,
)

PASSPORT_CONTEXT_RE = re.compile(r"паспорт|серия|выдан", re.IGNORECASE)
BIRTH_CONTEXT_RE = re.compile(
    r"родил|рождения|дата\s+рож|г\.\s?р\.|род\.", re.IGNORECASE
)
OMS_CONTEXT_RE = re.compile(r"полис", re.IGNORECASE)
CARD_CONTEXT_RE = re.compile(r"карт|card", re.IGNORECASE)


def _context(text: str, start: int) -> str:
    """Вернуть фрагмент текста перед совпадением для проверки контекста."""
    return text[max(0, start - CONTEXT_WINDOW) : start]


def _digits(value: str) -> str:
    return "".join(char for char in value if char.isdigit())


def _is_phone_like(digits: str) -> bool:
    """Отсечь 11-значные номера, похожие на телефон (7/8 + 10 цифр)."""
    return len(digits) == 11 and digits[0] in {"7", "8"}


def find_passports(text: str) -> list[Entity]:
    """Найти серию и номер паспорта РФ.

    Совпадение без слова «паспорт», «серия» или «выдан» рядом отбрасывается:
    10 цифр подряд слишком часто оказываются телефоном или счётом, чтобы
    считать их паспортом без подтверждающего контекста.
    """
    found: list[Entity] = []
    for match in PASSPORT_RE.finditer(text):
        raw = match.group(0)
        digits = _digits(raw)
        if len(digits) != 10 or _is_phone_like(digits):
            continue
        if not PASSPORT_CONTEXT_RE.search(_context(text, match.start())):
            continue
        found.append(
            Entity(
                text=raw,
                normal_form=digits,
                category="PASSPORT",
                start_char=match.start(),
                end_char=match.end(),
            )
        )
    return found


def find_inn(text: str) -> list[Entity]:
    """Найти ИНН из 10 или 12 цифр с корректной контрольной суммой."""
    found: list[Entity] = []
    for match in INN_RE.finditer(text):
        raw = match.group(0)
        if _is_phone_like(raw) or not valid_inn(raw):
            continue
        found.append(
            Entity(
                text=raw,
                normal_form=raw,
                category="INN",
                start_char=match.start(),
                end_char=match.end(),
            )
        )
    return found


def find_snils(text: str) -> list[Entity]:
    """Найти СНИЛС с корректной контрольной суммой."""
    found: list[Entity] = []
    for match in SNILS_RE.finditer(text):
        raw = match.group(0)
        digits = _digits(raw)
        if len(digits) != 11 or not valid_snils(digits):
            continue
        found.append(
            Entity(
                text=raw,
                normal_form=digits,
                category="SNILS",
                start_char=match.start(),
                end_char=match.end(),
            )
        )
    return found


def find_cards(text: str) -> list[Entity]:
    """Найти номера карт и полисов ОМС.

    Оба типа — 16 цифр с контрольной суммой Луна, поэтому тип определяется по
    контексту: слово «полис» даёт ОМС, «карта» — банковскую карту. Без
    контекста выбирается карта, так как это более частый случай.
    """
    found: list[Entity] = []
    for match in CARD_RE.finditer(text):
        raw = match.group(0)
        digits = _digits(raw)
        if not valid_card(digits):
            continue
        context = _context(text, match.start())
        if OMS_CONTEXT_RE.search(context) and len(digits) == 16 and valid_oms(digits):
            category = "OMS"
        elif CARD_CONTEXT_RE.search(context) or len(digits) != 16:
            category = "CARD"
        else:
            category = "CARD"
        found.append(
            Entity(
                text=raw,
                normal_form=digits,
                category=category,
                start_char=match.start(),
                end_char=match.end(),
            )
        )
    return found


def find_birthdates(text: str) -> list[Entity]:
    """Найти даты рождения по контексту «родился», «дата рождения», «г.р.»."""
    found: list[Entity] = []
    for match in DATE_RE.finditer(text):
        if not BIRTH_CONTEXT_RE.search(_context(text, match.start())):
            continue
        found.append(
            Entity(
                text=match.group(0),
                normal_form=match.group(0),
                category="BIRTHDATE",
                start_char=match.start(),
                end_char=match.end(),
                confidence=0.9,
            )
        )
    return found


#: Разделители между частями одного адреса: запятая, пробелы, перевод строки.
_ADDRESS_GAP_RE = re.compile(r"^[\s,]{0,4}$")


def find_addresses(text: str) -> list[Entity]:
    """Найти почтовые адреса по ключевым словам города, улицы и дома.

    Город и улица с домом часто идут через запятую как один адрес, поэтому
    соседние совпадения, разделённые только пробелами и запятыми, склеиваются
    в одну сущность — иначе обезличивание заменило бы части адреса по
    отдельности и разрушило его структуру.
    """
    matches = list(ADDRESS_RE.finditer(text))
    if not matches:
        return []

    merged: list[tuple[int, int]] = []
    for match in matches:
        if merged and _ADDRESS_GAP_RE.match(text[merged[-1][1] : match.start()]):
            merged[-1] = (merged[-1][0], match.end())
        else:
            merged.append((match.start(), match.end()))

    return [
        Entity(
            text=text[start:end],
            normal_form=text[start:end],
            category="ADDRESS",
            start_char=start,
            end_char=end,
            confidence=0.8,
        )
        for start, end in merged
    ]


def find_pii(text: str) -> list[Entity]:
    """Найти все поддерживаемые персональные данные."""
    return (
        find_passports(text)
        + find_inn(text)
        + find_snils(text)
        + find_cards(text)
        + find_birthdates(text)
        + find_addresses(text)
    )
