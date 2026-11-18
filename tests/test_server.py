"""Тесты регистрации примитивов MCP-сервера."""

from __future__ import annotations

import asyncio
import json

from ner_mcp.server import mcp, taxonomy_categories


def registered_tools() -> set[str]:
    return {tool.name for tool in asyncio.run(mcp.list_tools())}


class TestRegistration:
    def test_server_metadata(self) -> None:
        assert mcp.name == "ner-mcp"

    def test_tools_registered(self) -> None:
        assert registered_tools() == {"extract_entities", "redact_text", "restore_text"}

    def test_resources_registered(self) -> None:
        resources = asyncio.run(mcp.list_resources())
        uris = {str(resource.uri) for resource in resources}
        assert "taxonomy://entities/categories" in uris

    def test_prompt_registered(self) -> None:
        prompts = asyncio.run(mcp.list_prompts())
        assert "extract_and_summarize" in {prompt.name for prompt in prompts}


class TestTaxonomy:
    def test_lists_categories(self) -> None:
        payload = json.loads(taxonomy_categories())
        assert "PER" in payload["categories"]
        assert "PASSPORT" in payload["categories"]

    def test_marks_pii_categories(self) -> None:
        payload = json.loads(taxonomy_categories())
        assert "PHONE" in payload["pii_categories"]
        assert "PER" not in payload["pii_categories"]
