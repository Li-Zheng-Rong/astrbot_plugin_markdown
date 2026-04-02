"""Integration tests for the Playwright-based markdown renderer.

These tests require Playwright with Chromium installed:
    pip install playwright && playwright install chromium

Note: Some tests access private attributes (``_initialized``, ``_page``,
``_ensure_browser``) because the renderer's public surface is just
``render()`` / ``terminate()``.  Verifying browser lifecycle and
per-render HTML output requires page-level inspection, which justifies
the coupling to internal state.
"""

import pytest
import pytest_asyncio

pw = pytest.importorskip("playwright", reason="Playwright not installed — skipping renderer tests")

# Import path matches AstrBot's fixed plugin layout (data/plugins/<name>/).
# Tests are executed from the repository root via ``uv run python -m pytest``.
from data.plugins.astrbot_plugin_markdown.renderer import MarkdownRenderer


@pytest_asyncio.fixture
async def renderer():
    """Create a renderer and clean up after tests."""
    r = MarkdownRenderer()
    yield r
    await r.terminate()


@pytest.mark.asyncio
async def test_render_basic_markdown(renderer):
    """Renders a simple markdown document to PNG bytes."""
    md = "# Hello World\n\nThis is a **test** paragraph."
    result = await renderer.render(md)
    assert isinstance(result, bytes)
    assert len(result) > 0
    # PNG magic bytes
    assert result[:4] == b"\x89PNG"


@pytest.mark.asyncio
async def test_render_code_block(renderer):
    """Renders a code block with syntax highlighting."""
    md = "```python\nprint('hello')\n```"
    result = await renderer.render(md)
    assert result[:4] == b"\x89PNG"
    assert len(result) > 100


@pytest.mark.asyncio
async def test_render_math(renderer):
    """Renders KaTeX math expressions."""
    md = "Inline: $E = mc^2$\n\nDisplay:\n$$x = \\frac{-b}{2a}$$"
    result = await renderer.render(md)
    assert result[:4] == b"\x89PNG"


@pytest.mark.asyncio
async def test_render_table(renderer):
    """Renders a markdown table."""
    md = "| A | B |\n|---|---|\n| 1 | 2 |\n| 3 | 4 |"
    result = await renderer.render(md)
    assert result[:4] == b"\x89PNG"


@pytest.mark.asyncio
async def test_render_dark_theme(renderer):
    """Renders with dark theme."""
    md = "# Dark Theme\n\nSome text."
    result = await renderer.render(md, theme="dark")
    assert result[:4] == b"\x89PNG"


@pytest.mark.asyncio
async def test_render_with_footer(renderer):
    """Renders with a custom footer."""
    md = "# Title\n\nContent."
    result = await renderer.render(md, footer="Test Footer")
    assert result[:4] == b"\x89PNG"


@pytest.mark.asyncio
async def test_render_empty_string(renderer):
    """Renders an empty markdown string without crashing."""
    result = await renderer.render("")
    assert result[:4] == b"\x89PNG"


@pytest.mark.asyncio
async def test_multiple_renders_reuse_browser(renderer):
    """Multiple sequential renders reuse the same browser instance."""
    for i in range(3):
        result = await renderer.render(f"# Render {i}\n\nParagraph text.")
        assert result[:4] == b"\x89PNG"
    # After 3 renders, browser should still be alive
    assert renderer._initialized is True


@pytest.mark.asyncio
async def test_render_custom_width(renderer):
    """Renders with a custom width."""
    md = "# Wide\n\nSome text content here."
    result = await renderer.render(md, width=1200)
    assert result[:4] == b"\x89PNG"


@pytest.mark.asyncio
async def test_terminate_and_re_render(renderer):
    """After terminate, a new render should re-initialize the browser."""
    md = "# Test"
    result1 = await renderer.render(md)
    assert result1[:4] == b"\x89PNG"

    await renderer.terminate()
    assert renderer._initialized is False

    result2 = await renderer.render(md)
    assert result2[:4] == b"\x89PNG"
    assert renderer._initialized is True


@pytest.mark.asyncio
async def test_typographer_and_entities_render_as_text(renderer):
    """Typographic substitutions and markdown escapes should render correctly."""
    await renderer._ensure_browser()
    await renderer._page.evaluate(
        "(args) => renderMarkdown(args.text, args.options)",
        {
            "text": r"Brand (tm) &copy; \*literal\*",
            "options": {"theme": "light", "fontSize": 16, "footer": ""},
        },
    )
    await renderer._page.wait_for_function("window.__renderComplete === true")

    text = await renderer._page.eval_on_selector("#content", "el => el.textContent")
    html = await renderer._page.eval_on_selector("#content", "el => el.innerHTML")

    assert "Brand ™ © *literal*" in text
    assert "<em>literal</em>" not in html


@pytest.mark.asyncio
async def test_raw_html_is_escaped(renderer):
    """Raw HTML should be rendered as literal text, not injected into the page."""
    await renderer._ensure_browser()
    await renderer._page.evaluate(
        "(args) => renderMarkdown(args.text, args.options)",
        {
            "text": '<span class="unsafe">hello</span>',
            "options": {"theme": "light", "fontSize": 16, "footer": ""},
        },
    )
    await renderer._page.wait_for_function("window.__renderComplete === true")

    text = await renderer._page.eval_on_selector("#content", "el => el.textContent")
    html = await renderer._page.eval_on_selector("#content", "el => el.innerHTML")

    assert '<span class="unsafe">hello</span>' in text
    assert "&lt;span" in html


@pytest.mark.asyncio
async def test_superscript_and_subscript(renderer):
    """Superscript (^text^) and subscript (~text~) syntax should render."""
    await renderer._ensure_browser()
    await renderer._page.evaluate(
        "(args) => renderMarkdown(args.text, args.options)",
        {
            "text": "H~2~O and x^2^",
            "options": {"theme": "light", "fontSize": 16, "footer": ""},
        },
    )
    await renderer._page.wait_for_function("window.__renderComplete === true")

    html = await renderer._page.eval_on_selector("#content", "el => el.innerHTML")

    assert "<sub>" in html and "2" in html
    assert "<sup>" in html
