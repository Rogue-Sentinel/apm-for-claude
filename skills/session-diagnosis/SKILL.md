---
name: session-diagnosis
description: "Use when the user wants to know why an APM session went wrong (repeated work, an ignored plan, stumbles, a poor result, a skill that never fired, a worker that overstepped, it took too long, it cost too much, what is it doing) for the current session or a past one named by id or path, or wants a report or an issue built from one."
---

# Session diagnosis

Agree with the user on what went wrong, read the session's transcripts on disk, and report what
happened with evidence. Then trace each confirmed finding to the instruction that allowed it, so
that the wrong instruction gets fixed and the failure does not repeat.

## When this applies

- The user asks why a session went wrong: it repeated work, ignored the plan, kept stumbling,
  produced a poor result, never invoked a skill it should have, took too long, cost too much.
- A worker overstepped its role: it addressed the user, worked outside its files, ran something the
  guard denied, or reported a pass that the manager's own run did not show.
- A session is still running and the user asks what it is doing.
- The user wants an issue, or a shareable record, built from what happened.

**The manager runs this skill.** It talks to the user, dispatches the analysts, writes the report,
and routes the fixes. Analysts are read-only workers that report to the manager only. The session
can be the current one or a past one, named by its id or its path.

## The core rule

**Every finding cites `path:line`. No citation, no finding.** Every number comes from the
transcript, or from a command that was run, never from memory. Analysts report what happened; the
manager traces each confirmed finding to the instruction behind it, and proposes the fix. A
diagnosis that ends at "what happened" has not finished: "fixed properly" includes fixing the
instruction or project knowledge that let it happen.

## The problem statement

Track each step of the diagnosis (intake, locating, triage, the report, the fixes, and the export
or similar sessions when asked) as its own item in the task list; the optional steps run only on
their stated condition.

**Intake comes before any analysis.** Ask the user one question at a time until you can write a
statement that names:
- the session or sessions, and the turn range if known;
- what the user expected;
- what happened instead;
- the observable they care about: wall-clock time, tokens, repeated actions, or one specific action.

"It took too long" is a complaint, not a problem statement. Note whether the user wants an issue
filed, or a shareable bundle, as the outcome.

- **Nothing in the steps below starts until the user has answered.** If they are away, write the
  questions in chat and wait. A statement you reconstructed for them is not their answer.
- **An already-scoped request is itself the statement**: one specific event, what is running right
  now, or a named analysis to run. Answer it, then ask whether they want more. A whole-session "why"
  is a complaint, and needs intake.
- Record the agreed statement at the top of the case file.

## Finding the transcripts

Claude Code keeps each session as a JSON Lines transcript, one record per line, under
`~/.claude/projects/`:

```
~/.claude/projects/<project>/<session-id>.jsonl                       the main session
~/.claude/projects/<project>/<session-id>/subagents/agent-<id>.jsonl  each worker it dispatched
~/.claude/projects/<project>/<session-id>/subagents/agent-<id>.meta.json
                                                     the worker's agent type, description, model,
                                                     and the id of the call that dispatched it
~/.claude/projects/<project>/<session-id>/tool-results/                large tool outputs kept apart
```

`<project>` is the session's working directory as an absolute path, with every character that is not
a letter or a digit replaced by `-`: a project at `C:\Users\me\repos\My App` is under
`C--Users-me-repos-My-App`. A session started in a worktree has its own directory, named from the
worktree's path. Those formats belong to the harness and change between versions: **verify** every
path and record meaning against the files in front of you, never from this description alone.

1. **Resolve each session to verified absolute paths.** Confirm a past session by quoting its first
   human prompt and its first timestamp. List every candidate you rejected, with the reason, or
   "none". Recency alone is not confirmation.
2. **Enumerate the worker transcripts**, and match each to the dispatch that started it.
3. **Collect the framework's own evidence**: the ledger on the `apm/state` branch (the task
   statuses, workers, models, attempts and recorded evidence; read it through `apm brief` and
   `git log apm/state`, never by editing it), the approved plan, the profile, and the agent prompts
   and `apm:` skills of the installed plugin version.
