# APM for Claude — Issue 10: files metrics never measured — Implementation Plan

> **For agentic workers:** the manager builds this plan task by task. Each task is built test-first by one
> implementer in its own worktree and verified by the manager with the task's targeted tests. The whole
> branch is reviewed once at the end, and the full suite runs exactly once, through the merge gate, right
> before the PR. No task is safety-critical: none touches `scripts/apm/guard*.py`, `scripts/hook_*.py` or
> `hooks/**`. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:**
- `metrics` measures QML, Inno Setup and CMake files for size, the way it measures `.ps1` today.
- It ends every report with `Files not measured: N`, in both text and JSON, so a report on code it could not read never passes for a clean one.
- The debt check treats newly measured file sizes as notes, not new debt, so upgrading does not fail the ratchet.

**Architecture:**
- The three languages are `plain` entries in the language table (`metrics_lang.py`). `CMakeLists.txt` is found by its file name.
- A new pure module (`metrics_not_measured.py`) decides which language-less files count as not measured, from the name and the bytes.
- `metrics.py` gains one shared function, `measure_files`, used by both the tree and a git ref. It reads those files and puts their paths on `Report`.
- A new dict-only module (`debt_languages.py`) mirrors `debt_classes.py`: an over-limit file in a language the baseline never measured is set aside as a "newly measured" note.

**Tech Stack:** Python 3, standard library only, pytest. Test command: `python -B -m pytest -q <files>`.

**Spec:** GitHub issue #10 (Rogue-Sentinel/apm-for-claude) and the manager's brief of 2026-10-24.

## Platform facts this plan relies on
These come from the planner's knowledge on 2026-10-24 and were not checked against the tools. Task 1's tests pin the chosen reading.
- **QML** comments are JavaScript-style: `//` and `/* */`. Strings use `"`, `'` and backtick.
- **Inno Setup:** `;` starts a comment in the setup sections. The `[Code]` section is Pascal Script, with `//`, `{ }` and `(* *)` comments. Strings do not use backslash escapes: `\` is a path separator.
- **CMake:** `#` starts a line comment, and `#[[ … ]]` is a bracket comment (CMake 3.0 and later). Quoted arguments use `"` with `\` escapes. `'` is an ordinary character.

## Global Constraints
- Limits (profile defaults):
  - **15** lines of logic per function.
  - **200** lines of logic per file.
  - A review flag at **7** or more public methods.
  - They hold for every file this plan creates or changes, tests included.
- Standard library only; no new dependency.
- No `guard*` file changes; the guard is frozen by the user's decision. `metrics.py` keeps its existing import of `guard_paths.matches_any`, unchanged.
- Test-first:
  - No skipped tests, and no test waits on a person.
  - No existing test is weakened.
  - The one existing test this plan edits is `tests/test_metrics.py::test_render_text_for_a_clean_report_lists_nothing_under_the_counts` (Task 4). Its expected list gains the line `Files not measured: 0`, because a clean report now ends with it.
- The snapshot stays `version: 1`. A baseline written by apm 0.3.2 loads and compares unchanged.
- Example names are generic (`ui/Main.qml`, `setup.iss`, `Sample App`). No X-Plane, XP12 or VirtualAirline.
- American spelling in docs and skills (`tests/test_docs.py` checks it).

## Review Focus
1. **`CMakeLists.txt` is CMake.** It is measured for size, not dropped as a `.txt` file, because the file name is checked before the extension. Tests are in Task 1 and Task 4.
2. **Only in-scope files are listed.** A file the profile excludes (`**/vendor/**`, a narrowed `include`), or one outside the `PATH` arguments, never appears as not measured. Tests are in Task 4.
3. **`metrics --ref` lists the same files not measured as the working tree.** Tests are in Task 4.
4. **Text versus binary.** A UTF-16 text file with a byte-order mark counts as text, not binary. A file with a NUL byte in its first 8000 bytes is binary. An empty or blank file is not counted. Tests are in Task 3.
5. **Upgrade.** A project with a 250-line `.qml` file and a baseline recorded by 0.3.2 passes `debt check` with a "newly measured" note. Once `debt baseline` is run, growth of that file fails. Tests are in Task 5.

---

## File Structure
```
scripts/apm/metrics_lang.py            + QML, Inno Setup, CMake (plain); file-name lookup; LANGUAGE_NAMES
scripts/apm/metrics_not_measured.py    NEW: which language-less files count as not measured (pure, stdlib only)
scripts/apm/metrics.py                 measure_files (shared by tree and ref); Report.not_measured; text and JSON
scripts/apm/metrics_ref.py             measure_at_ref goes through measure_files
scripts/apm/debt_languages.py          NEW: a newly measured language's long files are notes, not debt (dicts only)
scripts/apm/debt.py                    snapshot gains measured_languages, file_languages; compare calls debt_languages
scripts/apm/debt_store.py              shapes for the two new fields
scripts/apm/cli_debt.py                TRACK_HINT names classes and files
tests/test_metrics_size_only.py        NEW (Task 1)
tests/test_metrics_not_measured.py     NEW (Task 3)
tests/test_metrics_not_measured_report.py  NEW (Task 4)
tests/test_metrics.py                  one expected list gains a line (Task 4)
tests/test_debt_languages.py           NEW (Task 5)
tests/test_cli_debt_languages.py       NEW (Task 5)
docs/adr/0009-files-with-no-scanner-are-counted-as-not-measured.md   NEW (Task 4)
docs/adr/0010-a-newly-measured-languages-file-sizes-are-not-new-debt.md   NEW (Task 5)
docs/adr/README.md                     two rows
docs/tutorial.md                       section 8: the new report line, one debt sentence
skills/clean-code/SKILL.md             "Measuring": size-only languages and the not-measured line
skills/clean-code-audit/SKILL.md       audit template's measurements line
```

