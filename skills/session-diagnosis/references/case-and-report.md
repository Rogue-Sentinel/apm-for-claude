# The case file and the report

Both live in the workspace, `<system temp>/apm-diagnosis/<session-id>/`, in the system's temporary
directory, outside the repository and the measured tree. The operating system may clean it, so the
report is copied elsewhere only if the user asks. The case file is what the analysts work from; the
report is what the user reads.

## Contents

- The case file
- The report
- Provenance labels

## The case file

Fill it after locating the sessions, before any analyst is dispatched.

````
# Case: <session-id>

Workspace: <system temp>/apm-diagnosis/<session-id>/ (the full path, as told to the user)
Created: <ISO timestamp>

## Problem statement (agreed with the user)

<One paragraph: the session or sessions, the turn range if known, what was expected, what
happened, and the observable that matters: wall-clock, tokens, repeated actions, or one specific
unexpected action.>

The goal includes an issue: yes | no        The goal includes a bundle: yes | no

## Sessions

| Role | Session id | Absolute path | Lines | Bytes | Longest line (bytes) | First prompt (first 120 characters) | First timestamp |
|---|---|---|---|---|---|---|---|
| main (the manager) | | | | | | | |
| worker (<agent type>, <model>) | | | | | | | |

Rejected candidates: <id -- path -- why rejected>, or "none".

Session still running when read: yes | no (modified <ISO>, <N> lines)

## Environment

- Operating system: <name and version>
- Harness: <name> <version>
- Models seen: <model id -- where (main, or which worker)>
- APM plugin: install root <path>; version <x.y.z>; commit <sha, or "not a checkout">
- The project's recorded framework version (from its profile): <x.y.z>
- Agent prompts and skills read or loaded during the session:

| Agent prompt, skill or source path | sha1, or unavailable | Provenance | Supporting location |
|---|---|---|---|

- Other plugins, extensions and connected servers configured: <list, or "none found">
- Instruction files present (paths only): <list>
- The project's evidence: the approved plan <path>, the ledger <branch and commit>, the profile <path>

Label every environment and skill observation with its provenance (see "Provenance labels"). Check
the notes, archives and captured skill bodies you were given before declaring historical
information unavailable. A missing original path does not erase a retained copy. A current version
or modification time does not establish the historical one, and one captured skill body does not
authenticate a whole installation.

## Context-safety rules for every reader of these files

- Follow the context-safety rules in the skill's transcripts reference before reading any file
  listed here.
- In a worker's transcript, the "user" is the manager.

## Discovered sources and record meanings

- Sources consulted: <absolute path, tool, help, or documentation>
- Extraction commands or queries: <the bounded commands or tool queries for each source>
- Target identity evidence: <session id, working directory, timestamps, matching content, and
  supporting record locations>
- Associated sessions: <session id, relationship, supporting record locations, or "none found">
- Human messages: <record shape, and the evidence for its meaning>
- Injected messages and the manager's dispatches: <record shape, and the evidence for its meaning>
- Assistant messages: <record shape, and the evidence for its meaning>
- Tool calls and results: <record shapes, how they are matched, and the evidence for those meanings>
- Usage counters: <fields, incremental or cumulative, units, and evidence, or "unavailable">
- Timing: <fields, units, event boundaries, and evidence, or "unavailable">
- Other relevant records: <models, versions, compactions, guard denials, or other meanings, and
  their evidence>
- Unresolved information: <missing, inaccessible, ambiguous or absent information, or "none">
````

## The report

Fill every section, in order, write it to the workspace, show it to the user, and give its path.

````
# Session diagnosis: <session-id>

Report path: <system temp>/apm-diagnosis/<session-id>/report.md
Written: <ISO timestamp>

## 1. Problem statement (required)

<Copied from the case file.>

## 2. Triage verdict (required)

<What the evidence shows happened around the reported problem. Prose, with a path:line after every
claim. State the confidence (high, medium or low) and what would raise it.>

## 3. Environment (required)

- Operating system:
- Harness and version:
- Models seen:
- APM plugin install root, version and commit; the project's recorded framework version:
- Agent prompts and skills read or loaded (the sha1 table from the case file):
- Other plugins, extensions and connected servers:
- Instruction files present (paths only):

Label every field and skill observation with its provenance, and record its supporting location.

## 4. Sessions examined (required)

| Role | Session id | Absolute path | Lines | Bytes |
|---|---|---|---|---|

Rejected candidates: <id -- path -- why>, or "none".

## 5. Timeline (required)

One row per prompt the user typed. The events column lists the skills invoked, the workers
dispatched, compactions, errors, guard denials, resumes and aborts.

| Turn | Line | Time | Request (one line) | Events |
|---|---|---|---|---|

## 6. Findings (required; one subsection per dimension)

Each finding:

    - finding: <one sentence>
      evidence: <path:line> -- "<a short quote>"
      turns: <first>-<last>
      confidence: high | medium | low

A dimension with nothing to report says "none found -- checked: <what was checked>".

### 6.1 Skill timeline
### 6.2 Plan adherence
### 6.3 Repeated work
### 6.4 Stumbles
### 6.5 Quality evidence
### 6.6 Request conflicts
### 6.7 Cost and time
### 6.8 Roles and safety
### 6.9 Other plugins and skills used

## 7. Instructions involved (required)

One entry per confirmed finding, or group of findings with one cause:

    - finding(s): <6.x references>
      instruction: <path:line> -- "<the quoted instruction>", or "none found"
      kind: wrong | missing | ambiguous | unreachable | not involved
      involvement: not indicated | possible | likely
      evidence: <path:line list>
      correction: <the exact proposed wording, or "none: the instruction was right">
      routed to: <a task for the project (issue or branch) | an issue on the framework's
                 repository, after the user approves its text | a question for the user | none>

Every correction cites the findings it answers, and is tested before it ships.

## 8. Coverage notes (required)

- Not read: <ranges and files, and why>
- Harness features unavailable: <list, or "none">
- The session was in progress when read: yes | no
- For the user to double-check: <list, or "none">

## 9. Similar sessions (only when asked)

| Session id | Path | Date | Harness | Matched | Did not match |
|---|---|---|---|---|---|
````

## Provenance labels

Every environment field and every observation of a skill or agent prompt carries one label, and its
supporting location:

| Label | Means |
|-------|-------|
| historical evidence | recorded in the transcript, or a copy captured at the time |
| unverified snapshot | a copy supplied later, whose match to the time of the session is not shown |
| current observation | read from the system now; it may differ from what the session had |
| unknown | no evidence either way |
