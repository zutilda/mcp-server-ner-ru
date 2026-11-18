"""MCP-сервер: тонкий адаптер над доменной логикой.

Инструменты только сериализуют готовые модели, вся работа выполняется в
модулях пакета. Сервер не знает о правилах извлечения — это позволяет
тестировать доменную логику отдельно от протокола.

Транспорт — stdio. Дескриптор stdout зарезервирован под кадры JSON-RPC,
поэтому логирование направлено в stderr, а ``print()`` в коде запрещён.
"""

from __future__ import annotations

import json
import logging
import sys
from typing import get_args

from mcp.server.mcpserver import MCPServer

from .models import (
    PII_CATEGORIES,
    EntityCategory,
    ExtractResponse,
    MappingEntry,
    RedactResponse,
    RestoreResponse,
)
from .pipeline import extract_entities as _extract_entities
from .redaction import redact_text as _redact_text
from .redaction import restore_text as _restore_text

logging.basicConfig(
    level=logging.INFO,
    stream=sys.stderr,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
logger = logging.getLogger("ner_mcp")

mcp = MCPServer(
    name="ner-mcp",
    version="0.1.0",
    description=(
        "Локальный сервер извлечения именованных сущностей и персональных "
        "данных из русского текста с обратимым обезличиванием"
    ),
)


@mcp.tool(
    description=(
        "Извлечь из русского текста именованные сущности (персоны, локации, "
        "организации) и персональные данные (телефоны, почта, паспорт, ИНН, "
        "СНИЛС, полис ОМС, банковская карта, адрес, дата рождения)"
    )
)
def extract_entities(text: str) -> ExtractResponse:
    """Извлечь все поддерживаемые сущности с позициями в исходном тексте."""
    logger.info("extract_entities: получено %d символов", len(text))
    response = _extract_entities(text)
    logger.info("extract_entities: найдено %d сущностей", response.total_found)
    return response


@mcp.tool(
    description=(
        "Заменить найденные сущности плейсхолдерами вида NAME_1 и вернуть "
        "карту соответствий. Карту нельзя отправлять во внешнюю модель — "
        "по ней данные восстанавливаются"
    )
)
def redact_text(text: str) -> RedactResponse:
    """Обезличить текст и вернуть карту соответствий для обратной подстановки."""
    logger.info("redact_text: получено %d символов", len(text))
    response = _redact_text(text)
    logger.info("redact_text: заменено %d вхождений", response.total_replaced)
    return response


@mcp.tool(
    description=(
        "Вернуть исходные значения на места плейсхолдеров по карте "
        "соответствий. Сообщает о плейсхолдерах, потерянных моделью, и о "
        "неизвестных маркерах, которых нет в карте"
    )
)
def restore_text(text: str, mapping: list[MappingEntry]) -> RestoreResponse:
    """Выполнить обратную подстановку по карте соответствий."""
    logger.info("restore_text: получено %d символов и %d записей карты", len(text), len(mapping))
    response = _restore_text(text, mapping)
    logger.info("restore_text: восстановлено %d вхождений", response.total_replaced)
    return response


@mcp.resource(
    "taxonomy://entities/categories",
    name="taxonomy",
    description="Список поддерживаемых категорий и признак персональных данных",
    mime_type="application/json",
)
def taxonomy_categories() -> str:
    """Вернуть таксономию категорий в формате JSON."""
    payload = {
        "categories": list(get_args(EntityCategory)),
        "pii_categories": sorted(PII_CATEGORIES),
    }
    return json.dumps(payload, ensure_ascii=False, indent=2)


@mcp.prompt(
    description="Промпт для пересказа текста с предварительным обезличиванием"
)
def extract_and_summarize(source_text: str) -> str:
    """Собрать промпт: обезличить текст, пересказать, вернуть подстановку."""
    redacted = _redact_text(source_text)
    return (
        "Ниже обезличенный текст. Плейсхолдеры вида NAME_1, PHONE_1, "
        "PASSPORT_1 — это удалённые персональные данные, их не нужно "
        "восстанавливать или додумывать.\n\n"
        f"{redacted.redacted_text}\n\n"
        "Перескажи текст, сохранив смысл и структуру. Используй плейсхолдеры "
        "в ответе ровно в том виде, в котором они даны."
    )


def main() -> None:
    """Запустить сервер по транспорту stdio."""
    logger.info("Запуск ner-mcp по транспорту stdio")
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
