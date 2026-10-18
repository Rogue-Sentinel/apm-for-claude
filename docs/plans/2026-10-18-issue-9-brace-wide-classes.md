# APM for Claude — Issue 9: Wide classes in brace languages — Implementation Plan

> **For agentic workers:** the manager builds this plan task by task. Each task is built test-first by one
> implementer in its own worktree and verified by the manager with the task's targeted tests. The whole
> branch is reviewed once at the end, and the full suite runs exactly once, through the merge gate, right
> before the PR. No task is safety-critical: none touches `scripts/apm/guard*.py`, `scripts/hook_*.py` or
> `hooks/**`. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** `metrics` counts the public methods of C++ classes (in `.hpp`/`.cpp`/`.cc`/`.cxx`/`.hh`, and in
`.h` headers that hold C++), reports "not measured" instead of `0` for any language that has classes but
no class scanner, and the debt ratchet does not report classes that were simply never measured before
as new debt.

**Architecture:** A new C++ class scanner (`metrics_cpp.py`, with its head rules in `metrics_cpp_heads.py`)
walks the already-stripped code with a scope stack and counts public methods per `class`/`struct`/`union`.
`metrics.measure_text` attaches its result to C++ brace metrics; `measure_braces` is not changed. A `.h`
file is read as C++ when its code holds a C++-only construct (`metrics_lang.language_of`). The report
names the languages whose classes were not measured. The debt snapshot records which languages it
scanned for classes, and `compare` sets aside wide classes in a language the baseline never scanned as
neutral "newly measured" notes (`debt_classes.py`).

**Tech Stack:** Python 3, standard library only, pytest. Test command: `python -m pytest -q <files>`.

**Spec:** GitHub issue #9 (Rogue-Sentinel/apm-for-claude), with the manager's confirmed causes:
`metrics_python.py:119` is the only place a `ClassMetric` is made, and `metrics_lang.py:66` maps `h` to C.

## Source material (read-only)
- `C:\Users\darby\source\repos\VirtualAirline Plugin for XP12\tools\check_clean_code.py`: the XP12 repo's own
  scanner, which finds 30 wide classes on that tree (for example `src/db/database.h:81 Database -- 7 public
  methods`, `src/ui/map_screen.h:36 MapScreen -- 8 public methods`). Its counting rule is the reference for
  Task 3; the differences this plan chooses on purpose are listed there. Nothing in that repo is changed.

## Global Constraints
- Limits (profile defaults): **15** lines of logic per function, **200** per file, review flag at **7** or
  more public methods. They hold for every file this plan creates or changes, tests included.
- Standard library only; no new dependency.
- Test-first, no skipped tests, no test waits on a person, no existing test weakened. The one existing test
  this plan edits is `tests/test_metrics.py::test_report_json_carries_every_number`, which gains the new
  `classes_measured` key (Task 2): the JSON gained a field, and the test's job is to pin every field.
- `scripts/apm/metrics_braces.py` and `scripts/apm/metrics_heads.py` are not changed: function measurement
  of every brace language, C and C++ included, stays exactly as it is.
- The text report of a project whose class-bearing files are all Python (or C++ after Task 3) is unchanged
  line for line (`test_render_text_for_a_clean_report_lists_nothing_under_the_counts` passes unmodified).
- The debt snapshot stays `version: 1`; a baseline written before this change loads and compares.
- Dependency direction: `metrics_*` never imports `debt*`; `metrics_cpp_heads.py` imports only `re`;
  `debt_classes.py` imports nothing from `apm` (it works on snapshot dicts).
- American spelling, plain voice in docs.

## Review Focus
1. **A baseline recorded before the fix, on C++ code nobody changed.** The same tree measures 30 wide classes
   where the baseline holds 0. `debt check` must pass and list them as "newly measured, not new debt", with
   no "total rose: wide_classes" line; a Python wide class added on the same branch must still fail. Tests
   are in Task 5 (`test_a_legacy_baseline_does_not_count_newly_measured_cpp_classes_as_debt`,
   `test_a_new_wide_python_class_is_still_a_regression_against_a_legacy_baseline`, and the CLI tests).
2. **A baseline hand-edited to stop scanning a language.** Removing `"C++"` from `class_scanners` (and its
   classes) on a branch would hide every C++ class from the ratchet. It must fail as "class scanner missing:
   C++", both in `debt check` and in the branch-baseline-versus-main check. Tests are in Task 5.
3. **A real C header read as C.** Include guards, `#ifdef __cplusplus` / `extern "C" {` wrappers, structs,
   typedefs, and the words `class` or `namespace` in comments, strings or as a C identifier must leave a
   `.h` file as C. Tests are in Task 4.
4. **Members that look like methods and are not.** Data members initialized with a call or braces,
   `std::function` members, function-pointer members, `using`, `friend`, `typedef`, nested `enum`s and
   `= delete` must not count; operators and `= default` assignment must. Tests are in Task 3.
5. **Parity with the XP12 checker on its real tree.** The 30 wide classes in `src/` must come out with the
   same path, class name and count, apart from the differences Task 3 lists. Checked by hand in Task 6 and
   recorded in `docs/platform-notes.md`; the two named examples are also pinned as inline tests in Task 3.

---

## File Structure

```
scripts/apm/metrics_model.py       (modify) CLASS_LANGUAGES, CLASSLESS_LANGUAGES, classes_measured()
scripts/apm/metrics.py             (modify) attach C++ classes; "not measured" in text and JSON; language_of
scripts/apm/metrics_cpp.py         (create) C++ classes: scope walk over stripped code, public-method counts
scripts/apm/metrics_cpp_heads.py   (create) C++ head rules: tidy, class head, access label, is-a-public-method
scripts/apm/metrics_lang.py        (modify) named C and CPP languages; language_of(path, text) for .h headers
scripts/apm/debt.py                (modify) snapshot records class_scanners and class_languages; compare uses them
scripts/apm/debt_classes.py        (create) set aside classes the baseline never scanned; spot a dropped scanner
scripts/apm/debt_store.py          (modify) validate the two new snapshot fields
scripts/apm/cli_debt.py            (modify) "newly measured, not new debt" section and its hint
skills/clean-code/SKILL.md         (modify) one sentence under **Measuring**: which languages count public methods
docs/adr/0003-newly-measured-classes-are-not-new-debt.md   (create)
docs/adr/0004-h-headers-are-cpp-when-their-code-is.md      (create)
docs/adr/README.md                 (modify) two index rows
docs/platform-notes.md             (modify) the Task 6 XP12 parity check
tests/test_cli_metrics_classes.py  (create) the issue's reproduction, through the CLI
tests/test_metrics_class_report.py (create) "not measured" in the text report and the JSON
tests/test_metrics.py              (modify) one key added to the exact-JSON test
tests/test_metrics_cpp.py          (create) the C++ counting rule
tests/test_metrics_headers.py      (create) .h detection
tests/test_debt_classes.py         (create) snapshot fields, projection, validation
tests/test_cli_debt_classes.py     (create) the ratchet end to end
```

