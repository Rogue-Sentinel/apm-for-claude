---
name: running-an-issue
description: "Use when the user asks for a feature or reports a bug, when an issue is filed or queued, when a plan is ready for the user to approve, when a worker finds a bug mid-build, or when the manager is about to stop between tasks to ask whether to continue."
---

# Running an issue

Take a request from the user's words to a merged pull request. The user speaks twice: the request, and
the approval of the plan. Everything between is the manager's, and it keeps them informed in plain
lines instead of asking.

The manager runs this workflow. `<CLI>` is the framework's command line, as the manager's prompt
defines it.

## When this applies

- The user asks for a feature, or reports a bug.
- An issue sits in the queue and its turn has come.
- A plan is ready, or approved, or being built.
- A worker reports a bug it found while building.
- The manager is about to ask "should I continue?" between tasks.

Large or unclear requests start with `apm:design-first`; this skill begins when the request is clear
enough to file.

## The core rule

**After the request, the user has one touchpoint, plan approval. From approval to merge, the manager
runs without asking, unless something comes up that the plan did not settle.**

Breaking the letter of this rule is breaking its spirit: a "quick check-in" between tasks, a
"want me to merge?" after a clean gate, or a question the plan already answered is the user being
used as a progress bar. Stop only for what "When to stop and ask" in `apm:executing-plans` lists.

## Filing the issue

An issue is filed before any planning. File it with `<CLI> github file --title T --body-file PATH`
(add `--kind feature|bug|debt`, `--lane NAME`, `--label L`, `--parent P`). It creates the GitHub
issue, records it in the ledger as `queued`, and prints `filed #N: URL`.

- **Use the repository's own issue templates and labels.** The body follows
  [references/issue-body-template.md](references/issue-body-template.md), adjusted to the template
  the repo uses for this kind of issue.
- **The branch is cut from the base** (`workflow.base`, normally `main`), named for the issue.
- **Lane rules.** Only one issue is active per lane. If the lane is busy, the issue stays `queued`.
- **If GitHub and state disagree, state wins.** The ledger is what the framework acts on. Say so to
  the user, correct GitHub by hand, and carry on.
- If `gh` is missing or fails, the command exits 2 and says how to do it by hand. File the issue
  yourself, then record it with `<CLI> issue N --title T --kind K`.

## The size check

Before planning, size the work against one pull request that one review can hold.

- **Fits:** continue to "Planning".
- **Too large:** it spans lanes, or several independent behaviors, or the plan would run past what a
  reviewer can read as one diff. Split it (below). Say why in one line.
- **Unclear:** go back to `apm:design-first`; do not plan a guess.

## Splitting into sub-issues

File each part with `<CLI> github file --parent P`. The body ends with `Part of #P`, and the ledger
links the child to its parent. Set the parent to `split` with `<CLI> issue P --status split`: it is
done when every child is merged, and the brief shows `split: K of M sub-issues merged`.

Each sub-issue is planned, approved, built and merged on its own, in an order the user agrees to.
When the last child closes, `<CLI> github close` says to close the parent too.

## Planning

Move the issue to `planning`, then brief `apm:planner` and write the plan with `apm:writing-plans`.
Check it yourself before the user sees it: the structural criteria are checkable, the tasks name their
targeted tests, and the last task runs `<CLI> gate`.

A **bug** is planned the same way, with the reproduction first: the failing test that shows the bug
is Task 1, and the cause is found (`apm:systematic-debugging`) before the fix is planned.

## The plan summary

The user does not read the whole plan. Give them a plain summary from
[references/plan-summary-template.md](references/plan-summary-template.md): what will change, how it
will be built, what it costs if wrong, every ruling made for them, and the decisions that are theirs.

- **The merge style.** If the profile declares none (`workflow.merge_style`), ask for it here, in the
  same message: merge commit, squash or rebase. The merge then never waits on a second question.
- Set the issue to `awaiting-approval` and ask for approval. **This is the one touchpoint.** An answer
  that approves some tasks and not others is not approval; revise the plan and ask again.
- Approval covers the plan as shown, including the allowlisted actions it names.

## Building

