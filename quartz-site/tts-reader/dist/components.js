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
  const LOOKAHEAD = 2
  const RETRY_BASE = 800, RETRY_MAX = 8000, RETRY_LIMIT = 6
  const LLM_API = "https://llm.elimelt.com"
  const LLM_MODEL = "llama3.2:3b"
  const LLM_PROMPT =
    "You prepare excerpts from technical notes for a text-to-speech engine. Return the text " +
    "essentially unchanged, EXCEPT convert the specific fragments that do not read aloud well into " +
    "the words a person would say. Only touch: math, LaTeX, symbols, operators, code identifiers, " +
    "and abbreviations. Examples: \"O(n log n)\" -> \"order n log n\"; \"x_i\" -> \"x sub i\"; " +
    "\"a != b\" -> \"a not equal to b\". LaTeX between \\( and \\) is inline math: replace just that " +
    "span with how the formula is read aloud and drop the delimiters. Leave every ordinary word, " +
    "including its wording, order, punctuation, and sentence structure, exactly as written. Copy any " +
    "fragment that needs no conversion character for character; if the whole excerpt contains nothing " +
    "to convert, return it completely unchanged. Do not paraphrase, reword, summarize, add, remove, " +
    "or explain anything else. Output only the resulting text with no preamble."
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

    const retryable = status => status === 429 || status === 408 || status >= 500
    const httpError = (label, status) => {
      const e = new Error(label + " " + status)
      e.retryable = retryable(status)
      return e
    }
    const netError = () => { const e = new Error("network"); e.retryable = true; return e }
    const sleep = ms => new Promise(r => setTimeout(r, ms))

    // Only chunks that actually contain something unspeakable need the LLM.
    // Plain prose is sent to TTS verbatim, which keeps the reading faithful to
    // the written text and avoids needless LLM requests.
    const needsRewrite = t =>
      /\\\(/.test(t) ||               // inline math marker
      /[_^{}\\=<>|~#$%*/]/.test(t) || // math/code symbols and operators
      /[A-Za-z]\([^)]*\)/.test(t) ||  // function-like calls, e.g. O(n), f(x)
      /\d[.,]?\d*\s*[+\-*/=xX]\s*\d/.test(t) || // arithmetic expressions
      /\b[A-Za-z]{2,}[._][A-Za-z0-9]/.test(t)   // code identifiers, e.g. foo.bar, snake_case

    // LLM naturalization. On a hard (non-retryable) failure we fall back to the
    // raw text so the chunk can still be spoken; retryable failures propagate so
    // the serial queue can back off and retry the same chunk.
    const rewrite = text => {
      if (!needsRewrite(text)) return Promise.resolve(text)
      return fetch(LLM_API + "/api/chat", {
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
      }).catch(() => { throw netError() })
        .then(r => { if (!r.ok) throw httpError("llm", r.status); return r.json() })
        .then(d => {
          const out = norm((d.message && d.message.content) || "")
          // Small models occasionally hallucinate or echo the prompt examples,
          // producing output far longer than the input. Since we only ask for
          // minimal edits, reject an implausible expansion and read the original.
          if (!out || out.length > text.length * 2 + 40) return text
          return out
        })
        .catch(e => { if (e && e.retryable) throw e; return text })
    }

    const synth = text =>
      rewrite(text).then(spoken =>
        fetch(API + "/v1/audio/speech", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ model: MODEL, input: spoken, voice: VOICE, response_format: FORMAT }),
        }).catch(() => { throw netError() }))
        .then(r => { if (!r.ok) throw httpError("speech", r.status); return r.blob() })
        .then(b => URL.createObjectURL(b))

    // Synthesize one chunk, retrying retryable failures (429/5xx/network) with
    // exponential backoff on the SAME index so processing stays exactly-once and
    // in order. Only a hard failure or exhausted retries rejects.
    const synthWithRetry = async i => {
      for (let attempt = 0; ; attempt++) {
        if (destroyed) throw new Error("destroyed")
        try { return await synth(chunks[i].text) }
        catch (e) {
          if (!(e && e.retryable) || attempt >= RETRY_LIMIT) throw e
          await sleep(Math.min(RETRY_BASE * 2 ** attempt, RETRY_MAX))
        }
      }
    }

    // Serial queue: one request in flight at a time, advancing strictly in
    // order and only running ahead of playback by LOOKAHEAD chunks. Waiters
    // parked on a not-yet-produced index are woken as each entry lands.
    let head = 0, working = false, epoch = 0
    const waiters = new Set()
    const wake = () => { for (const w of waiters) w(); }
    const pump = async () => {
      if (working || destroyed) return
      working = true
      const gen = epoch
      try {
        while (!destroyed && gen === epoch && head < chunks.length && head <= idx + LOOKAHEAD) {
          if (cache.has(head)) { head++; continue }
          const i = head
          let url, err
          try { url = await synthWithRetry(i) }
          catch (e) { err = e || new Error("synth failed") }
          if (destroyed || gen !== epoch) {
            if (url) URL.revokeObjectURL(url)
            return
          }
          cache.set(i, err ? Promise.reject(err) : Promise.resolve(url))
          head++
          wake()
        }
      } finally { working = false }
    }

    // Resolve the cached audio URL for a chunk, waiting for the serial queue to
    // reach it if necessary. Rejects only if that chunk's synthesis hard-failed.
    const awaitChunk = i => {
      if (cache.has(i)) return cache.get(i)
      const gen = epoch
      return new Promise((resolve, reject) => {
        const check = () => {
          if (destroyed || gen !== epoch) { waiters.delete(check); return reject(new Error("cancelled")) }
          if (cache.has(i)) { waiters.delete(check); cache.get(i).then(resolve, reject) }
        }
        waiters.add(check)
        pump()
      })
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
      epoch++
      audio.pause()
      audio.removeAttribute("src")
      for (const p of cache.values()) p.then(u => URL.revokeObjectURL(u)).catch(() => {})
      cache.clear()
      idx = 0; head = 0
      wake()
      setReading(null)
      render()
    }

    const playIdx = async i => {
      if (destroyed) return
      if (i >= chunks.length) return stop()
      idx = i
      const gen = epoch
      pump()
      state = "loading"; render()
      let url
      try { url = await awaitChunk(i) }
      catch {
        if (destroyed || gen !== epoch || state !== "loading") return
        return playIdx(i + 1)
      }
      if (destroyed || gen !== epoch || state === "paused") return
      setReading(chunks[i].el)
      currentUrl = url
      audio.src = url
      state = "playing"; render()
      audio.play().catch(() => {})
      pump()
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
