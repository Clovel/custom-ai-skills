# Delegating a tracker write to Claude Code

When the delegated task is "create the issue" or "post the comment", the deliverable is a record in
an external system. The read-back is what makes it evidence; everything else is prose.

## Grant, then constrain

The write tool needs an allow entry (see `SKILL.md` on the server-wide glob) **and** a prose limit:
name the single object the run may create, and say outright that every other issue, ticket and
system is read-only for this run. A tracker has no dry-run — an over-broad run posts twice, or edits
the ticket it was only meant to read.

## The workspace's conventions outrank generic tracker advice

Read one existing issue in the same team/project before writing, and mirror it rather than inventing
structure. Facts that generalise, adjust at write time:

- **Language follows the tracker, not the conversation.** A workspace whose issues are written in
  French gets a French issue even when the user asks for it in English. Code identifiers, paths and
  `file:line` citations stay in English inside French prose.
- **Copy the house section shape** from a neighbouring issue: typically `# Contexte` (what is broken,
  with citations), `# Comportement attendu`, `# Correctif proposé`, `# Vérification / reproduction`,
  `# Non vérifié`, `# Critères d'acceptation` as `- [ ]` checkboxes.
- **Never invent a label.** Read the team's existing set and pick from it. Do **not** inherit the
  parent ticket's labels — they describe the parent's nature (a client-requested evolution, a
  frontend change), not the relation to it, and a backend defect filed with the parent's labels is
  misfiled.
- **Assign by explicit user id**, not by a name lookup, and confirm the assignee after creation.
- **Leave state and priority at the team default** unless asked. If the finding might be urgent to
  someone else, say so in your report instead of escalating it in the record.
- **Link the origin**: relate or mention the source ticket and include the change request's URL.

## Make the run check the claims you hand it

A brief can assert something you never established — "the sibling form has the same gap". Require the
run to verify each such claim against the tree *before* it reaches the issue text, and to correct
your brief where it is wrong. Expect it to come back with a narrower, truer statement (one of two
products affected, and for a different reason than you said).

## Read the record back with your own connector

- A creation call that returns no identifier is not evidence the issue exists. Ask for identifier,
  URL, team, project, assignee, labels and description length.
- Then verify it yourself with your own tracker tools, field by field — state, team, project,
  assignee, labels, description length, relations. A child can report an assignee it did not set.
- Ask for its tool calls as name plus arguments: that is how you see whether it wrote once or five
  times, and whether it read before writing.

## Say what the record cannot hold

Volumetry ("how many contracts are affected") generally needs the database; a provider-side count
needs a query. Put those under `# Non vérifié` inside the issue rather than publishing an estimate as
fact, and keep the reproduction steps precise enough that whoever picks it up can confirm the
mechanism in one sitting.
