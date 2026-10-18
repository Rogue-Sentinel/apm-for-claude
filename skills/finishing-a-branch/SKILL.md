---
name: finishing-a-branch
description: "Use when every task of an approved plan is built, verified and reviewed and the manager is about to integrate the branch: merging main in, running the merge gate, the debt check, the pull request and the merge, or when anyone is tempted to discard a branch, a worktree or uncommitted work."
---

# Finishing a branch

Bring the finished branch up to date with `main`, prove the result yourself, pass the debt check,
then push it, open the pull request, and merge it the way the project merges. The manager's job ends
at merged to `main`.

## When this applies

- Every task in the approved plan is done, verified and reviewed, and the final whole-branch review
  is clean. The issue is `integrating`.
- Before any pull request or deploy.
- Whenever anyone is about to throw work away: a branch, a worktree, uncommitted files.

## The core rule

**Merge `main` in, verify everything on the result yourself, pass the debt check, then push, open the
pull request and merge it in the project's merge style.** Never merge partway, never drop a gate
criterion silently, and never discard work without the user's approval in chat.

There is no menu of options at the end. The user approved the plan, and that approval carries the
work through to merged; the manager asks again only when a criterion below cannot be met. Keeping
the branch for later, or discarding it, happens only when the user asks.

## Merge main in first

**Merge `main` into the branch before every pull request and every deploy.** A stale branch's build
once shipped against an old version of the shared data format and locked users out of their newer
saved data. The branch under test must be the branch that will land.

1. **Know the base.** It is normally `main`, as the plan and the issue say. If it is unclear, check
   where the branch forked (`git merge-base`) and confirm it; merging into the wrong base is
   expensive to undo.
2. **Fetch, then merge** `origin/main` into the feature branch. Merge; never rebase a shared branch,
   because rebasing rewrites history that then needs a force-push.
3. **Resolve conflicts deliberately**, keeping both sides' intent, and never by discarding one side.
   A conflict that changes what the plan delivers is a question for the user.
4. **Lanes.** Only one branch is open per lane at a time. When lanes share code or generated files,
   each one merges `main` and regenerates the shared outputs before its pull request.

## Verify everything

Run the merge gate on the merged result, **yourself**, and read every output. All four criteria
must hold:

1. **`main` is merged in, and the full build, the full test suite and every checker the profile
   declares pass**, run by the manager on this tree. "The tests passed earlier" proves only the tree
   they ran on.
2. **No debt number is worse than the baseline** (below).
3. **The final review has no unresolved findings.** Every deferred finding is fixed or decided by the
   user.
4. **Every structural acceptance criterion in the approved plan is met**, walked one by one with the
   evidence for each, and every promised document and decision record exists.

If the build or the tests fail, stop: nothing has been pushed, so the merge is local and
recoverable. The branch and its worktrees stay where they are, and the failure goes to a worker
(a debugger, with `apm:systematic-debugging`). "Probably flaky" is not a diagnosis. If any criterion
cannot be met, **stop and ask** the user. `apm:verification` governs every claim here.

## The debt check

Run `<CLI> debt check` (it compares with `main` by default) on the merged result.

- **Exit 0:** no number is worse. If debt was paid down, the manager runs `<CLI> debt baseline` to
  tighten the ratchet, and commits the new baseline on the branch.
- **Exit 1:** a number got worse, and the output lists each one. **This is a stop: never merge past a
  failed debt check.** Route the fix to a worker as an extraction (`apm:refactoring`); a split that
  leaves two over-limit files still fails. If the worsening genuinely cannot be avoided in this work,
  that is the user's decision.
- **Exit 2:** there is no baseline. Stop and tell the user: the project has not recorded one.

Never raise a limit to make a number pass, and never edit `.apm/debt.json` by hand. `--accept` is
used **only after the user approves that specific worsening in chat**, with their reason. Workers
may run the check, but only the manager runs `debt baseline`.

## The pull request

1. **Push** the branch: `git push -u origin <branch>`. Tests passed locally before anything is
   pushed. Work on a detached HEAD (a platform-managed worktree) has no branch to push: push it as a
   new named branch (`git push origin HEAD:refs/heads/<branch>`) and open the pull request from that.
2. **A rejected push means the remote moved.** Fetch, merge `main` again, and verify again. Never
   force-push; the guard blocks it, and it is done only on the user's explicit request.
3. **Open the pull request** against `main` with the forge's own tool, following the repository's
   template and conventions. Its description carries: what changed and why; the issue it closes; the
   plan's path; the verification commands you ran and their results; the debt check's output; each
   structural criterion and its evidence; the rulings you made; any existing test that changed, on
   purpose, and why. Report its link to the user.
