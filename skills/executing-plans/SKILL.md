---
name: executing-plans
description: "Use when the manager is building an approved plan: dispatching a worker per task, verifying its work, reviewing it, routing fixes, recording state after every task, or resuming a build after a context reset."
---

# Executing plans

Build an approved plan task by task: a fresh worker for each task, the manager's own verification
of what it produced, a review after every task, and a record after every task. The plan already did
the thinking. Carry it out exactly, prove each task with commands you ran yourself, and leave a
record that survives your own forgetting.

## When this applies

- The user has approved the plan in chat, and the issue is `building`.
- A build is being resumed after a closed session or a context reset.

Never build from a plan the user has not approved, and never from an imported plan until the user
approves it under the framework.

## The core rule

**A fresh worker per task, the manager's own verification, a review after every task, and a record
after every task.** The manager directs; it does not write production code when a worker can, and
it never fixes review findings itself, since a fix it makes skips review. A worker's claim is not
evidence.

**Once the plan is approved, run to the merge.** Do not stop between tasks to check in, and do not
ask "should I continue?": the user approved the plan so they would not have to answer that. Keep
them informed in short lines (what you are about to do, what a worker reported, what you verified),
and stop only for the reasons in "When to stop and ask".

## Before the first task

1. **Branch.** The work happens on the issue's branch, cut from `main`. Nothing is built on `main`
   itself. Every builder works in its own worktree (`apm:worktrees`).
2. **Read the state, not your memory.** Run `<CLI> brief` and read the issue's tasks in the ledger.
   Tasks marked `done` are done: do not re-dispatch them. Resume at the first task not done. A task
   left `running` by a reset is the one that was lost: check its worktree, its branch and `git log`
   before you dispatch it again. Conversation memory does not survive compaction, and a manager that
   lost its place and re-dispatched a whole sequence of finished tasks is the most expensive failure
   there is. The commits the ledger names exist in git even when you no longer remember them. Read
   only this issue's tasks: another issue's record is not your progress.
3. **Read the plan once.** Note its Global Constraints, Review Focus and structural criteria. Read
   the design it names: the design is the binding authority, the plan is its argument, and conflicts
   inside the plan resolve against the design. If no design is reachable, note it: rulings made
   without one are provisional.
4. **Scan for conflicts before Task 1**, writing down what you checked as you check it. The scan's
   output is a table, not a verdict:
   - one row for every pair of tasks that share a file or an interface: the two tasks, what one
     produces against what the other consumes, and what you found;
   - one row for every task: whether its own text agrees with itself (the tests it specifies
     against the code it specifies, the files it creates against the files it later touches);
   - anything the plan mandates that the review rubric treats as a defect (a test that asserts
     nothing, a duplicated block of logic).

   "The scan is clean" without those rows is not a scan you ran. Rule on what you find before
   building (below). The review loop remains the net for conflicts that only appear in the code.

**Rulings.** A conflict, an ambiguity or a plan defect that does not change what the user approved
is yours to settle: the design binds, the plan argues, your judgment settles what neither answers.
Record each as `Ruling: <what you decided> — <why> — <what it costs if wrong>` on the task it
affects (`<CLI> task N ID --evidence TEXT`), and carry it into the dispatch of every later task that
touches the same interface. A deviation without a recorded ruling is a decision made in secret. A
conflict that would change what gets built, or drop or loosen a structural criterion, is not a
ruling: it is a question for the user.

## One task at a time

The loop, for every task:

```
record    <CLI> task N ID --status running --worker implementer --model sonnet
dispatch  one fresh worker, in its own worktree, with its brief
report    read it; handle its status
verify    run the verification yourself, in its worktree; merge; run it again on the branch
review    a reviewer checks the diff; fix rounds until clean, or stop and ask
record    <CLI> task N ID --status done --evidence "<the command you ran and its result>"
next      the next task
```

