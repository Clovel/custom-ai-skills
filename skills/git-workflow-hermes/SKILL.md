---
name: git-workflow-hermes
description: Hermes variant of git-workflow — branching, commits, and MR/PRs with commit signing OFF. Use when creating branches, committing, rebasing, cherry-picking, or preparing MRs/PRs from a Hermes session, and whenever git mentions GPG, pinentry or a passphrase. Supersedes the generic git-workflow skill on commit signing and on interactive git commands.
---

# git-workflow-hermes

The generic `git-workflow` skill (in this repo, deliberately **not** installed
alongside this one) is written for harnesses that can drive an interactive
terminal (Claude Code with a pre-unlocked gpg-agent, a human shell).
A Hermes session cannot: its terminal is non-interactive, so any git command
that blocks on a prompt hangs the whole turn.

This skill is that same workflow with those two failure classes removed.
Everything not mentioned here is unchanged — read the generic skill for the
branching model and MR checklist.

## Precedence

Where this skill and `git-workflow` disagree, **this skill wins**:

| Topic | Generic `git-workflow` | Here |
| --- | --- | --- |
| Commit signing | Signed commits expected; warm the cache, pre-unlock, `git-gpg-precheck` hook | **Never sign. Signing is off globally and stays off.** |
| Splitting a commit | `git add -p` / `git add -i` | Explicit paths only — `-p`/`-i` are interactive |
| History cleanup | `git rebase -i` | Scripted `GIT_SEQUENCE_EDITOR`, or `--fixup` + autosquash |
| Commit message | implied editor use | Always `-m` / `-F` / `--no-edit` |

## Commit signing: never

Hermes does not sign commits, tags, or merges. `commit.gpgsign` is `false`
in the global config and Hermes must leave it that way.

**Never:**

- pass `-S` / `--gpg-sign` to `commit`, `tag`, `merge`, `cherry-pick`, `revert`, `rebase`
- pass `-c commit.gpgsign=true` or `-c tag.gpgsign=true`
- run `git config` to set `commit.gpgsign`, `tag.gpgsign`, `user.signingkey`
  or `gpg.format` — globally or in a repo
- try to warm or flush gpg-agent's cache (`gpg --clearsign`, `gpg-connect-agent
  clear_passphrase`, the `gpg-rewarm` helper from the generic skill). Those
  scripts unlock the key by triggering pinentry — which is exactly the prompt a
  Hermes terminal cannot display. They are for the human's own shell, not here.

**Why this is not a cop-out:** gpg-agent's pinentry needs a TTY it can draw on.
Hermes' terminal has none, so a signed git operation does not fail — it hangs
indefinitely, the turn times out, and the work in progress is lost. The 24h
passphrase cache documented in the generic skill only papers over this: it makes
signing *usually* work and then hangs unpredictably whenever the cache expired
or the wrong key was warmed.

Unsigned commits from Hermes are expected, not a defect. `git log --format='%G?'`
returning `N` on Hermes-authored commits is normal — do not report it as a problem
and do not set out to "fix" it.

### When a repo actually requires signed commits

If the target repo (or CI) enforces signed commits, **do not sign and do not
silently work around it**:

- Do not commit with `--no-gpg-sign` or a local `commit.gpgsign=false` override
  just to get past it — that hides a deliberate policy and produces a branch that
  will fail the check anyway.
- Stop, and report to the user which commit/branch needs signing, so they can
  make it from their own shell with the passphrase cache warm.

A local `commit.gpgsign = true` found in a repo is a human decision, not an
invitation to enable signing in this session.

## No interactive prompts

`core.editor` is `vim` here. Any git command that would open an editor or a
picker waits forever in a Hermes terminal. Always:

```bash
git commit -m "[#123] Fixed the delete button"   # or -F <file>
git commit --amend --no-edit                    # keep the existing message
git merge --no-edit <branch>
git cherry-pick -x <sha>                        # -x, no editor
git revert --no-edit <sha>
GIT_EDITOR=true git rebase --continue           # never bare `rebase --continue`
```

Non-interactive equivalent for the prompt-driven commands:

```bash
# Instead of `git add -p <file>`: stage the whole file, or split the change
# into separate files/commits first. There is no non-interactive patch picker.
git add path/to/file.ts

# Instead of `git rebase -i <base>`: script the sequence editor.
GIT_SEQUENCE_EDITOR='sed -i "1s/^pick/fixup/"' git rebase -i <base>
```

Avoid entirely: `git add -p`, `git add -i`, `git rebase -i` without a
`GIT_SEQUENCE_EDITOR`, `git commit` without `-m`/`-F`, `git tag -a` without `-m`,
and `git clean -i`.

## Commits

Format, rules, tense and atomicity: unchanged from the generic skill —
`[<issueRef>] <Description>`, atomic and revertible, dedicated refactor commits,
title-only, English, no Conventional Commits prefixes.

The one rule that changes in practice: split a mixed change with `git add
<path>` and several commits (or by rewriting the change), not with an
interactive hunk picker.

## Branching

Unchanged — pick the source branch from the repo's deployment model
(`main` / staged `dev`+`main`), name branches
`<type>/<short-kebab-description>` with the optional issue prefix, and target
`main` for hotfixes, the default/staging branch for everything else.

## Pulling & rebasing

Unchanged — keep history linear, `git pull --rebase` or `--ff-only`, rebase onto
the target branch before opening and before merging the MR, push at least daily,
prefer `git cherry-pick` over merging a sibling branch.

## MR/PR preparation

Unchanged — typecheck + lint + tests before pushing, bracketed issue ref in the
MR title, description covering what/why/how-to-test, hotfixes target production,
rebase onto the target branch just before requesting review.

## Related

- `git-workflow` — the harness-agnostic version, including the GPG signing
  strategy and the `gpg-rewarm` helper for harnesses that can prompt. Link the
  `skills/git-workflow` directory from this repo into that harness's skills dir
  where it is needed.
- `hooks/git-gpg-precheck.sh` — Claude Code `PreToolUse` hook that denies signed
  git operations when the passphrase cache is cold. Not applicable to Hermes,
  where signing is off outright.
