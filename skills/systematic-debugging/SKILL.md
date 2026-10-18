---
name: systematic-debugging
description: "Use when a test fails, a build breaks, behavior is unexpected, a bug is reported or found mid-task, performance degrades, or a fix you already tried did not work, before you propose or make any fix."
---

# Systematic debugging

Find the root cause before you change anything. Prove it with a failing test. Fix the cause, then
fix whatever wrong instruction or project knowledge let the bug be written.

## When this applies

Any technical problem: a failing test, a bug in production, unexpected behavior, a performance
problem, a build failure, an integration that does not work.

Use it **especially** when:
- there is time pressure, because an emergency makes guessing tempting;
- "one quick fix" looks obvious;
- you have already tried a fix, or several, and they did not work;
- you do not fully understand the problem.

Do not skip it when the problem looks simple (simple bugs have root causes too), when you are in a
hurry (rushing guarantees rework), or when someone wants it fixed now (a systematic search is faster
than thrashing).

**Who does what.** A bug a worker finds mid-task belongs to the manager, which dispatches a debugger
(`apm:debugger`) to fix it properly, without stopping to ask the user. If you are an implementer and
the bug is outside your task, do not fix it: describe it under **found elsewhere** in your report.
The debugger runs this whole skill. The manager uses it to decide what to dispatch when its own
verification fails.

## The core rule

```
NO FIX WITHOUT A ROOT CAUSE INVESTIGATION FIRST
```

A symptom fix is a failure, even when the symptom goes away. Until you have finished the
investigation in "Root cause first", you may not propose a fix. **Breaking the letter of this rule
is breaking its spirit.**

The four phases run in order, and each one is finished before the next starts:

| Phase | What you do | Done when |
|-------|-------------|-----------|
| 1. Root cause | read the errors, reproduce, check what changed, gather evidence at each boundary, trace the data | you can say what fails and why |
| 2. Pattern | find working code like it, compare it line by line | you have listed the differences |
| 3. Hypothesis | state one theory, test it with the smallest change | it is confirmed, or replaced by a new one |
| 4. Fix | a failing test, one fix, verification, then the instruction behind the bug | the bug is gone, every test passes, the cause cannot recur |

## Root cause first

**Phase 1: investigate.** Before attempting any fix:

1. **Read the error messages carefully.** Do not skim past errors or warnings; they often contain
   the exact answer. Read the whole stack trace. Note the line numbers, file paths and error codes.
2. **Reproduce it consistently.** Can you trigger it reliably? What are the exact steps? Does it
   happen every time? If it does not reproduce, gather more data. Do not guess.
3. **Check what changed.** What changed that could cause this? Read `git diff` and the recent
   commits. Look at new dependencies, configuration changes and differences in the environment.
4. **Gather evidence at every boundary** when the system has several components (a pipeline that
   builds and then signs, a service in front of a store, a hook in front of a command). Before
   proposing any fix, add instrumentation:

   ```
   for each component boundary:
       log what data enters the component
       log what data leaves it
       check that environment and configuration reach it
       check the state at that layer

   run once, to see WHERE it breaks
   then read the evidence to find the failing component
   then investigate that component
   ```

   For example, in a four-stage pipeline, print at each stage whether the credential it needs is
   set (print SET or UNSET, never the value), then what the next stage sees in its environment,
   then the state of the store the signing step reads, then run the failing step verbosely. The
   output shows which hand-off loses it: "present in stage 1, missing in stage 2".
5. **Trace the data flow** when the error is deep in a call stack. Where does the bad value come
   from? What called this with it? Keep going up until you find the source, and fix it there (see
   "Trace backward to the source").

**Phase 2: find the pattern.**

1. **Find working examples.** Locate similar code in the same codebase that works.
2. **Compare against the reference.** If you are implementing a known pattern, read the reference
   implementation **completely**, every line, before applying it. Skimming is not reading.
3. **List every difference** between the working and the broken code, however small. Do not decide
   in advance that something "can't matter".
4. **Understand the dependencies.** What other components, settings, configuration and environment
   does this need? What does it assume?

**Phase 3: one hypothesis at a time.** Work like a scientist.

1. **Form a single hypothesis** and write it down: "I think X is the root cause because Y". Be
   specific, not vague.
2. **Test it with the smallest possible change**, one variable at a time. Never fix several things
   at once.
3. **Check before you go on.** Confirmed: go to phase 4. Not confirmed: form a **new** hypothesis.
   Never pile another fix on top of one that failed.
4. **When you do not know, say so.** "I do not understand X" is a finding. Do not pretend. Research
   more, or ask: a worker asks the manager in its report, and the manager decides or asks the user.

## Reproduce it as a failing test

**Phase 4 starts with a test.** Before touching the fix, write the simplest reproduction as an
automated test that fails on the current code because of the bug (a one-off script only when the
project truly has no test runner, and say so in your report). Watch it fail, and check it fails for
the right reason: the defect, not a typo or a missing import. Then make the one fix that addresses
the root cause:

