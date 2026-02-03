#!/bin/bash

# 1. Start Ollama in the background
echo "🦙 Starting Ollama Server..."
ollama serve &

# 2. Background Process: Wait for Ollama & Pull Model
(
    echo "⏳ (Background) Waiting for Ollama to be ready..."
    # Loop until Ollama responds
    until curl -s http://127.0.0.1:11434/api/tags >/dev/null; do
        sleep 2
    done
    
    echo "⬇️ (Background) Pulling AI Model: qwen2.5:1.5b..."
    echo "Please wait... this may take a few minutes on local CPU."
    ollama pull qwen2.5:1.5b
    echo "✅ (Background) Model Ready!"
) &

# 3. Start Node.js Server IMMEDIATELY (Satisfy HF Health Check)
echo "🚀 Starting Chatbot Server..."
npm start