No committed C++ fixture files: every C++ sample lives as a string inside its test, so this repository's own
debt baseline gains no C++ wide class.

Tasks run in order, 1 to 7. None run in parallel: Tasks 2, 3 and 4 all change `metrics.py`, and Tasks 4 and
5 both add a row to `docs/adr/README.md`.

---

### Task 1: Reproduce the bug as failing tests

**Files:**
- Create: `tests/test_cli_metrics_classes.py`

**Interfaces:**
- Consumes: `apm_cli.main`, the `git_repo` fixture from `tests/conftest.py`.
- Produces: the module constant `WIDE_HEADER`, the text of a header declaring `class Database {` on line 1,
  then `public:`, then seven declarations `void m0();` … `void m6();`, then `};`.

- [ ] **Step 1: Write the failing tests.** A fixture writes `WIDE_HEADER` to `database.h` and `database.hpp`
  in `git_repo` (untracked files are measured) and changes into it.
  - `test_metrics_counts_the_public_methods_of_a_cpp_class[database.h]` and `[database.hpp]`
    (parametrized on the path): `metrics --json` gives that file's
    `"classes" == [{"name": "Database", "line": 1, "public_methods": 7}]`.
  - `test_a_h_header_holding_cpp_is_measured_as_cpp`: `metrics --json` gives `database.h` the language
    `"C++"`.
  - `test_metrics_text_flags_both_headers`: `metrics` prints
    `Review flags -- classes with 7+ public methods: 2`, `database.h:1 Database -- 7 public methods` and
    `database.hpp:1 Database -- 7 public methods`.
- [ ] **Step 2: Run** `python -m pytest -q tests/test_cli_metrics_classes.py`. Expected: 4 FAIL, each for the
  defect (`[]` where a class was expected, `"C"` where `"C++"` was expected, `: 0` in the text), not an
  import or fixture error. The `.hpp` case turns green in Task 3; the `.h` cases and the text test in Task 4.
- [ ] **Step 3: Commit** `"Reproduce issue 9: C++ classes are never measured"`. This commit is red on purpose;
  the manager verifies the failure reasons, not a pass.

### Task 2: Report classes as "not measured" where no scanner ran

**Files:**
- Modify: `scripts/apm/metrics_model.py` (two constants and one function)
- Modify: `scripts/apm/metrics.py` (`Report.classes_unscanned`, the class section, a new section, the JSON flag)
- Modify: `tests/test_metrics.py` (`test_report_json_carries_every_number`: add `"classes_measured": True`)
- Test: `tests/test_metrics_class_report.py`

**Interfaces:**
- Produces, in `metrics_model.py`:
  - `CLASS_LANGUAGES: frozenset[str] = frozenset({"Python"})`: the languages with a class scanner (Task 3 adds
    `"C++"`).
  - `CLASSLESS_LANGUAGES: frozenset[str] = frozenset({"C"})`: brace languages that have no methods to count.
  - `classes_measured(metric: FileMetric) -> bool`: `metric.language in CLASS_LANGUAGES and
    metric.functions_measured`.
- Produces, in `metrics.py`: `Report.classes_unscanned(self) -> dict[str, int]`: language name to file count,
  sorted by name, over files whose `language_for(path)` family is `"brace"` and whose `metric.language` is in
  neither set. Plain-family files are left out (the size-only section already covers them), and so is a
  Python file with a syntax error (the unmeasured section covers it).
- Text, exact (`{n}` is the wide-class count, `{langs}` the unscanned names joined by `, `):
  - nothing unscanned: `Review flags -- classes with 7+ public methods: {n}` (as today);
  - some unscanned, and at least one file with `classes_measured`:
    `Review flags -- classes with 7+ public methods: {n} (classes not measured for {langs})`;
  - some unscanned, and no file with `classes_measured`:
    `Review flags -- classes with 7+ public methods: not measured (no class scanner for {langs})`;
  - and, only when something is unscanned, right after the class section:
    `Files whose classes were not measured (no class scanner for the language): {k}` with one row per
    language, `  Java: 120`.
- JSON: each file gains `"classes_measured": classes_measured(metric)`.

- [ ] **Step 1: Write the failing tests** in `tests/test_metrics_class_report.py` (hand-made `FileMetric`s):
  - `test_a_java_only_report_says_classes_were_not_measured`: one `A.java` (`"Java"`, functions measured) gives
    `Review flags -- classes with 7+ public methods: not measured (no class scanner for Java)`, then
    `Files whose classes were not measured (no class scanner for the language): 1` and `  Java: 1`.
  - `test_a_mixed_report_counts_measured_classes_and_names_the_rest`: `a.py` with `ClassMetric("Wide", 4, 8)`,
    two `.java` files and one `.ts` file give
    `Review flags -- classes with 7+ public methods: 1 (classes not measured for Java, TypeScript)`, then
    `Files whose classes were not measured (no class scanner for the language): 3`, `  Java: 2`,
    `  TypeScript: 1`.
  - `test_c_plain_and_broken_python_files_are_not_listed_as_class_unmeasured`: a `.c` file, a `.sh` file and a
    `.py` file with `functions_measured=False` give `...: 0` and no `Files whose classes` line.
  - `test_json_marks_whether_each_file_had_its_classes_measured`: through `measure_text`, `a.py` gives `True`,
    `A.java` and `run.sh` give `False`.
- [ ] **Step 2: Run** `python -m pytest -q tests/test_metrics_class_report.py`. Expected: FAIL (no such
  section, no such key).