4. **Make the workspace** at `.apm/diagnosis/<session-id>/` in the project, and tell the user its
   path. It holds session data, so it is never committed; the guard blocks writes outside the
   project, so it does not go in the home directory.
5. **Fill the case file** there, following
   [references/case-and-report.md](references/case-and-report.md).

**Context safety, every file, every time.** One transcript record can exceed a megabyte; measure a
file before you read it, never print whole records, and never modify, move or delete a session file.
The rules, with the commands, are in [references/transcripts.md](references/transcripts.md).

## Triage

Read the region around the reported problem yourself first. Then dispatch one analyst per
dimension, each given the case file's absolute path, the common brief, and its dimension's brief
from [references/analyst-briefs.md](references/analyst-briefs.md):

| Dimension | What it looks for |
|-----------|-------------------|
| Skill timeline | which skills fired when, which requests matched a skill that never fired |
| Plan adherence | each step of the agreed plan, and what happened to it |
| Repeated work | reads, edits, commands and dispatches done more than once |
| Stumbles | every point where the session stopped moving forward |
| Quality evidence | claims of done or passing, against the results that would prove them |
| Request conflicts | instructions that could not all be followed, and how they were resolved |
| Cost and time | where the tokens and the wall-clock went |
| Roles and safety | the framework's own boundaries: who talked to the user, who changed what, the guard |

- **Analysts are read-only workers.** Dispatch each as `apm:auditor` (the read-only survey role) on
  the profile's model for it, and **never more at once than the worker cap** (three at most): run the
  eight dimensions in waves. Split a dimension by turn range when the transcript is long.
- **Pass exact paths and ids.** An analyst's "current session" is its own; it only knows the paths
  you give it.
- **Human prompts only.** Hook output, injected context, system reminders and tool results are not
  the user's words. In a worker's transcript, the "user" is the manager.

**Which to read first and lead with:**

| Complaint | Read first, and lead the verdict with |
|-----------|---------------------------------------|
| "It took too long." | cost and time, stumbles |
| "Why did it do this extra work?" | repeated work, plan adherence |
| "Why is it so expensive?" | cost and time |
| "What is it doing?" (still running) | skill timeline; note "in progress" in the coverage notes |
| "It ignored the plan." | plan adherence, the compaction lines first |
| "Skill X never fired." | skill timeline |
| "A worker went off on its own." | roles and safety, plan adherence |

## Every finding cites evidence

- **Discard any returned finding without a `path:line`.** It does not go in the report.
- **Check what the cited line proves.** A quote that mentions a test is not proof the test ran; a
  claim of "passing" is not proof it passed. Report what the evidence supports, and its confidence.
- **Numbers are computed, not recalled.** A token total, a cost or a duration comes from the
  transcript's own counters and timestamps, whose meanings were established in the case file, or it
  is left out.
- **Keep the supporting case.** Do not throw away the lines a finding rests on; a symbolic link or
  an alias of a file is not a redundant copy.
- **Fill the report** in [references/case-and-report.md](references/case-and-report.md), every
  section in order, write it to the workspace, show it to the user, and give its path.

## From finding to fix

For every confirmed finding, ask what instruction allowed it, and fix that.

1. **Find the instruction.** Was the agent told to do this, never told not to, or told something
   wrong? Look in this order: the brief the manager wrote for the worker, the approved plan, the
   agent prompt (`agents/<role>.md` in the installed plugin), the `apm:` skill that applied (or the
   one whose description failed to trigger), the project's instruction file, its profile, and its
   domain skills. Cite it, `path:line`, and quote it.
2. **Classify it:** wrong (it says something untrue), missing (nothing covered the case), ambiguous
   (it can be read both ways), unreachable (it exists but did not load: a description that did not
   trigger, a reference nobody linked), or not involved (the agent had the right instruction and did
   not follow it). Record the involvement as not indicated, possible or likely, with the evidence.
