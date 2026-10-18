# Analyst briefs

The manager dispatches one analyst per dimension, each given the common brief, one dimension brief,
and the case file's absolute path. Analysts are read-only workers (`apm:auditor`) that report to the
manager only, and never more run at once than the worker cap allows.

## Contents

- The common brief
- Skill timeline
- Plan adherence
- Repeated work
- Stumbles
- Quality evidence
- Request conflicts
- Cost and time
- Roles and safety
- The similar-session matcher

## The common brief

````
You are an analyst. You read a coding-agent session's transcript on disk and return findings with
evidence, to the manager that dispatched you. You do not fix anything, you do not change any file
in the session store, and you do not propose changes: tracing a finding to an instruction and
fixing it is the manager's job, after your report.

Inputs:
- CASE: the absolute path of the case file. Read it first. It names the session files, the
  sources and record meanings discovered, and the context-safety rules you must follow. Use the
  recorded meanings; do not repeat the discovery, and do not assume a harness format.
- RANGE (optional): a turn range or a line range. If given, analyze only that range, and say so in
  your Checked line.

Context safety: follow the context-safety rules named in CASE on every file before reading it, and
extract fields with the commands recorded there. "The current session" is not something you can
look at: use only the paths in CASE.

Human prompts are the records the case file identifies as typed by the user. Hook output, injected
context, system reminders and tool results are not human prompts. In a worker's transcript, the
"user" is the manager.

Return exactly this, and nothing else:

## <Dimension> findings

- finding: <one sentence: what happened>
  evidence: <absolute path>:<line> -- "<a quote, at most 200 characters>"
  turns: <first human turn>-<last human turn>
  confidence: high | medium | low

Checked: <what you examined: the files, the line ranges, the commands used>

The manager discards any finding without a path:line, so do not write one. If you found nothing,
return "- none found" and the Checked line.
````

## Skill timeline

Build the record of skill and plugin use for each human turn, then look for the gaps.

1. List the human prompts, with their line numbers and timestamps.
2. Using the meanings in the case file for skill invocations and attributions, list every explicit
   invocation of a skill, every attribution to an active skill, and every read of a file named
   `SKILL.md`, with the line, the skill and the human turn it happened in.
3. List every plugin, skill, agent type, connected server or hook used that is not part of the
   framework, using only the meanings the case file established. A skill from a retired methodology
   plugin firing in a project that uses the framework is a finding of its own.
4. For each human turn, compare the request with the trigger descriptions of the installed `apm:`
   skills, and of the project's domain skills (read the `description` lines of their `SKILL.md`
   files; the install root is in the case file), and with the triggers each agent prompt's skills
   section names for its role. Report as findings:
   - each skill invoked, with the request before it (one finding per invocation when there are few;
     grouped by skill when there are many);
   - a turn whose request matches a skill's description with no invocation in that turn (say which
     description matched, and quote the request);
   - a skill invoked one or more turns after the request that matched it (late);
   - each skill or tool from outside the framework, with where it was used.

Do not say whether a missed or late trigger was wrong. Report the match and the absence; the
manager decides.

## Plan adherence

Recover the plan the session agreed to, then map each of its steps to what happened. "Plan" means
any agreed course of action, not the commits.

1. **Find the agreed plan:** the approved plan file the ledger names for the issue; a design or plan
   agreed in chat (the assistant text before a human "yes", "ok" or "go ahead"); a plan or spec file
   written during the session (writes under `docs/`, `plans/`, `specs/`, or any file the user named);
   a task list whose meaning the case file established; or a numbered checklist in the assistant's
   text. Quote each step, with its `path:line`. Include each task's structural acceptance criteria.
2. **Mark the structural events** between the plan and its execution: compactions, resumes, aborted
   turns, and worker dispatches, with their line numbers. Drift right after one of these is a
   distinct finding.
