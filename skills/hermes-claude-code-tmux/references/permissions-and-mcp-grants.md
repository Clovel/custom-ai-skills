# Permissions, MCP grants and permission modes

Why a headless run silently lacks a tool, how to grant it, and how to prove the grant
took effect. Dispatch mechanics live in the parent skill's `SKILL.md`.

## Where rules live

| File | Scope | Written by |
| --- | --- | --- |
| `~/.claude/settings.json` | you, in every project on the machine | you, or `/config` |
| `<repo>/.claude/settings.json` | everyone in that repo — commit it | the team |
| `<repo>/.claude/settings.local.json` | you, that repo only | Claude Code, on "Yes, and don't ask again" |
| managed settings | the whole organisation; nothing you set overrides them | your admin |
| `~/.claude.json` | Claude Code's own state: sign-in, MCP server config, per-project trust (`hasTrustDialogAccepted`) | Claude Code |

A standing approval lands in `.claude/settings.local.json` at the **git repository
root**, resolved through worktrees to the main checkout: a worktree of that repo inherits
it, a directory outside it does not. Outside a git repository — or when the root, its
`.git` or its `.claude` is not owned by you — the rule goes next to `.claude/settings.json`
instead.

## Workspace trust

Project rules load only from a **trusted** workspace; `~/.claude.json` keeps that latch in
`projects["<abs path>"].hasTrustDialogAccepted`. Trust resolves **per exact directory**: ancestor
entries do not cover a clone, while a subdirectory of a trusted repo inherits it.

Prove it without touching the live config — copy the global config into a throwaway
`CLAUDE_CONFIG_DIR`, which is where the CLI looks for `.claude.json` when set, and run a local
command (`/usage` needs no API call) from the repo root:

```bash
D=/tmp/trusttest; mkdir -p $D/.claude
python3 -c "import json;json.dump({'projects':{'/abs/parent':{'hasTrustDialogAccepted':True}}},open('$D/.claude/.claude.json','w'))"
cp ~/.claude/.credentials.json ~/.claude/settings.json $D/.claude/
cd "$HOME/repository/<client>/<repo>"
CLAUDE_CONFIG_DIR=$D/.claude HOME=$D claude -p "/usage" --output-format json 2>&1 | grep -c "has not been trusted"
```

`0` means the entry covered the repo, `1` that it did not. Confirm with `projects["<repo path>"]`,
then write the real entries into `~/.claude.json` (atomic write, backup, mode `600`) for every
cloned repo — one per clone, since a parent entry is not enough.

## Precedence

Managed > command line (`--settings`, `--permission-mode`) > project local > shared
project > user. Merging is per key, so a `--settings` file that sets `permissions.allow`
does not erase the allow rules below it — a run-level file adds to them.

Within `permissions`, rules are evaluated **deny, then ask, then allow**; first match
wins and specificity does not reorder them, so a broad deny beats a narrow allow. Deny
holds in every mode including `bypassPermissions`; allow rules have no effect in
`bypassPermissions`.

## Rule shapes

- Built-ins: `Bash`, `Read`, `WebSearch`, `Edit`, or scoped — `Bash(git:*)`,
  `Read(//abs/path/**)`.
- MCP: `mcp__<server>` and `mcp__<server>__*` = every tool of that server;
  `mcp__<server>__<tool>` = one tool; `mcp__<server>__get_*` = a prefix glob.
- **Allow globs need a literal server segment.** `mcp__claude_ai_*` is skipped and grants
  nothing, so "every connector on the account" is one entry per connector.
- The server segment is the connector's display name with every character outside
  `A-Za-z0-9_-` replaced by `_`: `claude.ai Linear` → `claude_ai_Linear`,
  `Microsoft 365` → `Microsoft_365`, `monday.com` → `monday_com`.
- Deny and ask also take globs in the tool-name position — `mcp__*` denies every MCP tool.
- Deny and ask rules naming an unknown tool warn at startup; a typo'd **allow** rule is
  simply inert, so validate a grant with a probe rather than by reading the file.

