---
name: merge-gate
description: "Use when an issue's tasks are all built and reviewed and the manager is about to open a pull request or merge, when the gate fails or a check reports stale, or when anyone is tempted to merge on the strength of an earlier test run, a clean-looking review or a criterion that seems not to matter this time."
---

# The merge gate

Four criteria stand between a branch and the base. The manager checks each one itself, with commands
it ran on the tree that will land. A pass reported by anyone else, or earned on an earlier tree, is
a claim.

## When this applies

- Every task is done and the final whole-branch review has been dispatched.
- The issue is `integrating` and a pull request is the next step.
- A gate run failed, or a review is older than the latest commit.

The manager runs the gate. Workers never do: `<CLI> gate` is denied to them, and the full suite it
runs is the one full-suite run of the issue (`apm:running-an-issue`, "Pacing").

## The core rule

**All four criteria hold, checked by the manager itself, or it does not merge. It never merges
partway, and it never drops a criterion silently.**

Breaking the letter of this rule is breaking its spirit. "Three of four, and the fourth is
paperwork," "the review was clean before the last fix," and "CI will catch it" are each a merge
without the gate.

## Running the gate

From the feature branch, with the base merged in: `<CLI> gate N` (add `--base REF` for a base other
than `workflow.base`). It prints one line per check, `PASS` or `FAIL`, with the criterion, the name
and the detail, then `merge gate: passed` or `merge gate: N failed; stop and ask`.

- A pass means all four criteria hold. The gate checks them in order, and reports every failure, not
  only the first.
- Exit 0: every check passed. Exit 1: a check failed. Exit 2: the gate could not run, because the
  profile declares no test command or the issue has no plan recorded.
- The gate records nothing. Copy its output into the task's evidence (`apm:verification`) and into the
  pull request.
- The command logs are under `.apm/tmp/gate/`. A failure shows the last lines of its log; open the
  log for the rest.
- A failure goes to a worker as a fix, then the gate runs again on the new tree. Fixing and
  rerunning only the failed check is not a pass: the whole gate runs again.

## Criterion 1: everything passes

The base is merged in, the tree is clean, no file sits in two layers, and the build, the full test
suite and every checker the profile declares pass.

- If the tree is dirty or the base is not merged, the commands are reported `not run` and fail:
  commit the work that belongs, merge the base (`apm:finishing-a-branch`), then run again.
- A timeout (`workflow.gate_timeout`) is a failure, not a flake. "Probably flaky" is not a diagnosis;
  send it to a debugger (`apm:systematic-debugging`).
- A test command must be declared under `workflow.commands.test`. If none is, the gate cannot run.
  Ask the user for it and record it in the profile; do not substitute one.

## Criterion 2: no debt got worse

`<CLI> debt check` against the base passes: no function, file, wide type or smell count is worse than
the baseline, and the baseline itself was not loosened.

- A failed debt check is a stop (`apm:refactoring`). Extract; do not raise a limit.
- `--accept` on a baseline is used only after the user approves that specific worsening in chat.
- If debt was paid down, tighten the baseline with `<CLI> debt baseline` as a tracked commit, and
  commit it before the final review is recorded: a commit after the review makes criterion 3 stale.

## Criterion 3: the final review is clean

A whole-branch review was recorded, it was recorded at the commit being merged, and it has no open
findings.

1. Dispatch `apm:reviewer` for the whole branch with `apm:code-review`. It reports each structural
   criterion as met or unmet, and the count of open findings.
2. Fix every finding through a worker, not yourself, and re-review the fixes.
3. Record it: `<CLI> review N --open COUNT [--criteria-met] --evidence TEXT`. It stores the current
   `HEAD`, so the review is tied to that tree.
4. **A commit after the review makes it stale,** and the gate fails this criterion. Review again, or
   record a new review of the new `HEAD`; a changed branch is a new branch. A deferred finding the
   user has not decided counts as open.

## Criterion 4: the structure the plan promised

Every structural acceptance criterion in the approved plan is met, and every document the plan
promised exists.

- The gate reads the plan's `## Structural acceptance criteria`, checks that the plan file exists, and
  checks each backticked document path the criteria name. The review records `--criteria-met` only
  when the reviewer walked every criterion with evidence.
- A promised document that does not exist is a failure. Write it as a tracked commit, then review the
  branch again, since a commit makes the review stale.
- If a criterion is wrong, that is a change to the plan, and a plan changes only with the user's
  approval.

## When a criterion cannot be met

Stop and ask the user. Do not merge, and do not drop or weaken the criterion to get past it.

- Say which criterion failed, what you tried, and what the options are, each with its cost.
- Record the question with `<CLI> question`, and keep working on anything it does not block.
- The decision is the user's. If they accept a gap, record it as a ruling in the pull request with
  what it costs if wrong; the criterion is not removed from the plan or from the gate.
- A debt worsening is accepted only in chat, by the user, with their reason.

## Rationalizations

| Excuse | Reality |
|--------|---------|
| "The tests passed before the last commit." | They ran on a different tree. Run the gate again. |
| "The review was clean; the last fix was tiny." | A commit after the review makes it stale. |
| "Three criteria hold; the doc is paperwork." | A missing promised document fails criterion 4. |
| "The checker is slow; skip it this once." | A skipped checker is a dropped criterion. |
| "Fix the one failing check and merge." | The whole gate runs again on the new tree. |
| "CI will catch anything I missed." | CI is not a gate. The local gate is. |

## Common mistakes

- **Merging on a worker's report** of a pass instead of a gate the manager ran.
- **Running the gate on a dirty tree** or before the base is merged in.
- **Recording the review and then committing**, so criterion 3 is stale.
- **Fixing findings in the manager's own session**, which skips the review of the fix.
- **Rerunning only the failed check.**
- **Raising a limit or editing the baseline** to turn criterion 2 green.
- **Dropping a criterion** because it was inconvenient, instead of asking.
- **Declaring a test command on the spot** to let the gate run, without the user knowing.