3. **Propose the correction** as exact wording, with the finding it answers. A correction to wording
   is tested before it ships, like any skill edit (`apm:writing-skills`).
4. **Route it.**
   - **Project knowledge** (the instruction file, the profile, a domain skill, a plan template): a
     task for a debugger or an implementer, on its own branch or as its own commit, through the
     normal path. The manager does not edit it in the middle of the diagnosis.
   - **The framework itself** (an agent prompt or an `apm:` skill): an issue on the framework's
     repository. Search the open and closed issues first, show the user the exact text, and file it
     only after they approve it (see
     [references/export-and-redaction.md](references/export-and-redaction.md)).
   - **An approved plan, or a design decision:** a question for the user. The manager does not change
     an approved plan on its own.
5. **Report** the findings, the instructions behind them, and what was routed where, in the
   manager's next update.

**The fix is never a guess.** A finding with no instruction behind it says so ("the instruction was
right; the agent did not follow it"), and the correction, if any, is to wording that makes the
instruction hold (see "Wording that holds under pressure" in `apm:writing-skills`), tested against
the transcript's own failure as the baseline.

## Exporting and similar sessions

- **A bundle only when the user asks for one;** never build one unprompted. If the intake goal was an
  issue, say once that a scrubbed bundle is available on request, then wait. Ask the redaction level,
  saying what each includes: skeleton (no tool-result bodies), evidence (bodies only for cited
  events), or full. Build it, scrub it, audit it, and repeat the scrub and the audit until the audit
  returns clean; then show the scrub log, the file list, and the privacy and evidence outcomes.
  Archive it only after the user approves, and say that scrubbing can miss things: they must review
  every file before sharing it. The procedure and the briefs are in
  [references/export-and-redaction.md](references/export-and-redaction.md).
- **Similar sessions, when asked:** turn the confirmed findings into a signature, list the candidate
  transcripts by modification time and size, find the marker lines, dispatch the matcher brief per
  candidate (in waves under the worker cap), and add section 9 to the report.

## Red flags

| Thought | Reality |
|---------|---------|
| "The problem is obvious; skip intake." | The problem statement scopes everything. Ask. |
| "The user is away, so I'll reconstruct the statement." | You cannot reconstruct what they wanted. Write the questions and wait. |
| "I'll sweep everything now and ask at the end." | An unscoped sweep spends their budget on the wrong question. Ask first. |
| "They want an issue, so I'll build the bundle now." | The bundle is their session data, packaged. Build it only when they ask. |
| "The cost per token is well known." | A number you did not compute from the transcript is invented. Cite it or drop it. |
| "I'll fix the skill right now, while I'm here." | The fix goes through the normal path, tested, and a framework change through an approved issue. |
| "The agent just made a mistake; no instruction is involved." | Look first. Say "not involved" only with the evidence that the instruction was right. |
| "All eight analysts at once will be faster." | The worker cap holds here too. Run them in waves. |

## References

- [references/transcripts.md](references/transcripts.md): discovering the sessions, the record
  meanings to establish, and the context-safety rules for every reader.
- [references/analyst-briefs.md](references/analyst-briefs.md): the common analyst brief, one brief
  per dimension, and the similar-session matcher.
- [references/case-and-report.md](references/case-and-report.md): the case file and the report
  templates.
- [references/export-and-redaction.md](references/export-and-redaction.md): the redaction policy,
  the bundle, the scrub and audit briefs, and filing an issue.

## Common mistakes

- **Analyzing before the user has agreed the problem statement.**
- **Printing a whole transcript record**, and flooding the context.
- **A finding with no `path:line`**, or a number with no source.
- **Treating hook output or a manager's dispatch as the user's words.**
- **Stopping at "what happened"** without finding the instruction behind it.
- **Editing an instruction during the diagnosis** instead of routing a tested fix.
- **Filing an issue, or building a bundle, without the user's approval** of the exact text.
- **Committing the workspace**, which holds session data.