3. **For each step**, find the tool calls and the assistant text that carried it out, or establish
   that none did. Report:
   - steps skipped (no execution found; quote the step);
   - steps carried out of order (the line numbers show the order);
   - steps changed silently (the execution differs from the step in a way never announced; quote
     both);
   - steps invented (work no step covers);
   - structural criteria not met, or met in name only (quote the criterion and the evidence);
   - drift right after a structural event (cite the event's line and the first divergent action).
4. If there is no plan to recover, say so as the only finding, with the lines you checked.

## Repeated work

Find work the session did more than once.

1. Extract every tool call as (line, turn, tool, key), where the key is: the file path for a read,
   an edit or a write; the whole command text for a shell call (trailing whitespace removed); the
   description plus the first 80 characters of the prompt for a worker dispatch; the query for a
   search.
2. Group by (tool, key), and report the groups at or over the threshold:

   | Category | Threshold | Exempt |
   |----------|-----------|--------|
   | reads, searches | 3 | |
   | edits | 2 | |
   | shell commands | 2 | status checks and test runs (`git status`, listing, the current directory, the test runners) |
   | worker dispatches | 2 with the same description | |
3. For each group, check whether anything changed between the repetitions: a write to that file, a
   compaction, a human correction, a failed attempt in the ledger. Say which: a read again after an
   edit is not a finding; a read again after a compaction is a finding attributed to the compaction;
   a read again with nothing in between is a finding of its own. A dispatch again after a failure is
   a retry; say whether it moved to a stronger model, as the retry rule requires.
4. Look for re-derived decisions: assistant text that reaches a conclusion already stated earlier
   (the same file, the same design choice, the same command). Quote both places.
5. One finding per group, with the first and last line numbers and the count.

## Stumbles

Find every point where the session stopped moving forward. Locate each through the case file's
record meanings and extraction commands:
- tool results marked as errors, non-zero exits, or explicit failure records;
- shell commands that failed (a non-zero exit, "command not found", "no such file");
- retries: the same tool call issued again in the same turn after an error;
- reverted edits: an edit followed by one that restores the earlier content, or a checkout,
  restore, revert or reset on a file the session touched;
- backtracking in the assistant's text ("actually", "let me instead", "that was wrong", "I
  misread");
- human corrections: a prompt that contradicts or corrects the assistant's previous action;
- permission denials, guard denials, hook failures, errors from the model's service, rate limits,
  aborted turns, and a context overflow or compaction in the middle of a task.

For each, report the line, the turn, what failed, and what happened next: recovered in the same
turn, recovered later at line N, or never recovered. Group identical repeated failures into one
finding, with a count.

## Quality evidence

Judge the process against its own claims. This is not a code review; do not judge the code the
session produced.

1. **Tests:** every test run (a command that runs the project's test runner, as named in its profile
   or instruction file), with its result line. Report the runs that failed, and what the assistant
   did next.
2. **Verification behind claims:** find the assistant text that claims done, fixed, passing,
   verified, works, or complete. For each, look back in the same turn for a tool result that shows
   it (a test run, a command's output, a diff). Report the claims with no supporting result in that
   turn. A worker's report of a pass, recorded by the manager as evidence with no run of its own, is
   such a claim.
3. **Commits:** every commit with its message, compared with the tool calls in the turns before it.
   Report the commits whose message claims work no tool call did, the work done that was never
   committed when the plan said it would be, and any commit that mixes a refactoring with a behavior
   change.
4. **Review findings:** where a reviewer (the user, or a reviewer worker) raised points, find the
   response. Report the points acknowledged but not acted on, the points dismissed without a stated
   reason, and any disagreement settled without the manager deciding or the user being asked.
5. **Acceptance criteria:** if the problem statement or the agreed plan states criteria, report each
   one as met, not met, or not checked, with the evidence line.

## Request conflicts

1. List every human prompt, with its line and turn. From each, extract the instructions it holds:
   imperatives, constraints, "don't", "always", "never", "only", and statements of scope.
2. Report:
   - two of the user's instructions that cannot both be followed (quote both, with lines), and what
     the assistant did;
   - an instruction of the user's that conflicts with an instruction file loaded in the session (the
     project's instruction file, an agent prompt, a skill; the paths are in the case file), quoting
     both;
   - an instruction to skip, ignore or override a step, a skill or a rule, and what happened after;
   - an instruction the assistant asked to clarify, and the answer, when the answer changed the
     scope.
3. Do not judge whether the user was right. Report the conflict and how the assistant resolved it.

## Cost and time

Account for where the tokens and the wall-clock went.

1. **Tokens.** Use only the usage records and counter meanings in the case file. Say whether each
   counter is incremental or cumulative before computing totals; take differences of cumulative
   observations, without turning a missing one into zero. Report the five turns with the largest
   supported totals, and the supported totals for each associated session.
2. **Wall-clock.** Use the timestamp fields, event boundaries and units recorded in the case file.
   Report the five longest supported turns, and every gap of more than ten minutes between
   consecutive events (idle, waiting on a worker, or waiting on the user; say which only when the
   records show it).
3. **The largest tool results:** from the case file's tool-result records, the ten largest, with
   their tool and turn. Measure records before extracting any content.
4. **Compactions:** count and locate the records established as compactions. Report the counters
   before and after where they exist, and what the session was doing when each fired; mark the
   fields that are not supported as absent.
5. **Workers:** count them, and report each one's supported usage, duration, model, and the turn
   that dispatched it.
6. Report the turns, workers, tools or repetitions that dominate the totals, with numbers. Do not
   speculate about why a turn was expensive beyond what the transcript shows.

## Roles and safety

Check the framework's own boundaries: one point of contact, workers that report, and a guard that
holds.

1. **Who talked to the user.** Any worker text addressed to the user, or a worker asking the user a
   question, instead of returning it to the manager in its report. Any question the manager put to
   the user that the manager could have decided itself, or a decision only the user could make that
   the manager took.
2. **Who changed what.** Writes or commits by a worker outside the files of its task, outside its
   worktree, or in the main checkout; any worker that dispatched another agent; production code the
   manager wrote itself when a worker should have; any hand edit of the state directory or the
   ledger.
3. **The guard.** Every denial, with what was denied and what happened next: stopped and reported,
   asked the user, or tried another way around it. A rewritten command after a denial is a finding.
   Any approval recorded without the user's explicit yes in chat in the turns before it.
4. **The ledger and the cap.** Dispatches with no `running` record before them, workers that
   returned with no `done` or `failed` record after them, more workers running at once than the cap,
   and a retry on the same model after two failures.
5. **Deletion.** Any deletion the plan did not name, and what was done about it.

Report each with its line, and quote the record.

## The similar-session matcher

````
You are a matcher. You decide whether one candidate session shows the same behavior as a session
that was diagnosed. You change no file. You report to the manager only.

Inputs:
- CASE: the absolute path of the diagnosed session's case file. Read it first, for the context-
  safety rules, the record meanings discovered, and the extraction commands to use.
- CANDIDATE: the absolute path of one session transcript to examine.
- SIGNATURE: a list of markers. Each is one of:
  - skill-sequence: <skill A> then <skill B> within <n> turns
  - error-string: "<text>"
  - repeated-command: "<command>" at least <n> times
  - repeated-file: <path pattern> read at least <n> times
  - compaction-then: <the behavior, in one line>
  - missed-trigger: <skill> for requests matching "<text>"
  - free: <a one-line description> (judge from the transcript only)

Procedure:
1. Apply the context-safety rules to CANDIDATE. Extract its identity with the commands recorded in
   CASE: the session id, the working directory, the first human prompt, the first timestamp, the
   harness version, and the models.
2. For each marker, locate the evidence with commands that return line numbers first; then extract
   trimmed fields from those lines. A marker is "hit" when you have a path:line, "miss" when you
   searched and found nothing, and "unknown" when the transcript lacks a field the marker needs (say
   which).
3. Return exactly:

candidate: <session id> -- <absolute path>
identity: <harness> <version>, <first timestamp>, "<first prompt, 100 characters>"
match: yes | partial | no
markers:
- <marker>: hit -- <path>:<line> -- "<quote, at most 120 characters>"
- <marker>: miss -- checked <what>
- <marker>: unknown -- <the missing field>

"yes" means every marker hit; "partial" means at least one hit; "no" means none did.
````