- **Sequential by default.** Tasks run in parallel only through `apm:parallel-dispatch`: disjoint
  files, never more than the worker cap.
- **Never start the next task** while the review has open must-fix findings that are neither fixed
  nor brought to the user.
- **Batch small same-shape work.** Several small, independent edits of one kind (the same one-line
  fix across files, a constant changed in several places) go to one worker in one brief listing
  every file and its change, and are reviewed as one diff. Keep one dispatch per task for work that
  needs its own judgment, tests or review.
- **Bugs a worker finds** that are not the task's own: dispatch the debugger (`apm:debugger` role,
  with `apm:systematic-debugging`). If related to this work, its fix lands on this branch as its own
  commit; if not, file an issue. Either way it is in your next update. A fix that needs a design
  change, or would break the standard, is a question for the user.

**Choosing the model.** Use the least powerful model that can do the job well. The profile's
`models` gives each role's default (auditor haiku, planner opus, implementer sonnet, debugger opus,
reviewer opus).

- A mechanical task (one or two files, a complete specification, or plan text that contains the
  code to write): the cheapest tier.
- Integration and judgment (several files, matching patterns, debugging): the standard tier.
- Architecture and design, and the final whole-branch review: the most capable tier.
- Reviewers scale with the diff's size, complexity and risk. A scoped re-review of a small fix can
  run a tier lower.
- Turn count beats token price: the cheapest models often take two or three times the turns on
  multi-step work, and cost more overall. A mid tier is the floor for reviewers and for implementers
  working from prose.
- **Always set the model explicitly.** An omitted model inherits the session's, usually the most
  expensive one.

**Waiting on workers.** Never poll with short timeouts, and never sit in one silent, open-ended wait.
While you have local work (recording, packaging the next review, reading a report), do it; results
arrive on their own. When you are genuinely idle, wait in bounded stretches, and between them post
one line of status and check your live workers, chasing any that finished without reporting.

## Briefing a worker

**Record BASE before you dispatch:** the commit the task starts from, on the feature branch. Every
review range is cut from it, never from "the previous commit", which silently drops all but the last
commit of a task that made several.

**The brief is the task's own text**, exactly as the plan states it, and it is the single source of
the worker's requirements. Point the worker at its section of the committed plan file (the path, and
the `### Task N` heading) with the Global Constraints, or extract that section to a scratch file
outside the repository. Never make a worker read the whole plan, and never paraphrase the exact
values: numbers, strings, signatures and test cases appear only in the brief.

The dispatch says:

1. one line on where this task fits;
2. the brief, introduced as "read this first: it is your requirements, with the exact values to use
   verbatim";
3. the interfaces and rulings from earlier tasks that the brief cannot know;
4. your resolution of any ambiguity you noticed in the brief;
5. the files it owns, and that it stays inside them;
6. the project knowledge it needs from the profile;
7. a pointer to any deferred finding recorded in the area it touches;
8. the report it returns.

A dispatch describes one task, not the session's history. Do not paste summaries of earlier tasks:
one real dispatch reached 42,000 characters, nearly all of it pasted history. Everything you paste,
and everything a worker prints back, stays in your context for the rest of the session, so hand
artifacts over as files. When a task's evidence will be long, have the worker write its full output
to a report file outside the tracked tree and return the structured report with that path, kept
short; the same file then carries what was tried into every fix round. Note the worker's identity
from the dispatch result, so a fix round can resume it. The template is
[references/implementer-brief.md](references/implementer-brief.md).

**Handling the report.** Every worker returns status (done, blocked or needs decision), files
changed, commands run with their output, concerns, and found elsewhere.

- **Done, with concerns:** read the concerns first. About correctness or scope: address them before
  review. Observations ("this file is getting large"): note them and go on to review.
- **Blocked by missing context:** provide it and dispatch again on the same model.
- **Blocked because the task needs more reasoning:** dispatch again one tier stronger.
- **Blocked because the task is too large:** split it. A split that keeps what was approved is a
  ruling; one that changes it goes to the user.
