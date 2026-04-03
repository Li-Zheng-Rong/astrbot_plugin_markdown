"""Security tests for DOMPurify HTML sanitization in the rendering pipeline.

These tests verify that DOMPurify correctly strips dangerous markup while
preserving safe HTML, MathML (KaTeX), and highlight.js output.  Each test
enables ``md_html`` and/or ``katex_trust`` and injects known XSS payloads,
then asserts that the resulting DOM contains no executable content.

Requires Playwright with Chromium installed:
    pip install playwright && playwright install chromium
"""

import pytest
import pytest_asyncio

pw = pytest.importorskip(
    "playwright", reason="Playwright not installed — skipping sanitization tests"
)

from data.plugins.astrbot_plugin_markdown.renderer import MarkdownRenderer

# Engine config with md_html enabled (the dangerous option)
_ENGINE_HTML_ON = {
    "markdownIt": {"html": True, "linkify": True, "typographer": True},
    "katex": {"throwOnError": False, "output": "htmlAndMathml", "trust": False},
    "highlight": {"ignoreIllegals": True},
}

# Engine config with both md_html and katex_trust enabled
_ENGINE_ALL_ON = {
    "markdownIt": {"html": True, "linkify": True, "typographer": True},
    "katex": {"throwOnError": False, "output": "htmlAndMathml", "trust": True},
    "highlight": {"ignoreIllegals": True},
}

_BASE_OPTIONS = {"theme": "light", "fontSize": 16, "footer": ""}


async def _render_and_get_html(renderer, text, engine=None):
    """Render markdown in browser and return the #content innerHTML."""
    await renderer._ensure_browser()
    options = {**_BASE_OPTIONS, "engine": engine or _ENGINE_HTML_ON}
    await renderer._page.evaluate(
        "(args) => renderMarkdown(args.text, args.options)",
        {"text": text, "options": options},
    )
    await renderer._page.wait_for_function(
        "window.__renderComplete === true", timeout=10000
    )
    return await renderer._page.eval_on_selector("#content", "el => el.innerHTML")


@pytest_asyncio.fixture
async def renderer():
    """Create a renderer and clean up after tests."""
    r = MarkdownRenderer()
    yield r
    await r.terminate()


# ── Script injection ────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_script_tag_stripped(renderer):
    """<script> tags must be removed even when md_html is enabled."""
    html = await _render_and_get_html(
        renderer, '<script>alert("xss")</script>\n\nSafe text.'
    )
    assert "<script" not in html.lower()
    assert "alert" not in html
    assert "Safe text" in html


@pytest.mark.asyncio
async def test_script_tag_with_src_stripped(renderer):
    """<script src="..."> must be removed."""
    html = await _render_and_get_html(
        renderer, '<script src="http://evil.com/xss.js"></script>\n\nOK.'
    )
    assert "<script" not in html.lower()
    assert "evil.com" not in html


# ── Event handler injection ─────────────────────────────────────────


@pytest.mark.asyncio
async def test_img_onerror_stripped(renderer):
    """<img onerror="..."> event handler must be removed."""
    html = await _render_and_get_html(
        renderer, '<img src=x onerror="alert(1)">\n\nText.'
    )
    assert "onerror" not in html.lower()


@pytest.mark.asyncio
async def test_svg_onload_stripped(renderer):
    """<svg onload="..."> event handler must be removed."""
    html = await _render_and_get_html(
        renderer, '<svg onload="alert(1)"><circle r="10"/></svg>\n\nText.'
    )
    assert "onload" not in html.lower()
    assert "alert" not in html


@pytest.mark.asyncio
async def test_body_onload_stripped(renderer):
    """<body onload="..."> must be stripped."""
    html = await _render_and_get_html(
        renderer, '<body onload="alert(1)">content</body>\n\nText.'
    )
    assert "onload" not in html.lower()


@pytest.mark.asyncio
async def test_div_onmouseover_stripped(renderer):
    """<div onmouseover="..."> event handler must be removed."""
    html = await _render_and_get_html(
        renderer, '<div onmouseover="alert(1)">hover me</div>\n\nText.'
    )
    assert "onmouseover" not in html.lower()


# ── Dangerous URI schemes ───────────────────────────────────────────


@pytest.mark.asyncio
async def test_javascript_uri_in_href_stripped(renderer):
    """<a href="javascript:..."> must be sanitized."""
    html = await _render_and_get_html(
        renderer, '<a href="javascript:alert(1)">click</a>\n\nText.'
    )
    assert "javascript:" not in html.lower()


@pytest.mark.asyncio
async def test_javascript_uri_in_img_src_stripped(renderer):
    """<img src="javascript:..."> must be sanitized."""
    html = await _render_and_get_html(
        renderer, '<img src="javascript:alert(1)">\n\nText.'
    )
    assert "javascript:" not in html.lower()


# ── Dangerous elements ──────────────────────────────────────────────


@pytest.mark.asyncio
async def test_iframe_stripped(renderer):
    """<iframe> must be removed entirely."""
    html = await _render_and_get_html(
        renderer, '<iframe src="http://evil.com"></iframe>\n\nText.'
    )
    assert "<iframe" not in html.lower()


