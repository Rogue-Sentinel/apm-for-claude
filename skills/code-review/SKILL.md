---
name: code-review
description: "Use when a task or a feature is finished and needs review, before a branch merges, when you are stuck and want a fresh look, before a large refactoring, after a complex bug fix, or when review findings come back and have to be weighed, answered or acted on."
---

# Code review

The manager requests one whole-branch review before every merge, plus a per-task review in the
three cases below, and briefs the reviewer with exactly what it needs. Findings that come back are checked against the code before anyone
agrees with them, acted on one at a time, and answered with facts, not with gratitude.

## When this applies

**A review is required:**
- once, on the whole branch, when every task is done and before it merges to `main`. This is the
  default, and the final review is criterion 3 of the merge gate;
- after a single task, before the next one starts, only when the user asked for per-task review,
  when the profile says `"review": "per-task"`, or when the task touches a path in the profile's
  `workflow.safety_critical`. Otherwise a task's diff is reviewed with the rest of the branch.

The review reads the diff and the manager's evidence; it does not rerun the suite. The full suite
runs once, through `<CLI> gate`, after the final review's fixes and right before the pull request.

**A review is worth asking for:**
- when a worker or the manager is stuck and wants a fresh look;
- before a large refactoring, to have a baseline;
- after a complex bug fix.

**Receiving applies** whenever findings come back: from a reviewer worker, from the user (through
the manager), or from a reviewer on a pull request. It applies to the manager weighing a review, and
to the worker who is sent findings to fix.

## The core rule

**Review early, review often, and verify before you agree.** A reviewer is given crafted context,
never the requesting session's history. A finding is checked against the codebase before it is
implemented. Technical correctness comes before social comfort: no performative agreement, no blind
implementation, and no silent dismissal. A finding someone disagrees with is never dropped: **the
manager decides it, or asks the user.**

## Requesting a review

The manager requests it; a worker never dispatches a reviewer (workers cannot spawn agents).

1. **Fix the range.** The base is where the work started and the head is where it ends:

   ```
   BASE = git merge-base <base-branch> HEAD     -- or the commit before the task, for one task
   HEAD = git rev-parse HEAD
   ```
2. **Dispatch** `apm:reviewer` with the profile's model for that role (default opus), filling the
   brief in [references/reviewer-checklist.md](references/reviewer-checklist.md). Record the
   dispatch in the ledger as for any worker: `<CLI> task N ID --status running --worker reviewer
   --model opus`. `<CLI>` is the framework's command line, as the manager's prompt defines it.
3. **Act on the findings** (see "Receiving a review"). There are two tiers:
   - **Must fix**: every finding that blocks the next task or a merge. The reviewer's note on each
     says why (a security hole, a risk of data loss, broken behavior, a failed debt check, a broken
     limit, missing planned work), and the most severe go first. They enter the fix loop.
   - **Suggestion**: recorded as deferred, in the plan file's `## Deferred findings` section
     (`Task N: <one line>`), and listed for the final review, which decides which must be fixed
     before merge. A suggestion never enters the fix loop, and is never silently discarded.
   - **Wrong**: push back with technical reasoning (see "Pushing back").
4. **Re-review after fixes, and the limit on fix rounds,** follow `apm:executing-plans`: a fix
   round is one fix dispatch and one **scoped** re-review of the fix (its re-review brief, not this
   full brief again). The first try and one fix round run on the same model; after two failures,
   one round goes one tier stronger; if that also fails, every open must-fix finding goes to the
   user. A merge waits until the final review has no unresolved findings.

Example:

```
[Task 2 is done: a verify and a repair function, four kinds of issue]

manager:   BASE = the commit before task 2, HEAD = the task branch tip
           dispatch apm:reviewer
             WHAT WAS BUILT:  verifyIndex() and repairIndex(), four issue types
             REQUIREMENTS:    task 2 of the approved plan, with its acceptance criteria
             BASE, HEAD:      a7981ec, 3df7661
reviewer:  strengths: clean separation, tests exercise the real index
           must fix: no progress output on a long repair
           suggestion: the reporting interval 100 is a bare number
           ready to merge: with fixes
manager:   routes the must-fix finding to an implementer, verifies the fix itself,
           records the suggestion as deferred, runs a scoped re-review, then starts task 3
```

## What the reviewer is given