Set the issue to `building` and follow `apm:executing-plans`: a worker per task in its own worktree
(`apm:worktrees`), independent tasks in parallel (`apm:parallel-dispatch`), the manager's own
verification, and a record after every task. Do not stop between tasks. If a decision comes up that
the plan did not settle, make it yourself when the cost of being wrong is small and record it with
`<CLI> note N --decision TEXT`; a worker's worry goes in with `--concern TEXT`. A decision that
is large or hard to undo is a question to the user.

## Pacing

Lean by default. The point is to spend time once, where it proves the most.

- **Per task:** the worker and the manager run the **targeted tests** that cover the change, plus the
  size limits and `<CLI> debt check` on the files touched.
- **The full suite runs exactly once**, through `<CLI> gate`, right before the pull request. It runs
  again only if the gate failed and something changed.
- **One whole-branch review** at the end (`apm:code-review`), not one per task.
- **Per-task review is the exception.** It applies when the user asks for it, when the profile says
  `"review": "per-task"`, or when a task touches a `workflow.safety_critical` path. The task is
  reviewed on its own, in addition to the final review.

A task that touches a safety-critical path is flagged in the plan, so it is known before building.

## A bug a worker finds

A worker that finds a bug returns it in its report under **found elsewhere**; it never fixes what is
outside its task. The manager handles it, in this order:

1. **Dispatch `apm:debugger`** with the report. It finds the root cause, writes the failing test,
   fixes it, and also names the **wrong instruction behind it**: the skill, agent prompt or profile
   fact that let the bug through. A wrong skill or agent instruction is fixed when the brief names
   its file (`apm:writing-skills`). A wrong profile fact goes in the report for the manager to record.
2. **Related to this issue:** the fix is its own commit on the same branch, verified and reviewed like
   any other change.
3. **Unrelated:** file it with `<CLI> github file --kind bug`, mention it in the next update, and carry
   on. It is never fixed in this branch.
4. **A design change or a break of the standard is a stop and a question.** If the fix would change
   what the design says, or would worsen a debt number, ask the user.

## Integrating

When every task is done, the issue is `integrating`. Run `apm:merge-gate`: the four criteria, checked
by the manager, with the review recorded by `<CLI> review`. Then follow `apm:finishing-a-branch`:
merge the base in, push, open the pull request and merge it in the project's style.

## Reporting

After the merge, close the loop:

- `<CLI> github close N --pr URL` comments `Shipped in URL.`, closes the issue and records `merged`.
- Tell the user what shipped: the pull request, the behavior they can now see, every ruling made with
  what it costs if wrong, every deferred item and every concern recorded. Do not repeat the
  gate's output; link it.
- Mention each unrelated bug filed along the way.

## Lanes and the queue

One issue is active per lane at a time; others wait as `queued` and are reported. The worker cap is
shared across active issues. When an issue merges, `<CLI> brief` names the next queued issue in the
lane; start it the same way, with the same one touchpoint. Never run two issues that touch the same
files in different lanes without telling the user.

## Progress updates

Send **one plain line after each task**: what finished, what is next, and the rough time left. No
tables, no jargon, no output dumps.

```
Task 3 of 7 done: the order total now includes tax. Next: the receipt layout. About 20 minutes left.
```

If the build is blocked, say what it is waiting on in that same line.

## Quick reference

| Step | Status | Command |
|------|--------|---------|
| File | `queued` | `<CLI> github file` |
| Size, split | `split` for a parent | `<CLI> issue P --status split` |
| Plan, summary | `planning`, `awaiting-approval` | `<CLI> issue N --status ...` |
| Build | `building` | `<CLI> task N ID --status ...` |
| Gate | `integrating` | `<CLI> gate N` |
| Merge, report | `merged` | `<CLI> github close N --pr URL` |

## References

- [references/issue-body-template.md](references/issue-body-template.md): the body of a filed feature,
  bug or debt issue.
- [references/plan-summary-template.md](references/plan-summary-template.md): the summary the user
  approves.

## Common mistakes

- **Asking "should I continue?" between tasks.** The approval already answered it.
- **Filing no issue**, or planning before the issue exists.
- **Running the full suite after every task**, instead of the targeted tests and one gate.
- **Reviewing every task** when nothing asked for it, or skipping the review of a safety-critical task.
- **Fixing an unrelated bug on this branch.** File it; keep the branch's diff about its issue.
- **Fixing the bug and not the instruction** that let it through.
- **Leaving the merge style for after approval.**
- **Trusting GitHub over the ledger.** State wins.
- **Writing a progress update as a report.** One plain line.
