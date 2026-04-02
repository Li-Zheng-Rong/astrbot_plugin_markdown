/**
 * Browser entry point: exposes markdown-it + katex + highlight.js
 * as a global `MarkdownBundle` object for use in render.html.
 */

import markdownit from "markdown-it";
import katexPlugin from "@vscode/markdown-it-katex";
import hljs from "highlight.js";

/**
 * Create a configured markdown-it instance.
 * @param {object} [options] - Override options
 * @returns {object} markdown-it instance
 */
function createRenderer(options = {}) {
  const md = markdownit({
    // Render untrusted markdown safely: allow markdown syntax, not raw HTML.
    html: false,
    linkify: true,
    typographer: true,
    quotes: "\"\"''",
    highlight(str, lang) {
      const language = lang && hljs.getLanguage(lang) ? lang : null;
      const codeClass = language
        ? `hljs language-${language}`
        : "hljs language-plaintext";

      if (language) {
        try {
          return (
            `<pre class="${codeClass}"><code>` +
            hljs.highlight(str, { language, ignoreIllegals: true }).value +
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
    ...options,
  });

  md.use(katexPlugin, {
    throwOnError: false,
    output: "htmlAndMathml",
    trust: false,
  });

  return md;
}

// Export for global access
export { createRenderer, hljs };
