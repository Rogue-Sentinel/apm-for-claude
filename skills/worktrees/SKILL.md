---
name: worktrees
description: "Use when dispatching a worker that will change files, when a worker starts work and needs to know where it is, when integrating a worker's branch, or when tempted to clean up, remove or prune a worktree."
---

# Worktrees

Every builder works in its own isolated copy of the repository, so a mistake damages only that
copy. Worktrees are created by the platform's own mechanism, integrated by the manager, and never
removed by anyone without the user's approval.

## When this applies

- The manager is dispatching an implementer or a debugger.
- A worker is starting work and needs to know where it is.
- The manager is merging a worker's branch into the feature branch.
- Anyone is tempted to remove, prune or "tidy up" a worktree.

## The core rule

**Every builder builds in its own worktree, and nobody, manager or worker, removes one.** The guard
blocks removing a worktree. Removing one is the user's decision, approved in chat.

## Every builder works in its own worktree

The manager dispatches **every** implementer and **every** debugger with `isolation: "worktree"`,
whether it runs alone or beside others. The worker builds in its own copy, on its own branch, and a
misbehaving worker damages only that copy. This is decided: the manager does not ask the user before
creating one. Workers that only read (a reviewer, an auditor, the planner checking a design) need
none.

A worker in a worktree:

- works only there, and uses paths inside it;
- never changes the main checkout or another worktree;
- commits its work on its own branch, and leaves the merge to the manager.

**Check before you create.** Before creating anything, find out whether you are already in a linked
worktree: if git's own directory and its common directory differ, you are. (Inside a submodule they
differ too: if git reports a superproject working tree, you are in a submodule and should treat it
as a normal checkout.) A desktop session usually already runs in one. Never create a worktree inside
a worktree.

## Creating one

**Prefer the platform's native mechanism:** the `isolation: "worktree"` dispatch setting, or a native
worktree tool. It owns placement, branching and cleanup. Making one by hand when a native mechanism
exists creates state the platform cannot see or manage.

Only if no native mechanism exists, fall back to git:

1. **Choose the directory**, in this order: a location the profile or the user's instructions name;
   an existing `.worktrees/` at the project root; an existing `worktrees/`; otherwise `.worktrees/`.
   An explicit preference always beats what happens to exist.
2. **Make sure it is ignored** (`git check-ignore`). If it is not, add it to `.gitignore` and commit
   that first: an unignored worktree directory commits a whole second copy of the tree.
3. **Create it** with `git worktree add <path> -b <branch>`.
4. If the sandbox refuses, say so in your report and do not work around it.

**Check where it started.** A native worktree may be cut from the default branch, not from the
feature branch the manager is building on, and then it lacks the plan and the earlier tasks. The
manager hands the worker the recorded BASE and the feature branch's name. The worker checks that
BASE is an ancestor of HEAD (`git merge-base --is-ancestor <BASE> HEAD`). If it is not, the worker
fast-forwards to the feature branch with `git merge --ff-only <feature-branch>` and checks again. If
the fast-forward refuses, the worker stops and reports; it never merges any other way, and never
builds on the wrong base.

**Set it up and check the baseline.** Run the profile's setup command if it declares one, then the
targeted tests for the files the task will change (the full suite waits for `<CLI> gate`). If the
baseline fails, report the failures; whether to proceed is the manager's call,
or the user's through the manager. A dirty baseline makes every later failure ambiguous. If it
passes, report it ready:

```
Worktree ready at <full path>
Tests passing (<N> tests, 0 failures)
Ready to build Task <N>
```

| Situation | Action |
|-----------|--------|
| Already in a linked worktree | do not create another |
| In a submodule | treat it as a normal checkout |
| A native mechanism exists | use it |
| No native mechanism | the git fallback, above |
| The worktree directory is not ignored | ignore it and commit that first |
| The sandbox refuses | report it; do not work around it |
| The baseline fails | report it; the manager decides |
| BASE is not an ancestor of HEAD | fast-forward to the feature branch; if it refuses, stop and report |