- [ ] **Step 3: Implement** the constants and `classes_measured` in `metrics_model.py`; in `metrics.py`,
  `Report.classes_unscanned`, a `_class_header(report, limits) -> str` helper for the three header forms
  (keeps `_class_section` under the function limit), `_class_unscanned_section(report) -> list[str]` returning
  `[]` when nothing is unscanned, and the JSON key. Add the key to the exact-JSON test in `tests/test_metrics.py`.
- [ ] **Step 4: Run** `python -m pytest -q tests/test_metrics_class_report.py tests/test_metrics.py
  tests/test_cli_metrics.py tests/test_own_limits.py`. Expected: PASS.
- [ ] **Step 5: Commit** `"Say classes were not measured when no scanner ran, instead of 0"`.

### Task 3: Count the public methods of C++ classes

**Files:**
- Create: `scripts/apm/metrics_cpp_heads.py`, `scripts/apm/metrics_cpp.py`
- Modify: `scripts/apm/metrics_model.py` (`CLASS_LANGUAGES` gains `"C++"`)
- Modify: `scripts/apm/metrics.py` (`measure_text` attaches C++ classes to brace metrics)
- Test: `tests/test_metrics_cpp.py`

**Interfaces:**
- Consumes: `strip_code`, `Language` (`metrics_lang`); `ClassMetric`, `FileMetric` (`metrics_model`).
- Produces, in `metrics_cpp_heads.py` (all on stripped text):
  - `tidy_head(head: str) -> str`: drops leading `template <...>` prefixes (nested angles), `[[...]]`
    attributes, `alignas(...)` and `__declspec(...)`, and angle-bracket arguments unless the head holds
    `operator`; strips whitespace.
  - `scope_kind(head: str) -> Literal["namespace", "class", "other"]`: `"namespace"` for a `namespace` head
    without `(` and for `extern ""`; `"class"` when the tidied head starts with `class`, `struct` or `union`
    and holds no `(` and no `=`; `"other"` otherwise (`enum` heads included).
  - `class_head(head: str) -> tuple[str, str]`: (name, starting access). The name is the last word before a
    base-clause `:` (not `::`), ignoring `class`/`struct`/`union`/`final`; `"<anonymous>"` when none. Access is
    `"private"` for `class`, `"public"` for `struct` and `union`.
  - `access_label(head: str) -> str | None`: `"public"`, `"protected"` or `"private"` when the whole head before
    a single `:` is one of those words; else None.
  - `is_function_head(head: str) -> bool`: once trailing qualifiers (`const`, `volatile`, `noexcept` with or
    without `(...)`, `override`, `final`, `mutable`, `&`, `&&`) and a trailing return type (`-> T`) are
    removed, the tidied head holds `(` and ends with `)`, or ends with `{}` after a constructor initializer
    (`) :`). It tells a `{` that opens an inline body from one that opens an initializer (`y_{2}`).
  - `is_public_method(head: str, class_name: str) -> bool`: the counting rule below, for a member head that
    ended at `;` or at the `{` of an inline body.
- Produces, in `metrics_cpp.py`:
  - `cpp_classes(code: str) -> tuple[ClassMetric, ...]`: every class, struct and union defined at file,
    namespace or class scope, in source order of their heads. A nested class is named `Outer::Inner`;
    namespaces do not qualify names. `line` is the line of the class's name.
  - `with_cpp_classes(metric: FileMetric, text: str, language: Language) -> FileMetric`: `metric` unchanged
    unless `language.name == "C++"` and `metric.functions_measured`; then `dataclasses.replace(metric,
    classes=cpp_classes(strip_code(text, language)))`.
- `measure_text` returns `with_cpp_classes(measure_braces(path, text, language), text, language)` for the brace
  family.

**The counting rule.** A public method is a member function declared or defined directly in a class body
while the access is `public`. Each declaration counts once, so each overload counts.

| Counts | Does not count |
|---|---|
| ordinary, `static`, `virtual`, pure virtual (`= 0`), `override`, `const`/`noexcept` methods | constructors (any, `explicit` included) and destructors, `= default` or not |
| inline definitions (`int get() const { return x_; }`) | anything `= delete` |
| member templates (`template <class T> void visit(T)`) | `protected` and `private` members |
| operators, `operator=` with `= default` included, and conversion operators | `using`, `friend`, `typedef`, `static_assert`, nested `enum`, nested class heads |
| | data members, including `int x = f();`, `int y{0};`, `std::function<void()> cb;` and function pointers `void (*cb)(int);` |
| | out-of-class definitions (`void A::f() {}`) and classes defined inside function bodies |

Compared with `tools/check_clean_code.py` in the XP12 repo, this is the same rule (its `_is_public_method`,
its class/struct/union defaults, its scope walk), except on purpose:
- a function-pointer member is not a method (that tool counts `void (*cb)(int);` as a method named `void`);
- a nested class is named `Outer::Inner` (that tool prints `Inner`), matching how Python nested classes are
  named here;
- `line` is the line of the class name (that tool gives the line of the `{`; the two agree whenever the brace
  is on the head's line, as in both of the issue's examples);
- a head with `=` (`struct Point p = {1, 2};`) is not a class (that tool reads it as a class named `=`).

