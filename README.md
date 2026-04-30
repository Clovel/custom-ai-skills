# custom-ai-skills

A collection of custom SKILL.md skills for Claude Code and any agent that
supports the [Agent Skills](https://github.com/anthropics/skills) spec.

Each skill lives under `skills/<name>/SKILL.md` and is installable
individually or as a set via the [`skills` CLI](https://skills.sh).

## Skills

### [`ansible-ops`](./skills/ansible-ops)

Ansible playbook, inventory, and role conventions. Activates when
creating, editing, or reviewing playbooks, inventories, roles, or task
files — covers idempotence, handler patterns, variable precedence, and
common task hygiene.

```bash
npx skills add Clovel/custom-ai-skills --skill ansible-ops
```

### [`git-workflow`](./skills/git-workflow)

Git branching, commits, and MR/PR workflow. Activates when creating
branches, committing, or preparing merge/pull requests. Covers
deployment-model-aware branching (staging on default, prod on tag),
bracketed issue-referenced commit format (per-tracker: GitHub/GitLab
`#`, Linear, Jira), atomic/revertible commit rules, and
rebase-over-merge preferences.

```bash
npx skills add Clovel/custom-ai-skills --skill git-workflow
```

### [`glab`](./skills/glab)

Expert guidance for the GitLab CLI (`glab`) — issues, merge requests,
CI/CD pipelines, repository operations. Activates when the user needs
to interact with GitLab resources from the command line. Ships with
detailed command references and a troubleshooting guide under
`references/`.

```bash
npx skills add Clovel/custom-ai-skills --skill glab
```

### [`k8s-ops`](./skills/k8s-ops)

Kubernetes troubleshooting, deployment, and day-to-day operations.
Activates when debugging pods, inspecting cluster health, or authoring
manifests — covers `kubectl` diagnostics, common failure modes, and
manifest conventions.

```bash
npx skills add Clovel/custom-ai-skills --skill k8s-ops
```

### [`refine-qa-notes`](./skills/refine-qa-notes)

Generates a structured QA tracking document from raw QA session notes.
Takes a quickly-written, potentially multilingual markdown or plain-text
notes file and produces an English markdown document with an issue summary
table (status, priority, size) and per-issue analysis sections, designed to
be updated by humans or AI agents as fixes land.

```bash
npx skills add Clovel/custom-ai-skills --skill refine-qa-notes
```

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

Install:

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
once-daily pre-unlock).

## Install everything

```bash
npx skills add Clovel/custom-ai-skills
```

## Usage

Skills activate automatically based on their `description` frontmatter
field. In Claude Code, typing `/` lists available skills and lets you
invoke one explicitly.

## Updating

```bash
npx skills list      # show installed skills
npx skills update    # update all installed skills
```

## Contributing

Issues and pull requests are welcome. New skills should follow the existing
`skills/<name>/SKILL.md` layout and include valid YAML frontmatter. See
[AGENTS.md](./AGENTS.md) for conventions.

## License

[MIT](./LICENSE).
