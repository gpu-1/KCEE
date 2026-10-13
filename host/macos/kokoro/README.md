# Kokoro native audio
Port 8083 reserved for local voice gateway. Pre-provision weights locally; avoid implicit Hugging Face downloads at runtime. Implement bounded priority speech queue, mute, cancellation and macOS audio output. The demo only creates a voice-summary artifact. whisper.cpp port 8084 handles opt-in local transcription. Record voice/model hashes and license.
