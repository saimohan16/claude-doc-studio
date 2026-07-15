---
name: md-experience
description: Turn plain markdown into an interactive "Doc Studio" — a guided, editable HTML reading experience with a focus map, Claude's inline suggestions with one-click accept, click-to-edit sections, export back to .md, and a live ask-Claude panel. Use whenever the user shares or points to a .md file (README, docs, notes, spec) and wants it read nicely, reviewed, guided-tour'd, or edited interactively — phrasings like "make this readable", "walk me through this doc", "review my README", "render this md", "what should I focus on". Also use when pointed at a folder, repo, or codebase with multiple .md files for a docs overview, reading order, or combined review — builds one workspace app with a file switcher and cross-file findings. Do NOT use for creating brand-new documents from scratch or for non-markdown files.
---

# md-experience: Doc Studio

Turns any markdown file into a single self-contained HTML app where the user can:
read with nice typography, follow a guided tour ordered by importance, see your
improvement suggestions pinned to sections (accept/dismiss in one click), edit any
section in place, export the edited markdown, and ask Claude live questions about
a section. Works in Claude.ai (artifact) and Claude Code (local HTML file).

## Workflow

### 1. Read the markdown — one file or many
Single file: read it (from disk if a path, else the pasted content).

**Folder / repo / multiple files**: discover the .md files first —
`find <root> -name '*.md' -not -path '*/node_modules/*' -not -path '*/.git/*' -not -path '*/vendor/*' -not -path '*/dist/*'`
— and read them all. Judgment on scope: up to ~12 files, include everything; larger
doc sites, include the files relevant to the user's goal and tell them what you
skipped (or ask). Skip generated files (CHANGELOG from tooling, license boilerplate
duplicates) unless asked.

### 2. Analyze — this is where your judgment matters most
Split the document into sections at headings (content before the first heading is an
"intro" section with `heading: null`, `level: 1`). Very short adjacent subsections
(< ~3 lines each) may be merged into their parent to avoid a noisy map. Each
section's `md` must contain its own heading line, so that concatenating all
sections with blank lines reproduces a valid document.

For each section assign:

- **priority** — the focus map:
  - `must`: the reader cannot use/understand the doc without it, OR it has problems
    that need the reader's decision (outdated, contradictory, risky).
  - `skim`: useful context; fine to read diagonally.
  - `ref`: look-up material — API tables, changelogs, license, long option lists.
  - Calibration: in a typical doc roughly 20–40% `must`. If everything is `must`,
    the map is useless — force-rank.