- [ ] **Step 1: Write the failing tests** in `tests/test_metrics_cpp.py`, through `measure_text("a.hpp", text)`
  unless named otherwise, asserting `[(c.name, c.line, c.public_methods) for c in metric.classes]`:
  - `test_methods_after_public_are_counted_and_private_ones_are_not`: `class A {` / `public:` / `void a();` /
    `void b();` / `private:` / `void c();` / `};` gives `[("A", 1, 2)]`.
  - `test_a_class_starts_private_and_a_struct_or_union_starts_public`: `class A { void a(); };` gives
    `[("A", 1, 0)]`; `struct S { void a(); };` gives `[("S", 1, 1)]`; `union U { void a(); };` gives
    `[("U", 1, 1)]`.
  - `test_protected_methods_are_not_public`: `struct S {` / `protected:` / `void a();` / `};` gives 0.
  - `test_constructors_destructors_and_deleted_members_are_not_counted`: in a struct `A`: `A();`,
    `explicit A(int);`, `A(const A&) = delete;`, `A(A&&) = default;`, `virtual ~A();` and
    `void f() = delete;` give 0.
  - `test_operators_including_defaulted_assignment_are_counted`: `A& operator=(A&&) noexcept;`,
    `A& operator=(const A&) = default;`, `bool operator==(const A&) const;`, `explicit operator bool() const;`
    give 4.
  - `test_static_virtual_pure_inline_and_template_methods_are_counted`: `static A make();`,
    `virtual void v() = 0;`, `int get() const { return x_; }`, `template <typename T> void visit(T t) { t(); }`,
    `[[nodiscard]] auto size() const -> int;` give 5.
  - `test_data_members_and_declarations_that_are_not_methods`: `int x = compute();`, `int y{0};`,
    `std::function<void()> cb;`, `void (*fp)(int);`, `using Base::Base;`, `friend void swap(A&, A&);`,
    `typedef int T;`, `enum class Mode { On, Off };`, `static_assert(sizeof(int) == 4);` in a struct give 0.
  - `test_nested_classes_are_counted_on_their_own`: `struct Outer {` / `void a();` / `struct Inner {` /
    `void b();` / `void c();` / `};` / `};` gives `[("Outer", 1, 1), ("Outer::Inner", 3, 2)]`.
  - `test_forward_declarations_and_out_of_class_definitions_are_not_classes`: `class A;` / `void A::f() {` /
    `}` gives `[]`.
  - `test_templates_attributes_bases_and_final_are_read_from_the_head`:
    `template <typename T>` / `class [[nodiscard]] Box final : public Base<T>, private Other {` / `public:` /
    `void a();` / `};` gives `[("Box", 2, 1)]`; `struct alignas(16) V { void a(); };` gives `[("V", 1, 1)]`.
  - `test_namespaces_and_extern_c_blocks_are_transparent`: `namespace va::ui {` / `extern "C" {` /
    `struct S { void a(); };` / `}` / `}` gives `[("S", 3, 1)]`.
  - `test_classes_inside_function_bodies_and_struct_initializers_are_not_reported`: `void f() {` /
    `struct L { void a(); };` / `}` / `struct Point p = {1, 2};` gives `[]`.
  - `test_access_labels_and_bitfields_and_constructor_initializers_do_not_confuse_the_count`: `class A {` /
    `public:` / `A() : x_(1), y_{2} {}` / `int bits : 3;` / `void a();` / `private:` / `int x_, y_;` / `};`
    gives `[("A", 1, 1)]`.
  - `test_the_xp12_database_header_has_seven_public_methods`: inline text with the shape of
    `src/db/database.h`'s `class Database` (a public `enum class Mode { ReadWrite, ReadOnly };`,
    `explicit Database(const std::string& path, Mode mode = Mode::ReadWrite);`, `~Database();`, deleted copy
    constructor and copy assignment, move constructor, `Database& operator=(Database&& other) noexcept;`,
    `void exec(std::string_view sql);`, `[[nodiscard]] Statement prepare(std::string_view sql);`,
    `query_string`, `query_int`, `[[nodiscard]] sqlite3* handle() const noexcept { return db_; }`,
    `[[nodiscard]] int changes() const noexcept;`, then `private:` / `sqlite3* db_{nullptr};`) gives
    `("Database", 1, 7)`.
  - `test_the_xp12_map_screen_header_has_eight_public_methods`: inline text with the shape of
    `src/ui/map_screen.h` (`namespace va::ui {`, `class MapScreen {`, `public:`, the explicit constructor,
    `show_flight`, `flight`, `draw`, `leave`, `tiles_needed`, `upload_tile`, `set_basemap_failed`,
    `resident_tile_bytes`, then `private:` with a nested `struct Canvas { ImVec2 origin; float width{}; };`
    and several private methods, one spanning two lines) gives `MapScreen` 8 and `MapScreen::Canvas` 0.
  - `test_a_cpp_file_with_unbalanced_braces_reports_no_classes`: `class A {` / `public:` / `void a();` gives
    `functions_measured is False` and `classes == ()`.
  - `test_c_files_are_not_scanned_for_classes`: `measure_text("a.c", "struct S { int a; };\n")` gives
    `classes == ()`.
  - `test_cpp_files_no_longer_count_as_class_unmeasured`: `Report((measure_text("a.hpp", ...),))` gives
    `classes_unscanned() == {}`.
- [ ] **Step 2: Run** `python -m pytest -q tests/test_metrics_cpp.py`. Expected: FAIL (no module
  `apm.metrics_cpp`).
- [ ] **Step 3: Implement** `metrics_cpp_heads.py`, then `metrics_cpp.py`: a scope stack over the structural
  characters `{ } ; :` of the stripped code, in the manner of `metrics_braces._Scanner`. File, namespace and
  class scopes collect a head; every other `{` opens an opaque scope whose contents are skipped. In a class,
  a `{` whose head passes `is_function_head` is an inline body (the count is decided there, and the head is
  reset when it closes); any other closed opaque scope appends `{}` to the class's head (so `int y{0};` stays
  a data member). At
  a `:` that is not part of `::`, `access_label` may change the access and reset the head. At `;`, and at the
  `{` of an inline body, `is_public_method` decides the count while the access is `public`. Add `"C++"` to
  `CLASS_LANGUAGES` and wire `with_cpp_classes` into `measure_text`.
- [ ] **Step 4: Run** `python -m pytest -q tests/test_metrics_cpp.py tests/test_metrics_class_report.py
  tests/test_metrics.py tests/test_metrics_braces.py tests/test_metrics_braces_heads.py tests/test_cli_metrics.py
  tests/test_own_limits.py`, then `python -m pytest -q tests/test_cli_metrics_classes.py`. Expected: PASS for the
  first; in the second, `[database.hpp]` now PASSES and the three `.h`/text tests still FAIL for the `.h` reason.
- [ ] **Step 5: Commit** `"Count the public methods of C++ classes"`.

*Ruling during Task 3: RED was a behavior failure (C++ files reported no classes; 14 failed, 4 passed — the four that expect an empty result), not the "no module `apm.metrics_cpp`" the brief predicted, because the tests go through `measure_text` and never import the new module. That is the stronger kind of red. Cost if wrong: none.*

