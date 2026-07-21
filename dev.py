#!/usr/bin/env python3
from __future__ import annotations

import argparse
import os
import threading
import webbrowser
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path


DEFAULT_HOST = "127.0.0.1"
# Falls back to the harness-assigned PORT env var (set when 4173 is already
# taken) so autoPort in .claude/launch.json can hand this server a free
# port without needing a hardcoded --port flag.
DEFAULT_PORT = int(os.environ.get("PORT", 4173))
ROOT = Path(__file__).resolve().parent
DIST = ROOT / "dist"


def create_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Build, watch, and serve the Moo UI catalog.",
    )
    parser.add_argument(
        "--host",
        default=DEFAULT_HOST,
        help=f"Host interface to bind. Defaults to {DEFAULT_HOST}.",
    )
    parser.add_argument(
        "--port",
        default=DEFAULT_PORT,
        type=int,
        help=f"Port to serve on. Defaults to {DEFAULT_PORT}.",
    )
    parser.add_argument(
        "--open",
        action="store_true",
        help="Open the catalog URL in the default browser after startup.",
    )
    return parser


def display_url(host: str, port: int) -> str:
    display_host = "localhost" if host == DEFAULT_HOST else host
    return f"http://{display_host}:{port}/"


def create_handler():
    return partial(
        SimpleHTTPRequestHandler,
        directory=str(DIST),
    )


def load_build_module():
    import build as catalog_build

    return catalog_build


def watch_sources(stop_event: threading.Event) -> None:
    catalog_build = load_build_module()
    previous = catalog_build.source_snapshot()
    while not stop_event.wait(0.5):
        current = catalog_build.source_snapshot()
        if current == previous:
            continue
        catalog_build.build()
        print("Rebuilt Moo UI catalog.", flush=True)
        previous = current


def main() -> None:
    args = create_parser().parse_args()
    catalog_build = load_build_module()
    catalog_build.build()
    print("Built Moo UI catalog.", flush=True)

    url = display_url(args.host, args.port)
    server = ThreadingHTTPServer((args.host, args.port), create_handler())
    stop_event = threading.Event()
    watcher = threading.Thread(
        target=watch_sources,
        args=(stop_event,),
        daemon=True,
    )
    watcher.start()

    if args.open:
        webbrowser.open(url)

    print(f"Serving Moo UI catalog at {url}", flush=True)
    print("Press Ctrl-C to stop.", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopping Moo UI dev server.", flush=True)
    finally:
        stop_event.set()
        server.server_close()


if __name__ == "__main__":
    main()
