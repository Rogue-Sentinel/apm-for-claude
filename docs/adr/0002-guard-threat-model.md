# ADR-0002: The guard is a guardrail against a cooperative worker's mistakes, not a sandbox against an adversary

## Status

Accepted, 2026-10-18. Amended by ADR-0007.

Builds on section 9 of the design spec, which names the guard as one layer of several.

## Context

Section 9 of the design spec (`docs/specs/2026-10-17-apm-for-claude-design.md`) says the framework's safety
has several layers "because no single rule is enough": protected paths, blocked destructive commands, the
approved plan as an allowlist, planned deletion, and isolated worktrees. Around the guard sit worktree
isolation, the plan allowlist, review, and the manager's own verification of every task.

The guard is a hook. It reads the text of a shell command and decides whether to allow it. A check that
pattern-matches shell text cannot be complete, because the shell is a full language. `eval "$cmd"`,
`$GH issue create`, and a script the worker writes and then runs all build the command at run time, after
the check has looked. The known limits are written down in the docstrings of `scripts/apm/guard_github.py`
and `scripts/apm/guard_workers.py`.

In Plan 3 the guard was reviewed again and again, and every review found a new bypass. Every one of those
findings was an input the reviewer constructed to get past the check: brace expansion, `exec -a`, flags split
on purpose, a quoted module name, indirection through a variable. No worker in the build ever tried to get
past the guard. The reviews had no stated threat model, so the brief asked for "any way past the guard", and
a search with no bound against a check that cannot be complete never ends.

Patching those constructed inputs was not free. The patches caused real regressions against `main`: commands
that `main` denied, such as a protected-path write after an escaped line ending, were allowed. Those patches were
reworked or reverted. They also added false positives on routine work.

## Decision

**The guard is a guardrail against the mistakes of a cooperative worker. It is not a sandbox against an
adversary.**

What the guard must stop is the command a cooperative worker, or the manager, could plausibly type by mistake
or by misreading its brief:

- plain `gh` writes, such as `gh issue create` and `gh pr merge`;
- a multi-line `gh api` call;
- destructive commands (`rm -rf`, `git reset --hard`, force-push and the like);
- writes to a protected path or to `.apm/`;
- APM state changes through the CLI as normally written (`apm issue`, `apm task`, `apm debt baseline`).

What is outside the model is an input built to evade the check: brace expansion, `exec -a`, deliberately
split flags, quoted module names, and indirection through a variable, an `eval`, or a script the worker
writes. These are not fixed. Each is recorded in the known-limits docstring of the guard module it concerns.

**The guard never gets weaker than it was before a change.** A change that loosens any verdict, so that a
command denied before is now allowed, is a regression and blocks the change.

## Consequences

- **Guard reviews are bounded by this model.** A finding about the guard, a hook or another safety check must
  name a plausible way a cooperative worker or the manager would produce that command while following its
  brief. A finding that cannot is recorded as a known limit, a suggestion, and never as must-fix. This is in
  `apm:code-review`, `apm:executing-plans` and `apm:writing-plans`.
- **A scoped re-review stops looping.** It blocks only on a finding not addressed or a regression the fix
  introduced, a looser verdict included. Every other new finding goes to deferred findings or a follow-up.
- **Exotic bypasses are documented, not chased.** The guard stays small enough to read, and the other layers
  carry the weight they were designed to carry.
- **False positives on routine work are defects too.** A guard that denies what a cooperative worker needs
  to do pushes workers to work around it, and that is the larger risk in practice.
- **A determined or compromised worker is not stopped by the guard alone.** The accepted risk is real. The
  protection against it is the other layers: the isolated worktree limits the damage to a copy, review and the
  manager's verification see what came back, and protected paths are enforced for the manager too.
- **Issue #6's evasion items are closed as outside the model.** Any that is a plausible mistake, not a
  constructed input, is reopened as a new issue with the command a worker would type.

## Rules

A reviewer applies these to any change to the guard, a hook or another safety check:

1. Does the finding name a command a cooperative worker or the manager would plausibly produce? If not, it is
   a known limit: a suggestion, recorded in the module's docstring.
2. Does the change loosen a verdict that was a denial before? If so, it is must-fix, always.
3. Does it deny a routine command a cooperative worker needs? That is a defect, graded by how routine the
   command is.
4. A fix to a guard comes with a test for the realistic command, and a test that the verdicts of the cases
   around it are unchanged.
5. A check that cannot be made complete is never reviewed by asking for "any way past" it.

## Alternatives considered

- **Treat the guard as a sandbox and close every bypass.** Rejected: a text check over a full shell language
  cannot be complete, so the work never ends, and each patch risks denying routine commands. Plan 3 showed
  both.
- **Replace the text check with an operating system sandbox.** Rejected for now: it would not be portable
  across the platforms the plugin supports, and it is a different project. It is the right answer if a
  worker is ever treated as an adversary, and this record would then be superseded.
- **Remove the guard.** Rejected: the mistakes a cooperative worker makes are real and expensive, such as a
  `gh pr merge` the user never approved, and a hook stops them for almost nothing.
- **Leave the threat model unstated.** Rejected: that is how the review loop began. Reviewers need a bound
  they can apply.
