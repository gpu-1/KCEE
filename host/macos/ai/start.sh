#!/bin/sh
set -eu
: "${LLAMA_SERVER_BIN:?Set absolute path to llama-server}"
: "${KCEE_MODEL_PATH:?Set absolute path to local GGUF weights}"
exec "$LLAMA_SERVER_BIN" --model "$KCEE_MODEL_PATH" --host 127.0.0.1 --port 8081 -ngl 99