**Crafted context, never your session's history.** The reviewer judges the work product, not the
reasoning that produced it, and its context stays free for the diff. Reviewing the diff yourself
instead of dispatching a reviewer burns the manager's context, which it needs to keep driving the
work; only the findings should come back.

The brief carries:
- **What was built**: a short description.
- **What it should do**: the task text from the approved plan, its structural acceptance criteria,
  and any promised documents or decision records.
- **The range**: the base and head commits, and the base branch.
- **The project facts** the review needs: the profile's limits, layer map, checkers, declared
  overrides and protected paths, and whether the project has a user interface.
- **The verification the manager ran**, with its output, so the reviewer knows what was proven.
- **What the reviewer may not do**: change files, move the checkout, create or remove worktrees,
  or dispatch anyone. A reviewer who needs another revision reads it with `git show` and
  `git diff`, or asks the manager for a checkout.

The full brief, what to check, the calibration rules, the output format and an example are in
[references/reviewer-checklist.md](references/reviewer-checklist.md). For a scored review of a whole
branch, the reviewer also uses `apm:branch-review`; for smells, `apm:code-smells`; for dependency
direction, `apm:clean-architecture`, with `<CLI> debt check` output as evidence.

## Receiving a review

```
when findings come back:
    1. READ        all of it, without reacting
    2. UNDERSTAND  restate each item in your own words, or ask about it
    3. VERIFY      check it against the code as it is
    4. EVALUATE    is it technically right for THIS codebase?
    5. RESPOND     a technical acknowledgment, or reasoned pushback
    6. IMPLEMENT   one item at a time, testing each
```

**Unclear items stop everything.** If any item is unclear, implement nothing yet and ask about the
unclear ones first: items are often related, and a partial understanding gives a wrong fix.

```
the findings say: fix items 1 to 6
you understand 1, 2, 3 and 6; you are unsure about 4 and 5

WRONG  fix 1, 2, 3 and 6 now, and ask about 4 and 5 later
RIGHT  "I understand 1, 2, 3 and 6. I need 4 and 5 clarified before I start."
```

A worker asks in its report (status: needs decision); the manager answers it, asks the reviewer,
or asks the user.

**By source:**
- **From the user**, relayed by the manager: trusted. Implement once you understand it, still ask
  if the scope is unclear, and skip straight to the work.
- **From a reviewer**, a worker or a pull-request reviewer: be skeptical, but check carefully. Run
  "Verify before you agree" on every item.
- **A finding that contradicts a decision the user already made**, or the approved plan: stop. It
  goes to the manager, and the manager takes it to the user. Neither the reviewer nor the worker
  overrides the user.

**Order of work** for several findings: clarify everything unclear first; then the blocking issues
(breakage, security), then the simple fixes (typos, imports), then the complex ones (refactoring,
logic). Test each fix on its own, and check for regressions (`apm:verification`). A refactoring
finding is its own commit, separate from behavior (`apm:refactoring`).

**On a pull request**, the manager replies to an inline comment in that comment's thread, not as a
new top-level comment on the pull request. Each code host has its own call for a thread reply; on
one host's API, for example, it is a reply posted to the review comment itself:

```
gh api repos/<owner>/<repository>/pulls/<pull-request>/comments/<comment-id>/replies -f body="<reply>"
```

## Verify before you agree

Before implementing a finding, check:

1. Is it technically correct for **this** codebase?
2. Would it break existing behavior? Run the tests that cover it.
3. Is there a reason for the current implementation? Read the history (`git log -p`, `git blame`)
   and any decision record.
4. Does it work on every platform and version the project supports?
5. Did the reviewer have the full context?

**The YAGNI check.** When a finding asks to "implement it properly" (a full feature, a general
mechanism, a professional-grade version), search the codebase for real use first:

```
if nothing uses it:  "Nothing calls this endpoint. Remove it instead (YAGNI)?"
if it is used:       implement it properly
```

```
reviewer:  "Implement proper metrics tracking: a store, date filters, and a spreadsheet export"
RIGHT      "Searched the codebase: nothing calls the metrics endpoint. Remove it (YAGNI)? Or is
            there a use I'm missing?"
```

You and the reviewer both serve the user's plan. A feature nobody needs is not added because a
review asked for it.

**When you cannot verify it**, say so: "I can't verify this without X. Should I investigate, ask,
or go ahead?" Never go ahead on an item you could not check without saying that you could not.

