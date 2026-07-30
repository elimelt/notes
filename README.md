# Elijah's Notes

This repository contains my technical notes and the source for
[notes.elimelt.com](https://notes.elimelt.com). The notes are ordinary Markdown,
can be edited as an [Obsidian](https://obsidian.md/) vault, and are published as
a connected knowledge garden with [Quartz](https://quartz.jzhao.xyz/).

Much of the information is paraphrased from textbooks, papers, and lectures. I
claim no ownership over those sources. The collection is a work in progress; if
you have a question or correction, feel free to [reach out](https://elimelt.com/contact).

## Local development

Requirements:

- Git
- Node.js 22 or newer
- npm

From the repository root, run:

```sh
npm run dev
```

The first run clones the Quartz `v4` branch into the ignored `.quartz/`
directory and installs its locked dependencies. Quartz then serves the site at
`http://localhost:8080` and rebuilds it as content changes. Stop it with
<kbd>Ctrl</kbd>+<kbd>C</kbd>.

To create the same production output used by GitHub Pages:

```sh
npm run build
```

The generated site is written to `public/`. Both `.quartz/` and `public/` are
disposable and ignored by Git. To use a particular Quartz tag or commit, set
`QUARTZ_REF` before the first run (or remove `.quartz/` to bootstrap it again):

```sh
QUARTZ_REF=<tag-or-commit> npm run dev
```

## Writing and organizing notes

- Put publishable Markdown and attachments in `content/`.
- Use YAML front matter for `title`, `category`, `tags`, and `date`.
- Link related notes with Obsidian wikilinks, for example
  `[[algorithms/BFS|breadth-first search]]`. Quartz turns these links into
  backlinks and graph edges.
- Use `draft: true` in front matter to keep an unfinished note out of the
  published site.
- Put site-wide visual overrides in `quartz-site/custom.scss` and Quartz layout
  changes in `quartz.layout.ts`.

## How the build works

The repository keeps only site-specific Quartz configuration. The
`scripts/quartz.sh` wrapper bootstraps a cached upstream Quartz checkout, syncs
`content/` and the local configuration into it, and invokes the Quartz CLI. This
keeps the notes repository small while avoiding a locally maintained static-site
generator.

Pushes to `main` trigger `.github/workflows/static.yml`, which builds `public/`
and deploys it through the official GitHub Pages artifact actions. The custom
domain is configured as `notes.elimelt.com` in `quartz.config.ts`.

## Optional research utilities

The scripts under `scripts/` for embeddings, keyword extraction, semantic
search, text cleanup, and related experiments are independent of the website
build. Run them directly with Python and install their optional dependencies as
needed; they are intentionally not part of the deployment toolchain.