**Parallelism:**
- Tasks 1, 2 and 3 touch disjoint files and may run in parallel.
- Task 4 needs Tasks 1 to 3.
- Task 5 needs Task 1, and runs after Task 4: both edit `docs/adr/README.md` and `docs/tutorial.md`.

---

### Task 1: QML, Inno Setup and CMake are measured for size

**Files:**
- Modify: `scripts/apm/metrics_lang.py`
  - `_plain` gains `quotes` and `raw` parameters.
  - Three table entries.
  - A by-name table.
  - `language_for` checks the file name first.
  - `LANGUAGE_NAMES`.
  - Two known limits added to the module docstring.
- Test: `tests/test_metrics_size_only.py` (new)

**Interfaces:**
- Produces:
  - `language_for(path)` returns `Language("QML", "plain", …)` for `*.qml`, `"Inno Setup"` for `*.iss`, and `"CMake"` for `*.cmake` and for any file named `CMakeLists.txt`. Matching is case-insensitive on the file name and the extension. Every other `.txt` file still returns None.
  - `LANGUAGE_NAMES: tuple[str, ...]`: every language name in the table, sorted, each once. There are 25: the 22 at ea0e5e7 plus `"CMake"`, `"Inno Setup"` and `"QML"`.
  - `_plain(name, line=("#",), block=(), quotes=_PLAIN_QUOTES, raw=())`.
- Entries:
  - QML: line `("//",)`, block `(("/*","*/"),)`, quotes `_BACKTICK_QUOTES`.
  - Inno Setup: line `(";", "//")`, block `(("{","}"), ("(*","*)"))`, quotes `('"', "'")`, raw `('"', "'")` (no backslash escapes).
  - CMake: line `("#",)`, block `(("#[[", "]]"),)`, quotes `('"',)`, extension `cmake`.
  - By name: `{"cmakelists.txt": CMake}`, looked up with `os.path.basename(path).lower()`.
- Docstring known limits:
  - An Inno Setup `{` comment that opens after a `;` on the same line is missed.
  - CMake `#[=[ … ]=]` bracket comments are read as line comments.

- [ ] **Step 1: Write the failing tests**
  - `test_qml_inno_setup_and_cmake_are_size_only_languages`:
    - `language_for` gives these names, each with family `"plain"`: `ui/Main.qml` gives `"QML"`, `UI/MAIN.QML` gives `"QML"`, `setup/installer.iss` gives `"Inno Setup"`, `cmake/deps.cmake` gives `"CMake"`.
    - `CMakeLists.txt`, `src/CMakeLists.txt` and `src/cmakelists.TXT` all give `"CMake"`.
  - `test_other_txt_files_still_have_no_language`: `language_for("notes.txt")` and `language_for("CMakeLists.txt.bak")` are None.
  - `test_qml_comments_do_not_count`: `measure_text("Main.qml", "import QtQuick\n// note\n/* a\n b */\nItem {\n    width: 10\n}\n")` has `lines == 3` and `functions_measured is False`.
  - `test_inno_setup_section_and_pascal_comments_do_not_count`: `measure_text("setup.iss", "[Setup]\n; comment\nAppName=Sample App\nDefaultDirName={autopf}\\Sample\n[Code]\n{ pascal comment }\n(* another *)\n// line\nfunction InitializeSetup(): Boolean;\nbegin\n  Result := True;\nend;\n")` has `lines == 8`.
  - `test_an_inno_setup_string_ending_in_a_backslash_does_not_escape_its_quote`: `measure_text("setup.iss", "x := 'C:\\' + '{';\ny := 2;\nz := '}';\n").lines == 3`. With backslash escapes it would be 2.
  - `test_cmake_line_and_bracket_comments_do_not_count`: `measure_text("CMakeLists.txt", "# top\ncmake_minimum_required(VERSION 3.20)\n#[[ a\nblock ]]\nproject(Sample)\nadd_library(core\n  src/a.c\n)\n")` has `lines == 4`.
  - `test_a_cmake_string_hides_a_comment_marker`: `measure_text("a.cmake", "message(\"#[[ not a comment\")\nset(Y 2)\n").lines == 2`.
  - `test_language_names_are_the_old_table_plus_the_three_new_ones`:
    - `set(LANGUAGE_NAMES)` equals a hand-written set of the 22 names at ea0e5e7 plus `{"QML", "Inno Setup", "CMake"}`. The 22 are: C, C#, C++, Dart, Go, Java, JavaScript, Kotlin, Lua, Objective-C, PHP, Perl, PowerShell, Python, R, Ruby, Rust, SQL, Scala, Shell, Swift, TypeScript.
    - `list(LANGUAGE_NAMES) == sorted(LANGUAGE_NAMES)`.
