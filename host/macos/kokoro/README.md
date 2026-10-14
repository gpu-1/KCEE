# Local Kokoro voice output

Implemented: native CPU ONNX synthesis of verified saved run summaries, signed local queue, bounded requests, hash-checked WAV delivery and opt-in browser playback. The viewer exposes Prepare voice summary for bracket structural studies. Audio never plays automatically; browser controls provide play/pause/mute. Selecting another run stops playback and clears the previous audio. whisper.cpp input remains a scaffold.

## Provision and start

Use a Python 3.12 executable (tested on this Apple Silicon Mac):

```sh
python3 scripts/provision_kokoro.py --python /absolute/path/to/python3.12
python3 scripts/start_voice_worker.py
# Or start the whole workspace including already provisioned voice:
python3 scripts/start_kcee.py --voice
```

Provisioning explicitly downloads fixed upstream model-release assets and pinned PyPI packages into ignored project-local directories. Runtime synthesis uses only those files and verifies their hashes. The runtime manifest records locally computed SHA-256 hashes, upstream URLs, release and licenses; that release supplied no asset digest, so these are recorded local trust anchors, not upstream signed checksums. Weights stay in `models/kokoro/`, the isolated Python environment in `.local/kokoro/`, and transport/logs in `.local/voice/`. Reprovision the environment on Mac Studio rather than copying its interpreter paths.

No host TCP listener, cloud TTS, runtime model download or microphone access is used. The API mounts only voice transport, not the Python environment or model files. The native worker accepts signed UUID jobs with a 30-second delivery deadline, at most eight queued/processing jobs and 600 text characters. A synthesis subprocess has a 120-second limit; WAV output is capped at 120 seconds, 24 kHz mono PCM16. Responses retain source run/summary, model-manifest and audio hashes and expire after one hour. The API rechecks saved source integrity; the browser independently checks audio bytes before enabling playback.

This first phase is manual result-summary preparation. Automatic warning speech, priority scheduling, streaming and cancelling active inference remain pending. Playback can be paused/muted immediately. Existing saved summary artifacts are unchanged.

Upstream: [Kokoro ONNX](https://github.com/thewh1teagle/kokoro-onnx), [model release](https://github.com/thewh1teagle/kokoro-onnx/releases/tag/model-files-v1.0). Runtime license MIT; model license Apache-2.0.

Stop voice alone with `python3 scripts/stop_voice_worker.py`. Full CLI shutdown also stops voice; the website Engineering services controls still affect geometry/structural workers only.