### Task 4: Read a `.h` header as C++ when its code is C++

*This task plans the recommended option, a content check. The choice is the user's; see the report. If the
user picks another option, this task and ADR 0004 are replanned before the build reaches them.*

**Files:**
- Modify: `scripts/apm/metrics_lang.py` (name the C and C++ languages; add `language_of`)
- Modify: `scripts/apm/metrics.py` (`measure_text` uses `language_of`)
- Modify: `skills/clean-code/SKILL.md` (one sentence at the end of the **Measuring** paragraph)
- Create: `docs/adr/0004-h-headers-are-cpp-when-their-code-is.md`
- Modify: `docs/adr/README.md` (row 0004)
- Test: `tests/test_metrics_headers.py`

**Interfaces:**
- Produces, in `metrics_lang.py`:
  - `C: Language` and `CPP: Language`, the two table entries now bound to names (the table uses them; nothing
    else in the table changes).
  - `language_of(path: str, text: str) -> Language | None`: `language_for(path)`, except that a path ending in
    `.h` (any case) whose `strip_code(text, C)` matches a C++ marker gives `CPP`. Markers, one compiled
    multiline regex: a line starting `template` then `<`; `namespace` followed by an optional name (with `::`)
    and `{`; `using namespace`; `class Name` followed by anything but `; { ( =` and then `{`; a line that is
    only `public`, `protected` or `private` then a single `:`.
- `language_for(path)` is unchanged, so `select_files` stays path-only and `.h` still selects as a brace file.

- [ ] **Step 1: Write the failing tests** in `tests/test_metrics_headers.py`:
  - `test_a_header_declaring_a_class_is_cpp_and_its_classes_are_counted`: `measure_text("db.h", ...)` with one
    class and seven public methods gives language `"C++"` and `public_methods == 7`.
  - `test_each_cpp_marker_makes_a_header_cpp` (parametrized): `namespace a {}`, `namespace a::b {}`,
    `template <typename T> T id(T);`, `using namespace std;`, `class Y : public Base {};`, and an access
    label inside a struct (`struct S {` / `public:` / `};`) each give `language_of("x.h", text) is CPP`.
  - `test_a_c_header_with_guards_and_an_extern_c_wrapper_stays_c`: include guard, `#ifdef __cplusplus` /
    `extern "C" {` / `#endif`, `struct point { int x; int y; };`, `typedef struct node node;`,
    `int add(int a, int b);`, the closing wrapper; gives `C`.
  - `test_cpp_words_in_comments_strings_and_c_identifiers_leave_a_header_c`:
    `/* class Foo { namespace x { */`, `const char* s = "template <T>";`, `int class;`,
    `struct s { int private; };` gives `C`.
  - `test_only_h_files_are_sniffed`: `language_of("a.c", "class X {};")` gives `C`;
    `language_of("a.hpp", "int f(void);")` gives `CPP`.
  - `test_language_for_still_reads_h_as_c`: `language_for("a.h").name == "C"`.
- [ ] **Step 2: Run** `python -m pytest -q tests/test_metrics_headers.py`. Expected: FAIL (no `language_of`).
- [ ] **Step 3: Implement** `language_of`, and have `measure_text` call it. Add to `skills/clean-code/SKILL.md`,
  at the end of the **Measuring** paragraph: "Public methods are counted for Python and C++ (a `.h` header
  counts as C++ when its code declares a class, a namespace, a template or an access label); for any other
  language with classes the review-flag line says \"not measured\" and names the language, never 0." Write
  ADR 0004 (below) and its index row.
- [ ] **Step 4: Run** `python -m pytest -q tests/test_metrics_headers.py tests/test_cli_metrics_classes.py
  tests/test_metrics_lang.py tests/test_metrics_cpp.py tests/test_metrics.py tests/test_cli_metrics.py
  tests/test_skills_clean_code.py tests/test_skills.py tests/test_docs.py tests/test_own_limits.py`. Expected:
  PASS, with all four reproduction tests from Task 1 green.
- [ ] **Step 5: Commit** `"Read a .h header as C++ when its code is C++"`.

*Ruling during Task 4: the verbatim skill sentence names a language, which `tests/test_skills.py::test_no_banned_term_outside_by_language_references` forbids outside `references/*-by-language.md` (the framework is language agnostic). So the language detail goes in a new `skills/clean-code/references/class-scanners-by-language.md` (which languages count public methods, and the `.h` rule), and the **Measuring** paragraph gains a language-neutral sentence linking to it: "Public methods are counted only for the languages that have a class scanner, listed in [references/class-scanners-by-language.md](references/class-scanners-by-language.md); for any other language with classes the review-flag line says \"not measured\" and names the language, never 0." The structural criterion "`skills/clean-code/SKILL.md` names the languages whose public methods are counted" is met through that linked reference. No test is changed. Cost if wrong: one sentence moved between two files.*

**ADR 0004, "A `.h` header is C++ when its code holds a C++-only construct":** context (issue 9: `.h` mapped
to C, so every C++ header was skipped; C and C++ function scanning is identical, so the language only decides
the class scan and the label); decision (the marker list above, checked on stripped code, `.h` only);
consequences (no configuration; a C header misread as C++ costs only its label, because a C struct has no
methods and function pointers are not counted; a C++ header with no marker, such as one holding only a
`struct` with methods, is read as C and its classes are missed, which the "not measured" line does not
catch because C has no class scanner); alternatives (a profile setting, the presence of other C++ files in
the repository, always C++, with why each lost, from the report).

### Task 5: Do not count newly measured classes as new debt

**Files:**
- Create: `scripts/apm/debt_classes.py`
- Modify: `scripts/apm/debt.py` (`snapshot` records two fields; `Comparison` gains `newly_measured`; `compare`
  applies the projection)
- Modify: `scripts/apm/debt_store.py` (`_SHAPES` gains the two fields; a `_str_map` validator)
- Modify: `scripts/apm/cli_debt.py` (`render_comparison` section and hint)
- Create: `docs/adr/0003-newly-measured-classes-are-not-new-debt.md`
- Modify: `docs/adr/README.md` (row 0003)
- Test: `tests/test_debt_classes.py`, `tests/test_cli_debt_classes.py`

