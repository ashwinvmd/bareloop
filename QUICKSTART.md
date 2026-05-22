# QUICKSTART: deploy a 2-agent bare loop on your local machine

A minimal recipe for reproducing the validation deployments. Assumes you have a serving stack already running and an OpenAI-compatible agentic client (we use OpenCode in our validation; LiteLLM-based clients should also work).

## Prerequisites

1. **An LLM serving endpoint** at an OpenAI-compatible API URL. Options:
   - Ollama (easiest): `ollama serve` then `ollama pull <model>`
   - vLLM: `vllm serve <model> --enable-auto-tool-choice --tool-call-parser <parser>` (see `protocol/serve_llama33_fp8.sh` for a worked example)
2. **OpenCode** installed: `npm i -g opencode` or follow the OpenCode upstream instructions.
3. **tmux** installed: standard on Linux distributions.
4. **Python 3** with no extra dependencies (the router script uses only stdlib).

## Setup

### 1. Choose a workspace path

Pick a directory that will hold the deployment artifacts. The examples below use `/data/agents/run1/`. Adjust to your environment.

```bash
export WORKSPACE=/data/agents/run1
mkdir -p $WORKSPACE/inbox/_processed
cp -r protocol $WORKSPACE/
```

### 2. Configure OpenCode

Create `~/.config/opencode/opencode.json` with a provider entry for your serving endpoint:

```json
{
  "$schema": "https://opencode.ai/config.json",
  "provider": {
    "local-serving": {
      "npm": "@ai-sdk/openai-compatible",
      "name": "Local serving stack",
      "options": {
        "baseURL": "http://localhost:8000/v1",
        "apiKey": "EMPTY"
      },
      "models": {
        "your-model-id": {
          "name": "Your model display name"
        }
      }
    }
  },
  "model": "local-serving/your-model-id"
}
```

Replace `your-model-id` with the served model name (e.g., `meta-llama/Llama-3.3-70B-Instruct` for vLLM, `gpt-oss:120b` for Ollama).

### 3. Fill in two primer files

Copy `primers/PRIMER_TEMPLATE.md` twice, once for each agent. Replace the placeholder variables:

```bash
cp primers/PRIMER_TEMPLATE.md $WORKSPACE/PRIMER_agent1.md
cp primers/PRIMER_TEMPLATE.md $WORKSPACE/PRIMER_agent2.md
```

Edit each primer:

- `PRIMER_agent1.md`: set `${AGENT_NAME}` to `agent1`, `${PEER_NAME}` to `agent2`, `${WORKSPACE}` to your absolute workspace path, `${USER_NAME}` to your name.
- `PRIMER_agent2.md`: set `${AGENT_NAME}` to `agent2`, `${PEER_NAME}` to `agent1`, and so on.

The routing tokens (`agent1`, `agent2`) must be lowercase letters/digits only and must match the tmux window names you create below.

## Run

### 4. Open a tmux session with three windows

```bash
tmux new -s bareloop
```

Inside the session, create three windows named exactly `agent1`, `agent2`, `router` (in tmux: `Ctrl-b c` for new window, `Ctrl-b ,` to rename).

### 5. Window `agent1`

```bash
cd $WORKSPACE
opencode
```

Once OpenCode loads, paste:

```
Read $WORKSPACE/PRIMER_agent1.md and follow the 7 steps in it exactly. Use absolute paths everywhere. Do not improvise.
```

(Substitute the actual workspace path; OpenCode does not expand environment variables in the prompt.)

### 6. Window `agent2`

Same as window 1 but with `PRIMER_agent2.md`.

### 7. Window `router`

```bash
cd $WORKSPACE && \
BARELOOP_TMUX_SESSION=bareloop \
BARELOOP_INBOX=$WORKSPACE/inbox \
BARELOOP_STATE_FILE=$WORKSPACE/.router_state.json \
BARELOOP_LOG_FILE=$WORKSPACE/router.log \
BARELOOP_FALLBACK_RECIPIENT=agent1 \
python3 $WORKSPACE/protocol/router.py
```

(All env vars are optional; defaults are workspace-relative so running the router from `$WORKSPACE` with the bundled `inbox/` works out of the box. Set `BARELOOP_FALLBACK_RECIPIENT` to route mail with no live recipient window to a chosen agent.)

## What to expect

1. Each agent reads its primer, writes a hello message to the other, and stops.
2. The router (within ~10 sec) detects each new file and types a nudge into the recipient's window.
3. Each agent reads the inbound message and writes a reply.
4. The loop continues until you redirect them with an operator prompt or stop them.

## Stopping

- `Ctrl-c` in the router window to stop delivery
- `Ctrl-c` in each agent window to quit OpenCode (`/exit` also works)
- `tmux kill-session -t bareloop` to nuke the whole session

## Driving a real task

Once both agents are bootstrapped and replying to each other, you can inject a task into one of the panes. Example:

```
This is the final task. Ask the other agent to write a Python one-liner that prints the first 10 prime numbers. When they reply, run their code via Bash, verify the output matches [2, 3, 5, 7, 11, 13, 17, 19, 23, 29], send a final 'verified, demo complete' message, then stop.
```

The agent will write a request to the other, the router will deliver, the other will reply, and the loop converges on the verification.

## Troubleshooting

- **Router logs "no window for X" errors:** tmux window name does not match the routing token in the filename. Rename the window (`Ctrl-b ,`).
- **OpenCode pauses on first Bash tool call:** click "Allow always" in the permission dialog. The `--dangerously-skip-permissions` flag exists for `opencode run` but not the TUI.
- **Agents loop forever on low-content acknowledgments:** the protocol has no built-in stop condition. Inject a task with a termination instruction, or kill one of the agents.
- **Tool-call format errors:** check that your serving stack's tool-call parser matches the model. Llama 3.x needs `--tool-call-parser llama3_json` on vLLM; Qwen3-Coder needs `--tool-call-parser qwen3_coder`.
