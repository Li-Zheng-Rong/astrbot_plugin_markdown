"""Tests for plugin config handling in main.py."""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from astrbot.api.message_components import Plain

from data.plugins.astrbot_plugin_markdown.main import Main


class DummyConfig(dict):
    """Minimal config object with save tracking."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.saved = False

    def save_config(self) -> None:
        self.saved = True


class DummyContext:
    """Context stub that exposes core config via get_config()."""

    def __init__(self, core_config):
        self._core_config = core_config

    def get_config(self, umo=None):
        return self._core_config


class DummyResult:
    """Result stub for on_decorating_result."""

    def __init__(self, chain):
        self.chain = chain
        self.use_t2i_ = True

    def is_llm_result(self) -> bool:
        return True


class DummyEvent:
    """Event stub for command and filter handlers."""

    def __init__(self, result=None):
        self._result = result

    def get_result(self):
        return self._result

    def plain_result(self, text: str):
        return text


@pytest.mark.asyncio
async def test_on_decorating_result_uses_plugin_footer(monkeypatch):
    """Injected plugin config should win over core config when rendering."""
    core_config = DummyConfig({"footer": "core footer"})
    plugin_config = DummyConfig(
        {
            "enabled": True,
            "llm_only": True,
            "char_threshold": 0,
            "score_threshold": 0,
            "width": 800,
            "theme": "light",
            "font_size": 16,
            "render_timeout": 10,
            "footer": "plugin footer",
            "md_html": False,
            "md_linkify": True,
            "md_typographer": True,
            "md_quotes": "\"\"''",
            "katex_throw_on_error": False,
            "katex_output": "htmlAndMathml",
            "katex_trust": False,
            "hljs_ignore_illegals": True,
        }
    )
    plugin = Main(DummyContext(core_config), config=plugin_config)
    plugin._playwright_available = True

    captured = {}

    async def fake_render(*args, **kwargs):
        captured["footer"] = kwargs["footer"]
        return b"\x89PNGtest"

    plugin.renderer = SimpleNamespace(render=fake_render)

    monkeypatch.setattr(
        "data.plugins.astrbot_plugin_markdown.main.should_render",
        lambda *args, **kwargs: True,
    )
    monkeypatch.setattr(
        "data.plugins.astrbot_plugin_markdown.main._save_temp_png",
        lambda png_bytes: "D:\\fake\\render.png",
    )

    event = DummyEvent(DummyResult([Plain("**markdown** output")]))

    await plugin.on_decorating_result(event)

    assert captured["footer"] == "plugin footer"
    assert event.get_result().use_t2i_ is False


@pytest.mark.asyncio
async def test_katex_escaped_delimiters_config_controls_detection_and_engine(
    monkeypatch,
):
    """The escaped delimiter switch should affect detection and rendering config."""
    plugin_config = DummyConfig(
        {
            "enabled": True,
            "llm_only": True,
            "char_threshold": 0,
            "score_threshold": 0,
            "force_render_char_threshold": 0,
            "katex_escaped_delimiters": False,
        }
    )
    plugin = Main(DummyContext(DummyConfig({})), config=plugin_config)
    plugin._playwright_available = True

    captured = {}

    async def fake_render(*args, **kwargs):
        captured["engine"] = kwargs["engine"]
        return b"\x89PNGtest"

    def fake_should_render(*args, **kwargs):
        captured["should_render_kwargs"] = kwargs
        return True

    plugin.renderer = SimpleNamespace(render=fake_render)

    monkeypatch.setattr(
        "data.plugins.astrbot_plugin_markdown.main.should_render",
        fake_should_render,
    )
    monkeypatch.setattr(
        "data.plugins.astrbot_plugin_markdown.main._save_temp_png",
        lambda png_bytes: "D:\\fake\\render.png",
    )

    event = DummyEvent(DummyResult([Plain(r"Inline \(E = mc^2\)")]))

    await plugin.on_decorating_result(event)

    assert (
        captured["should_render_kwargs"]["enable_escaped_math_delimiters"] is False
    )
    assert captured["engine"]["katex"]["enableEscapedDelimiters"] is False


@pytest.mark.asyncio
async def test_md_theme_saves_plugin_config_not_core_config():
    """The theme command should persist changes to plugin config."""
    core_config = DummyConfig({"theme": "light"})
    plugin_config = DummyConfig({"theme": "light"})
    plugin = Main(DummyContext(core_config), config=plugin_config)

    event = DummyEvent()
    outputs = [item async for item in plugin.cmd_theme(event, "dark")]

    assert plugin_config["theme"] == "dark"
    assert plugin_config.saved is True
    assert core_config["theme"] == "light"
    assert outputs == ["Markdown theme set to: dark"]
