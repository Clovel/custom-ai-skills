---
name: hermes-code-delegation
description: Routes all codebase work to the Claude Code CLI instead of the agent's own file tools, and picks the model the task warrants. Use whenever a request involves reading, searching, analysing, reviewing, explaining, debugging, testing, refactoring, or changing code in a repository — "review this MR", "review this branch", "why is this test failing", "how does auth work here", "add an endpoint", "fix this bug", "write tests for", "explain this function", "clean up this module", "look at this project", "what does this code do". Applies BEFORE opening any file inside a repository, not after.
---

# hermes-code-delegation

**Codebase work goes to Claude Code. Not to this agent's own file tools.**

Read this before the first file you open inside a repository — the decision this skill
governs is made at that moment, and it cannot be unmade afterwards.

## Why

Two reasons, and the first is the one that bites quietly.

**Reading a codebase with your own tools bills every byte to your own model provider.**
Forty files read is forty files of context, metered, and most of it is never used
again. Delegating sends the reading to a harness billed separately — typically a flat
subscription rather than per-token — and what comes back is a paragraph. The work
moves; the token cost mostly disappears rather than relocating.

This is the difference between a task costing a few hundred tokens and a task costing a
hundred thousand. An agent that analyses codebases directly will exhaust a daily quota
on a single afternoon's work, and the failure looks like an unrelated outage later.

**Second: a code-specialised harness is simply better at it.** It has the file
navigation, the diff handling, the test loop and the model tiering already built. Doing
it by hand with generic read and write tools produces worse results more slowly.

## What counts

| Do it yourself | Delegate |
| --- | --- |
| `git log`, `git status`, branch and tag names | Reading a diff in order to **judge** it |
| Your own configuration, memory and notes | Anything inside a repository working tree |
| One file, to answer one direct question about it | Anything spanning more than a file or two |
| A snippet someone pasted into the conversation | Any edit to a tracked file, ever |
| Reporting what a delegated run concluded | Searching a repository to find something |

The boundary that matters: **if the answer requires looking at code you have not
already been given, delegate.** Opening "just one more file" to check something is how
a delegated task becomes an undelegated one.

## Choosing the model

Pass `--model`. The task's difficulty decides, not its length.

Three tiers are chosen freely. A fourth is not — see below.

| Tier | Use for | `--model` |
| --- | --- | --- |
| Cheap | Mechanical and bounded: "where is X defined", renames, formatting, generated boilerplate, a single obvious fix | `haiku` |
| Default | Most real work: implementing a feature, fixing a bug, writing tests, reviewing a diff, explaining a module | `sonnet` |
| Hard | Everything demanding: subtle or security-relevant bugs, tricky algorithms, expensive design decisions, large refactors, whole-codebase review, work spanning many modules, long autonomous runs | `opus` |

Aliases select the current model in each tier; full identifiers also work when a
specific one is required.

**Default to `sonnet` when unsure.** Under-modelling a hard task does not fail loudly —
it returns confident, wrong code that costs far more to find and undo than the tokens it
saved. Reserve `haiku` for tasks whose correctness you could verify at a glance.

**Do not read a tool-access failure as a model-tier limit.** A run that reports an MCP
tool "not available" may simply have declined to search for it — the same model, same
prompt shape, succeeds on the next run. Change one thing at a time: forcing the attempt
("you must call X; quote the failure verbatim") is what fixes these, and a tier bump made
in the same edit masks whether it was ever the model. Verify capability before writing a
rule about it — an over-claimed model limit is worse than none, because it quietly routes
work to a more expensive tier forever.

`opus` covers the whole top end: depth and breadth alike. There is no task in this table
that requires reaching past it.

Escalate rather than retry: if a run comes back confused, contradictory, or having
misread the structure of the code, re-run one tier up with the same prompt rather than
repeating it at the same tier.

### `fable` is opt-in, never chosen on your own

**Do not select `fable` autonomously.** It is used only when the user has explicitly
asked for it, or when you have suggested it and they agreed. This is a standing rule,
not a default that a sufficiently large task overrides.

