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
    html: true,
    linkify: true,
    typographer: false,
    highlight(str, lang) {
      if (lang && hljs.getLanguage(lang)) {
        try {
          return (
            '<pre class="hljs"><code>' +
            hljs.highlight(str, { language: lang, ignoreIllegals: true }).value +
            "</code></pre>"
          );
        } catch (_) {
          /* fall through */
        }
      }
      return (
        '<pre class="hljs"><code>' + md.utils.escapeHtml(str) + "</code></pre>"
      );
    },
    ...options,
  });

  md.use(katexPlugin, {
    throwOnError: false,
    output: "htmlAndMathml",
  });

  return md;
}

// Export for global access
export { createRenderer, hljs };
