# 00_inbox - Local Rules

> [!WARNING]
> Fast capture zone. Nothing here is durable and nothing here is citable.
> Everything is expected to leave via `01_ingest/`.

Rules declare **Binds / Tier / Check / Escape**. The Escape is the named, cheap,
non-penalized way to comply when you cannot meet the letter of the rule.

Tiers: **T0** advisory · **T1** detected · **T2** blocked · **T3** reconciled.

---

## 1. This file is not a capture, and neither is any other operational file.

> **Binds:** `bin/ingest-minion`
> **Tier:** T2 (blocked)
> **Check:** `IngestMinion.RESERVED_NAMES` in `01_ingest/minion.py`, with a
> regression test in `tests/test_ingest_minion.py`
> **Escape:** n/a, if you genuinely want a file named `AGENTS.md` ingested,
> rename it first.

Until 2026-08-10 the scanner returned every non-dotfile, so a contract file
placed here to govern this folder was normalized and moved into
`01_ingest/ready/` on the first apply. **The contract migrated out of the folder
it governed, silently.** Reserved: `AGENTS.md`, `README.md`, `index.md`,
`CLAUDE.md`, `LICENSE`, `.gitkeep`, matched case-insensitively because
`core.ignorecase` is true here.

## 2. A capture that claims a source must have fetched it.

> **Binds:** any file here carrying `url`, `doi`, `authors`, or `year`
> **Tier:** T2 (blocked) at the routing gate, not on arrival
> **Check:** `bin/capture-validate` R1–R3 via `01_ingest/minion.py`
> **Escape:** drop the citation fields and set `type: hypothesis`. Capturing a
> thought with no source is completely fine; capturing it with a source you did
> not fetch is not.

Deliberately checked at the gate rather than here. This folder is meant to be
frictionless, and a capture zone that argues with you stops being used.

**The Escape did not work until 2026-08-27.** `hypothesis` was absent from
`ALLOWED_TYPES` in `01_ingest/minion.py`, so taking the documented escape route
produced `unsupported type: hypothesis` and stranded the file. Six documents
promised it — AGENTS.md principle 11, two workflow standards, `ingest-minion.md`,
this rule, and `bin/capture-validate`'s own fix message. None of them was the set
the gate reads.

That is the exact failure principle 11 names: an escape valve that does not open
leaves fabricating the citation as the only way past the check. It is now in
`ALLOWED_TYPES` and deliberately not in `KNOWLEDGE_TYPES` — a hypothesis is a
valid capture and is not durable knowledge, so it moves through the pipeline and
stops before `10_knowledge/` for a human to decide.

## 2b. A source lead is not a source.

> **Binds:** captures written by `bin/deep-research-ingest leads`
> **Tier:** T2 (blocked) at the routing gate, same as rule 2
> **Check:** `bin/capture-validate` R1 — a lead carries `asserted_doi` /
> `asserted_url` / `asserted_arxiv`, never `url` / `doi` / `authors` / `year` /
> `journal` / `venue`
> **Escape:** n/a. Retrieving the thing is the only way a lead becomes a capture.

A lead records that a language model *asserted* a source exists. Promoting one
means retrieving it and recording `fetch_method` plus a `retrieval_receipt`.

If the asserted identifier resolves to something unrelated to the claim, that is
a finding — record it and stop. Do not go looking for a better source to put in
its place. On 2026-08-19 the resolver did exactly that and attached a
cultural-studies interview to a report on agent runtimes. See
`local-only: 20_live/provenance/` for the dated ingest-audit record.

## 3. Nothing here may be cited.

> **Binds:** any agent answering a question
> **Tier:** T1 (detected)
> **Check:** `bin/knowledge-reconcile` will show anything that reached
> `10_knowledge/` without a routing record
> **Escape:** route it properly first. `bin/ingest-minion run --dry-run` shows
> what would move without moving it.

Contents are unreviewed, unclassified, and may be duplicates.

## 4. Do not tidy this folder.

> **Binds:** any agent or minion pass
> **Tier:** T0 (advisory)
> **Check:** none
> **Escape:** n/a

Backlog here is a signal about capture rate, not a mess to clean. Deleting or
renaming captures destroys the only record that something was seen.
