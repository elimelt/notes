# Notebook templates

`scripts/new_notebook.py` discovers every `.ipynb` file in this directory. The
filename becomes the value accepted by `--template`, so a new workflow can be
added without changing the generator.

Templates may use these placeholders anywhere in notebook strings:

- `{{title}}`
- `{{category}}`
- `{{date}}`
- `{{description}}`
- `{{tags}}`
- `{{sources}}`
- `{{notebook_page}}`

Keep the YAML frontmatter in the first Markdown cell. Include warning
suppression and deterministic seeds near the start, followed by cells that ask
for provenance, method, interpretation, environment, and reproduction details.
The generated notebook should remain useful before any project-specific code is
added.
