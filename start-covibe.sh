#!/usr/bin/env bash
# start-covibe.sh — Start Ollama + covibe-router
# Usage: bash start-covibe.sh [--stop]

set -e
REPO_DIR="$(cd "$(dirname "$0")" && pwd)"
OLLAMA_BIN="/tmp/OllamaApp/Ollama.app/Contents/Resources/ollama"
OLLAMA_PID_FILE="/tmp/ollama.pid"
ROUTER_PID_FILE="/tmp/covibe_router.pid"

# Use the app if /tmp copy is gone (e.g. after reboot)
if [ ! -f "$OLLAMA_BIN" ]; then
  # Re-extract from zip if available
  if [ -f "/tmp/Ollama.zip" ]; then
    cd /tmp && unzip -q Ollama.zip -d OllamaApp
  else
    echo "❌ Ollama binary not found at $OLLAMA_BIN"
    echo "   Run: curl -L 'https://github.com/ollama/ollama/releases/download/v0.17.4/Ollama-darwin.zip' -o /tmp/Ollama.zip && cd /tmp && unzip -q Ollama.zip -d OllamaApp"
    exit 1
  fi
fi

if [ "$1" = "--stop" ]; then
  echo "Stopping services..."
  [ -f "$OLLAMA_PID_FILE" ] && kill $(cat "$OLLAMA_PID_FILE") 2>/dev/null && echo "Ollama stopped"
  [ -f "$ROUTER_PID_FILE" ] && kill $(cat "$ROUTER_PID_FILE") 2>/dev/null && echo "Router stopped"
  exit 0
fi

# Start Ollama
if ! curl -s http://localhost:11434/ > /dev/null 2>&1; then
  echo "Starting Ollama..."
  "$OLLAMA_BIN" serve > /tmp/ollama_server.log 2>&1 &
  echo $! > "$OLLAMA_PID_FILE"
  sleep 3
  echo "✅ Ollama started (PID: $(cat $OLLAMA_PID_FILE))"
else
  echo "✅ Ollama already running"
fi

# Start covibe-router
if ! curl -s http://localhost:8888/health > /dev/null 2>&1; then
  echo "Starting covibe-router..."
  cd "$REPO_DIR"
  python3 covibe-router/router.py > /tmp/covibe_router.log 2>&1 &
  echo $! > "$ROUTER_PID_FILE"
  sleep 3
  echo "✅ Router started (PID: $(cat $ROUTER_PID_FILE))"
else
  echo "✅ covibe-router already running"
fi

echo ""
echo "=== Status ==="
curl -s http://localhost:8888/health | python3 -m json.tool
echo ""
echo "Logs: /tmp/ollama_server.log | /tmp/covibe_router.log"
