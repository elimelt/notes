const css = String.raw`
#style-debug-launcher {
  position: fixed; right: 1rem; bottom: 1rem; z-index: 10001;
  border: 1px solid color-mix(in srgb, var(--dark) 20%, transparent);
  border-radius: 999px; padding: .55rem .8rem; cursor: pointer;
  color: var(--light); background: var(--dark); box-shadow: 0 8px 28px #0003;
  font: 600 12px/1 var(--codeFont); letter-spacing: .02em;
}
#style-debug-panel {
  position: fixed; inset: .75rem .75rem .75rem auto; z-index: 10002;
  width: min(340px, calc(100vw - 1.5rem)); overflow: auto; box-sizing: border-box;
  color: #e9eee9; background: #18201dcc; border: 1px solid #ffffff24;
  border-radius: 14px; padding: 14px; box-shadow: 0 22px 70px #0008;
  backdrop-filter: blur(18px) saturate(130%); font: 12px/1.35 var(--codeFont);
}
#style-debug-panel[hidden] { display: none; }
.sdp-head { display: flex; align-items: start; justify-content: space-between; margin-bottom: 12px; }
.sdp-head strong { color: #fff; font-size: 14px; }
.sdp-head small { display: block; color: #aab8b0; margin-top: 2px; }
.sdp-close, .sdp-actions button { border: 1px solid #ffffff26; color: #e9eee9; background: #ffffff0d; border-radius: 7px; cursor: pointer; }
.sdp-close { width: 26px; height: 26px; font-size: 18px; }
.sdp-group { border: 0; border-top: 1px solid #ffffff1c; padding: 11px 0 3px; margin: 0; }
.sdp-group legend { color: #91c4ad; padding: 0 8px 0 0; font-weight: 700; text-transform: uppercase; letter-spacing: .08em; }
.sdp-row { display: grid; grid-template-columns: 92px 1fr 58px; gap: 8px; align-items: center; margin: 8px 0; }
.sdp-row label { color: #cbd5cf; }
.sdp-row input[type=range] { width: 100%; accent-color: #7ab899; }
.sdp-row output { color: #fff; text-align: right; font-variant-numeric: tabular-nums; }
.sdp-color input { width: 100%; height: 25px; padding: 0; border: 1px solid #ffffff26; border-radius: 5px; background: transparent; }
.sdp-actions { display: grid; grid-template-columns: 1fr 1fr; gap: 7px; margin-top: 10px; }
.sdp-actions button { padding: 8px; }
.sdp-actions button:hover, .sdp-close:hover { background: #ffffff1c; }
.sdp-toast { min-height: 16px; margin-top: 8px; color: #91c4ad; text-align: center; }
`

