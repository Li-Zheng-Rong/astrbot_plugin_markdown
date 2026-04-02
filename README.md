# astrbot_plugin_markdown

High-quality markdown-to-image rendering plugin for [AstrBot](https://github.com/AstrBotDevs/AstrBot), powered by VS Code's markdown-it ecosystem.

## Features

- **Code Highlighting** — Syntax highlighting via [highlight.js](https://highlightjs.org/) with 190+ languages
- **Math Rendering** — LaTeX math (inline `$...$` and display `$$...$$`) via [@vscode/markdown-it-katex](https://github.com/microsoft/vscode-markdown-it-katex)
- **Full Markdown** — Headers, tables, blockquotes, lists, bold/italic, inline code, links, images, horizontal rules
- **Light & Dark Themes** — GitHub-inspired styling with theme switching (`/md_theme light|dark`)
- **Smart Detection** — Only renders when markdown syntax is detected AND text exceeds a configurable length threshold
- **Coexists with built-in t2i** — When the plugin skips a message, AstrBot's built-in text-to-image can still handle it
- **High Performance** — Headless browser stays alive between renders; first render ~2s, subsequent renders <300ms

## Architecture

```
LLM Response (text with markdown)
    │
    ▼
┌─ on_decorating_result (priority=10) ──────────────┐
│  MarkdownDetector: pattern scoring + length check  │
│  MarkdownRenderer: Playwright → headless Chromium  │
│    ├─ render.html loads bundled JS (markdown-it)   │
│    ├─ page.evaluate() injects markdown             │
│    └─ element.screenshot() → PNG                   │
│  Replace chain with Image, set use_t2i_ = False    │
└────────────────────────────────────────────────────┘
```

## Requirements

- Python 3.10+
- [Playwright](https://playwright.dev/python/) with Chromium

## Installation

1. Install the plugin into AstrBot (the `requirements.txt` will be auto-installed):

2. Install the Chromium browser for Playwright:
   ```bash
   playwright install chromium
   ```

3. Restart AstrBot. The plugin will be loaded automatically.

## Configuration

All settings are configurable from the AstrBot dashboard via `_conf_schema.json`:

| Setting | Type | Default | Description |
|---------|------|---------|-------------|
| `enabled` | bool | `true` | Enable/disable the plugin |
| `char_threshold` | int | `100` | Minimum text length to trigger rendering |
| `score_threshold` | int | `2` | Minimum markdown score to trigger rendering |
| `width` | int | `800` | Image width in pixels |
| `theme` | string | `"light"` | `"light"` or `"dark"` |
| `font_size` | int | `16` | Base font size in pixels |
| `render_timeout` | int | `10` | Max seconds per render |
| `footer` | string | `"Powered by AstrBot"` | Footer text (empty to hide) |

## Commands

| Command | Description |
|---------|-------------|
| `/md_theme <light\|dark>` | Switch rendering theme |

## Development

### Rebuilding JS Assets

The `dist/` directory contains pre-built JS/CSS assets. To rebuild after modifying JS dependencies:

```bash
cd data/plugins/astrbot_plugin_markdown
npm install
npm run build
```

This requires Node.js 18+ (development only — end users do not need Node.js).

### Running Tests

```bash
cd <AstrBot root>
uv run pytest data/plugins/astrbot_plugin_markdown/tests/ -v
```

## License

See [LICENSE](LICENSE) file.