- **One change** at a time.
- **No "while I'm here" improvements** and no bundled refactoring. Refactoring is a separate commit
  (`apm:refactoring`).
- **Verify the fix.** The new test passes, no covering test broke (run the tests for every file the
  fix changed; the whole suite runs once, through `<CLI> gate`, right before the PR), and
  the original symptom is gone. `<CLI>` is the framework's command line, as the manager's prompt
  defines it. Then prove the test guards the bug: revert the fix, run the test and
  see it **fail**, restore the fix, and see it pass. Claims follow `apm:verification`.

The test-first rules (`apm:test-first`, "A bug fix starts with a failing test") apply in full:
never weaken another test to make room for the fix, and never skip one. One difference matters:
test-first's "simplest code that passes" is not debugging's "root cause". A hard-coded value or a
guard at the symptom can turn the regression test green and leave the cause in place. Here the fix
is the smallest change that removes the cause, found by the investigation, not the smallest change
that makes the test pass.

## Trace backward to the source

Bugs often show deep in the call stack: a command run in the wrong directory, a file written to
the wrong place, a store opened with the wrong path. The instinct is to fix where the error
appears. That treats the symptom.

```
observe the symptom             what failed, and where
find the immediate cause        the line that directly does it
ask what called it              and with which values
keep tracing up                 each caller, each value, each hop
find the original trigger       where the bad value was born
fix it there                    then add a check at every layer it passed (defense in depth)
```

**Never fix only where the error appears.** If you cannot trace one level further, that is a dead
end, and only then is a fix at the symptom acceptable, stated as such in your report. The full
technique, with instrumentation for when you cannot trace by hand and the search for the test that
pollutes shared state, is in [references/root-cause-tracing.md](references/root-cause-tracing.md).

## Fix the cause, then the instruction behind it

**"Fixed properly" includes fixing why the bug was written.** Once the code is fixed, ask: what led
to this code? Very often the answer is an instruction someone followed: a wrong fact in the
project's instruction file or its project knowledge, a domain skill, a plan step, an agent prompt, a
framework skill, a comment, or a document. Code that faithfully follows a wrong instruction will be
written again, by the next worker, from the same instruction.

```
bug:        a distance is shown a factor of about three too large
root cause: the code multiplies a value that is already in feet by the meters-to-feet factor
behind it:  the project knowledge says "this value is reported in meters"; it is in feet
fix 1:      a failing test with the real unit, then the conversion removed
fix 2:      the project-knowledge fact corrected, with how it was confirmed
```

- **Name the instruction** behind the bug, with its file and line, and quote it.
- **Correct it** in its own commit, separate from the code fix, when it is in the files of the bug
  you were given. State what was wrong and how you confirmed the right value.
- **Report it** under **found elsewhere** when it is outside those files, or is part of the
  framework itself (an agent prompt or an `apm:` skill). The manager routes it: a project file goes
  to a task, and the framework's own instructions go to an issue on the framework's repository.
- **No instruction behind it?** Say so plainly in your report ("no instruction led to this; the
  cause was a slip"). Do not invent one.

**Where the fix lands.** If the bug relates to the current work, its fix is its own commit on the
same branch. If not, the manager files an issue for it. Either way it appears in the manager's next
update to the user. If the fix needs a design change, or would break the standard, **stop**: report
it as a decision, and the manager raises it with the user.

## After three failed fixes

When a fix does not work, **stop** and count how many you have tried.

- **Fewer than three:** go back to phase 1 and analyze again with what the failure taught you.
- **Three or more:** stop fixing. **Do not attempt a fourth fix.** Question the architecture.

Signs that the architecture is the problem: each fix reveals new shared state, coupling or a problem
in a different place; a fix needs "massive refactoring" to apply; each fix creates new symptoms
somewhere else. Ask: is this pattern fundamentally sound? Are we keeping it through sheer inertia?
Should the structure change instead of the symptoms being chased?

This is not a failed hypothesis; it is a wrong architecture, and changing an architecture is not a
debugger's decision. Report **needs decision** to the manager, with the three attempts, what each
showed, and the structural question. **The manager decides, or brings it to the user** as a design
decision. This is separate from the manager's retry rule for a task (two failures on the same model,
then one round one tier stronger, then the user): three failed fixes inside one run is a stop and a
report, never a reason for the debugger to try again itself.

## When there is no root cause

If a complete investigation shows the problem is truly environmental, timing-dependent or external:

1. You have completed the process.
2. Record what you investigated, and what ruled each cause out.
3. Add the appropriate handling (a retry, a timeout, a clear error message).
4. Add monitoring or logging, so the next investigation has evidence.

**But** about 95% of "no root cause" cases are an incomplete investigation. Before you conclude it,
go back over phase 1.

## Defense in depth

A single check at the point of the bug feels sufficient, but other code paths, a later refactoring,
or a test double can bypass it. Once the cause is fixed, **make the bug structurally impossible**:
validate at every layer the data passes through.

