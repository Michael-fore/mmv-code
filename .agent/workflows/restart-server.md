---
description: Restart the local MMV dev server (kills port 3000, installs deps if needed, starts fresh)
---

# Restart Dev Server

Use this when you need to restart the MMV front-end server after code changes.

// turbo-all

## Steps

1. Kill any existing server on port 3000:

```bash
lsof -ti :3000 | xargs kill 2>/dev/null || true
```

2. Wait for port to free up:

```bash
sleep 1
```

3. Ensure dependencies are installed (workaround for macOS sandbox restrictions on node_modules):

```bash
if [ ! -d /tmp/mmv-deps/node_modules/express ]; then
  mkdir -p /tmp/mmv-deps
  cp /Users/tako/projects/ai-playground/MMV/mmv-front/package.json /tmp/mmv-deps/
  cd /tmp/mmv-deps && npm install --cache /tmp/npm-cache
fi
```

4. Start the server:

```bash
cd /Users/tako/projects/ai-playground/MMV/mmv-front && NODE_PATH=/tmp/mmv-deps/node_modules node server.js
```

5. Verify in a separate terminal:

```bash
sleep 2 && curl -s http://localhost:3000/api/tools | python3 -c "import json,sys;t=json.load(sys.stdin);print(f'✅ Server ready — {len(t)} tools loaded')"
```

## Notes

- Uses `NODE_PATH` to point to `/tmp/mmv-deps/node_modules` because direct `npm install` in the project dir fails due to macOS extended attributes.
- This is the same as `/sync-tools` but without `--watch` mode.
