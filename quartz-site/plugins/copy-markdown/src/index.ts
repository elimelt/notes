import fs from "node:fs/promises";
import path from "node:path";
import type {
  BuildCtx,
  FilePath,
  ProcessedContent,
  QuartzEmitterPlugin,
} from "@quartz-community/types";

export interface CopyMarkdownOptions {
  outputDir?: string;
  sourceDir?: string;
}

const defaultOptions: Required<Pick<CopyMarkdownOptions, "outputDir">> = {
  outputDir: "static/markdown",
};

function normalizeOutputDir(outputDir: string): string {
  const normalized = outputDir.replaceAll("\\", "/").replace(/^\/+|\/+$/g, "");
  const segments = normalized.split("/");
  if (
    !normalized ||
    segments.some((segment) => segment === ".." || segment === ".")
  ) {
    throw new Error(`Invalid Copy Markdown output directory: ${outputDir}`);
  }
  return normalized;
}

function getPublishedSource(
  content: ProcessedContent,
  sourceRoot?: string,
): { slug: string; source: string } | null {
  const file = content[1];
  const slug = file.data.slug;
  const filePath = file.data.filePath;
  const relativePath = file.data.relativePath;

  if (
    typeof slug !== "string" ||
    typeof filePath !== "string" ||
    !filePath.endsWith(".md")
  ) {
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

function destinationFor(
  ctx: BuildCtx,
  outputDir: string,
  slug: string,
): string {
  return path.join(ctx.argv.output, outputDir, ...`${slug}.md`.split("/"));
}

async function publishSource(
  ctx: BuildCtx,
  outputDir: string,
  source: { slug: string; source: string },
): Promise<FilePath> {
  const destination = destinationFor(ctx, outputDir, source.slug);
  await fs.mkdir(path.dirname(destination), { recursive: true });
  await fs.copyFile(source.source, destination);
  return destination as FilePath;
}

export const CopyMarkdown: QuartzEmitterPlugin<CopyMarkdownOptions> = (
  userOptions,
) => {
  const outputDir = normalizeOutputDir(
    userOptions?.outputDir ?? defaultOptions.outputDir,
  );
  const sourceRoot = userOptions?.sourceDir
    ? path.resolve(userOptions.sourceDir)
    : undefined;
  let publishedSlugs = new Set<string>();

  return {
    name: "CopyMarkdown",
    async *emit(ctx, content) {
      const currentSlugs = new Set<string>();
      for (const item of content) {
        const source = getPublishedSource(item, sourceRoot);
        if (!source) continue;

        currentSlugs.add(source.slug);
        yield await publishSource(ctx, outputDir, source);
      }
      publishedSlugs = currentSlugs;
    },
    async *partialEmit(ctx, content) {
      const sources = content
        .map((item) => getPublishedSource(item, sourceRoot))
        .filter(
          (source): source is { slug: string; source: string } =>
            source !== null,
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
    },
  };
};

export default CopyMarkdown;
