# The auditor brief

Dispatch `apm:auditor` with this brief, filled in. At most three auditors at once, each on a part of
the tree no other auditor reads. The auditor reads and reports; it changes nothing and removes
nothing.

```
You are auditing one part of <project> for initialization under the framework.

Your part of the tree: <paths, for example src/billing/** and tests/billing/**>
Read it as committed at <base>, not from the working tree:
  git show <base>:<path>      git ls-tree -r --name-only <base>
The APM command line is: <CLI>

Do, in this order:
1. Run `<CLI> metrics --json --ref <base> <your paths>` and report the numbers that are over a limit.
2. Run `<CLI> audit --json` once and report the in-flight work that touches your part (branches,
   worktrees, plans, specs, issues). Report it; do not remove or change any of it.
3. Find the build, test and lint commands this part uses, and the layers and the direction of their
   dependencies.
4. Inventory every rule the project states for itself (instruction files, style guides, lint
   configuration, skills) that applies to your part. One rule per row: where it is stated, what it
   says in one sentence, and whether it is methodology (how to work) or domain knowledge (a fact
   about this project).
5. List committed data, files outside the repository, secrets and configuration that should be
   protected paths.

Return the structured report. Put the draft profile fields, the rule-by-rule inventory (in the
shape of the framework's coverage file) and the in-flight work in separate sections. Anything
uncertain goes under concerns. Do not ask the user anything.

Load `apm:clean-code-audit` first, and `apm:verification` before you report a number.
```

The manager merges the auditors' sections, checks the numbers itself, and writes the audit report
from the audit report template.
