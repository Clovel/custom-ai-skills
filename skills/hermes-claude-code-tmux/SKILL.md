---
name: hermes-claude-code-tmux
description: Required procedure for a Hermes agent invoking the Claude Code CLI. Use whenever about to run `claude`, delegate a coding task to Claude Code, dispatch a subagent run, or resume one. Every invocation goes inside a named detached tmux session — never a direct terminal call. Supersedes the bundled autonomous-ai-agents/claude-code skill where they conflict.
---

# hermes-claude-code-tmux

How a Hermes agent invokes Claude Code. Read this **before** the first `claude` call
of a task, not after one fails.

## Precedence

Where this skill and the bundled `autonomous-ai-agents/claude-code` skill disagree,
**this skill wins**. The bundled skill assumes a foreground call; that assumption is
wrong here.

## Authentication: subscription, not API key

Claude Code is authenticated with a **Claude subscription (OAuth)**, not an
`ANTHROPIC_API_KEY`. Two consequences:

- **Never pass `--max-budget-usd`.** It expresses an API-billing cap, which does not
  apply to subscription auth.
- **Never pass `--bare`.** It skips auto-discovery of skills, hooks, MCP servers,
  subagents and `CLAUDE.md` — exactly the context that should be loaded.

If a `claude` call fails on authentication, do **not** reach for an API key. Re-check
the OAuth session instead; a fresh box needs one interactive `claude` login on the
desktop, because print mode cannot prompt.

## Never call `claude` directly

A direct terminal call blocks the Hermes turn for as long as Claude Code runs. A run
with subagents is minutes, not seconds — long enough that the turn times out, the
work is lost, and the failure looks like a Claude Code bug rather than a dispatch
mistake.

**Every invocation goes inside a named, detached tmux session.** Named, so it can be
found again; detached, so the turn returns immediately.

### Dispatch

```bash
S="cc-$(date +%s)"                     # or a task-derived name; must be unique
tmux new-session -d -s "$S" -c "$WORKDIR" \
  'claude -p "<prompt>" --output-format json --allowedTools "Read,Edit,Bash" > out.json 2>err.log'
echo "$S"                               # return the handle, end the turn
```

### Poll

```bash
tmux has-session -t "$S" 2>/dev/null && echo running || echo done
tmux capture-pane -p -t "$S" | tail -40          # progress without attaching
```

### Collect

```bash
cat out.json                            # keep session_id from the JSON for --resume
tmux kill-session -t "$S" 2>/dev/null || true
```

## Rules that keep dispatch predictable

- **Pre-grant tools explicitly** (`--allowedTools "Read,Edit,Bash"`) or use a
  permission policy file. Print mode cannot prompt, so an ungranted tool is a silent
  stall. Skip-permissions belongs in a container, not on a credentialed host.
- **Keep the `session_id`** from `--output-format json` and pass `--resume <id>` for
  follow-ups, rather than restating context in a new run.
- **One git worktree per parallel run**, with concurrency capped. Two agents in one
  working tree will fight over the index.
- **Retry in one layer only** — Hermes *or* Claude Code, never both. Nested retries
  turn one failure into an exponential pile of them.
- **Never leave sessions behind.** A dead session holds its worktree and its output
  files; sweep them when the task ends.
