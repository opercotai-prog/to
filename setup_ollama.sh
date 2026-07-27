#!/usr/bin/env bash
set -euo pipefail

echo "Installing Ollama..."
curl -fsSL https://ollama.com/install.sh | sh

echo "Starting Ollama server..."
if pgrep -af "ollama serve" >/dev/null 2>&1; then
  echo "Ollama server is already running."
else
  nohup ollama serve > /tmp/ollama.log 2>&1 &
fi

for _ in $(seq 1 30); do
  if curl -s http://127.0.0.1:11434/api/tags >/dev/null 2>&1; then
    break
  fi
  sleep 2
done

echo "Pulling model llama3.2:1b..."
ollama pull llama3.2:1b

echo "Ollama setup complete."
echo "Run: curl http://localhost:11434/api/generate -d '{\"model\":\"llama3.2:1b\",\"prompt\":\"Hello\",\"stream\":false}'"
