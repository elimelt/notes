const css = String.raw`
.tts-control { display: inline-flex; align-items: center; gap: .3rem; vertical-align: baseline; margin-left: .6rem; }
.tts-control[hidden] { display: none; }
.tts-btn {
  display: inline-flex; align-items: center; gap: .3rem; box-sizing: border-box;
  border: 1px solid color-mix(in srgb, var(--gray) 45%, transparent);
  background: transparent; color: var(--gray); border-radius: 999px;
  padding: .1rem .55rem; font: inherit; font-size: .72em; line-height: 1.5;
  cursor: pointer; transition: color .15s, border-color .15s, background .15s;
}
.tts-btn:hover { color: var(--secondary); border-color: var(--secondary); }
.tts-btn:focus-visible { outline: 2px solid var(--secondary); outline-offset: 2px; }
.tts-btn svg { width: .95em; height: .95em; flex: none; }
.tts-stop { padding: .1rem .35rem; }
.tts-stop[hidden] { display: none; }
.tts-control.is-loading .tts-icon { animation: tts-spin 1s linear infinite; }
.tts-reading { background: var(--highlight); border-radius: .25rem; box-shadow: 0 0 0 .25rem var(--highlight); }
@keyframes tts-spin { to { transform: rotate(360deg); } }
@media (prefers-reduced-motion: reduce) { .tts-control.is-loading .tts-icon { animation: none; } }
`

