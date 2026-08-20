import type {
  QuartzComponent,
  QuartzComponentConstructor,
  QuartzComponentProps,
} from "@quartz-community/types";

interface CopyMarkdownOptions {
  outputDir?: string;
}

const styles = `
.copy-markdown-control {
  display: inline-flex;
  align-items: center;
  margin-left: 0.6rem;
  vertical-align: baseline;
}

.copy-markdown-control[hidden] {
  display: none;
}

.copy-markdown-button {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  box-sizing: border-box;
  min-width: 6.75rem;
  padding: 0.1rem 0.55rem;
  border: 1px solid color-mix(in srgb, var(--gray) 45%, transparent);
  border-radius: 999px;
  background: transparent;
  color: var(--gray);
  font: inherit;
  font-size: 0.72em;
  line-height: 1.5;
  cursor: pointer;
  transition: color 0.15s, border-color 0.15s, background 0.15s;
}

.copy-markdown-button:hover {
  color: var(--secondary);
  border-color: var(--secondary);
}

.copy-markdown-button:focus-visible {
  outline: 2px solid var(--secondary);
  outline-offset: 2px;
}

.copy-markdown-button:disabled {
  cursor: wait;
  opacity: 0.65;
}

.copy-markdown-status {
  position: absolute;
  width: 1px;
  height: 1px;
  padding: 0;
  margin: -1px;
  overflow: hidden;
  clip: rect(0, 0, 0, 0);
  white-space: nowrap;
  border: 0;
}
`;

const copyScript = `
const copyMarkdownFallback = (text) => {
  const textarea = document.createElement("textarea")
  textarea.value = text
  textarea.setAttribute("readonly", "")
  textarea.style.position = "fixed"
  textarea.style.opacity = "0"
  document.body.appendChild(textarea)
  textarea.select()
  const copied = document.execCommand("copy")
  textarea.remove()
  if (!copied) throw new Error("The browser rejected the copy command")
}

const writeMarkdownToClipboard = async (text) => {
  if (navigator.clipboard && window.isSecureContext) {
    try {
      await navigator.clipboard.writeText(text)
      return
    } catch {
      copyMarkdownFallback(text)
      return
    }
  }
  copyMarkdownFallback(text)
}

const setupCopyMarkdown = () => {
  for (const control of document.querySelectorAll(".copy-markdown-control")) {
    const host = document.querySelector(".page-header .content-meta") || document.querySelector(".page-header")
    if (!host) continue

    const listenControl = host.querySelector(".tts-control")
    if (listenControl) host.insertBefore(control, listenControl)
    else host.appendChild(control)
    control.hidden = false

    const button = control.querySelector(".copy-markdown-button")
    if (!button) continue
    if (button.dataset.copyMarkdownBound === "true") continue
    button.dataset.copyMarkdownBound = "true"

    const label = button.querySelector(".copy-markdown-label")
    const status = control.querySelector(".copy-markdown-status")
    const originalLabel = label?.textContent ?? "Copy Markdown"
    let resetTimer

    const setResult = (message, visibleLabel) => {
      if (status) status.textContent = message
      if (label) label.textContent = visibleLabel
      window.clearTimeout(resetTimer)
      resetTimer = window.setTimeout(() => {
        if (label) label.textContent = originalLabel
      }, 2000)
    }

    const onClick = async () => {
      const markdownPath = button.dataset.markdownPath
      if (!markdownPath) return

      button.disabled = true
      try {
        const basePath = document.body.dataset.basepath ?? ""
        const response = await fetch(basePath + markdownPath, { cache: "force-cache" })
        if (!response.ok) throw new Error("Markdown request failed with " + response.status)
        await writeMarkdownToClipboard(await response.text())
        setResult("Markdown copied to the clipboard.", "Copied")
      } catch (error) {
        console.error("Unable to copy Markdown", error)
        setResult("Markdown could not be copied.", "Try again")
      } finally {
        button.disabled = false
      }
    }

    button.addEventListener("click", onClick)
    window.addCleanup?.(() => {
      window.clearTimeout(resetTimer)
      button.removeEventListener("click", onClick)
    })
  }
}

document.addEventListener("nav", setupCopyMarkdown)
document.addEventListener("render", setupCopyMarkdown)
if (document.readyState === "loading") {
  document.addEventListener("DOMContentLoaded", setupCopyMarkdown, { once: true })
} else {
  setupCopyMarkdown()
}
`;

function normalizeOutputDir(outputDir: string): string {
  return outputDir.replaceAll("\\", "/").replace(/^\/+|\/+$/g, "");
}

function encodeSlug(slug: string): string {
  return slug.split("/").map(encodeURIComponent).join("/");
}

const CopyMarkdown = ((options?: CopyMarkdownOptions) => {
  const outputDir = normalizeOutputDir(options?.outputDir ?? "static/markdown");

  const Component: QuartzComponent = ({
    fileData,
    displayClass,
  }: QuartzComponentProps) => {
    const slug = fileData.slug;
    const source = fileData.filePath;
    if (
      typeof slug !== "string" ||
      typeof source !== "string" ||
      !source.endsWith(".md")
    ) {
      return null;
    }

    const markdownPath = `/${outputDir}/${encodeSlug(slug)}.md`;
    return (
      <span class={`${displayClass ?? ""} copy-markdown-control`} hidden>
        <button
          class="copy-markdown-button"
          type="button"
          data-markdown-path={markdownPath}
          aria-label="Copy this note as Markdown"
        >
          <span class="copy-markdown-label">Copy Markdown</span>
        </button>
        <span
          class="copy-markdown-status"
          role="status"
          aria-live="polite"
        ></span>
      </span>
    );
  };

  Component.css = styles;
  Component.afterDOMLoaded = copyScript;
  return Component;
}) satisfies QuartzComponentConstructor<CopyMarkdownOptions>;

export { CopyMarkdown };
export default CopyMarkdown;
