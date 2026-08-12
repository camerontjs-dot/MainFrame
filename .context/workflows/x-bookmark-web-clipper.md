# X Bookmark Web Clipper Workflow

Use this workflow when capturing X bookmarks into MainFrame as raw inbox evidence with Obsidian Web Clipper.

## Purpose

Capture each bookmarked X post, plus any directly linked article or readable source page, into `00_inbox/` without changing the raw captured files. This is a fast-capture workflow; normalization and routing happen later through the ingest workflow.

## Defaults

- Browser: the user's real Chrome session.
- Source list: `https://x.com/i/bookmarks`.
- Capture action: Obsidian Web Clipper `Save file...`.
- Temporary save location: `~/Downloads`.
- Final destination: `00_inbox/`.
- Run note location: `00_inbox/YYYY-MM-DD__x-bookmark-web-clipper-run.md`.

## Setup Checks

1. Confirm Chrome is already authenticated to X.
2. Confirm Obsidian Web Clipper is installed and available from Chrome Extensions.
3. Record a Downloads baseline before clipping:

   ```sh
   find ~/Downloads -maxdepth 1 -type f -print | sort
   ```

4. Create a run note with start time, baseline files, and a capture table with columns for bookmark URL, linked article URL, post clip, article clip, cleanup, and notes.
5. Run one pilot bookmark before the full batch.

## Clipping Loop

For each bookmark:

1. Open the bookmarked status URL directly when possible.
2. Click Chrome toolbar Extensions.
3. Click Obsidian Web Clipper.
4. Click `Save file...`.
5. Verify a new `.md` file appears in Downloads.
6. Record the post URL, generated filename, and any capture quirks in the run note.

Direct status URLs are more reliable than clipping from the scrolling bookmark timeline because they make Web Clipper target the intended post instead of a nearby item.

## Linked Articles

If the bookmarked post links to a readable article:

1. Open the article or article card.
2. Prefer the canonical readable page when available.
3. For X Articles, click the article card from the post. If that fails, try the visible focus-mode URL or direct `/article/<id>` URL.
4. Save the article page with Obsidian Web Clipper `Save file...`.
5. Record the article URL and generated filename in the same run-note row as the source post.

If the link is a GitHub repository, product page, course page, or project page rather than an article, capture it only when it is the key linked source or provenance for the bookmark. For external lead forms, capture the visible page only; do not enter personal data or submit forms.

## X Article Quirks

- Some X Article cards are wrapped in a video or image surface. Click the lower title/card area if the first click only starts video playback.
- If a card opens `/photo/1`, search the exact article title to recover a direct `/article/<id>` URL.
- If exact-title search does not expose a readable article and the card remains media-bound, log the article as partial and keep the bookmark row as a failure/partial.
- Reply bookmarks may save as the parent post with the bookmarked reply included in Comments. Log that quirk rather than rewriting the raw capture.

## Batch Move

Move only new Web Clipper Markdown files from Downloads into `00_inbox/`. Preserve filenames and avoid overwrites with suffixes:

```sh
python3 - <<'PY'
from pathlib import Path

src_dir = Path.home() / "Downloads"
dst_dir = Path.home() / "Desktop" / "MainFrame" / "00_inbox"

for src in sorted(src_dir.glob("*.md")):
    dst = dst_dir / src.name
    if dst.exists():
        stem, suffix = dst.stem, dst.suffix
        i = 2
        while True:
            candidate = dst_dir / f"{stem}-{i}{suffix}"
            if not candidate.exists():
                dst = candidate
                break
            i += 1
    src.rename(dst)
    print(f"MOVED\t{dst.name}")
PY
```

After moving, update the run note with final `00_inbox/` filenames.

## Completion Policy

- Do not unbookmark or remove X bookmarks unless the user explicitly confirms that cleanup action during the run.
- If the user confirms cleanup, unbookmark only after the post and required article/source sidecars are confirmed in `00_inbox/`.
- Failed or partially clipped bookmarks stay bookmarked and are listed in the run note.
- If no cleanup confirmation is given, leave all X bookmarks intact and rely on the run note for future duplicate avoidance.

## Failure Handling

- If Web Clipper stays open after `Save file...`, check Downloads before clicking again. Duplicate files can be discarded only after verifying they are duplicate captures.
- If Chrome or the accessibility tree stops exposing windows, restart or reactivate Chrome and re-check the current URL before continuing.
- If an article is behind a login, form, Telegram gate, or bio-only promise, do not chase it unless the user explicitly asks. Capture the visible post and log the limitation.
- If Downloads contains non-baseline files that are not Web Clipper Markdown files, leave them alone.

## Verification

At the end:

1. Confirm Downloads has no new Web Clipper Markdown left behind:

   ```sh
   find ~/Downloads -maxdepth 1 -name '*.md' -print
   ```

2. Confirm all moved filenames listed in the run note exist in `00_inbox/`.
3. Confirm the run note lists every processed bookmark and every failure/partial.
4. Record whether bookmark cleanup was attempted.
5. Leave raw captures unedited as evidence.

## Privacy And Provenance

- Treat all clipped files in `00_inbox/` as private raw evidence.
- Do not edit generated clip bodies after capture.
- Do not enter personal data, submit forms, follow gates, or alter accounts while clipping.
- Preserve source URLs in the run note so later ingest can distinguish raw evidence from extracted working copies.
