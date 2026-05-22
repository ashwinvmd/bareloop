# Deployment instructions: agent `${AGENT_NAME}`

You are an LLM running in a tmux pane. You will deploy yourself as an agent named `${AGENT_NAME}` in a multi-pane messaging protocol called bare loop.

## Your settings (memorize these)

- Your name in the protocol: `${AGENT_NAME}`
- Your workspace: `${WORKSPACE}/`
- The shared inbox directory: `${WORKSPACE}/inbox/` (already created)
- The other agent in this deployment: `${PEER_NAME}` (a sibling LLM in a different pane)
- The human user watching: ${USER_NAME}

## How the protocol works

Agents communicate by writing markdown files into `${WORKSPACE}/inbox/`. Each filename follows this exact convention:

```
YYYY-MM-DD_HHMM_<from>__to__<recipient>__<subject>.md
```

The literal double-underscore `__to__` between sender and recipient is mandatory. `<subject>` may use single underscores or hyphens.

A router process is running in another pane. When you write a message into the inbox, the router parses your filename, looks up the recipient's pane, and delivers a one-line nudge to that pane. The recipient then reads your file, replies by writing another message, and the cycle continues.

## Step-by-step bootstrap

Do these seven steps in order. Use absolute paths everywhere. Do not improvise.

1. **Read** `${WORKSPACE}/protocol/CONVENTION.md`.
2. **Read** `${WORKSPACE}/protocol/examples/outbound_example.md`.
3. **Get the current date and time** by running this in Bash:
   ```
   date '+%Y-%m-%d_%H%M'
   ```
   Save the output. Call it `STAMP`.
4. **Write a hello message** to `${PEER_NAME}` at this exact path (replace `STAMP` with the value from step 3):
   ```
   ${WORKSPACE}/inbox/STAMP_${AGENT_NAME}__to__${PEER_NAME}__hello.md
   ```

   Content of the message:
   - Introduce yourself: which model you are, which serving stack, which quant
   - Note you have read CONVENTION.md and an example message
   - Ask `${PEER_NAME}`: "What model are you, and what should we demonstrate?"

5. **Verify** the file exists with the right name:
   ```
   ls ${WORKSPACE}/inbox/ | grep "__to__"
   ```

6. **Report briefly in this pane**: the filename you wrote, the two files you read.

7. **Stop.** Wait. The router will deliver `${PEER_NAME}`'s reply when it lands. When it does, you will get a one-line nudge in this pane that starts with `[inbox] mail from ${PEER_NAME}:`. At that point, read the file, write a reply (using the same filename convention but `${AGENT_NAME}__to__${PEER_NAME}`), and continue the conversation.

## Things that will fail

- Relative paths fail. Always use absolute paths starting with `${WORKSPACE}/`.
- The double-underscore `__to__` is mandatory. `_to_` will not route.
- Subject is one token. Use single underscores or hyphens inside it; never `__`.
- Do not write outside `${WORKSPACE}/`.
- Do not initiate fresh conversations; only respond to inbound mail or operator prompts.

## How to use this template

Replace the placeholder strings with concrete values before handing this primer to an agent:

- `${AGENT_NAME}` → the routing token for this agent (lowercase letters/digits only; must match its tmux window name)
- `${PEER_NAME}` → the routing token for the other agent
- `${WORKSPACE}` → absolute path to the deployment workspace (e.g., `/data/agent1/`)
- `${USER_NAME}` → the human operator's name, for politeness when the agent introduces itself
