#!/usr/bin/env python3
"""JARVIS OS — dashboard launcher (voice + live Iron-Man-style interface).

Run:  python gui.py
Starts a local web server and opens the dashboard in your browser. Voice input
and spoken replies run in the browser (use Chrome or Edge) — nothing to install.

The dashboard talks to the SAME orchestrator as terminal mode, so all commands,
agents, memory, safety, and the LLM work identically here.
"""
from __future__ import annotations
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


def main() -> int:
    try:
        from channels.web_server import serve
    except Exception as e:
        print("JARVIS dashboard failed to start (import error):", e)
        return 1
    port = 8765
    for i, a in enumerate(sys.argv):
        if a in ("--port", "-p") and i + 1 < len(sys.argv):
            try: port = int(sys.argv[i + 1])
            except ValueError: pass
    no_open = "--no-open" in sys.argv
    serve(port=port, open_browser=not no_open)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
