# Agent Guide

This repository is a Quartz-backed notes site. Most edits are content edits.

## First reads

- `README.md`
- `.notes/prose.yml`
- `.notes/content.yml`
- `.notes/frontmatter.yml`
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

## Repo-specific rules

- Do not add an in-body `#` heading to a note that already has frontmatter
  `title`.
- Keep `tags` as YAML lists, not comma-separated strings.
- Put publishable notes and attachments in `content/`.
- `content/templates/` is for scaffolding and is ignored by Quartz.
- Non-Markdown files inside `content/` are published as static assets by Quartz.
- Repo-root `docs/` is mirrored into the built site for legacy URLs by
  `scripts/quartz.sh`.

## Useful commands

```sh
npm run new:note -- path/to/note.md --template concept --title "Example title" --category "Algorithms" --tags graph traversal bfs
npm run validate:notes
npm run validate:notes:all
npm run build
npm run dev
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

## When backfilling

- Normalize frontmatter first.
- Fix rendering breakage next.
- Improve structure and evidence after that.
- Commit coherent batches by note family when possible.
