# Root cause tracing

Bugs often show deep in the call stack: a repository initialized in the wrong directory, a file
created in the wrong place, a store opened with the wrong path. The instinct is to fix where the
error appears. That treats a symptom. **Trace backward through the call chain until you find the
original trigger, then fix it at the source.**

## Contents

- When to trace
- The tracing process
- Instrumenting when you cannot trace by hand
- Finding the test that pollutes
- A worked example
- The principle

## When to trace

- The error happens deep in execution, not at the entry point.
- The stack trace shows a long call chain.
- It is unclear where the invalid data came from.
- You need to know which test or which code triggers the problem.

```
is the bug deep in the stack?
    no  -> investigate where it appears
    yes -> can you trace one level up?
               yes -> trace back to the original trigger, fix there, then add defense in depth
               no  -> a dead end: fix at the symptom, and say in your report that you could not trace it
```

## The tracing process

1. **Observe the symptom.**

   ```
   error: repository initialization failed in <project>/packages/core
   ```
2. **Find the immediate cause.** What code directly does this?

   ```
   run("init", workingDirectory: projectDir)
   ```
3. **Ask what called it.**

   ```
   WorktreeManager.createSessionWorktree(projectDir, sessionId)
     called by Session.initializeWorkspace()
     called by Session.create()
     called by a test, at Project.create()
   ```
4. **Keep tracing up. What value was passed?** `projectDir` is `""`, the empty string. An empty
   working directory resolves to the process's current directory, which is the source tree.
5. **Find the original trigger.** Where did the empty string come from?

   ```
   context = setupCoreTest()                 // returns { tempDir: "" } until setup has run
   Project.create("name", context.tempDir)   // read at load time, before the per-test setup ran
   ```

## Instrumenting when you cannot trace by hand

Add logging **just before** the dangerous operation (not after it fails), with everything that
could matter:

```
function initRepository(directory):
    log_to_stderr("DEBUG init repository", {
        directory: directory,
        currentDirectory: process.currentDirectory(),
        environment: environment("APP_ENV"),
        stack: captureStackTrace(),
    })
    run("init", workingDirectory: directory)
```

- **In tests, write to the error stream directly**, not through the application's logger, which may
  be silenced during tests.
- **Include the context:** the directory, the current directory, the relevant environment
  variables, and timestamps.
- **Capture the stack:** the full call chain, not just the message.

Run the suite and keep only those lines, for example by piping the test command's combined output
through a filter for `DEBUG init repository`. Then read the stacks: look for test file names, find
the line that triggers the call, and look for the pattern (the same test, the same parameter).
Remove the instrumentation once the cause is found, unless it becomes a deliberate debug layer
(see `defense-in-depth.md`).

## Finding the test that pollutes

When something appears during a test run (a stray file or directory, a changed setting, leftover
state) and you do not know which test causes it, run the test files one at a time and stop at the
first one after which the pollution exists.

```
findPolluter(artifact, testPattern):
    files = every test file matching testPattern, sorted
            -- match the pattern with and without a leading "./", and let "**/" also match
            -- zero directories, so files directly in the base directory are not missed
    report "found N test files"

    if exists(artifact):
        report "the artifact already exists before any test has run; start from a clean copy"
        stop with a failing status                 -- never delete it to reset the search

    for index, file in files:
        report "[index/N] running file"
        runTests(file), ignoring its exit status   -- a failing test may still be the polluter
        if exists(artifact):
            report "polluter found: file created artifact"
            show the artifact's details, and how to run just this file and read it
            stop with a failing status

    report "no polluter found"
    stop with a passing status
```

- **Start clean.** Run it in a fresh copy where the artifact does not exist. If the artifact is
  already there before the first file runs, the search stops and reports it, as the pseudo-code
  does; do not delete it to reset the search. Deletion is a planned, tracked change, never a side
  effect of debugging. Because the search stops at the first file after which the artifact exists,
  it never needs to run a file with the artifact already present.
- **One file at a time**, in a fixed order, so the result is repeatable. A failing test can still
  be the one that pollutes, so a test's own result does not stop the search.
- Write the search as a small script in the system's temporary directory, outside the project so it
  is neither committed nor measured, run it through its interpreter from your worktree, and report
  the polluter it found, with the output.

## A worked example

**Symptom:** a `.git` directory appeared in `packages/core/`, inside the source tree.

**Trace chain:**
1. The repository initialization ran in the process's current directory, because its working
   directory parameter was empty.
2. The worktree manager was called with an empty project directory.
3. `Session.create()` passed the empty string down.
4. The test read `context.tempDir` at load time, before the per-test setup assigned it.
5. `setupCoreTest()` returns `{ tempDir: "" }` until that setup has run.

**Root cause:** a top-level variable read a value that is only filled in later.

**Fix:** `tempDir` became an accessor that fails loudly if it is read before setup has run.

**Defense in depth added:** `Project.create()` validates the directory; the workspace manager
rejects an empty one; the repository step refuses to run outside the temporary directory during
tests; and a stack trace is logged before every initialization. The whole suite then passed with no
pollution.

## The principle

```
found the immediate cause
    can you trace one level up?
        yes -> trace backward
                   is this the source?
                       no  -> keep tracing
                       yes -> fix at the source
                                  add validation at each layer
                                      the bug is now impossible
        no  -> NEVER fix just the symptom without saying so
```

**Never fix only where the error appears.** Trace back to the original trigger.
