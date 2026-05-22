# Validation deployments: three-model comparison

This directory contains conversation logs and per-run notes from three bare-loop deployments performed on 2026-05-21, demonstrating that the protocol runs identical-topology on multiple open-weight LLMs with different origins, serving stacks, and tool-call formats.

## Hardware

All three runs used the same workstation:

- 2× NVIDIA RTX PRO 6000 Blackwell Max-Q (96 GB each, 192 GB total)
- AMD Threadripper PRO 9995WX
- 256 GB system RAM
- CUDA 13.1, driver 590.48.01

Each run pinned the model to a single GPU; the second GPU was reserved for display.

## Summary

| Run | Model | Backend | Tool-call parser | Closed-loop messages | Wall-clock | Tool-call errors |
|---|---|---|---|---:|---|---|
| `qwen_run/` | Qwen3-Coder-Next 80B-A3B FP8 | vLLM | `qwen3_coder` | 18 | ~6 min | 0 |
| `llama_run/` | Llama 3.3 70B Instruct FP8 | vLLM | `llama3_json` | 16 | ~9 min | 0 (but model hallucinated SHA-256 output instead of computing it) |
| `gptoss_run/` | gpt-oss-120b MXFP4 | Ollama | native harmony | 7 | ~10 min | Pathology emerged after ~7 turns (Ollama issues #11704, #12187, #12203) |

## Negative control: Llama 3.3 70B Q8 via Ollama (not included in this directory)

The same Llama 3.3 70B Instruct, served via Ollama with the Llama native chat template, failed at the first tool call. OpenCode's OpenAI-compatible adapter expects function calls in `{"name": ..., "arguments": ...}` format; Ollama's Llama template emits them in `{"name": ..., "parameters": ...}` format. Schema mismatch, the call never satisfies the tool's argument schema. Same model, same client, different serving stack: the vLLM path with the `llama3_json` parser translates correctly into OpenAI-format function calls, the Ollama path does not. **Tool-call viability is determined as much by serving-stack integration as by the model itself.**

## Per-run highlights

### `qwen_run/conversation_log.md`

Cleanest run. Two real tasks completed end-to-end:

1. Organic delegation of 7! computation (peer returned 5040, qwen verified)
2. Operator-injected final task: peer wrote a Python one-liner for the first 10 primes, qwen ran it via Bash, verified output, declared demo complete, both agents stopped on cue

Zero tool-call format errors throughout. ~80 tok/s steady-state.

### `llama_run/conversation_log.md`

US-aligned working option. Bootstrap clean, 16 message exchanges, real cross-pane work demonstrated. Notable model-level failure on the SHA-256 verification task: the agent fabricated a digest string containing non-hex characters rather than executing Python via Bash to compute the real digest. This is distinct from a protocol or serving-stack failure; it is a model-level tool-use discipline weakness. ~25-33 tok/s steady-state.

### `gptoss_run/conversation_log.md`

OpenAI-lineage US-aligned model. Bootstrap clean, organic Fibonacci task delegation completed correctly. After roughly seven autonomous round-trip exchanges, the agent began emitting malformed tool calls consistent with the documented gpt-oss harmony-format parsing pathology in current Ollama. The run was halted at that point and the conversation log here covers the seven clean exchanges before degradation.

## Operational frictions observed (paper-relevant)

1. **Window names must literally match routing tokens.** Initial setup attempts with windows named generically (`test1`, `test2`) silently failed delivery until renamed to match the routing tokens in the filenames.
2. **OpenCode TUI requires manual permission approval** on the first Bash tool invocation per session. `--dangerously-skip-permissions` exists only on `opencode run`, not the TUI.
3. **HuggingFace IP-level rate-limiting** can stop large direct downloads. A working pattern: download via a different IP (here, a NAS), then copy locally.
4. **File-read race conditions** can emerge when both agents act on inbound mail within seconds of each other. The protocol has no concurrency primitive.
5. **Agent stop-intent does not override the protocol's read-and-react loop.** Both agents repeatedly declared "demo complete, stopping" and then immediately processed the next inbox arrival. Production deployments need an explicit stop token or external coordinator.
