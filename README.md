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
┌─ on_decorating_result (priority=10) ───────────────┐
│  MarkdownDetector: pattern scoring + length check  │
│  MarkdownRenderer: Playwright → headless Chromium  │
│    ├─ render.html loads bundled JS (markdown-it)   │
│    ├─ page.evaluate() injects markdown             │
│    └─ element.screenshot() → PNG                   │
│  Replace chain with Image, set use_t2i_ = False    │
└────────────────────────────────────────────────────┘
```

## Requirements

- AstrBot >= 4.0.0
- Python 3.10+
- `playwright` Python package (installed from `requirements.txt`)
- Chromium for Playwright (`playwright install chromium`)

## Installation

1. Install the plugin into AstrBot (the `requirements.txt` will be auto-installed):

2. Install the Chromium browser for Playwright:
   ```bash
   playwright install chromium
   ```

If Chromium is missing, the plugin logs a warning and leaves the original text untouched.

## Configuration

All settings are configurable from the AstrBot dashboard via `_conf_schema.json`:

| Setting | Type | Default | Description |
|---------|------|---------|-------------|
| `enabled` | bool | `true` | Enable or disable markdown-to-image rendering |
| `char_threshold` | int | `100` | Minimum text length required before rendering is considered |
| `score_threshold` | int | `2` | Minimum markdown score required before rendering |
| `width` | int | `800` | Rendered image width in pixels |
| `theme` | string | `"light"` | Rendering theme: `light` or `dark` |
| `font_size` | int | `16` | Base font size in pixels |
| `render_timeout` | int | `10` | Maximum time in seconds allowed for one render |
| `footer` | string | `"Powered by AstrBot"` | Footer text shown at the bottom of rendered images; empty hides it |
| `llm_only` | bool | `true` | Only render LLM responses; command outputs such as `/help` are skipped |

## Command

| Command | Description |
|---------|-------------|
| `/md_theme <light\|dark>` | Update the configured rendering theme |

## Development

### Rebuilding JS Assets

The `dist/` directory contains pre-built JS/CSS assets. To rebuild after modifying JS dependencies:

```bash
cd data/plugins/astrbot_plugin_markdown
npm install
npm run build
```

`package-lock.json` is committed for reproducible builds. Node.js is only needed when rebuilding assets.

### Running Test

```bash
cd <AstrBot root>
uv run pytest data/plugins/astrbot_plugin_markdown/tests/ -v
```

## License

See [LICENSE](LICENSE).
