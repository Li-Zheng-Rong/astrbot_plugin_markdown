/**
 * Browser entry point: exposes markdown-it + katex + highlight.js
 * as a global `MarkdownBundle` object for use in render.html.
 */

import markdownit from "markdown-it";
import katexPlugin from "@vscode/markdown-it-katex";
import subPlugin from "markdown-it-sub";
import supPlugin from "markdown-it-sup";
import markPlugin from "markdown-it-mark";
import footnotePlugin from "markdown-it-footnote";
import hljs from "highlight.js";

/**
 * Create a configured markdown-it instance.
 *
 * All options use safe defaults when omitted.  Dangerous options
 * ({@code html}, {@code trust}) must be set to {@code true} explicitly.
 *
 * @param {object} [options]                          Grouped engine options
 * @param {object} [options.markdownIt]               markdown-it core options
 * @param {boolean} [options.markdownIt.html=false]   Allow raw HTML tags
 * @param {boolean} [options.markdownIt.linkify=true] Auto-link plain URLs
 * @param {boolean} [options.markdownIt.typographer=true] Typographic replacements
 * @param {string}  [options.markdownIt.quotes="\"\"''"]  Quote characters
 * @param {object} [options.katex]                    KaTeX plugin options
 * @param {boolean} [options.katex.throwOnError=false] Throw on parse errors
 * @param {string}  [options.katex.output="htmlAndMathml"] Output format
 * @param {boolean} [options.katex.trust=false]       Allow unsafe commands
 * @param {object} [options.highlight]                highlight.js options
 * @param {boolean} [options.highlight.ignoreIllegals=true] Tolerate syntax errors
 * @returns {object} markdown-it instance
 */
function createRenderer(options = {}) {
  const mdOpts = options.markdownIt || {};
  const katexOpts = options.katex || {};
  const hljsOpts = options.highlight || {};

  const ignoreIllegals = hljsOpts.ignoreIllegals !== false;

  const md = markdownit({
    html: mdOpts.html === true,
    linkify: mdOpts.linkify !== false,
    typographer: mdOpts.typographer !== false,
    quotes: mdOpts.quotes || "\"\"''",
    highlight(str, lang) {
      const language = lang && hljs.getLanguage(lang) ? lang : null;
      const codeClass = language
        ? `hljs language-${language}`
        : "hljs language-plaintext";

      if (language) {
        try {
          return (
            `<pre class="${codeClass}"><code>` +
            hljs.highlight(str, { language, ignoreIllegals }).value +
            "</code></pre>"
          );
        } catch (_) {
          /* fall through */
        }
      }
      return (
        `<pre class="${codeClass}"><code>` +
        md.utils.escapeHtml(str) +
        "</code></pre>"
      );
    },
  });

  md.use(katexPlugin, {
    throwOnError: katexOpts.throwOnError === true,
    output: katexOpts.output || "htmlAndMathml",
    trust: katexOpts.trust === true,
  });

  md.use(subPlugin);
  md.use(supPlugin);
  md.use(markPlugin);
  md.use(footnotePlugin);

  return md;
}

// Export for global access
export { createRenderer, hljs };