- [ ] **Step 2: Run** `python -B -m pytest -q tests/test_metrics_size_only.py`. Expected: FAIL (no language for `.qml`, `.iss` or `CMakeLists.txt`; no `LANGUAGE_NAMES`).
- [ ] **Step 3: Implement** the entries, the by-name lookup and `LANGUAGE_NAMES` in `scripts/apm/metrics_lang.py`.
- [ ] **Step 4: Run** `python -B -m pytest -q tests/test_metrics_size_only.py tests/test_metrics_lang.py tests/test_metrics.py tests/test_metrics_headers.py tests/test_audit_scan.py`. Expected: PASS.
- [ ] **Step 5: Commit** `"Measure QML, Inno Setup and CMake files for size"`.

### Task 2: one measuring function for the tree and a ref (pure refactoring)

**Files:**
- Modify: `scripts/apm/metrics.py`
  - Add `Read` and `measure_files`.
  - Change `_read` to return bytes.
  - Extract `_in_scope` from `select_files`.
- Modify: `scripts/apm/metrics_ref.py` (`_text_at` becomes `_bytes_at`; `measure_at_ref` calls `measure_files`)
- Test: no new tests. The same tests pass, unchanged, before and after.

**Interfaces:**
- Produces:
  - `Read = Callable[[str], bytes | None]`.
  - `measure_files(names: Sequence[str], read: Read) -> Report`. It reads each name, skips None, decodes with `decode_text` and measures with `measure_text`. This is exactly what both callers do today.
  - `_in_scope(path: str, config: MetricsConfig) -> bool`: the include/exclude test, now separate from the language test inside `select_files`.
- `measure_tree` and `measure_at_ref` keep their signatures and results.
- After this task, `metrics_ref.py` imports only `Report, measure_files, select_files, under_paths` from `apm.metrics`.

- [ ] **Step 1: Run** `python -B -m pytest -q tests/test_metrics.py tests/test_metrics_ref.py tests/test_cli_metrics.py tests/test_cli_metrics_classes.py tests/test_metrics_class_report.py tests/test_audit_scan.py tests/test_own_limits.py` and record the pass count.
- [ ] **Step 2: Move** the read-decode-measure loop into `measure_files`, and the scope test into `_in_scope`. No behavior change.
- [ ] **Step 3: Run** the same command. Expected: the same pass count, no test edited.
- [ ] **Step 4: Commit** `"Measure the tree and a ref through one shared function"` (a refactoring commit only).

### Task 3: which files with no language count as not measured

**Files:**
- Create: `scripts/apm/metrics_not_measured.py` (standard library only)
- Test: `tests/test_metrics_not_measured.py` (new)

