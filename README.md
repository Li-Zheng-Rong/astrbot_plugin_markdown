# astrbot_plugin_markdown

High-quality markdown-to-image rendering plugin for [AstrBot](https://github.com/AstrBotDevs/AstrBot), powered by markdown-it, [@vscode/markdown-it-katex](https://github.com/microsoft/vscode-markdown-it-katex), [highlight.js](https://highlightjs.org/), and Playwright Chromium.

## Features

- **Rich markdown rendering** - Headers, tables, lists, blockquotes, links, inline code, fenced code blocks, and horizontal rules
- **Syntax highlighting** - highlight.js renders code blocks with GitHub-style themes
- **Math support** - Inline and display LaTeX via KaTeX
- **Light and dark themes** - Switch at runtime with `/md_theme light` or `/md_theme dark`
- **Smart triggering** - Renders only when markdown score and text length exceed configured thresholds
- **LLM-only by default** - Skips non-LLM outputs such as command/help responses unless `llm_only` is disabled
- **Safer HTML handling** - Raw HTML is escaped instead of being injected into the preview page
- **Typographic substitutions** - `(tm)`, `(c)`, and dash-style substitutions are enabled while plain quotes stay literal
- **Built-in t2i friendly** - If this plugin skips rendering, AstrBot's built-in text-to-image path can still run
- **Prebuilt frontend assets** - `dist/` is committed, so end users do not need Node.js

## How it works

1. `@filter.on_decorating_result(priority=10)` intercepts outgoing results before AstrBot's built-in t2i step.
2. The plugin collects leading `Plain` text components and checks `llm_only`, markdown score, and minimum length.
3. `renderer.py` reuses a persistent Playwright page that loads `templates/render.html` plus bundled assets from `dist/`.
4. On success, the plugin replaces the leading text with a PNG image and sets `result.use_t2i_ = False`.

## Requirements

- AstrBot >= 4.0.0
- Python 3.10+
- `playwright` Python package (installed from `requirements.txt`)
- Chromium for Playwright (`playwright install chromium`)

## Installation

1. Place this plugin under `data\plugins\astrbot_plugin_markdown`.
2. Start AstrBot once so plugin dependencies from `requirements.txt` are installed, or install them manually:
   ```bash
   pip install -r requirements.txt
   ```
3. Install the Playwright Chromium browser:
   ```bash
   playwright install chromium
   ```
4. Restart AstrBot.

If Chromium is missing, the plugin logs a warning and leaves the original text untouched.

## Configuration

All settings are configurable from the AstrBot dashboard via `_conf_schema.json`.

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

## Rendering engine defaults

These defaults live in `src\entry.js` and are bundled into `dist\bundle.js`.

| Layer | Setting | Value | Recommendation |
|---------|------|---------|-------------|
| `markdown-it` | `html` | `false` | Keep disabled for untrusted LLM/user content so raw HTML is shown as text instead of being injected |
| `markdown-it` | `linkify` | `true` | Keep enabled so plain URLs become clickable links in the rendered preview |
| `markdown-it` | `typographer` | `true` | Enable to support `(tm)`, `(c)`, and dash substitutions in normal prose |
| `markdown-it` | `quotes` | `"\"\"''"` | Keep straight quotes literal while still benefiting from other typographer replacements |
| `KaTeX` | `throwOnError` | `false` | Keep disabled so malformed math degrades gracefully instead of aborting the whole render |
| `KaTeX` | `output` | `"htmlAndMathml"` | Keep enabled for better accessibility and copy/paste behavior |
| `KaTeX` | `trust` | `false` | Keep disabled so unsafe HTML/URL-style KaTeX commands are not executed |
| `highlight.js` | `ignoreIllegals` | `true` | Keep enabled so partially invalid code fences do not break rendering |
| `highlight.js` | auto-detect | disabled | Keep disabled for deterministic output and lower render latency |
| `highlight.js` | language CSS class | enabled | Keep enabled so theme/style overrides can target the rendered code language when needed |

## Command

| Command | Description |
|---------|-------------|
| `/md_theme <light\|dark>` | Update the configured rendering theme |

## Development

### Rebuilding frontend assets

The browser-side source lives in `src\`. Rebuild committed assets in `dist\` with:

```bash
cd data/plugins/astrbot_plugin_markdown
npm install
npm run build
```

`package-lock.json` is committed for reproducible builds. Node.js is only needed when rebuilding assets.

### Running tests

```bash
cd <AstrBot root>
uv run pytest data/plugins/astrbot_plugin_markdown/tests/ -v
```

## License

See [LICENSE](LICENSE).
