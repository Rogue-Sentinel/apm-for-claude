---
name: parallel-dispatch
description: "Use when the manager has two or more independent pieces of work (plan tasks with disjoint files, unrelated failures in different subsystems, auditors on separate parts of a tree) and is deciding whether to run workers at the same time, and how."
---

# Parallel dispatch

When several pieces of work are truly independent, doing them one after another wastes time. Give
each one its own worker, with its own brief and its own worktree, and let them run at once. Each
worker gets exactly the context its problem needs, never the manager's history, which also keeps
the manager's own context free for coordinating.

## When this applies

- An approved plan has tasks that touch disjoint files and do not depend on each other.
- Several failures turn up that look unrelated: different test files, different subsystems,
  different bugs.
- An initial audit, where auditors survey separate parts of the tree.

## The core rule

**One worker per independent problem, running at once, only when their files are disjoint, never
more than the worker cap, and each in its own worktree.** Anything less than certain independence
runs one at a time.

## When work can run in parallel

```
several pieces of work?
  related (fixing one might fix the others)?   -> one worker investigates them together
  independent?
    they share a file, a resource or an interface?   -> one at a time
    nothing shared?                                  -> parallel, up to the cap
```

**Use it when:**
- three or more test files fail with different root causes;
- several subsystems are broken independently;
- each problem can be understood without context from the others;
- the plan says the tasks may run in parallel, and their files confirm it.

**Do not use it when:**
- the failures are related: fixing one might fix the others, so investigate them together first;
- understanding the problem needs the whole system's state;
- it is exploratory debugging, and you do not yet know what is broken;
- the workers would interfere: the same files, or the same resources.

## Disjoint files only

Compare the **Files** blocks of the tasks. If any file appears in two of them, those tasks run one
at a time, whatever else is true. Then look past the file lists:

- **Shared resources count as shared files:** the same database, port, fixture directory, cache, or
  generated output.
- **A file every task appends to** (a registry, a changelog, a list of credits, an index) is shared.
- **Interfaces order the work:** a task that consumes what another produces runs after it.
- **Worktrees isolate copies, not merges.** Two workers editing one file in separate worktrees still
  collide when their branches come together.

The plan's note that tasks may run in parallel is a claim to check, not a permission. If the files
say otherwise, the files win.

## The worker cap

**Never run more than the profile's `max_workers` at once.** It is 3 at most; a profile may lower it
and never raise it. The platform enforces the same number.

- The cap counts every worker: implementers, debuggers, reviewers, auditors and the planner.
- It is shared across every active issue, not per issue.
- Work over the cap waits in a queue. When a worker finishes, start the next.
- "Just one more" is still over the cap.

## Writing each brief

A good brief is:

1. **Focused:** one clear problem, one test file or one subsystem.
2. **Self-contained:** all the context needed to understand it, and nothing from the others.
3. **Specific about output:** the structured report, and what it must contain.

Every brief gives the worker its **scope** (the files it owns), its **goal**, its **constraints**
(what it must not change), and its **expected output**. Tell it that other workers are running on
other files at the same time, so a surprise in a file it does not own is reported, not fixed.

```
Fix the 3 failing tests in tests/session/test_abort:

1. "aborting keeps the partial output": expects 'interrupted at' in the message
2. "mixed completed and aborted calls": the fast call is aborted instead of completed
3. "pending count is tracked": expects 3 results, gets 0

These look like timing problems. Your task:
1. Read the test file and understand what each test checks.
2. Find the root cause: timing, or a real bug?
3. Fix it by waiting on the event the test needs instead of an arbitrary delay,
   or by fixing the abort logic if that is where the bug is.
   Do not just lengthen a timeout: find the real issue.

You own src/session/abort and tests/session/test_abort. Other workers are fixing other
subsystems at the same time; change nothing else.

Return the structured report, with the root cause stated plainly.
```

| Weak brief | Strong brief |
|------------|--------------|
| "Fix all the tests": the worker gets lost | "Fix tests/session/test_abort": a focused scope |
| "Fix the race condition": the worker does not know where | the error messages and test names, pasted in |
| no constraints: the worker refactors everything | "change only these files"; "fix the tests only" |
| "Fix it": you cannot tell what changed | "return the root cause and every change" |

**Dispatch them together.** Every dispatch in one message runs at once; one dispatch per message
runs them one after another. Each dispatch sets `subagent_type`, an explicit `model`, and
`isolation: "worktree"`. Before dispatching, record each task as running
(`<CLI> task N ID --status running --worker <role> --model <model>`).

## Integrating the results

When the workers return:

1. **Read each report.** Understand what changed, and why.
2. **Verify each one yourself, in its own worktree.** A worker's claim is not evidence.
3. **Check for conflicts.** Did two workers edit the same code after all? If so, the files were not
   disjoint: integrate one, then route the other back with the first one's change in its brief.
4. **Merge one branch at a time** into the feature branch, and run the full suite after each merge.
   A green task can still break once combined with another.
5. **Spot-check.** Workers make systematic errors; read a sample of each diff, not just the reports.
6. **Review and record each task** as `apm:executing-plans` says: one review per task, and one record
   per task, with the evidence from your own runs.

An example. After a large refactoring, six tests fail across three files: three timing failures in
the abort tests, two in batch completion (calls never run), one in an approval race (a count of
zero). The domains are independent: abort logic, batch completion and the approval race share no
code. Three workers run at once. One replaces arbitrary delays with waiting on events, one fixes an
event carrying its identifier in the wrong field, one waits for the asynchronous call to finish. The
fixes touch different files and do not conflict; after each merge the full suite is green.

## Common mistakes

- **Parallel work on shared files**, trusting worktrees to keep them apart until the merge collides.
- **A fourth worker** "because it's small", or a cap counted per issue instead of across all of them.
- **Briefs that are too broad**, carry no context, set no constraints, or ask for vague output.
- **Parallel investigation of related failures**, so three workers fix one root cause three ways.
- **Merging every branch at once** and running the suite only at the end, so a break cannot be
  traced to one merge.
- **Trusting the reports** instead of verifying each worktree and spot-checking the diffs.
- **Pasting the session's history** into every brief instead of each problem's own context.