**Interfaces:**
- Produces:
  - `NOT_CODE_EXTENSIONS: frozenset[str]`: docs, data and config. The values are `.md .markdown .mdx .rst .adoc .asciidoc .txt .rtf .json .jsonc .json5 .yaml .yml .toml .ini .cfg .conf .properties .xml .csv .tsv .lock .log .svg`.
  - `BINARY_EXTENSIONS: frozenset[str]`. The values are `.png .jpg .jpeg .gif .bmp .ico .icns .webp .tif .tiff .psd .pdf .zip .gz .tgz .bz2 .xz .7z .tar .rar .jar .war .whl .exe .dll .so .dylib .a .lib .o .obj .pyc .class .wasm .ttf .otf .woff .woff2 .eot .mp3 .wav .ogg .flac .mp4 .mov .avi .mkv .webm .db .sqlite`.
  - `NOT_CODE_NAMES: frozenset[str]`, lowercase file names: `license copying notice authors contributors changelog changes readme owners codeowners`.
  - `named_as_not_code(path: str) -> bool`. True when any of these holds:
    - the file name starts with `.` (a dotfile, so config);
    - the lowercased file name is in `NOT_CODE_NAMES`;
    - the lowercased extension is in `NOT_CODE_EXTENSIONS` or `BINARY_EXTENSIONS`.
    - The caller has already found that the path has no language.
  - `holds_text(data: bytes | None) -> bool`. It is False for None and for data with no non-whitespace byte. Otherwise it is True when the data starts with a UTF-16 byte-order mark (`\xff\xfe` or `\xfe\xff`), or has no NUL byte in its first 8000 bytes (git's own binary heuristic).
  - `file_kind(path: str) -> str`: the lowercased extension with its dot, or the file name when it has no extension.

- [ ] **Step 1: Write the failing tests**
  - `test_docs_data_and_config_files_are_named_as_not_code`: True for `README.md`, `docs/guide.rst`, `notes.txt`, `data/items.json`, `ci.yml`, `pyproject.toml`, `setup.cfg`, `config.ini`, `layout.xml`, `table.csv`, `poetry.lock`, `icon.svg`.
  - `test_binary_extensions_are_named_as_not_code`: True for `logo.png`, `photo.JPG`, `lib.dll`, `font.woff2`, `archive.zip`, `doc.pdf`.
  - `test_license_files_and_dotfiles_are_named_as_not_code`: True for `LICENSE`, `sub/COPYING`, `NOTICE`, `.gitignore`, `.editorconfig`, `src/.clang-format`.
  - `test_unknown_code_files_are_not_named_as_not_code`: False for `ui/Panel.qrc`, `Makefile`, `Dockerfile`, `bin/run`, `config.h.in`, `style.css`.
  - `test_plain_text_holds_text`: `holds_text(b"x = 1\n")`.
  - `test_a_nul_byte_marks_a_binary_file`: `not holds_text(b"\x89PNG\r\n\x1a\n\x00\x00")`.
  - `test_a_nul_after_the_first_8000_bytes_still_reads_as_text`: `holds_text(b"a" * 8000 + b"\x00")`.
  - `test_utf16_text_with_a_byte_order_mark_holds_text`: `holds_text("x = 1\n".encode("utf-16"))`.
  - `test_an_empty_blank_or_unreadable_file_holds_no_text`: `holds_text(b"")`, `holds_text(b" \n\t\n")` and `holds_text(None)` are all False.
  - `test_file_kind_is_the_lowercased_extension_or_the_file_name`: `file_kind("ui/Panel.QRC") == ".qrc"`, `file_kind("build/Makefile") == "Makefile"`, `file_kind("config.h.in") == ".in"`.
- [ ] **Step 2: Run** `python -B -m pytest -q tests/test_metrics_not_measured.py`. Expected: FAIL (no module).
- [ ] **Step 3: Implement** `scripts/apm/metrics_not_measured.py`.
- [ ] **Step 4: Run** `python -B -m pytest -q tests/test_metrics_not_measured.py`. Expected: PASS.
- [ ] **Step 5: Commit** `"Decide which files with no language count as not measured"`.

### Task 4: the report lists the files it did not measure

**Files:**
- Modify: `scripts/apm/metrics.py`
  - `Report.not_measured` and `not_measured_kinds`.
  - `not_measured_candidates`.
  - `measure_files` takes candidates.
  - `measure_tree` passes them.
  - `_not_measured_section`, the last section of `render_text`.
  - Two JSON keys.
- Modify: `scripts/apm/metrics_ref.py` (`measure_at_ref` passes candidates)
- Modify: `tests/test_metrics.py`: the clean-report expected list gains `"Files not measured: 0"` as its last line. This is deliberate and stated in the commit.
- Create: `tests/test_metrics_not_measured_report.py`
- Create: `docs/adr/0009-files-with-no-scanner-are-counted-as-not-measured.md`. Modify: `docs/adr/README.md` (its row).
- Modify:
  - `docs/tutorial.md` §8: the sample output gains `Files not measured: 0` as its last line, plus one sentence after the block.
  - `skills/clean-code/SKILL.md` "Measuring": two or three sentences on the size-only languages and the not-measured line.
  - `skills/clean-code-audit/SKILL.md`: the template line becomes "N files over the limit, N wide classes, N files unmeasured, N files not measured".

**Interfaces:**
- Consumes:
  - `measure_files` and `_in_scope` (Task 2).
  - `named_as_not_code`, `holds_text` and `file_kind` (Task 3).
  - `language_for` (Task 1).
- Produces:
  - `Report(files, not_measured: tuple[str, ...] = ())`: paths in input (sorted) order. `Report(())` still works.
  - `Report.not_measured_kinds() -> dict[str, int]`: `file_kind` to count, ordered by count descending, then kind.
  - `not_measured_candidates(paths: Sequence[str], config: MetricsConfig) -> list[str]`: in scope, `language_for` None, and not `named_as_not_code`.
  - `measure_files(names, read, candidates: Sequence[str] = ()) -> Report`: a candidate is kept when `holds_text(read(name))`.
  - `measure_tree` and `measure_at_ref`: names and candidates are both taken from the tracked or ref files, filtered by `under_paths`.
  - Text: the last section is the title `Files not measured: N`, then one row per kind, `  <kind>: <count>`. It is always printed, 0 included.
  - JSON: `"files_not_measured": N` and `"not_measured": [paths]`.

- [ ] **Step 1: Write the failing tests** (in `tests/test_metrics_not_measured_report.py`, with the `git_repo` fixture)
  - `test_measure_tree_lists_text_files_with_no_language_as_not_measured`:
    - Arrange: `a.py`, `ui/Panel.qrc` (`<RCC/>\n`), `Makefile` (`all:\n\techo hi\n`), `README.md`, `logo.bin` holding `b"\x00\x01"`, and an empty `marker.typed`.
    - Assert: `report.not_measured == ("Makefile", "ui/Panel.qrc")` and `[f.path for f in report.files] == ["a.py"]`.
  - `test_the_new_size_only_languages_are_measured_not_listed`:
    - Arrange: `ui/Main.qml`, `setup.iss`, `CMakeLists.txt`, `cmake/deps.cmake`.
    - Assert: `not_measured == ()` and `sorted(f.path for f in report.plain())` lists all four.
  - `test_excluded_files_are_not_listed_as_not_measured`:
    - With `vendor/lib/Tool.qrc` and the default config, `not_measured == ()`.
    - With `MetricsConfig(include=("src/**",))` and `tools/Makefile`, `not_measured == ()`.
  - `test_paths_limit_the_not_measured_files`: with `Makefile` and `sub/Makefile`, `measure_tree(repo, MetricsConfig(), ["sub"]).not_measured == ("sub/Makefile",)`.
  - `test_measure_at_ref_lists_the_same_not_measured_files`:
    - Arrange: commit `Makefile`, `ui/Panel.qrc` and `logo.bin` (with a NUL), then delete `Makefile` from the working tree.
    - Assert: `measure_at_ref(repo, "HEAD", MetricsConfig()).not_measured == ("Makefile", "ui/Panel.qrc")`.
  - `test_render_text_ends_with_the_not_measured_total_and_kinds`: `render_text(Report((py_file,), ("a/Makefile", "ui/A.qrc", "ui/B.qrc")), Limits()).splitlines()[-3:] == ["Files not measured: 3", "  .qrc: 2", "  Makefile: 1"]`.
  - `test_an_empty_report_still_says_files_were_not_measured`: `render_text(Report((), ("x.qrc",)), Limits())` contains both `"Files over 200 lines of logic: 0 of 0"` and `"Files not measured: 1"`.
  - `test_report_json_carries_the_not_measured_files`: `report_json(Report((), ("Makefile", "ui/A.qrc")), Limits())` has `files_not_measured == 2` and `not_measured == ["Makefile", "ui/A.qrc"]`. It survives `json.dumps`.
  - `test_cli_metrics_reports_files_not_measured` (chdir to a repo holding `a.py` and `Makefile`):
    - `apm_cli.main(["metrics"])` prints `Files not measured: 1` and `  Makefile: 1`.
    - `apm_cli.main(["metrics", "--json"])` gives `files_not_measured == 1`.
  - Edit `tests/test_metrics.py::test_render_text_for_a_clean_report_lists_nothing_under_the_counts`: append `"Files not measured: 0"` to the expected list.
- [ ] **Step 2: Run** `python -B -m pytest -q tests/test_metrics_not_measured_report.py tests/test_metrics.py`. Expected: FAIL (`Report` has no `not_measured`; no last line).
- [ ] **Step 3: Implement** the interfaces above in `metrics.py` and `metrics_ref.py`.
- [ ] **Step 4: Write ADR 0009**, "Files with no scanner are counted as not measured", with its row in `docs/adr/README.md`.
  - **Context:** issue #10. A project's 82 QML files, 4 CMake files and an Inno Setup script vanished from the report, which then read `0 of 0`.
  - **Decision:** a tracked, in-scope file with no language is counted as not measured unless it is a doc, data or config file by name, a dotfile, a binary by extension, a binary by content (a NUL in the first 8000 bytes, unless it has a UTF-16 byte-order mark), or empty. The count is printed on every report, 0 included. It stays **out of the debt snapshot**: it is not debt the code can pay down, and a new not-measured file could only be "fixed" by narrowing the scope, which the ratchet already treats as a regression.
  - **Consequences:**
    - Unknown kinds (`.html`, `.css`, `.qrc`, a shebang script) are listed; the user can add a language or an exclude.
    - Each candidate file is read once more.
  - **Alternatives:**
    - Count every text file: rejected, because docs and data drown the line.
    - List only known code extensions: rejected, because it repeats the silent drop for any extension not listed.
    - Add the count to the ratchet: rejected, for the reason under Decision.
- [ ] **Step 5: Update the docs** listed under Files.
- [ ] **Step 6: Run** `python -B -m pytest -q tests/test_metrics_not_measured_report.py tests/test_metrics_not_measured.py tests/test_metrics.py tests/test_metrics_ref.py tests/test_cli_metrics.py tests/test_cli_metrics_classes.py tests/test_metrics_class_report.py tests/test_audit_scan.py tests/test_audit_report.py tests/test_cli_audit.py tests/test_own_limits.py tests/test_docs.py tests/test_skills.py tests/test_skills_clean_code.py`. Expected: PASS.
- [ ] **Step 7: Commit** `"List the files metrics did not measure, with a total, so an empty report never reads as clean"`. The body says the clean-report test gained the new last line.

### Task 5: a newly measured language's long files are not new debt

**Files:**
- Create: `scripts/apm/debt_languages.py` (snapshot dicts only, standard library only, like `debt_classes.py`)
- Modify:
  - `scripts/apm/debt.py`:
    - add `_language_fields` to the snapshot;
    - have `compare` call `project_languages` after `project_classes` and before `project_onto`;
    - join both kinds of notes into `newly_measured`;
    - update its field comment.
  - `scripts/apm/debt_store.py`: `_SHAPES` gains `"measured_languages": _strings` and `"file_languages": _str_map`.
  - `scripts/apm/cli_debt.py`: `TRACK_HINT = "Run \`apm debt baseline\` to start tracking the newly measured classes and files"`.
- Create: `tests/test_debt_languages.py`, `tests/test_cli_debt_languages.py`
- Create: `docs/adr/0010-a-newly-measured-languages-file-sizes-are-not-new-debt.md`. Modify: `docs/adr/README.md` (its row).
- Modify: `docs/tutorial.md` §8, adding one sentence: after an upgrade measures a new language, its long files show under "newly measured, not new debt:" until `debt baseline` records them.

**Interfaces:**
- Consumes: `LANGUAGE_NAMES` (Task 1).
- Produces:
  - The snapshot fields `"measured_languages": list(LANGUAGE_NAMES)` and `"file_languages": {path: language}`, for every file in `files` (the over-limit files).
  - In `debt_languages.py`:
    - `LEGACY_LANGUAGES: tuple[str, ...]`: the 22 names at ea0e5e7, as listed in Task 1. A baseline with no `measured_languages` measured these.
    - `project_languages(base: Mapping, current: dict) -> tuple[dict, list[str], list[str]]`. It returns:
      - `current` without the over-limit files that are absent from `base["files"]` and whose recorded language is not in the base's measured languages, with `totals.long_files` and `totals.excess_file_lines` recomputed from what is kept (excess against `current["limits"]["file"]`);
      - the regressions, `language no longer measured: <name>`, for each base language the current snapshot lacks;
      - the notes, `newly measured: <path> (<N> lines; the baseline did not measure <language> files)`.
    - A file with no recorded language is kept and judged as measured.

- [ ] **Step 1: Write the failing tests** (`tests/test_debt_languages.py`, built with `debt_helpers.file_metric` and `snap`; `_legacy` drops the two new fields)
  - `test_snapshot_records_the_measured_languages_and_the_language_of_each_long_file`: for `snap(file_metric("ui/Main.qml", lines=250, language="QML"), file_metric("a.py"))`, `"QML" in result["measured_languages"]`, the list is sorted, and `result["file_languages"] == {"ui/Main.qml": "QML"}`.
  - `test_a_legacy_baseline_does_not_count_a_newly_measured_long_file_as_debt`:
    - Compare `_legacy(snap(file_metric("a.py")))` with `snap(file_metric("a.py"), qml_250)`.
    - Assert: `not result.worse`; `result.newly_measured == ("newly measured: ui/Main.qml (250 lines; the baseline did not measure QML files)",)`; no regression mentions `long_files` or `excess_file_lines`.
  - `test_a_new_long_python_file_is_still_a_regression_against_a_legacy_baseline`: `"new over-limit file: b.py (250 lines)"` is in the regressions.
  - `test_once_recorded_a_long_qml_file_that_grows_is_a_regression`: `compare(snap(qml_250), snap(qml_260))` has `"grew: ui/Main.qml 250 → 260"` in its regressions and `newly_measured == ()`.
  - `test_a_new_long_qml_file_against_a_baseline_that_measured_qml_is_a_regression`: `compare(snap(), snap(qml_250))` gives `"new over-limit file: ui/Main.qml (250 lines)"`.
  - `test_dropping_a_language_from_the_current_snapshot_is_a_regression`: a current snapshot whose `measured_languages` lacks `"QML"` gives `"language no longer measured: QML"`.
  - `test_a_long_file_with_no_recorded_language_is_judged_as_measured`: a legacy base against `{**snap(qml_250), "file_languages": {}}` gives `"new over-limit file: ui/Main.qml (250 lines)"`.
  - `test_a_hand_broken_language_field_is_rejected`: parametrized over `("measured_languages", "QML")` and `("file_languages", {"a": 3})`. `validate` raises `DebtError` matching `"has the wrong shape"`.
  - `tests/test_cli_debt_languages.py`, using a repo fixture holding a committed 250-line `ui/Main.qml` and an initialized profile:
    - `test_check_passes_on_an_unchanged_long_qml_file_measured_for_the_first_time`:
      - Arrange: run `debt baseline`, then rewrite the file as 0.3.2 would have written it: drop the two fields, drop `ui/Main.qml` from `files`, and set `long_files` and `excess_file_lines` to 0.
      - Assert: `debt check` exits 0, and the output holds `newly measured, not new debt:` and `TRACK_HINT`.
    - `test_after_a_baseline_a_grown_qml_file_fails`: after `debt baseline`, append 10 lines; `debt check` exits 1 with `grew: ui/Main.qml`.
- [ ] **Step 2: Run** `python -B -m pytest -q tests/test_debt_languages.py tests/test_cli_debt_languages.py`. Expected: FAIL (no fields; `new over-limit file` reported as a regression).
- [ ] **Step 3: Implement** the interfaces above.
- [ ] **Step 4: Write ADR 0010**, "A newly measured language's file sizes are not new debt". Status: `Accepted, <date>. Builds on ADR-0003.` ADR 0003 itself is not edited.
  - **Context:** after Task 1, a 0.3.2 baseline that never measured QML meets a 250-line `.qml` file, and "new over-limit file" plus "total rose: long_files" would fail every upgraded project on code nobody touched.
  - **Decision:** the rules above, including the legacy list.
  - **Consequences:**
    - Newly measured files are outside the ratchet until `debt baseline` runs. The hint says so.
    - The rule covers every future size-only language without further change.
    - The snapshot stays at version 1.
  - **Alternatives:**
    - Bump the version: rejected, as in ADR 0003.
    - `--accept`: rejected, because it records a false reason.
    - Key files by language: rejected, because it renames every recorded file.
- [ ] **Step 5: Add** the tutorial sentence.
- [ ] **Step 6: Run** `python -B -m pytest -q tests/test_debt_languages.py tests/test_cli_debt_languages.py tests/test_debt.py tests/test_debt_classes.py tests/test_debt_store.py tests/test_debt_scope.py tests/test_debt_match.py tests/test_debt_moves.py tests/test_debt_tighten.py tests/test_debt_sources.py tests/test_debt_guards.py tests/test_cli_debt.py tests/test_cli_debt_classes.py tests/test_audit_report.py tests/test_gate.py tests/test_cli_gate.py tests/test_docs.py`. Expected: PASS.
- [ ] **Step 7: Commit** `"Treat a newly measured language's long files as notes, not new debt"`.

### Task 6: the merge gate
- [ ] **Step 1: Run** `<CLI> gate 10`. This is the one full-suite run, right before the PR. Expected: every criterion passes.

---

## Structural acceptance criteria (checked before the PR)
- **Sizes.** Every file this plan creates or changes is at most 200 lines of logic, and every function at most 15, measured by `<CLI> metrics`.
  - `scripts/apm/metrics.py` (131 at ea0e5e7) and `scripts/apm/metrics_lang.py` stay at or under 200.
  - `metrics_not_measured.py` and `debt_languages.py` are new and each well under 200.
  - The new test files are under 200 too.
- **Imports.** `metrics_not_measured.py` and `debt_languages.py` import only the standard library. `debt_languages.py` works on snapshot dicts only, like `debt_classes.py`.
- **No duplicate loop.** `metrics_ref.py` has no read-decode-measure loop of its own; it calls `metrics.measure_files`.
- **Report shape.**
  - The text report's last metrics line is always `Files not measured: N`, followed by `  <kind>: <count>` rows. The layer-overlap lines still come after it.
  - The JSON has `files_not_measured` and `not_measured`.
- **Snapshot.** The snapshot stays `version: 1`. `debt check` passes on this repository's own `.apm/debt.json` with no re-baseline.
- **Protected files.** `git diff --name-only origin/main...HEAD -- "scripts/apm/guard*" "scripts/hook_*" hooks .apm` prints nothing.
- **Tests.** The only existing test edited is `test_render_text_for_a_clean_report_lists_nothing_under_the_counts`, which gains one expected line. No test is skipped or weakened.
- **Documents.**
  - `docs/adr/0009-files-with-no-scanner-are-counted-as-not-measured.md` and `docs/adr/0010-a-newly-measured-languages-file-sizes-are-not-new-debt.md` exist and are listed in `docs/adr/README.md`. Renumber them if #27's ADR 0008 has not landed.
  - `docs/tutorial.md` §8, `skills/clean-code/SKILL.md` ("Measuring") and `skills/clean-code-audit/SKILL.md` (template) describe the new line.
- **Generic names.** `git grep -n -i -E "xp12|x-plane|virtualairline"` over the files this branch changes prints nothing.
- **Gate.** `<CLI> gate 10` passes.

## Allowlisted actions
None. No task deletes a file, writes a protected path or runs a destructive command.

## Risks
- **ADR numbers.** These collide with #27 (ADR 0008), and both branches add rows to `docs/adr/README.md`. The manager resolves this when main is merged in.
- **Heuristic comment syntax** for Inno Setup and CMake. The known limits are in the `metrics_lang.py` docstring. The size numbers can be off by a few lines in odd files.
- **The doc, data and config list is short on purpose.** Web and Qt-resource files (`.html`, `.css`, `.qrc`, `.ui`) will show as not measured. That is visible, not silent, but it may read as noise in some projects.
- **Speed.** Every language-less candidate in scope is read once more, through `git show` per file in `--ref` mode. Media files with known extensions are skipped by name.

---

# Plan summary (for the user)

```
Plan for #10: metrics silently skips files it has no scanner for

What changes
metrics now measures QML, Inno Setup (.iss) and CMake files for size, the way it already measures
PowerShell. Every report ends with "Files not measured: N", listing by kind any code-like file it
still cannot read, so a report on code it never looked at can no longer pass for a clean one.
Upgrading will not fail your debt check: newly measured files show up as notes until you record them.

How it will be built
6 tasks. The three new languages; a small cleanup so the working tree and a git ref are measured
the same way; the rule for which files count as "not measured"; the new report line; the debt
check's handling of newly measured files; then the gate. The first three run at the same time.

Rough time
About two hours, with the gate and the pull request at the end.

What I decided for you
- Docs, data and config files (.md, .json, .yml, .txt, LICENSE, dotfiles) and binary files are left
  out of "not measured"; anything else with no scanner is listed. Cost if wrong: a project with
  many .html/.css or Qt .qrc files sees them listed until a language or an exclude is added.
- Binary is detected by a NUL byte in the first 8000 bytes (git's own rule) plus a list of known media
  and archive extensions; UTF-16 text with a byte-order mark counts as text. Cost if wrong: an odd
  text file is skipped silently.
- The "not measured" count stays out of the debt ratchet: it is not debt the code can pay down.
  Cost if wrong: a new unreadable file does not fail the debt check, only shows in the report.
- A long file in a newly measured language is a note, not new debt, until `debt baseline` runs,
  the same rule ADR 0003 set for classes. Cost if wrong: such a file can grow unseen until then.
- Recorded as ADR 0009 and ADR 0010.

How it will merge
A merge commit (the profile's merge style).

The full plan: docs/plans/2026-10-24-issue-10-metrics-not-measured.md
Reply "approved" to start. After that I will send one plain line after each task and come back
when it is merged, unless something comes up the plan did not settle.
```

## Pre-flight scan
| Check | Finding |
|---|---|
| Task 1 → Task 5 | Task 1 produces `LANGUAGE_NAMES`; Task 5 consumes it through `debt_languages` and the snapshot. Consistent. |
| Task 2 → Task 4 | Task 2 produces `measure_files(names, read)` and `_in_scope`; Task 4 extends `measure_files` with `candidates=()` and uses `_in_scope`. Both edit `metrics.py` and `metrics_ref.py`, so they run in order. |
| Task 3 → Task 4 | Task 3 produces `named_as_not_code`, `holds_text` and `file_kind`; Task 4 consumes all three. Consistent. |
| Task 4 and Task 5: shared files | `docs/adr/README.md` and `docs/tutorial.md` §8, so they run in order (the plan already says so). |
| Task 1 self-consistency | At ea0e5e7, `language_for` gives None for `.qml`, `.iss`, `.cmake`, `CMakeLists.txt`, `notes.txt`. The CMake and QML line counts assume that a line holding only `)` or `}` is not logic, which the QML case (expected 3) relies on too. |
| Task 3/4 self-consistency | `Makefile`, `.qrc`, `Dockerfile`, `.css`, `bin/run` and `config.h.in` have no language at ea0e5e7, so the not-measured cases hold. |
| Task 4: existing test | `tests/test_metrics.py:223` expects exactly five lines; the plan's single added line matches it. |
| ADR numbers | #27 adds ADR 0008 and merges first; 0009 and 0010 stand. The README rows will conflict when main is merged in; the manager resolves it. |
| Rubric conflicts | None. |

*Ruling before Task 1: `.ts` files read as Qt translations are out of scope; filed as #29. Cost if wrong: none to this plan.*

*Ruling during Task 4 (2026-10-24): `not_measured_kinds` is a module-level function, `not_measured_kinds(report)` in `metrics.py`, not a `Report` method. As a method it made `Report` a class with 7 public methods, which `debt check` reports as a new wide class. Task 4 also adds `choose_files(files, config, paths)`, shared by `measure_tree` and `measure_at_ref`, so the two cannot drift apart. Task 5 consumes neither. Cost if wrong: one call site moves if the method is wanted later.*

*Ruling on the final review (2026-10-24): no must-fix findings. One fix round takes these:*
- *SF1: rename the local `unmeasured` in `measure_files` to `not_measured`.*
- *SF2: the skill and ADR 0009 say "add an exclude under `standard.metrics`, or file an issue asking for the language". A profile cannot add a language.*
- *SF3 (folded in, not a follow-up): `apm audit` drops the same files silently, so it is the bug #10 names, on the init path. `audit --json` gains `files_not_measured`, and the text report gains one line naming the count, so a "fresh" verdict for a project whose code is all unscanned also says how many files were not measured. Cost if wrong: one more line in the audit report.*
- *Suggestion 1 (folded in): an empty or blank UTF-16 file, a byte-order mark only or whitespace only, holds no text, as Review Focus 4 says.*
- *Suggestions 2, 3 and 4 (folded in, wording only): the `not_measured_kinds` docstring gives its design reason (a rendering helper), and the two module helpers used only inside `metrics.py` become private; the audit template reads "N files whose functions were not measured, N files not measured at all"; ADR 0009 cites ADR-0010 for the newly-measured rule, and no longer says "only" narrowing the scope fixes a not-measured file.*
- *Suggestion 5 (reading a candidate whole for the 8000-byte check) is deferred: the plan's Risks section accepts it. Suggestion 6 is already a documented limit. Suggestion 7 is noted: the plan's generic-names grep matches the rule's own text in this plan file.*

## Deferred findings
- Final review: a not-measured candidate is read whole for the 8000-byte binary check; reading only the first 8000 bytes would be cheaper for large files.