- **Blocked because the plan is wrong:** rule on the correction and dispatch again with the ruling,
  or, if it changes what gets built, ask the user.
- **Needs decision:** decide it if you can, and answer clearly and completely, with whatever extra
  context it needs, before dispatching again; do not rush it into building. If only the user can
  decide it, ask them and record it (below).

Never ignore an escalation, and never send the same model back to the same task with nothing
changed. If a worker said it is stuck, something has to change.

## Verify it yourself

When a worker reports done, run the verification **yourself**, read the actual output, and only then
believe it:

1. Run the task's tests and the project's full suite and checkers in the **worker's worktree**.
2. If they pass, merge the worktree's branch into the feature branch (`apm:worktrees`).
3. Run them again **on the feature branch**: a clean task can still break once merged with the
   others.

Before a task is recorded done, all of these hold, with evidence from this session rather than an
impression of the diff:

- every test the brief names exists, ran, and you read its output;
- the report shows the test failing first (its output, and why the failure was expected) and then
  passing;
- your final run passed, and the output is clean: warnings and stray noise are findings;
- every `Expected:` line in the brief was compared with real output;
- the touched files are within the limits (`<CLI> metrics`), and `<CLI> debt check` passes;
- every deviation from the brief has a recorded ruling.

If any is missing, the task is not done. `apm:verification` governs the claim.

When a run's output does not match the brief's `Expected:` line, there are two causes. **The code is
wrong:** it goes back to the worker, or to a debugger, to find the cause; never patch the symptom so
the output matches. **The plan is wrong** (a step contradicts the design, an interface does not match
what an earlier task produced, a command that cannot work): rule on the smallest change that
satisfies the design, record the ruling, and carry it into later tasks that touch the same interface.

## Review after every task

Every task gets a review, and the review is a gate: never skip it, and never accept a review that
lacks either verdict. Spec compliance **and** quality are both required. The worker's own
self-review never replaces it.

Dispatch the reviewer (`apm:reviewer` role) with
[references/reviewer-brief.md](references/reviewer-brief.md) and four things:

- **the brief** the worker built from;
- **the worker's report**;
- **the review package:** one file holding the commit list, the change summary, and the full diff
  with ten lines of context, for BASE..HEAD. Before writing it, check that BASE is an ancestor of
  HEAD and that the range holds at least one commit: a range from the wrong branch, or an empty one,
  silently produces a package that reviews nothing. Never dispatch a reviewer without one;
- **the binding constraints**, copied verbatim from the plan's Global Constraints and the design:
  exact values, formats, and stated relationships between parts. This is the reviewer's lens; the
  brief already carries the review method.

Do not add open-ended directives ("check all uses") without a concrete, task-specific reason. Do not
ask the reviewer to re-run tests you already ran on the same code: your run is the evidence. **Do not
pre-judge findings:** never tell a reviewer not to flag something. If the prompt you are writing
contains "do not flag", "don't treat X as a defect", "at most minor" or "the plan chose", stop: you
are trying to spare yourself a fix round.

Items the reviewer marks **cannot verify from the diff** (a requirement that lives in unchanged code
or spans tasks) do not block the rest of the review, but you resolve each one yourself before the
task is done: you hold the plan and the cross-task context. A real gap is a failed spec review.

**The fix loop** starts when the review finds a spec gap, any must-fix finding, or a
cannot-verify item you confirmed as real. Two routes leave it at once:

- **Suggestions** (minor findings) are recorded as deferred on the task
  (`minor (deferred): <one line>`) and listed for the final review, which decides which must be
  fixed before merge. A roll-up nobody reads is a silent discard. Suggestions never enter the loop.
