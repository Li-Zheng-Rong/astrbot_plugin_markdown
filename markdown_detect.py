"""Markdown syntax detection and scoring for deciding when to render as image."""

from __future__ import annotations

import re

_ESCAPED_MATH_RULES: list[tuple[re.Pattern, int]] = [
    # LaTeX display math using escaped bracket delimiters
    (re.compile(r"\\\[[\s\S]+?\\\]", re.MULTILINE), 3),
    # LaTeX inline math using escaped parenthesis delimiters
    (re.compile(r"\\\((?!\s)[\s\S]+?(?<!\s)\\\)"), 2),
]

# (pattern, score)
_MARKDOWN_RULES: list[tuple[re.Pattern, int]] = [
    # Fenced code blocks — strong indicator
    (re.compile(r"```[\s\S]*?```", re.MULTILINE), 3),
    # LaTeX display math
    (re.compile(r"\$\$[\s\S]+?\$\$", re.MULTILINE), 3),
    # LaTeX inline math (at least one non-trivial expression)
    (re.compile(r"(?<!\$)\$(?!\$)(?!\s)[^$\n]+(?<!\s)\$(?!\$)"), 2),
    # Headers
    (re.compile(r"^#{1,6}\s+.+", re.MULTILINE), 2),
    # Tables (pipe-delimited rows)
    (re.compile(r"^\|.+\|$", re.MULTILINE), 2),
    # Images
    (re.compile(r"!\[.*?\]\(.+?\)"), 2),
    # Blockquotes
    (re.compile(r"^>\s+.+", re.MULTILINE), 1),
    # Unordered lists
    (re.compile(r"^[\t ]*[-*+]\s+.+", re.MULTILINE), 1),
    # Ordered lists
    (re.compile(r"^[\t ]*\d+\.\s+.+", re.MULTILINE), 1),
    # Bold
    (re.compile(r"\*\*[^*]+\*\*"), 1),
    # Italic (single asterisk, not bold)
    (re.compile(r"(?<!\*)\*(?!\*)(?!\s)[^*\n]+(?<!\s)\*(?!\*)"), 1),
    # Inline code
    (re.compile(r"`[^`\n]+`"), 1),
    # Links
    (re.compile(r"\[.+?\]\(.+?\)"), 1),
    # Horizontal rules
    (re.compile(r"^[-*_]{3,}\s*$", re.MULTILINE), 1),
]


def compute_markdown_score(
    text: str,
    *,
    enable_escaped_math_delimiters: bool = True,
) -> int:
    """Compute a score indicating how much markdown syntax the text contains.

    Each matching pattern adds its weight to the total score.
    Duplicate matches of the same pattern are counted only once.
    """
    score = 0
    rules = _MARKDOWN_RULES
    if enable_escaped_math_delimiters:
        rules = [*_ESCAPED_MATH_RULES, *_MARKDOWN_RULES]
    for pattern, weight in rules:
        if pattern.search(text):
            score += weight
    return score


def should_render(
    text: str,
    *,
    char_threshold: int = 100,
    score_threshold: int = 2,
    force_render_char_threshold: int = 500,
    enable_escaped_math_delimiters: bool = True,
) -> bool:
    """Decide whether the text should be rendered as a markdown image.

    Returns True if:
    - Text length >= force_render_char_threshold (force render regardless of
      markdown content), OR
    - Text contains enough markdown syntax (score >= score_threshold) AND is
      long enough (len >= char_threshold).
    """
    if force_render_char_threshold > 0 and len(text) >= force_render_char_threshold:
        return True
    if len(text) < char_threshold:
        return False
    return (
        compute_markdown_score(
            text,
            enable_escaped_math_delimiters=enable_escaped_math_delimiters,
        )
        >= score_threshold
    )
