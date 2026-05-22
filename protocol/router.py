#!/usr/bin/env python3
"""
router.py - cross-agent message delivery for the shared inbox.

NOT an LLM. A plain polling loop. It never reasons; it parses filenames,
resolves the recipient's live tmux window, checks whether that window is at an
idle agent prompt, and either delivers a one-line nudge (idle) or leaves the
message queued for the next cycle (busy). It never moves files: closing the
loop (move to _processed/) stays with the recipient agent, so _processed/ keeps
meaning "actioned", not merely "delivered".

Filename convention (new mail only):
    YYYY-MM-DD_HHMM_<from>__to__<recipient>__<subject>.md

Legacy files (single _to_, or no recipient token) are reported as
"unaddressed" and left untouched for a manual maintainer drain.
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import re
import subprocess
import time
from datetime import datetime, timezone
from pathlib import Path

# Inbox path and tmux session can be overridden by env vars so a fresh deployer
# doesn't have to edit code. Defaults are workspace-relative so the bundle's
# inbox/ skeleton works out of the box.
INBOX = Path(os.environ.get("BARELOOP_INBOX", "./inbox"))
STATE_FILE = Path(os.environ.get("BARELOOP_STATE_FILE", "./.router_state.json"))
LOG_FILE = Path(os.environ.get("BARELOOP_LOG_FILE", "./router.log"))
TMUX_SESSION = os.environ.get("BARELOOP_TMUX_SESSION", "bareloop")
FALLBACK_RECIPIENT = os.environ.get("BARELOOP_FALLBACK_RECIPIENT", "")
POLL_SECONDS = 10
STUCK_AFTER_HOURS = 6                  # delivered but not actioned -> escalate to fallback recipient if configured

NAME_RE = re.compile(
    r"^\d{4}-\d{2}-\d{2}_\d{4}_(?P<frm>[a-z0-9]+)__to__(?P<to>[a-z0-9]+)__(?P<subj>.+)\.md$"
)

# All CCIs run --dangerously-skip-permissions, so no permission dialog can
# exist and an injected Enter cannot auto-approve anything. The only residual
# risk is a pane that has fallen out of Claude to a bare shell, where the
# nudge would run as a command. So the sole gate is "does this pane look like
# a live Claude TUI?". If none of these signatures are present the CCI is
# probably dead - hold and log (doubles as dead-CCI detection).
CLAUDE_TUI_MARKERS = (
    # Claude Code markers
    "esc to interrupt",
    "bypass permissions on",
    "? for shortcuts",
    "⏵⏵",
    # OpenCode markers (added 2026-05-21 for gpt-oss deployment)
    "ctrl+p commands",
    "OpenCode",
    "Local Ollama",
)

log = logging.getLogger("inbox_router")


# --------------------------------------------------------------------------- #
# tmux helpers
# --------------------------------------------------------------------------- #
def _tmux(*args: str) -> str:
    return subprocess.run(
        ["tmux", *args], capture_output=True, text=True, check=True
    ).stdout


def live_windows() -> dict[str, str]:
    """token -> 'session:index'. Resolved every cycle so renames self-heal."""
    out = _tmux(
        "list-windows", "-t", TMUX_SESSION,
        "-F", "#{window_index}\t#{window_name}",
    )
    mapping: dict[str, str] = {}
    for line in out.splitlines():
        idx, _, name = line.partition("\t")
        mapping[name.strip()] = f"{TMUX_SESSION}:{idx.strip()}"
    return mapping


def capture(target: str) -> str:
    try:
        return _tmux("capture-pane", "-p", "-t", target)
    except subprocess.CalledProcessError:
        return ""


def pane_is_live_claude(target: str) -> bool:
    """
    True iff the pane looks like a running Claude Code TUI. Delivery is safe
    whether Claude is idle or mid-generation: Claude Code queues typed-ahead
    input and processes it at the next turn boundary. We only refuse to inject
    into a pane that is NOT a live Claude session (e.g. crashed to a shell),
    where the nudge would execute as a command.
    """
    pane = capture(target)
    if not pane:
        return False
    tail = "\n".join(pane.splitlines()[-25:])
    return any(m in tail for m in CLAUDE_TUI_MARKERS)


def deliver(target: str, filename: str, frm: str) -> bool:
    """Type a one-line nudge and submit. Returns True on success."""
    msg = (
        f"[inbox] mail from {frm}: {INBOX}/{filename} - read it, "
        f"action or reply with a new note in {INBOX}, then move it to "
        f"{INBOX}/_processed/{datetime.now().strftime('%Y-%m-%d')}/ to close the loop."
    )
    try:
        _tmux("send-keys", "-t", target, "-l", msg)
        _tmux("send-keys", "-t", target, "Enter")
        return True
    except subprocess.CalledProcessError as e:
        log.error("send-keys failed for %s: %s", target, e)
        return False


# --------------------------------------------------------------------------- #
# state
# --------------------------------------------------------------------------- #
def load_state() -> dict:
    if STATE_FILE.exists():
        try:
            return json.loads(STATE_FILE.read_text())
        except json.JSONDecodeError:
            log.warning("state file corrupt; starting fresh")
    return {}


def save_state(state: dict) -> None:
    STATE_FILE.write_text(json.dumps(state, indent=2, sort_keys=True))


# --------------------------------------------------------------------------- #
# main cycle
# --------------------------------------------------------------------------- #
def cycle(state: dict, dry_run: bool) -> None:
    windows = live_windows()
    pending = sorted(
        p for p in INBOX.glob("*.md")
        if p.name not in ("README.md", "CONVENTION.md") and p.is_file()
    )

    seen: set[str] = set()
    live_cache: dict[str, bool] = {}  # one liveness check per window per cycle
    for path in pending:
        name = path.name
        seen.add(name)
        m = NAME_RE.match(name)
        if not m:
            if name not in state.get("_unaddressed", []):
                log.info("UNADDRESSED (legacy/manual drain): %s", name)
                state.setdefault("_unaddressed", []).append(name)
            continue

        frm, to = m["frm"], m["to"]
        recipient_token = to if to in windows else FALLBACK_RECIPIENT
        target = windows.get(recipient_token)

        rec = state.get(name)
        if rec and rec.get("delivered"):
            # already nudged once; escalate if stuck unactioned too long
            age_h = (
                datetime.now(timezone.utc)
                - datetime.fromisoformat(rec["delivered_at"])
            ).total_seconds() / 3600
            if age_h > STUCK_AFTER_HOURS and not rec.get("escalated"):
                maint = windows.get(FALLBACK_RECIPIENT)
                if maint and not dry_run and deliver(maint, name, f"STUCK<-{frm}"):
                    rec["escalated"] = True
                    log.warning("ESCALATED stuck mail to maint: %s", name)
            continue

        if target is None:
            log.error("no window for %s and no %s fallback; skipping %s",
                      recipient_token, FALLBACK_RECIPIENT, name)
            continue

        if dry_run:
            log.info("[dry-run] would deliver %s -> %s (%s)",
                     name, recipient_token, target)
            continue

        if target not in live_cache:
            live_cache[target] = pane_is_live_claude(target)
        if not live_cache[target]:
            log.warning("recipient %s has no live Claude TUI (dead?); "
                        "%s held for next cycle", recipient_token, name)
            continue

        if deliver(target, name, frm):
            state[name] = {
                "delivered": True,
                "delivered_at": datetime.now(timezone.utc).isoformat(),
                "recipient": recipient_token,
                "from": frm,
            }
            log.info("DELIVERED %s -> %s (%s)", name, recipient_token, target)

    # prune state for files the recipient has actioned (moved out of root)
    for gone in [k for k in state if k != "_unaddressed" and k not in seen]:
        log.info("CLOSED (recipient moved to _processed): %s", gone)
        del state[gone]
    if "_unaddressed" in state:
        state["_unaddressed"] = [n for n in state["_unaddressed"] if n in seen]

    save_state(state)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true",
                    help="detect and log only; never send-keys")
    ap.add_argument("--once", action="store_true",
                    help="run a single cycle and exit")
    args = ap.parse_args()

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
        handlers=[logging.FileHandler(LOG_FILE), logging.StreamHandler()],
    )
    log.info("inbox_router start (dry_run=%s, once=%s)", args.dry_run, args.once)

    state = load_state()
    while True:
        try:
            cycle(state, args.dry_run)
        except subprocess.CalledProcessError as e:
            log.error("tmux error (session '%s' attached?): %s", TMUX_SESSION, e)
        except Exception:                       # never let the loop die
            log.exception("unexpected error in cycle")
        if args.once:
            break
        time.sleep(POLL_SECONDS)


if __name__ == "__main__":
    main()
