# Reviewing a merge request by delegation

End-to-end recipe for "review MR !N" / "review this branch": how to locate the MR,
what to hand the reviewer, the prompt skeleton, and the checks a review must pass
before it is delivered. Session mechanics (`tmux` dispatch, polling, collecting, the
read-only settings file, `SOURCES.md` for host audits) live in
`hermes-claude-code-tmux`.

## 1. Locate the MR from the source

```bash
glab auth status                       # confirm the instance before reading anything
glab mr list --output=json | jq -r '.[] | "\(.iid)\t\(.author.username)\t\(.title)\t\(.source_branch) -> \(.target_branch)"'
```

Run it inside the clone (`~/repository/<client|category>/<repo>`); `-R owner/repo`
works from anywhere. Keep `glab mr view <iid> --output=json` as an artifact: the
description, source/target, `has_conflicts` and `detailed_merge_status` are what the
review has to be judged against. "Alexandre's MR" is not an identifier — resolve it to
an iid, then say which one you reviewed.

## 2. Give the reviewer a tree at the MR head

```bash
git fetch origin <target> <source>
git worktree add --detach /tmp/<mr>/wt origin/<source>      # head, base = origin/<target>
git log --oneline origin/<target>..origin/<source>
git diff --stat origin/<target>...origin/<source>           # three dots = against merge base
```

A detached worktree at the MR head, never a checkout in the user's clone — the review
must not disturb whatever they have open, and the head is what is being merged. Remove
it when the task ends (`git worktree remove --force` then `git worktree prune`); leave a
worktree you did not create in place and mention it.

Because the reviewer reads the real tree, it can trace callers of a changed primitive,
which a diff-only review cannot. That is the point of the worktree.

## 3. Artifact dump

Dump under one workdir (`raw/`) and write `SOURCES.md` naming each file and the exact
command that produced it:

- `mr-<iid>.json` — `glab mr view <iid> --output=json`
- `commits.txt` — `git log --oneline <target>..<source>`
- `mr-<iid>.diff` — `git diff <target>...<source>`
- `diffstat.txt` — the file list, so the reviewer can see scope without opening it

Known gaps worth stating explicitly, because each one changes how a claim must be
labelled:

- **Generated or untracked build output is absent from a fresh worktree** (codegen'd API
  clients, ORM clients, compiled assets). Name the paths in `SOURCES.md` so modules that
  import them are read for intent, instead of the reviewer reporting a missing import as
  a defect or guessing at its shape.
- **No `node_modules`**, so nothing can be executed: every test, lint and type-check
  result quoted in the MR description is *the author's claim*, and the prompt must say so.
- **The GitLab instance and its CI are outside the reviewer's reach** (a self-hosted
  GitLab is not in Claude Code's MCP roster). Pipeline status is not yours to assert
  either unless you fetched it yourself.

## 4. Settings and prompt

`--settings cc-settings.json` with `permissions.allow` scoped to the workdir
(`Read(//abs/workdir/**)`, plus `Grep`/`Glob` on the same root) and `permissions.deny`
listing `Bash`, `Edit`, `Write`, `NotebookEdit`, `WebFetch` and the secret paths. Then
`--allowedTools "Read,Grep,Glob"` — read-only means *no Bash*, and the diff is already on
disk, so nothing legitimate needs a shell.

Write the prompt to a file and pass it as `-p "$(cat prompt.md)"`; inline quoting of a
multi-paragraph prompt with backticks is a needless failure mode.

**A read-only run cannot write its own deliverable.** With `Write` denied, a prompt that
ends "write the review to `review.md`" asks for something refused at the last step, after
the whole review has been paid for. Require the document as the run's *final message*
(or allow `Write` for that one scratch path) and extract it yourself: dispatch with
`--output-format json` and collect `jq -r '.result' out.json > review.md`. Saying so in
the prompt is cheaper than discovering the contradiction on the way out.

A review prompt that produces the shape the user wants:

1. **Scope and standing** — which repo/MR/branch/head, the artifact paths, and "read
   only, change nothing anywhere: no edits, no commits, no MR comments, no writes to the
   tracker".
2. **Findings by severity** (blocker / major / minor / nit), each with `file:line`, the
   condition under which it breaks, and a concrete suggestion. Say that a few real
   defects beat an inventory of style notes.
3. **A verdict per item the ticket asked for**, with the evidence line.
4. **The author's own open questions**, answered with a recommendation and the risk on
   the other side.
5. **The author's "out of scope" claims**, checked rather than repeated.
6. **Mechanism review of the risky changes** — for each, what it catches, what it misses,
   and what could regress the other way.
7. **Tests** — do the added tests pin the claimed behaviour, would they fail if the fix
   were reverted, and what changed without a test. jsdom does no layout: say where a
   test is load-bearing and where it is tautological.
8. **Breaking changes and convention violations**, called out — including the repo's own
   rules (`AGENTS.md`, `CLAUDE.md`, `.cursor/rules/*`) when a review touches them.
