---
name: verification
description: "Use when you are about to say that work is done, fixed, passing, clean or ready, before you commit, push, open a pull request, report to the manager, mark a task done, move to the next task, or tell the user how things stand."
---

# Verification

Evidence before claims, always. Run the command that proves the claim, read what it printed, and
only then say what it shows. If something is red, it is red.

## When this applies

**Always, before:**
- any claim that work is complete, fixed, passing, clean or correct, in any wording;
- any expression of satisfaction about the state of the work;
- committing, pushing, opening a pull request, or merging;
- a worker's report to the manager;
- the manager marking a task done, recording evidence, or merging a worker's branch;
- moving on to the next task;
- delegating, or accepting what a delegated worker says it did;
- the manager telling the user what shipped, what passed, or where things stand.

The rule covers exact phrases, paraphrases and synonyms, and anything that implies success.

## The core rule

```
NO CLAIM OF COMPLETION WITHOUT FRESH VERIFICATION EVIDENCE
```

If you have not run the verification command since your last change, you cannot claim it passes.
**Breaking the letter of this rule is breaking its spirit.**

## Evidence before claims

Before claiming any status, or sounding pleased about it, pass this gate:

```
1. IDENTIFY  which command proves this claim?
2. RUN       the whole command, fresh, after the last change
3. READ      all of its output: the exit status, and the count of failures and errors
4. CHECK     does the output confirm the claim?
                 no  -> state the actual status, with the evidence
                 yes -> state the claim, with the evidence
5. ONLY THEN make the claim
```

Skipping any step is not a shortcut. It is reporting something you do not know.

**Fresh** means after your last edit, in the place the claim is about: your worktree for a worker,
the worker's worktree and then the feature branch for the manager. An earlier run, a run before
the last edit, or a run in a different checkout is not evidence for this one.

**The manager trusts only the commands it runs itself.** A worker reporting that the build passed,
the tests are green or a lint is clean is a claim, not evidence. The manager runs the verification
itself, reads the output, and records that output as the task's evidence. A worker reports the
commands it ran with their real output, so the manager knows what to re-run and what to expect.

## What counts as evidence

| Claim | Requires | Not enough |
|-------|----------|------------|
| Tests pass | the project's whole test command, run fresh: zero failures | an earlier run, one test file, "should pass" |
| A checker is clean | the checker's output: zero errors | a partial check, an extrapolation |
| The build succeeds | the build command: exit status 0 | a clean lint, logs that "look good" |
| A bug is fixed | the original symptom, re-tested: it passes | the code changed, so it is assumed fixed |
| A regression test works | the full cycle: red without the fix, green with it | a test that passed once |
| Debt did not grow | `apm debt check` against the base: exit 0 | `apm metrics` read by eye |
| A worker finished | the diff in its worktree shows the changes, and the manager's own run passes | the worker's report says "success" |
| Requirements are met | each item of the plan's task and acceptance criteria, checked one by one | the tests pass |
| A promised document exists | the file, opened and read | a commit message that says it was added |

The key patterns:

```
TESTS        run the project's test command; see "34 passed, 0 failed"; then say "all 34 tests pass"
             never "should pass now" or "looks correct"

REGRESSION   write the test; run it (it passes with the fix); revert the fix; run it (it MUST fail);
             restore the fix; run it (it passes)
             never "I've written a regression test" without that red-green check

BUILD        run the build; see exit 0; then say "the build passes"
             never "the linter passed", because a linter does not compile anything

REQUIREMENTS re-read the plan's task; make a checklist of every item and structural criterion;
             check each one; report the gaps, or that each item was met, with evidence
             never "tests pass, so the task is complete"

DELEGATION   a worker reports success; read its diff; run the verification yourself; report what
             you saw
             never record a worker's report as the evidence
```

## Honest reporting

**Report results honestly. If something is red, it is red.**

- **Red is reported as red**, by name: the failing test, the error, the exit status. Never round
  "mostly passing" up to passing, and never leave a failure out because it seems unrelated.
- **Failures you did not cause are still reported.** A test that was already failing, a flaky one,
  a checker error in a file you never touched: name it, and say you did not cause it and how you
  know. A red test you saw scroll past and left out falsifies the report.
- **What you did not run, you say you did not run.** "Not verified: the device test needs hardware
  I do not have" is honest. Silence is not.
- **Uncertainty is stated as uncertainty.** "I am not sure the cache is invalidated on every path;
  I checked two of the three" is a finding the manager can act on.
- **A worker's status matches its evidence.** Done means the evidence shows it is done. Otherwise
  the status is blocked, or needs decision, with what stands in the way.
- **The manager tells the user what it verified** and what it only heard from a worker, and keeps
  the two apart. A weakened test, a skipped check, or a criterion that was not met is said out loud,
  never smoothed over.
- **Fixing the record beats defending it.** If you claimed something that turns out to be wrong, say
  so as soon as you know, with the new evidence.

## Red flags

Stop, and run the verification, if you notice any of these:

- Using "should", "probably", "seems to", "looks like" about the state of the work.
- Sounding satisfied before verifying: "Great!", "Perfect!", "Done!", "All set!".
- About to commit, push, open a pull request or merge with no fresh run behind it.
- Trusting a worker's report of success, or a report from any agent.
- Relying on a partial check: one file of the suite, one checker of several.
- Thinking "just this once".
- Being tired, and wanting the work to be over.
- A failure you are planning not to mention.
- **Any wording that implies success when you have not run the verification.**

## Rationalizations

| Excuse | Reality |
|--------|---------|
| "It should work now." | Run the verification. |
| "I'm confident." | Confidence is not evidence. |
| "Just this once." | No exceptions. |
| "The linter passed." | A linter is not a compiler, and not a test suite. |
| "The worker said it succeeded." | Verify it independently. A report is a claim. |
| "I'm tired." | Exhaustion is not an excuse. |
| "A partial check is enough." | A partial check proves nothing about the rest. |
| "I used different words, so the rule doesn't apply." | The spirit is the rule. Any implied success counts. |
| "That failure isn't mine." | Report it anyway, and say why you think it is not yours. |
| "It passed a minute ago." | Not since your last change. Run it again. |

## References

- `apm:test-first`: the red-green cycle that a regression check repeats, and the rule that the
  whole suite is what you verify.
- `apm:systematic-debugging`: what to do when the evidence says the fix did not work.

## Common mistakes

- **Running the one test you wrote** and reporting the suite green.
- **Reading the summary line only**, and missing the error printed above it.
- **Verifying in the wrong place**: your worktree passes, the merged branch fails.
- **A regression test never checked against the code without the fix.**
- **Reporting a worker's words as evidence.**
- **Leaving out a failure** because you did not cause it.
- **"Done" with an acceptance criterion never checked**, because the tests passed.
