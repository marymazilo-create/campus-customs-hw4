#!/bin/bash
# Double-click to run the Campus Customs site (MGT 409 HW 4).
#   Backend  (FastAPI): http://localhost:8000
#   Website  (Vite):    http://localhost:5173  <- opens in your browser
# Close this window (or press Ctrl+C) to stop both.
#
# OneDrive workaround: the Python environment and the website's node_modules live in
# ~/.venvs (outside OneDrive) so syncing can't stall them. The website code is mirrored
# there (scripts/sync_frontend.py), so edits in hw4/frontend still show up live.

cd "$(dirname "$0")" || exit 1
HW4="$(pwd)"
VENV="$HOME/.venvs/mgt409-hw4"
WEB="$HOME/.venvs/mgt409-hw4-frontend"

pause() { echo; read -n 1 -s -r -p "Press any key to close this window."; }

if ! command -v npm >/dev/null 2>&1; then
  echo "Node.js isn't installed. Get the LTS installer from https://nodejs.org, then double-click this again."
  pause; exit 1
fi
if [ ! -f "$HW4/data/campus_customs.db" ]; then
  echo "Missing data/campus_customs.db. Unzip the course data pack into hw4/data/ first."
  pause; exit 1
fi

# 1) Python environment for the backend
if [ ! -x "$VENV/bin/python" ]; then
  echo "One-time setup: creating a Python environment in $VENV ..."
  mkdir -p "$HOME/.venvs" && python3 -m venv "$VENV" || { echo "Setup failed."; pause; exit 1; }
fi
if ! "$VENV/bin/python" -c "import fastapi, uvicorn, dotenv, pydantic_ai" 2>/dev/null; then
  echo "Installing Python packages (about a minute)..."
  "$VENV/bin/pip" install -q --upgrade pip
  "$VENV/bin/pip" install -q -r requirements.txt || { echo "Install failed."; pause; exit 1; }
fi

# 2) Website: mirror the code outside OneDrive and install packages there
# Copies only files whose contents changed (so Vite doesn't restart over and over)
SYNC=("$VENV/bin/python" "$HW4/scripts/sync_frontend.py" "$HW4/frontend" "$WEB")
mkdir -p "$WEB"
"${SYNC[@]}" || { echo "Copying the website code failed."; pause; exit 1; }
if [ ! -x "$WEB/node_modules/.bin/vite" ] || [ "$HW4/frontend/package.json" -nt "$WEB/node_modules/.installed" ]; then
  echo "Installing website packages (a minute or two the first time)..."
  (cd "$WEB" && npm install --no-audit --no-fund) || { echo "npm install failed."; pause; exit 1; }
  touch "$WEB/node_modules/.installed"
fi

# Free the ports if an earlier run is still going
for port in 8000 5173; do lsof -ti tcp:$port | xargs kill 2>/dev/null; done

cleanup() { trap - INT TERM HUP EXIT; echo; echo "Stopping..."; kill $API_PID $SYNC_PID $WEB_PID 2>/dev/null; exit 0; }
trap cleanup INT TERM HUP EXIT

echo "Starting the backend on http://localhost:8000 ..."
(cd "$HW4/backend" && exec "$VENV/bin/python" -m uvicorn main:app --reload --port 8000) &
API_PID=$!

"${SYNC[@]}" --watch &
SYNC_PID=$!

echo "Starting the website on http://localhost:5173 ..."
(cd "$WEB" && exec ./node_modules/.bin/vite --port 5173 --strictPort --open) &
WEB_PID=$!

echo
echo "Running. Leave this window open while you use the site. Close it to stop."
wait $WEB_PID
