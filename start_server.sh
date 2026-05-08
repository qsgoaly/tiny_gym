#!/bin/bash
python -m sglang.launch_server \
    --model-path Qwen/Qwen3.5-9B \
    --tool-call-parser qwen3_coder \
    --host 0.0.0.0 \
    --port 30000 \
    --trust-remote-code \
    --reasoning-parser qwen3