4. **Continuous integration is not a gate.** Local verification is, and a failed check on the forge
   never blocks the merge by itself. The manager reads it. If it reveals a real bug, that bug follows
   the path of any bug found mid-task: a debugger finds the cause and fixes it with a regression test,
   on this branch as its own commit if it belongs to this work, or as a new issue if it does not, and
   it appears in the next update to the user. A related fix on this branch is verified and reviewed
   like any other change before the merge.

## The project's merge style

**Merge the pull request the way the project's profile says.** The merge style is a declared override
in the profile: for example, merge commits and never squashing, because the individual commits are
the record; or squash, or rebase, if the project declares it. If the profile declares none, the
style was asked for **at plan approval**, in the plan summary (`apm:writing-plans`), so the merge
never waits on a second question; use the answer the user gave there, and suggest recording it in the
profile through a pull request. It is their call, never a framework default.

After the merge:

- confirm `main` holds the merge;
- record it: `<CLI> issue N --status merged` (the CLI writes the project log itself);
- close the issue, if the merge did not;
- report to the user: what shipped, the pull request's link, every ruling you made with what it costs
  if wrong, and every deferred item;
- leave the worktrees where they are (`apm:worktrees`). A merged feature branch may be deleted only
  with git's safe delete, which refuses unmerged work; never forced.

## Never discard work

Discarding means anything that loses committed or uncommitted work: deleting an unmerged branch,
removing a worktree, resetting, cleaning, checking out over changes, dropping a stash, force-pushing.

- **It happens only when the user asks for it**, in so many words. Never offer it because they "seem
  done" with the work.
- **Confirm first, listing exactly what would be lost:** the branch, its commits, the worktree's path,
  and any uncommitted files, **and the exact commands** you will ask the user to approve, each in
  full, with the directory it will run in:

  ```
  This will permanently delete:
  - branch resume-points, with commits a1b2c3d "Price an order", d4e5f6a "Resume from a save point"
  - the worktree at <path>, with 2 uncommitted files: notes.md, scratch.txt
  The commands, run from <main checkout>:
  - git worktree remove --force <path>
  - git branch -D resume-points
  Reply `discard` to approve exactly these.
  ```

  Wait for exactly that reply. "Yeah, get rid of it" is not that confirmation, and the reply covers
  only the commands listed.
- **The guard blocks these commands.** After the confirmation, record each one with
  `<CLI> approve --command "<the exact full command>" --reason TEXT`, then run it once. Run
  the approve call on its own, with nothing chained to it, from the directory the command will
  run in (a command approval applies only there), quoting the command in single quotes if it holds
  double quotes. The approval lasts 10 minutes and covers that exact full command only. If the
  approve call is itself denied, stop and ask the user to run the command themselves; never rewrite
  a command to make it approvable. A command that changes needs a new confirmation.
- **Keeping the branch for later**, if the user asks: report the branch and the worktree's path, and
  leave both in place.

| Step | Who decides | Blocked by the guard |
|------|-------------|----------------------|
| Merge `main` in, verify, debt check | the manager | no |
| Push, open the pull request, merge | the manager (the approved plan) | force-push only |
| `--accept` a worse debt number | the user, in chat | workers only |
| Keep the branch for later | the user | no |
| Discard a branch, worktree or files | the user, confirming `discard` | yes |

## Rationalizations

| Excuse | Reality |
|--------|---------|
| "Tests passed earlier this session." | Run them on the tree you are about to integrate. |
| "`main` hasn't moved much; no need to merge it in." | A stale branch once locked users out of their own data. Merge it in. |
| "The debt check is one function over; merge and fix it later." | A failed debt check is a stop. Later never comes. |
| "I'll just raise the limit." | Raising a limit is a worsening. It needs the user's approval. |
| "They obviously want it merged." | They approved the plan, so it merges, through every gate, or not at all. |
| "They seem done; I'll offer to discard it." | Discarding happens only when they ask. |
| "'Yeah, get rid of it' counts as confirmation." | Only the reply `discard` does. |
| "The push was rejected; force-push will fix it." | The remote moved. Fetch, merge, verify. |
| "The merged-result failure is probably flaky." | A failing merged result stops everything. Investigate. |
| "The base branch is obviously `main`." | Check where it forked, or confirm it. |
| "The pull request is up, so the worktree is clutter now." | It stays until the work lands. |

## Common mistakes

- **Opening the pull request before merging `main` in.**
- **Verifying the branch before the merge** and not the merged result.
- **Merging past a failed debt check**, or editing the baseline by hand.
- **A pull request description without evidence**: no commands, no outputs, no criteria.
- **The wrong merge style**: squashing a project whose commits are its record, or the reverse.
- **Force-pushing** after a rejected push.
- **Removing worktrees after the merge.**
- **Offering to discard work**, or accepting anything but `discard` as the confirmation.
- **Dropping a criterion silently** because it was inconvenient, instead of asking.