- **A finding that conflicts with the plan's text** (the reviewer flags something the plan mandates)
  is yours to rule on, with the design as the authority. Do not dismiss it because the plan says so,
  and do not dispatch a fix that contradicts the plan without a recorded ruling. If the ruling would
  change what the user approved, ask them.

Everything else enters the loop. **A fix round is one fix dispatch and one scoped re-review.** Each
round re-dispatches the worker, so it is marked `running` again, which counts an attempt:

- **The first two rounds** go to the same worker: resume it with the open findings, verbatim. If it
  cannot be resumed, dispatch a fresh one on the same model with the brief, its report and the
  findings.
- **After two failed rounds**, one round goes to a fresh worker **one tier stronger**
  (haiku, then sonnet, then opus), told: "A prior worker attempted this task N times; you own it now.
  Read its report for what was tried." A loop that survives two rounds usually means the worker
  cannot see its own problem; fresh eyes and more capability, in one move.
- **If the stronger worker also leaves must-fix findings open**, stop dispatching and bring it to
  the user (below). Count rounds from the task's `attempts` in the ledger, not from memory.

Every round: the worker fixes, re-runs the tests covering what it changed, and reports what it
changed, the covering tests, the command and the output. Confirm all three are there before you
dispatch the re-review, and name the covering test files in the fix message; a one-line fix does not
need a whole-suite run from the worker (you run the suite yourself when you verify). After each
round, record it on the task: `fix round R (X addressed, Y open: <one line each>; commits a..b)`.

**When the loop stops,** decide each open finding, and record each decision; a silent discard is
forbidden. Decide only at the stop: deciding earlier to end a loop is pre-judging under another
name.

- **The reviewer is wrong, or the point is contestable:** record a ruling saying why the code stands.
  The final review sees both sides, and the user sees the ruling.
- **Real, but nothing later builds on it:** record it as a deferred finding. The merge gate requires
  a final review with no unresolved findings, so it is fixed or decided by the user before merge.
- **Real, and load-bearing** (a later task builds on it, or it reveals a plan defect): bring it to
  the user before the next task builds on it.

**The final review.** When every task is done, the whole branch gets one review, on the most capable
model: a package from the merge base with `main` to HEAD, the plan and design paths, the plan's Review
Focus verbatim (the reviewer checks each line deliberately), and pointers to the recorded rulings and
deferred findings so it can weigh them. Use `apm:code-review` (and `apm:branch-review` for a scored
review). Its severity labels are advice; the gate is yours. Re-grade each finding by its effect, by
what a reasonable person using the software gets if it ships, not by whether the design happened to
name the input that triggers it. Suggestions are recorded as deferred and listed for the user; they
are never turned into rulings, because a ruling decides a conflict, not a declined polish. If it
returns must-fix findings, dispatch **one** fix worker with the complete list (not one worker per
finding; one real fix wave run that way cost more than all its tasks together). Each fix starts with
a test that reproduces the finding and is seen failing; a fix without one is not verified. Then one
scoped re-review of the fix. There is no second wave: residual findings go to the user, because
criterion 3 of the merge gate is a final review with nothing unresolved. Then finish with
`apm:finishing-a-branch`.

## Re-review after fixes

A re-review is not a fresh review: the full review already happened. It checks that each finding was
addressed and that the fix broke nothing.

- Package the fix range: FIX_BASE..HEAD, where FIX_BASE is the head the previous review saw.
- Dispatch the reviewer with [references/re-review-brief.md](references/re-review-brief.md), the
  findings verbatim, the brief, the worker's report and the package.
- It gives each finding a verdict, **addressed** or **not addressed**, with the line that shows it.
  "Attempted" is not addressed: the specific defect must no longer exist.
- It checks the fix diff, and only the fix diff, for new breakage. New must-fix breakage joins the
  open findings.
- What it notices outside the fix diff is recorded as a deferred observation. It never extends the
  loop.

## Recording each task

You own all state. Record **after every task**, not at the end, so a crash or a reset loses at most
the task that was running, and the record shows which one it was.

