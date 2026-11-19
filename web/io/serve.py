#!/usr/bin/env python3
"""Serve web/ and POST /compute using the same computation as ./engine."""
from __future__ import annotations

import http.server
import json
import os
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REPO = os.path.dirname(ROOT)


def compute(book: dict) -> dict:
    """Match ./engine - so the page shows what the CLI computes."""
    raw = json.dumps(book)
    out = subprocess.run(
        [os.path.join(REPO, "engine"), "-"],
        input=raw,
        capture_output=True,
        text=True,
        cwd=REPO,
        check=False,
    )
    if out.returncode != 0:
        raise RuntimeError(out.stderr or f"engine exited {out.returncode}")
    return json.loads(out.stdout)


class H(http.server.SimpleHTTPRequestHandler):
    extensions_map = {
        **http.server.SimpleHTTPRequestHandler.extensions_map,
        ".js": "text/javascript",
    }

    def __init__(self, *a, **k):
        super().__init__(*a, directory=ROOT, **k)

    def do_POST(self):
        if self.path != "/compute":
            return self.send_error(404)
        length = int(self.headers.get("Content-Length", "0"))
        body = self.rfile.read(length)
        try:
            result = compute(json.loads(body))
            payload = json.dumps(result).encode()
        except Exception as e:  # noqa: BLE001 — surface to the page
            payload = json.dumps({"error": str(e)}).encode()
            self.send_response(500)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(payload)))
            self.end_headers()
            self.wfile.write(payload)
            return
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)


def main() -> None:
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8000
    http.server.ThreadingHTTPServer(("127.0.0.1", port), H).serve_forever()


if __name__ == "__main__":
    main()
