// Semantic eval: does the model produce the CONVENTIONAL spoken reading of
// math notation (e.g. "A transpose A", not "A to the power of T A")? Uses
// known-answer cases with expected (must-match) and forbidden (must-not-match)
// patterns, embedded in realistic sentences. Compares prompt variants.
// Usage: node eval-semantic.mjs [model] [promptNames...]
import { PROMPTS } from "./prompts.mjs"

const LLM_API = "https://llm.elimelt.com"
const MODEL = process.argv[2] || "qwen2.5-coder:7b"
const WHICH = process.argv.slice(3)

// Each case: text sent to the model; expect = regexes that must ALL match the
// output; forbid = regexes that must NOT match. Case-insensitive.
export const CASES = [
  { text: "The Gram matrix is \\(A^T A\\) and it is symmetric.",
    expect: [/A transpose A/i], forbid: [/power of T|to the T\b|T A squared/i] },
  { text: "Solve the system by computing \\(A^{-1} b\\) directly.",
    expect: [/A inverse/i], forbid: [/power of (minus|negative) (1|one)|to the (minus|negative) (1|one)/i] },
  { text: "The derivative \\(f'(x)\\) vanishes at the optimum.",
    expect: [/f prime of x/i], forbid: [/f apostrophe|f tick/i] },
  { text: "We bound the error by \\(\\|x - y\\|\\) in the proof.",
    expect: [/norm of x minus y|norm of (the )?difference/i], forbid: [/pipe|bar bar|absolute value/i] },
  { text: "By Bayes rule, \\(P(A \\mid B)\\) depends on the prior.",
    expect: [/(probability|P) of A given B/i], forbid: [/A mid B|divided by B|A bar B|conditional on B squared/i] },
  { text: "The estimator \\(\\hat{y}\\) converges to the truth.",
    expect: [/y hat/i], forbid: [/hat of y|caret|circumflex/i] },
  { text: "The sample mean \\(\\bar{x}\\) is unbiased.",
    expect: [/x bar/i], forbid: [/bar of x|overline/i] },
  { text: "The variance is \\(\\sigma^2\\) for each component.",
    expect: [/sigma squared/i], forbid: [/sigma two|sigma caret|power of 2|s i g m a/i] },
  { text: "Gradient descent follows \\(-\\nabla f(x)\\) at each step.",
    expect: [/gradient of f|nabla f/i], forbid: [/del f of|triangle|upside/i] },
  { text: "There are \\(\\binom{n}{k}\\) ways to pick the subset.",
    expect: [/n choose k/i], forbid: [/binom|n over k|fraction/i] },
  { text: "Binary search takes \\(\\log_2 n\\) comparisons.",
    expect: [/log base (2|two) of n|log (2|two) of n/i], forbid: [/log underscore|log sub/i] },
  { text: "The expectation \\(E[X]\\) is finite by assumption.",
    expect: [/(expect(ed value|ation)|E) of X/i], forbid: [/E bracket|E times X|E sub X/i] },
  { text: "Vectors live in \\(\\mathbb{R}^n\\) throughout.",
    expect: [/R (to the )?n\b|R\^n reads as R n/i], forbid: [/mathbb|double.?struck|blackboard/i] },
  { text: "The total is \\(\\sum_{i=1}^{n} x_i\\) over all items.",
    expect: [/sum (from )?i equals (1|one) to n of x (sub )?i|sum over i (from (1|one) to n )?of x (sub )?i/i], forbid: [/sigma i|underscore|caret/i] },
  { text: "Precision drops below \\(10^{-3}\\) after training.",
    expect: [/(ten|10) to the (minus|negative) (3|three)|one thousandth/i], forbid: [/ten minus three|10 - 3/i] },
  { text: "Sorting runs in \\(O(n \\log n)\\) time in the worst case.",
    expect: [/order (of )?n log n|big o of n log n/i], forbid: [/O times n|zero of/i] },
  { text: "The updated state \\(x'\\) differs from \\(x\\) in one bit.",
    expect: [/x prime/i], forbid: [/x apostrophe|x tick|x quote/i] },
  { text: "The matrix product \\(U \\Sigma V^T\\) gives the SVD.",
    expect: [/V transpose/i], forbid: [/power of T|V to the T\b/i] },
]

const ask = async (system, text) => {
  const t0 = Date.now()
  const body = { model: MODEL, stream: false, options: { temperature: 0.2 },
    messages: [{ role: "system", content: system }, { role: "user", content: text }] }
  if (MODEL.startsWith("gpt-oss")) body.think = "low"
  if (MODEL.startsWith("gemma4")) body.think = false
  const r = await fetch(LLM_API + "/api/chat", {
    method: "POST", headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  })
  const ms = Date.now() - t0
  if (!r.ok) return { ms, err: "http " + r.status }
  const d = await r.json()
  return { ms, out: ((d.message && d.message.content) || "").replace(/\s+/g, " ").trim() }
}

const residual = o => /[\\_^{}$]/.test(o)

const names = WHICH.length ? WHICH : Object.keys(PROMPTS)
for (const name of names) {
  const sys = PROMPTS[name]
  if (!sys) { console.log("unknown prompt: " + name); continue }
  let pass = 0, resid = 0, totalMs = 0
  const fails = []
  for (const c of CASES) {
    const { ms, out, err } = await ask(sys, c.text)
    totalMs += ms || 0
    if (err) { fails.push("ERR " + err); continue }
    const okExpect = c.expect.every(re => re.test(out))
    const okForbid = c.forbid.every(re => !re.test(out))
    if (residual(out)) resid++
    if (okExpect && okForbid && !residual(out)) pass++
    else fails.push(JSON.stringify(c.text.slice(0, 46)) + " -> " + JSON.stringify(out.slice(0, 100)))
  }
  console.log("=== " + name + " (" + MODEL + ") ===")
  console.log("  semantic pass " + pass + "/" + CASES.length + " | residual " + resid +
    " | avg " + Math.round(totalMs / CASES.length) + "ms")
  for (const f of fails) console.log("    FAIL " + f)
}
