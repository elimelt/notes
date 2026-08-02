// Shared extraction + cleanup helpers for TTS evals, mirroring the reader's
// textOf/cleanTex/needsRewrite. collectBlocks returns whole blocks (paragraphs),
// which is the unit for the per-block rewrite design (LLM sees a full block; TTS
// chunking happens on the naturalized result afterward).
import { fromHtml } from "hast-util-from-html"
import { readFileSync } from "node:fs"
import { execSync } from "node:child_process"

const SKIP = new Set(["pre", "code", "figure", "table", "svg"])
const SKIP_CLASS = ["jupyter-notebook-embedded", "notebook-link-unavailable", "footnotes"]
const BLOCKS = new Set(["p", "li", "dt", "dd", "h1", "h2", "h3", "h4", "h5", "h6"])
export const norm = t => t.replace(/\s+/g, " ").trim()
const cls = n => (n.properties && [].concat(n.properties.className || [])) || []
const hasClass = (n, c) => cls(n).includes(c)
const isSkip = n => (n.tagName && SKIP.has(n.tagName)) || SKIP_CLASS.some(c => hasClass(n, c)) ||
  (n.tagName === "sup" && hasClass(n, "footnote-ref"))
const textOf = node => {
  let out = ""
  for (const n of node.children || []) {
    if (n.type === "text") out += n.value
    else if (n.type === "element") {
      if (isSkip(n)) continue
      if (hasClass(n, "katex")) { const tex = n.properties && n.properties.dataTex; out += tex ? " \\(" + tex + "\\) " : " " + textOf(n) + " " }
      else out += textOf(n)
    }
  }
  return out
}
export const cleanTex = t => t
  .replace(/[\u2018\u2019]/g, "'").replace(/[\u201c\u201d]/g, '"')
  .replace(/[\u2013\u2014]/g, "-").replace(/\u2026/g, "...")
  .replace(/\\(?:text|mathrm|mathbf|mathit|mathsf|mathtt|mathcal|operatorname|textbf|textit|mbox)\s*\{([^{}]*)\}/g, "$1")
  .replace(/\\left\s*|\\right\s*/g, "")
  .replace(/\\(?:quad|qquad|;|:|,|!)(?![A-Za-z])/g, " ")
  .replace(/\\lbrack/g, "[").replace(/\\rbrack/g, "]")
  .replace(/\s+/g, " ").trim()

export const needsRewrite = t =>
  /\\\(/.test(t) || /[_^{}\\|~]/.test(t) ||
  /[A-Za-z0-9]\s*[=<>]=?\s*[A-Za-z0-9\-]/.test(t) ||
  /[A-Za-z]\([^)]*[,\s][^)]*\)|[A-Za-z]\([a-z]\)|\bO\([^)]*\)/.test(t) ||
  /\d\s*[+*×÷]\s*\d|\d\s*\/\s*\d/.test(t) ||
  /[A-Za-z]_[A-Za-z0-9]|[A-Za-z0-9]\^[A-Za-z0-9]/.test(t) ||
  /\b[a-z][a-zA-Z0-9]*[._][a-z][a-zA-Z0-9]/.test(t)

let article = null
const findArticle = n => { if (article) return; if (n.type === "element" && n.tagName === "article") { article = n; return } for (const c of n.children || []) findArticle(c) }
const collect = (n, acc) => { if (n.type === "element" && (BLOCKS.has(n.tagName) || hasClass(n, "katex-display"))) { acc.push(n); return } for (const c of n.children || []) collect(c, acc) }

// Return whole cleaned blocks (paragraph units) across the built site.
export const collectBlocks = ({ maxFiles = 120 } = {}) => {
  const root = process.cwd().replace(/\.quartz$/, "")
  const files = execSync("grep -rl 'data-tex=' public --include='*.html'", { cwd: root, encoding: "utf8" })
    .trim().split("\n").slice(0, maxFiles)
  const blocks = []
  for (const f of files) {
    article = null
    findArticle(fromHtml(readFileSync(root + "/" + f, "utf8")))
    if (!article) continue
    const els = []; collect(article, els)
    for (const b of els) { const t = cleanTex(norm(textOf(b))); if (t) blocks.push(t) }
  }
  return { files, blocks }
}
