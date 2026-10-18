# Evidence by language

The scorecard's dimensions are language-neutral. This file gives the concrete patterns to count for
each of them in the common languages. Count each pattern on both sides, with `git grep -c -E` (see
[scoring-evidence-guide.md](scoring-evidence-guide.md)), and read a sample of the matches before
scoring on a count: a pattern can also match a comment or a string.

Patterns are POSIX extended regular expressions, as `git grep -E` reads them. A dimension a language
section leaves out has no pattern worth counting there; read the code instead. A project adds its own
patterns under `standard.review_patterns` (see [the last section](#project-patterns-standardreview_patterns)).

Sizes are never counted with a pattern: `apm metrics` measures functions and files for every
language in this file.

## TypeScript

Also JavaScript. Pathspecs: `'*.ts' '*.tsx'`, and `'*.js' '*.jsx'` where the project has them.

- **Type and contract safety.** Unsafe casts: `as any`, `as unknown`, `: any`, `Record<string, any>`.
  Suppressions: `@ts-ignore`, `@ts-expect-error`, `@ts-nocheck`, `eslint-disable`. Strict mode:
  `"strict": true` under `"compilerOptions"` in `tsconfig.json`
  (`grep -A5 '"compilerOptions"' tsconfig.json | grep strict`). Boundary validation: a schema
  library (`z\.object\(`, `yup\.object\(`) at the edges.
- **State management.** Shared state: `createContext\(`, `configureStore\(`, `createSlice\(`,
  Zustand `create\(`, `atom\(`. Reusable state units: custom hooks
  `(function|const) use[A-Z]`. Memoization and derived state: `useMemo\(`, `useCallback\(`,
  `createSelector\(`, `computed\(`, `signal\(`. Prop drilling is traced by hand: follow one prop
  from the component that owns it to the one that reads it.
- **Module architecture.** Components per file: `export (default )?(function|const) [A-Z]`. Largest
  React component files: `git ls-files '*.tsx' '*.jsx' | xargs wc -l | sort -rn | head -20`.
- **Entry points and routing.** Lazy loading: `React\.lazy\(`, `lazy\(\(\) => import\(`,
  `loadable\(`, dynamic `import\(`. Nested layouts: `<Outlet`, `children:` in a route table. Error
  and not-found routes: `path="\*"`, `errorElement`. Breadcrumbs: `[Bb]readcrumb`. Prefetching:
  `prefetch`.
- **Styling and presentation.** Inline styles: `style=\{\{`, `style=\{`. Style modules:
  `git ls-files '*.module.css' '*.module.scss' | wc -l`. Tokens: custom properties `var\(--`, a
  theme object.
- **Testing.** Files: `git ls-files '*.test.*' '*.spec.*' | wc -l`. Cases: `(it|test)\(`, suites
  `describe\(`. Skips: `(it|test|describe)\.skip\(`, `xit\(`, `xdescribe\(`, `\.only\(`. Shallow
  renders: `shallow\(`. Accessibility tests: `jest-axe`, `toHaveNoViolations`, `axe\(`. End-to-end:
  `playwright`, `cypress` directories.
- **Error handling.** Boundaries: `ErrorBoundary`, `componentDidCatch`. Handling: `try \{`,
  `\.catch\(`. Swallowed: `catch *(\([^)]*\))? *\{ *\}`. Query error states: `isError`, `error:`.
- **External integration.** Raw calls: `fetch\(`, `axios\.`. Cancellation: `AbortController`,
  `signal:`, a cleanup function returned from `useEffect`. Libraries with caching and retries:
  `useQuery\(`, `useSWR\(`, `retry:`. Typed responses: `fetch` results cast with `as` are not typed.
- **Accessibility.** ARIA: `aria-`, `role=`. Semantic HTML:
  `<(main|nav|aside|header|footer|section|article)`. Images: `alt=`. Click handlers on
  non-interactive elements: `<div[^>]*onClick` (then check for `onKeyDown` and `tabIndex`).
- **Code duplication.** Hardcoded addresses: `https?://`. Repeated helpers: search for the name of
  each helper found in more than one file.
- **Developer experience and maintainability.** ESLint: `eslint.config.*`, `.eslintrc*`. Prettier:
  `.prettierrc*`. Pre-commit: `.husky/`, `lint-staged`. Import sorting: `simple-import-sort`,
  `import/order`. Path aliases: `"paths"` in `tsconfig.json`, an `@/` prefix. CI: `.github/workflows/`.

## Python

Pathspec: `'*.py'`.

- **Type and contract safety.** Suppressions: `# type: ignore`, `# pyright: ignore`, `# noqa`. The top
  type: `: Any`, `-> Any`, `dict\[str, Any\]`. Casts: `cast\(`. Strict mode: `strict = true` under
  `[tool.mypy]`, or `typeCheckingMode = "strict"` for pyright, in `pyproject.toml`. Boundary
  validation: `pydantic`, `@dataclass` with checks in `__post_init__`.
- **State management.** Module-level mutation: `^\s*global `, mutable module constants
  `^[a-z_]+ *= *(\[|\{)`. Memoization: `@(functools\.)?(cache|lru_cache|cached_property)`.
- **Module architecture.** Public surface: `__all__`. Layer crossings: `^(from|import) <outer
  package>` inside an inner package (or an `import-linter` contract).
- **Entry points and routing.** `if __name__ == .__main__.:`, `add_subparsers\(`, `@click\.command`,
  `\[project\.scripts\]`, `@(app|router)\.(route|get|post|put|delete)\(`.
- **Styling and presentation.** Desktop interfaces: `setStyleSheet\(` with literals, `QColor\(`,
  literal colors `#[0-9a-fA-F]{6}`.
- **Testing.** Files: `git ls-files 'test_*.py' '*_test.py' | wc -l`. Cases: `def test_`. Skips:
  `@pytest\.mark\.skip`, `pytest\.skip\(`, `@unittest\.skip`, `@pytest\.mark\.xfail`. Markers for
  integration tests: `@pytest\.mark\.integration`.
- **Error handling.** Bare catches: `except *:`, `except Exception *:` followed by `pass`. Chaining:
  `raise .* from `. Failure as a sentinel: `return None` in a function that can fail.
- **External integration.** Calls without a timeout: `requests\.(get|post|put|delete)\(` (then check
  for `timeout=`). Processes: `subprocess\.run\(` (check for `check=` and `timeout=`). Retries:
  `tenacity`, `Retry\(`. Cancellation: `asyncio\.timeout\(`, `wait_for\(`.
- **Accessibility.** Desktop interfaces: `setAccessibleName\(`, `setAccessibleDescription\(`.
- **Developer experience and maintainability.** `ruff`, `flake8`, `black`, `isort` in
  `pyproject.toml`; `.pre-commit-config.yaml`; `mypy` or `pyright` in CI.

## C++

Pathspecs: `'*.cpp' '*.cc' '*.cxx' '*.h' '*.hpp'`.

- **Type and contract safety.** Casts: `reinterpret_cast<`, `const_cast<`, C-style casts
  `\((int|unsigned|long|float|double|char|void) *\*?\)`, `void *\*`. Suppressions:
  `#pragma warning *\(disable`, `#pragma (GCC|clang) diagnostic ignored`, `NOLINT`. Strictness:
  `-Wall -Wextra -Werror` or `/W4 /WX` in the build files. Ownership: `new `, `delete `, `malloc\(`
  against `std::unique_ptr`, `std::make_unique`.
- **State management.** Globals: `^static [^(]*=`, `^extern `. Singletons: `::instance\(\)`,
  `getInstance\(`.
- **Module architecture.** Layer crossings: `#include "<outer layer>/` inside an inner layer.
  `apm metrics` counts both arms of a conditional-compilation block; a project needing exactness
  declares its own checker.
- **Entry points and routing.** `int main\(`. Host plugin callbacks, for example in an X-Plane plugin:
  `XPluginStart`, `XPluginEnable`, `XPluginReceiveMessage`, `XPLMRegisterFlightLoopCallback\(`,
  `XPLMRegisterCommandHandler\(`. Each callback should only forward to tested logic.
- **Styling and presentation.** Immediate-mode interfaces (ImGui): literal colors `ImVec4\(`,
  `IM_COL32\(`, and `PushStyleColor\(`, `PushStyleVar\(` with literal arguments, against named theme
  tokens. Qt: `setStyleSheet\(`.
- **Testing.** GoogleTest: `TEST(_F|_P)?\(`; disabled: `DISABLED_`, `GTEST_SKIP\(`. Catch2:
  `TEST_CASE\(`, `SECTION\(`; hidden: `\[\.\]`, `\[!hide\]`. doctest: `TEST_CASE\(`, `skip\(`.
- **Error handling.** Catch-alls: `catch *\(\.\.\.\)`. Swallowed: `catch *\([^)]*\) *\{ *\}`. Discarded
  results: `\(void\)`. Failure as a value: `std::optional`, `std::expected`, `\[\[nodiscard\]\]`.
- **External integration.** A host SDK (such as `XPLM[A-Za-z]+\(` calls) used only behind an adapter;
  network calls with timeouts (`CURLOPT_TIMEOUT`, `CURLOPT_CONNECTTIMEOUT`); threads
  `\.detach\(\)` that outlive their owner.
- **Accessibility.** Platform accessibility interfaces where the toolkit has them; for ImGui,
  keyboard navigation `ImGuiConfigFlags_NavEnableKeyboard`.
- **Developer experience and maintainability.** `.clang-format`, `.clang-tidy`,
  `compile_commands.json`, CMake presets, sanitizers in CI (`-fsanitize=`).

## C#

Pathspecs: `'*.cs'`, and `'*.xaml' '*.razor'` for interfaces.

- **Type and contract safety.** `dynamic`, `\(object\)`, `#nullable disable`, the null-forgiving
  operator `[A-Za-z0-9_)\]]!(\.|;|,|\))`, `#pragma warning disable`, `\[SuppressMessage`. Strictness:
  `<Nullable>enable</Nullable>`, `<TreatWarningsAsErrors>true` in the project files.
- **State management.** Mutable statics: `static [A-Za-z<>,]+ [A-Za-z_]+ *=`, then drop the
  `readonly` and `const` matches. View models:
  `INotifyPropertyChanged`, `\[ObservableProperty\]`.
- **Entry points and routing.** `static (async )?(void|int|Task(<int>)?) Main\(`,
  `app\.Map(Get|Post|Put|Delete)\(`, `\[Route\(`, `\[Http(Get|Post|Put|Delete)`. Blazor: `@page`.
- **Styling and presentation.** XAML literals: `(Background|Foreground|Fill)="#`, against
  `StaticResource` and `DynamicResource`. Razor: `style="`.
- **Testing.** `\[(Fact|Theory|Test|TestMethod)\]`. Skips: `Skip *=`, `\[Ignore`, `\[Explicit`.
- **Error handling.** Swallowed: `catch *(\(Exception[^)]*\))? *\{ *\}`. `async void`. Blocking on
  tasks: `\.Result[^A-Za-z]`, `\.Wait\(\)`.
- **External integration.** `new HttpClient\(` per call, against `IHttpClientFactory`. Cancellation:
  `CancellationToken`. Retries: Polly `Policy\.`, `AddResilienceHandler\(`.
- **Accessibility.** `AutomationProperties\.(Name|HelpText)`; Razor `aria-`, `role=`.
- **Developer experience and maintainability.** `.editorconfig`, `dotnet format`, `<AnalysisLevel>`,
  `Directory.Build.props`.

## Java

Pathspec: `'*.java'`.

- **Type and contract safety.** `@SuppressWarnings\("(unchecked|rawtypes)"\)`, `\(Object\)`,
  `Map<String, *Object>`, `Optional[^;]*\.get\(\)`. Strictness: `-Xlint:all`, `-Werror`, Error
  Prone, NullAway in the build.
- **State management.** Mutable statics: `static [A-Za-z<>,]+ [a-zA-Z_]+ *=` without `final`.
- **Entry points and routing.** `public static void main\(`, `@(Get|Post|Put|Delete|Request)Mapping`,
  `@RestController`.
- **Styling and presentation.** JavaFX inline: `setStyle\(`, `-fx-` in code. Swing literals:
  `new Color\(`.
- **Testing.** `@Test`, `@ParameterizedTest`. Skips: `@Disabled`, `@Ignore`, `assume(True|False)\(`.
  Integration: `git ls-files '*IT.java' | wc -l`.
- **Error handling.** Swallowed: `catch *\([^)]*\) *\{ *\}`. `printStackTrace\(\)`,
  `throws Exception`, `return null;`.
- **External integration.** Timeouts: `\.timeout\(`, `connectTimeout`. Retries and breakers:
  `@Retry`, `@CircuitBreaker`.
- **Accessibility.** `getAccessibleContext\(\)`, `setAccessibleName\(`, `setAccessibleText\(`.
- **Developer experience and maintainability.** Checkstyle, SpotBugs, PMD, Spotless in the build,
  `.editorconfig`.

## Go

Pathspec: `'*.go'`.

- **Type and contract safety.** The top type: `interface\{\}`, `[^A-Za-z_]any[^A-Za-z_]`. Unchecked
  assertions: `\.\([A-Za-z*.]+\)` without a following `, ok`. `unsafe\.`. Suppressions: `//nolint`.
  Strictness: `go vet`, `staticcheck`, a `.golangci.yml`.
- **State management.** Package-level variables: `^var `. Side effects at load: `func init\(\)`.
- **Entry points and routing.** `func main\(\)`, `&cobra\.Command\{`, `http\.HandleFunc\(`,
  `\.Handle(Func)?\(`, `\.(GET|POST|PUT|DELETE)\(`.
- **Testing.** Files: `git ls-files '*_test.go' | wc -l`. Cases: `func Test`, `t\.Run\(`. Skips:
  `t\.Skip\(`. Integration: `//go:build integration`.
- **Error handling.** Discarded errors: `_ *= `, `, _ :?= `. `panic\(`. Wrapping:
  `fmt\.Errorf\(.*%w`, against a bare `return err`.
- **External integration.** The default client: `http\.(Get|Post)\(`. Timeouts:
  `http\.Client\{` with `Timeout:`. Cancellation: `ctx context\.Context`, `ctx\.Done\(\)`.
- **Accessibility.** Web templates: `aria-`, `role=`.
- **Developer experience and maintainability.** `gofmt -l`, `goimports`, `golangci-lint`, a
  `go mod tidy` check in CI.

## Rust

Pathspec: `'*.rs'`.

- **Type and contract safety.** `unsafe `, `transmute`, narrowing casts
  `as (u8|u16|u32|i8|i16|i32|usize|isize)`, `Box<dyn Any`. Suppressions: `#\[allow\(`. Strictness:
  `#!\[deny\(warnings\)\]`, `[lints]` in `Cargo.toml`, `clippy::pedantic`.
- **State management.** `static mut`, `lazy_static!`, `OnceLock`, `Rc<RefCell<`, `Arc<Mutex<`.
- **Entry points and routing.** `fn main\(`, `#\[derive\(Parser\)\]`, `Router::new\(\)`,
  `\.route\(`, `#\[(get|post|put|delete)\(`.
- **Styling and presentation.** Immediate-mode interfaces: literal colors `Color32::from_rgb\(`.
- **Testing.** `#\[test\]`, `#\[cfg\(test\)\]`, the `tests/` directory. Skips: `#\[ignore\]`.
- **Error handling.** Panics: `\.unwrap\(\)`, `\.expect\(`, `panic!\(`, `todo!\(`, `unreachable!\(`.
  Failure as a value: `Result<`, `\?;`, `thiserror`, `anyhow`.
- **External integration.** Timeouts: `\.timeout\(`. Cancellation: `select!`,
  `CancellationToken`. Retries: `backoff`.
- **Accessibility.** `accesskit`.
- **Developer experience and maintainability.** `rustfmt.toml`, `cargo clippy -- -D warnings`,
  `cargo fmt --check`, `cargo deny` in CI.

## Any other language

For a language not listed, find its equivalents before scoring: the ways to escape or silence the
type checker, the markers of a test case and of a skipped test, the catch-all error handler, the
entry-point forms, and the lint and format configuration. Record them under `standard.review_patterns`
so the next review counts them the same way.

## Project patterns: `standard.review_patterns`

A project adds its own patterns in its profile, under `standard.review_patterns`. Each key is a
dimension name exactly as the scorecard writes it, and each value is a list of patterns (extended
regular expressions, escaped for JSON):

```json
{
  "standard": {
    "review_patterns": {
      "Styling and presentation": ["ImVec4\\(", "IM_COL32\\("],
      "External integration": ["XPLM[A-Za-z]+\\("],
      "Entry points and routing": ["XPLMRegister[A-Za-z]+Callback\\("]
    }
  }
}
```

- Each pattern is counted with `git grep -c -E` on the base and on the branch, and reported under
  its dimension as the pattern with its old and new counts.
- A pattern says what to count, not whether more is better; the evidence sentence says which way the
  count should move and why.
- Project patterns add to the language patterns above; they never replace them.
- A key that names no dimension is reported in the review as a profile mistake to fix, with its
  patterns still counted, rather than silently dropped.
