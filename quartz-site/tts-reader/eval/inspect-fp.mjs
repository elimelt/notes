// Which needsRewrite branch fires on chunks that contain NO real math/code?
// This surfaces false positives (prose needlessly sent to the LLM).
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
const isSkip = n => (n.tagName && SKIP.has(n.tagName)) || SKIP_CLASS.some(c => hasClass(n, c)) || (n.tagName === "sup" && hasClass(n, "footnote-ref"))
const textOf = node => {
  let out = ""
  for (const n of node.children || []) {
    if (n.type === "text") out += n.value
    else if (n.type === "element") {
      if (isSkip(n)) continue
      if (isKatex(n)) { const tex = n.properties && n.properties.dataTex; out += tex ? " \\(" + tex + "\\) " : " " + textOf(n) + " " }
      else out += textOf(n)
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
    else for (const w of p.split(/(\s+)/)) { if ((buf + w).length > MAX && buf) { out.push(buf.trim()); buf = w } else buf += w }
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
const branches = {
  math: t => /\\\(/.test(t),
  symbols: t => /[_^{}\\=<>|~#$%*/]/.test(t),
  call: t => /[A-Za-z]\([^)]*\)/.test(t),
  arith: t => /\d[.,]?\d*\s*[+\-*/=xX]\s*\d/.test(t),
  ident: t => /\b[A-Za-z]{2,}[._][A-Za-z0-9]/.test(t),
}
let article = null
const findArticle = n => { if (article) return; if (n.type === "element" && n.tagName === "article") { article = n; return } for (const c of n.children || []) findArticle(c) }
const collectBlocks = (n, acc) => { if (n.type === "element" && BLOCKS.has(n.tagName)) { acc.push(n); return } for (const c of n.children || []) collectBlocks(c, acc) }

const root = process.cwd().replace(/\.quartz$/, "")
const files = execSync("grep -rl 'data-tex=' public --include='*.html'", { cwd: root, encoding: "utf8" }).trim().split("\n").slice(0, Number(process.argv[2] || 60))
const all = []
for (const f of files) {
  article = null
  findArticle(fromHtml(readFileSync(root + "/" + f, "utf8")))
  if (!article) continue
  const blocks = []; collectBlocks(article, blocks)
  for (const b of blocks) { const text = norm(textOf(b)); if (text) for (const c of chunkText(text)) all.push(c) }
}
// false positive = flagged by a NON-math branch but has no \( and no obvious code
const tally = {}
const fps = []
for (const c of all) {
  if (branches.math(c)) continue
  const fired = Object.keys(branches).filter(k => k !== "math" && branches[k](c))
  if (!fired.length) continue
  for (const k of fired) tally[k] = (tally[k] || 0) + 1
  fps.push({ c, fired })
}
console.log("no-math chunks flagged for LLM:", fps.length)
console.log("branch tallies:", JSON.stringify(tally))
console.log("\n=== sample false positives per branch ===")
for (const k of ["symbols", "call", "arith", "ident"]) {
  const ex = fps.filter(x => x.fired.includes(k)).slice(0, 3)
  console.log("\n-- " + k + " --")
  for (const { c } of ex) console.log("  " + c.slice(0, 160))
}
