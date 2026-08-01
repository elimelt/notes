# Agent Guide

This repository is a Quartz-backed notes site. Most edits are content edits.

## First reads

- `README.md`
- `.notes/prose.yml`
- `.notes/content.yml`
- `.notes/frontmatter.yml`
- `.notes/artifacts.yml`
- `content/templates/`

These files define the current authoring contract. Treat them as the default
target for any new note or backfill pass.

## Core workflow

1. Read the target note and a few related notes before editing.
2. Preserve frontmatter ownership of the page title.
3. Keep claims either cited, derived in the note, or tied to an explicit
   measurement.
4. Run `npm run validate:notes`.
5. Run `npm run build` if the change touches rendering, layout, note structure,
   math, or assets.

## Notebook workflow

- Notebook source of truth lives in `content/**/*.ipynb`.
- Standalone notebooks generate `*.md` wrappers beside the notebook containing
  frontmatter plus the source link consumed by `quartz-jupyter-embed`.
- A companion notebook can be embedded in an existing note without generating
  another page. Put `notebook_page: false` in the notebook's first-cell YAML
  frontmatter, then link `/path/from/content/root.ipynb` in its own paragraph.
- Do not hand-edit generated notebook wrappers. Edit the notebook, then
  regenerate them.
- `npm run build`, `npm run dev`, and `npm run sync:quartz` already call
  `scripts/render_notebooks.py` before Quartz runs.
- For notebook-only changes without a full site build, run
  `python3 scripts/render_notebooks.py`.
- To execute notebooks with outputs in place, prefer a repo-local Python 3.12
  environment and run `python3.12 -m venv .venv`, install notebook deps into
  it, then use `.venv/bin/python scripts/execute_notebooks.py <path>.ipynb`.
- Cache downloaded notebook data under `work/notebook-data/`, not under
  `content/`.

## Executable artifacts

- Consult `.notes/artifacts.yml` before choosing inline code, a source file, a
  benchmark, or a notebook.
- Add executable material when it exposes a mechanism, checks a derivation, or
  supplies evidence used by the note. Do not add code as decoration.
- Put reusable source and benchmark harnesses under `content/` beside the note,
  link them from the note, and include exact run commands.
- For benchmarks, record the environment, workload, controls, warmup,
  repetitions, units, and variability. Never fabricate missing measurements.
- Execute claimed-runnable examples and notebooks before publication. Commit
  notebook outputs that the note discusses.

## Repo-specific rules

- Do not add an in-body `#` heading to a note that already has frontmatter
  `title`.
- Keep `tags` as YAML lists, not comma-separated strings.
- Put publishable notes and attachments in `content/`.
- `content/templates/` is for scaffolding and is ignored by Quartz.
- Non-Markdown files inside `content/` are published as static assets by Quartz.
- Repo-root `docs/` is mirrored into the built site for legacy URLs by
  `scripts/quartz.sh`.
- `npm run validate:notes` validates notebook wrappers, not raw `.ipynb` cells.
  If you change notebooks, regenerate the wrappers first.
- Keep `.venv/`, `.quartz/`, `public/`, and `work/notebook-data/` untracked.

## Useful commands

```sh
npm run new:note -- path/to/note.md --template concept --title "Example title" --category "Algorithms" --tags graph traversal bfs
npm run validate:notes
npm run validate:notes:all
npm run test:notebooks
npm run build
npm run dev
python3 scripts/render_notebooks.py
.venv/bin/python scripts/execute_notebooks.py content/path/to/notebook.ipynb
```

`npm run validate:notes` checks changed Markdown files. Use
`npm run validate:notes:all` when you intentionally want the full corpus
backlog.

## Editing notes

- Start with note purpose.
- Prefer dense sections over thin bullet piles.
- Add inline links near nontrivial claims.
- Add setup and reproduction details for benchmark notes.
- Add assumptions and intermediate steps when a derivation skips too much.
- Keep prose direct. Avoid formulaic contrasts, fake certainty, and generic
  conclusions.

## Writing and linking style

- Treat the notes as a connected body of thought, not a hierarchy that must be
  completed from top to bottom. Folder placement is storage; links carry the
  conceptual structure.
- Give larger narrative notes the job of explaining the landscape and pointing
  to focused notes, experiments, source readings, and implementation branches.
  Keep the detailed mechanism in the focused note rather than duplicating it in
  every narrative.
- Let focused notes stand on their own: state the question or mechanism,
  explain enough context to make it useful, and expose the next questions or
  branches that follow from it.
- Put links at the moment a concept branches or a claim needs support. A
  related-notes list is useful for navigation, but it should not be the only
  connection between notes.
- Prefer concrete mechanisms, code, diagrams, derivations, measurements, and
  source excerpts over broad summaries. When a note is exploratory or
  incomplete, say what is known, what was measured, what is inferred, and what
  remains open.
- Preserve multiple valid entry points. A reader may arrive through a
  benchmark result, an implementation detail, a paper, or a high-level
  explanation; each should link naturally to the others.
- Do not force a premature taxonomy or canonical reading order. Add structure
  when it helps a reader move through the material, not to make the collection
  look finished.

## When backfilling

- Normalize frontmatter first.
- Fix rendering breakage next.
- Improve structure and evidence after that.
- Commit coherent batches by note family when possible.
