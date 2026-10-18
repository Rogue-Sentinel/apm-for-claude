# APM for Claude — Plan 2: The Standard — Implementation Plan

> **For agentic workers:** the manager builds this plan task by task. Each task is built test-first by one
> implementer, verified by the manager, and reviewed before the next task starts. Steps use checkbox
> (`- [ ]`) syntax for tracking.

**Goal:** The framework carries its own language-agnostic Clean Code and Clean Architecture standard as
plugin skills. A tested coverage inventory proves that no item of the user's previous standard is lost. A
stdlib metrics tool measures any project that has no checker of its own. A debt ratchet records a baseline
and fails whenever any debt number gets worse.

**Architecture:** The standard is Markdown skills under `skills/<name>/SKILL.md`, invoked as `apm:<name>`, with
`references/` files for the long catalogs. Tests check their structure, not their prose. The coverage
inventory is data (`standard/coverage.json`), validated by `scripts/apm/coverage.py` and rendered to
`docs/coverage.md`. Metrics are pure functions over source text (`metrics_*.py`), plus one tree walk that
uses `git ls-files`. The ratchet is a pure snapshot-and-compare module (`debt.py`), with thin I/O around it
for the baseline file and for project checkers. Everything is reached through new `apm` subcommands.

**Tech Stack:** Python 3.12+ (stdlib only at runtime: `ast`, `tokenize`, `re`, `subprocess`), pytest, git.

**Spec:** `docs/specs/2026-10-17-apm-for-claude-design.md` §8 (the standard), with §6.1's no-loss rule.

## Roadmap (this plan is 2 of 4)
1. **Foundation** (merged): plugin, agents, safety hooks, state and briefing, `apm setup`.
2. **The standard** (this plan): language-agnostic Clean Code and Clean Architecture skills, a coverage
   inventory against VirtualAirline and superpowers (spec §8.1), the default metrics tool, and the debt ratchet.
3. **Workflows:** init and audit, design conversation, planner, feature and bug paths, the merge gate,
   GitHub issues.
4. **Adoption:** install into VirtualAirline through the framework's own init.

**Boundary with Plan 3.** This plan supplies the *discipline*: what a good design conversation, plan, review
or debugging session is, as skills; the numbers and the ratchet check, as commands. Plan 3 supplies the
*orchestration*: when the manager runs each one, the GitHub issues, and the full merge gate that calls
`apm debt check` as its criterion 2. The process skills here are written so Plan 3 can point the manager's
workflows at them without rewriting them.

## Source material (read-only)
- `C:\Users\darby\source\repos\VirtualAirline Plugin for XP12\.claude\skills\`: the 21 vendored skills
  (helmedeiros/clean-code-skills `b9805c9`, MIT) with their `references/` and `examples/` files. Also
  `CLEAN-CODE-SKILLS.md`, and the domain skills `xp12-ui` and `ui-screen-structure`, which stay in the
  project and are not methodology.
- `...\.claude\commands\clean-code-audit.md` and `branch-review.md`.
- `...\CLAUDE.md`: the methodology sections (TDD, architecture rule, extract before you add, clean code,
  limits). Domain facts and project conventions stay in the project. Plan 3's audit inventories them into
  that project's profile as domain knowledge or declared overrides.
- `...\tools\check_clean_code.py`: the reference for "line of logic" and for the 15/200/7 numbers.
- `C:\Users\darby\.claude\plugins\cache\claude-plugins-official\superpowers\7.0.0\skills\`: the 15 superpowers skills.

The framework's skills are its own wording, written from these sources. Where a skill adapts substantial
material from the MIT-licensed set, `skills/CREDITS.md` names the source and carries its license notice.

## Global Constraints
- Everything from Plan 1 still holds: stdlib-only runtime, **≤ 15 lines of logic per function and ≤ 200
  per file**, a stated reason for 7+ public methods, test-first, no skipped tests, refactor and behavior in
  separate commits, American spelling.
- **The limits now have a definition the tool enforces.** A line of logic is a line that still holds code
  after comments, docstrings and preprocessor lines are removed, and that isn't only brackets, `;` and `,`.
  A test runs the framework's own metrics tool over `scripts/` and requires zero functions over 15 and
  zero files over 200.
- Skills are **language-agnostic**. A `SKILL.md` names no language, framework or project. Examples are
  pseudo-code. A test bans a fixed list of terms (`TypeScript`, `React`, `tsconfig`, `C++`, `XPLM`, `ImGui`,
  `X-Plane`, `VirtualAirline`, `superpowers:`). Language-specific evidence lives only in files named
  `references/*-by-language.md`.
- Every skill's frontmatter has `name` (equal to its directory) and a quoted `description` that starts
  with `"Use when`.
- Profile keys added by this plan live under one key, `standard`, so Plan 1's loader keeps them in `extra`
  without changing.
- Plugin version becomes `0.2.0` in the last task.

## Review Focus
1. **Lines of logic must agree with a hand count.** This covers Python docstrings, multi-line strings, comments
   that hold braces, `//` inside strings, and lone-bracket lines. Tests are in Tasks 1 to 3.
2. **The brace scanner must not mistake control blocks for functions** (`if`, `for`, `while`, `switch`,
   `catch`, `else if`, `do`, `try`), and must name a Go method with a receiver, an arrow function assigned
   to a variable, and an annotated Java method correctly. Tests are in Task 3.
3. **The ratchet must not be gamed.** The ways to try are: growing an already-over function, adding a
   new over-limit item, loosening a limit, editing the baseline, or a worker running `debt baseline`.
   A pure move must not count as new debt. Tests are in Tasks 5 and 6.
4. **No item can drop out of the coverage inventory unnoticed.** The test holds its own independent list of
   expected items, and `apm coverage --source` cross-checks the real source directories. Tests are in Task 13.

---

## File Structure

```
skills/<name>/SKILL.md               21 framework skills (list in Tasks 7–11), invoked as apm:<name>
skills/<name>/references/*.md        catalogs, checklists, briefs and before/after examples
skills/CREDITS.md                    sources and the MIT notice for adapted material
standard/coverage.json               the coverage inventory (data)
docs/coverage.md                     the coverage table, rendered from the inventory
scripts/apm/metrics_model.py         FunctionMetric, ClassMetric, FileMetric
scripts/apm/metrics_lang.py          language table, comment and string stripping, line counting
scripts/apm/metrics_python.py        Python files through ast and tokenize
scripts/apm/metrics_braces.py        brace-family function scanner
scripts/apm/metrics.py               file selection, Report, text and JSON rendering
scripts/apm/standard_config.py       Limits, MetricsConfig, DebtSource from profile["standard"]
scripts/apm/debt.py                  snapshot and compare (pure)
scripts/apm/debt_sources.py          numbers from a project's own checker
scripts/apm/debt_store.py            .apm/debt.json, and the baseline at a git ref
scripts/apm/coverage.py              load, check and render the inventory, and cross-check a source tree
scripts/apm/cli_standard.py          handlers for metrics, debt and coverage
tests/skill_helpers.py               shared frontmatter and section helpers for skill tests
tests/test_metrics_*.py, test_debt*.py, test_coverage.py, test_skills*.py
```

---

### Task 1: Languages and lines of logic

**Files:**
- Create: `scripts/apm/metrics_model.py`, `scripts/apm/metrics_lang.py`, `tests/test_metrics_lang.py`

**Interfaces:**
- Produces (`metrics_model.py`):
  - `@dataclass(frozen=True) class FunctionMetric: name: str; line: int; lines: int`
  - `@dataclass(frozen=True) class ClassMetric: name: str; line: int; public_methods: int`
  - `@dataclass(frozen=True) class FileMetric: path: str; language: str; lines: int; functions: tuple[FunctionMetric, ...] = (); classes: tuple[ClassMetric, ...] = (); functions_measured: bool = False; note: str = ""`
- Produces (`metrics_lang.py`):
  - `@dataclass(frozen=True) class Language: name: str; family: Literal["brace", "python", "plain"]; line_comments: tuple[str, ...]; block_comments: tuple[tuple[str, str], ...]; quotes: tuple[str, ...]; preprocessor: bool = False; raw_quotes: tuple[str, ...] = ()`
    (`raw_quotes` have no escapes: the Go backtick, and `"""` in Kotlin, Scala and C#. *Added after the Task 1 review.*)
  - `language_for(path: str) -> Language | None`, by lower-cased extension. The brace family covers
    `.c .h .cc .cpp .cxx .hpp .hh .cs .java .js .jsx .mjs .cjs .ts .tsx .go .rs .swift .kt .kts .scala .php .dart .m`
    (`preprocessor=True` for C, C++, C# and Objective-C; a backtick quote for JS, TS and Go). Python is
    `.py`. The plain family (file size only) covers `.sh .bash .ps1 .rb .lua .sql .pl .r`.
    Anything else gives `None`.
  - `strip_code(text: str, language: Language) -> str`: removes comments and the contents of string
    literals (the quotes stay), and preprocessor lines when `preprocessor`. **Every newline survives**, so
    line numbers are unchanged. A `\` escape inside a literal is honored (except in a raw quote). **A literal
    that spans lines is logic on every line it spans**, as in Python, so each spanned line keeps a placeholder
    quote and no brace from inside it. Known limits are listed in the module docstring.
  - `is_logic_line(line: str) -> bool`: non-blank, and not made only of `{ } ( ) [ ] ; ,` and whitespace.
  - `count_logic(stripped: str) -> int`
  - `measure_plain(path: str, text: str, language: Language) -> FileMetric`: file lines only, with `functions_measured=False`.

- [ ] **Step 1: Write the failing tests**
  - `test_language_for_known_and_unknown`: `src/a.TS` gives TypeScript in the brace family, `x.py` gives python, `run.sh` gives plain, `README.md` gives `None`.
  - `test_strip_removes_line_and_block_comments_keeping_newlines`: `"a(); // {\n/* x\n y */ b();\n"` strips to three lines, and the count is 2.
  - `test_brace_inside_string_is_not_code`: `'s = "{";'` keeps `s = "";`.
  - `test_escaped_quote_does_not_end_literal`: `'s = "a\\"{";'` strips to `s = "";`.
  - `test_preprocessor_lines_drop_only_when_flagged`: `#include <x>` is dropped for C++ and kept for a `#`-comment language as a comment.
  - `test_lone_brackets_are_not_logic` (parametrized): `"}"`, `"};"`, `"});"`, `"  ],"`, `")"` are not logic, while `"} else {"` and `"x"` are.
  - `test_measure_plain_counts_file_only`: a shell script with comments and blank lines.
