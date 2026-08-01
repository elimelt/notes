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

Optional notebook tooling:

- Python 3.12 is the safest choice for local notebook execution because the
  current notebook stack uses `torch` and related wheels that are not equally
  available on newer Python releases.

From the repository root, run:

```sh
npm run dev
```

The first run clones the Quartz `v5` branch into the ignored `.quartz/`
directory and installs its locked dependencies. Quartz then serves the site at
`http://localhost:8080` and rebuilds it as content changes. Stop it with
<kbd>Ctrl</kbd>+<kbd>C</kbd>.

To create the same production output used by GitHub Pages:

```sh
npm run build
```

After adding or changing a Quartz plugin in `quartz.config.yaml`, run
`npm run sync:quartz` and commit the updated `quartz.lock.json`.

The generated site is written to `public/`. Both `.quartz/` and `public/` are
disposable and ignored by Git. To use a particular Quartz tag or commit, set
`QUARTZ_REF` before the first run (or remove `.quartz/` to bootstrap it again):

```sh
QUARTZ_REF=<tag-or-commit> npm run dev
```

To validate repo-specific note rules before a larger edit or backfill pass:

```sh
npm run validate:notes
```

To scan the full corpus instead of only changed Markdown files:

```sh
npm run validate:notes:all
```

## Code and benchmarks

Use a fenced code block for a short example that belongs in the narrative. Put
a reusable program or benchmark harness under `content/` beside its note, link
the source file from the note, and include the exact build or run command. Files
under `content/` are published as static assets; the site does not execute them.

Start empirical work from the benchmark template:

```sh
npm run new:note -- content/path/benchmark.md \
  --template benchmark \
  --title "Benchmark title" \
  --category "Performance Engineering" \
  --tags benchmarks
```

Record the environment, workload, controls, warmup, repetitions, units, and
variability. Commit the source and measured results, then run
`npm run validate:notes` and `npm run build`. The complete artifact-selection
and publication policy lives in `.notes/artifacts.yml`.

## Notebook-backed and embedded notes