- Before every dispatch: `<CLI> task N ID --status running --worker <role> --model <model>`. It adds
  one to the task's `attempts`, which is what the retry rule counts.
- After your verification: `<CLI> task N ID --status done --evidence "<command and result>"`, or
  `--status failed` with the failing output. The evidence is the output of commands **you** ran.
- Rulings and deferred findings go on the task they belong to, as `--evidence` lines, in the same
  step as the rest of the task's record. Bookkeeping rides along with the work; it never waits for a
  convenient moment.
- The issue moves to `integrating` when the last task is done (`<CLI> issue N --status integrating`).
- Never edit state or the ledger by hand. Workers never run state-changing commands; the guard denies
  them, and you record what they report.
- Nothing is deleted at the end. State lives on the state branch; scratch briefs and review packages
  stay where they are, and the guard blocks a recursive delete anyway.

When the work is merged, your report to the user lists **every ruling you made**, in order, each
with what it costs if wrong, and every deferred finding. It is exhaustive: if the record holds a
ruling, the report holds it. That list is the only place the decisions you took on the user's behalf
reach them, so they can rework whatever you got wrong.

## When to stop and ask

Stop, and ask the user, for these and only these:

1. **A destructive or irreversible action, or a protected-path write, that the approved plan did not
   name.** The guard denies it; a denial is a stop. Ask in chat for that exact action, and only after
   an explicit yes record `<CLI> approve` and retry once.
