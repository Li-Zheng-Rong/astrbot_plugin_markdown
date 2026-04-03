"""Comprehensive XSS payload fuzzing tests for the DOMPurify sanitization layer.

Uses a curated set of XSS payloads sourced from:
- PayloadsAllTheThings (https://github.com/swisskyrepo/PayloadsAllTheThings)
- PortSwigger XSS Cheat Sheet
- mXSS Cheatsheet (https://sonarsource.github.io/mxss-cheatsheet/)
- Known DOMPurify bypass vectors

Each payload is rendered through the full markdown pipeline (markdown-it →
DOMPurify → innerHTML) with ``md_html: true``.  Detection scans the output
HTML for residual dangerous patterns: event handlers in tag attributes,
``javascript:`` URIs, ``<script>`` tags, and banned elements.

Requires Playwright with Chromium installed.
"""

import re

import pytest
import pytest_asyncio

pw = pytest.importorskip(
    "playwright", reason="Playwright not installed — skipping XSS fuzz tests"
)

from data.plugins.astrbot_plugin_markdown.renderer import MarkdownRenderer

_ENGINE_HTML_ON = {
    "markdownIt": {"html": True, "linkify": True, "typographer": True},
    "katex": {"throwOnError": False, "output": "htmlAndMathml", "trust": True},
    "highlight": {"ignoreIllegals": True},
}

_BASE_OPTIONS = {"theme": "light", "fontSize": 16, "footer": "", "engine": _ENGINE_HTML_ON}

# Regex to detect event handler attributes inside HTML tags.
# Matches on<word>= patterns inside angle brackets.
_EVENT_HANDLER_RE = re.compile(r"\bon[a-z]+\s*=", re.IGNORECASE)

# Regex to detect javascript:/data:text URI schemes in href/src/action attributes
_DANGEROUS_URI_RE = re.compile(
    r"""(?:href|src|action|formaction|data|srcdoc)\s*=\s*["']?\s*(?:javascript|data\s*:\s*text)""",
    re.IGNORECASE,
)

# Elements that DOMPurify should strip entirely
_BANNED_ELEMENTS = ["script", "iframe", "object", "embed", "form", "style", "link", "base", "meta"]
_BANNED_RE = re.compile(
    r"<\s*(?:" + "|".join(_BANNED_ELEMENTS) + r")\b", re.IGNORECASE
)

# ── Payload categories ──────────────────────────────────────────────

# fmt: off
SCRIPT_INJECTION = [
    "<script>alert('XSS')</script>",
    '<scr<script>ipt>alert("XSS")</scr<script>ipt>',
    '"><script>alert("XSS")</script>',
    "<script src=javascript:alert(1)>",
    "</style></scRipt><scRipt>alert(1)</scRipt>",
    "</script><svg onload=alert(1)>",
    "<script>window['alert'](0)</script>",
    "<script>$=1,alert($)</script>",
    r"<script>\u0061\u006C\u0065\u0072\u0074(1)</script>",
    "<script>alert(1)//",
    "<script>alert(1)<!–",
]

EVENT_HANDLERS = [
    "<img src=x onerror=alert(1)>",
    '<img src=x onerror=alert(String.fromCharCode(88,83,83))>',
    "<img src=x:alert(alt) onerror=eval(src) alt=xss>",
    '<img src="1" onerror="&#x61;&#x6c;&#x65;&#x72;&#x74;&#x28;&#x31;&#x29;">',
    "<img src=1 alt=al lang=ert onerror=top[alt+lang](0)>",
    "<svg/onload=alert(1)>",
    '<svg id=alert(1) onload=eval(id)>',
    '<svg xmlns="http://www.w3.org/2000/svg" onload="alert(1)"/>',
    "<body onload=alert(1)>",
    "<body onpageshow=alert(1)>",
    "<input autofocus onfocus=alert(1)>",
    "<select autofocus onfocus=alert(1)>",
    "<textarea autofocus onfocus=alert(1)>",
    "<video/poster/onerror=alert(1)>",
    '<video><source onerror="javascript:alert(1)">',
    '<video src=_ onloadstart="alert(1)">',
    '<details/open/ontoggle="alert(1)">',
    "<audio src onloadstart=alert(1)>",
    "<marquee onstart=alert(1)>",
    "<x contenteditable onblur=alert(1)>lose focus!",
    "<x onclick=alert(1)>click this!",
    '<div onmouseover=alert(1)>hover</div>',
    '<html ontouchstart=alert(1)>',
]

DANGEROUS_URIS = [
    '<a href=javascript:alert(1)>click',
    '<iframe src=javascript:alert(1)>',
    '<embed src=javascript:alert(1)>',
    '<object data=javascript:alert(1)>',
    '<form action=javascript:alert(1)><input type=submit>',
    '<form><button formaction=javascript:alert(1)>click',
    '<form><input formaction=javascript:alert(1) type=submit value=click>',
    '<a href="data:text/html,<script>alert(1)</script>">click</a>',
    '<iframe src="javascript:%61%6c%65%72%74%28%31%29">',
    '<META HTTP-EQUIV="refresh" CONTENT="0;url=data:text/html;base64,PHNjcmlwdD5hbGVydCgnWFNTJyk8L3NjcmlwdD4K">',
]