**Interfaces:**
- Consumes: `CLASS_LANGUAGES` (`metrics_model`, `{"C++", "Python"}` after Task 3); `Findings`, `merge`
  (`debt_compare`).
- Produces:
  - Snapshot fields: `"class_scanners": sorted(CLASS_LANGUAGES)` (a list of language names), and
    `"class_languages": {path: language}` for every file that has at least one listed wide class.
  - `debt_classes.LEGACY_CLASS_SCANNERS = ("Python",)`: what a snapshot without `class_scanners` scanned.
  - `debt_classes.project_classes(base: Mapping, current: dict) -> tuple[dict, list[str], list[str]]`:
    (`current` without the wide classes whose file's language, from `current["class_languages"]`, is not in the
    base's scanners, with `totals["wide_classes"]` lowered to match; the regressions, one
    `class scanner missing: {lang}` per base scanner absent from the current scanners, both defaulting to
    `LEGACY_CLASS_SCANNERS`; the notes, sorted by key,
    `newly measured: {key} ({n} public methods; the baseline did not measure {lang} classes)`). A class whose
    file has no recorded language is kept, so it is judged as measured.
  - `Comparison.newly_measured: tuple[str, ...] = ()`; `compare` calls `project_classes` after the version
    check and before `project_onto`, adds its regressions as a `Findings`, and passes its notes through.
  - `cli_debt.TRACK_HINT = "Run \`apm debt baseline\` to start tracking the newly measured classes"`;
    `render_comparison` prints `newly measured, not new debt:` and the notes after the moves section, and
    `TRACK_HINT` when there are notes and nothing is worse.
  - `debt_store` validates `class_scanners` as a list of strings and `class_languages` as a string-to-string
    map: a wrong shape raises `DebtError("<label>: class_languages has the wrong shape")`.

- [ ] **Step 1: Write the failing tests.** In `tests/test_debt_classes.py`, with `debt_helpers`; a "legacy"
  baseline is a snapshot with `class_scanners` and `class_languages` deleted:
  - `test_snapshot_records_the_scanned_languages_and_the_language_of_each_wide_class_file`: files `db.h`
    (`"C++"`, `Database` 7) and `a.py` (`Slim` 3) give `class_scanners == ["C++", "Python"]` and
    `class_languages == {"db.h": "C++"}`.
  - `test_a_legacy_baseline_does_not_count_newly_measured_cpp_classes_as_debt`: legacy base of `db.h` with no
    classes; current with `Database` 7. Not worse; `newly_measured == ("newly measured: db.h::Database (7 public
    methods; the baseline did not measure C++ classes)",)`; no regression mentions `wide_classes`.
  - `test_a_new_wide_python_class_is_still_a_regression_against_a_legacy_baseline`: legacy base; current adds
    `a.py::Wide` 8. Regressions include `new wide class: a.py::Wide (8 public methods)`.
  - `test_once_recorded_a_cpp_class_that_grows_is_a_regression`: base and current in the new shape, 7 then 9.
    Regressions include `grew: db.h::Database 7 → 9`; `newly_measured == ()`.
  - `test_a_new_cpp_class_against_a_baseline_that_scanned_cpp_is_a_regression`.
  - `test_dropping_a_scanner_from_the_current_snapshot_is_a_regression`: base scanners `["C++", "Python"]`,
    current `["Python"]`. Regressions include `class scanner missing: C++`.
  - `test_a_wide_class_with_no_recorded_language_is_judged_as_measured`: legacy base; current lists
    `db.h::Database` 7 but its `class_languages` is `{}`. Regressions include the new wide class.
  - `test_a_baseline_with_malformed_class_fields_is_rejected` (parametrized): `class_scanners: "C++"` and
    `class_languages: {"db.h": 3}` each raise `DebtError` naming the field.
  In `tests/test_cli_debt_classes.py`, a fixture like `tests/test_cli_debt.py`'s `repo`, holding `db.hpp` with
  one class of eight public methods:
  - `test_check_passes_on_unchanged_cpp_code_measured_for_the_first_time`: write a legacy-shaped baseline (the
    current snapshot with `classes` emptied, `totals.wide_classes` 0 and both new fields removed); `debt check`
    exits 0 and prints `newly measured, not new debt:` and `TRACK_HINT`.
  - `test_baseline_then_records_the_classes_and_their_growth_fails`: after that, `debt baseline` exits 0 and the
    file holds `classes == {"db.hpp::Database": 8}` and `"C++"` in `class_scanners`; growing to nine methods
    makes `debt check` exit 1 with `grew: db.hpp::Database 8 → 9`.
  - `test_a_branch_baseline_that_adds_newly_measured_classes_passes_against_main`: the legacy baseline committed
    on `main`, `debt baseline` on a branch; `debt check --base main` exits 0.
  - `test_a_branch_baseline_that_drops_a_scanner_fails_against_main`: the new-shape baseline committed on
    `main`; on a branch, `"C++"` removed from `class_scanners` and the class removed, by hand; `debt check`
    exits 1 and prints `class scanner missing: C++`.
- [ ] **Step 2: Run** `python -m pytest -q tests/test_debt_classes.py tests/test_cli_debt_classes.py`. Expected:
  FAIL (no `debt_classes`, no snapshot fields).
- [ ] **Step 3: Implement** `debt_classes.py`, the snapshot fields and `compare` wiring in `debt.py`, the
  validators in `debt_store.py`, and the section and hint in `cli_debt.py`. Write ADR 0003 (below) and its
  index row.
- [ ] **Step 4: Run** `python -m pytest -q tests/test_debt_classes.py tests/test_cli_debt_classes.py
  tests/test_debt.py tests/test_debt_guards.py tests/test_debt_match.py tests/test_debt_moves.py
  tests/test_debt_scope.py tests/test_debt_sources.py tests/test_debt_store.py tests/test_debt_tighten.py
  tests/test_cli_debt.py tests/test_audit_report.py tests/test_audit_scan.py tests/test_cli_audit.py
  tests/test_guard_debt.py tests/test_docs.py tests/test_own_limits.py`. Expected: PASS.
- [ ] **Step 5: Commit** `"Do not count classes the baseline never measured as new debt"`.