## Generate the allow list

```bash
claude mcp list          # every server, marked "Connected" or "Needs authentication"
claude mcp list | sed -n 's/^claude\.ai \(.*\): .*/\1/p' | while read -r n; do
  printf '      "mcp__claude_ai_%s__*",\n' "$(printf '%s' "$n" | sed 's/[^A-Za-z0-9_-]/_/g')"
done
```

Sign in first where the list says authentication is needed: a rule for a dark server
changes nothing. Prefer read-shaped globs (`__get_*`, `__list_*`, `__search_*`,
`__find_*`) — a server-wide entry also grants its write tools to unattended runs, which
is exactly the guarantee a read-only dispatch is trying to make.

**Do not hand-invent tool names.** No CLI surface enumerates a connector's tools:
`claude mcp list` gives server names and auth state, `claude mcp get <server>` only
repeats the status. A `--allowedTools` line assembled from guessed names therefore looks
authoritative and is not — a run can call a tool the dispatch never named, because a glob
or a settings rule elsewhere already granted it, and conversely a named tool that does not
exist is inert with no warning. Grant with the read-shaped glob, which needs no names, or
with a rule in a settings file; when you genuinely must name one tool, take the name from
a `tool_use` event in a transcript, never from memory.

## Permission modes

| Mode | Runs without asking |
| --- | --- |
| `default` (Manual) | reads only |
| `acceptEdits` | reads, file edits, common filesystem commands |
| `plan` | reads, plus classifier-approved commands when auto is available |
| `auto` | everything, with background safety checks |
| `dontAsk` | reads plus pre-approved rules; anything that would prompt is denied |
| `bypassPermissions` | everything — containers and VMs only |

- **`dontAsk` is the probe.** Only pre-approved rules run there, so a call that succeeds
  under it proves the allow rule grants; a refusal quotes itself as
  `Permission to use <tool> has been denied because Claude Code is running in don't ask mode`.
- `permissions.defaultMode` is honoured from the **user** settings file only: `auto` and
  `bypassPermissions` written in a project file are ignored and the session falls back to
  the built-in default. `--permission-mode <mode>` overrides for a single run, above every
  file — which is how you neutralise a machine-wide `auto` while testing a rule.
- **`auto` is machine-wide in effect.** It auto-approves actions no allow rule names — a
  shell command outside every rule runs — so it is the lever for "stop all prompts" and
  the wrong one for "stop MCP prompts", where an allow list already suffices.
- Never auto-approved in any mode: tools matched by an ask rule, connector tools the org
  set to `ask`, tools a server marks `requiresUserInteraction`, and `rm`/`rmdir` against a
  critical path. In `dontAsk` those are denied rather than prompted.
- Read the mode a run actually started in from `permissionMode` in the `system`/`init`
  event of `--output-format stream-json --verbose`.

## Prove a grant

```bash
claude -p "Call the MCP tool mcp__claude_ai_Sentry__find_projects (no arguments). You must
attempt this exact call; if it fails, quote the exact error text and print FAILED." \
  --model haiku --output-format stream-json --verbose \
  --permission-mode dontAsk --allowedTools "Read,mcp__claude_ai_Sentry__*"
```

Read the `tool_use` / `tool_result` events, never the closing prose. A permitted call
shows the tool's own output (including an argument-validation error, which still proves
it ran); a denial shows the `don't ask mode` sentence above. A one-turn "tool not
available in this environment" with **no `tool_use` event** means the model never tried —
inconclusive, not a capability answer.

MCP tools are loaded on demand through tool search, so they do not appear in the
`system/init` event's `tools` list and `mcp_servers` there stays empty even when calls
work. Judge capability from a forced call, never from the init event. Separately,
`~/.claude/mcp-needs-auth-cache.json` lists the connectors waiting on sign-in — an
authentication problem that no allow rule resolves.
