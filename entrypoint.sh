#!/bin/bash

# Start Ollama in the background
echo "🦙 Starting Ollama Server..."
ollama serve &

# Wait for Ollama to be ready
echo "⏳ Waiting for Ollama to start..."
sleep 10

# Pull the requested model (Qwen 1.5B)
# 'qwen2.5:1.5b' is a great balance of speed/intelligence for CPU
MODEL_NAME="qwen2.5:1.5b"

echo "⬇️  Pulling AI Model: $MODEL_NAME..."
ollama pull $MODEL_NAME

echo "✅ Model ready!"

# Start Node.js Server
echo "🚀 Starting Chatbot Server..."
npm start
