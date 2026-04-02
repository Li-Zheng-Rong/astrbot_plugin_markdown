/**
 * Build script: bundles markdown-it + @vscode/markdown-it-katex + highlight.js
 * into a single browser-ready bundle in dist/.
 *
 * Usage: npm run build
 */

import { build } from "esbuild";
import { cpSync, mkdirSync, existsSync } from "fs";
import { resolve, dirname } from "path";
import { fileURLToPath } from "url";

const __dirname = dirname(fileURLToPath(import.meta.url));
const distDir = resolve(__dirname, "dist");

// Ensure dist directory exists
mkdirSync(distDir, { recursive: true });
mkdirSync(resolve(distDir, "fonts"), { recursive: true });

// 1. Bundle JS: markdown-it + katex plugin + highlight.js
await build({
  entryPoints: [resolve(__dirname, "src", "entry.js")],
  bundle: true,
  outfile: resolve(distDir, "bundle.js"),
  format: "iife",
  globalName: "MarkdownBundle",
  platform: "browser",
  target: ["chrome100"],
  minify: true,
  sourcemap: false,
});

console.log("✅ JS bundle built: dist/bundle.js");

// 2. Copy KaTeX CSS and fonts
const katexDist = resolve(__dirname, "node_modules", "katex", "dist");
if (existsSync(katexDist)) {
  cpSync(resolve(katexDist, "katex.min.css"), resolve(distDir, "katex.min.css"));
  cpSync(resolve(katexDist, "fonts"), resolve(distDir, "fonts"), { recursive: true });
  console.log("✅ KaTeX CSS + fonts copied");
} else {
  console.warn("⚠️  katex not found in node_modules — KaTeX CSS/fonts not copied");
}

// 3. Copy highlight.js theme
const hljsStyles = resolve(
  __dirname,
  "node_modules",
  "highlight.js",
  "styles"
);
if (existsSync(hljsStyles)) {
  cpSync(
    resolve(hljsStyles, "github.min.css"),
    resolve(distDir, "hljs-github-light.css")
  );
  cpSync(
    resolve(hljsStyles, "github-dark.min.css"),
    resolve(distDir, "hljs-github-dark.css")
  );
  console.log("✅ highlight.js themes copied");
} else {
  console.warn("⚠️  highlight.js styles not found");
}

console.log("🎉 Build complete!");
