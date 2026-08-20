// quartz-site/plugins/copy-markdown/src/index.ts
import fs from "node:fs/promises";
import path from "node:path";
var defaultOptions = {
  outputDir: "static/markdown"
};
function normalizeOutputDir(outputDir) {
  const normalized = outputDir.replaceAll("\\", "/").replace(/^\/+|\/+$/g, "");
  const segments = normalized.split("/");
  if (!normalized || segments.some((segment) => segment === ".." || segment === ".")) {
    throw new Error(`Invalid Copy Markdown output directory: ${outputDir}`);
  }
  return normalized;
}
function getPublishedSource(content, sourceRoot) {
  const file = content[1];
  const slug = file.data.slug;
  const filePath = file.data.filePath;
  const relativePath = file.data.relativePath;
  if (typeof slug !== "string" || typeof filePath !== "string" || !filePath.endsWith(".md")) {
    return null;
  }
  if (!sourceRoot) return { slug, source: filePath };
  if (typeof relativePath !== "string" || !relativePath.endsWith(".md")) {
    return null;
  }
  const source = path.resolve(sourceRoot, relativePath);
  if (source !== sourceRoot && !source.startsWith(sourceRoot + path.sep)) {
    return null;
  }
  return { slug, source };
}
function destinationFor(ctx, outputDir, slug) {
  return path.join(ctx.argv.output, outputDir, ...`${slug}.md`.split("/"));
}
async function publishSource(ctx, outputDir, source) {
  const destination = destinationFor(ctx, outputDir, source.slug);
  await fs.mkdir(path.dirname(destination), { recursive: true });
  await fs.copyFile(source.source, destination);
  return destination;
}
var CopyMarkdown = (userOptions) => {
  const outputDir = normalizeOutputDir(
    userOptions?.outputDir ?? defaultOptions.outputDir
  );
  const sourceRoot = userOptions?.sourceDir ? path.resolve(userOptions.sourceDir) : void 0;
  let publishedSlugs = /* @__PURE__ */ new Set();
  return {
    name: "CopyMarkdown",
    async *emit(ctx, content) {
      const currentSlugs = /* @__PURE__ */ new Set();
      for (const item of content) {
        const source = getPublishedSource(item, sourceRoot);
        if (!source) continue;
        currentSlugs.add(source.slug);
        yield await publishSource(ctx, outputDir, source);
      }
      publishedSlugs = currentSlugs;
    },
    async *partialEmit(ctx, content) {
      const sources = content.map((item) => getPublishedSource(item, sourceRoot)).filter(
        (source) => source !== null
      );
      const currentSlugs = new Set(sources.map(({ slug }) => slug));
      for (const slug of publishedSlugs) {
        if (currentSlugs.has(slug)) continue;
        await fs.rm(destinationFor(ctx, outputDir, slug), { force: true });
      }
      for (const source of sources) {
        yield await publishSource(ctx, outputDir, source);
      }
      publishedSlugs = currentSlugs;
    }
  };
};
var index_default = CopyMarkdown;
export {
  CopyMarkdown,
  index_default as default
};