2. **A security-sensitive action.**
3. **A side effect outside the project the plan did not name** (publishing, pushing to a shared
   branch other than the issue's own). Merging the issue's pull request is not one: the approved plan
   authorizes it, through the merge gate.
4. **A decision only the user can make** that the plan did not settle: anything that changes what
   gets built, drops or loosens a structural criterion, raises a limit or accepts a worse debt
   number, or needs a design change.
5. **A worker that failed after its stronger-model retry**, or a load-bearing finding still open.
6. **A merge-gate criterion that cannot be met.**
7. **A plan so broken that every path forward is a guess.**

**How to ask.** One clear question, recorded with `<CLI> question N --text TEXT --blocks ID` (one
`--blocks` per task it blocks), so it survives a reset. Then wait: no pings. While you wait, keep
working on anything the question does not block, and park only the blocked work. Record the answer
with `<CLI> resolve N INDEX --answer TEXT`.

Everything else, decide: rule, record, continue. A wrong ruling costs rework the user can see and
undo; a session parked on a routine question costs their whole day and buys nothing. If no worker
can be dispatched at all, stop and tell the user: the manager does not build the plan itself.

## Rationalizations

| Excuse | Reality |
|--------|---------|
| "Close enough on spec compliance." | A spec gap means not done. Fix it, or stop and ask. |
| "I'll fix it myself; dispatching is overhead." | Your fixes skip review and fill your context. Send it back. |
| "One more round will converge." | Past the retry rule, rounds do not converge; the failure is structural. Stop and ask. |
| "The reviewer will just find something new anyway." | A scoped re-review verifies fixes and cannot wander. New findings outside the fix are recorded, not looped. |
| "This finding is obviously wrong; I'll drop it." | You decide only at the stop, and every decision is recorded. Silent discards are forbidden. |
| "The fix was small; skip the re-review." | Unreviewed fixes are how regressions land. Every round ends with a re-review. |
| "Reviews slow the loop down." | Without reviews the loop is unverified churn. |
| "Recording is overhead; I'll catch up after a few tasks." | The record is what survives a reset. Record every task as it finishes. |
| "I remember what Task N says." | You remember a summary. The brief has the exact values. |
| "The worker said the tests pass." | A claim is not evidence. Run them. |
| "Tests should pass; the change was trivial." | "Should" is not evidence. Run the command and read the output. |
| "The plan is wrong here; I'll just do the right thing." | Do it, and record the ruling, or ask if it changes what was approved. |
| "Let me check in before the next task." | They approved the plan so you would not. Only the listed stops stop you. |
| "The reviewer said minor, so it's minor." | Grade by what a person using it gets if it ships, not by whether the design mentioned the input. |
| "I'll fix the minors too while I'm in there." | Minors are recorded; the final review decides. Unasked work is unreviewed scope. |
| "The worker spawned its own reviewer; extra assurance." | Workers cannot dispatch workers. If one tried, that is a defect to report, not rigor. |
| "I read the diff carefully; the final review is redundant." | Same reader, same blind spots. The final review is the one fresh look at the whole branch. |
| "Workers are slow and expensive; skip the final review." | One whole-branch review is the floor, not the ceiling. |
| "The fix is obvious; it doesn't need a failing test first." | The failing test is the only proof the finding was real and is now gone. |
| "The new test passed straight away, so the task is done." | A test that never failed proves nothing. It goes back to the worker. |

## An example

```
[brief: no tasks done for issue #42; read plan docs/plans/2026-03-02-resume.md and its design]
[pre-flight: 2 shared-interface rows, 4 self-consistency rows; one finding:
 Task 2 consumes save_point, Task 1 produces savePoint]
[Ruling: use savePoint, as Task 1 produces it; cost if wrong: one rename. Recorded on Task 2.]

Task 1: the save-point store
[BASE a1b2c3d; task 42 1 --status running --worker implementer --model sonnet]
[dispatch: brief, files owned, report contract]
worker: done. RED: test_saves_and_loads failed (no such function); GREEN: 6/6 pass.
[manager: suite in the worktree, 214 pass; merge into the branch; suite again, 214 pass]
[reviewer: spec compliant; quality approved]
[task 42 1 --status done --evidence "suite 214 passed, on the branch after merge"]

Task 2: resuming from a save point
[BASE d4e5f6a; running; dispatch, carrying the savePoint ruling]
worker: done. 9/9 pass.
[manager: suite green in the worktree and on the branch]
[reviewer: spec gap, the "resume within one second" limit is not tested; must-fix: a magic number]
[fix round 1: resume the same worker with both findings]
worker: limit test added and failing first, then passing; constant extracted; covering tests 11/11.
[re-review: both addressed, no new breakage]
[record: fix round 1 (2 addressed, 0 open; commits d4e5f6a..b7c8d9e); done, with the suite output]

[all tasks done: final review on the most capable model, Review Focus verbatim, rulings listed]
final reviewer: no must-fix findings; one suggestion, deferred.
[issue 42 --status integrating; apm:finishing-a-branch]

Report to the user: what shipped, the pull request, rulings made (savePoint; cost: one rename),
deferred: the suggestion.
```

## References

- [references/implementer-brief.md](references/implementer-brief.md): the dispatch for the worker
  that builds a task, and what it returns.
- [references/reviewer-brief.md](references/reviewer-brief.md): the task review, with its two
  verdicts and severity calibration.
- [references/re-review-brief.md](references/re-review-brief.md): the scoped re-review after a fix
  round.

## Common mistakes

- **Re-dispatching finished tasks** after a reset because you trusted memory over the ledger.
- **A review range cut from the previous commit** instead of the recorded BASE.
- **Pasting the session's history** into a dispatch, or the whole plan.
- **Omitting the model**, so a worker silently runs on the most expensive one.
- **Recording a worker's claim as evidence** instead of the output of a command you ran.
- **Skipping the second verification** on the feature branch after merging a worktree.
- **Moving to the next task** with must-fix findings open.
- **Pre-judging a finding** in the reviewer's brief.
- **Fixing findings yourself** in the manager's session.
- **Parking a load-bearing finding** so later tasks build on it.
- **Asking the user about routine work**, or **stalling all work** on one open question.
- **Rulings that never reach the user** because they were not recorded.
