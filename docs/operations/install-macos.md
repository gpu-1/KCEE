# macOS installation
1. Run the standard-library demo using Python 3.9+.
2. Install Docker Desktop for Apple Silicon and enable its daemon. Copy .env.example to .env, choose separate local admin/application database passwords, validate Compose, then build services.
3. For viewer development install Node 22 and use npm ci / npm run dev in viewer. The dependency lock and container digest are already committed.
4. Native integrations: provision compatible .NET/PicoGK, llama.cpp Metal binary and local GGUF weights, whisper.cpp and local models, Python Kokoro and local voice weights. Verify upstream licenses and record exact versions/checksums in host/macos/runtime-manifest.example.json before enabling. No model downloads are automatic.
5. Keep native listeners on loopback until a restricted authenticated gateway is implemented. Do not run launch agents automatically yet.

Upstreams: https://picogk.org/doc/setup.html ; https://github.com/ggml-org/llama.cpp ; https://github.com/ggml-org/whisper.cpp ; https://github.com/hexgrad/kokoro ; https://github.com/pgvector/pgvector
