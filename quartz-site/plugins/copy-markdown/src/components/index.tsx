import type {
  QuartzComponent,
  QuartzComponentConstructor,
  QuartzComponentProps,
} from "@quartz-community/types";

interface CopyMarkdownOptions {
  outputDir?: string;
}

const styles = `
.copy-markdown {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 1.5rem;
  max-width: 48rem;
  margin-top: 1.5rem;
  padding: 1rem 1.125rem;
  border: 1px solid var(--lightgray);
  border-radius: 0.75rem;
  background: color-mix(in srgb, var(--lightgray) 18%, transparent);
}

.copy-markdown__content {
  min-width: 0;
}

.copy-markdown h2 {
  margin: 0 0 0.25rem;
  font-size: 1rem;
  line-height: 1.3;
}

.copy-markdown p {
  margin: 0;
  color: var(--darkgray);
  font-size: 0.9rem;
  line-height: 1.45;
}

.copy-markdown__button {
  flex: 0 0 auto;
  min-width: 5.5rem;
  padding: 0.55rem 0.8rem;
  border: 1px solid var(--secondary);
  border-radius: 0.5rem;
  background: var(--secondary);
  color: var(--light);
  font: inherit;
  font-size: 0.875rem;
  font-weight: 600;
  line-height: 1.2;
  cursor: pointer;
}

.copy-markdown__button:hover {
  filter: brightness(1.08);
}

.copy-markdown__button:focus-visible {
  outline: 2px solid var(--tertiary);
  outline-offset: 3px;
}

.copy-markdown__button:disabled {
  cursor: wait;
  opacity: 0.7;
}

.copy-markdown__status {
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

@media all and (max-width: 600px) {
  .copy-markdown {
    align-items: stretch;
    flex-direction: column;
    gap: 0.75rem;
  }

  .copy-markdown__button {
    width: 100%;
  }
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
  for (const button of document.querySelectorAll(".copy-markdown__button")) {
    if (button.dataset.copyMarkdownBound === "true") continue
    button.dataset.copyMarkdownBound = "true"

    const label = button.querySelector(".copy-markdown__label")
    const section = button.closest(".copy-markdown")
    const status = section?.querySelector(".copy-markdown__status")
    const originalLabel = label?.textContent ?? "Copy"
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
      <section
        class={`${displayClass ?? ""} copy-markdown`}
        aria-labelledby="copy-markdown-title"
      >
        <div class="copy-markdown__content">
          <h2 id="copy-markdown-title">Copy Markdown</h2>
          <p>
            Copy this note's source Markdown for your editor or another tool.
          </p>
        </div>
        <button
          class="copy-markdown__button"
          type="button"
          data-markdown-path={markdownPath}
        >
          <span class="copy-markdown__label">Copy</span>
        </button>
        <span
          class="copy-markdown__status"
          role="status"
          aria-live="polite"
        ></span>
      </section>
    );
  };

  Component.css = styles;
  Component.afterDOMLoaded = copyScript;
  return Component;
}) satisfies QuartzComponentConstructor<CopyMarkdownOptions>;

export { CopyMarkdown };
export default CopyMarkdown;
