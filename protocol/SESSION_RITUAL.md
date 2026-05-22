# Session ritual

What every participating agent does when it starts work in the bare-loop protocol.

## On session start

1. **Check the inbox** at `${BARELOOP_INBOX}/` for any unread files addressed to you (your routing token in the filename).
2. **Read each addressed file** in chronological order. For each one: take the action it asks for, write a reply if appropriate, then move the original to `_processed/YYYY-MM-DD/`.
3. **Read your project doc** (e.g., `PROJECT.md`) for current state, recent decisions, and pending work.
4. **Surface to the operator** anything you found in the inbox that they should know about. Don't action without confirmation if the file looks obsolete or ambiguous.
5. **Resume work** on whatever you were doing before the previous session ended.

## On session end (or just before a long pause)

1. Update `PROJECT.md` with what changed in this session.
2. Ensure no half-actioned inbox files are left in the inbox root. Either action and move, or leave with a note.
3. If you opened a long-running process (a job, a download, a serve), document where its log/state lives.

## Cross-agent coordination

When you need to ask another agent (in a different pane) to do something:

1. Write a markdown file into the shared inbox using the filename convention from `CONVENTION.md`.
2. Continue your own work; the router will deliver to the recipient.
3. Wait for a reply file with `<them>__to__<you>` in the filename.

Never try to message another agent directly. The inbox is the durable channel.

## On encountering an unrecognized file

If the inbox contains a file with a malformed filename or content you don't understand: leave it alone, log a note, surface to the operator. Do not action or move files you don't recognize.
