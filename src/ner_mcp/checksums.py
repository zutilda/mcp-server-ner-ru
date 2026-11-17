"""Контрольные суммы российских идентификаторов.

Все функции принимают строку в любом форматировании (с пробелами, дефисами,
скобками) и работают только с цифрами.

Реализованные алгоритмы:

* ИНН — 10 знаков (юрлицо) и 12 знаков (физлицо), веса из приказа ФНС.
* СНИЛС — 11 знаков, веса 9..1, частные случаи 100/101 -> 00.
* ОМС — 16 знаков, алгоритм Mod10 (ISO/HL7 27931:2009), он же Luhn.
* Банковская карта — Luhn, длина 12..19.
"""

from __future__ import annotations

INN10_WEIGHTS = (2, 4, 10, 3, 5, 9, 4, 6, 8)
INN12_WEIGHTS_FIRST = (7, 2, 4, 10, 3, 5, 9, 4, 6, 8)
INN12_WEIGHTS_SECOND = (3, 7, 2, 4, 10, 3, 5, 9, 4, 6, 8)


def digits_only(value: str) -> list[int]:
    """Return the decimal digits of ``value`` as integers."""
    return [int(char) for char in value if char.isdigit()]


def _weighted_sum(weights: tuple[int, ...], digits: list[int]) -> int:
    return sum(weight * digit for weight, digit in zip(weights, digits))


def valid_inn(value: str) -> bool:
    """Validate a Russian INN: 10 digits for a legal entity, 12 for a person."""
    digits = digits_only(value)

    if len(digits) == 10:
        checksum = _weighted_sum(INN10_WEIGHTS, digits[:9]) % 11 % 10
        return checksum == digits[9]

    if len(digits) == 12:
        first = _weighted_sum(INN12_WEIGHTS_FIRST, digits[:10]) % 11 % 10
        second = _weighted_sum(INN12_WEIGHTS_SECOND, digits[:11]) % 11 % 10
        return first == digits[10] and second == digits[11]

    return False


def valid_snils(value: str) -> bool:
    """Validate a SNILS number (11 digits, checksum is the last two digits)."""
    digits = digits_only(value)
    if len(digits) != 11:
        return False

    # Numbers up to 001-001-998 are not checked: the control rule does not apply.
    if digits[:9] <= [0, 0, 1, 0, 0, 1, 9, 9, 8]:
        return True

    total = sum(digit * (9 - index) for index, digit in enumerate(digits[:9]))

    if total < 100:
        checksum = total
    elif total in (100, 101):
        checksum = 0
    else:
        checksum = total % 101
        if checksum == 100:
            checksum = 0

    return checksum == digits[9] * 10 + digits[10]


def valid_luhn(value: str) -> bool:
    """Validate a number with the Luhn (Mod10) checksum."""
    digits = digits_only(value)
    if not digits:
        return False

    total = 0
    for index, digit in enumerate(reversed(digits)):
        if index % 2 == 1:
            digit *= 2
            if digit > 9:
                digit -= 9
        total += digit
    return total % 10 == 0


def valid_oms(value: str) -> bool:
    """Validate a 16-digit compulsory medical insurance policy number (Mod10)."""
    digits = digits_only(value)
    return len(digits) == 16 and valid_luhn(value)


def valid_card(value: str) -> bool:
    """Validate a bank card number: 12..19 digits and a correct Luhn checksum."""
    digits = digits_only(value)
    if not 12 <= len(digits) <= 19:
        return False
    return valid_luhn(value)
