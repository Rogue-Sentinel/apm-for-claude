# The plan summary

This is what the user reads before they approve. It is plain language, short enough to read in a
minute, and it is the one place they decide. The full plan is linked, not pasted.

```
Plan for #N: <title>

What changes
Two or three sentences on what the user will be able to see or do when this is merged.

How it will be built
<K> tasks. <One line each, or the three that matter.> Independent tasks run at the same time,
in their own worktrees.

Rough time
About <time>, with the gate and the pull request at the end.

What I decided for you
Each ruling, with what it costs if wrong:
- <decision>. Cost if wrong: <one line>.

What needs your yes
- Anything the plan does that the guard would otherwise block (a deletion, a protected file),
  named exactly. Approving the plan approves exactly these.
- Which tasks touch safety-critical paths and will be reviewed on their own.

How it will merge
<The profile's merge style.> If the profile declares none: "How should this merge: a merge
commit, a squash, or a rebase?" (This is the one question; the merge waits on nothing after it.)

The full plan: <path>
Reply "approved" to start. After that I will send one plain line after each task and come back
when it is merged, unless something comes up the plan did not settle.
```

Leave out any section that is empty, except "How it will merge". A summary that grows past a screen
is a plan that was not sized: split the issue (`apm:running-an-issue`, "Splitting into sub-issues").
