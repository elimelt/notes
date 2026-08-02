// End-to-end timeline of the TTS reader pipeline on one real note.
// Faithfully replays the shipped component: same chunking (TARGET/MAX/
// FIRST_TARGET), same needsRewrite gate, same model+prompt, same prefetch
// queue (LOOKAHEAD, CONCURRENCY, single-worker priority until the needed
// chunk lands), then simulates playback using real mp3 durations (ffprobe)
// to find stalls (buffer underruns) and time-to-first-audio.
// Usage: node timeline.mjs <built-html-path-relative-to-repo-root> [maxChunks]
import { readFileSync, writeFileSync, mkdtempSync } from "node:fs"
import { execFileSync } from "node:child_process"
import { tmpdir } from "node:os"
import { join } from "node:path"
import { fromHtml } from "hast-util-from-html"
import { norm, cleanTex, needsRewrite } from "./tts-extract.mjs"
import { S3 } from "./prompts.mjs"

const TTS_API = "https://transcribe.elimelt.com"
const TTS_MODEL = "speaches-ai/Kokoro-82M-v1.0-ONNX"
const VOICE = "af_heart"
const LLM_API = "https://llm.elimelt.com"
const LLM_MODEL = process.env.LLM_MODEL || "qwen2.5-coder:7b"
const URGENT_BUFFER_S = Number(process.env.URGENT_BUFFER_S ?? 10)
const CHARS_PER_SECOND = 15
const TARGET = 260, MAX = 500, FIRST_TARGET = 120
const LOOKAHEAD = 6, CONCURRENCY = 2

const FILE = process.argv[2] || "public/algorithms/stable-matching.html"
const MAX_CHUNKS = Number(process.argv[3] || 24)

// --- extraction + chunking, mirroring components.js ---
const SKIP = new Set(["pre", "code", "figure", "table", "svg"])
const SKIP_CLASS = ["jupyter-notebook-embedded", "notebook-link-unavailable", "footnotes"]
const BLOCK_TAGS = new Set(["p", "li", "dt", "dd", "h1", "h2", "h3", "h4", "h5", "h6"])
const cls = n => (n.properties && [].concat(n.properties.className || [])) || []
const isSkip = n => (n.tagName && SKIP.has(n.tagName)) || SKIP_CLASS.some(c => cls(n).includes(c)) ||
  (n.tagName === "sup" && cls(n).includes("footnote-ref"))
