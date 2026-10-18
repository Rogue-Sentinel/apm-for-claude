# Scoring evidence guide

Every dimension's score must rest on concrete evidence that a reader can check. This guide says what
to gather for each dimension and how to present it. The concrete patterns for each language are in
[evidence-by-language.md](evidence-by-language.md); a project's own patterns are in its profile under
`standard.review_patterns`.

## How to gather evidence

- **Measure on both sides.** Every count is taken for the old code (the base) and the new code (the
  branch). `git grep` reads a commit directly, so the base needs no checkout:

  ```
  git grep -c -E '<pattern>' <base> -- '<pathspec>'     # old: per-file counts on the base
  git grep -c -E '<pattern>' -- '<pathspec>'            # new: per-file counts on the branch
  git ls-files '<pathspec>' | wc -l                     # how many files of a kind
  git ls-tree -r --name-only <base> -- '<pathspec>' | wc -l   # the same, on the base
  ```

  Sum the per-file counts for a total, and keep the per-file lines: the largest ones are the
  evidence worth quoting.
- **Sizes come from the tool.** `apm metrics` (and `apm metrics --json`) lists every function and
  file over the profile's limits and every wide type. For the old side, read the baseline recorded on
  the base (`git show <base>:.apm/debt.json`) or run `apm metrics` in a separate checkout of the base.
- **The ratchet is evidence too.** `apm debt check --base <base>` prints each regression, or says
  there is no baseline. Quote what it printed.
- **Patterns are evidence, not verdicts.** A count says how often something occurs; read a sample of
  the matches to confirm what they are before scoring on them. A pattern that also matches comments
  or strings gets its count checked by hand.
- **Present each score as one sentence:** the score, then the facts behind it, then what is missing.
  Name files with their paths; give counts as numbers.

## Type and contract safety

### What to look for
- The strictest checking mode the toolchain offers, and whether it is turned on in the project's
  configuration.
