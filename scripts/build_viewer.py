#!/usr/bin/env python3
"""Inject a doc-analysis JSON into viewer_template.html.

Usage:
    python build_viewer.py <doc.json> <output.html> [--template path] [--widget]

--widget emits a body-only fragment (style + markup + scripts) for inline
chat-widget rendering instead of a standalone HTML page.

Accepts EITHER a single-doc JSON or a multi-file WORKSPACE JSON.

Single doc:
{
  "title": "README.md", "source": "...", "generated": "...", "summary": "...",
  "sections": [ { "id","level","heading","priority","why","md","suggestions":[...] } ]
}

Workspace (multiple .md files):
{
  "workspace": "taskpipe docs",
  "generated": "2026-07-03",
  "overview": "2-3 sentence read on the whole doc set",
  "crossNotes": ["cross-file finding 1", "..."],       # optional
  "readingOrder": ["d1","d2","d3"],                    # doc ids, best-first
  "docs": [
    {"id": "d1", "title": "README.md", "source": "README.md",
     "summary": "one-liner on this file's state",
     "sections": [ ...same section schema as single doc... ]}
  ]
}

Section schema:
  id (unique across the whole workspace), level, heading (null for intro),
  priority: "must"|"skim"|"ref", why (<=140 chars), md (raw markdown incl. its
  heading line), suggestions: [{id, note, proposed|null}]
"""
import json, re, sys, pathlib

PLACEHOLDER = "/*__DOC_DATA__*/null"

WIDGET_ADAPTER = """
<style>
.app{display:block}
.sidebar{display:none!important}
.topbar{display:block!important;position:static!important;margin:0 0 16px!important;
  border:0.5px solid var(--line);border-radius:12px;padding:10px 12px!important;background:var(--surface)}
.main{padding:0 0 40px!important;max-width:none}
.backdrop{display:none!important}
.tourbar{position:static!important;display:none;padding:0!important;margin:0 0 14px;pointer-events:auto}
body.touring .tourbar{display:flex}
.tourbar .inner{max-width:none;width:100%;justify-content:space-between}
.drawer{position:static!important;width:100%!important;height:auto!important;display:none;
  border:0.5px solid var(--line);border-radius:12px;margin:0 0 16px;box-shadow:none!important;transform:none}
.drawer.open{display:flex}
.drawer .chat{max-height:300px;overflow-y:auto}
.notebtn,.notepop{position:absolute}
.toast{position:absolute;left:12px;top:6px;bottom:auto}
</style>
<script>
(function(){
  var tb=document.querySelector('.toolbar');if(!tb)return;
  ['fbDrawer','drawer'].forEach(function(id){var el=document.getElementById(id);
    if(el)tb.parentNode.insertBefore(el,tb.nextSibling);});
  var tour=document.querySelector('.tourbar');if(tour)tb.parentNode.insertBefore(tour,tb.nextSibling);
  var mb=document.getElementById('mapBtn');if(mb)mb.style.display='none';
})();
</script>
"""


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    if len(args) != 2:
        sys.exit(__doc__)
    doc_path, out_path = map(pathlib.Path, args)
    template = pathlib.Path(__file__).parent.parent / "assets" / "viewer_template.html"
    if "--template" in sys.argv:
        template = pathlib.Path(sys.argv[sys.argv.index("--template") + 1])

    doc = json.loads(doc_path.read_text(encoding="utf-8"))

    # --- validate ---
    if "docs" in doc:  # workspace mode
        docs = doc["docs"]
        assert docs, "workspace needs at least one doc"
        did = set()
        for d in docs:
            assert d.get("id") and d["id"] not in did, f"doc id missing/duplicated: {d.get('id')}"
            did.add(d["id"])
            assert d.get("title"), f"doc {d['id']} needs a title"
        order = doc.get("readingOrder") or [d["id"] for d in docs]
        assert set(order) == did, "readingOrder must list every doc id exactly once"
        doc["readingOrder"] = order
        all_sections = [(d["id"], s) for d in docs for s in d.get("sections") or []]
    else:
        assert doc.get("title"), "doc.title required"
        all_sections = [(None, s) for s in doc.get("sections") or []]

    ids = set()
    for _owner, s in all_sections:
        assert s.get("id") and s["id"] not in ids, f"section id missing/duplicated: {s.get('id')}"
        ids.add(s["id"])
        assert s.get("priority") in ("must", "skim", "ref"), f"bad priority in {s['id']}"
        assert isinstance(s.get("md"), str) and s["md"].strip(), f"empty md in {s['id']}"
        for g in s.get("suggestions") or []:
            assert g.get("id") and g["id"] not in ids, f"suggestion id missing/duplicated: {g.get('id')}"
            ids.add(g["id"])
            assert g.get("note"), f"suggestion {g['id']} needs a note"

    payload = json.dumps(doc, ensure_ascii=False)
    payload = payload.replace("</", "<\\/")  # keep </script> safe inside the inline block

    html = template.read_text(encoding="utf-8")
    assert PLACEHOLDER in html, "placeholder not found in template"
    html = html.replace(PLACEHOLDER, payload)
    if "--widget" in sys.argv:
        # emit a fragment for inline chat widgets: <style> + body contents,
        # no DOCTYPE/html/head/body wrapper
        style = re.search(r"<style>.*?</style>", html, re.S).group(0)
        body = re.search(r"<body>\n(.*)\n</body>", html, re.S).group(1)
        html = style + "\n" + body + WIDGET_ADAPTER
    out_path.write_text(html, encoding="utf-8")
    n_docs = len(doc.get("docs") or []) or 1
    n_sec = len(all_sections)
    n_sug = sum(len(s.get("suggestions") or []) for _o, s in all_sections)
    print(f"Built {out_path} ({n_docs} file(s), {n_sec} sections, {n_sug} suggestions)")

if __name__ == "__main__":
    main()
