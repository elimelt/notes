// Inspect the ACTUAL model inputs the TTS reader produces, by replicating its
// extraction logic (textOf/chunkText/needsRewrite) over real built pages.
import { fromHtml } from "hast-util-from-html"
import { readFileSync } from "node:fs"
import { execSync } from "node:child_process"

const TARGET = 260, MAX = 500
const SKIP = new Set(["pre", "code", "figure", "table", "svg"])
const SKIP_CLASS = ["jupyter-notebook-embedded", "notebook-link-unavailable", "footnotes"]
const BLOCKS = new Set(["p", "li", "dt", "dd", "h1", "h2", "h3", "h4", "h5", "h6"])
const norm = t => t.replace(/\s+/g, " ").trim()
const cls = n => (n.properties && [].concat(n.properties.className || [])) || []
const hasClass = (n, c) => cls(n).includes(c)
const isKatex = n => hasClass(n, "katex")
const isSkip = n =>
  (n.tagName && SKIP.has(n.tagName)) ||
  SKIP_CLASS.some(c => hasClass(n, c)) ||
  (n.tagName === "sup" && hasClass(n, "footnote-ref"))

const textOf = node => {
  let out = ""
  for (const n of node.children || []) {
    if (n.type === "text") out += n.value
    else if (n.type === "element") {
      if (isSkip(n)) continue
      if (isKatex(n)) {
        const tex = n.properties && n.properties.dataTex
        out += tex ? " \\(" + tex + "\\) " : " " + textOf(n) + " "
      } else out += textOf(n)
    }
  }
  return out
}

const sentences = t => t.match(/[^.!?]+[.!?]+(?:["')\]]+)?\s*|[^.!?]+$/g) || [t]
const splitLong = s => {
  const parts = s.match(/\\\([^]*?\\\)|[^]+?(?=\\\(|$)/g) || [s]
  const out = []; let buf = ""
  for (const p of parts) {
    if (p.startsWith("\\(")) { if (buf) { out.push(buf.trim()); buf = "" } out.push(p.trim()) }
    else for (const w of p.split(/(\s+)/)) {
      if ((buf + w).length > MAX && buf) { out.push(buf.trim()); buf = w } else buf += w
    }
  }
  if (buf.trim()) out.push(buf.trim())
  return out.filter(Boolean)
}
const chunkText = t => {
  const out = []; let buf = ""
  for (const s of sentences(t)) {
    if (s.length > MAX) { if (buf) { out.push(buf.trim()); buf = "" } for (const p of splitLong(s)) out.push(p); continue }
    if ((buf + s).length > TARGET && buf) { out.push(buf.trim()); buf = s } else buf += s
  }
  if (buf.trim()) out.push(buf.trim())
  return out.filter(Boolean)
}
const needsRewrite = t =>
  /\\\(/.test(t) ||
  /[_^{}\\|~]/.test(t) ||
  /[A-Za-z0-9]\s*[=<>]=?\s*[A-Za-z0-9\-]/.test(t) ||
  /[A-Za-z]\([^)]*[,\s][^)]*\)|[A-Za-z]\([a-z]\)|\bO\([^)]*\)/.test(t) ||
  /\d\s*[+*×÷]\s*\d|\d\s*\/\s*\d/.test(t) ||
  /[A-Za-z]_[A-Za-z0-9]|[A-Za-z0-9]\^[A-Za-z0-9]/.test(t) ||
  /\b[a-z][a-zA-Z0-9]*[._][a-z][a-zA-Z0-9]/.test(t)

// find <article> subtree
let article = null
const findArticle = n => {
  if (article) return
  if (n.type === "element" && n.tagName === "article") { article = n; return }
  for (const c of n.children || []) findArticle(c)
}
const collectBlocks = (n, acc) => {
  if (n.type === "element" && BLOCKS.has(n.tagName)) { acc.push(n); return } // top-level block only
  for (const c of n.children || []) collectBlocks(c, acc)
}

const files = execSync("grep -rl 'data-tex=' public --include='*.html'", { cwd: process.cwd().replace(/\.quartz$/, ""), encoding: "utf8" })
  .trim().split("\n").slice(0, Number(process.argv[2] || 40))
const root = process.cwd().replace(/\.quartz$/, "")

const all = []
for (const f of files) {
  article = null
  const tree = fromHtml(readFileSync(root + "/" + f, "utf8"))
  findArticle(tree)
  if (!article) continue
  const blocks = []; collectBlocks(article, blocks)
  for (const b of blocks) {
    const text = norm(textOf(b))
    if (text) for (const c of chunkText(text)) all.push(c)
  }
}

const llm = all.filter(needsRewrite)
const lens = llm.map(c => c.length).sort((a, b) => a - b)
const pct = p => lens[Math.floor((lens.length - 1) * p)] || 0
// correctness checks against the tightened gate
const withMath = all.filter(c => c.includes("\\("))
const mathMissed = withMath.filter(c => !needsRewrite(c))
const noMathButLLM = llm.filter(c => !c.includes("\\("))
console.log("pages inspected:", files.length)
console.log("total chunks:", all.length)
console.log("LLM chunks (needsRewrite):", llm.length, "(" + Math.round(100 * llm.length / all.length) + "%)")
console.log("verbatim chunks:", all.length - llm.length)
console.log("FALSE NEGATIVES (has \\( but gate says no):", mathMissed.length)
console.log("no-math chunks still routed to LLM (candidate FPs):", noMathButLLM.length)
console.log("LLM chunk length p50/p90/p99/max:", pct(0.5), pct(0.9), pct(0.99), lens[lens.length - 1])
console.log("LLM chunks with \\(:", llm.filter(c => c.includes("\\(")).length)
console.log("\n=== sample LLM inputs (longest 8) ===")
for (const c of [...llm].sort((a, b) => b.length - a.length).slice(0, 8)) console.log("[" + c.length + "] " + c.slice(0, 200))
console.log("\n=== remaining no-math chunks routed to LLM (up to 20) ===")
for (const c of noMathButLLM.slice(0, 20)) console.log("  " + c.slice(0, 120))
console.log("\n=== dup analysis ===")
const counts = new Map(); for (const c of llm) counts.set(c, (counts.get(c) || 0) + 1)
const dups = [...counts.entries()].filter(([, n]) => n > 1)
console.log("unique LLM inputs:", counts.size, "of", llm.length, "| repeated inputs:", dups.length)
