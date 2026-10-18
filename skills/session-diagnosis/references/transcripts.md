# Transcripts: discovery and context safety

Every reader of a session file, the manager or an analyst, follows this file for every file, every
time.

## Discovering the sessions

Resolve the session the user named with the tools and information in this environment. What you
know can suggest where to look; the actual files decide.

- **Where to look.** Claude Code keeps transcripts under `~/.claude/projects/<project>/`, one
  `<session-id>.jsonl` per session, with the session's workers under `<session-id>/subagents/` (an
  `agent-<id>.jsonl` transcript and an `agent-<id>.meta.json` per worker) and large tool outputs
  under `<session-id>/tool-results/`. `<project>` is the working directory's absolute path with
  every character that is not a letter or digit replaced by `-`; a worktree session has its own.
  Use the harness's own session tools, its help and documentation, or bounded inspection of the
  directory. Look in archives or indexes when the environment points to them. A usable path the user
  supplied needs no further search.
- **Measure before reading** (see "Context safety").
- **Confirm the identity** with the session id, the working directory, the timestamps, and matching
  content. Recency alone is not confirmation. Tell the requested session apart from its workers and
  from unrelated candidates. When the evidence cannot tell them apart, ask the user for the missing
  fact.
- **Use full absolute paths** for every source, with the home directory and any variables expanded,
  and use the same path in the case file and in what you tell the user.

## The record meanings to establish

Establish what each kind of record means from records you observed, or from documentation; never
infer a format from another harness, and never turn a missing field into a zero.

- **Human messages**, told apart from injected messages: hook output (the framework's session-start
  context, the guard's denials), system reminders, skill bodies loaded into the conversation, and
  tool results. In a worker's transcript the "user" is the manager's dispatch.
- **Assistant messages**, and the tool calls inside them.
- **Tool calls and their results**, and how they are matched (by an id the call and its result
  share). A worker's `.meta.json` names the id of the call that dispatched it.
- **Usage counters:** which fields, whether incremental or cumulative, and their units, before any
  total is computed.
- **Timing:** which fields, their units, and what bounds an event.
- **Other records** a finding may need: the models, the harness version, compactions, resumes,
  aborted turns, permission decisions.

**Record it all in the case file**: the exact sources, the field meanings and the evidence for each,
the supporting record locations, the associated sessions, the plausible candidates you rejected, and
what is still unresolved. Later readers use that record instead of repeating the discovery. If the
history is missing, unreadable or ambiguous, state the specific limitation, and ask the user for the
missing path, export, or identifying detail.

## Context safety

One transcript record can exceed a megabyte, or embed a whole history. Printing one record whole can
overflow the context of the reader. So:

1. **Measure before reading.** Count the lines and bytes of the file, and list the line numbers of
   any line over 100,000 characters:

   ```
   wc -lc "$FILE"
   awk '{ if (length($0) > 100000) print NR, length($0) }' "$FILE"
   ```
2. **Never print a record, or search for content, whole.** Get line numbers and counts first (a
   search that prints only the line numbers; a count of the record types), then extract small fields
   from specific lines (one line, parsed, with only the fields you need, or cut to the first 500
   characters). Use the extraction commands recorded in the case file for the source in front of you.
3. **Narrow anything over 500 characters.** If a command returns more than 500 characters for one
   record, tighten the field or the slice.
4. **Read-only.** Never modify, move or delete a session file. Work on copies, inside the workspace,
   `<system temp>/apm-diagnosis/<session-id>/`.