**ADR 0003, "A newly measured language is not new debt":** context (issue 9: a baseline recorded before C++
classes were measured holds 0 wide classes; after the fix the unchanged XP12 tree measures 30, which
`compare_items` and `compare_totals` would both report as regressions on code nobody touched); decision
(snapshots record `class_scanners` and `class_languages`; a wide class in a language the baseline did not
scan is a neutral note; a baseline without the field scanned Python only; a scanner missing from the current
side is a regression, like a narrowed scope); consequences (until someone runs `debt baseline`, the newly
measured classes are outside the ratchet and can grow unseen, which the hint names; the rule extends to every
future class scanner with no further change; the snapshot gains two fields but keeps version 1);
alternatives (bump the version and refuse old baselines, which forces every project to re-baseline by hand;
accept the regressions with `--accept`, which asks the user to approve debt that is not new; key classes by
language, which renames every existing key).

### Task 6: Check parity on the XP12 tree (manual, by the manager)

**Files:**
- Modify: `docs/platform-notes.md` (a new section, `## Issue 9 live check (2026-10-18)`, one table row per check)

Read-only in `C:\Users\darby\source\repos\VirtualAirline Plugin for XP12`: nothing is written there. Run this
branch's code, not the installed plugin.

- [ ] **Step 1 (manual):** in the XP12 repo, run `python -B tools/check_clean_code.py` and
  `python -B "<this worktree>/scripts/apm_cli.py" metrics src`. Compare the two wide-class lists by path, class
  name and count. Expected: 30 on both sides, `src/db/database.h ... Database -- 7` and
  `src/ui/map_screen.h:36 MapScreen -- 8` among them; any difference is one of the four Task 3 lists
  (function pointers, nested names, brace line, `=` heads) or a bug. A bug goes back to Task 3 as a failing
  inline test first.
- [ ] **Step 2 (manual):** if the XP12 repo has an APM baseline, run
  `python -B "<this worktree>/scripts/apm_cli.py" debt check` there. Expected: exit 0, with the C++ wide
  classes under `newly measured, not new debt:`.
- [ ] **Step 3:** record both results in `docs/platform-notes.md` (check, result, evidence: the counts, and each
  difference with its reason). **Commit** `"Record the issue 9 parity check against the XP12 tree"`.

*Ruling during Task 6: the parity run found 8 Qt classes counted as 0, a difference outside the four listed, so per Step 1 it went back to Task 3's code: a debugger (opus) added two failing inline tests (macros before `public:` and before `private:`) and fixed `access_label` to read the access word that ends the head, as the XP12 checker does; `signals:` and `slots:` are not labels, as in the checker. Rerun: 30 of 30. Step 2 had no XP12 baseline to run against (XP12's `origin/main` has no `.apm/`), so the manager recorded one with apm 0.3.0 in the scratch export and ran this branch's `debt check` against it: exit 0, 48 newly measured. The Risks line on Qt is amended below. Cost if wrong: none; it matches the checker on the real tree.*

### Task 7: Run the merge gate

- [ ] **Step 1: Run** `<CLI> gate 9`. Expected: PASS: the full suite once, `<CLI> debt check` passing, and every
  structural criterion below met. On a failure, fix the cause in the task that owns it and run the gate again.

---

## Structural acceptance criteria (checked before the PR)
- Every file this plan creates or changes is at most 200 lines of logic and every function in it at most 15,
  measured by `<CLI> metrics`: `scripts/apm/metrics.py`, `metrics_model.py`, `metrics_lang.py`,
  `metrics_cpp.py`, `metrics_cpp_heads.py`, `debt.py`, `debt_classes.py`, `debt_store.py`, `cli_debt.py`, and
  every test file listed in File Structure. `tests/test_own_limits.py` passes.
- `scripts/apm/metrics_braces.py` and `scripts/apm/metrics_heads.py` are unchanged against `main`.
- `metrics_*` modules import nothing from `debt*`; `metrics_cpp_heads.py` imports only `re` (and `typing`);
  `debt_classes.py` imports nothing from `apm`.
- The snapshot `VERSION` is still 1, and a baseline without `class_scanners` loads and compares.
- `test_render_text_for_a_clean_report_lists_nothing_under_the_counts` passes unmodified; the only edited
  existing test is `test_report_json_carries_every_number`, with one key added.
- `docs/adr/0003-newly-measured-classes-are-not-new-debt.md` and `docs/adr/0004-h-headers-are-cpp-when-their-code-is.md`
  exist, are Accepted, and have rows in `docs/adr/README.md`.
- `skills/clean-code/SKILL.md` names the languages whose public methods are counted.
- `docs/platform-notes.md` holds the Task 6 parity results.
- No C++ source file is committed to this repository (the samples are strings in tests).
- `<CLI> debt check` passes; no existing test was weakened, skipped or deleted.
- `<CLI> gate 9` passes. Merge style: `merge` (profile).

## Allowlisted actions
None. Task 6 runs two read-only commands in the XP12 repository and writes nothing there.

