#!/bin/sh
set -eu
: "${WHISPER_SERVER_BIN:?Set absolute path to whisper-server}"
: "${KCEE_WHISPER_MODEL:?Set absolute path to local whisper model}"
exec "$WHISPER_SERVER_BIN" --host 127.0.0.1 --port 8084 -m "$KCEE_WHISPER_MODEL"
