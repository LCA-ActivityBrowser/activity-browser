# Embed SHRECC Explorer via local Streamlit + WebEngine

**SHRECC Explorer** is a plugin-level tab (sibling to workflows), not a Create-gated stage. For v1 we embed the existing Brightway-free Streamlit explorer in that tab: the plugin depends on a packaged `shrecc-explorer` distribution that exposes a runnable Streamlit entry, starts one localhost server on first need, shows it in a `QWebEngineView`, and may open the same URL in an external browser. We rejected a Qt rewrite of the three explorer pages (too large for “use the current explorer”) and rejected vendoring page scripts into the plugin (explorer stays the source of truth). Trade-offs accepted: second process, port lifecycle, and weaker CI coverage of the Streamlit UI itself—covered by an injectable explorer session seam and host chrome tests instead.

**Status:** accepted

## Considered options

- Embed Streamlit (chosen)
- Rebuild explorer UI in Qt / Plotly-WebEngine using only `shrecc_explorer` logic
- External-browser-only launch with no in-tab embed

## Consequences

- Plugin gains a runtime dependency on `shrecc-explorer` (including Streamlit) and requires WebEngine for the embed.
- `shrecc_explorer` must ship a stable app entry (package data or console script); that packaging change lives in the explorer repo.
- **Explorer prepare**, data-directory discovery, and process lifecycle live behind a Qt-free session service so Create/Write-style tests stay fast without a real Streamlit server.