```
reviewer:  "Remove the legacy code path"
WRONG      "Agreed, removing it now."
RIGHT      "Checked: the supported minimum version still needs this path, and the newer API
            only exists from version 13. The path has a wrong identifier, though. Fix the
            identifier, or drop support below 13? That is a decision for the manager."
```

## Pushing back

Push back when a finding:
- breaks existing behavior;
- comes from a reviewer without the full context;
- adds something nothing uses (YAGNI);
- is technically wrong for this stack;
- ignores a legacy or compatibility reason;
- conflicts with the architecture or a decision the user made.

**How:** with technical reasoning, not defensiveness. Ask specific questions. Point at the working
tests or code that show the current behavior is right. If you are uneasy pushing back, say that
plainly in your report, and then state the problem anyway; candor helps the manager more than
silence.

**Who decides.** The worker and the reviewer do not settle a disagreement between themselves. A
worker that disagrees reports the finding, its reasoning and its evidence to the manager. A
pull-request reviewer's finding is weighed the same way. Then **the manager decides** when the
answer is technical and within the approved plan, and **asks the user** when it touches a design
decision, the plan, or a tradeoff only the user can make. The decision is recorded, and the review
is resolved only when every finding is fixed or explicitly decided. A finding is never dropped
silently.

**When your pushback was wrong**, correct it plainly and move on:

```
RIGHT  "You were right: I checked X and it does Y. Fixing it now."
RIGHT  "Verified; you're correct. I misread the call order. Fixing."
WRONG  a long apology, a defense of why you pushed back, or an over-explanation
```

## No performative agreement

**Never:**
- "You're absolutely right!"
- "Great point!", "Excellent feedback!"
- "Thanks for catching that!", or thanks for anything
- "Let me implement that now", before you have verified it

**Instead:** restate the technical requirement, ask a clarifying question, push back with
reasoning, or simply do the work. Actions speak; the code shows the finding was heard.

When a finding is correct:

```
RIGHT  "Fixed. The date is now validated as an ISO date before the search runs."
RIGHT  "Good catch: the empty list was indexed. Fixed in search.ext, with a test."
RIGHT  the fix itself, shown in the diff and the report
WRONG  "You're absolutely right!", "Great point!", "Thanks for catching that!"
```

If you are about to write "thanks", delete it and state the fix instead.

## Red flags

- Skipping the final whole-branch review because the change is "simple".
- Reviewing every task on its own, when none of the three triggers fired.
- Ignoring a must-fix finding, however it was labeled.
- Starting the next task, or merging, with a must-fix finding unfixed.
- A suggestion neither fixed nor recorded as deferred.
- Arguing with valid technical feedback.
- Implementing a finding you have not verified.
- Implementing the clear items and leaving the unclear ones for later.
- A finding dismissed without a stated reason.
- A worker, or a reviewer, settling a disagreement without the manager.
- Gratitude or praise in place of a fix.

## Rationalizations

| Excuse | Reality |
|--------|---------|
| "I'll just review the diff myself instead of dispatching a reviewer." | The manager's context is for driving the work. The diff and its evaluation belong in the reviewer's context; only the findings come back. |
| "The reviewer needs my whole session to understand the change." | Give it crafted context, never the session. That keeps it on the work product, not your thought process. |
| "It's a small change; it doesn't need a review." | Small changes break things too, and the merge gate requires the final review. A small change gets no review of its own only because the whole branch gets one. |
| "The reviewer is the expert; I'll just do what it says." | A reviewer can lack context. Verify every item first. |
| "Pushing back looks uncooperative." | Technical correctness beats comfort. Unvoiced disagreement becomes a bug. |
| "We disagree, so I'll leave that finding out." | Nothing is dropped silently. The manager decides it, or asks the user. |

## References

- [references/reviewer-checklist.md](references/reviewer-checklist.md): the reviewer's brief with
  its placeholders, what to check, calibration, the output format, and an example.

## Common mistakes

| Mistake | Fix |
|---------|-----|
| Performative agreement | State the requirement, or just act. |
| Blind implementation | Verify against the codebase first. |
| Fixing a batch, then testing once | One at a time, and test each. |
| Assuming the reviewer is right | Check whether it breaks things. |
| Avoiding pushback | Technical correctness over comfort. |
| Partial implementation | Clarify every item first. |
| Unverifiable, done anyway | State the limit, and ask for direction. |
| A disagreement settled without the manager | Report it; the manager decides, or asks the user. |