Notebook pages use the
[`quartz-jupyter-embed`](https://github.com/vazome/quartz-jupyter-embed) plugin:

1. Author and execute the notebook under `content/` beside its related note.
2. Choose a standalone notebook page or an embedded-only companion.
3. Run `scripts/render_notebooks.py` to generate standalone wrappers and prepare
   notebook metadata.
4. Let Quartz render Markdown, code, tables, plots, and stored outputs directly
   from the checked-in notebook JSON.

Scaffold notebooks from the tracked templates instead of copying an existing
experiment:

```sh
npm run new:notebook -- content/ml/example/topic.ipynb \
  --template experiment \
  --title "Topic experiment" \
  --category "Machine Learning" \
  --tags topic evaluation \
  --sources https://example.org/paper https://example.org/dataset \
  --description "Measure how the method behaves on a small public dataset."
```

Available templates are `experiment`, `derivation`, and `benchmark`. List them
from the CLI so newly added templates appear automatically:

```sh
npm run new:notebook -- --list-templates
```

Embedded-only companions are the default. Pass `--standalone` when the notebook
should have its own graph node and page. Template files live in
`notebook-templates/`; adding another `.ipynb` there makes it available to the
generator without a code change.

The normal site commands already do the render step for you:

```sh
npm run dev
npm run build
```

If you only need to refresh notebook-derived Markdown without a full site
build:

```sh
python3 scripts/render_notebooks.py
```

If you want executed outputs checked into the notebook itself, use a local
Python 3.12 environment and run the executor directly:

```sh
python3.12 -m venv .venv
.venv/bin/python -m pip install -U pip
.venv/bin/python -m pip install numpy pandas matplotlib torch datasets nbclient ipykernel
.venv/bin/python scripts/execute_notebooks.py content/path/to/notebook.ipynb
```

The executor suppresses Python warnings and common Hugging Face progress noise,
then removes warning streams from stored outputs. Templates include the same
setup so interactive Jupyter runs remain quiet. To clean warning output already
stored in one or more notebooks without rerunning their experiments:

```sh
.venv/bin/python scripts/execute_notebooks.py --clean-only \
  content/path/to/first.ipynb content/path/to/second.ipynb
```

The `.ipynb` file is the source of truth. For a standalone notebook page, omit
`notebook_page` or set it to `true` in the first Markdown cell's YAML
frontmatter. The generated `.md` sibling contains only page metadata and the
public source link and should not be edited by hand.

To embed a notebook inside an existing note without creating another page, put
this frontmatter in the notebook's first Markdown cell:

```yaml
---
notebook_page: false
---
```

The notebook may share the note's stem, for example `topic.md` and
`topic.ipynb`. Add its content-root-relative link to the Markdown note in a
paragraph of its own:

```markdown
[Open the executable companion notebook](/ml/deep-learning/topic.ipynb)
```

During the build, that link is replaced by the rendered notebook, including
stored code outputs, tables, HTML, and plots. The root-relative source asset is
also published, and the notebook header links to it. Run
`python3 scripts/render_notebooks.py` after changing the notebook, then run
`npm run build` to seed the offline embed cache and verify the result.

The complete workflow for a new embedded companion is:

1. Run `npm run new:notebook` with the appropriate template.
2. Replace template prompts with code, math, provenance, and interpretation.
3. Execute it with `npm run execute:notebooks -- content/path/topic.ipynb`.
4. Add `[Open the executable companion](/path/topic.ipynb)` to its parent note.
5. Run `npm run render:notebooks`, `npm run test:notebooks`, and `npm run build`.
6. Commit the `.ipynb`, parent note, and any generated wrapper for a standalone notebook.

## Embedding the graph

The build publishes a full-viewport graph at `https://notes.elimelt.com/graph/`.
It reads the same content index as Quartz, excludes unconnected nodes from the
visualization, and opens notes in a new tab. Embed it without the surrounding
Quartz layout:

```html
<iframe
  src="https://notes.elimelt.com/graph/"
  title="Elijah's notes graph"
  loading="lazy"
  style="width: 100%; height: 720px; border: 0"
></iframe>
```

Append `?target=top` when node selection should navigate the containing window
instead of opening a new tab.

## Writing and organizing notes

- Put publishable Markdown and attachments in `content/`.
- Use YAML front matter for `title`, `category`, `tags`, and `date`.
- Link related notes with Obsidian wikilinks, for example
  `[[algorithms/BFS|breadth-first search]]`. Quartz turns these links into
  backlinks and graph edges.
- Use `draft: true` in front matter to keep an unfinished note out of the
  published site.
- Use `content/templates/` as the starting point for new concept, paper, and
  benchmark notes. Quartz ignores that directory during site generation.
- Treat `.notes/` as the repository's authoring contract. `prose.yml`,
  `content.yml`, `frontmatter.yml`, and `artifacts.yml` define the target style
  for future notes and for the backfill of existing notes.
- Use `npm run new:note -- ...` to scaffold a note from one of the tracked
  templates instead of copying and editing template files by hand.
- Put site-wide visual overrides in `quartz-site/custom.scss` and Quartz layout
  changes in `quartz.config.yaml`.

### Scaffolding a note

```sh
npm run new:note -- content/algorithms/example.md \
  --template concept \
  --title "Example title" \
  --category "Algorithms" \
  --tags graph traversal bfs
```

### Agent-facing workflow

- Read `AGENTS.md` first if you are using an LLM coding agent.
- `npm run validate:notes` checks changed Markdown files.
- `npm run validate:notes:all` scans the full corpus backlog.
- Run `npm run build` after changes that affect rendering, assets, math, or
  note structure.
- If you edit notebooks, regenerate their wrappers before validation.

## Repo-specific gotchas

- `scripts/quartz.sh` mirrors repo-root `docs/` into the built site for legacy
  URLs.
- `npm run validate:notes` validates Markdown only, not raw `.ipynb` files.
- Keep `.quartz/`, `public/`, `.venv/`, and `work/notebook-data/` out of Git.

## How the build works

The repository keeps only site-specific Quartz configuration. The
`scripts/quartz.sh` wrapper bootstraps a cached upstream Quartz checkout, syncs
`content/` and the local configuration into it, and invokes the Quartz CLI. This
keeps the notes repository small while avoiding a locally maintained static-site
generator.

Pushes to `main` trigger `.github/workflows/static.yml`, which builds `public/`
and deploys it through the official GitHub Pages artifact actions. The custom
domain is configured as `notes.elimelt.com` in `quartz.config.yaml`.

## Optional research utilities

The scripts under `scripts/` for embeddings, keyword extraction, semantic
search, text cleanup, and related experiments are independent of the website
build. Run them directly with Python and install their optional dependencies as
needed; they are intentionally not part of the deployment toolchain.
