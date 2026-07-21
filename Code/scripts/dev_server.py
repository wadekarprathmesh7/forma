#!/usr/bin/env python3
"""Static file server for local preview.

Avoids `python3 -m http.server`, whose argparse setup evaluates
os.getcwd() as an eager default and can crash under sandboxed process
spawners that don't grant that permission at import time.
"""
import http.server
import os
import socketserver

PORT = int(os.environ.get("PORT", "4173"))
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

os.chdir(ROOT)


class Handler(http.server.SimpleHTTPRequestHandler):
    def log_message(self, fmt, *args):
        pass  # keep stdout quiet

    def end_headers(self):
        # Local preview only: never let the browser cache anything, so
        # edited icons/CSS/JS always show up on refresh instead of a stale
        # heuristically-cached copy (SimpleHTTPRequestHandler sends no
        # Cache-Control by default, which browsers are free to cache anyway).
        self.send_header("Cache-Control", "no-store, must-revalidate")
        super().end_headers()


class ReusableServer(socketserver.TCPServer):
    allow_reuse_address = True


with ReusableServer(("127.0.0.1", PORT), Handler) as httpd:
    print(f"Serving {ROOT} at http://127.0.0.1:{PORT}")
    httpd.serve_forever()
