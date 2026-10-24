# ADR-0008: The guard is frozen at issue 20: a false alarm with a workaround is accepted, not fixed

## Status

Accepted, 2026-10-24. Builds on ADR-0002 and ADR-0007.

## Context

Issues #11, #14, #19 and #20 each refined the guard's rules, and each fix opened the next false alarm:
#13, #15 and #21. ADR-0007 is the latest of these: it made the guard read where a shell command writes, and named
its own limits. Every refinement added parsing rules, and every rule had edges the next report found.

The user decided on 2026-10-24 to stop here. Their words: "if anything is dangerous the agent needs to ask the users
permission then it can do it".

## Decision

**After issue 20 (PR #28), the guard gets no new command-reading rules.**

- **What stays blocked.** Destructive commands, protected paths, `.git`, APM state, and writes outside the project.
  Where ADR-0006 and ADR-0007 allow an approval, the user gives it in chat; the rest stay unapprovable. The rules of
  ADR-0002 and ADR-0007 are unchanged.
- **What is accepted.** A false alarm on harmless work that has a workaround (the Read tool, `git show`) is accepted
  rather than fixed.
- **When the guard may change.** Only when a false alarm blocks real work with no workaround, or when a dangerous
  action gets through, meaning a command a cooperative worker would produce while following its brief (the test of
  ADR-0002).

## Consequences

- A worker sometimes falls back to the Read tool, or to another command, when the guard misreads a harmless call.
- Issues #13, #15 and #21 are closed as not planned.
- The known limits named in ADR-0007 and in the guard docstrings stay limits.
- ADR-0002 and ADR-0007 are not changed by this record.

## Alternatives considered

- **Keep fixing each false alarm.** Rejected: it is unbounded parsing work for no safety gain, and each fix has
  opened the next report.
- **Cut the guard down to the hard rules only.** Rejected for now: it is a bigger change than the user asked for.
