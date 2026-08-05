# Example Host Shell

The one example host for the Moo UI Generic Host Conformance Kit. It
demonstrates the kit's core claim: the fixtures are plain static files,
and any host that can serve static files can consume the kit — no Moo UI
Core build tooling required.

## What this directory is

- `serve.py` — the whole host: a Python **standard-library-only** static
  server. It mounts `../fixtures/` (the kit's distributable files) under
  the `/fixtures` URL prefix and serves this shell's own `index.html` at
  `/`. It imports nothing from the repository, uses no Jinja, and never
  invokes Core's `build.py`.
- `index.html` — host-owned content, proving the host can keep its own
  pages alongside the mounted kit.

## How to run it

Serve with the system interpreter — deliberately **not** the repository
`.venv`, to prove the host side needs none of Core's dev dependencies:

```sh
cd conformance/host-shell
/usr/bin/python3 serve.py --port 8124
```

Then run the reference runner (the runner *may* use Core's Python
environment; the host must not need it) against the mount prefix:

```sh
python conformance/runner/run.py \
  --base-url http://127.0.0.1:8124/fixtures \
  --report-out report.json
```

A clean, all-passing report against this URL is the end-to-end proof
that the kit works host-neutrally. `tests/test_host_shell.py` repeats
this proof in CI, spawning `serve.py` with a non-venv interpreter and a
stripped environment.

## How another host adapts the pattern

1. Copy the kit's `fixtures/` tree (from the hash-locked release
   artifact) anywhere in the host's web root. The pages reference their
   assets relatively, so the tree keeps its internal layout but may sit
   under any prefix.
2. Serve it with whatever the host already uses — this shell's
   `serve.py` is one minimal example; a WordPress, Odoo, or CDN static
   route works the same way.
3. Point the runner's `--base-url` at the mount prefix and keep the
   report as the host's conformance evidence.

The host remains free to add its own pages, headers, and CSP around the
kit; the contract checks run against the served URLs, not against any
assumption about the host's stack.
