# The audit report

The manager writes this for the user, in plain language, from `<CLI> audit --json`, the auditors'
reports and `<CLI> metrics --json --ref <base>`. The user reads it once and approves, changes or
refuses it. Keep every section; write `None found.` for an empty one.

```
# Audit of <project>

## Mode
Existing or fresh, and why (for example: "existing; 212 tracked files in 3 languages").

## Measured at <base>
- Files and functions over the limits, with the five worst by name.
- The commands found for build, test and each checker.
- The layers found and the direction of their dependencies; any file in two layers.

## In-flight work
| Item | Kind | Detail | Decision |
|------|------|--------|----------|
| branch:<name> | branch | 4 ahead, also on origin | finish first / adopt / leave |
| worktree:<path> | worktree | uncommitted changes | finish first / adopt / leave |
| plan:<path> | plan | not approved | finish first / adopt / leave |
| issue:<n> | issue | <title> | finish first / adopt / leave |

Leave the Decision cell for the user. Say which choice you suggest for each row, and why, below
the table.

## Debt issues
The open issues already filed as debt, by number. Then the debt the numbers show that nobody has
filed, as a short ranked list grouped by area, worst first.

## Capability coverage
The table from `<CLI> coverage --table`, or "Not inventoried yet." The last line is `Gaps: N`.
Approval waits for `Gaps: 0`.

## Draft profile
The commands, layers, protected paths, lanes and any `workflow` overrides, as they will be written
to `.apm/profile.json`, with the methodology each override stands in for.

## Methodology to replace, and domain knowledge to keep
Two lists of files. Nothing in the first is replaced until the user approves this report.

## Notes
Everything the audit could not read, word for word: no `origin`, `gh` missing or not signed in,
no `main`, no commits, a worktree whose folder is gone.
```
