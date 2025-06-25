#!/bin/sh
set -e

# Start ollama serve in the background, redirecting its output to a log file.
echo "Starting Ollama server in background..."
ollama serve > /tmp/ollama.log 2>&1 &
pid=$!

# Wait for the server to be ready by polling its log file for the
# "Listening on" message.
echo "Waiting for Ollama server to be ready..."
retries=15
while [ "$retries" -gt 0 ]; do
    if grep -q "Listening on" /tmp/ollama.log; then
        echo "Ollama server is ready."
        break
    fi
    retries=$((retries - 1))
    sleep 1
done

if [ "$retries" -eq 0 ]; then
    echo "Error: Ollama server did not start in time. Logs:"
    cat /tmp/ollama.log
    exit 1
fi

# Pull the model.
echo "Pulling llama3 model (this may take a few minutes)..."
ollama pull llama3
echo "Model pull complete."

# Bring the server process to the foreground.
echo "Ollama is ready. Bringing server to foreground..."
wait $pid