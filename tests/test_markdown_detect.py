"""Unit tests for markdown_detect module."""

from data.plugins.astrbot_plugin_markdown.markdown_detect import (
    compute_markdown_score,
    should_render,
)


class TestComputeMarkdownScore:
    """Tests for the scoring function."""

    def test_plain_text_scores_zero(self):
        assert compute_markdown_score("Hello, this is plain text.") == 0

    def test_headers(self):
        score = compute_markdown_score("# Heading 1\n\nSome text")
        assert score >= 2

    def test_fenced_code_block(self):
        text = "Look at this:\n```python\nprint('hi')\n```"
        score = compute_markdown_score(text)
        assert score >= 3

    def test_display_math(self):
        text = "The formula:\n$$x = \\frac{-b}{2a}$$"
        score = compute_markdown_score(text)
        assert score >= 3

    def test_inline_math(self):
        text = "Einstein's equation $E = mc^2$ is famous."
        score = compute_markdown_score(text)
        assert score >= 2

    def test_bold_text(self):
        text = "This is **bold** text."
        assert compute_markdown_score(text) >= 1

    def test_italic_text(self):
        text = "This is *italic* text."
        assert compute_markdown_score(text) >= 1

    def test_inline_code(self):
        text = "Use the `print()` function."
        assert compute_markdown_score(text) >= 1

    def test_unordered_list(self):
        text = "Items:\n- first\n- second\n- third"
        assert compute_markdown_score(text) >= 1

    def test_ordered_list(self):
        text = "Steps:\n1. first\n2. second\n3. third"
        assert compute_markdown_score(text) >= 1

    def test_blockquote(self):
        text = "> This is a quote\n> from someone wise."
        assert compute_markdown_score(text) >= 1

    def test_table(self):
        text = "| Name | Age |\n|------|-----|\n| Alice | 30 |"
        assert compute_markdown_score(text) >= 2

    def test_link(self):
        text = "Visit [AstrBot](https://github.com/AstrBotDevs/AstrBot)."
        assert compute_markdown_score(text) >= 1

    def test_image(self):
        text = "![screenshot](https://example.com/img.png)"
        assert compute_markdown_score(text) >= 2

    def test_horizontal_rule(self):
        text = "Section 1\n\n---\n\nSection 2"
        assert compute_markdown_score(text) >= 1

    def test_combined_score_adds_up(self):
        text = "# Title\n\n**Bold** and `code`\n\n```python\nx = 1\n```"
        score = compute_markdown_score(text)
        # header(2) + bold(1) + inline_code(1) + fenced_code(3) = 7
        assert score >= 5

    def test_empty_string(self):
        assert compute_markdown_score("") == 0

    def test_dollar_sign_not_math(self):
        # A single $ without matching close shouldn't score as math
        text = "The price is $100 for one item."
        score = compute_markdown_score(text)
        assert score < 3, "Lone $ sign should not produce a high math score"


class TestShouldRender:
    """Tests for the should_render decision function."""

    def test_short_markdown_does_not_render(self):
        # Has markdown but too short
        assert should_render("# Hi\n**bold**", char_threshold=100) is False

    def test_long_plain_text_does_not_render(self):
        # Long but no markdown
        text = "This is a very long plain text. " * 20
        assert should_render(text, char_threshold=100) is False

    def test_long_markdown_renders(self):
        text = (
            "# Introduction\n\n"
            "This is a **detailed** explanation with `code` examples.\n\n"
            "```python\ndef hello():\n    print('world')\n```\n\n"
            "More explanatory text to exceed the threshold easily here."
        )
        assert should_render(text, char_threshold=100, score_threshold=2) is True

    def test_custom_thresholds(self):
        text = "# Title\n\n**Bold** paragraph with enough text for 50 chars."
        # Score should be >= 2 (header + bold)
        assert should_render(text, char_threshold=50, score_threshold=2) is True
        # But not if we require a very high score
        assert should_render(text, char_threshold=50, score_threshold=10) is False

    def test_default_thresholds(self):
        # Default: char_threshold=100, score_threshold=2
        short = "# Hi"
        assert should_render(short) is False

    def test_exactly_at_threshold(self):
        # Generate text that is exactly at the char threshold
        base = "# Title\n\n**bold** text"  # Score >= 3
        padding = "x" * (100 - len(base))
        text = base + padding
        assert len(text) == 100
        assert should_render(text, char_threshold=100) is True

    def test_one_below_threshold(self):
        base = "# Title\n\n**bold** text"
        padding = "x" * (99 - len(base))
        text = base + padding
        assert len(text) == 99
        assert should_render(text, char_threshold=100) is False