const script = String.raw`
(() => {
  const API = "https://transcribe.elimelt.com"
  const MODEL = "speaches-ai/Kokoro-82M-v1.0-ONNX"
  const VOICE = "af_heart"
  const FORMAT = "mp3"
  const TARGET = 260, MAX = 500
  const LLM_API = "https://llm.elimelt.com"
  const LLM_MODEL = "llama3.2:3b"
  const LLM_PROMPT =
    "You rewrite excerpts from technical notes so they can be read aloud naturally by a " +
    "text-to-speech engine. Expand math, symbols, code identifiers, and abbreviations into " +
    "spoken words (for example \"O(n log n)\" becomes \"order n log n\", \"x_i\" becomes \"x sub i\"). " +
    "LaTeX between \\( and \\) delimiters is inline math: speak it as a person would read the " +
    "formula aloud and drop the delimiters. Smooth awkward notation into plain sentences but keep " +
    "the meaning and technical content identical. Do not add, explain, or summarize. Output only " +
    "the rewritten text with no preamble."
  const SKIP = "pre, code, .jupyter-notebook-embedded, .notebook-link-unavailable, figure, table, svg, sup.footnote-ref, .footnotes"
  const MATH = ".katex"
  const BLOCKS = "p, li, dt, dd, h1, h2, h3, h4, h5, h6"
  const ICONS = {
    play: '<svg class="tts-icon" viewBox="0 0 24 24" fill="currentColor" aria-hidden="true"><path d="M8 5v14l11-7z"/></svg>',
    pause: '<svg class="tts-icon" viewBox="0 0 24 24" fill="currentColor" aria-hidden="true"><path d="M6 5h4v14H6zm8 0h4v14h-4z"/></svg>',
    load: '<svg class="tts-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" aria-hidden="true"><path d="M12 3a9 9 0 1 0 9 9" opacity=".9"/></svg>',
    stop: '<svg viewBox="0 0 24 24" fill="currentColor" aria-hidden="true"><rect x="6" y="6" width="12" height="12" rx="1.5"/></svg>',
  }

  const norm = t => t.replace(/\s+/g, " ").trim()

  const textOf = node => {
    let out = ""
    node.childNodes.forEach(n => {
      if (n.nodeType === 3) out += n.nodeValue
      else if (n.nodeType === 1) {
        if (n.matches(SKIP)) return
        if (n.matches(MATH)) {
          const tex = n.getAttribute("data-tex")
          out += tex ? " \\(" + tex + "\\) " : " " + textOf(n) + " "
        } else out += textOf(n)
      }
    })
    return out
  }

  const sentences = t => t.match(/[^.!?]+[.!?]+(?:["')\]]+)?\s*|[^.!?]+$/g) || [t]

  // Character-split an oversized prose segment on whitespace, but never break
  // inside a \( ... \) math block (splitting LaTeX would corrupt the formula).
  const splitLong = s => {
    const parts = s.match(/\\\([^]*?\\\)|[^]+?(?=\\\(|$)/g) || [s]
    const out = []
    let buf = ""
    for (const p of parts) {
      if (p.startsWith("\\(")) {
        if (buf) { out.push(buf.trim()); buf = "" }
        out.push(p.trim())
      } else {
        for (const w of p.split(/(\s+)/)) {
          if ((buf + w).length > MAX && buf) { out.push(buf.trim()); buf = w }
          else buf += w
        }
      }
    }
    if (buf.trim()) out.push(buf.trim())
    return out.filter(Boolean)
  }

  const chunkText = t => {
    const out = []
    let buf = ""
    for (const s of sentences(t)) {
      if (s.length > MAX) {
        if (buf) { out.push(buf.trim()); buf = "" }
        for (const piece of splitLong(s)) out.push(piece)
        continue
      }
      if ((buf + s).length > TARGET && buf) { out.push(buf.trim()); buf = s }
      else buf += s
    }
    if (buf.trim()) out.push(buf.trim())
    return out.filter(Boolean)
  }

  const collect = article => {
    const chosen = [...article.querySelectorAll(BLOCKS)].filter(el => {
      if (el.closest(SKIP)) return false
      const parentBlock = el.parentElement && el.parentElement.closest(BLOCKS)
      return !(parentBlock && article.contains(parentBlock))
    })
    const chunks = []
    for (const el of chosen) {
      const text = norm(textOf(el))
      if (text) for (const c of chunkText(text)) chunks.push({ el, text: c })
    }
    return chunks
  }

  const setup = () => {
    document.querySelectorAll(".tts-control").forEach(el => el.remove())
    const article = document.querySelector(".center article") || document.querySelector("article")
    if (!article) return null
    const chunks = collect(article)
    if (!chunks.length) return null

    const control = document.createElement("span")
    control.className = "tts-control"
    control.innerHTML =
      '<button type="button" class="tts-btn tts-toggle" aria-label="Read this note aloud">' +
      ICONS.play + '<span class="tts-label">Listen</span></button>' +
      '<button type="button" class="tts-btn tts-stop" hidden aria-label="Stop reading">' + ICONS.stop + '</button>'
    const toggle = control.querySelector(".tts-toggle")
    const stopBtn = control.querySelector(".tts-stop")
    const label = control.querySelector(".tts-label")
    const host = document.querySelector(".page-header .content-meta") || document.querySelector(".page-header")
    if (host) host.appendChild(control)
    else article.insertBefore(control, article.firstChild)

    const audio = new Audio()
    const cache = new Map()
    let idx = 0, state = "idle", reading = null, destroyed = false, currentUrl = null

    const rewrite = text =>
      fetch(LLM_API + "/api/chat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          model: LLM_MODEL,
          stream: false,
          options: { temperature: 0.2 },
          messages: [
            { role: "system", content: LLM_PROMPT },
            { role: "user", content: text },
          ],
        }),
      }).then(r => { if (!r.ok) throw new Error("llm " + r.status); return r.json() })
        .then(d => norm((d.message && d.message.content) || "") || text)
        .catch(() => text)

    const synth = text =>
      rewrite(text).then(spoken =>
        fetch(API + "/v1/audio/speech", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ model: MODEL, input: spoken, voice: VOICE, response_format: FORMAT }),
        })).then(r => { if (!r.ok) throw new Error("speech " + r.status); return r.blob() })
        .then(b => URL.createObjectURL(b))

    const prefetch = i => {
      if (i < 0 || i >= chunks.length || cache.has(i)) return
      cache.set(i, synth(chunks[i].text).catch(e => { cache.delete(i); throw e }))
    }

    const setReading = el => {
      if (reading) reading.classList.remove("tts-reading")
      reading = el || null
      if (reading) {
        reading.classList.add("tts-reading")
        reading.scrollIntoView({ block: "nearest" })
      }
    }

    const render = () => {
      control.classList.toggle("is-loading", state === "loading")
      const playing = state === "playing"
      toggle.querySelector(".tts-icon").outerHTML =
        state === "loading" ? ICONS.load : playing ? ICONS.pause : ICONS.play
      label.textContent = playing ? "Pause" : state === "loading" ? "Loading" : state === "paused" ? "Resume" : "Listen"
      stopBtn.hidden = state === "idle"
    }

    const stop = () => {
      state = "idle"
      audio.pause()
      audio.removeAttribute("src")
      for (const p of cache.values()) p.then(u => URL.revokeObjectURL(u)).catch(() => {})
      cache.clear()
      idx = 0
      setReading(null)
      render()
    }

    const playIdx = async i => {
      if (destroyed) return
      if (i >= chunks.length) return stop()
      idx = i
      prefetch(i); prefetch(i + 1)
      state = "loading"; render()
      let url
      try { url = await cache.get(i) }
      catch { return playIdx(i + 1) }
      if (destroyed || state === "paused") return
      setReading(chunks[i].el)
      currentUrl = url
      audio.src = url
      state = "playing"; render()
      audio.play().catch(() => {})
    }

    audio.addEventListener("ended", () => {
      const done = idx, finishedUrl = currentUrl
      cache.delete(done)
      playIdx(done + 1).finally(() => { if (finishedUrl) URL.revokeObjectURL(finishedUrl) })
    })
    audio.addEventListener("error", () => { if (state === "playing") playIdx(idx + 1) })

    toggle.addEventListener("click", () => {
      if (state === "loading") return
      if (state === "playing") { audio.pause(); state = "paused"; render() }
      else if (state === "paused") { state = "playing"; render(); audio.play().catch(() => {}) }
      else playIdx(idx)
    })
    stopBtn.addEventListener("click", stop)

    return { destroy() { destroyed = true; stop(); control.remove() } }
  }

  let current = null
  const mount = () => { if (current) current.destroy(); current = setup() }
  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", mount, { once: true })
  else mount()
  document.addEventListener("nav", mount)
})()
`

export const TTSReader = () => {
  const Component = () => null
  Component.css = css
  Component.afterDOMLoaded = script
  return Component
}

export default TTSReader
