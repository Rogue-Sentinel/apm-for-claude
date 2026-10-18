# Defense in depth

When you fix a bug caused by invalid data, one check at one place feels sufficient. But a single
check can be bypassed by another code path, by a later refactoring, or by a test double. **Validate
at every layer the data passes through, so the bug becomes structurally impossible.**

One check says "we fixed the bug". Checks at every layer say "we made the bug impossible".

## Contents

- Why several layers
- The four layers
- Applying the pattern
- The worked example
- The key insight

## Why several layers

Different layers catch different cases:
- entry validation catches most bugs;
- business logic catches edge cases;
- environment guards prevent dangers specific to one context;
- debug instrumentation helps when every other layer fails.

## The four layers

### Layer 1: entry point validation

Reject plainly invalid input at the boundary.

```
function createProject(name, workingDirectory):
    if workingDirectory is empty or only whitespace:
        fail "workingDirectory cannot be empty"
    if not exists(workingDirectory):
        fail "workingDirectory does not exist: " + workingDirectory
    if not isDirectory(workingDirectory):
        fail "workingDirectory is not a directory: " + workingDirectory
    ...
```

### Layer 2: business logic validation

Check the data makes sense for this operation.

```
function initializeWorkspace(projectDir, sessionId):
    if projectDir is empty:
        fail "projectDir is required to initialize a workspace"
    ...
```

### Layer 3: environment guards

Refuse an operation that is dangerous in a specific context.

```
function initRepository(directory):
    if running under tests:
        target = normalize(resolve(directory))
        temporary = normalize(resolve(temporaryDirectory()))
        if target is not under temporary:
            fail "refusing to initialize a repository outside the temporary directory during tests: " + directory
    ...
```

### Layer 4: debug instrumentation

Capture the context for forensics.

```
function initRepository(directory):
    logDebug("about to initialize a repository", {
        directory: directory,
        currentDirectory: process.currentDirectory(),
        stack: captureStackTrace(),
    })
    ...
```

## Applying the pattern

When you find a bug:

1. **Trace the data flow.** Where does the bad value come from, and where is it used?
2. **Map every checkpoint** the data passes through.
3. **Add validation at each layer:** entry, business, environment, debug.
4. **Test each layer.** Try to bypass layer 1, and check that layer 2 catches it. Each layer gets its
   own test, written first and seen failing, like any other behavior (`apm:test-first`).

## The worked example

Bug: an empty `projectDir` caused a repository to be initialized in the source tree.

Data flow:
1. Test setup produces an empty string.
2. `Project.create(name, "")`.
3. `WorkspaceManager.createWorkspace("")`.
4. The initialization runs in the process's current directory.

The four layers added:
- Layer 1: `Project.create()` checks the directory is not empty, exists, and is writable.
- Layer 2: `WorkspaceManager` checks `projectDir` is not empty.
- Layer 3: the worktree manager refuses to initialize outside the temporary directory during tests.
- Layer 4: a stack trace is logged before every initialization.

Result: the whole suite passed, and the bug could no longer be reproduced.

## The key insight

All four layers were needed. During testing, each caught a case the others missed: different code
paths bypassed the entry validation, test doubles bypassed the business checks, edge cases on
another platform needed the environment guard, and the debug logging exposed a structural misuse.
**Do not stop at one validation point.**

Keep each layer inside the standard: a check is a small, named function (`apm:clean-code`), the
environment guard sits at the edge rather than in the core (`apm:clean-architecture`), and a
failure is a value or a clear error, never a silent default (`apm:functional-core`).
