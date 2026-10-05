# Verifying a delegated run's result before you report it

The dispatch mechanics are in `SKILL.md`; this is the check that turns a run's self-report into
something you are entitled to state. Applies whether the run committed (see also
`delegated-implementation-runs`, which owns the landing workflow on a machine where it is
installed).

## A cached re-run is not a re-run

Monorepo task runners replay the child's own result: the second `yarn test` prints the child's
timestamped test output and `Cached: 25 cached, 25 total >>> FULL TURBO`, because the inputs hashed
identically. Pass the runner's cache-bypass flag (`yarn test --force`) and read the `Cached:` line —
only `0 cached` makes it your verification. Otherwise report it as the run's result, not as an
independent one. A test count is cheap to quote honestly and expensive to have quoted back at you.

## Anything the build regenerates is not part of the change

A test or typecheck that pulls a package through its build can re-fetch a generated client from a
live upstream spec, leaving hundreds of unrelated lines in the tree. Check the diff for files that
the change cannot have produced (`git show --stat`, then look at any large `__generated__`-style
path), require `git checkout -- <path>` before staging, and re-check after every command that can
rebuild — a resumed or follow-up run regenerates them again, so the clause has to survive into the
next prompt.

## Check the citation's path, not only its line number

A report can cite the right line number in the wrong directory
(`lib/topology.ts:181` for `lib/data/topology.ts:181`) and read perfectly plausible. Grep the quoted
content and confirm the file it lands in is the one named. Verified claims are the ones you
reproduced from the same file the report pointed at.

The number can also come from a different *artifact* of the same source. A claim about code inside
a container image is routinely cited against the project's tree while the image runs a compiled
copy whose numbering differs — both numbers exist, so the citation checks out against the file you
are shown and against nothing that executes. Name the artifact a line number was read from, and
re-read it in the artifact that actually runs.

## Reproduce the decisive number yourself, especially a refutation

When a run contradicts something you believed — "the plugin is registered, so the hazard does not
nexist" — run the probe yourself under the same conditions and compare numbers. Reproduce with the
real harness shape (`new Function('with (this) { return (<expr>); }').call(context)`), not a
friendlier equivalent. Two traps decide whether the number means anything:

- **Pin the SHAs the A/B probe reads from.** A probe that takes the old value from `HEAD` or from the
  working tree starts comparing the fixed code with itself the moment the fix is committed, and
  reports zero regressions with a straight face. Read each version from an explicit commit
  (`git show <old-sha>:<path>` vs `git show <new-sha>:<path>`) and rebuild the probe rather than
  re-running the child's script: a script authored mid-run encodes the pre-commit state implicitly.
- **Probe the environment that actually runs, not an illustrative one.** Do not reach for the zone,
  version or platform that makes the bug most photogenic — that answers a question nobody asked and
  invites the reply "why that one?". Read the deployment's real configuration from primary sources
  (image Dockerfile, k8s manifests, env of the actual service), and when the base image leaves a
  setting unset, run the image to read the effective value
  (`docker run --rm <base-image> date` → `/etc/localtime -> Etc/UTC`). Then split the verdict:
  **live** (wrong under the real configuration) vs **latent** (only wrong if someone pins it). A
  defect that is a no-op in production is a latent one, and reporting it as live costs the user a
  the user a decision they did not need to make.
  - **Behaviour, not only settings.** A claim that a script fires when a given install command runs is
    settled by executing both arms in the real image and printing a marker from inside that script —
    not by chaining citations (image env → tool helper → library guard), however authoritative each
    link looks. A chain that long can be wrong at exactly one link and still read as proof, and the
    user will believe it until someone runs it. When you have composed a mechanism rather than
    executed it, label it that way in the same sentence; a composed claim presented flat is how you
    lose the argument the moment an experiment contradicts it. Anchor the claim to the revision it
    describes: once you have authored a change to the thing in question, a bare present tense
    silently mixes the pre-change and post-change states — name the state and the revision in the
    same sentence, and when the two differ, say which one you measured.
- **Sweep the domain, do not hand-pick cases.** Every day of the period at the boundary hours, in
  each candidate zone, and count the failures (`samples=1460 OLD wrong=42 NEW wrong=0`). A sweep is
  also what exposes a pair of faults cancelling: the same input can look correct in one zone while
  being wrong twice, which a three-row table never shows.

## Check the gate before acting on the recommendation

A run that recommends an action commonly attaches a condition to it — do X provided Y holds. That
condition is the run's own caveat and the cheapest item in the report to check, and finding it
false overturns the headline recommendation. A run whose gate was never tested has effectively
handed the decision back to you while appearing to have made it. Establish the gate against primary
evidence first, then report the conditional outcome rather than the recommendation.

## Two facts about a fix that uses a library

- **Declared, not merely installed.** A package imported somewhere in a tree can be hoisted from a
transitive dependency and declared in no `package.json` at all — `grep '"<lib>"' **/package.json`
  returning nothing is the tell. Imports elsewhere in the repo do not make it a dependency of the
  package you are changing.
- **Scope of a string-evaluated value.** When the value being fixed is a *string* evaluated at
  runtime (a fixture default value, a template expression), its scope is the evaluator's alone, so
  an imported helper is unreachable however available the package is elsewhere. Find the evaluator
  (`grep -rn 'new Function\|evalExpression'`) and write the fix in what that scope has. When the user
  asks "do we already have <lib>?", answer with the scope, not the availability.

## Triage a deploy-window finding against the release practice

A mechanism that only bites while old and new readers overlap for a few minutes is a note, not a
blocker, where releases go out outside the users' working hours. State the window you assumed and
let the user correct it rather than escalating on the code path alone — they often hold operational
context that decides the severity, and re-litigating it after they have answered wastes a turn.

## Sequence an audit after the fixes it judges

A read-only audit that ends by proving `git status --porcelain` empty proves nothing if a writing
run changed the tree underneath it. Dispatch the audit once the fixes have landed, or give the
writer its own worktree; if the audit's subject is not the tree at all (a tracker issue), overlap is
fine.

When you do tolerate the overlap, require the read-only run to **attribute** any dirt it finds
rather than clean it: prove the change is not its own (its own tool-call log, the file mtime against
its own start time) and report it verbatim. Reverting a sibling run's in-flight work is worse than a
dirty tree, and a clean-tree claim obtained with `git checkout --` is a false statement about the
run's own discipline.