| Layer | Purpose |
|-------|---------|
| Entry point | reject plainly invalid input at the boundary |
| Business logic | check the data makes sense for this operation |
| Environment guard | refuse a dangerous operation in a context where it must never run |
| Debug instrumentation | record the context, for the forensics when the others fail |

Then test each layer: bypass the first and check the second catches it. The layers, each with an
example, are in [references/defense-in-depth.md](references/defense-in-depth.md).

## Waiting on conditions, not time

A test that sleeps a guessed amount and then checks is a race: it passes on a fast machine and fails
under load, in parallel, or on a slow runner. **Wait for the condition you care about**, polling it
with a timeout and a clear message, never for a guess at how long it takes.

```
BAD   start(job); sleep(50ms); expect(job.result).toExist()
GOOD  start(job); waitFor(() => job.result, "the job's result", 5s); expect(job.result).toExist()
```

A fixed delay is right only when the test is about timing itself (a debounce, a tick interval), and
then only after waiting for the triggering condition, with the timing derived from the known
interval and a comment saying why. A wait that times out fails the test with its description; it
never hangs waiting for a person. The helpers, patterns and mistakes are in
[references/condition-based-waiting.md](references/condition-based-waiting.md).

## Red flags

If you catch yourself thinking any of these, **stop and go back to phase 1**:

- "Quick fix for now, investigate later."
- "Just try changing X and see if it works."
- "Make several changes, then run the tests."
- "Skip the test, I'll check it by hand."
- "It's probably X; let me fix that."
- "I don't fully understand it, but this might work."
- "The pattern says X, but I'll adapt it differently."
- "Here are the main problems:" followed by fixes, with no investigation behind them.
- Proposing a solution before you have traced the data.
- **"One more fix attempt"** when you have already tried two.
- **Each fix reveals a new problem in a different place.**
- The code is fixed, and you have not asked what instruction led to it.

**Signs from the manager, or from the user through the manager, that you are doing it wrong:**

- "Is that not happening?": you assumed without checking.
- "Will it show us...?": you should have gathered evidence.
- "Stop guessing.": you are proposing fixes without understanding.
- "Think harder about this.": question the fundamentals, not just the symptoms.
- "We're stuck?": your approach is not working.

When you see one: stop, and go back to phase 1.

## Rationalizations

| Excuse | Reality |
|--------|---------|
| "The problem is simple; it doesn't need the process." | Simple problems have root causes too, and the process is fast on simple bugs. |
| "It's an emergency; there's no time." | A systematic search is faster than guess-and-check thrashing. |
| "Just try this first, then investigate." | The first fix sets the pattern. Do it right from the start. |
| "I'll write the test after I confirm the fix works." | An untested fix does not stick. The test first proves it. |
| "Several fixes at once save time." | You cannot tell which one worked, and it causes new bugs. |
| "The reference is too long; I'll adapt the pattern." | Partial understanding guarantees bugs. Read it completely. |
| "I see the problem; let me fix it." | Seeing a symptom is not understanding the root cause. |
| "One more fix attempt." (after two or more) | Three failures mean an architectural problem. Question the pattern; do not fix again. |
| "The senior approach is obviously right; investigating looks like distrust." | Experience is a hypothesis, not evidence. Test it like any other. |
| "I've spent hours; a longer sleep makes it pass." | A longer sleep moves the race. Sunk cost is not a reason to keep a guess. |
| "The code is fixed; the instruction file is someone else's problem." | A wrong instruction writes the bug again. Fix it, or report it so the manager can. |

## Reporting

The debugger returns the framework's structured report to the manager, and nothing else: status
(done, blocked or needs decision), files changed (the regression test included), commands run with
their real output (the test failing, then passing, and the covering tests), concerns, and found elsewhere.
Add the root cause stated plainly, the instruction or project knowledge behind it and what you did
about it, and whether the fix belongs on this branch or in a new issue. You never address the user.

## References

- [references/root-cause-tracing.md](references/root-cause-tracing.md): tracing backward through the
  call chain, instrumenting when you cannot trace by hand, and finding the test that pollutes.
- [references/defense-in-depth.md](references/defense-in-depth.md): the four layers of validation,
  with examples and how to test each.
- [references/condition-based-waiting.md](references/condition-based-waiting.md): polling helpers,
  quick patterns, mistakes, and when a fixed delay is right.

## Common mistakes

- **Fixing where the error appears** instead of where the bad value was born.
- **Fixing before reproducing**, so you cannot tell whether the fix did anything.
- **Bundling several changes** into one attempt, then not knowing which one mattered.
- **A regression test that was never seen failing**, or never re-checked by reverting the fix.
- **A longer sleep** in place of a wait on the real condition.
- **Stopping at the code**, and leaving the wrong instruction that produced it.
- **A fourth fix attempt** instead of a stop and a decision for the manager.
- **Declaring "no root cause"** after half an investigation.
- **Fixing a bug outside your task** instead of reporting it to the manager.
