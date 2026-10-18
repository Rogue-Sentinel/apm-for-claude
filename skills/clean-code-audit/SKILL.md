---
name: clean-code-audit
description: "Use when a whole codebase needs a quality audit against the standard: when the framework is first set up in a project, before planning a debt paydown, or for a periodic health check that ranks findings and names the top five actions."
---

# Clean code audit

Audit a whole codebase against the framework's standard, measure what can be measured, and produce
a structured report with a score per category, ranked findings and the five actions that matter
most.

## When this applies

- The framework is being set up in a project: the auditor runs this audit at init, so the project's
  starting debt is known before any work begins.
- Someone asks for a code quality audit, a health check, or an assessment of a whole codebase rather
  than of one branch (a branch is `apm:branch-review`).
- Debt is to be paid down, and the work needs ranking before it is planned.
- A module is about to be heavily changed, and its state should be known first.

## The core rule

**Evaluate the codebase against every part of the standard, with measured numbers first and
judgment second, and report each finding so it can be acted on.** Every finding names a file and a
line, and carries a concrete, incremental recommendation. Findings are ranked by impact, and the
report ends with the five actions worth doing first. The audit reports; it changes no code, records
no baseline and edits no profile.

## Scan

1. **Identify the project.** Its primary languages, its frameworks, and its structure: where the
   source, the tests, the build and the configuration live.
2. **Choose the files.** Focus on source files. Leave out vendored dependencies and generated code:
   the profile's `standard.metrics` (`include`, `exclude`, `extra_exclude`) says which files count,
   and without a profile the defaults leave out dependency, vendor, third-party, build and output
   directories, minified and generated files, and `.apm/`. `git ls-files` lists what is tracked.
   Count the files scanned; the report needs the number.
3. **Find what the project already has**: its test suites and how they run, its linter and
   formatter, its continuous integration, and any checker of its own that measures sizes or rules
   (a script that counts long functions, say). A checker found here is used in Measure.
4. **Note whether the project has a user interface.** A later branch review scores the UI-only
   dimensions N/A without one.

## Measure

Numbers come from tools, never from reading and estimating.

- **`apm metrics`** (or `apm metrics --json` for every number) measures every selected file against
  the profile's limits, `standard.limits`: by default **15 lines of logic per function** (`function`),
  **200 per file** (`file`), and a review flag at **7 or more public methods** (`public_methods`). It
  lists each over-limit function and file as `path:line name -- N lines`, largest first, the wide
  types, and any file it could not measure, with the reason. It works in any git repository, so it
  runs before the project is initialized, with the defaults.
- **The profile's checkers.** A project with its own checker declares it under
  `standard.debt_sources`, and its numbers join the ratchet. Run each declared checker, and any
  checker found during the scan, and record its numbers. A checker found but not yet declared is
  reported as a candidate for `standard.debt_sources`.
- **`apm debt check`**, when the project already has a baseline, reports whether any debt has grown
  since it was recorded. Exit 2 means there is no baseline yet, which is expected at init. The audit
  never runs `apm debt baseline`: only the manager records a baseline, after the user has seen the
  numbers.
- **Counts for each category**, taken with `git grep -c -E`, using the patterns per language in
  [the branch review's evidence reference](../branch-review/references/evidence-by-language.md)
  and the project's own `standard.review_patterns`.

Then assess each category. Each one names the skill that holds its full rules; load it.

### Test-first

The rules are in `apm:test-first`.

- Look for test files and the patterns of test coverage: which source modules have tests and which
  have none.
- Check whether tests follow arrange, act, assert.
- Look for test-first indicators: test files matching source files one to one, thorough edge-case
  coverage, and tests landing in the same commits as the behavior they cover (`git log --stat`).
- Flag public functions, methods and types with no test.
- Flag skipped or disabled tests, tests that wait on a person, and assertions weakened to pass.

### Refactoring

The rules are in `apm:refactoring`; the limits are in `apm:clean-code`.

- Every function over the profile's function limit (`standard.limits.function`, default 15 lines of
  logic) is a candidate for extract method. Take the list from `apm metrics`, largest first; never
  judge length by eye.
- Every file over the file limit (default 200 lines of logic) is a candidate for splitting, and every
  type with 7 or more public methods needs a stated reason.
- Flag poorly named variables, functions and types (`apm:clean-code`, meaningful names).
- Detect complex conditionals (nested if and else chains, switch statements with shared logic, the
  same branching on a type in several places) that polymorphism would replace.

### SOLID

The rules are in `apm:solid`.

- **Single responsibility:** types and modules with more than one reason to change (mixed concerns).
- **Open-closed:** code that must be modified for every new case, where an extension point belongs.
- **Liskov substitution:** inheritance hierarchies whose subtypes break the base type's contract.
- **Interface segregation:** large interfaces that force clients to depend on methods they do not
  use.
- **Dependency inversion:** high-level modules depending directly on low-level implementations.

### Object design

The rules are in `apm:object-design`.

