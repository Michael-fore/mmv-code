---
description: Restart the dev server and sync all tool manifests
---

# Sync Tools & Restart Dev Server

Use this workflow whenever you need to restart the MMV front-end server
with the latest tool manifests loaded.

// turbo-all

## Steps

1. Kill any existing server on port 3000:

```bash
lsof -ti :3000 | xargs kill 2>/dev/null || true
```

2. Ensure dependencies are installed (workaround for macOS provenance attrs):

```bash
if [ ! -d /tmp/mmv-deps/node_modules/express ] || [ ! -d /tmp/mmv-deps/node_modules/pg ]; then
  mkdir -p /tmp/mmv-deps
  cp /Users/tako/projects/ai-playground/MMV/mmv-front/package.json /tmp/mmv-deps/
  cd /tmp/mmv-deps && npm install --cache /tmp/npm-cache
fi
```

3. Start the dev server with NODE_PATH and watch mode:

```bash
cd /Users/tako/projects/ai-playground/MMV/mmv-front
NODE_PATH=/tmp/mmv-deps/node_modules node --watch server.js
```

4. Verify all tools were discovered by checking the startup banner.
   The tool count should match the number of `.tool.json` files:

```bash
find /Users/tako/projects/ai-playground/MMV -name '*.tool.json' | wc -l
```

## Notes

- **Tool discovery is live** — `manifest-loader.js` queries `GET http://localhost:8001/tools`
  at startup and gets full manifests (name, description, parameters, tags, ontologyLayer)
  across all repos in one call.
- **Fallback chain**: live API → disk scan (`pipelines/` + `tools/manifests/`) → hardcoded registry
- **Adding a new tool**: create a `*.tool.json` manifest and a `*.py` implementation in the
  appropriate repo's directory, then restart the FastAPI service (`kill $(lsof -ti :8001)` +
  restart). The Node server picks it up automatically on next request — no restart of `server.js`
  required since tools are fetched live.
- **`--watch` mode** reloads `server.js` and `manifest-loader.js` on change, but the tool list
  itself is always fetched fresh from the FastAPI service.

## Where to Add New Tool Manifests

**Canonical location** (the only place you should ever create `.tool.json` files):

| Repo | Path |
|------|------|
| `mmv-data` | `mmv-data/pipelines/tools/manifests/` |
| `mmv-tools/underwriting` | `mmv-tools/underwriting/tools/` |
| `mmv-tools/reporting` | `mmv-tools/reporting/tools/` |
| `mmv-agent` | `mmv-agent/pipelines/` |

After adding a manifest, restart the FastAPI service (`docker compose restart tools`) — the Node server picks it up automatically as it fetches live.
