# TTS Reader — agent notes

Operational knowledge for the "Listen" feature (`quartz-site/tts-reader/dist/components.js`).
Gathered while building it; verify against the component before relying on constants.

## Architecture (as shipped)

- **Block-level extraction**: `collect()` walks `article` for
  `p, li, dt, dd, h1-h6, .katex-display`, skipping `pre/code/figure/table/svg`,
  notebook embeds, and footnotes. `.katex-display` matters: Quartz emits
  `$$...$$` as a *sibling* span of paragraphs, so without it every standalone
  equation (402 across the site when measured) is silently skipped.
- Inline/display math is carried as `\( raw LaTeX \)` via the `data-tex`
  attribute on `.katex` spans; chunking never splits inside a math span.
- **LLM rewrite gate** (`needsRewrite`): only chunks containing math/code
  markers go to the LLM; plain prose goes to TTS verbatim.
- **Urgency skip**: if estimated buffered audio ahead of a chunk
  (`~15 chars/s`) is under `URGENT_BUFFER_S=10`, skip the LLM and speak the
  deterministic `speakLeftovers()` regex rendering immediately; a background
  quality rewrite fills the localStorage cache for revisits.
- **LLM serialization** (`llmSerial`): exactly one LLM generation in flight.
  TTS requests still parallelize (`CONCURRENCY=2`).
- **Rewrite cache**: localStorage, keyed by `CACHE_VERSION + text`.
  **Bump `CACHE_VERSION` whenever the prompt, model, or gate changes.**

## Backend facts (llm.elimelt.com, ollama)

- **One resident model.** Never mix models per request tier: alternating
  models evicts/reloads and made everything worse (llama fallback: 39s;
  reloaded qwen: 60–107s).
- **Concurrent generations collapse the server.** Two parallel qwen calls
  measured 100–113s each (prompt eval ~650 t/s -> ~15 t/s). Serialize.
- **Prompt caching dominates.** The ~1.6k-token system prompt costs one cold
  eval (gemma4:e4b 28s, qwen 49s), then ~1s warm. Keep the system prompt
  byte-identical across calls or the cache misses.
- Thinking models: pass `think: false` (gemma4) or `think: "low"` (gpt-oss)
  in the request body; default thinking adds 10–37s of latency.

## Model selection (S3 prompt, 2026-08)

| Model | Semantic 18-case | Residual on 15 real blocks | Warm rewrite |
|---|---|---|---|
| gemma4:e4b think=false (shipped) | 18/18 | 0/15 | ~2.5s |
| gemma4:26b think=false | 18/18 | — | ~2.7s (2x the RAM, same quality) |
| qwen2.5-coder:7b | 18/18 | 1/15 | 3.4–4.0s |
| gpt-oss:20b think=low | 18/18 | 0/15 | 7.8–17.3s |
| gemma2:2b | 11/18 | leaves raw LaTeX | rejected |
| llama3.2:3b | 13/18 (S0 era) | — | fast but weak |

Prompt lessons (see `eval/prompts.mjs`, shipped prompt = S3):
- Few-shot examples of only *rich* formulas teach models to skip trivial spans
  (`\(t_s\)` left raw). S3 adds an explicit "EVERY span" rule + a worked
  example using exactly that failure; this fixed it.
- Include WRONG readings next to correct ones (`A^T` -> "A transpose",
  NEVER "A to the power of T").

## Eval harnesses

Source of truth: `quartz-site/tts-reader/eval/`. They import
`hast-util-from-html`, which only resolves inside the Quartz checkout, so run
them from `.quartz/` (which is gitignored and wiped on ref changes — hence the
copies here):

```sh
npm run build                        # eval reads built HTML from public/
cp quartz-site/tts-reader/eval/*.mjs .quartz/
cd .quartz
node eval-semantic.mjs gemma4:e4b S3          # 18-case known-answer suite
node eval-perblock.mjs 15 gemma4:e4b S3       # real blocks: residual/fidelity
LLM_MODEL=gemma4:e4b node timeline.mjs public/algorithms/stable-matching.html 20
```

`timeline.mjs` replays the exact shipped pipeline (chunking, gate, queue
policy, urgency skip, serialization) with real TTS audio durations via
`ffprobe`, and reports time-to-first-audio, stalls, and wall-vs-audio time.
**Keep it in sync with components.js when changing queue/rewrite logic.**

Reference numbers (gemma4:e4b, warm cache): stable-matching 0.8s TTFT,
one ~1.4s stall, wall 122.4s / audio 120.2s; static-timing-analysis (display
math heavy) 0.7s TTFT, one 1.6s stall, wall 188.9s / audio 186.5s.

## Known gaps / follow-ups

- Cold prompt eval (~28s) can land mid-note in a replay; in the browser the
  urgency skip covers it, but a page-load pre-warm request would remove the
  window entirely.
- The first chunk after a very short heading always stalls ~1.5s (TTS
  synthesis can't be hidden behind 1s of audio).
- `CHARS_PER_SECOND=15` is a rough Kokoro estimate; measured durations could
  refine urgency decisions.