- [ ] **Step 2: Run** `python -m pytest tests/test_metrics_lang.py -v`. Expected: FAIL (ImportError).
- [ ] **Step 3: Implement.** Model the scanner on VirtualAirline's `strip_source` (one pass, an index, a
  small helper per construct), generalized over the `Language` fields. Keep each function at or under 15 lines.
- [ ] **Step 4: Run** the tests. Expected: PASS.
- [ ] **Step 5: Commit** `"Count lines of logic in any listed language"`.

### Task 2: Python, measured exactly

**Files:**
- Create: `scripts/apm/metrics_python.py`, `tests/test_metrics_python.py`

**Interfaces:**
- Consumes: `FileMetric`, `FunctionMetric`, `ClassMetric`, `is_logic_line` (Task 1).
- Produces: `measure_python(path: str, text: str) -> FileMetric`.
  - Logic lines are lines that hold a token other than COMMENT, NL, NEWLINE, INDENT, DEDENT or ENDMARKER
    (from `tokenize`). Docstring lines (a module, class or function whose first statement is a string
    constant) are removed, and so are lone-bracket lines.
  - Every `def` and `async def` is a `FunctionMetric`, named by its qualified path (`Class.method`,
    `outer.inner`). Its `line` is the `def` line. Its `lines` are the logic lines from the first body
    statement to `end_lineno`, without the docstring. A nested function's lines count in its parent too.
  - Every class is a `ClassMetric` whose `public_methods` counts the `def`s directly in its body whose names
    don't start with `_`.
  - A file that doesn't parse gives file lines from `tokenize` where possible (otherwise from
    `measure_plain` with `#` comments), `functions_measured=False`, and `note="syntax error: ..."`.

- [ ] **Step 1: Write the failing tests**
  - `test_docstring_and_comments_are_not_logic`: a function with a three-line docstring, a comment and two statements has `lines == 2`.
  - `test_multiline_string_value_is_logic`: a non-docstring triple-quoted assignment spanning 3 lines counts as 3.
  - `test_methods_are_qualified_and_nested_counted_in_parent`
  - `test_public_method_count_skips_private_and_dunder`: a class with `__init__`, `_helper`, `a`, `b` has `public_methods == 2`.
  - `test_decorator_and_signature_lines_are_not_body`: a decorated function whose signature spans 3 lines and whose body is 1 line has `lines == 1`.
  - `test_syntax_error_is_reported_not_raised`
  - `test_matches_a_hand_count`: a committed fixture `tests/fixtures/metrics/sample.py` with a hand count written in a comment at its top (file lines and each function), asserted exactly.
- [ ] **Step 2: Run** `python -m pytest tests/test_metrics_python.py -v`. Expected: FAIL.
- [ ] **Step 3: Implement.**
- [ ] **Step 4: Run** the tests. Expected: PASS.
- [ ] **Step 5: Commit** `"Measure Python functions and classes through the ast"`.

### Task 3: Functions in brace languages

**Files:**
- Create: `scripts/apm/metrics_braces.py`, `tests/test_metrics_braces.py`, `tests/fixtures/metrics/` (one small file per language below)