## Never remove a worktree yourself

**The guard blocks removing a worktree**, for the manager and every worker. A denial is a stop.

- **Workers never remove, prune or delete a worktree**, their own included, and never delete its
  directory by other means.
- **The manager never removes one on its own judgment.** Stale worktrees and branches are reported to
  the user, never removed, unless the user approves removing that specific one in chat. Only then is
  the exact command recorded with `<CLI> approve --command "<the exact full command>" --reason TEXT`
  and run once. Run the approve call on its own, with nothing chained to it, from the directory the
  command will run in (a command approval applies only there), quoting the command in single
  quotes if it holds double quotes. The approval lasts 10 minutes and covers that exact full command only. If the
  approve call is itself denied, stop and ask the user to run the command themselves; never rewrite
  a command to make it approvable.
- **A worktree's uncommitted files exist nowhere else.** Before any removal the user has approved,
  show them what is at stake (`git -C <path> status --porcelain -uall`) and let them choose: commit
  the files to the branch, move them somewhere safe, or delete them, which cannot be undone. Never
  force a removal past that refusal.
- **A worktree with an open pull request stays** until the work has landed: review feedback is fixed
  there.
- **Worktrees you did not create are not yours.** They belong to the platform, the user, or another
  session. Leave them alone. If the platform offers a way to leave its own worktree, use that.

## Integrating a worktree branch

When a worker reports done, the manager:

1. **verifies in the worktree:** runs the targeted tests (the task's own and those for the files it
   changed) and the profile's checkers there, and reads the output; the full suite runs once, later,
   through `<CLI> gate`;
2. **merges the worktree's branch into the feature branch** with a merge, never a rebase, so the
   worker's commits stay the record;
3. **verifies again on the feature branch**, because a clean task can break once merged with others;
4. **records the task** only then, with the evidence from its own runs.

If the merge conflicts, resolve it deliberately, keeping both sides' intent, or send it back to a
worker with both changes in its brief. Never resolve a conflict by throwing one side away (checking
out over changes, resetting, or cleaning); the guard blocks those for a reason. A conflict between
tasks that were dispatched in parallel means their files were not disjoint: note it in the record.

After the merge, the worker's branch may stay. If it is deleted at all, only with git's safe delete,
which refuses a branch that is not fully merged; never a forced delete.

## Rationalizations

| Excuse | Reality |
|--------|---------|
| "I'm obviously not in a worktree; no need to check." | Platform-made isolation and submodules both fool a glance. Check. |
| "A manual worktree is quicker than the native mechanism." | It creates state the platform cannot see or clean up. |
| "The directory is surely ignored already." | Check it. An unignored worktree commits a second copy of the tree. |
| "The workspace is fresh; the baseline can wait." | A dirty baseline makes every later failure ambiguous. Run it now. |
| "The pull request is up, so the worktree is clutter." | Review feedback is fixed there. It stays until the work lands. |
| "That other worktree looks stale; I'll clean it too." | Report it. Removing it is the user's call. |
| "Removal was refused; forcing it just finishes the job." | The refusal means files exist only there. Forcing destroys them. Ask the user. |
| "The guard is in the way; I'll delete the directory instead." | A denial is a stop, not a puzzle. Ask the user. |

## Common mistakes

- **Dispatching a builder without `isolation: "worktree"`** because it runs alone.
- **Creating a worktree inside a worktree.**
- **A worker reaching into the main checkout** or another worker's worktree.
- **Skipping the baseline run**, or proceeding past a failing one without the manager's decision.
- **Rebasing a worker's branch** onto the feature branch instead of merging it.
- **Removing, pruning or force-removing a worktree**, or deleting its directory another way.
- **Resolving a merge conflict by discarding one side.**
- **Force-deleting a branch** that still holds unmerged commits.
