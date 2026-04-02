# astrbot_plugin_markdown

A markdown-to-image rendering plugin for [AstrBot](https://github.com/AstrBotDevs/AstrBot).
It converts LLM responses containing markdown into high-quality PNG screenshots
using a headless Chromium browser powered by
[Playwright](https://playwright.dev/python/).

The rendering pipeline is built on the same libraries used by Visual Studio Code:
[markdown-it](https://github.com/markdown-it/markdown-it) for markdown parsing,
[@vscode/markdown-it-katex](https://github.com/microsoft/vscode-markdown-it-katex)
for LaTeX math, and [highlight.js](https://highlightjs.org/) for syntax
highlighting.

## Features

- Fenced code blocks with syntax highlighting for 190+ languages.
- Inline and display LaTeX math via KaTeX (`$...$` and `$$...$$`).
- Full CommonMark support: headings, tables, lists, blockquotes, links, images,
  horizontal rules.
- Light and dark themes with GitHub-inspired styling.
- Typographic substitutions: `(tm)` → ™, `(c)` → ©, `--` → –, `---` → —.
- All rendering-engine options (markdown-it, KaTeX, highlight.js) exposed as
  plugin settings and applied at runtime without restart.
- Smart triggering based on markdown pattern scoring and minimum text length.
- Coexistence with AstrBot's built-in text-to-image pipeline.

## Requirements

| Component  | Version   | Purpose                                               |
|------------|-----------|-------------------------------------------------------|
| AstrBot    | ≥ 4.0.0   | Host framework                                        |
| Python     | ≥ 3.10    | Plugin runtime                                        |
| Playwright | ≥ 1.40.0  | Headless browser automation (from `requirements.txt`) |
| Chromium   | —         | Browser binary managed by Playwright                  |

Node.js is required **only** for rebuilding the frontend assets in `dist/`.

## Installation

1. Clone or copy this plugin into `data/plugins/astrbot_plugin_markdown`.
2. Start AstrBot. The plugin manager installs dependencies from
   `requirements.txt` automatically. To install them manually:
   ```bash
   pip install -r data/plugins/astrbot_plugin_markdown/requirements.txt
   ```
3. Install the Chromium browser binary:
   ```bash
   playwright install chromium
   ```
4. Restart AstrBot to load the plugin.

If the Chromium binary is not found at runtime, the plugin logs a warning and
passes the message through unmodified.

## Architecture

```
on_decorating_result (priority 10)
│
├─ Read plugin configuration
├─ Check preconditions: enabled, playwright available, llm_only filter
├─ Collect leading Plain text components from the result chain
├─ Evaluate markdown score and character length thresholds
│
├─ renderer.py
│   ├─ Lazy-initialize Playwright browser on first render
│   ├─ Load templates/render.html with bundled JS/CSS from dist/
│   ├─ page.evaluate("renderMarkdown(text, options)")
│   │   └─ options includes theme, fontSize, footer, and engine config
│   ├─ Screenshot #content element → PNG bytes
│   └─ Reuse browser page across renders; reload every 200 renders
│
├─ Replace leading Plain components with Image
└─ Set result.use_t2i_ = False to suppress built-in t2i
```

## Configuration

All settings are read from the AstrBot dashboard. The schema is defined in
`_conf_schema.json`.

### Plugin behavior

| Key               | Type   | Default                | Description                                                       |
|-------------------|--------|------------------------|-------------------------------------------------------------------|
| `enabled`         | bool   | `true`                 | Master switch for the plugin                                      |
| `llm_only`        | bool   | `true`                 | Only process LLM responses; skip command outputs such as `/help`  |
| `char_threshold`  | int    | `100`                  | Minimum text length in characters to consider rendering           |
| `score_threshold` | int    | `2`                    | Minimum markdown pattern score to trigger rendering               |
| `width`           | int    | `800`                  | Viewport and image width in pixels                                |
| `theme`           | string | `"light"`              | Color theme: `light` or `dark`                                    |
| `font_size`       | int    | `16`                   | Base font size in pixels                                          |
| `render_timeout`  | int    | `10`                   | Maximum seconds to wait for a single render                       |
| `footer`          | string | `"Powered by AstrBot"` | Footer text at the bottom of each image; leave empty to hide      |

### Rendering engine

These settings control the bundled markdown-it, KaTeX, and highlight.js
libraries. They are forwarded to the browser page on every render call, so
changes take effect immediately without restarting the plugin.

| Key                     | Type   | Default            | Description                                                                                                |
|-------------------------|--------|--------------------|------------------------------------------------------------------------------------------------------------|
| `md_html`               | bool   | `false`            | **⚠️ Security risk.** Allow raw HTML tags in markdown. Enable only if all input sources are trusted.         |
| `md_linkify`            | bool   | `true`             | Automatically convert plain-text URLs into clickable links.                                                |
| `md_typographer`        | bool   | `true`             | Typographic replacements: `(tm)` → ™, `(c)` → ©, `--` → –, `---` → —.                                    |
| `md_quotes`             | string | `"\"\"''"`         | Quote characters for the typographer (4 chars). Default preserves ASCII straight quotes.                   |
| `katex_throw_on_error`  | bool   | `false`            | Throw on invalid LaTeX instead of rendering an error message inline.                                       |
| `katex_output`          | string | `"htmlAndMathml"`  | KaTeX output format: `html`, `mathml`, or `htmlAndMathml`.                                                 |
| `katex_trust`           | bool   | `false`            | **⚠️ Security risk.** Allow KaTeX commands that generate arbitrary HTML. Enable only if all input is trusted. |
| `hljs_ignore_illegals`  | bool   | `true`             | Continue highlighting even when code contains syntax errors for the declared language.                      |

## Commands

| Command                  | Description                             |
|--------------------------|-----------------------------------------|
| `/md_theme <light\|dark>` | Persistently change the rendering theme |

## Security considerations

Two settings carry explicit security warnings:

- **`md_html`** — When set to `true`, raw HTML embedded in markdown is rendered
  as-is. This enables script injection if the markdown source is untrusted.
  The default (`false`) escapes all HTML tags.
- **`katex_trust`** — When set to `true`, KaTeX allows commands such as
  `\href{javascript:...}{...}` that can produce arbitrary HTML. The default
  (`false`) blocks these commands.

Both settings default to their safe values. The plugin logs a one-time warning
when either is enabled.

## Development

### Directory structure

```
astrbot_plugin_markdown/
├── main.py                 Plugin entry point (Star subclass)
├── renderer.py             Playwright browser lifecycle and screenshot pipeline
├── markdown_detect.py      Regex-based markdown pattern scoring
├── _conf_schema.json       AstrBot configuration schema
├── metadata.yaml           Plugin metadata
├── requirements.txt        Python dependencies
├── templates/
│   └── render.html         HTML page loaded by Playwright
├── src/
│   └── entry.js            JS entry point (esbuild input)
├── dist/                   Pre-built browser assets (committed)
│   ├── bundle.js           markdown-it + KaTeX + highlight.js IIFE bundle
│   ├── style.css           Custom markdown styling
│   ├── katex.min.css       KaTeX stylesheet
│   ├── fonts/              KaTeX font files
│   ├── hljs-github-light.css
│   └── hljs-github-dark.css
├── package.json            JS dependency manifest
├── package-lock.json       JS dependency lockfile (committed)
├── build.mjs               esbuild build script
├── tests/
│   ├── test_markdown_detect.py
│   └── test_renderer.py
└── README.md
```

### Rebuilding frontend assets

After modifying `src/entry.js` or updating JS dependencies:

```bash
cd data/plugins/astrbot_plugin_markdown
npm install
npm run build
```

The build produces `dist/bundle.js` and copies CSS and font files from
`node_modules/`. Both `package-lock.json` and `dist/` are committed to ensure
reproducible builds and a zero-Node.js runtime requirement.

### Running tests

```bash
uv run pytest data/plugins/astrbot_plugin_markdown/tests/ -v
```

Tests require Playwright with Chromium installed. The detection tests are pure
Python and complete in under one second; the renderer integration tests launch a
headless browser and take approximately 40 seconds in total.

## License

See [LICENSE](LICENSE).
