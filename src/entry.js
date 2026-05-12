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
import DOMPurify from "dompurify";

function findUnescapedDelimiter(src, delimiter, start) {
  let match = start;
  while ((match = src.indexOf(delimiter, match)) !== -1) {
    let pos = match - 1;
    while (src[pos] === "\\") {
      pos -= 1;
    }

    if ((match - pos) % 2 === 1) {
      return match;
    }

    match += delimiter.length;
  }

  return -1;
}

function escapedMathDelimitersPlugin(md) {
  function inlineParenMath(state, silent) {
    if (state.src.slice(state.pos, state.pos + 2) !== "\\(") {
      return false;
    }

    const start = state.pos + 2;
    const match = findUnescapedDelimiter(state.src, "\\)", start);
    if (match === -1) {
      return false;
    }

    const content = state.src.slice(start, match);
    if (!content.trim()) {
      return false;
    }

    if (!silent) {
      const token = state.push("math_inline", "math", 0);
      token.markup = "\\(";
      token.content = content;
    }

    state.pos = match + 2;
    return true;
  }

  function inlineBracketMath(state, silent) {
    if (state.src.slice(state.pos, state.pos + 2) !== "\\[") {
      return false;
    }

    const start = state.pos + 2;
    const match = findUnescapedDelimiter(state.src, "\\]", start);
    if (match === -1) {
      return false;
    }

    const content = state.src.slice(start, match);
    if (!content.trim()) {
      return false;
    }

    if (!silent) {
      const token = state.push("math_block", "math", 0);
      token.block = true;
      token.markup = "\\[";
      token.content = content;
    }

    state.pos = match + 2;
    return true;
  }

  function blockBracketMath(state, start, end, silent) {
    let pos = state.bMarks[start] + state.tShift[start];
    let max = state.eMarks[start];

    if (pos + 2 > max || state.src.slice(pos, pos + 2) !== "\\[") {
      return false;
    }

    let firstLine = state.src.slice(pos + 2, max);
    let lastLine = "";
    let found = false;
    let next = start;

    const firstLineClose = findUnescapedDelimiter(firstLine, "\\]", 0);
    if (firstLineClose !== -1) {
      if (firstLine.slice(firstLineClose + 2).trim()) {
        return false;
      }
      firstLine = firstLine.slice(0, firstLineClose);
      found = true;
    }

    while (!found) {
      next += 1;
      if (next >= end) {
        return false;
      }

      pos = state.bMarks[next] + state.tShift[next];
      max = state.eMarks[next];

      if (pos < max && state.tShift[next] < state.blkIndent) {
        return false;
      }

      const line = state.src.slice(pos, max);
      const close = findUnescapedDelimiter(line, "\\]", 0);
      if (close !== -1) {
        if (line.slice(close + 2).trim()) {
          return false;
        }
        lastLine = line.slice(0, close);
        found = true;
      }
    }

    if (silent) {
      return true;
    }

    state.line = next + 1;

    const token = state.push("math_block", "math", 0);
    token.block = true;
    token.content =
      (firstLine && firstLine.trim() ? `${firstLine}\n` : "") +
      state.getLines(start + 1, next, state.tShift[start], true) +
      (lastLine && lastLine.trim() ? lastLine : "");
    token.map = [start, state.line];
    token.markup = "\\[";
    return true;
  }

  md.inline.ruler.before("escape", "math_inline_paren", inlineParenMath);
  md.inline.ruler.before("escape", "math_inline_bracket", inlineBracketMath);
  md.block.ruler.after("blockquote", "math_block_bracket", blockBracketMath, {
    alt: ["paragraph", "reference", "blockquote", "list"],
  });
}

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
 * @param {boolean} [options.katex.enableEscapedDelimiters=true] Support \(...\) and \[...\]
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

  if (katexOpts.enableEscapedDelimiters !== false) {
    md.use(escapedMathDelimitersPlugin);
  }
  md.use(subPlugin);
  md.use(supPlugin);
  md.use(markPlugin);
  md.use(footnotePlugin);

  return md;
}

/**
 * Sanitize HTML produced by markdown-it to prevent XSS.
 *
 * Allows standard HTML formatting and MathML (required by KaTeX)
 * while stripping scripts, event handlers, and dangerous URIs.
 *
 * @param {string} html - Raw HTML string from md.render()
 * @returns {string} Sanitized HTML safe for innerHTML assignment
 */
function sanitizeHtml(html) {
  return DOMPurify.sanitize(html, {
    USE_PROFILES: { html: true, mathMl: true, svg: true, svgFilters: false },
    FORBID_TAGS: [
      "form",
      "input",
      "textarea",
      "select",
      "button",
      "style",
      "iframe",
      "object",
      "embed",
      "link",
      "base",
      "meta",
      "foreignObject",
    ],
  });
}

// Export for global access
export { createRenderer, hljs, sanitizeHtml };