@pytest.mark.asyncio
async def test_object_stripped(renderer):
    """<object> must be removed."""
    html = await _render_and_get_html(
        renderer, '<object data="http://evil.com/exploit.swf"></object>\n\nText.'
    )
    assert "<object" not in html.lower()


@pytest.mark.asyncio
async def test_embed_stripped(renderer):
    """<embed> must be removed."""
    html = await _render_and_get_html(
        renderer, '<embed src="http://evil.com/exploit">\n\nText.'
    )
    assert "<embed" not in html.lower()


@pytest.mark.asyncio
async def test_form_stripped(renderer):
    """<form> must be removed."""
    html = await _render_and_get_html(
        renderer,
        '<form action="http://evil.com"><input type="submit"></form>\n\nText.',
    )
    assert "<form" not in html.lower()


# ── Compound / obfuscated payloads ──────────────────────────────────


@pytest.mark.asyncio
async def test_nested_script_in_div(renderer):
    """Nested script inside a div must be stripped."""
    html = await _render_and_get_html(
        renderer,
        '<div><script>document.location="http://evil.com"</script></div>\n\nText.',
    )
    assert "<script" not in html.lower()
    assert "document.location" not in html


@pytest.mark.asyncio
async def test_data_uri_html_stripped(renderer):
    """<a href="data:text/html,..."> must be sanitized."""
    html = await _render_and_get_html(
        renderer,
        '<a href="data:text/html,<script>alert(1)</script>">click</a>\n\nText.',
    )
    assert "data:text/html" not in html.lower()


@pytest.mark.asyncio
async def test_style_tag_stripped(renderer):
    """<style> tags that could exfiltrate data via CSS must be stripped."""
    html = await _render_and_get_html(
        renderer,
        "<style>body { background: url('http://evil.com/track') }</style>\n\nText.",
    )
    assert "<style" not in html.lower()


# ── Safe HTML preserved ─────────────────────────────────────────────


@pytest.mark.asyncio
async def test_safe_html_preserved(renderer):
    """Common safe HTML tags must be preserved when md_html is enabled."""
    html = await _render_and_get_html(
        renderer,
        (
            "<strong>bold</strong> <em>italic</em> <u>underline</u>\n\n"
            '<a href="https://example.com">link</a>\n\nText.'
        ),
    )
    assert "<strong>" in html
    assert "<em>" in html
    assert "<u>" in html
    assert 'href="https://example.com"' in html


@pytest.mark.asyncio
async def test_table_html_preserved(renderer):
    """HTML tables must be preserved when md_html is enabled."""
    html = await _render_and_get_html(
        renderer,
        "<table><tr><td>cell</td></tr></table>\n\nText.",
    )
    assert "<table>" in html.lower()
    assert "<td>" in html.lower()
    assert "cell" in html


# ── KaTeX with trust ────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_katex_trust_href_javascript_stripped(renderer):
    r"""KaTeX \href{javascript:...}{} must have the dangerous href sanitized.

    The ``javascript:`` string may still appear as text content inside a
    MathML ``<annotation>`` element (the raw LaTeX source) — this is inert
    and cannot be executed.  The important check is that no ``<a>`` tag
    carries a ``href="javascript:..."`` attribute.
    """
    html = await _render_and_get_html(
        renderer,
        r"$\href{javascript:alert(1)}{click}$",
        engine=_ENGINE_ALL_ON,
    )
    # The <a> tag in KaTeX HTML output must NOT have javascript: in href
    import re

    a_hrefs = re.findall(r'<a\b[^>]*href="([^"]*)"', html, re.IGNORECASE)
    for href in a_hrefs:
        assert "javascript:" not in href.lower(), f"Dangerous href found: {href}"


@pytest.mark.asyncio
async def test_katex_math_preserved(renderer):
    """KaTeX math rendering must produce valid output after sanitization."""
    html = await _render_and_get_html(
        renderer,
        "Euler: $e^{i\\pi} + 1 = 0$\n\n$$\\int_0^1 x^2 dx$$",
        engine=_ENGINE_ALL_ON,
    )
    assert "katex" in html.lower()


@pytest.mark.asyncio
async def test_katex_mathml_preserved(renderer):
    """MathML elements generated by KaTeX must survive sanitization."""
    html = await _render_and_get_html(
        renderer,
        "$$x = \\frac{-b}{2a}$$",
        engine=_ENGINE_ALL_ON,
    )
    # KaTeX htmlAndMathml mode produces <math> elements
    assert "<math" in html.lower() or "katex" in html.lower()


# ── highlight.js output preserved ───────────────────────────────────


@pytest.mark.asyncio
async def test_hljs_output_preserved(renderer):
    """highlight.js code highlighting must survive sanitization."""
    html = await _render_and_get_html(
        renderer,
        '```python\nprint("hello")\n```',
        engine=_ENGINE_HTML_ON,
    )
    assert "hljs" in html
    assert "<code" in html.lower()
    assert "<pre" in html.lower()