const script = String.raw`
(() => {
  const storageKey = "notes.style-debug.v1"
  const controls = [
    { group: "Layout", label: "Page width", key: "--site-page-width", min: 1100, max: 1800, step: 10, unit: "px" },
    { group: "Layout", label: "Article width", key: "--site-article-width", min: 36, max: 64, step: .5, unit: "rem" },
    { group: "Layout", label: "Column gap", key: "--site-column-gap", min: 1, max: 4, step: .1, unit: "rem" },
    { group: "Typography", label: "Body size", key: "--site-body-size", min: 14, max: 21, step: .25, unit: "px" },
    { group: "Typography", label: "Line height", key: "--site-body-leading", min: 1.35, max: 2, step: .025, unit: "" },
    { group: "Typography", label: "Paragraph gap", key: "--site-paragraph-gap", min: .5, max: 2, step: .05, unit: "rem" },
    { group: "Typography", label: "Article title", key: "--site-title-size", min: 1.6, max: 3.2, step: .05, unit: "rem" },
    { group: "Typography", label: "Section title", key: "--site-heading-size", min: 1.15, max: 2.2, step: .05, unit: "rem" },
    { group: "Shape", label: "Code radius", key: "--site-code-radius", min: 0, max: 1.5, step: .05, unit: "rem" },
    { group: "Shape", label: "Media radius", key: "--site-media-radius", min: 0, max: 1.5, step: .05, unit: "rem" },
    { group: "Current theme", label: "Background", key: "--light", type: "color" },
    { group: "Current theme", label: "Text", key: "--darkgray", type: "color" },
    { group: "Current theme", label: "Heading", key: "--dark", type: "color" },
    { group: "Current theme", label: "Links", key: "--secondary", type: "color" },
    { group: "Current theme", label: "Link hover", key: "--tertiary", type: "color" }
  ]
  const root = document.documentElement
  const defaults = Object.fromEntries(controls.map(c => [c.key, getComputedStyle(root).getPropertyValue(c.key).trim()]))
  let values = {}
  try { values = JSON.parse(localStorage.getItem(storageKey) || "{}") } catch {}

  const apply = (key, value, persist = true) => {
    root.style.setProperty(key, value)
    values[key] = value
    if (persist) localStorage.setItem(storageKey, JSON.stringify(values))
  }
  Object.entries(values).forEach(([key, value]) => root.style.setProperty(key, value))

  const mount = () => {
    if (document.querySelector("#style-debug-panel")) return
    const launcher = document.createElement("button")
    launcher.id = "style-debug-launcher"
    launcher.textContent = "Style"
    const panel = document.createElement("aside")
    panel.id = "style-debug-panel"
    panel.hidden = true
    panel.innerHTML = '<div class="sdp-head"><div><strong>Style Debug</strong><small>Local overrides · Shift+S</small></div><button class="sdp-close" aria-label="Close">×</button></div><div class="sdp-controls"></div><div class="sdp-actions"><button data-action="reset">Reset</button><button data-action="copy">Copy CSS</button></div><div class="sdp-toast" aria-live="polite"></div>'
    document.body.append(launcher, panel)
    const container = panel.querySelector(".sdp-controls")
    for (const group of [...new Set(controls.map(c => c.group))]) {
      const fieldset = document.createElement("fieldset")
      fieldset.className = "sdp-group"
      fieldset.innerHTML = '<legend>' + group + '</legend>'
      controls.filter(c => c.group === group).forEach(c => {
        const row = document.createElement("div")
        row.className = "sdp-row" + (c.type === "color" ? " sdp-color" : "")
        const current = values[c.key] || defaults[c.key]
        const numeric = parseFloat(current)
        row.innerHTML = c.type === "color"
          ? '<label>' + c.label + '</label><input type="color" value="' + current + '"><output>' + current + '</output>'
          : '<label>' + c.label + '</label><input type="range" min="' + c.min + '" max="' + c.max + '" step="' + c.step + '" value="' + numeric + '"><output>' + numeric + c.unit + '</output>'
        const input = row.querySelector("input")
        const output = row.querySelector("output")
        input.addEventListener("input", () => {
          const value = input.value + (c.unit || "")
          output.textContent = value
          apply(c.key, value)
        })
        fieldset.append(row)
      })
      container.append(fieldset)
    }
    const toggle = () => { panel.hidden = !panel.hidden; launcher.hidden = !panel.hidden }
    launcher.addEventListener("click", toggle)
    panel.querySelector(".sdp-close").addEventListener("click", toggle)
    panel.querySelector('[data-action="reset"]').addEventListener("click", () => {
      controls.forEach(c => root.style.removeProperty(c.key))
      localStorage.removeItem(storageKey)
      location.reload()
    })
    panel.querySelector('[data-action="copy"]').addEventListener("click", async () => {
      const lines = controls.filter(c => values[c.key]).map(c => "  " + c.key + ": " + values[c.key] + ";")
      await navigator.clipboard.writeText(":root {\n" + lines.join("\n") + "\n}")
      const toast = panel.querySelector(".sdp-toast")
      toast.textContent = "CSS copied"
      setTimeout(() => toast.textContent = "", 1600)
    })
    window.addEventListener("keydown", event => {
      if (event.shiftKey && event.key.toLowerCase() === "s" && !/input|textarea/i.test(event.target.tagName)) toggle()
    })
  }
  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", mount, { once: true })
  else mount()
  document.addEventListener("nav", mount)
})()
`

export const StyleDebugPanel = () => {
  const Component = () => null
  Component.css = css
  Component.afterDOMLoaded = script
  return Component
}

export default StyleDebugPanel
