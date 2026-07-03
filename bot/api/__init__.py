"""Low-level OSINT source clients (one module per family of sources).

Each source exposes small async functions returning plain ``dict`` results.
Sources that require an API key gracefully return ``{"skipped": ...}`` when the
key is absent, so the bot works out-of-the-box with keyless sources only.
"""
