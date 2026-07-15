#!/usr/bin/env python3
"""Local review server for Doc Studio HTML (Claude Code / local use).

Gives the built studio a real browser tab and a feedback channel back to the
agent, lavish-axi style, using only the Python standard library.

Usage:
  studio_serve.py serve <file.html> [--port N] [--open]
      Serves the file at http://127.0.0.1:PORT/ (fresh from disk each request,
      so rebuilds show up on refresh / auto-reload). Endpoints:
        GET  /studio-ping   -> {"ok": true}            (the page detects server mode)
        GET  /studio-mtime  -> {"mtime": <float>}      (page auto-reloads on change)
        POST /feedback      -> body {"text": "..."}    (queued to <file>.feedback.jsonl)
      Writes <file>.server.json with the chosen port. Run in the background.

  studio_serve.py poll <file.html> [--timeout SECONDS]
      Blocks until new feedback arrives (or timeout, default 240s), prints it,
      and marks it consumed via <file>.feedback.offset. Exit 0 with feedback,
      exit 3 on timeout with none — just poll again.

Session identity is the canonical file path; queued feedback is file-backed,
so it survives server restarts and interrupted polls.
"""
import json, os, pathlib, sys, threading, time, webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer


def paths(file):
    f = pathlib.Path(file).resolve()
    return f, pathlib.Path(str(f) + ".feedback.jsonl"), pathlib.Path(str(f) + ".server.json"), pathlib.Path(str(f) + ".feedback.offset")


def cmd_serve(file, port=0, open_browser=False):
    f, fb, meta, _ = paths(file)
    if not f.exists():
        sys.exit(f"not found: {f}")

    class H(BaseHTTPRequestHandler):
        def _json(self, obj, code=200):
            body = json.dumps(obj).encode()
            self.send_response(code)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def do_GET(self):
            if self.path == "/studio-ping":
                return self._json({"ok": True})
            if self.path == "/studio-mtime":
                return self._json({"mtime": f.stat().st_mtime})
            if self.path in ("/", "/index.html", "/" + f.name):
                body = f.read_bytes()
                self.send_response(200)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)
                return
            self._json({"error": "not found"}, 404)

        def do_POST(self):
            if self.path != "/feedback":
                return self._json({"error": "not found"}, 404)
            try:
                n = int(self.headers.get("Content-Length", 0))
                data = json.loads(self.rfile.read(n).decode() or "{}")
                text = str(data.get("text", "")).strip()
                assert text
            except Exception:
                return self._json({"error": "bad body"}, 400)
            with open(fb, "a", encoding="utf-8") as out:
                out.write(json.dumps({"ts": time.time(), "text": text}) + "\n")
            self._json({"queued": True})

        def log_message(self, *a):
            pass

    srv = ThreadingHTTPServer(("127.0.0.1", port), H)
    chosen = srv.server_address[1]
    meta.write_text(json.dumps({"port": chosen, "pid": os.getpid()}))
    url = f"http://127.0.0.1:{chosen}/"
    print(f"Doc Studio serving {f.name} at {url}  (Ctrl-C to stop)", flush=True)
    if open_browser:
        threading.Timer(0.3, lambda: webbrowser.open(url)).start()
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        pass


def cmd_poll(file, timeout=240):
    f, fb, _, off = paths(file)
    consumed = int(off.read_text()) if off.exists() else 0
    deadline = time.time() + timeout
    while time.time() < deadline:
        if fb.exists():
            lines = fb.read_text(encoding="utf-8").splitlines()
            if len(lines) > consumed:
                fresh = lines[consumed:]
                off.write_text(str(len(lines)))
                for line in fresh:
                    try:
                        print(json.loads(line)["text"])
                        print("---")
                    except Exception:
                        print(line)
                return 0
        time.sleep(0.5)
    print("(no feedback within timeout — poll again or ask the user)")
    return 3


def main():
    args = sys.argv[1:]
    if len(args) < 2 or args[0] not in ("serve", "poll"):
        sys.exit(__doc__)
    if args[0] == "serve":
        port = int(args[args.index("--port") + 1]) if "--port" in args else 0
        cmd_serve(args[1], port=port, open_browser="--open" in args)
    else:
        t = int(args[args.index("--timeout") + 1]) if "--timeout" in args else 240
        sys.exit(cmd_poll(args[1], timeout=t))


if __name__ == "__main__":
    main()
