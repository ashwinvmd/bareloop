# Bare-loop: a minimal multi-agent coordination protocol via shared inbox

A file-based message-passing protocol for coordinating multiple LLM agents running in separate tmux panes. No queue server, no message bus, no Anthropic dependency. Each agent writes markdown files into a shared directory; a small Python router (`protocol/router.py`) watches the directory and types one-line nudges into the appropriate tmux window via `tmux send-keys`.

This repository accompanies the bare-loop protocol paper (NEJM AI, `AIcs` Case Studies track). It contains:

- The protocol specification (`protocol/`)
- Primer documents that bootstrap a fresh agent into the protocol (`primers/`)
- Three validation deployments on different open-weight LLMs (`deployments/`)
- A quickstart for reproducing the deployment on your own hardware (`QUICKSTART.md`)

## Why this matters

LLM-based multi-agent systems usually depend on closed-source coordination layers (LangGraph, AutoGen, vendor-specific orchestrators) or on the closed model itself doing the orchestration. The bare-loop protocol shows that **the coordination layer can be a 200-line Python script and a filename convention**, and that the protocol is **portable across open-weight LLMs** with no protocol-level changes. This matters for clinical research environments where on-prem deployment without BAA is a hard requirement.

## The protocol in one paragraph

Each agent has a routing token equal to its tmux window name. Agents communicate by writing markdown files into a shared inbox directory using a strict filename convention:

```
YYYY-MM-DD_HHMM_<from>__to__<recipient>__<subject>.md
```

A router process polls the inbox every 10 seconds. When a new file arrives, the router parses the filename and uses `tmux send-keys` to type a one-line nudge into the recipient's pane. The recipient reads the file, takes action (or writes a reply file), then moves the original to `_processed/YYYY-MM-DD/` to close the loop.

No more, no less. The simplicity is the point.

## Repository structure

```
.
├── README.md                          this file
├── LICENSE                            Apache-2.0
├── NOTICE                             Apache-2.0 attribution notice
├── QUICKSTART.md                      deployment recipe for a fresh user
├── protocol/
│   ├── CONVENTION.md                  filename format and routing rules
│   ├── INBOX_README.md                inbox usage guidance for agents
│   ├── SESSION_RITUAL.md              what every agent does on session start
│   ├── router.py                      env-var-configurable router (Python)
│   ├── serve_llama33_fp8.sh           example vLLM serve script (Llama 3.3 70B)
│   └── examples/
│       ├── inbound_example.md         synthetic request
│       └── outbound_example.md        synthetic reply
├── primers/
│   ├── PRIMER_TEMPLATE.md             generic template with ${VARIABLE} placeholders
│   ├── PRIMER_qwen_example.md         filled primer used in the Qwen run
│   └── PRIMER_peer_example.md         filled primer for the second agent
└── deployments/
    ├── README.md                      three-model summary
    ├── qwen_run/
    │   └── conversation_log.md        18 closed-loop messages
    ├── llama_run/
    │   └── conversation_log.md        16 closed-loop messages
    └── gptoss_run/
        └── conversation_log.md        7 closed-loop messages
```

## Three-model validation summary

| Model | Backend | Outcome |
|---|---|---|
| Qwen3-Coder-Next 80B-A3B FP8 | vLLM, `qwen3_coder` parser | Cleanest. 18 messages, zero tool-call errors, real task delegation, clean termination on cue. |
| Llama 3.3 70B Instruct FP8 | vLLM, `llama3_json` parser | US-aligned working option. 16 messages. Model fabricated a SHA-256 digest rather than running Python to compute it (tool-use discipline weakness, distinct from protocol failure). |
| gpt-oss-120b MXFP4 | Ollama | US-aligned (OpenAI). 7 clean exchanges; then the documented harmony-format pathology (Ollama issues #11704, #12187, #12203) caused malformed tool calls in extended multi-tool turns. |
| Llama 3.3 70B Q8 (negative control) | Ollama | Failed at first tool call due to serving-stack-level format adapter mismatch (`parameters:` vs `arguments:`). |

The protocol itself ran identically across all four configurations. Observed differences were model-specific (harmony format, tool-use discipline) and serving-stack-specific (format adapter availability), not protocol-specific.

## Hardware

The validation runs used:

- 2× NVIDIA RTX PRO 6000 Blackwell Max-Q (96 GB each)
- AMD Threadripper PRO 9995WX
- 256 GB RAM
- CUDA 13.1

Lower-end hardware (e.g., a single A6000 or H100) will also work for smaller models. The protocol does not assume any particular hardware tier.

## Reproducing a deployment

See `QUICKSTART.md` for the exact tmux + opencode + router commands. Briefly:

1. Pick two open-weight LLMs and an OpenAI-compatible serving stack (vLLM or Ollama).
2. Stand up the serving endpoint.
3. Configure OpenCode (or another OpenAI-compatible agentic client) to point at it.
4. Create a workspace directory; symlink or copy `protocol/` into it; create an `inbox/_processed/` subdirectory.
5. Open three tmux windows: two for the agents, one for the router.
6. Start the agents and the router; paste a filled primer from `primers/` into each agent's TUI as the kickoff prompt.

## Honest caveats for production deployment

- **Race conditions** can occur when both agents act on the same file in the same poll cycle. Add read-before-move or copy-then-move logic for production use.
- **Stop intent** is not first-class. Agents will respond to inbound mail even if they previously declared the demo complete. Production deployments need an explicit stop signal.
- **Tool-call format compatibility** between the model, the serving stack, and the agentic client is the main deployment friction. Test the specific combination before committing.
- **Tool-use discipline** varies by model. Coding-specialized models (Qwen3-Coder, Devstral, gpt-oss in tool-use mode) are more disciplined than general-purpose instruction-tuned models (Llama 3.3 Instruct, plain gpt-oss).

## Citation

If you use this protocol or the validation deployments in published work, please cite the bare-loop paper:

```
@article{bareloop2026,
  title   = {The bare-loop protocol: a minimal multi-agent coordination layer for on-prem clinical LLM deployment},
  author  = {Viswanathan, Ashwin},
  journal = {NEJM AI},
  year    = {2026}
}
```

(BibTeX entry to be finalized when the paper is published.)

## Authors

Ashwin Viswanathan, MD (corresponding author and copyright holder).
Engineering assistance from Claude (Anthropic), used throughout the protocol design, validation runs, and release preparation.

## License

Apache License 2.0. See `LICENSE` and `NOTICE`.