- **why** — one sentence, ≤ 140 chars, telling the reader what to look for or why it
  matters ("Defines the three config modes everything below assumes" — not "This
  section is important"). It doubles as the guided-tour caption.
- **suggestions** — 0–3 per section, only where you'd genuinely change something:
  factual staleness, missing steps, redundancy, unclear ordering, broken links,
  tone/length problems. Each has a `note` (what & why, ≤ 2 sentences) and, when the
  fix is concrete, a `proposed` full replacement markdown for the whole section
  (must include the heading line; keep the author's voice; `null` if the fix needs
  info you don't have — then the note should say what info is needed).
  Aim for 3–10 suggestions total across the doc. Quality over coverage: a doc with
  zero real problems gets zero suggestions, not invented ones.
- **summary** (doc-level) — 2–3 sentences: what the doc is, its overall state, and
  the single biggest thing you'd improve.

**When there are multiple files, also analyze across them:**
- **readingOrder** — the sequence a newcomer should read the files in (entry points
  like README first, contributor/internal docs later, reference last).
- **overview** (workspace-level) — 2–3 sentences on the doc set as a whole.
- **crossNotes** — findings that live *between* files: duplicated content
  ("CONTRIBUTING repeats README's install steps"), contradictions (two files state
  different minimum versions), broken relative links between the files, and gaps
  (a file every doc references but that doesn't exist). 0–5 notes; only real ones.
- Per-file `summary` becomes a one-liner on that file's state, shown when switching.
- Section ids must stay unique across the WHOLE workspace (prefix per doc:
  `d1s1`, `d1g1`, `d2s1`, …).

### 3. Write the doc JSON and build
Write the analysis as JSON — single-doc or workspace schema, both documented in
`scripts/build_viewer.py`'s docstring (the script validates either) — then:

```bash
python <skill_path>/scripts/build_viewer.py doc.json <OutputName>.html
```

The script validates the JSON and injects it into `assets/viewer_template.html`.
Do not hand-edit the template per-document; all per-document data goes in the JSON.
Name the output after the source file (`README.studio.html`) or, for a workspace, after the project (`taskpipe-docs.studio.html`).

### 4. Deliver by environment
Each branch below states what to run and what persistence/API-key behavior to
expect. For the widget tool's own setup mechanics, see
`references/delivery-environments.md`.

- **Claude.ai, inline widget tool available (preferred there)**: build with
  `--widget` and stream the fragment as an inline widget — renders directly in
  the conversation, no download/open step; Feedback drawer posts back via
  `sendPrompt`. Persistence: none needed (lives in the chat). Only additionally
  save/present the standalone .html if the user asks to keep, share, or open it
  outside the chat.
- **Claude.ai, no widget tool**: save the built HTML to
  `/mnt/user-data/outputs/` and present it — renders as an interactive artifact
  when opened. Persistence: artifact storage. Ask-Claude panel: no API key needed.
- **Claude Code / local (preferred: live review tab)**: write the HTML next to
  the source files, then start the bundled review server in the background and
  open the user's browser tab:
  `python <skill_path>/scripts/studio_serve.py serve <file>.studio.html --open &`
  Tell the user the printed URL in case the tab didn't open, then enter the
  review loop (step 6). Persistence: browser localStorage. Ask-Claude drawer:
  prompts for an Anthropic API key on first use (kept in tab memory only). If
  the user declines a server or just wants the file, plain `open`/`xdg-open
  <file>` still works — the app detects the absence of the server and falls
  back to the copy-paste feedback queue.

### 5. Round-trip edits
The app's **Download .md** button exports the edited document. If the user brings
that file (or pasted edits) back and asks to update the original, apply the changes
to the source file (Claude Code) or produce the updated .md in outputs (Claude.ai).
If asked to regenerate the viewer after edits, re-run the analysis on the new
content — don't reuse stale suggestions.

### 6. Claude Code: the live review loop
While the server from step 4 is running, the app's Feedback drawer shows a
"Send to Claude" button that POSTs the feedback block to the server. Receive it
by blocking on:
`python <skill_path>/scripts/studio_serve.py poll <file>.studio.html --timeout 240`
- Exit 0: feedback text was printed — apply it per step 7, rebuild the studio
  HTML with build_viewer.py (the open tab auto-reloads and preserves scroll),
  summarize what changed, and poll again.
- Exit 3: no feedback within the timeout — ask the user if they're still
  reviewing or done; poll again if they're continuing.
Stop the loop when the user says they're done, then kill the background serve
process. Feedback is file-backed (<file>.feedback.jsonl + .offset), so nothing
is lost across interrupted polls or server restarts.

### 7. Consuming feedback from the app
The app has an annotation mode: the user selects text, queues notes, and the
Feedback drawer produces a block starting with `## Doc Studio feedback — …`,
containing per-file bullet lines like `- [Section heading] re: "quoted text" —
comment`, plus accepted/dismissed suggestion ids and a list of hand-edited
sections. When the user pastes such a block (or a feedback.md):
- Treat every bullet as an edit request against the named section of the source
  markdown. The quote pinpoints the exact text; the comment says what to do.
- "Accepted suggestion rewrites … already applied in my export" means those ids
  are done — don't redo them; if the user provides their exported .md, prefer its
  text for those sections and any listed hand-edited sections.
- Apply the changes directly to the source files (Claude Code) or produce updated
  .md files in outputs (Claude.ai), summarize what changed per note, then offer to
  rebuild the viewer on the new content.

### 8. Claude Code only: optional live-review handoff
If the user has [lavish-axi](https://github.com/kunchenguid/lavish-axi) (or asks
for a live review loop outside the Doc Studio), see
`references/delivery-environments.md` for the handoff flow. Never install or
suggest it unprompted — the built-in server loop (step 6) and feedback queue
(step 7) are the default.

## What the generated app already handles (don't rebuild these)
All modes:
- Focus spine with priority colors + progress
- Guided tour (spotlight, keyboard ←/→/Esc, auto-ordered must → skim → ref)
- Per-section edit/revert; suggestion accept/dismiss with persistence
- Export/copy; dark mode; offline markdown fallback when the CDN is unreachable
- Ask-Claude drawer (keyless inside Claude.ai, API-key fallback locally)
- Annotation mode (select text → queue note) and Feedback drawer with
  copy/download of the structured feedback block

Workspace mode additionally:
- Numbered file switcher with per-file progress and open-suggestion counts
- Workspace overview card with crossNotes
- Cross-file guided tour (follows readingOrder, skips `ref` sections)
- Per-file and download-all export; per-file edit state

## Judgment calls
- Huge docs (> ~60 sections): keep the map readable — merge level-4+ headings into
  their parents.
- Code-heavy sections: suggestions may target prose around code, but never propose
  code changes you can't verify.
- If the user asks only to "read" (no review), still build the app but keep
  suggestions minimal (only clear defects) — the tour and map are the point.
- The user's own framing wins: if they say "focus my attention on security stuff",
  weight priorities and `why` lines toward that lens.
