# Local study assistant

Implemented: native llama.cpp Metal inference with the official Qwen3 4B Q4_K_M model, grounded in one verified structural or thermal study. It explains evidence and cannot edit designs, run tools/solvers, approve engineering acceptance or access arbitrary files. Generated text remains an AI draft, not a verified engineering result.

## Provision and start

```sh
python3 scripts/provision_ai.py
python3 scripts/start_ai_worker.py
# Whole provisioned workspace, with optional local voice:
python3 scripts/start_kcee.py --ai --voice
```

Provisioning explicitly downloads pinned upstream assets: [llama.cpp b11417](https://github.com/ggml-org/llama.cpp/releases/tag/b11417) and [official Qwen3 4B GGUF](https://huggingface.co/Qwen/Qwen3-4B-GGUF/tree/bc640142c66e1fdd12af0bd68f40445458f3869b). The 2,497,280,256-byte model is checked against its upstream LFS SHA-256; the runtime archive is checked against its GitHub release digest. Runtime file hashes and source revisions are retained in `.local/ai/runtime-manifest.json`. Models and binaries remain ignored. Reprovision paths/runtime on Mac Studio rather than copying process IDs or credentials.

The model server binds 127.0.0.1:8081 and requires a private API key for inference. The browser and Docker API never receive this key or a model filesystem mount. A separate signed file queue in `.local/assistant/` carries bounded evidence/question jobs to the host gateway. Its local HTTP requests bypass proxy settings. The server uses the detected MTL device, all model layers requested on GPU, one slot, 8192 context tokens, 768 output tokens and disabled thinking. Metal offload of 37/37 layers was confirmed on this Mac.

The API verifies saved artifacts, selects evidence from recorded results, diagnostics and source-linked exploratory investigations, and hashes the snapshot. Questions are limited to 800 characters, evidence to 20 KB, one pending/processing job, 30-second delivery TTL and 150-second inference timeout. Responses are signed, their source/evidence identities are checked again, and cited category names are schema constrained and validated. Responses retain question, evidence, model/runtime hashes and expire after one day. Local logs and queue data are private to the project account.

Select a bracket FEA, bracket thermal or 1D thermal benchmark study and use Ask about this study. Answers cite evidence categories and remain explicitly labelled as drafts. A passing schema/hash check does not prove every generated claim; check explanations against the displayed results. Fixed tests of a manufacture-approval override and an unsupported thermal question on a structural-only source were refused by the model, but these examples are not comprehensive model safety or engineering validation.

Website Local AI Start/Stop uses the same restricted supervisor as the other services and asks for confirmation on stop. The model and gateway stop separately from geometry/structural/voice. Full CLI shutdown includes them. Changing studies aborts the browser's pending request and clears its answer; cancelling active native inference is not yet implemented.

Stop manually: `python3 scripts/stop_ai_worker.py`. Runtime inference makes no external API calls. Database knowledge ingestion, embeddings, multi-turn conversation, design proposals and AI answer speech remain pending. Heart US English at 1.2× remains the voice-summary default.

Local document references can be included explicitly for verified study questions. See [source ingestion, citation checks and limits](../../../docs/operations/local-knowledge.md). This uses local English full-text retrieval, not embeddings; source citation validity does not certify factual entailment or engineering acceptance.