## Risks
- *Amended after Task 6: Qt macros with no `;` (`Q_OBJECT`, `Q_PROPERTY(...)`) run into the next member's head; the access label is the access word that ends the head, and tests cover macros before `public:` and before `private:`. A macro before an ordinary member still joins that member's head, as in the XP12 checker.*
- **The heuristics are a scanner, not a compiler.** Macros that expand to members (`DECLARE_X(Foo)`), Qt's
  `signals:` / `public slots:`, C++20 `requires` clauses, raw strings (`strip_code`'s known limit) and
  `#ifdef` arms that each open a class can miscount. `metrics_cpp.py` lists these in its docstring as the
  brace scanner does.
- **Parity is checked by hand on one tree.** The XP12 run (Task 6) is the only real-code check; the inline
  tests pin its two named examples.
- **The `.h` content check misses C++ headers with no marker** (a header holding only a `struct` with member
  functions and no namespace). Those are read as C and their classes are not counted, and because C has no
  class scanner the report does not say "not measured" for them. A profile override is the follow-up if a real
  project hits it.
- **Newly measured classes sit outside the ratchet until `debt baseline` runs.** The check prints the hint; the
  manager's tighten-on-better habit should cover it, but nothing forces it.

## Approval (2026-10-18)

*Approved by the user in chat: "Approved: content check for .h, keep the read-only Task 6 parity check against
XP12, and the two differences from the XP12 checker are fine." So: option B (content check) for `.h`; Task 6
stays, read-only; function-pointer members are not methods and nested classes are named `Outer::Inner`.*

## Pre-flight scan

| Tasks | Shared file or interface | Producer vs consumer | Found |
|---|---|---|---|
| 1 ↔ 3, 4 | the `classes` JSON shape | Task 1 asserts `{"name", "line", "public_methods"}`; `report_json` emits `asdict(ClassMetric)` with exactly those fields | agrees |
| 1 ↔ 3, 4 | the text flag line | Task 1 asserts `database.h:1 Database -- 7 public methods`; `_class_section` prints `{p}:{c.line} {c.name} -- {c.public_methods} public methods` | agrees |
| 2 ↔ 3 | `metrics_model.CLASS_LANGUAGES` | Task 2 creates it as `{"Python"}`; Task 3 adds `"C++"` | agrees, sequential |
| 2 ↔ 3 | `Report.classes_unscanned` | Task 2 produces it; Task 3's `test_cpp_files_no_longer_count_as_class_unmeasured` consumes it | agrees |
| 2, 3, 4 | `scripts/apm/metrics.py` | Task 2: class sections and JSON key; Task 3: `measure_text` brace branch; Task 4: `measure_text` language lookup | same file, run in order |
| 3 ↔ 4 | `measure_text` and the language name | Task 3's `with_cpp_classes` checks `language.name == "C++"`; Task 4's `language_of` returns `CPP` (the C++ table entry, named `"C++"`) | agrees |
| 2 ↔ 4 | `classes_unscanned` and `.h` | Task 2 reads `metric.language`, so a `.h` that Task 4 makes C++ leaves the unscanned list; a C `.h` is in `CLASSLESS_LANGUAGES` | agrees |
| 3 ↔ 5 | `CLASS_LANGUAGES` | Task 5 consumes `{"C++", "Python"}` for `class_scanners` | agrees |
| 4 ↔ 5 | `docs/adr/README.md` | each adds one row (0004 in Task 4, 0003 in Task 5) | same file, run in order; rows sorted by number |
| 1 | self | 4 tests, all failing for the defect; the commit is red on purpose | consistent |
| 2 | self | the three header forms and the section are all pinned by tests; Python-only output unchanged | consistent |
| 3 | self | files created (`metrics_cpp*.py`) match those it tests; the counting table matches the test list | consistent |
| 4 | self | `language_for` stays path-only, as `test_language_for_still_reads_h_as_c` pins | consistent |
| 5 | self | the snapshot fields it produces are the ones its validators and tests name | consistent |
| 6 | self | manual and read-only in XP12; it writes only `docs/platform-notes.md` here | consistent |
| 7 | self | the gate | consistent |

Rubric check: Task 1 commits a red test on purpose (the plan says so; the manager verifies the failure reasons).
No test asserts nothing; no duplicated logic is mandated.

## Final review (2026-10-18)

Whole-branch review, opus, range 0d03ee9..88f7b6a: spec compliant apart from one must-fix; quality good;
scorecard 8/10 old and new; ready to merge with fixes.

- **M1 (must fix):** `metrics_cpp_heads.py` matches "operator" as a substring (`_drop_angles`, `_is_data_member`),
  so `std::function<void(int)> on_operator_change;` and `int operator_id = f();` count as methods. Confirmed by
  the manager. Goes to the fix wave.

*Rulings by the manager on the suggestions, graded by effect on a person using the result:*
- *S1, arrays of function pointers (`void (*handlers[4])(int);`) count as methods: fix in the wave. It breaks
  the user's ruling that function-pointer members are not methods. Cost if wrong: one regex.*
- *S2, `__attribute__((...))` on a class head makes the class vanish: fix in the wave. A silently missed class
  is the failure issue 9 exists to remove. Cost if wrong: one more strip in `tidy_head`.*
- *S3, `operator std::vector<int>() const;` is not counted although the plan counts conversion operators: fix
  in the wave. A `requires` clause before an inline body: record as a known limit in both scanner
  docstrings, as the plan's Risks promised. Cost if wrong: one missed method in C++20 constraint code.*
- *S4, a hand-relabeled `class_languages` can hide a known class's growth from the branch-versus-main check:
  fix in the wave (a key the base already lists was measured by the base), with a test. Under ADR 0002 it is
  a known limit, but the fix is one line and closes it. Cost if wrong: none.*
- *S5, the clean-code reference overstates coverage for a marker-less C++ header: fix in the wave, one
  clause matching ADR 0004.*
- *S6, `_BASE_COLON` and the key-to-path split are duplicated: fix in the wave as its own refactoring commit.*

*Rulings on what the reviewer declined to judge:*
- *Marker-less C++ headers read as C: stands; the user chose the content check, and ADR 0004 records the cost.*
- *`signals:`/`slots:` keep the previous access: stands; parity with the XP12 checker (Task 6 ruling).*
- *A C++-only tree whose every file has unbalanced braces prints `: 0`: stands. Those files are listed under
  "could not be measured", so the output does not read as clean. Cost if wrong: a follow-up wording change.*
- *A `.h` is stripped up to three times: stands; no limit on speed, and `metrics_braces.py` may not change.*
- *Task 4's naming of `C`/`CPP` shares its behavior commit, and the Qt fix shares tests and code: stands; the
  plan prescribed Task 4's single commit, and tests with their behavior is this repo's convention.*
- *`public::std::string f();` misread: stands; pathological formatting, no plausible source.*
- *Long source lines: stands; the profile sets no line-length limit.*

Scoped re-review of the fix wave (opus, 280ead1..0a5e673): M1 and S1–S6 all addressed; no regression and no
looser verdict in the fix diff; open findings 0; ready to merge, subject to the gate.

## Deferred findings
- Final review: `skills/clean-code/references/class-scanners-by-language.md` still opens with "read as C, which has
  no classes to count" just before the sentence saying such classes are missed; one clause could be reworded.
- Final review: a conversion operator to a type whose last name matches the class (`struct Handle { operator
  ns::Handle() const; };`) is read as a constructor and not counted. Rare.
- Final review: the `newly = {...}` line in `scripts/apm/debt_classes.py` is past 120 characters (no limit set).
