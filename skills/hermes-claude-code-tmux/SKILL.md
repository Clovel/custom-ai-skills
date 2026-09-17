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

## MCP servers are live — scope and word prompts accordingly

Claude Code here inherits the account's claude.ai MCP servers. **Do not assume a
roster — read it:**

```bash
claude mcp list        # every server, and whether it is authenticated
```

Authentication state is the one fact in this area guaranteed to change: a server gets
connected, a token expires, a new one is added. A roster written into this file is
therefore wrong shortly after it is written, and wrong in the most misleading
direction — it reads as authoritative. Run the command while preparing the dispatch and
word the prompt against what it actually returns.

Consequences for a dispatch:

- **Never tell CC it has "no network access"**, and never write that a tracker it has
  an MCP for is out of its reach. The claim is false, and CC will faithfully report
  back "could not verify — no access" for something it could have checked itself. A
  delegated agent's self-report about its own capabilities is not evidence: run
  `claude mcp list`, don't believe it.
- **Name the systems to cross-check** in the prompt ("verify the release against
  Sentry via MCP", "read the issue's current body via Linear") and require each claim
  to be labelled *verified via MCP* or *taken on trust*.
- **Not everything is covered.** A self-hosted GitLab and a Kubernetes cluster are not
  in that roster, so those claims stay yours to verify with `glab`/`kubectl`. State
  that explicitly rather than letting CC guess which facts it owns.
- **A read-only run needs the restriction spelled out.** MCP tools can write to
  external systems — an audit must say "read only, change nothing in Linear/Sentry"
  and keep the `--settings` deny list, or a review can end in a mutated issue.
- **Do not pass `--bare` or `--strict-mcp-config`** on a task that needs those
  servers; both cut MCP discovery off.

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

## Model choice

**Which model a task warrants is decided in `hermes-code-delegation`, not here** — it
owns the tiers, and the rule that one of them is never selected without the user asking.
Restating any of that in this skill is how the two come to disagree.

Mechanically: pass `--model <alias-or-full-name>`, or omit it for the account default.
Aliases follow Anthropic's line-up and change over time — confirm the current ones with
`claude --help` (the `--model` help text lists them) rather than assuming. For a
Claude-model second opinion, always go through Claude Code; do not substitute a direct
API call to a Claude model via a reseller.

## Read-only / audit runs: pre-collect evidence, then grant no Bash

For an audit or review, do the collection **yourself** and let Claude Code only read.
A credentialed host plus `--allowedTools "Bash"` is a blank cheque, and print mode
cannot prompt, so a tool you forget to grant is a silent stall — not an error.

1. **Dump every artifact into one workdir** (`raw/` files: configs, `sshd -T`-style
effective output, unit cats, log extracts) so CC needs no shell. Never copy private
keys, the system password database, or the agent's own home directory into the
workdir; public keys and fingerprints are fine.
2. **Write a `SOURCES.md`** naming each artifact and the exact command that produced
it, plus a "known gaps" list. CC cites `file:line` against artifacts, and a negative
claim ("fail2ban is absent") needs its own citation to be checkable.
3. **Gate tools with a settings file, not just `--allowedTools`** — `--settings ./cc-settings.json`
with `permissions.allow` scoped to the workdir (`Read(//abs/workdir/**)`) and
`permissions.deny` naming `Bash` plus every secret path. Deny is what makes the
"no secrets" claim enforceable rather than aspirational.
4. **Verify CC's citations before delivering.** Parse its JSON output and check that
every referenced `file:line` exists and the line count is not exceeded; CC will cite
line 1 of a 0-byte file and call a sampled log complete.

### Artifacts that arrive after a run started are invisible to it

CC reads the workdir as it goes, so a file you add mid-run may never be opened — a
first pass finished still asserting "X is unknown" after X's evidence had landed.
Collect first, dispatch second; when evidence is genuinely late, do a second pass with
`--resume <session_id>` and a short prompt listing only what changed, saying explicitly
"do not re-audit from scratch, keep finding IDs stable". Check the deliverable with
`grep` for the new artifact's filename to prove the fold-in actually happened.

Budget: an opus audit pass over ~25 artifacts runs 15–25 minutes and can exceed
$3 of API-equivalent cost; size `--allowedTools` and the artifact set accordingly.

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
- **Sweep by name, never with `tmux kill-server`.** Other Hermes turns, cron jobs and
the user's own runs share `/tmp/tmux-<uid>/default`; `kill-server` destroys every
  session on that socket — including sessions deliberately left alive with
  `remain-on-exit on` so a finished run can still be inspected, whose pane scrollback
  exists nowhere else. Kill only the names you created:

```bash
tmux ls                                          # see what is actually running
tmux kill-session -t "$S" 2>/dev/null || true     # your own handle only
```

  If a session you did not create is present, leave it and report it instead of
  cleaning it up.
