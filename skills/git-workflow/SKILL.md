---
name: git-workflow
description: Git branching, commits, GPG signing, and merge request workflow. Use when creating branches, committing (including signed commits), troubleshooting commit hangs / GPG / pinentry issues, or preparing MRs/PRs.
---
# Git Workflow

## Branching

### Picking the source branch

The default branch depends on the repo's deployment model — identify it before branching:

- **Small project**: `main` is both default and production (deploy on push or tag).
- **Standard**: `main` deploys to staging on push, production on tag. Branch from `main`.
- **Staged**: `dev` deploys to staging on push, `main` is preprod, tags are prod. Branch from `dev`.

If unsure, check CI config or ask before branching.

### Branch naming

`<type>/<short-kebab-description>`, optionally prefixed with the issue ID.

- Types: `feature/`, `fix/`, `hotfix/`, `refactor/`, `chore/`, `release/vX.Y.Z[-target]`
- Examples: `feature/vista-123-user-authentication`, `fix/login-redirect`, `hotfix/memory-leak`
- `hotfix/*` targets the **production** branch (usually `main`), not `dev`. Everything else targets the default/staging branch.
- Optional: `fix/various` as a batch branch for rapid low-risk bug sweeps. Only use when the maintainer is comfortable with it.

For collaboration on the same feature, use sub-branches: `feature/my-feature-alice`, `feature/my-feature-bob`, reconciled into `feature/my-feature` via rebase or merge.

## Commits

### Format

Bracketed prefix matching the issue tracker's native format, then a description in English:

```
[<issueRef>] <Description of the change>
```

- GitHub/GitLab: `[#123]`
- Linear: `[VISTA-123]`
- Jira: `[PROJ-456]`
- Match whatever the repo uses — do not invent a format.

If the commit addresses PR/MR review feedback or a CI failure, prepend the MR ref:

```
[!51, #123] Fixed code after peer review
```

Unreferenced commits are fine for linters, dependency bumps, cleanups:

```
Updated Meteor packages & dependencies
```

Avoid `feat:` / `fix:` / `(fix)` Conventional Commits prefixes — not the convention here.

### Rules

- **Atomic and revertible.** One logical change per commit. A `git revert` on any commit should leave a coherent tree.
- **Dedicated refactor commits.** Never mix refactors with behavioral changes — the diff becomes unreadable.
- **Tense.** Past (what the dev did: `Fixed the delete button`) or present general truth (what the commit brings: `Fixes the delete button`). Pick one and stick with it in the branch.
- **Title-only.** If you feel the need for a multi-paragraph description, the commit probably needs to be split. Use `git add -p` / `git add -i`.
- **Clean the history before merging.** Use `git commit --amend` or `git rebase -i` to squash WIPs, fix typos, reorder.
- WIP-style commits (`[WIP] ...`) are fine during work but should be squashed or renamed before the MR is ready.

### GPG signing

When `commit.gpgsign = true`, signed git operations (commit, tag, merge, cherry-pick, revert, rebase) must reach gpg-agent's pinentry to unlock the signing key. **Pinentry cannot prompt from inside Claude Code's TTY** — curses, GUI, anything interactive — so the operation hangs indefinitely.

Two practical workarounds:

1. **Long passphrase cache + once-daily pre-unlock** (recommended). In `~/.gnupg/gpg-agent.conf`:

   ```
   default-cache-ttl 86400
   max-cache-ttl 86400
   ```

   Then once a day, in a normal terminal: `echo test | gpg --clearsign > /dev/null`. The cache stays warm for 24h and signed commits inside Claude Code "just work."

2. **PreToolUse hook** — see [`hooks/git-gpg-precheck.sh`](../../hooks/git-gpg-precheck.sh) in this repo. Probes the cache before any signed git operation and returns `permissionDecision: "deny"` with a clear "cold cache" message when the cache is empty, so the agent stops and asks the user to pre-unlock instead of hanging.

Last resort: pass `--no-gpg-sign` for an unsigned commit. Don't pre-emptively bypass signing — only use this when the user has explicitly authorized it for the specific operation, otherwise commits stop being verifiable.

## Pulling & rebasing

Keep history linear to avoid spurious merge commits and conflicts.

- Prefer `git pull --rebase` or `git pull --ff-only` over plain `git pull`. Configure once: `git config --global pull.ff only`.
- Rebase your feature branch on the target branch **before opening the MR** and again before merging if it has drifted.
- Push at least once a day — remote is your backup and lets others review in progress.
- To pull in a fix from a sibling branch, prefer `git cherry-pick <sha>` over merging the whole branch.

## MR/PR preparation

- Run typecheck + lint + tests before pushing. Fix warnings caused by your changes.
- MR title: include the issue ref in the same bracketed format as commits. Example: `[VISTA-1234] Implemented user authentication`.
- MR description: what changed, why, how to test.
- Target branch: default/staging branch for features and fixes, production branch for hotfixes.
- Rebase onto the target branch just before requesting review.