**Interfaces:**
- Consumes: `strip_code`, `count_logic`, `Language` (Task 1); the model types.
- Produces: `measure_braces(path: str, text: str, language: Language) -> FileMetric` with `functions_measured=True`
  and no classes (the 7+ public-method flag is reviewer judgment for brace languages).
  - It scans the stripped text with a scope stack. A `{` opens a scope classified from the *head*, which
    is the text since the last `;`, `{` or `}` in the enclosing scope. Leading annotations and attributes
    (`@Name(...)`, `[...]`, `[[...]]`) are dropped first, and so are template and generic arguments (`<...>`).
  - **Function** when the head holds a parenthesized group, the identifier before the first group isn't a
    control keyword (`if for while switch catch foreach using lock synchronized with when match do try
    else`), and what follows the last group is empty, `=>`, a return-type tail (`-> T`, `: T`, or a bare
    type, as in Go), or qualifiers (`const noexcept override final throws ... async where ...`).
  - **Name:** the identifier (with any `Type::` qualifier) before the first parenthesized group that is
    preceded by a non-keyword identifier. For an arrow function or lambda with no such group, the name is
    the variable before `=`. Otherwise it's `<anonymous>`.
  - *Amended after the Task 3 review:* a head is only the **last statement** before the `{`. A newline at
    paren depth 0 also ends a statement unless the statement plainly continues: the next line opens with
    `{`, `.`, `)`, `->`, `:`, `=>`, `throws`, `where` and the like, or the line ends with an operator, `,` or
    `(`. Without this, a Go `import (...)` block, a Kotlin `val`, or a JS line with no semicolon would leak
    into the next function's head. Allman braces (`)\n{`) and multi-line signatures still work.
  - *Amended after the Task 3 review:* a **callback passed as a call argument** at file level, or inside
    another such callback, is a function **named after its callee** (`describe`, `it`, `app.get`). Its
    lines leave out the callbacks nested in it as call arguments, and each of those is reported on its own.
    So a test suite is many small functions, not one large one.
  - Inside a named function, nested braces are part of its body: a lambda's lines count in its parent, and it
    isn't reported on its own. Every other scope (class, struct, namespace, impl, object literal, control
    block at file level) is declarative, so the functions inside it are found.
  - `lines` is `count_logic` of the body between the braces.
  - An unbalanced file gives `functions_measured=False` and `note="unbalanced braces"`, but still a file count.
  - **Known limit, documented in the module docstring:** a C++ constructor whose initializer list uses
    braces (`: x_{1} {`) is misread. A project that needs exactness declares its own checker (Task 6).

- [ ] **Step 1: Write the failing tests** (each asserts `[(f.name, f.lines) for f in metric.functions]`)
  - C: `int add(int a, int b) {\n  return a + b;\n}` gives `[("add", 1)]`.
  - C++: `class A {\npublic:\n  void f() const {\n    x();\n  }\n};` and `A::A() : x_(1) {\n y();\n}` give `f` and `A::A`.
  - Java: `@Override\npublic void run() throws IOException {\n a();\n b();\n}` gives `[("run", 2)]`.
  - Go: `func (s *Server) Start(ctx context.Context) error {\n return nil\n}` gives `[("Start", 1)]`.
  - Rust: `impl Foo {\n  fn new() -> Self {\n    Foo {}\n  }\n}` gives `[("new", 1)]`.
  - JS: `function load(url) {...}` gives `load`, and `const handler = async (e) => {...}` gives `handler`.
    A `.map((x) => {...})` inside `load` isn't reported separately, and its lines count in `load`.
  - TS: `async fetch(id: string): Promise<User> {` inside a class gives `fetch`.
  - Kotlin `fun area(): Double {` and Swift `func f(x: Int) -> Int {` give `area` and `f`.
  - Control blocks (parametrized, at file level and inside a class method): `if (x) {`, `} else if (y) {`,
    `for (;;) {`, `while (a) {`, `switch (k) {`, `catch (e) {`, `do {`, `try {` are never functions.
  - `test_braces_in_strings_and_comments_are_ignored`
  - `test_unbalanced_file_is_noted`