Suggesting it is allowed, and is the right move when a task is unusually large or
long-running — a change spanning much of a tree, a review of an entire codebase, a run
expected to work unattended for a long stretch. Say what it would buy and let the user
decide; then proceed with `opus` if they do not answer or do not want it.

Never treat "this task is big enough" as consent. `opus` is always a legitimate choice
for the same work, so a task being hard is never on its own a reason to reach for
`fable`.

## Reviewing code

Review is delegation like anything else — the criteria go in the prompt, not into your
own reading of the diff. A review prompt should ask for:

- Type safety and error handling
- Edge cases, and what happens on the unhappy path
- Security-relevant changes
- Whether tests actually cover what changed
- Breaking changes, called out explicitly

Reviewing a diff is `sonnet` work. Reviewing a whole codebase, or a change whose
consequences are not confined to the lines it touches, is `opus` work — a small diff
that edits a shared primitive has consequences outside the lines it touches, and is
`opus`.

A review prompt for a merge request should also demand:

- **A verdict per item the ticket asked for** — fixed / partially fixed / not fixed /
  cannot verify — one line each with the `file:line` that proves it, so "7 of 7" cannot
  cover a point that regressed.
- **An explicit answer to the author's own open questions.** When the description asks
  "should this live in the shared primitive?", the deliverable is "here is what I would
  choose, and what regresses the other way" — not a restatement of the question.
- **The claims the author filed as out of scope**, checked against the tree rather than
  echoed back.
- **A closing list of what the reviewer could not verify**, so the gaps are visible
  instead of distributed through the findings.

Reviewing **work you commissioned** is the same discipline turned on your own deliverable. Hand the
author's written report over explicitly as claims to be falsified ("treat as claims, not facts"),
require each one labelled *verified / unverified / disproved* with the evidence, and require a
closing note naming what blocked any check that could not be run. A reviewer that returns "I
confirmed the mechanism but did not reproduce these three numbers" is doing its job; one that
restates the report back is not. Two things to expect and plan for: a review may be unable to
test a counterfactual without mutating the tree — give it a scratch clone in the brief rather than
a prohibition alone — and a permission block on some commands is normal, so require the reviewer to
name what it could not run instead of going quiet about it.

Then report the findings. Do not re-read the diff yourself to check the review; if the
review is not trustworthy, re-run it a tier up. That is not the same as *verifying* it,
which is yours and must happen before delivery: check its citations and its counted
claims mechanically, and supply the facts it could not reach (the tracker ticket, the
CI instance, anything outside its sandbox). The ticket wording is often richer than the
author's restatement of it — a symptom present in the issue and absent from the MR
description is a finding the delegated run cannot produce and you can.

Support file: `references/mr-review-dispatch.md` — the end-to-end recipe (locating the
MR, the worktree at the MR head, the artifact dump and settings file, the prompt
skeleton, the pre-delivery checks, and posting the finished review as MR comments).

## How to dispatch

Mechanics — sessions, polling, collecting output, resuming — are not repeated here.
Follow the `hermes-claude-code-tmux` skill, which is the authority on how a run is
started and retrieved. In short: a named detached session, never a blocking foreground
call.

Two substrates exist there, and the **interactive one is the default**: a live TUI session
driven by `scripts/cc-drive.py`. Print mode (`claude -p`) is the exception, for a run that
needs the machine-readable result object (`--output-format json`, `--json-schema`) or piped
stdin, and that cannot prompt. Default to the interactive session for any delegated codebase
work: it answers permission dialogs and clarifying questions that print mode cannot, has no
600 s background ceiling, and carries several turns in one process.

Write the prompt as a brief, not an instruction to a file editor. State the goal, the
constraints, and what a good answer looks like. A delegated run has its own context and
its own tools; it does not need the files listed for it, and listing them usually
narrows the work incorrectly.

## When not to delegate

The rule has a floor. Do not spawn a run to read a single short file that has already
been named, to answer a question about code that is already quoted in the conversation,
or to check something a shell command answers outright (whether a file exists, what a
branch is called, what a command's help output says). A delegated run has a fixed
overhead in time and coordination; below a certain size, doing it directly is both
cheaper and faster.

The test is whether the work involves *exploring* code. Exploration delegates. Lookups
of a known thing do not.