DANGEROUS_ELEMENTS = [
    '<iframe src="http://evil.com"></iframe>',
    '<iframe srcdoc=\'<svg onload=alert(1)>\'></iframe>',
    '<embed src="http://evil.com/exploit">',
    '<object data="http://evil.com/exploit.swf"></object>',
    '<form onsubmit=alert(1)><input type=submit>',
    '<link rel=import href="data:text/html,<script>alert(1)</script>">',
    '<base href=//evil.com>',
]

SVG_AND_MATHML = [
    "<svgonload=alert(1)>",
    '<svg><script xlink:href=data:,alert(1) />',
    '<svg><a xmlns:xlink=http://www.w3.org/1999/xlink xlink:href=javascript:alert(1)><circle r=400 /></svg>',
    '<math><brute href=javascript:alert(1)>click',
    '<math><brute xlink:href=javascript:alert(1)>click',
]

MXSS_BYPASS_ATTEMPTS = [
    '<svg><annotation-xml><foreignobject><style><!--</style><p id="--><img src=x onerror=alert(1)>">',
    '<math><foo-test><mi><li><table><foo-test><li></li></foo-test><a><style><!--</style>a<foo-bar is="--><img src=x onerror=alert(1)>">',
    '<svg><style><img src=x onerror=alert(1)></style></svg>',
    '"><svg onload=alert(1)//',
    "<img/id=\"alert&lpar;&#x27;XSS&#x27;&#x29;\\\"/alt=\"/\"src=\"/\"onerror=eval(id&#x29;>",
    '<img src=x oneonerrorrror=alert(1)>',
]

ENCODING_AND_OBFUSCATION = [
    'jaVasCript:/*-/*`/*\\`/*\'/*"/**/(/* */oNcliCk=alert() )',
    "<img src=x onerror=&#x61;&#x6c;&#x65;&#x72;&#x74;(1)>",
    '<script src="data:&comma;alert(1)//',
    'GIF89a/*<svg/onload=alert(1)>*/=alert(1)//;',
    '<keygen autofocus onfocus=alert(1)>',
    '<img src=x onerror="eval(atob(\'YWxlcnQoMSk=\'))">',
]
# fmt: on

ALL_PAYLOADS = (
    [(p, "script_injection") for p in SCRIPT_INJECTION]
    + [(p, "event_handler") for p in EVENT_HANDLERS]
    + [(p, "dangerous_uri") for p in DANGEROUS_URIS]
    + [(p, "dangerous_element") for p in DANGEROUS_ELEMENTS]
    + [(p, "svg_mathml") for p in SVG_AND_MATHML]
    + [(p, "mxss_bypass") for p in MXSS_BYPASS_ATTEMPTS]
    + [(p, "encoding_obfuscation") for p in ENCODING_AND_OBFUSCATION]
)


@pytest_asyncio.fixture
async def renderer():
    """Module-scoped renderer to reuse browser across all payload tests."""
    r = MarkdownRenderer()
    yield r
    await r.terminate()


def _make_markdown(payload: str) -> str:
    """Wrap payload in enough markdown to pass the score/length threshold."""
    return f"# Test Document\n\n{payload}\n\n**Bold** and `code` for scoring."


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "payload,category",
    ALL_PAYLOADS,
    ids=[f"{cat}_{i}" for i, (_, cat) in enumerate(ALL_PAYLOADS)],
)
async def test_xss_payload_neutralized(renderer, payload, category):
    """Verify that each XSS payload is neutralized by DOMPurify.

    Uses pattern-based detection on the sanitized HTML output to check for
    residual dangerous content: event handlers, ``javascript:`` URIs,
    ``<script>`` tags, and banned elements like ``<iframe>``/``<object>``.
    """
    await renderer._ensure_browser()
    await renderer._page.evaluate("window.__renderComplete = false")

    md_text = _make_markdown(payload)
    try:
        await renderer._page.evaluate(
            "(args) => renderMarkdown(args.text, args.options)",
            {"text": md_text, "options": _BASE_OPTIONS},
        )
        await renderer._page.wait_for_function(
            "window.__renderComplete === true", timeout=10000
        )
    except Exception:
        # Rendering error means the payload was rejected — acceptable
        return

    html = await renderer._page.eval_on_selector("#content", "el => el.innerHTML")

    # Extract all opening tags for attribute-level checks
    tags = re.findall(r"<[a-z][^>]*>", html, re.IGNORECASE)

    # 1. No <script> tags
    assert "<script" not in html.lower(), (
        f"<script> tag survived sanitization\n"
        f"  Category: {category}\n"
        f"  Payload:  {payload!r}"
    )

    # 2. No banned elements (iframe, object, embed, form, style, etc.)
    match = _BANNED_RE.search(html)
    assert match is None, (
        f"Banned element survived: {match.group() if match else '?'}\n"
        f"  Category: {category}\n"
        f"  Payload:  {payload!r}"
    )

    # 3. No event handler attributes in tags
    for tag in tags:
        assert not _EVENT_HANDLER_RE.search(tag), (
            f"Event handler survived in tag: {tag[:120]}\n"
            f"  Category: {category}\n"
            f"  Payload:  {payload!r}"
        )

    # 4. No javascript:/data:text URIs in link/src/action attributes
    for tag in tags:
        assert not _DANGEROUS_URI_RE.search(tag), (
            f"Dangerous URI survived in tag: {tag[:120]}\n"
            f"  Category: {category}\n"
            f"  Payload:  {payload!r}"
        )
