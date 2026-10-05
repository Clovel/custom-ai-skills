---
name: hermes-claude-code-tmux
description: Required procedure for a Hermes agent invoking the Claude Code CLI. Use whenever about to run `claude`, delegate a coding task to Claude Code, dispatch a subagent run, or resume one. Every invocation goes inside a named detached tmux session — never a direct terminal call. Default substrate is an interactive TUI session driven by scripts/cc-drive.py, with print mode the exception. Supersedes the bundled autonomous-ai-agents/claude-code skill where they conflict.
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
- **"Connected" does not mean "callable".** A server listed as connected can still
  refuse an individual tool call for want of a granted permission, and print mode
  cannot run an authorization flow — CC comes back "permission not granted" and stops.
  Ask it to *name* any refused call rather than work around it, then read that system
  with your own connector tools and fold the answer into the deliverable. Deliver the
  fact, not the caveat: a review handed over as "could not check the ticket" is worse
  than one you closed out yourself before reporting.
- **A refused call and an invented one read the same in prose.** CC reports a tool as
  absent — "not available in this environment" — without having attempted any call, and
  does it repeatedly. Only the `tool_use` / `tool_result` events of
  `--output-format stream-json` are evidence about what it could and could not call.
- **Separate auth from permission when a connector is dark.** `claude mcp list` shows
  `✔ Connected` or `! Needs authentication`; a server in the second state needs a
  sign-in and no permission rule will help until then. Permission questions are settled
  by the probes in `references/permissions-and-mcp-grants.md`.

### MCP tools need an explicit grant in a headless run

