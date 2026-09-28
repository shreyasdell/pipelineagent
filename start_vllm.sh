#!/bin/bash

# Script to start vLLM server with Qwen 2.5 7B model
# This will start the vLLM server that the agents will connect to

echo "Starting vLLM server with Qwen 2.5 7B model..."
echo "This may take a few minutes to download the model and start the server..."

# Activate virtual environment
source .venv/bin/activate

# Start vLLM server
# Using Qwen/Qwen2.5-7B-Instruct model
# Serving on port 8000 with OpenAI-compatible API
python -m vllm.entrypoints.openai.api_server \
    --model Qwen/Qwen2.5-7B-Instruct \
    --host 0.0.0.0 \
    --port 8000 \
    --trust-remote-code