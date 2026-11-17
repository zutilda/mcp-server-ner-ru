"""Pydantic-схемы данных сервера.

Схемы описывают публичный контракт инструментов: разметку сущностей,
результат обезличивания и результат обратной подстановки. Доменная логика
работает с этими моделями, MCP-адаптер только сериализует их.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

EntityCategory = Literal[
    "PER",
    "LOC",
    "ORG",
    "PHONE",
    "EMAIL",
    "PASSPORT",
    "INN",
    "SNILS",
    "OMS",
    "CARD",
    "ADDRESS",
    "BIRTHDATE",
]

#: Категории, которые относятся к персональным данным.
PII_CATEGORIES: frozenset[str] = frozenset(
    {
        "PHONE",
        "EMAIL",
        "PASSPORT",
        "INN",
        "SNILS",
        "OMS",
        "CARD",
        "ADDRESS",
        "BIRTHDATE",
    }
)


class Entity(BaseModel):
    """Найденная сущность с позицией в исходном тексте."""

    text: str = Field(description="Исходное упоминание в тексте")
    normal_form: str = Field(description="Нормальная форма или нормализованное значение")
    category: EntityCategory = Field(description="Тип сущности")
    start_char: int = Field(ge=0, description="Индекс первого символа включительно")
    end_char: int = Field(
        ge=0,
        description="Индекс после последнего символа, как в срезах Python",
    )
    confidence: float = Field(
        default=1.0,
        ge=0.0,
        le=1.0,
        description="Достоверность: 1.0 для проверенных регуляркой, ниже для эвристик",
    )


class ExtractResponse(BaseModel):
    """Результат извлечения сущностей."""

    total_found: int = Field(ge=0, description="Количество найденных сущностей")
    entities: list[Entity] = Field(default_factory=list)


class MappingEntry(BaseModel):
    """Соответствие плейсхолдера исходному значению."""

    placeholder: str
    value: str
    category: EntityCategory


class RedactResponse(BaseModel):
    """Результат обезличивания текста."""

    redacted_text: str = Field(description="Текст с заменой сущностей на плейсхолдеры")
    mapping: list[MappingEntry] = Field(
        default_factory=list,
        description="Карта соответствий; не должна попадать в контекст языковой модели",
    )
    total_replaced: int = Field(ge=0)


class RestoreResponse(BaseModel):
    """Результат обратной подстановки плейсхолдеров."""

    restored_text: str
    total_replaced: int = Field(ge=0)
    missing: list[str] = Field(
        default_factory=list,
        description="Плейсхолдеры из карты, которых не оказалось в тексте",
    )
    unknown: list[str] = Field(
        default_factory=list,
        description="Маркеры в тексте, отсутствующие в карте",
    )