Print mode cannot prompt, so an MCP tool with no allow rule is denied — and the denial
comes back as prose ("access not authorized", or worse "tool not available in this
environment" with no call attempted), not as an error you can catch. Grant it one of two
ways:

- **Name the tools in `--allowedTools`** (`--allowedTools "Read,mcp__claude_ai_Linear__get_issue"`).
  Verified sufficient with no settings file anywhere on the machine — this is the default
  for a one-off review.
- **Rely on an allow rule.** An interactive "Yes, and don't ask again" writes
  `mcp__<server>__<tool>` into `.claude/settings.local.json` at the git repository root,
  resolved *through worktrees* to the main checkout, so a worktree of that repo inherits
  it while a scratch directory does not. A `--settings` file merges with the lower levels
  instead of replacing them, so a run-level deny list does not wipe the project's grants.
- **Or write the rule once in the user settings file.** `permissions.allow` in
  `~/.claude/settings.json` applies in every project on the machine, scratch directories
  included — the way to stop re-granting the same read tools on every dispatch.
- **When the delegated task *is* a tracker write** (create the issue, post the comment), grant the
  server-wide glob deliberately — `mcp__claude_ai_Linear__*` — and constrain it in prose to the one
  object it may create. Then read that object back with your own connector: a write reported
  without an identifier, URL or read-back is not evidence it happened. House shape, language, label
  and assignee rules: `references/tracker-writes-via-mcp.md`.

Rule syntax (permissions docs): allow globs are accepted only after a literal
`mcp__<server>__` prefix (`mcp__claude_ai_Linear__get_*`); a bare `mcp__<server>` or
`mcp__<server>__*` matches every tool of that server — which also grants its write tools
in unattended runs, so prefer per-tool read globs. There is **no wildcard for a family of
servers**: the server segment must be literal, so `mcp__claude_ai_*` grants nothing and
"every connector on the account" is one entry per connector. Evaluation order is deny,
ask, allow, and a deny cannot be carved out by a narrower allow.

`references/permissions-and-mcp-grants.md` — where each kind of rule lives, the
precedence order, the mode semantics, and the probes that prove a rule grants.

Never accept a delegated run's word that an MCP tool is out of reach: force the call
("Call the MCP tool `<exact name>` with no arguments; you must attempt it; quote the
failure verbatim") and read the events it produced, then grant and re-run.

### Answering a permission dialog yourself, in a live session

A run that hits a wall can be reproduced **interactively** in tmux and driven: start
`claude` with no `-p`, send the prompt, read the dialog with `tmux capture-pane -p`, move
the selection with `send-keys … Down` (confirm with `capture-pane` that the `❯` marker
moved — do not assume), and commit with `Enter`. Send the text and the `Enter` as separate
`send-keys` calls; combined, the text often sits unsent in the input box.

Read the footer before reasoning about why a prompt appeared. The interactive TUI refuses
auto mode for some models ("auto mode unavailable for this model", seen with `haiku`) and
runs Manual instead, while a headless run of the same model still reported
`permissionMode: "auto"`. Interactive and print mode are not the same permission surface.

**Do not count on the prompt's permanent option.** Choosing "Yes, and always allow access
to `<dir>` from this project" for a Bash command left nothing on disk in two folders — one
trusted, one not — before and after a clean `/exit`: no `settings.local.json`, no
`allowedTools` entry in `~/.claude.json` (diffed against its own newest backup), no change
to user settings. MCP tool approvals *do* persist, into `.claude/settings.local.json` at
the git repository root. So answer the dialog to unblock a session, but treat durability as
unproven until you have seen the rule on disk — and when a rule must hold, write it into the
settings file yourself and re-run headless.

## The project's own rules only apply when the workspace is trusted

Claude Code **ignores `<repo>/.claude/settings.json`** — and says so — unless `~/.claude.json`
carries `projects["<abs repo path>"].hasTrustDialogAccepted = true`:

```
Ignoring 20 permissions.allow entries from .claude/settings.json: this workspace has not been trusted.
```

- **Trust is per exact directory, and a parent entry does not cover a clone.** Verified by probe
  on CLI 2.1.274: with `$HOME`, `$HOME/repository` or
  `$HOME/repository/<client>` trusted, a run inside `<client>/<repo>` still reports the
  workspace untrusted; only the repo path itself works. Subdirectories *inside* a trusted repo are
  covered (`apps/web` is fine), so one entry per clone suffices — but a git worktree at a new path,
  and a submodule directory (its own git root), each need their own.
- **Never rely on the project's rules to grant anything.** Grant what the run needs with
  `--allowedTools` regardless: an untrusted workspace drops the team's committed rules silently,
  and the run then reports the resulting denials as prose about its own capabilities.
- `.claude.json` is rewritten by a Claude Code session as it exits, so make trust edits while no
  run is in flight and re-read the file afterwards. Write atomically (parse → modify → temp file →
  `os.replace`), back it up first, keep mode `600`.

Probe recipe: `references/permissions-and-mcp-grants.md`.
Bulk-trusting a machine's clones: `scripts/trust_cloned_repos.py <root>` discovers every git repo
under a root and writes each its own entry, backing up `~/.claude.json` first and verifying the
result — re-run it after cloning a new repo, since trust does not extend to one.

## Before you report what a run did

A run's summary is a claim, not evidence. `references/verifying-a-delegated-run.md` — the checks
that make it yours: why a cached re-run (`Cached: N cached`) proves nothing until you pass
`--force`, how a build command re-dirties generated files the change never touched, verifying a
citation's path and not only its line number, reproducing a refutation yourself, checking the gate a
recommendation is conditioned on before you act on it, the declared-vs-
installed and string-eval-scope traps behind "do we already have this library?", and how to triage a
deploy-window finding against the user's release practice.

## Never call `claude` directly

A direct terminal call blocks the Hermes turn for as long as Claude Code runs. A run
with subagents is minutes, not seconds — long enough that the turn times out, the
work is lost, and the failure looks like a Claude Code bug rather than a dispatch
mistake.

**Every invocation goes inside a named, detached tmux session.** Named, so it can be
found again; detached, so the turn returns immediately.

**Default substrate: an interactive TUI session**, driven by `scripts/cc-drive.py`. It is the
default for delegated codebase work because it can answer a permission dialog or a clarifying
question, keeps several turns in one process, and has no print-mode background ceiling.

### Dispatch (default)

```bash
python3 scripts/cc-drive.py start job1 "$WORKDIR" --model sonnet
python3 scripts/cc-drive.py send  job1 /path/prompt.txt
python3 scripts/cc-drive.py wait  job1 600       # done | needs-input:<kind> | dead | timeout
python3 scripts/cc-drive.py capture job1 120
```

On `needs-input:permission`, run `answer job1 <option_index>` and `wait` again. Repeat
`send`/`wait` for the next turn in the same session. `stop job1` when finished.

### Dispatch (exception): print mode

Use `claude -p` only when you need the machine-readable result object (`--output-format
json`, `--json-schema`), piped stdin, or a run that by construction can never prompt.

```bash
S="cc-$(date +%s)"                     # or a task-derived name; must be unique
tmux new-session -d -s "$S" -c "$WORKDIR" \
  'claude -p "<prompt>" --output-format json --allowedTools "Read,Edit,Bash" > out.json 2>err.log'
echo "$S"                               # return the handle, end the turn
```

### Poll (print mode)

```bash
# Once, right after dispatch: keeps the pane and its scrollback after the run exits.
tmux set-option -t "$S" remain-on-exit on

tmux display-message -p -t "$S" '#{pane_dead}'   # 1 = the run has exited
tmux capture-pane -p -t "$S" | tail -40          # progress without attaching
```

**`has-session` stops being a liveness check the moment `remain-on-exit` is on.** The
session outlives the command, so `tmux has-session && echo running` keeps answering
"running" for a run that finished minutes ago — the pane itself reads
`Pane is dead (status 0)`, which is where you can also read the exit code. Probe
`#{pane_dead}` instead.

**Wait in chunks, and re-poll rather than re-dispatch.** A foreground wait loop here
comes back `timed out` at the terminal tool's cap (~7 minutes) even when a larger
timeout was requested — harmless: the tmux run is untouched and keeps working, so a
cut-off wait means "poll again", never "start over". The output file stays at 0 bytes
until the run finishes, so its size is not a progress signal; the pane is.

### Print mode kills background subagents at 600 s

`claude -p` will not outlive background work it spawned: after 600 s with a background task
still running it writes `Background tasks still running after 600s; terminating` to **stderr**
and exits **0**, and the turn's own summary reads as if it had merely paused ("I'll wait for
the grading agent's completion notification before proceeding"). Exit 0, `stop_reason:
end_turn`, `permission_denials: []` and an empty error field all read as success; the only
evidence is that one stderr line plus half-finished artefacts on disk.

- **A brief that asks for many items to be processed will hit this** by spawning background
  `Task` agents. Say so in the prompt: do the work **in the foreground** (`Task` without
  `run_in_background`, or batches inline).
- **If background work is genuinely wanted, raise the ceiling**: export
  `CLAUDE_CODE_PRINT_BG_WAIT_CEILING_MS=<ms>` (the message names it). Use a large finite value,
  not `0`, unless you accept waiting forever on a stall.
- **Require per-batch writes to disk** so a kill costs at most one batch, then **resume**
  (`--resume <session_id>`) with a prompt naming what landed, what is left, and "do not redo or
  re-fetch anything already on disk" — never re-dispatch.
- This is the third failure shape that presents as a clean exit with the work missing, after the
  OOM kill and the shell-quoting death: read the pane and stderr, never the exit code.

### Watch a run live: the transcript, not the pane

`claude -p` in a detached tmux pane shows **nothing** while it works: print mode buffers its
output and writes only on exit, so `tmux capture-pane` is blank and `out.json` stays at 0 bytes
for the whole run. Attaching the user to that pane is not a live view — it is an empty screen,
and it invites "is it stuck?". The live stream is the transcript JSONL:
`~/.claude/projects/<slug>/<session_id>.jsonl`, appended as the run goes. Render it with
`scripts/cc-live.py <session_id|latest> [lines]` (assistant text, tool calls and truncated
results). The `session_id` is in the transcript directory name's newest file before the run
finishes, and in the `--output-format json` result afterwards.

When the user wants to *steer* rather than watch, neither works retroactively — the choice is
made at dispatch: `claude -p` has no command input surface, so `/remote-control` and any slash
command cannot be injected into a run already in flight, and `--remote-control` is documented as
"start an interactive session with Remote Control enabled" (also printed by `claude --help`). For
an attendable run, dispatch `--output-format stream-json --verbose` (pane shows progress) or an
interactive `claude --remote-control` session in tmux, and say so to the user before starting.

### Collect (print mode)

```bash
cat out.json                            # keep session_id from the JSON for --resume
tmux kill-session -t "$S" 2>/dev/null || true
```

## Switching the dispatch substrate (tmux alternatives)

The tmux session is the substrate of every dispatch here, not a stylistic preference. When a
new "tmux for agents" runtime is proposed — herdr is the current one — the candidate has to
pass four gates, all of them about the **headless** path this agent drives, before adoption is
even a question:

1. **An exit-status / pane-death primitive.** tmux gives `#{pane_dead}` and
   `#{pane_dead_status}`. Without one you cannot tell a finished run from a quiet one, and
   every candidate that omits it collapses back to reading pane text.
2. **Pane processes survive the last client detaching.** Unattended runs have no client
   attached by design; a server that exits when the last client leaves kills the work.
3. **Drivable from a plain non-interactive shell outside the runtime's own panes**, with no
   ambient env var required. That shell is what this agent is.
4. **It must not require the agent to be interactive.** A state machine that only classifies
   an interactive TUI does not cover `claude -p`.

**herdr fails these for our use, so tmux stays.** Its agent-state layer (`idle`/`working`/
`blocked`/`done`) classifies an agent by reading the live bottom of the interactive TUI screen;
a `claude -p` run prints nothing until it exits, so there is no screen to classify, and the
documented fallback state for a recognized agent whose rules match nothing is `idle` — which its
`agent wait` and `agent prompt --wait` treat as *settled*. A wait on a headless run can therefore
return "idle" immediately: the same silent-false-success shape as the OOM kill and the 600 s
ceiling. It also documents no exit-status primitive, carries open bugs on detach-survival and on a
nested headless `claude -p --resume` overwriting the pane's stored session id, and resolves
`--current` to the *UI-focused* pane (the human's) when its env vars are unset. Nesting is lossy in
both directions: run tmux inside a herdr pane and herdr sees `tmux`, not the agent behind it.

Verdict shape for this class of request: the candidate's advertised value is real for a human
supervising several interactive agents, and that is a separate recommendation from automation.
Say both. Detail, the evidence behind each gate and the re-evaluation checklist:
`references/alternative-multiplexer-runtimes.md`.

## Interactive mode: the default substrate (`scripts/cc-drive.py`)

**This is the default substrate for delegated codebase work.** A live interactive `claude`
session inside tmux, driven by `scripts/cc-drive.py`. Print mode (`claude -p`) is the
exception, kept only for a run that needs the machine-readable result object
(`--output-format json`, `--json-schema`) or piped stdin, and that cannot prompt by
construction.

The interactive substrate is the default because it covers what print mode does not:

- the task may stop on a permission dialog or ask a clarifying question (`AskUserQuestion`,
  `ExitPlanMode`), which print mode cannot answer, so it stalls or reports a capability limit,
- the run must outlive print mode's 600 s background-task ceiling (see above),
- the user wants to steer mid-run or watch progress live,
- several turns belong in one process, carrying context without a re-dispatch.

Driver: `scripts/cc-drive.py`. State under `/tmp/cc-drive/<name>/`, tmux session `cc-<name>`.

```bash
python3 scripts/cc-drive.py start  <name> <workdir> [--model M] [-- <extra claude args>]
python3 scripts/cc-drive.py send   <name> <prompt_file>      # multi-line brief lives in a file
python3 scripts/cc-drive.py wait   <name> [timeout_s]        # done | needs-input:<kind> | dead | timeout
python3 scripts/cc-drive.py state  <name>                    # markers, dialog kind, pane tail
python3 scripts/cc-drive.py answer <name> <option_index>     # navigate a permission dialog, then confirm
python3 scripts/cc-drive.py capture <name> [scrollback]
python3 scripts/cc-drive.py stop   <name>
```

Why it stays reliable:

- **Completion comes from a hook, not from scraping the TUI.** `start` writes a per-session
  `--settings` file installing `Stop`, `SessionStart` and `Notification` hooks that touch marker
  files. `wait` returns `done` on the `Stop` marker. `--settings` merges with the lower settings
  levels, so the account's allow list, MCP servers and plugins survive.
- **Send the brief from a file via `paste-buffer`.** Bracketed paste can swallow the first
  `Enter`; `send` resends it when the pasted text is still sitting in the input box. Never inline
  a long prompt into `send-keys`.
- **Answer a dialog by moving the `❯` marker.** `answer` steps with Up/Down, re-reads the pane to
  confirm the marker landed on the requested option, then commits with `Enter`. Never assume the
  movement worked.
- **Structured data is not lost.** The interactive session writes the same transcript JSONL
  (`~/.claude/projects/<slug>/<id>.jsonl`) live; render it with `scripts/cc-live.py latest`.

Permission-surface facts, observed on CLI 2.1.274 and 2.1.280:

- `--permission-mode` accepts `acceptEdits, auto, bypassPermissions, manual, dontAsk, plan`.
  `default` is **not** a value in this version (the bundled `autonomous-ai-agents/claude-code`
  skill lists it; that table is stale).
- With `permissions.defaultMode: "auto"` in `~/.claude/settings.json`, benign commands run
  without a prompt even under a narrow `--allowedTools`: a `Bash` call ran while only `Read` was
  allowed. A dialog appears only for what the auto classifier refuses, or in `manual` mode. The
  interactive TUI refuses auto for some models ("auto mode unavailable for this model", seen with
  `haiku`) and runs manual instead.
- The `Notification` hook did **not** fire for a permission request in the probe. Detect a dialog
  from the pane (`Do you want to proceed?` plus a `❯ 1.` option line), not from that marker.
- A first-run trust dialog appears on an untrusted directory; `start` answers it with `Enter`.

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
5. **Prose does not enforce read-only — capture the tree around the run.** A brief that said "do not
modify, stage, commit, revert or checkout anything" still edited a tracked file mid-review (to test
its own counterfactual) and only reverted it because the harness blocked the follow-up command.
Have the runner record provenance itself, so the claim is checkable instead of trusted:

```bash
echo "HEAD before: $(git rev-parse HEAD)"  > review-head.log
git status --porcelain                    >> review-head.log
<the claude call>
echo "HEAD after: $(git rev-parse HEAD)"   >> review-head.log
git status --porcelain                    >> review-head.log
```

Compare the two halves before you report anything: unchanged HEAD *and* empty status is the only
proof the tree survived, and a run that reverted its own edit leaves no other trace. If falsifying a
claim genuinely needs a mutated tree, **hand it a scratch clone or worktree in the brief** — that is
the fix, not a stricter sentence.
6. **A permission denial inside a run is not a capability limit.** Auto mode's classifier refuses on
prose-shaped grounds — a plain vitest invocation came back as `[Irreversible Local Destruction]` —
and the run then reports it as something it cannot do. Reconstruct what it actually attempted by
pairing the `tool_use` and `tool_result` events in the transcript JSONL (this works with
`--output-format json` too, not only `stream-json`), then decide: benign → re-run or re-word the
command, and say in your report which checks were lost to it.

### Artifacts that arrive after a run started are invisible to it

CC reads the workdir as it goes, so a file you add mid-run may never be opened — a
first pass finished still asserting "X is unknown" after X's evidence had landed.
Collect first, dispatch second; when evidence is genuinely late, do a second pass with
`--resume <session_id>` and a short prompt listing only what changed, saying explicitly
"do not re-audit from scratch, keep finding IDs stable". Check the deliverable with
`grep` for the new artifact's filename to prove the fold-in actually happened.

Budget: an opus audit pass over ~25 artifacts runs 15–25 minutes and can exceed
$3 of API-equivalent cost; size `--allowedTools` and the artifact set accordingly.

## A run that measures memory can OOM the machine

A delegated run that allocates to prove a memory property takes the whole host down when it
overshoots. Seen here: a run swept upload payloads up to 2 GiB on a 7.9 GB host with **no swap**,
the kernel OOM killer fired, and the pane died on **signal 15** mid-work with `out.json` still at
0 bytes and no commits — which reads like a Claude Code crash rather than a host limit. So:

- **Put the ceiling in the brief** ("largest payload in any probe at or below N MiB"), not the
  run's judgement. `node --max-old-space-size` does **not** bound ArrayBuffer/external memory, so
  it is no substitute for a payload cap.
- **Wrap the run in a cgroup** so an overshoot kills the child, not the machine:
  `tmux new-session -d -s "$S" -c "$WORKDIR" 'systemd-run --user --scope -p MemoryMax=3G -p MemorySwapMax=0 --unit=<unique-name> bash /path/runner.sh'`.
  On a small host this is the difference between one lost probe and a rebooting desktop session.
- **A `signal 15` pane with an empty output file is a host kill, not a run failure.** Check
  `journalctl -k | grep -i oom` before blaming the run or the model. Then `--resume <session_id>`
  with a short prompt naming what was interrupted, the resource limit, and "commit before doing
  anything else" — committing per step is what makes a kill cheap.
- **Re-measure rather than trusting the pre-kill numbers** for anything the brief calls decisive;
  the run itself should say which points were taken before the cap and never repeated.

## Rules that keep dispatch predictable

- **Pre-grant tools explicitly** (`--allowedTools "Read,Edit,Bash"`) or use a
  permission policy file. Print mode cannot prompt, so an ungranted tool is a silent
  stall. Skip-permissions belongs in a container, not on a credentialed host.
- **Never hand a delegated run a file path you care about.** A run told to "use
  `--description-file /tmp/x.md`" may rewrite `/tmp/x.md` with its own text first — it treats the
  path as its own to fill. Compose such artefacts from a path the run is not told about, or (as
  here) write the real content after it exits; otherwise your next read of that file silently
  reinstates the run's version.
- **Route approval-gated shell work into the run, not through your own terminal.** This host gates
  some terminal commands behind a user approval prompt — compound or conditional commands, clones,
  registry access. Work the user has already asked for that needs those commands (cloning a repo to
  patch, pulling an image to inspect) belongs inside the dispatched run, where Claude Code's own
  permission model takes the decision and the user is not interrupted mid-task. A prompt the user
  has to answer for mechanical setup is friction the dispatch exists to remove.
- **Keep the `session_id`** from `--output-format json` and pass `--resume <id>` for
  follow-ups, rather than restating context in a new run.
- **One git worktree per parallel run**, with concurrency capped. Two agents in one
  working tree will fight over the index. A *read-only* run whose subject is not the tree
  itself may share the checkout — but then it must attribute any dirt it finds instead of
  cleaning it; see `references/verifying-a-delegated-run.md`.
- **Put the prompt in a file and read it with `"$(cat …)"`.** The runner should call
  `claude -p "$(cat /path/prompt.txt)" …`, **not** inline it as `PROMPT='…'`. In the inline form
  **one apostrophe in the prompt text** closes the string and the session dies in under a second
  with `unexpected EOF while looking for matching` — which reads as a broken model or a dead tmux
  server rather than a quoting mistake. `"$(cat …)"` removes the hazard entirely, so the brief can
  contain apostrophes, quotes and code blocks freely. Still run `bash -n runner.sh` before
  dispatching, and keep the prompt in a file you can re-read and re-dispatch.
- **A killed session is resumable, not lost.** A host restart or a stray `kill-server` takes the
  `claude` process with it; the transcript under `~/.claude/projects/<slug>/<session_id>.jsonl` and
  the working tree survive. Read the `session_id` from the `system`/`init` event of the
  `stream-json` output and re-dispatch with `--resume <session_id>` plus a short prompt naming what
  was interrupted and what to finish — not a fresh run that redoes the exploration. A session that
  was mid-command leaves its edits uncommitted, so tell the run to confirm the change set rather
  than assume it must start over.
- **The run cannot sign commits either.** A detached tmux pane is still not a usable pinentry TTY
  (`gpg: signing failed: Inappropriate ioctl for device`, then the commit fails), so a signed
  commit is unreachable from any non-interactive run. Put `--no-gpg-sign` in the brief and report
  the signed-history mismatch to the user rather than resolving it (see `git-workflow-hermes`).
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
