# Inbox

A drop-zone for messages between agents in the bare-loop protocol.

## Why this exists

When agents in separate tmux panes need to coordinate, they pass markdown files through this shared inbox directory. The router process delivers a one-line nudge to the recipient's pane when a new file arrives matching that recipient's routing token.

## How to send a message

Write a markdown file into this directory using the exact filename convention from `CONVENTION.md`:

```
YYYY-MM-DD_HHMM_<from>__to__<recipient>__<subject>.md
```

That's the entire send operation. The router handles delivery.

## How to receive a message

When the router types a nudge into your pane (it looks like `[inbox] mail from <sender>: <path> - read it, action or reply ...`), you:

1. Read the file at the path the nudge gives you
2. Action it (do whatever the message asks for)
3. If you have a reply, write a new file into the inbox using the convention
4. **Move the original file** to `_processed/YYYY-MM-DD/` (create the date subdir if it doesn't exist)

Step 4 is what closes the loop. The router tracks files in the inbox root; once a file has been moved out, the router knows it has been actioned and stops re-delivering it.

## What the operator does on session start

For new operators picking up an existing inbox:

1. List every file in `_inbox/` (excluding `README.md` and `_processed/`).
2. For each file, in chronological order: read it, surface its contents briefly, ask whether to integrate or defer.
3. If integrating: action the file as the addressed recipient would have.
4. After acting, **move** the file to `_processed/YYYY-MM-DD/<original-filename>`. Never delete; keep the audit trail.

## What to avoid

- Don't delete files. Always move to `_processed/`. Audit trail matters.
- Don't process the same item twice. The move-to-`_processed/` step is what prevents that.
- Don't dump all inbox files into a single response. Process one at a time.
- Don't action without confirming. Some items may be obsolete by the time you read them.

## Empty inbox

If the inbox has no pending items: good. Nothing to do.
