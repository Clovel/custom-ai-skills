# Alternative multiplexer runtimes (tmux replacements)

Companion to the "Switching the dispatch substrate" section of SKILL.md. Read this when a
runtime is proposed as a replacement for the tmux dispatch, or when revisiting one that was
already assessed.

## What the current substrate actually provides

The dispatch recipe depends on four tmux primitives. A candidate has to replace all four, not
just the visible ones:

| Primitive | tmux |
|---|---|
| Liveness + exit code | `#{pane_dead}`, `#{pane_dead_status}` |
| Detached launch that returns the turn | `new-session -d -s <name>` |
| Output capture without attaching | `capture-pane -p`, plus the run's own output file |
| Scrollback after exit | `remain-on-exit on` |

## Assessment checklist

Run these in order. Each step has already caught a wrong "it's better" once.

1. **Read the candidate's own CLI/API reference and search it for the words your procedure
   needs**: `exit`, `dead`, `remain`, `detach`, `headless`, `service`, `systemd`. Absence from
   the documented command list is a finding — phrase it as "nothing documented", not
   "impossible", and never invent a flag to fill the gap.
2. **Find out how it detects state.** If the answer is "it reads the interactive screen", then
   it does not cover `claude -p`, and any wait built on that state can report a not-yet-started
   run as settled. Read the documented fallback for an agent whose rules match nothing.
3. **Check the detach/shutdown semantics in the docs**, then check the tracker for the
   mechanism (not the feature name): a server that stops with the last client takes every
   unattended run with it.
4. **Check how it is driven from outside itself.** Env-var-gated CLIs (`HERDR_ENV=1`-style) and
   "current pane" selectors that silently fall back to the UI-focused pane are the two failure
   modes; both make an unattended caller target the human's window.
5. **Check integration with the agent's own session file** if the candidate claims
   `--resume` restoration. Hooks that report session ids without process identity can be
   clobbered by any nested headless run.
6. **Check what the vendor can push into a running daemon** (remote manifest/config updates,
   auto-install onto a remote host). State it even when it is rules, not code.

## herdr — what was found (project: herdr.dev, "the runtime your coding agents live on")

- Scope: Rust terminal multiplexer, client + background server, real PTYs, `ctrl+b` prefix,
  detach/reattach, JSON CLI + local socket API, worktrees and saved SSH machines as first-class
  objects. Primary docs: <https://herdr.dev/docs/cli-reference/>, `/docs/agents/`,
  `/docs/agent-automation/`, `/docs/session-state/`, `/docs/concepts/`.
- Verdict for this skill: **do not adopt for dispatch**. Gates 1 and 4 fail, gates 2 and 3 have
  open bugs against them.
- Its genuine strength is the human case: sidebar state rollups (blocked / working / done) across
  panes, tabs, workspaces and machines, blocked-state waits instead of hunting for the stuck
  pane, mouse-first UI, `worktree create/remove` per run. That is worth a pilot for interactive
  sessions, and it is a separate recommendation from automation.
- Search hygiene on this project: several unaffiliated domains publish "herdr replaces tmux"
  copy, one advertising a different license than the repo, and a near-empty fork carries the same
  homepage. Verify the canonical repo (homepage match) before quoting any of it.

## If it is ever adopted

- Replace the dispatch with the candidate's run + wait-for-output pair, keep the prompt in a file
  read with `"$(cat …)"`, and keep the per-run worktree rule.
- The acceptance gate before trusting it unattended: prove that an in-flight `claude -p` is
  **never** reported in the settled state (`idle`/`done`), with a run that takes long enough to
  observe. Until that is demonstrated, keep tmux for automated runs and use the candidate only
  for interactive sessions a human is watching.
