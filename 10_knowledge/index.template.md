# Knowledge Index Template

Durable, slower-moving knowledge.

The live `10_knowledge/index.md` is local/private navigation and is ignored by Git because it can expose the current domain inventory. Keep this template tracked so a fresh checkout still shows the expected shape.

## Domain Inventory

- `<domain-slug>` — one-sentence description of the durable knowledge domain.
- `<seed-domain-slug>` — one-sentence description. Mark seed domains with the date and reason they were created.

## Topic Promotion Rule

A topic does not start as its own folder. It starts as a note or entry in an index.

Promote to a sub-wiki, meaning a folder inside a domain, only when:

- There are 5+ meaningful files.
- It sees recurring use.
- It requires internal structure such as sources, concepts, or syntheses.

## Domain Creation Rule

Seed domains may start from as few as one or two strong captures when the topic is clearly distinct from existing domains and active research is expected to bring more. The 5+ threshold above governs internal sub-wikis, not domain creation.

Seed domains should be reviewed periodically. If they stay small without recurring use, merge them back into an index entry or park them.

The ingest-agent may propose a new top-level domain when an inbox item does not fit an existing domain and the topic is likely to recur. A proposal should include:

- the proposed domain slug
- the captures or notes that justify it
- why an existing domain is a poor fit
- whether it should start as a domain, a subdomain, or just an index entry

Create the folder only after user confirmation. For a new top-level domain, create a local `index.md` and `raw/` directory so deterministic PDF routing has a clear destination.

## Navigation And Synthesis Aids

- Use `bin/knowledge-report --domain <slug>` for raw/note ratios and audit candidates.
- Run `bin/audit-sweep --apply --subset <slug>` to surface `needs-audit` items for the epistemic auditor.
- Use `bin/extract-knowledge` to pull reusable lessons from `30_projects/` into `10_knowledge/`.