- Data types with no behavior (anemic domain models), whose rules live in the code that uses them.
- Exposed internal state: public fields, and getter and setter pairs that guard no invariant.
- Deep inheritance hierarchies that composition would serve better.
- Types with 7 or more public methods and no stated reason.

### Functional core

The rules are in `apm:functional-core`.

- Impure functions with hidden side effects.
- Loops that a map, filter or reduce would replace.
- Absence or failure signaled by null or a sentinel, where an option or result value belongs.
- Logic that reads the clock or a random source directly, instead of taking them as parameters.

### Architecture

The rules are in `apm:clean-architecture`.

- Dependency direction: do domain modules depend on infrastructure?
- Port and adapter separation at the system's boundaries.
- Domain logic mixed with I/O, serialization or framework code.
- Imports against the profile's layer map, when the profile declares one. Without one, describe the
  layers the code actually has, as a candidate layer map for the profile.

### Hygiene

The rules are in `apm:clean-code` (the boy scout rule) and `apm:code-smells` (the catalog).

- Apply the boy scout rule: find the areas where small improvements would compound.
- Catalog the code smells: duplicated code, feature envy, long parameter lists, data clumps,
  primitive obsession, and the rest of the catalog, each reported as `apm:code-smells` describes.

## Report format

Produce the report in this shape:

```
## Clean Code Audit Report

### Summary
- Overall health: [Good / Needs Attention / Critical]
- Files scanned: N
- Issues found: N (H high / M medium / L low)

### Measurements
- Limits: function F, file L, public methods P (from the profile, or the defaults)
- apm metrics: N functions over the limit (largest: path:line name -- N lines),
  N files over the limit, N wide types, N files unmeasured
- Project checkers: name -> numbers (declared, or a candidate for standard.debt_sources)
- apm debt check: exit 0 / 1 (each regression) / 2 (no baseline yet)

### Findings by Category

#### Test-first (score: X/10)
- [H/M/L] path:line: finding -> recommendation

#### Refactoring (score: X/10)
...

#### SOLID (score: X/10)
...

#### Object design (score: X/10)
...

#### Functional core (score: X/10)
...

#### Architecture (score: X/10)
...

#### Hygiene (score: X/10)
...

### Top 5 Priority Actions
1. ...
2. ...
3. ...
4. ...
5. ...
```

An older audit may use the earlier category names: TDD is Test-first, OOP is Object design,
Functional Programming is Functional core, and Code Hygiene is Hygiene.

**Scoring a category.** Score it from 1 to 10 on its findings, with the same honesty as a branch
review: a 5/10 with a clear path is worth more than a generous 7/10. As a guide, 9-10 has only low
findings; 7-8 has medium findings but no high ones; 4-6 has high findings in some parts of the code;
1-3 has high findings throughout, or nothing the category asks for exists (no tests at all is 1-3
for test-first).

**Overall health.** **Good** when no category is below 7 and no finding is high. **Critical** when
test-first or architecture is at 3 or below, or when debt is so widespread that most changes would
have to pay some down first. **Needs Attention** otherwise. Say in one line why.

## Priorities

- **Rank by impact.** A finding in code that changes often outranks one in stable code that is
  rarely touched. Use the severity matrix in `apm:code-smells` (impact against effort): high impact
  and low effort first.
- **High, medium, low.** High: it causes defects or blocks safe change now (no tests around logic
  that changes, a domain that depends on infrastructure, a function far over the limit in active
  code). Medium: it slows every change in its area. Low: a local improvement that the boy scout rule
  will pick up.
- **Be specific.** Every finding names the file, the line, and the concrete change: "extract
  `validateOrder` and `calculateTotal` from `placeOrder` (42 lines of logic, limit 15) in
  `src/orders/checkout.ext:42`", never "improve the checkout code".
- **Actionable and incremental.** Every recommendation is a step a single task can take, with tests
  first where tests are missing. Never "rewrite the module".
- **The top 5 are the five actions that buy the most**, each one small enough to become one issue.
  Missing tests around code that is about to change come before refactoring it.
- **Where the debt goes.** Debt in code that planned work will touch is paid down in that work,
  through extract-before-you-add tasks. Debt elsewhere becomes a ranked issue for the user to
  schedule.

## Common mistakes

- **Counting lengths by eye**, or using a fixed number instead of the profile's limits. The numbers
  come from `apm metrics` and the profile.
- **Findings with no file, no line or no fix.** The reader cannot act on "the architecture is
  messy".
- **Treating every finding as urgent.** Rank by impact; most findings are scheduled, and many are
  left to the boy scout rule.
- **A top 5 of rewrites.** Every action is incremental and fits one task.
- **Changing code during the audit**, or running `apm debt baseline`. The audit reports; the manager
  records the baseline once the user has seen the numbers.
- **Auditing vendored or generated code.** It inflates the numbers and nobody will fix it.
- **Skipping a category** because nothing seemed wrong. Each category gets a score and the evidence
  for it, even when the evidence is "no findings".
- **Recommending a refactoring where there are no tests.** The first action is the tests.