const textOf = node => {
  let out = ""
  for (const n of node.children || []) {
    if (n.type === "text") out += n.value
    else if (n.type === "element") {
      if (isSkip(n)) continue
      if (cls(n).includes("katex")) { const tex = n.properties && n.properties.dataTex; out += tex ? " \\(" + tex + "\\) " : " " + textOf(n) + " " }
      else out += textOf(n)
    }
  }
  return out
}
const sentences = t => {
  const spans = []
  const masked = t.replace(/\\\([^]*?\\\)/g, m => { spans.push(m); return "\u0001" + (spans.length - 1) + "\u0002" })
  const dot = masked.replace(/(\d)\.(\d)/g, "$1\u0003$2")
  const parts = dot.match(/[^.!?]+[.!?]+(?:["')\]]+)?\s*|[^.!?]+$/g) || [dot]
  return parts.map(p => p.replace(/\u0003/g, ".").replace(/\u0001(\d+)\u0002/g, (_, i) => spans[Number(i)]))
}
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
const chunkText = (t, firstTarget) => {
  const out = []; let buf = ""
  const target = () => (firstTarget && out.length === 0 ? firstTarget : TARGET)
  for (const s of sentences(t)) {
    if (s.length > MAX) { if (buf) { out.push(buf.trim()); buf = "" } for (const p of splitLong(s)) out.push(p); continue }
    if ((buf + s).length > target() && buf) { out.push(buf.trim()); buf = s } else buf += s
  }
  if (buf.trim()) out.push(buf.trim())
  return out.filter(Boolean)
}
let article = null
const findArticle = n => { if (article) return; if (n.type === "element" && n.tagName === "article") { article = n; return } for (const c of n.children || []) findArticle(c) }
const collectEls = (n, acc) => { if (n.type === "element" && (BLOCK_TAGS.has(n.tagName) || cls(n).includes("katex-display"))) { acc.push(n); return } for (const c of n.children || []) collectEls(c, acc) }

const root = process.cwd().replace(/\.quartz$/, "")
article = null
findArticle(fromHtml(readFileSync(join(root, FILE), "utf8")))
if (!article) { console.error("no <article> in " + FILE); process.exit(1) }
const els = []; collectEls(article, els)
const chunks = []
for (const el of els) {
  const t = cleanTex(norm(textOf(el)))
  if (t) for (const c of chunkText(t, chunks.length === 0 ? FIRST_TARGET : 0)) chunks.push(c)
}
chunks.length = Math.min(chunks.length, MAX_CHUNKS)
console.log("note: " + FILE + " | chunks: " + chunks.length +
  " | needing LLM: " + chunks.filter(needsRewrite).length)

// --- pipeline with real requests + event log ---
const T0 = Date.now()
const ev = (i, kind, extra = "") =>
  console.log("  t=" + String(((Date.now() - T0) / 1000).toFixed(1)).padStart(6) + "s  #" +
    String(i).padStart(2) + "  " + kind + (extra ? "  " + extra : ""))
const tmp = mkdtempSync(join(tmpdir(), "tts-timeline-"))
const speakLeftovers = o => o.replace(/\$([^$]*)\$/g, "$1").replace(/\\\(|\\\)/g, "")
  .replace(/\\[a-zA-Z]+/g, m => m.slice(1)).replace(/\^\{([^{}]*)\}/g, " $1 ")
  .replace(/_\{([^{}]*)\}/g, (_, b) => " " + b.replace(/,/g, " ") + " ")
  .replace(/([A-Za-z0-9])\^([A-Za-z0-9]+)/g, "$1 $2")
  .replace(/([A-Za-z0-9])_([A-Za-z0-9,]+)/g, (_, a, b) => a + " " + b.replace(/,/g, " "))
  .replace(/[{}]/g, "").replace(/\s+/g, " ").trim()

const bufferedSecondsBefore = i => {
  let chars = 0
  for (let j = idx; j < i; j++) chars += chunks[j].length
  return chars / CHARS_PER_SECOND
}

let llmChain = Promise.resolve()
const llmSerial = fn => { const run = llmChain.then(fn, fn); llmChain = run.catch(() => {}); return run }

const synth = async i => {
  const text = chunks[i]
  let spoken = text, llmMs = 0
  if (needsRewrite(text)) {
    const urgent = bufferedSecondsBefore(i) < URGENT_BUFFER_S
    if (urgent) {
      // Shipped behavior: skip the LLM, speak the deterministic rendering now;
      // background quality rewrite omitted here (it only fills the cache).
      ev(i, "llm-skip", "[URGENT buf=" + bufferedSecondsBefore(i).toFixed(1) + "s] deterministic speakLeftovers")
      spoken = speakLeftovers(text)
    } else {
      const t = Date.now()
      const d = await llmSerial(async () => {
        const body = { model: LLM_MODEL, stream: false, options: { temperature: 0.2 },
          messages: [{ role: "system", content: S3 }, { role: "user", content: text }] }
        if (LLM_MODEL.startsWith("gemma4")) body.think = false
        if (LLM_MODEL.startsWith("gpt-oss")) body.think = "low"
        const r = await fetch(LLM_API + "/api/chat", { method: "POST", headers: { "Content-Type": "application/json" },
          body: JSON.stringify(body) })
        return r.json()
      })
      llmMs = Date.now() - t
      ev(i, "llm-metrics", "load=" + ((d.load_duration || 0) / 1e9).toFixed(1) + "s prompt=" + (d.prompt_eval_count || 0) +
        "tok/" + ((d.prompt_eval_duration || 0) / 1e9).toFixed(1) + "s decode=" + (d.eval_count || 0) + "tok@" +
        ((d.eval_count || 0) / (((d.eval_duration || 1)) / 1e9)).toFixed(1) + "t/s")
      const raw = norm((d.message && d.message.content) || "")
      spoken = !raw || raw.length > text.length * 2 + 40 ? text : speakLeftovers(raw)
    }
  }
  const t = Date.now()
  const r = await fetch(TTS_API + "/v1/audio/speech", { method: "POST", headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ model: TTS_MODEL, input: spoken, voice: VOICE, response_format: "mp3" }) })
  const buf = Buffer.from(await r.arrayBuffer())
  const ttsMs = Date.now() - t
  const f = join(tmp, i + ".mp3")
  writeFileSync(f, buf)
  const dur = Number(execFileSync("ffprobe", ["-v", "quiet", "-show_entries", "format=duration", "-of", "csv=p=0", f], { encoding: "utf8" }).trim())
  return { llmMs, ttsMs, dur }
}

// --- replay the component's queue: workers claim indexes, pool capped at 1
// while the chunk playback needs isn't ready, else CONCURRENCY. Playback is
// simulated: when chunk idx lands we "play" it for its real duration, then
// need idx+1. Stalls = time playback spent waiting on an unready chunk.
const ready = new Map()   // i -> { at, llmMs, ttsMs, dur }
const waiters = new Set()
const wake = () => { for (const w of [...waiters]) w() }
let next = 0, active = 0, idx = 0, doneAll = false
const worker = async () => {
  while (true) {
    while (next < chunks.length && ready.has(next)) next++
    if (next >= chunks.length || next > idx + LOOKAHEAD) return
    const i = next++
    ev(i, "start", JSON.stringify(chunks[i].slice(0, 50)) + (needsRewrite(chunks[i]) ? " [LLM]" : " [verbatim]"))
    const r = await synth(i)
    ready.set(i, { at: Date.now(), ...r })
    ev(i, "ready", "llm=" + (r.llmMs / 1000).toFixed(1) + "s tts=" + (r.ttsMs / 1000).toFixed(1) + "s audio=" + r.dur.toFixed(1) + "s")
    wake(); pump()
  }
}
const pump = () => {
  if (doneAll) return
  const limit = ready.has(idx) ? CONCURRENCY : 1
  const eligible = Math.min(chunks.length, idx + LOOKAHEAD + 1) - next
  const want = Math.min(limit - active, Math.max(0, eligible))
  for (let k = 0; k < want; k++) { active++; worker().finally(() => { active--; pump() }) }
}
const awaitChunk = i => ready.has(i) ? Promise.resolve() :
  new Promise(res => { const c = () => { if (ready.has(i)) { waiters.delete(c); res() } }; waiters.add(c); pump() })
const sleep = ms => new Promise(r => setTimeout(r, ms))

const stalls = []
let firstAudioAt = null
const play = async () => {
  for (idx = 0; idx < chunks.length; idx++) {
    pump()
    const waitStart = Date.now()
    await awaitChunk(idx)
    const waited = (Date.now() - waitStart) / 1000
    if (idx === 0) firstAudioAt = (Date.now() - T0) / 1000
    else if (waited > 0.05) { stalls.push({ i: idx, s: waited }); ev(idx, "STALL", waited.toFixed(1) + "s waiting") }
    const { dur } = ready.get(idx)
    ev(idx, "play", dur.toFixed(1) + "s")
    pump()
    await sleep(dur * 1000)
  }
  doneAll = true
}
await play()

// --- summary ---
const rs = [...ready.values()]
const llm = rs.filter(r => r.llmMs > 0).map(r => r.llmMs / 1000)
const tts = rs.map(r => r.ttsMs / 1000)
const audio = rs.reduce((a, r) => a + r.dur, 0)
const avg = a => a.length ? a.reduce((x, y) => x + y, 0) / a.length : 0
console.log("\n=== summary ===")
console.log("time-to-first-audio: " + firstAudioAt.toFixed(1) + "s")
console.log("stalls after start:  " + stalls.length + (stalls.length ? " (total " + stalls.reduce((a, s) => a + s.s, 0).toFixed(1) + "s): " + stalls.map(s => "#" + s.i + "=" + s.s.toFixed(1) + "s").join(" ") : ""))
console.log("llm: n=" + llm.length + " avg=" + avg(llm).toFixed(1) + "s max=" + (llm.length ? Math.max(...llm) : 0).toFixed(1) + "s")
console.log("tts: n=" + tts.length + " avg=" + avg(tts).toFixed(1) + "s max=" + Math.max(...tts).toFixed(1) + "s")
console.log("audio total: " + audio.toFixed(1) + "s | wall: " + ((Date.now() - T0) / 1000).toFixed(1) + "s")
