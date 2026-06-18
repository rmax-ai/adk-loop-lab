import path from "node:path";

const docLayoutPath = path.resolve("./src/lib/components/DocLayout.svelte");

export default {
  extensions: [".svx", ".md"],
  smartypants: { dashes: "oldschool" },
  layout: {
    _: docLayoutPath
  },
  highlight: {
    highlighter: async (code, lang) => {
      return `<pre><code class="language-${lang || "text"}">${escapeHtml(code)}</code></pre>`;
    }
  }
};

function escapeHtml(text) {
  return text.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
}
