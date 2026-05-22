# Inbox filename convention (auto-routed)

The inbox router (`router.py`) auto-delivers new mail to the recipient agent's tmux window. For routing to work, **every new file must use this exact filename format**:

```
YYYY-MM-DD_HHMM_<from>__to__<recipient>__<subject>.md
```

- `<from>` / `<recipient>`: a canonical token equal to the recipient's tmux window name. Lowercase letters and digits only.
- The delimiter is a literal double-underscore: `__to__`. Use single `_` inside `<subject>` freely.
- `<subject>` may contain single underscores or hyphens, but not additional double-underscores.

Examples:

```
2026-05-21_0915_agent1__to__agent2__hello.md
2026-05-21_1030_agent2__to__agent1__reply.md
2026-05-21_1145_agent1__to__operator__status-update.md
```

## Delivery semantics

- The router polls the inbox directory every 10 seconds.
- When a new file is detected, the router parses the filename and resolves the recipient by matching the recipient token against tmux window names in the configured session.
- The router types a one-line nudge into the recipient's tmux window (using `tmux send-keys`) telling the recipient agent that mail has arrived and where to read it.
- The router does **not** move files. Closing the loop is the recipient's responsibility: after reading and acting on the file, the recipient agent moves it to `_processed/YYYY-MM-DD/`.

## Routing fallbacks

- If a recipient token has no matching tmux window, the file falls through to a configurable `BARELOOP_FALLBACK_RECIPIENT` (no default; unset means no fallback). This is useful when an agent is offline or its pane has crashed.
- Files using the old single-`_to_` form (or no recipient token) are NOT auto-routed. The router logs them as "unaddressed" and leaves them in place for manual drain.

## Concurrency caveat

The protocol has no concurrency primitive. If two agents act on the same file in the same poll cycle, race conditions can occur (file moved before recipient reads it). Production deployments should consider a read-before-move invariant or a copy-then-move pattern.
