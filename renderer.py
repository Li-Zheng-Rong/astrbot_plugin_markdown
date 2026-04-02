"""Playwright-based markdown renderer.

Manages a headless Chromium browser that loads a local HTML template
with pre-built markdown-it + KaTeX + highlight.js. Renders markdown
text to PNG images by injecting content and taking element screenshots.
"""

from __future__ import annotations

import asyncio
import time
from pathlib import Path

from astrbot.api import logger

_TEMPLATES_DIR = Path(__file__).parent / "templates"
_RENDER_HTML = _TEMPLATES_DIR / "render.html"

# How many renders before we force-reload the page to avoid memory leaks
_PAGE_RELOAD_INTERVAL = 200


class MarkdownRenderer:
    """Renders markdown text to PNG images via headless Chromium."""

    def __init__(self) -> None:
        self._playwright = None
        self._browser = None
        self._page = None
        self._lock = asyncio.Lock()
        self._render_count = 0
        self._initialized = False

    async def initialize(self) -> None:
        """Lazy — actual browser start deferred to first render."""

    async def _ensure_browser(self, width: int = 800) -> None:
        """Start browser and load template if not already done."""
        if self._initialized and self._page and not self._page.is_closed():
            return

        await self._cleanup()

        try:
            from playwright.async_api import async_playwright

            self._playwright = await async_playwright().start()
            self._browser = await self._playwright.chromium.launch(
                headless=True,
                # --no-sandbox is required in Docker / rootless containers
                # where the user namespace sandbox is unavailable.  The
                # security surface is limited because md_html defaults to
                # false (raw HTML stripped) and katex_trust defaults to
                # false, so user-controlled content cannot inject
                # executable markup into the page.
                args=[
                    "--no-sandbox",
                    "--disable-gpu",
                    "--disable-dev-shm-usage",
                    "--font-render-hinting=none",
                ],
            )
            self._page = await self._browser.new_page()
            await self._page.set_viewport_size({"width": width, "height": 600})

            template_url = _RENDER_HTML.resolve().as_uri()
            await self._page.goto(template_url, wait_until="domcontentloaded")

            self._render_count = 0
            self._initialized = True
            logger.info("Markdown renderer: browser started and template loaded.")
        except Exception as e:
            logger.error(f"Markdown renderer: failed to start browser — {e}")
            await self._cleanup()
            raise

    async def _cleanup(self) -> None:
        """Close browser and playwright."""
        self._initialized = False
        try:
            if self._page and not self._page.is_closed():
                await self._page.close()
        except Exception as e:
            logger.debug(f"Markdown renderer: page close error — {e}")
        try:
            if self._browser:
                await self._browser.close()
        except Exception as e:
            logger.debug(f"Markdown renderer: browser close error — {e}")
        try:
            if self._playwright:
                await self._playwright.stop()
        except Exception as e:
            logger.debug(f"Markdown renderer: playwright stop error — {e}")
        self._page = None
        self._browser = None
        self._playwright = None

    async def render(
        self,
        markdown_text: str,
        *,
        width: int = 800,
        theme: str = "light",
        font_size: int = 16,
        footer: str = "",
        timeout: int = 10,
        engine: dict | None = None,
    ) -> bytes:
        """Render markdown text to PNG bytes.

        Args:
            markdown_text: The markdown content to render.
            width: Image width in pixels.
            theme: "light" or "dark".
            font_size: Base font size in pixels.
            footer: Optional footer text.
            timeout: Max seconds to wait for rendering.
            engine: Engine options forwarded to the JS createRenderer.

        Returns:
            PNG image bytes.

        Raises:
            RuntimeError: If rendering fails after retries.
        """
        # Serialise renders: a Playwright page is NOT thread-safe, so
        # concurrent evaluate() calls would corrupt state.  A page-pool
        # could increase throughput, but adds complexity and memory cost
        # that is unjustified for typical chatbot message rates.
        async with self._lock:
            return await self._render_impl(
                markdown_text,
                width=width,
                theme=theme,
                font_size=font_size,
                footer=footer,
                timeout=timeout,
                engine=engine,
            )

    async def _render_impl(
        self,
        markdown_text: str,
        *,
        width: int,
        theme: str,
        font_size: int,
        footer: str,
        timeout: int,
        engine: dict | None = None,
    ) -> bytes:
        last_error: Exception | None = None

        for attempt in range(2):
            try:
                await self._ensure_browser(width=width)

                # Periodically reload to avoid memory leaks
                if self._render_count >= _PAGE_RELOAD_INTERVAL:
                    template_url = _RENDER_HTML.resolve().as_uri()
                    await self._page.goto(template_url, wait_until="domcontentloaded")
                    self._render_count = 0

                # Resize viewport if width changed
                vp = self._page.viewport_size
                if vp and vp["width"] != width:
                    await self._page.set_viewport_size({"width": width, "height": 600})

                # Reset completion flag before rendering to avoid
                # stale true from a prior run (race-condition guard)
                await self._page.evaluate("window.__renderComplete = false")

                # Call renderMarkdown() using Playwright's structured
                # arg passing — safer than f-string concatenation
                options = {
                    "theme": theme,
                    "fontSize": font_size,
                    "footer": footer,
                    "engine": engine or {},
                }

                start = time.monotonic()
                await self._page.evaluate(
                    "(args) => renderMarkdown(args.text, args.options)",
                    {"text": markdown_text, "options": options},
                )

                # Wait for rendering to complete
                await self._page.wait_for_function(
                    "window.__renderComplete === true",
                    timeout=timeout * 1000,
                )

                elapsed = time.monotonic() - start
                if elapsed > 3:
                    logger.warning(
                        f"Markdown render took {elapsed:.1f}s (threshold: 3s)"
                    )

                # Screenshot the content element
                content_el = await self._page.query_selector("#content")
                if not content_el:
                    raise RuntimeError("Could not find #content element")

                # Include footer if present
                if footer:
                    # Screenshot the full body to include footer
                    screenshot_el = await self._page.query_selector("body")
                else:
                    screenshot_el = content_el

                png_bytes = await screenshot_el.screenshot(type="png")
                self._render_count += 1

                logger.debug(
                    f"Markdown rendered: {len(markdown_text)} chars → "
                    f"{len(png_bytes)} bytes PNG in {elapsed:.2f}s"
                )
                return png_bytes

            except Exception as e:
                last_error = e
                logger.warning(f"Markdown render attempt {attempt + 1} failed: {e}")
                # Reset browser state for retry
                await self._cleanup()

        raise RuntimeError(f"Markdown rendering failed after 2 attempts: {last_error}")

    async def terminate(self) -> None:
        """Shut down browser and release resources."""
        async with self._lock:
            await self._cleanup()
            logger.info("Markdown renderer: browser closed.")
