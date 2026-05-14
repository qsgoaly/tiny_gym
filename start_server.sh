#!/bin/bash
# Launch the sglang server with OTel tracing enabled.
# Use this when you want the server running independently of run.py (e.g. so
# model load happens once across many workflow.py invocations).
#
# Override the trace target with $OTEL_EXPORTER_OTLP_ENDPOINT or disable
# tracing by setting it to empty.

OTLP="${OTEL_EXPORTER_OTLP_ENDPOINT-http://localhost:4317}"
HOST_PORT="${OTLP#http://}"
HOST_PORT="${HOST_PORT#https://}"
HOST_PORT="${HOST_PORT%/}"

ARGS=(
  --model-path Qwen/Qwen3.5-9B
  --tool-call-parser qwen3_coder
  --reasoning-parser qwen3
  --host 0.0.0.0
  --port 30000
  --trust-remote-code
  --enable-metrics
)

if [ -n "$HOST_PORT" ]; then
  ARGS+=(--enable-trace --otlp-traces-endpoint "$HOST_PORT")
fi

exec python -m sglang.launch_server "${ARGS[@]}"