- [ ] **Step 2: Run** `python -m pytest tests/test_metrics_braces.py -v`. Expected: FAIL.
- [ ] **Step 3: Implement.** Keep the classifier, the namer and the scope walk as separate small functions
  (one file, under 200 lines; split the head helpers into `metrics_heads.py` if it doesn't fit).
- [ ] **Step 4: Run** the tests. Expected: PASS.
- [ ] **Step 5: Commit** `"Find functions in brace languages without a compiler"`.

*Tasks 2 and 3 touch disjoint files and may run in parallel.*

### Task 4: Measuring a project, and `apm metrics`

**Files:**
- Create: `scripts/apm/metrics.py`, `scripts/apm/standard_config.py`, `scripts/apm/cli_standard.py`, `tests/test_metrics.py`, `tests/test_standard_config.py`, `tests/test_cli_metrics.py`, `tests/test_own_limits.py`
- Modify: `scripts/apm/cli_parser.py`, `scripts/apm_cli.py`, `scripts/apm/cli_handlers.py` (merge in the new handlers)

**Interfaces:**
- Consumes: Tasks 1 to 3; `Profile.extra` (Plan 1); `glob_matches` and `matches_any` from `guard_paths`.
- Produces (`standard_config.py`):
  - `@dataclass(frozen=True) class Limits: function: int = 15; file: int = 200; public_methods: int = 7`
  - `DEFAULT_EXCLUDES = ("**/node_modules/**", "**/vendor/**", "**/third_party/**", "**/dist/**", "**/build/**", "**/*.min.js", "**/*.generated.*", ".apm/**")`
  - `@dataclass(frozen=True) class MetricsConfig: include: tuple[str, ...] = (); exclude: tuple[str, ...] = DEFAULT_EXCLUDES; builtin: bool = True`.
    An empty `include` means every file with a known language.
  - `@dataclass(frozen=True) class DebtSource: name: str; command: str; numbers: Mapping[str, str]` (metric name to regex with one group)
  - `@dataclass(frozen=True) class Standard: limits: Limits; metrics: MetricsConfig; sources: tuple[DebtSource, ...]; adr_dir: str = "docs/adr/"; review_patterns: Mapping[str, tuple[str, ...]] = {}`
    (`adr_dir` and `review_patterns` are named by the `adr` and `branch-review` skills. *Added after the Task 7 review.*)
    It also has `ui: bool | None = None`: whether the project has a user interface. `None` means the reviewer
    decides from the code. `review_patterns` maps a scorecard dimension name to grep patterns. *Added after Task 9.*
    It also has `layers: tuple[Mapping[str, Any], ...] = ()`, the layer map that the `clean-architecture` skill
    reads. Each entry is `{"name", "paths": [globs], "may_import": [layer names]}`. The loader checks that shape. *Added after Task 8.*
    `may_import` may also hold two reserved names: `"outside"` (libraries beyond the language's standard
    library) and `"*"` (every layer, as a test layer needs). A file whose path matches two layers' globs is
    an error in the map. The loader accepts both reserved names and rejects an unknown layer name.
  - `load_standard(profile: Profile | None) -> Standard`. It reads `profile.extra["standard"]`
    (`limits`, `metrics`, `debt_sources`, `adr_dir`, `review_patterns`, `ui`, `layers`; `review_patterns` is
    checked for shape only, and an unknown dimension name is left for the review to report), uses the defaults when there's no profile or no key, and raises
    `ProfileError` for a non-positive limit, a non-string glob, a source without a name or command, or a
    regex that doesn't compile or doesn't have exactly one group. A profile's `metrics.exclude` replaces the
    defaults, and a profile may add to them with `metrics.extra_exclude`.
- Produces (`metrics.py`):
  - `measure_text(path: str, text: str) -> FileMetric | None`: dispatches by language family.
  - `tracked_files(root: Path) -> list[str]`: `git ls-files --cached --others --exclude-standard`, POSIX paths, sorted.
  - `select_files(paths: Sequence[str], config: MetricsConfig) -> list[str]`
  - `@dataclass(frozen=True) class Report: files: tuple[FileMetric, ...]`, with `over_functions(limits) -> list[tuple[str, FunctionMetric]]`,
    `over_files(limits) -> list[FileMetric]`, `wide_classes(limits) -> list[tuple[str, ClassMetric]]` (≥ `public_methods`),
    and `unmeasured() -> list[FileMetric]` (files whose functions couldn't be measured, with their note). Each list is sorted largest first.
  - `measure_tree(root: Path, config: MetricsConfig, paths: Sequence[str] | None = None) -> Report`
  - `render_text(report: Report, limits: Limits) -> str`: counts of over-limit functions and files, each
    item as `path:line name -- N lines`, the review flags for wide classes, and the unmeasured files, in
    the same spirit as VirtualAirline's checker output.
  - `report_json(report: Report, limits: Limits) -> dict`: `{"limits": ..., "files": [...]}` with every measured number.
- CLI: `apm metrics [--json] [PATH ...]` works in **any git repository** (the Plan 3 audit runs it before
  init). It uses the profile's `standard` when the project is initialized, and the defaults otherwise.
  It always exits 0, because the ratchet is the gate, not this. `apm_cli._run` gains a per-subcommand
  requirement table: `none`, `repo`, `profile`, or `state`. Plan 1's existing behavior for each existing
  subcommand stays the same.

- [ ] **Step 1: Write the failing tests**
  - `test_standard_defaults_without_profile`, `test_profile_limits_override`, `test_bad_limit_rejected`,
    `test_source_regex_needs_one_group`, `test_extra_exclude_adds_to_defaults`.
  - `test_select_files_include_and_exclude`: `src/a.py` and `src/vendor/b.js` with `include=("src/**",)` select only `src/a.py`. An unknown extension is never selected.
  - `test_measure_tree_uses_tracked_and_untracked_not_ignored` (`git_repo` with a `.gitignore`d file).
  - `test_report_over_limit_lists_are_sorted_largest_first`
  - `test_cli_metrics_outside_apm_project` prints the counts and exits 0. `test_cli_metrics_json_round_trips`.
  - `test_framework_meets_its_own_limits`: `measure_tree(repo_root, MetricsConfig(include=("scripts/**",)))`
    has no function over 15, no file over 200, and nothing unmeasured.
- [ ] **Step 2: Run** `python -m pytest tests/test_standard_config.py tests/test_metrics.py tests/test_cli_metrics.py tests/test_own_limits.py -v`. Expected: FAIL.
- [ ] **Step 3: Implement.** The new handlers live in `cli_standard.py` and are merged into `HANDLERS`, so `cli_handlers.py` stays small.
- [ ] **Step 4: Run** the whole suite. Expected: all PASS.
- [ ] **Step 5: Commit** `"Measure any project against the limits with apm metrics"`.

### Task 5: The debt snapshot and the comparison

**Files:**
- Create: `scripts/apm/debt.py`, `tests/test_debt.py`

**Interfaces:**
- Consumes: `Report`, `Limits` (Task 4).
- Produces (pure; plain dicts so the file stays diff-friendly):
  - `snapshot(report: Report, limits: Limits, sources: Mapping[str, Mapping[str, int]] | None = None) -> dict`:
    ```
    {"version": 1, "limits": {"function": 15, "file": 200, "public_methods": 7},
     "totals": {"long_functions": n, "long_files": n, "wide_classes": n,
                "excess_function_lines": n, "excess_file_lines": n,
                "unmeasured_files": n},   # syntax errors and unbalanced files; added after the Task 4 review
     "unmeasured": ["<path>", ...],    # a file that stops parsing hides its debt, so this may only shrink
     "functions": {"<path>::<name>": lines, ...},   # only items over the limit
     "files": {"<path>": lines, ...},
     "classes": {"<path>::<name>": public_methods, ...},
     "sources": {"<source>": {"<metric>": n}},
     "accepted": []}
    ```
    Duplicate function names in one file get `#2`, `#3`, … in source order.
  - `@dataclass(frozen=True) class Comparison: regressions: tuple[str, ...]; improvements: tuple[str, ...]`, with property `worse -> bool`.
  - `compare(base: dict, current: dict) -> Comparison`. A regression is any of the following:
    - a total that rose;
    - an item in both whose number rose (*"grew: path::name 18 → 21"*);
    - a new item (*"new over-limit function: …"*), unless it's a **move**: an item that left the base
      (or shrank under the limit) matched by the same bare name (function or class) or the same file name
      (file), with a number no larger. A move is reported as an improvement-neutral note;
    - a source metric that rose, or a source metric that disappeared;
    - a limit that is looser than the base's (*"limit loosened: function 15 → 20"*).
    Improvements are items that shrank or left, and totals that fell.
  - `accept(new: dict, previous: dict | None, reason: str, now: datetime) -> dict`: `new` with
    `accepted = previous.accepted + [{"reason": reason, "at": ISO-8601 UTC}]`. Without a reason it carries
    `previous.accepted` forward unchanged.

- [ ] **Step 1: Write the failing tests** (snapshots built from small hand-made `Report`s)
  - `test_snapshot_lists_only_over_limit_items_and_totals`
  - `test_identical_snapshots_have_no_regressions`
  - `test_growing_an_over_limit_function_is_a_regression`: 18 lines to 19.
  - `test_new_over_limit_function_is_a_regression`
  - `test_pure_move_to_another_file_is_not_a_regression`: `a.py::load` 30 moves to `b.py::load` 30.
  - `test_reordering_same_named_functions_is_not_a_regression`: `it` 20 and `it#2` 25 swap places
    (added after the Task 3 review).
  - `test_move_that_grows_is_a_regression`: 30 moves to 31.
  - `test_splitting_a_file_into_two_over_limit_files_is_a_regression` (totals `long_files` rose). The skill
    and the manager prompt say what to do: split further, or ask the user.
  - `test_loosened_limit_is_a_regression`, `test_source_metric_rise_and_disappearance_are_regressions`
  - `test_shrinking_is_an_improvement_and_not_a_regression`
  - `test_accept_appends_reason_and_keeps_history`
- [ ] **Step 2: Run** `python -m pytest tests/test_debt.py -v`. Expected: FAIL.
- [ ] **Step 3: Implement.** One small comparison per section, and a shared `_match_moves` helper.
- [ ] **Step 4: Run** the tests. Expected: PASS.
- [ ] **Step 5: Commit** `"Snapshot debt and find anything that got worse"`.

### Task 6: The ratchet: baseline, check, project checkers and the guard

**Files:**
- Create: `scripts/apm/debt_sources.py`, `scripts/apm/debt_store.py`, `tests/test_debt_sources.py`, `tests/test_debt_store.py`, `tests/test_cli_debt.py`
- Modify: `scripts/apm/cli_standard.py`, `scripts/apm/cli_parser.py`, `scripts/apm/guard.py`, `scripts/apm/guard_cli.py`, `scripts/apm/profile.py`, `tests/test_guard.py` (or a new `tests/test_guard_debt.py`)

**Interfaces:**
- Consumes: `snapshot`, `compare`, `accept` (Task 5); `measure_tree`, `load_standard` (Task 4).
- Produces:
  - `debt_sources.run_source(source: DebtSource, root: Path, run=subprocess.run) -> dict[str, int]`. It runs
    `source.command` with `shell=True` in `root` and applies each regex to stdout. The exit code is
    ignored, because checkers exit non-zero when they find debt. A regex that doesn't match raises
    `DebtError(f"{source.name}: no match for {metric}")`.
  - `debt_store.DEBT_FILE = ".apm/debt.json"`, `class DebtError(Exception)`.
  - `load_baseline(path: Path) -> dict | None` (`None` if the file is missing, `DebtError` if it's corrupt),
    and `write_baseline(path: Path, snapshot: dict) -> None` (indent 2, sorted keys, trailing newline).
  - `baseline_at(root: Path, ref: str) -> dict | None`: `git show <ref>:.apm/debt.json`. `None` when the
    file isn't in that ref. `DebtError` when the ref doesn't exist.
  - `current_snapshot(root: Path, standard: Standard) -> dict`: the built-in metrics (when
    `metrics.builtin`) plus every declared source.
  - CLI (needs an initialized project, but not the state worktree):
    - `apm debt baseline [--accept REASON]`: writes `.apm/debt.json` from the current numbers. If a
      baseline exists and the current numbers are worse, it refuses (exit 1, listing each regression)
      unless `--accept` is given. Otherwise it writes the file, so the same command **tightens** the
      ratchet after debt is paid down.
    - `apm debt check [--base REF]` (default `main`): exit 2 if there's no working-tree baseline. Exit 1
      if the current numbers are worse than the working-tree baseline, **or** if the working-tree baseline
      is worse than the one at `REF` and the working tree records no acceptance that `REF` lacks (a
      baseline can only be loosened through `--accept`). Otherwise exit 0. It prints the regressions, then
      the improvements, then a hint to run `debt baseline` when it would tighten.
  - Guard: `profile.WORKER_PROTECTED = (".apm/**",)`. Workers may never write the profile or the baseline,
    by tool or by command. `decide` adds it to the globs only when `agent_id` is set. The worker-mutation
    pattern also denies `debt baseline`. `debt check`, `metrics` and `coverage` stay allowed for workers.
    `guard_cli.SUBCOMMANDS` gains `metrics`, `debt` and `coverage`.

- [ ] **Step 1: Write the failing tests**
  - `test_run_source_reads_numbers_ignoring_exit_code`: an injected `run` returning exit 1 and VirtualAirline-style output `"Functions over 15 lines of logic: 41 of 900"` gives `{"long_functions": 41}`.
  - `test_run_source_no_match_raises`
  - `test_baseline_at_ref_missing_file_is_none`, `test_baseline_at_unknown_ref_raises`, `test_corrupt_baseline_raises`
  - In an initialized `git_repo` with a Python file holding a 20-line function:
    - `test_debt_baseline_then_check_passes`
    - `test_check_fails_after_growing_the_function`: exit 1, and the output names the function and `20 → 21`.
    - `test_baseline_refuses_worse_without_accept`, then `test_baseline_with_accept_records_reason`
    - `test_baseline_tightens_after_shrinking`: shrink to 10 lines, then `debt baseline`, then the file has no functions.
    - `test_check_fails_when_branch_loosened_baseline_without_acceptance`: commit the baseline on `main`, branch, hand-edit `.apm/debt.json` to raise a number, run `debt check` and get exit 1.
    - `test_check_passes_after_recorded_acceptance_on_branch`
    - `test_check_without_baseline_exits_2`
  - Guard: `test_worker_cannot_run_debt_baseline` (deny), `test_worker_may_run_debt_check_and_metrics` (none),
    `test_worker_cannot_write_apm_files` (Write `.apm/debt.json` and `.apm/profile.json` give deny),
    `test_main_session_debt_baseline_is_exempt_cli_call` (none).
- [ ] **Step 2: Run** the new test files. Expected: FAIL.
- [ ] **Step 3: Implement**, and wire `debt` into the parser and handlers.
- [ ] **Step 4: Run** the whole suite. Expected: all PASS (Plan 1's guard tests included).
- [ ] **Step 5: Commit** `"Ratchet debt: a baseline that only tightens, and a check that fails on anything worse"`.

---

**The skills (Tasks 7–11).** Each skill is written from the sources named in its task. The implementer reads
every named source file in full before writing, and carries over every rule, checklist item, warning and
worked example in its own words, language-agnostic, with pseudo-code examples. Coverage (Task 13) checks
each source item against the headings named below, so **every heading listed is required, exactly as
written.** More sections are welcome. Each skill opens with when it applies and its core rule, and closes
with common mistakes. Each `references/` file is linked from its `SKILL.md`. *Made exact by Task 7's
harness:* the first `##` is `## When this applies`, the second is `## The core rule`, and the last is
`## Common mistakes`. Every file in a skill directory is linked from its `SKILL.md`. A refactoring done
under the boy scout rule still goes in its own commit.

### Task 7: Skill tests, and the code-level Clean Code skills

**Files:**
- Create: `tests/skill_helpers.py`, `tests/test_skills.py`, `tests/test_skills_clean_code.py`, `skills/CREDITS.md`
- Create: `skills/clean-code/`, `skills/code-smells/`, `skills/refactoring/`, `skills/test-first/`, `skills/adr/` (each `SKILL.md` plus `references/`)

**Interfaces:**
- Produces (`skill_helpers.py`): `SKILLS_DIR`, `parse_skill(name) -> tuple[dict[str, str], str]`
  (the same frontmatter rules as Plan 1's agent tests), `sections(body) -> list[str]` (every `#`-heading line),
  and `assert_sections(name, required: Sequence[str])`.
- Produces (`test_skills.py`, over **every** `skills/*/SKILL.md`, so later tasks are checked automatically):
  the name matches the directory; the description is quoted and starts with `"Use when`; the body has an
  H1; no banned term appears in a `SKILL.md`; every relative link resolves; no British spelling from a fixed
  list (`colour behaviour favour centre analyse organise recognise prioritise initialise normalise catalogue judgement`)
  appears in any file under `skills/`; `CREDITS.md` names `helmedeiros/clean-code-skills` and carries the MIT notice.

**Skills and required headings:**
- `clean-code`: when you touch a file, and for the limits. Sources: `clean-code-boy-scout-rule` (+ checklist),
  `refactor-rename/references/naming-conventions.md`, the VirtualAirline `CLAUDE.md` "Clean code is the
  working standard" section and `check_clean_code.py`'s docstring.
  `## The limits`, `## Counting lines of logic`, `## Debt never grows`, `## The boy scout rule`, `## Meaningful names`,
  `## Functions do one thing`. References: `improvement-checklist.md`, `naming-conventions.md`.
  It explains `apm metrics` and the profile's override of the limits.
- `code-smells`: for reviews and audits. Source: `clean-code-detect-smells` (+ `smell-catalog.md`).
  `## Finding smells`, `## Severity`, `## Reporting a smell`. Reference `smell-catalog.md` keeps one `##`
  section per category of the source catalog, and every smell it lists.
- `refactoring`: when a function is over a limit, or a change touches debt. Sources: `refactor-extract-method`,
  `refactor-rename`, `refactor-replace-conditional-with-polymorphism` (each + reference/examples), and
  `CLAUDE.md` "Extract before you add".
  `## Extract before you add`, `## Refactor and behavior never share a commit`, `## Logic does not move sideways`,
  `## Extract method`, `## Rename`, `## Replace conditional with polymorphism`, `## Splitting a file`
  (a split must land each part under the file limit, or the debt ratchet fails it, so split further or raise it as a decision).
  References: `extraction-heuristics.md`, `polymorphism-before-after.md`.
- `test-first`: before any new behavior or fix. Sources: `tdd-test-first`, `tdd-red-green-refactor`,
  `tdd-arrange-act-assert` (each + reference/examples), superpowers `test-driven-development`
  (+ `writing-good-tests.md`), and `CLAUDE.md` "Test-driven development is mandatory".
  `## Test first`, `## Red, green, refactor`, `## Arrange, act, assert`, `## A bug fix starts with a failing test`,
  `## No test skips`, `## No test waits on a person`, `## Never weaken a test`, `## Writing good tests`.
  References: `cycle-steps.md`, `test-first-checklist.md`, `aaa-patterns.md`, `writing-good-tests.md`.
- `adr`: when a decision is made that a later reader would question. Sources: the VirtualAirline ADR practice
  (`docs/adr/`, e.g. ADR-0037 and ADR-0038, read for form only) and `CLAUDE.md`'s "a plan's promised
  documents are acceptance criteria". `## When a decision needs an ADR`, `## Writing one`, `## Superseding one`,
  `## Promised ADRs are acceptance criteria`. Reference `adr-template.md`. The directory comes from the
  profile's `standard.adr_dir` (default `docs/adr/`).

- [ ] **Step 1: Write** `skill_helpers.py`, `test_skills.py` and `test_skills_clean_code.py` (`assert_sections` for the five skills).
- [ ] **Step 2: Run** `python -m pytest tests/test_skills.py tests/test_skills_clean_code.py -v`. Expected: FAIL (no skills).
- [ ] **Step 3: Write the five skills** and `CREDITS.md`.
- [ ] **Step 4: Run** the tests. Expected: PASS.
- [ ] **Step 5: Commit** `"Carry the code-level Clean Code standard as skills"`.

### Task 8: Design and architecture skills

**Files:**
- Create: `tests/test_skills_design.py`; `skills/solid/`, `skills/object-design/`, `skills/functional-core/`, `skills/clean-architecture/`

**Skills and required headings:**
- `solid`: when adding or changing a type or module. Sources: the five `solid-*` skills (+ references and examples).
  `## Single responsibility`, `## Open-closed`, `## Liskov substitution`, `## Interface segregation`,
  `## Dependency inversion`. References: `srp-indicators.md`, `ocp-strategies.md`, `lsp-violations.md`,
  `isp-patterns.md`, `dip-patterns.md`.
- `object-design`: when designing a type's surface. Sources: `oop-encapsulation`, `oop-composition-over-inheritance`
  (+ checklist and examples), and the 7+ public-method rule. `## Encapsulation`, `## Composition over inheritance`,
  `## Seven or more public methods`. References: `encapsulation-checklist.md`, `composition-patterns.md`.
- `functional-core`: for state, side effects, absence and failure. Sources: `fp-pure-functions`,
  `fp-higher-order-functions`, `fp-error-handling` (+ references and examples). `## Pure functions`,
  `## Higher-order functions`, `## Absence and failure are values`, `## Time and randomness are parameters`.
  References: `purity-rules.md`, `hof-patterns.md`, `result-and-option.md`.
- `clean-architecture`: when crossing a layer or adding a dependency. Sources: `hexagonal-ports-adapters`,
  `hexagonal-domain-isolation` (+ references), and `CLAUDE.md` "Architecture rule that makes TDD possible"
  (generalized: frameworks and I/O only at the edges, so the core is tested without them).
  `## The dependency rule`, `## Ports and adapters`, `## Domain isolation`, `## Testing at the edges`,
  `## The layer map` (the profile declares layers and their allowed direction, and the reviewer checks imports against it).
  References: `port-adapter-anatomy.md`, `anti-corruption-layer.md`.

- [ ] **Step 1: Write** `tests/test_skills_design.py`. **Step 2: Run** it. Expected: FAIL.
- [ ] **Step 3: Write the skills.** **Step 4: Run** `tests/test_skills.py` and `tests/test_skills_design.py`. Expected: PASS.
- [ ] **Step 5: Commit** `"Carry SOLID, object design, a functional core and Clean Architecture as skills"`.

### Task 9: The review scorecard and the audit

**Files:**
- Create: `tests/test_skills_review.py`; `skills/branch-review/`, `skills/clean-code-audit/`

**Skills and required headings:**
- `branch-review`: for a scored review of a branch against its base. Sources: VirtualAirline `branch-review`
  skill (+ `scoring-evidence-guide.md`) and `commands/branch-review.md`. The TypeScript and React checks
  become language-neutral dimensions, and the per-language evidence moves to `references/evidence-by-language.md`
  (TypeScript, Python, C++, C#, Java, Go, and Rust at least). A project adds its own patterns in
  `standard.review_patterns`. UI-only dimensions are scored **N/A with a reason** when the profile declares no UI.
  `## Gather evidence`, `## The scorecard`, then one `###` per dimension, all eleven:
  `### Type and contract safety`, `### State management`, `### Module architecture`, `### Entry points and routing`,
  `### Styling and presentation`, `### Testing`, `### Error handling`, `### External integration`,
  `### Accessibility`, `### Code duplication`, `### Developer experience and maintainability`;
  `## Previous reviews` (the `BRANCH_REVIEW.md` progression column), `## Report`, `## Scoring honestly`.
  The evidence includes `apm metrics` and `apm debt check`. References: `scoring-evidence-guide.md`, `evidence-by-language.md`.
- `clean-code-audit`: a whole-codebase audit, used by the auditor at init. Source: `commands/clean-code-audit.md`.
  `## Scan`, `## Measure` (`apm metrics` and the profile's checkers, replacing the source's "more than 20 lines"
  with the profile's limits), `### Test-first`, `### Refactoring`, `### SOLID`, `### Object design`,
  `### Functional core`, `### Architecture`, `### Hygiene`, `## Report format` (the source's summary,
  per-category scores and findings, and top 5 actions), `## Priorities`.

- [ ] Steps as in Task 8. Commit `"Score a branch and audit a codebase without language-specific checks"`.

### Task 10: Process skills: designing, planning and building

**Files:**
- Create: `tests/test_skills_process.py`; `skills/design-first/`, `skills/writing-plans/`, `skills/executing-plans/`, `skills/parallel-dispatch/`, `skills/worktrees/`, `skills/finishing-a-branch/`

**Skills and required headings** (each adapted to the framework's roles: the manager orchestrates, workers report,
the user is reached only through the manager, and the guard and its approvals are respected):
- `design-first` ← superpowers `brainstorming` (+ `builder-check-prompt.md`). `## Nothing is built before an approved design`,
  `## One question at a time`, `## Goals, non-goals and anti-goals`, `## Approaches and tradeoffs`, `## The design document`,
  `## The builder check`, `## Splitting into issues`. Reference: `builder-check-brief.md`.
- `writing-plans` ← superpowers `writing-plans`, plus `CLAUDE.md`'s structural-constraints rules, and this
  repo's two plans as the house style. `## Before writing`, `## The plan header`, `## File structure`, `## Tasks`,
  `## Interfaces between tasks`, `## Structural acceptance criteria`, `## Extract before you add`,
  `## Allowlisted actions`, `## Review focus`, `## Self-review`.
- `executing-plans` ← superpowers `subagent-driven-development` (+ `implementer-prompt.md`, `task-reviewer-prompt.md`,
  `re-review-prompt.md`) and `executing-plans`. `## One task at a time`, `## Briefing a worker`,
  `## Verify it yourself`, `## Review after every task`, `## Re-review after fixes`, `## Recording each task`,
  `## When to stop and ask`. References: `implementer-brief.md`, `reviewer-brief.md`, `re-review-brief.md`.
- `parallel-dispatch` ← superpowers `dispatching-parallel-agents`. `## When work can run in parallel`,
  `## Disjoint files only`, `## The worker cap`, `## Writing each brief`, `## Integrating the results`.
- `worktrees` ← superpowers `using-git-worktrees`. `## Every builder works in its own worktree`, `## Creating one`,
  `## Never remove a worktree yourself`, `## Integrating a worktree branch`.
- `finishing-a-branch` ← superpowers `finishing-a-development-branch`. `## Merge main in first`, `## Verify everything`,
  `## The debt check`, `## The pull request`, `## The project's merge style`, `## Never discard work`.

- [ ] Steps as in Task 8. Commit `"Carry the design, planning and build process as skills"`.

### Task 11: Process skills: debugging, verifying, reviewing and skills

**Files:**
- Create: `tests/test_skills_quality.py`; `skills/systematic-debugging/`, `skills/verification/`, `skills/code-review/`, `skills/writing-skills/`, `skills/session-diagnosis/`

**Skills and required headings:**
- `systematic-debugging` ← superpowers `systematic-debugging` (+ `root-cause-tracing.md`, `defense-in-depth.md`,
  `condition-based-waiting.md`), plus spec decision 12. `## Root cause first`, `## Reproduce it as a failing test`,
  `## Trace backward to the source`, `## Fix the cause, then the instruction behind it`, `## After three failed fixes`,
  `## Defense in depth`, `## Waiting on conditions, not time`. References: `root-cause-tracing.md`,
  `defense-in-depth.md`, `condition-based-waiting.md`.
- `verification` ← superpowers `verification-before-completion`, and `CLAUDE.md` "Report results honestly".
  `## Evidence before claims`, `## What counts as evidence`, `## Honest reporting`, `## Red flags`.
- `code-review` ← superpowers `requesting-code-review` (+ `code-reviewer.md`) and `receiving-code-review`.
  `## Requesting a review`, `## What the reviewer is given`, `## Receiving a review`, `## Verify before you agree`,
  `## Pushing back`, `## No performative agreement`. Reference: `reviewer-checklist.md`.
- `writing-skills` ← superpowers `writing-skills` (+ `testing-skills-with-subagents.md`, `anthropic-best-practices.md`,
  `persuasion-principles.md`). It covers writing the framework's own skills **and a project's domain skills**
  (such as a UI-look skill), which the framework keeps rather than replaces. `## A skill is tested like code`,
  `## The description says when`, `## Structure`, `## Domain skills belong to the project`, `## Testing with subagents`.
  References: `testing-skills-with-subagents.md`, `best-practices.md`.
- `session-diagnosis` ← superpowers `diagnosing-superpowers`, retargeted: what went wrong in an APM session,
  so that the wrong instruction gets fixed (spec decision 12). `## The problem statement`, `## Finding the transcripts`,
  `## Every finding cites evidence`, `## From finding to fix`.

- [ ] Steps as in Task 8. Commit `"Carry debugging, verification, review and skill writing as skills"`.

*Tasks 8 to 11 touch disjoint files and may run in parallel (three at a time) once Task 7 has landed.
They may also run alongside Tasks 1 to 6.*

### Task 12: The agents carry the standard

**Files:**
- Modify: `agents/manager.md`, `agents/auditor.md`, `agents/planner.md`, `agents/implementer.md`, `agents/debugger.md`, `agents/reviewer.md`, `tests/test_agents.py`

**Interfaces:**
- Consumes: the 21 skill names (Tasks 7–11), the CLI subcommands `metrics`, `debt`, and `coverage` (Tasks 4, 6 and 13).
- Produces: a `## Skills` section in every agent. **Skills are invoked, not remembered**: each agent names the
  `apm:` skills to load at each trigger. For example, the implementer uses `apm:test-first` before any behavior,
  `apm:clean-code` on touching a file, `apm:refactoring` over a limit, `apm:solid` and `apm:object-design`
  when adding a type, `apm:clean-architecture` when crossing a layer, `apm:functional-core` for absence and
  failure, and `apm:verification` before reporting. The manager's section also maps its own work to
  `apm:design-first`, `apm:writing-plans`, `apm:executing-plans`, `apm:parallel-dispatch`, `apm:worktrees`,
  `apm:finishing-a-branch`, `apm:code-review` and `apm:session-diagnosis`.
- Manager: a `## Debt` section. It runs `<CLI> metrics` and `<CLI> debt check` itself. It runs
  `<CLI> debt baseline` to tighten after debt is paid down, and adds `--accept` **only after the user
  approves that specific worsening in chat**. A failed debt check is a stop: it never merges past one.
  The section also says what to do with a split that leaves two over-limit files.
- The reviewer's job names `apm:branch-review`, `apm:code-smells`, `apm:clean-architecture`, and `<CLI> debt check`
  output as evidence. The auditor names `apm:clean-code-audit` and `metrics --json`. The planner names
  `apm:writing-plans` and `apm:adr`. The debugger names `apm:systematic-debugging` and `apm:test-first`.

- [ ] **Step 1: Write the failing tests**:
  - Every agent has `## Skills`.
  - Every skill directory is named as `apm:<name>` by at least one agent, and every `apm:<name>` an agent names exists.
  - The manager contains "invoked, not remembered" and `## Debt`.
  - `CLI_SUBCOMMANDS` gains `metrics`, `debt`, and `coverage` (each documented as `` `<CLI> <verb>` ``).
  - The manager's debt section contains "only after the user approves".
- [ ] **Step 2: Run** `python -m pytest tests/test_agents.py -v`. Expected: FAIL.
- [ ] **Step 3: Edit the agents.** **Step 4: Run** the whole suite. Expected: PASS.
- [ ] **Step 5: Commit** `"Point every agent at the skills it must invoke"`.

### Task 13: The coverage inventory

**Files:**
- Create: `standard/coverage.json`, `scripts/apm/coverage.py`, `docs/coverage.md`, `tests/test_coverage.py`, `tests/fixtures/coverage/` (a tiny fake source tree)
- Modify: `scripts/apm/cli_standard.py`, `scripts/apm/cli_parser.py`

**Interfaces:**
- Produces (`standard/coverage.json`):
  ```
  {"sources": [{"id": "va-skills", "title": "...", "origin": "...", "scan": ["skills/*/SKILL.md", ...],
                "not_methodology": [{"path": "skills/xp12-ui/SKILL.md", "reason": "..."}]}, ...],
   "items": [{"id": "va-skill/solid-single-responsibility", "source": "va-skills",
              "what": "SOLID: single responsibility", "source_path": "skills/solid-single-responsibility/SKILL.md",
              "covered_by": [{"file": "skills/solid/SKILL.md", "anchor": "## Single responsibility"}]}, ...]}
  ```
  The sources are:
  - `va-skills`: the 21 vendored skills, plus every `references/` and `examples/` file as its own item.
  - `va-commands`: `clean-code-audit` and `branch-review`.
  - `va-scorecard`: the 11 dimensions.
  - `va-audit`: the audit's 7 assessment steps and its report format.
  - `va-rules`: spec §8.1's list, one item per rule. These are the 15-line function limit, the 200-line file
    limit, the 7+ public-method reason, mandatory TDD, no skipped tests, no tests that wait on a person, a
    regression test before every bug fix, never weakening a test, extract before you add, refactor and
    behavior never in the same commit, structural plan constraints as acceptance criteria, logic doesn't
    move sideways, ADRs for decisions, honest reporting, debt that may shrink but never grow, and skills
    that are invoked rather than remembered.
  - `sp-skills`: the 15 superpowers skills, plus each methodology supporting file. Superpowers' own skill
    tests and creation logs are listed under `not_methodology` with a reason.
  `covered_by` may point at skills, agents, or (for the ratchet and limits) the code and its test.
- Produces (`coverage.py`):
  - `load_inventory(path: Path) -> dict` (raises `CoverageError` on bad shape: unknown source, duplicate id, empty `covered_by`).
  - `find_gaps(inventory: dict, root: Path) -> list[str]`: an item with no cover, a cover file that doesn't
    exist, or an anchor that isn't a line in that file (exact line match for headings, substring otherwise).
  - `scan_source(inventory: dict, source_id: str, source_root: Path) -> list[str]`: every file matching that
    source's `scan` globs that is neither an item's `source_path` nor `not_methodology` gives
    `"not inventoried: <path>"`, and every item whose `source_path` doesn't exist gives `"missing in source: <path>"`.
  - `render_table(inventory: dict) -> str`: one table per source (Item | Covered by), with links to each file and anchor,
    and a closing line `**Gaps: 0**` computed by `find_gaps`.
- CLI: `apm coverage [--source ID=DIR ...] [--table]` needs no project (it reads the plugin's own
  inventory). It prints the gaps, or the table with `--table`. It exits 1 if there are any gaps, else 0.

- [ ] **Step 1: Write the failing tests**
  - The test holds its **own** expected lists, independent of the JSON: `VA_SKILLS` (21 names), `VA_COMMANDS` (2),
    `SCORECARD` (11), `AUDIT` (8), `VA_RULES` (16), `SUPERPOWERS` (15). It asserts that each one has an item
    of the right id.
  - `test_no_gaps`: `find_gaps(load_inventory(...), repo_root) == []`.
  - `test_rendered_table_is_current`: `docs/coverage.md` equals `render_table(...)` (regenerate with `apm coverage --table`).
  - `test_find_gaps_reports_missing_file_and_anchor` (a hand-made inventory over `tmp_path`).
  - `test_load_rejects_duplicate_ids_and_unknown_source`
  - `test_scan_source_finds_uninventoried_and_missing` (over `tests/fixtures/coverage/`).
  - `test_cli_coverage_exit_codes`
- [ ] **Step 2: Run** `python -m pytest tests/test_coverage.py -v`. Expected: FAIL.
- [ ] **Step 3: Implement `coverage.py`**, then write `standard/coverage.json` item by item, reading each
  source file to choose its anchors. Generate `docs/coverage.md`.
- [ ] **Step 4: Cross-check against the real sources** (manual; record the exact commands and outputs in the PR description):
  ```
  python scripts/apm_cli.py coverage --source "va-skills=C:/Users/darby/source/repos/VirtualAirline Plugin for XP12/.claude"
  python scripts/apm_cli.py coverage --source "va-commands=C:/Users/darby/source/repos/VirtualAirline Plugin for XP12/.claude"
  python scripts/apm_cli.py coverage --source "sp-skills=C:/Users/darby/.claude/plugins/cache/claude-plugins-official/superpowers/7.0.0"
  ```
  Expected: `Gaps: 0` and exit 0 for each. Any gap is fixed in the inventory or a skill, never waved through.
- [ ] **Step 5: Run** the whole suite. Expected: all PASS.
- [ ] **Step 6: Commit** `"Prove the standard covers every item of the old one"`.

### Task 14: Version, docs and the final check

**Files:**
- Modify: `scripts/apm/__init__.py`, `.claude-plugin/plugin.json` (both `0.2.0`), `docs/platform-notes.md` (skill namespacing as observed), `tests/test_manifest.py` if it pins `0.1.0`

- [ ] **Step 1:** Bump the version. Run the whole suite. Expected: all PASS.
- [ ] **Step 2: Live check** (manual; record the results in `docs/platform-notes.md`): reinstall the plugin
  from the local marketplace, then in the Plan 1 scratch repo confirm that:
  (a) `apm:test-first` and `apm:branch-review` are offered as skills;
  (b) the manager's `<CLI> metrics` prints counts;
  (c) a worker that runs `debt baseline` is denied;
  (d) `debt check` fails after a function is grown.
- [ ] **Step 3: Run** `python scripts/apm_cli.py metrics scripts` and `python scripts/apm_cli.py coverage`, and
  paste both outputs into the PR.
- [ ] **Step 4: Commit** `"Release the standard as apm 0.2.0"`, push `plan-2-standard`, and open the PR.

## Structural acceptance criteria (checked before the PR)
- Every runtime file is at most 200 lines of logic, and every runtime function at most 15, **measured by the
  framework's own tool** (`test_framework_meets_its_own_limits`).
- 21 skills exist, each passing `test_skills.py`. No `SKILL.md` names a language or a project.
- `docs/coverage.md` ends with `**Gaps: 0**`, and the three `--source` cross-checks report no gaps.
- `apm debt check` fails on each gaming attempt listed in Review Focus 3.
- No Plan 1 test was weakened. Any Plan 1 test that changed was changed on purpose for a new rule (for example
  the subcommand list), and the PR says so.
