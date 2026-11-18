"""Извлечение именованных сущностей нейросетевой моделью Natasha.

Модуль отвечает только за персоны, локации и организации. Контактные данные
и персональные идентификаторы извлекаются детерминированно в соседних
модулях, поэтому здесь их нет.

Пайплайн повторяет рекомендованный порядок Natasha: сегментация, морфология,
синтаксис, NER и нормализация. Синтаксический разбор обязателен: без него
``span.normalize`` приводит названия организаций к косвенному падежу
(«Министерство иностранные дела» вместо «Министерство иностранных дел»).

Модели инициализируются один раз при импорте модуля. Повторная инициализация
в обработчике инструмента стоила бы около секунды на каждый запрос.
"""

from __future__ import annotations

from natasha import (
    Doc,
    MorphVocab,
    NewsEmbedding,
    NewsMorphTagger,
    NewsNERTagger,
    NewsSyntaxParser,
    Segmenter,
)

from .models import Entity

#: Достоверность сущностей, найденных статистической моделью.
#: Модель не отдаёт вероятность, поэтому значение фиксированное и ниже, чем
#: у детерминированных совпадений регулярных выражений.
NER_CONFIDENCE = 0.9

#: Соответствие типов Natasha категориям протокола.
_CATEGORY_MAP: dict[str, str] = {
    "PER": "PER",
    "LOC": "LOC",
    "ORG": "ORG",
}

_SEGMENTER = Segmenter()
_MORPH_VOCAB = MorphVocab()
_EMBEDDING = NewsEmbedding()
_MORPH_TAGGER = NewsMorphTagger(_EMBEDDING)
_NER_TAGGER = NewsNERTagger(_EMBEDDING)
_SYNTAX_PARSER = NewsSyntaxParser(_EMBEDDING)


def extract_named_entities(text: str) -> list[Entity]:
    """Найти персоны, локации и организации в русском тексте.

    Возвращает сущности с нормальной формой и позициями в исходной строке.
    Пустой или пробельный текст даёт пустой список без загрузки моделей.
    """
    if not text.strip():
        return []

    doc = Doc(text)
    doc.segment(_SEGMENTER)
    doc.tag_morph(_MORPH_TAGGER)
    doc.parse_syntax(_SYNTAX_PARSER)
    doc.tag_ner(_NER_TAGGER)

    found: list[Entity] = []
    for span in doc.spans:
        category = _CATEGORY_MAP.get(span.type)
        if category is None:
            continue
        span.normalize(_MORPH_VOCAB)
        found.append(
            Entity(
                text=span.text,
                normal_form=span.normal or span.text,
                category=category,  # type: ignore[arg-type]
                start_char=span.start,
                end_char=span.stop,
                confidence=NER_CONFIDENCE,
            )
        )
    return found