- Casts to the top type, and double casts through it to another type.
- Comments or attributes that silence a type checker or compiler diagnostic.
- Maps from strings to untyped values standing in for a real type.
- Inputs from outside the program (requests, files, a host's callbacks) used without validation.

### Commands
```
git grep -c -E '<unchecked-cast pattern>' -- '<source pathspec>'
git grep -c -E '<suppression pattern>' -- '<source pathspec>'
git grep -n -E '<strict-mode setting>' -- '<checker configuration file>'
```

### Evidence format
"Type and contract safety: 7/10. Strict checking is on in the checker configuration, 3 unchecked
casts in `src/api/client.ext`, zero suppressed diagnostics."

---

## State management

### What to look for
- Pass-through: how many layers a value passes through to reach the one that uses it.
- Global or shared mutable state: which stores, providers or singletons exist, and who writes them.
- Reusable state units (stores, view models, state hooks): how many, and whether logic is in them or
  spread through the user of the state.
- Derived values stored and synchronized by hand; expensive derivations without memoization.

### Evidence format
"State management: 6/10. 2 shared state providers; `userId` passes through 4 levels
(`Dashboard -> Sidebar -> UserMenu -> Avatar`); no memoization on the expensive selectors."

---

## Module architecture

### What to look for
- `apm metrics`: the files and functions over the limits, largest first.
- The largest source files, and how many exported units each holds.
- Imports that cross a layer in the wrong direction, against the profile's layer map when one is
  declared.

### Commands
```
apm metrics
git ls-files '<source pathspec>' | xargs wc -l | sort -rn | head -20
git grep -c -E '<exported-unit pattern>' -- '<source pathspec>'
```

`wc -l` counts raw lines, which is only a quick way to find the largest files; the scored numbers are
the lines of logic from `apm metrics`.

### Evidence format
"Module architecture: 5/10. `OrderForm.ext` is 480 lines of logic with 3 exported units; 8 of 22
modules are over the 200-line file limit."

---

## Entry points and routing

### What to look for
- The entry points: the main function, subcommands, request and message handlers, a host's
  callbacks. Whether there is one dispatch place, and whether the entry points only forward.
- Unknown commands, routes and messages: handled, or silently ignored.
- With a user interface: screens loaded on demand (lazy loading, dynamic loading, code splitting),
  nested layouts sharing a frame, not-found and error routes, breadcrumbs, prefetching.
- Without a user interface, the navigation half is N/A with that reason, and the entry points alone
  are scored.

### Evidence format
"Entry points and routing: 8/10. Every screen is loaded on demand, nested layouts under
`/dashboard/*`, a not-found catch-all is present, no breadcrumbs."

"Entry points and routing: 7/10 (navigation N/A, no user interface). One dispatch table in
`cli/handlers.ext` forwards every subcommand; an unknown subcommand prints usage and exits 2; 2
handlers still validate their input themselves."

---

## Styling and presentation

### What to look for
- Literal style values (colors, sizes, spacing) written inline where things are drawn.
- Style modules, stylesheets or a theme, and how many there are.
- Design tokens, and whether the code uses them consistently or mixes them with literals.
- UI-only: without a user interface, N/A with that reason.

### Commands
```
git grep -c -E '<inline-style pattern>' -- '<ui pathspec>'
git ls-files '<style-module pathspec>' | wc -l
```

### Evidence format
"Styling and presentation: 4/10. 47 inline style values, 3 style modules, no design tokens; the
color constants module is used inconsistently."

---

## Testing

### What to look for
- Test files against source modules.
- Test cases, and disabled or skipped tests.
- Integration and end-to-end tests, against unit tests and shallow tests that only run or render.
- Accessibility assertions, where there is a user interface.
- Whether tests arrived with the behavior: `git log --stat <base>..HEAD` shows whether each
  behavior commit carries its test.

### Commands
```
git ls-files '<test-file pathspec>' | wc -l
git grep -c -E '<test-case pattern>' -- '<test-file pathspec>'
git grep -c -E '<skip pattern>' -- '<test-file pathspec>'
git ls-files | grep -E '(^|/)(integration|e2e|end-to-end)/' | wc -l
```

### Evidence format
"Testing: 3/10. 4 test files for 22 modules, 12 test cases, all shallow; no integration or
end-to-end tests, no accessibility assertions."

---

## Error handling

### What to look for
- Boundaries that contain a failure (for a user interface, an error boundary around each route
  segment or screen).
- Calls to the outside world wrapped in failure handling, with the failure shown to the user or
  returned to the caller.
- Catch blocks that swallow an error; failures signaled by a sentinel value.
- Loading, error and empty states handled wherever data is shown.

### Evidence format
"Error handling: 6/10. A top-level error boundary exists, and the query layer handles errors, but 3
raw calls in `src/api/legacy.ext` have no error handling."

---

## External integration

### What to look for
- One adapter or wrapper per outside system, against raw calls spread through the code.
- Cancellation and timeouts: work stopped when the code waiting for it goes away.
- Retries, by hand or through a library.
- Types on responses, and validation of what comes back.
- Caching (including stale-while-revalidate), pagination, optimistic updates.

### Evidence format
"External integration: 7/10. One query client with typed responses on every endpoint, automatic
caching and cancellation, no retry configuration, no optimistic updates."

---

## Accessibility

### What to look for
- Accessible names and roles on controls.
- Semantic structure (main area, navigation, headings, lists, sections) rather than generic
  containers.
- Status conveyed by color alone, with no text or shape alternative.
- Keyboard navigation and visible focus, and tests of them.
- UI-only: without a user interface, N/A with that reason.

### Commands
```
git grep -c -E '<accessible-name pattern>' -- '<ui pathspec>'
git grep -c -E '<role pattern>' -- '<ui pathspec>'
git grep -c -E '<semantic-structure pattern>' -- '<ui pathspec>'
```

### Evidence format
"Accessibility: 5/10. 12 accessible labels; semantic main and navigation regions used; status badges
use color only, with no text alternative; no keyboard navigation tests."

---

## Code duplication

### What to look for
- Constants repeated across files.
- Copy-pasted units of the user interface or of logic.
- Duplicated helper functions.
- Shared patterns not extracted into a reusable unit, or one-off copies written although a shared
  unit exists.

### Commands
```
git grep -n -F '<a literal that should exist once>' -- '<source pathspec>'
git grep -n -E '<name of a helper> *\(' -- '<source pathspec>'
```

### Evidence format
"Code duplication: 6/10. The service base address is hardcoded in 4 files, `formatCurrency` is
duplicated in `OrderList.ext` and `Invoice.ext`, and a shared button exists but 3 one-off buttons
were written."

---

## Developer experience and maintainability

### What to look for
- A linter and a formatter, configured and passing.
- Pre-commit hooks.
- Import sorting rules and import path aliases.
- A continuous integration pipeline, and what it runs: the tests, the linter, `apm metrics`,
  `apm debt check`.
- Automatic fixing, consistent conventions, and documentation for a newcomer.

### Evidence format
"Developer experience and maintainability: 8/10. Linter and formatter configured, a pre-commit hook
runs them on staged files, path aliases for the source root; no continuous integration pipeline."

---

## Overall score weighting

The overall score is not an average. These dimensions weigh more because they compound:

| Dimension | Weight |
|-----------|--------|
| Type and contract safety | High |
| Module architecture | High |
| Testing | High |
| Error handling | Medium |
| State management | Medium |
| External integration | Medium |
| Accessibility | Medium |
| Code duplication | Medium |
| Entry points and routing | Low |
| Styling and presentation | Low |
| Developer experience and maintainability | Low |

A project with 9/10 type and contract safety, 9/10 testing and 4/10 styling is in better shape than
one with 9/10 styling, 4/10 type and contract safety and 4/10 testing. An N/A dimension is left out
of the overall; it counts neither for nor against.
