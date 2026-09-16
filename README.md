# custom-ai-skills

A collection of custom SKILL.md skills for Claude Code and any agent that
supports the [Agent Skills](https://github.com/anthropics/skills) spec.

Each skill lives under `skills/<name>/SKILL.md`. Distribution is **GitHub
only** — this repo is not published to any skill registry (`skills.sh`,
ClawHub), and no install command should point at one. Clone it, then link or
copy the skills you want into your harness.

```bash
git clone https://github.com/Clovel/custom-ai-skills.git ~/src/custom-ai-skills
```

## Installing

Two ways, both driven by the clone. No registry, no install CLI.

### Harnesses with a skills directory (Claude Code, and anything that reads `SKILL.md`)

Link each skill you want (recommended — one link, then `git pull` is the
update):

```bash
ln -s ~/src/custom-ai-skills/skills/git-workflow ~/.claude/skills/git-workflow
```

Or copy it for a detached snapshot you control:

```bash
cp -R ~/src/custom-ai-skills/skills/git-workflow ~/.claude/skills/
```

Point the path at whatever directory your harness scans (`~/.claude/skills`,
`~/.agents/skills`, a project's `.claude/skills`, ...). Keywords: symlink the
skill directory itself, one link per skill.

### Hermes

Register the clone's `skills/` directory as an external skills directory in
`~/.hermes/config.yaml`:

```yaml
skills:
  external_dirs:
    - ~/src/custom-ai-skills/skills
```

- Paths are `~`/`${VAR}` expanded and resolved; entries that don't exist are
  skipped silently.
- External dirs are **read-only**: autonomous skill maintenance (the curator)
  never edits skills outside the profile's own `skills/` dir, and no copies are
  made — `git pull` in the clone is the entire update.
- Every skill in the directory becomes available. To expose only a subset,
  point `external_dirs` at a directory of symlinks to the individual skills.
- Takes effect in a new session. A local skill of the same name in
  `~/.hermes/skills/` wins over the external one, so don't install these twice.

### Picking individual skills

Both methods are per-skill: link/copy only what you need, or keep the full set
live. Nothing here assumes the whole collection is installed.

## Skills

### [`ansible-ops`](./skills/ansible-ops)

Ansible playbook, inventory, and role conventions. Activates when
creating, editing, or reviewing playbooks, inventories, roles, or task
files — covers idempotence, handler patterns, variable precedence, and
common task hygiene.

### [`git-workflow`](./skills/git-workflow)

Git branching, commits, and MR/PR workflow. Activates when creating
branches, committing, or preparing merge/pull requests. Covers
deployment-model-aware branching (staging on default, prod on tag),
bracketed issue-referenced commit format (per-tracker: GitHub/GitLab
`#`, Linear, Jira), atomic/revertible commit rules, and
rebase-over-merge preferences. Includes the GPG signing strategy and the
`gpg-rewarm` helper under `references/` for harnesses that can drive an
interactive pinentry.

### [`git-workflow-hermes`](./skills/git-workflow-hermes)

Hermes variant of `git-workflow`. Same branching, commit and MR/PR
conventions, with two harness-specific changes: **commit signing is never
performed** (a signed git operation hangs on a pinentry prompt a Hermes
terminal cannot display), and every editor/picker-driven git command
(`git add -p`, bare `git rebase -i`, `git commit` without `-m`) is replaced
by its non-interactive equivalent. Supersedes `git-workflow` where they
conflict; use the generic skill on harnesses that can prompt.

### [`glab`](./skills/glab)

Expert guidance for the GitLab CLI (`glab`) — issues, merge requests,
CI/CD pipelines, repository operations. Activates when the user needs
to interact with GitLab resources from the command line. Ships with
detailed command references and a troubleshooting guide under
`references/`.

### [`hermes-claude-code-tmux`](./skills/hermes-claude-code-tmux)

Required procedure for a Hermes agent invoking the Claude Code CLI.
Activates before any `claude` call, coding-task delegation, or subagent
dispatch. Every invocation runs inside a named detached tmux session
rather than a blocking terminal call, with dispatch/poll/collect
patterns, explicit tool pre-granting, and `--resume` session handling.
Supersedes the bundled `autonomous-ai-agents/claude-code` skill where
they conflict.

### [`hermes-code-delegation`](./skills/hermes-code-delegation)

Routes all codebase work to the Claude Code CLI rather than the agent's
own file tools, and picks the model tier the task warrants. Activates on
codebase-shaped requests — reviewing a branch or MR, debugging a failing
test, explaining how something works, adding or refactoring code — and
deliberately triggers *before* any file inside a repository is opened,
since that is when the decision is made. Pairs with
`hermes-claude-code-tmux`, which owns the dispatch mechanics.

### [`k8s-ops`](./skills/k8s-ops)

Kubernetes troubleshooting, deployment, and day-to-day operations.
Activates when debugging pods, inspecting cluster health, or authoring
manifests — covers `kubectl` diagnostics, common failure modes, and
manifest conventions.

### [`refine-qa-notes`](./skills/refine-qa-notes)

Generates a structured QA tracking document from raw QA session notes.
Takes a quickly-written, potentially multilingual markdown or plain-text
notes file and produces an English markdown document with an issue summary
table (status, priority, size) and per-issue analysis sections, designed to
be updated by humans or AI agents as fixes land.

## Hooks

Beyond skills, this repo also ships a small set of [Claude Code
hooks](https://docs.claude.com/en/docs/claude-code/hooks) under
[`hooks/`](./hooks). Hooks are shell scripts the harness invokes around
tool calls — useful for enforcement that should not depend on the model
remembering to consult a skill.

### [`git-gpg-precheck`](./hooks/git-gpg-precheck.sh)

`PreToolUse` hook for `Bash`. Probes `gpg-agent`'s passphrase cache
before any git operation that may sign a commit/tag (`git commit`,
`git tag`, `git merge`, `git cherry-pick`, `git revert`, `git rebase`).
If the cache is cold, denies the call with a clear "ask the user to
pre-unlock" message instead of letting Claude Code hang on a pinentry
prompt it cannot display.

Install (a copy is correct here — hooks are wired into the harness's own
settings, not discovered from a directory):

```bash
mkdir -p "$HOME/.claude/hooks"
curl -fL https://raw.githubusercontent.com/Clovel/custom-ai-skills/main/hooks/git-gpg-precheck.sh \
  -o "$HOME/.claude/hooks/git-gpg-precheck.sh"
chmod +x "$HOME/.claude/hooks/git-gpg-precheck.sh"
```

Wire it in `~/.claude/settings.json` (merge with any existing `hooks`):

```json
{
  "hooks": {
    "PreToolUse": [
      {
        "matcher": "Bash",
        "hooks": [
          {
            "type": "command",
            "command": "$HOME/.claude/hooks/git-gpg-precheck.sh",
            "if": "Bash(git *)",
            "timeout": 5
          }
        ]
      }
    ]
  }
}
```

Pairs with the [`git-workflow`](./skills/git-workflow) skill, which
documents the surrounding GPG signing strategy (24h passphrase cache +
once-daily pre-unlock) for harnesses where signing applies.

## Updating

```bash
git -C ~/src/custom-ai-skills pull
```

Symlinks and Hermes `external_dirs` pick the change up immediately (new session
for Hermes); copied skill directories must be re-copied, which is why linking is
preferred.

## Usage

Skills activate automatically based on their `description` frontmatter
field. In Claude Code, typing `/` lists available skills and lets you
invoke one explicitly. In Hermes, `hermes skills list` shows installed and
external skills; external ones are read-only.

## Contributing

Issues and pull requests are welcome. New skills should follow the existing
`skills/<name>/SKILL.md` layout and include valid YAML frontmatter. See
[AGENTS.md](./AGENTS.md) for conventions.

Skills are distributed from this repository only — do not add registry
install commands to this README.

## License

[MIT](./LICENSE).