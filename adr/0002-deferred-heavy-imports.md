# Deferred imports of heavy dependencies

Startup and tests must stay responsive despite large Brightway and Qt stacks. Activity Browser deliberately delays importing heavy packages (see startup threads in `activity_browser/__main__.py`) rather than pulling everything in at module import time. Prefer following existing deferred-import patterns when adding code on hot import paths; do not reintroduce costly top-level imports without a strong reason and tests/CI awareness.