9. **Honesty labels on every non-obvious claim** — *verified via MCP*, *verified in tree*
   with `file:line`, or *taken on trust* — plus a closing **what I could not verify**.
10. **The project's code language** (English code, whatever language the UI copy and the
    MR description are in), and the language the finding list should be written in.

## 5. Before delivering

**Check the citations mechanically.** Parse the delivered text for `file:line`
references and confirm each file resolves and each cited line number is within that
file's length. Resolve a cited path **by suffix of its full path, never by basename**: a
monorepo has several `package.json` (root, `apps/*`, `packages/*`) and many repeated
component filenames, so basename matching silently checks the wrong file and reports a
false "line out of range" on a citation that was correct. Treat an isolated mismatch as
a resolver artifact until the one file it claims is checked directly. To *find* a file
cited by bare filename, search the tree (`find <root> -name '<basename>'`) rather than
prepending the directory the neighbouring citations suggest: in a monorepo a component's
folder follows neither from its name nor from its consumer, and shared primitives land
wherever their first consumer happened to be.

**Recount its quantitative claims.** The counts in a review ("this fixes 7 dialogs"),
the hit counts ("this utility is referenced in 3 files"), the caller counts — re-derive
them with `grep -rn` / `-l` before repeating them to the user, who will challenge a
single-instance extrapolation. A UI review's colour and accessibility findings are
numbers too, and a contrast ratio is recomputable in seconds from the hex tokens it
cites with a short relative-luminance script — recompute them instead of repeating them,
since that is the claim the author will act on.

**Fill the gaps it declared.** Read the tracker ticket yourself with your own connector
tools; the review cannot, and the ticket wording is often richer than the author's
restatement — an item present in the ticket and absent from the MR description is a
finding only you can surface. Then check the concrete sub-symptoms the MR's own summary
drops, against the tree.

**Report, do not replay.** Conclusion first; the two or three findings that change the
merge decision; the author's questions answered; what was left unverified (and why —
a construct that could compile to nothing, an unrunnable test suite, a CI instance out
of reach); cost and duration one line at most. Keep the full review as a file and attach
it rather than inlining it into chat, and say where it was saved.

## 6. Posting the review to the MR

State-changing, and only after an explicit go-ahead (see Pitfalls). Two note kinds, and
the distinction matters because a resolvable thread on a merge gate blocks the merge:

```bash
# Summary: the verdict and the findings. Non-resolvable — prose has nothing to resolve.
glab mr note create <iid> --resolvable=false -m "$(cat note.md)"

# Inline: one actionable blocker, pinned to a line. Resolvable, so it can be ticked off.
glab mr note create <iid> --file <path-from-repo-root> --line <new-side-line> -m "..."
```

- **The inline line must fall inside a diff hunk.** Read the hunk headers before
  commenting — `grep -n '^@@' raw/mr-<iid>.diff` gives `@@ -old,+new @@` ranges, and only a
  new-side line one of them covers is commentable. `--file` takes the path as the repo
  reports it, with no `wt/` prefix.
- `--file` cannot be combined with `--reply` or `--unique`, and `--resolvable=false`
  cannot be combined with `--file`. Put the long body in a file and pass it as
  `-m "$(cat note.md)"` rather than fighting shell quoting.
- **Language and shape follow the instance, not the diff.** A self-hosted company GitLab
  gets the review in the team's working language — French on this account — with code,
  identifiers and the suggested fix quoted verbatim in English.
- **Blockers first, each with the fix in copy-pasteable form**
  (`<DropdownMenu modal={false} open={open} onOpenChange={handleOpenChange}>`, not "make it
  non-modal"), then the non-blocking findings by severity, then the author's questions
  answered with the risk on the other side, then what was verified and what was not,
  closing with a one-line disclosure that the review was produced with Claude Code.
- **Read the notes back** and confirm author, resolvable flag and position before
  reporting success:

```bash
glab mr note list <iid> -F json \
  | jq -r '.[] | .notes[] | "\(.id) resolvable=\(.resolvable) \(.position.new_path // "-"):\(.position.new_line // "-")"'
```

- When the user asks for a change to something already posted, edit the note in place
  (`glab mr note update <note-id> ...`) instead of posting a second one. The same applies
  when their instruction for a note arrives truncated: write the version the findings
  support, say plainly which part of the instruction was cut off, and offer the rewrite.

## Pitfalls

- **Don't let a shared-primitive change be reviewed as a local one.** A diff that edits
  `ui/*` primitives has a blast radius across every consumer; the prompt should require
  the reviewer to trace callers, and the model tier should be `opus`.
- **Cleanup before you report.** Kill only the tmux session you created (never
  `kill-server`), remove only the worktree you created, and leave the artifact directory
  with the review file in it.
- **Posting the review anywhere is a separate, state-changing step.** MR comments,
  tracker writes and `docs/` commits wait for an explicit go-ahead; offer the language
  and the trim, and stop there. The go-ahead covers the one MR it names — §6 is the
  mechanics once it comes, and it does not extend to approving or merging.
