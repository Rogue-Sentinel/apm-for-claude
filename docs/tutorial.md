# A short tutorial

This walks through APM on a small example project, a notes app. Each step has three parts:

- **What you say** to the manager, in plain words.
- **What it does**: the commands it runs and the shortened output.
- **What you decide**, which is often nothing.

You never type the commands yourself. They are shown so you know what is happening and can check the work.
In this tutorial `<CLI>` stands for the command line the manager runs. Everything you type is a plain
request in the chat, plus the two install lines and `/apm:setup` in section 1 (and one remove line if you
installed APM from a local folder before).

A note on the examples. The output of `audit`, `metrics`, `coverage` and `brief` was captured from the real
commands and then shortened. The output of `github file`, `github close`, `init`, `gate` and the guard's
denial is written from what the code prints, because running them here would have changed a real repository.

## 1. Install and set up

**What you say:** type the two install lines, then `/apm:setup`. These are the only commands you type,
plus one more if you installed APM from a local folder before.

If you installed APM from a local folder before, remove that marketplace first. Uninstalling the plugin
leaves it behind, and because it has the same name, adding the new one fails with only "Failed to add
marketplace." Type `/plugin marketplace remove rogue-sentinel` in Claude Code, or
`claude plugin marketplace remove rogue-sentinel` in a terminal. A first install skips this step.

```
/plugin marketplace add Rogue-Sentinel/apm-for-claude
/plugin install apm@rogue-sentinel
```

Then open Claude Code in your project and type this in the chat:

```
/apm:setup
```

**What it does:** Claude runs the setup for you. Setup prints the files it wrote, and nothing for files that
were already right.

```
.claude/settings.json
.apm/profile.json
.gitignore
```

It makes `apm:manager` the project's main agent, caps the workers at three at a time, writes a starting
profile and keeps the state folders out of git. Run it twice and the second run prints nothing.

**What you decide:** nothing. Claude ends by asking you to open a new Claude Code session in the project.
That session is the manager. The first thing the manager reads is the
briefing, and it says `No work recorded yet.`

## 2. Initialize a project

**What you say:** "Set this project up."

**What it does:** the manager loads the `apm:initializing` skill and looks before it touches anything. The
first command only reads:

**The manager runs:**

```
<CLI> audit
```

```
# Audit

## Mode

existing: the repository already has code in a language the framework measures.

## Measured at main

- long functions: 0
- long files: 0
- wide classes: 0

## In-flight work

Nothing in flight.

## Capability coverage

Not inventoried yet.

## Notes

- could not fetch origin: fatal: 'origin' does not appear to be a git repository
```

The notes are things it could not read. Here there is no `origin`, so it cannot list open issues. The
manager passes every note on to you. On a bigger codebase it sends up to three auditor workers to survey
separate parts of the tree. Then it writes the audit report for you in plain language. The report has four
parts you act on:

1. **The measurements.** How many functions and files are over the limits today. This becomes the
   starting point of the debt ratchet. Nothing has to be paid down.
2. **The coverage table.** If your project has its own style guides or instruction files, every rule in them
   gets a row saying where the framework covers it, or that you keep it as your own. The manager checks the
   table with `<CLI> coverage`, which prints `Gaps: 0` when every rule has a home.
3. **In-flight work.** Each open branch, plan or issue gets a decision from you: **finish first** (it
   merges before setup), **adopt** (it comes under the framework; an adopted plan still needs your
   approval before anything is built from it) or **leave** (recorded and left alone).
4. **Debt.** A short list of the worst offenders, grouped by area. The manager files only the ones you
   approve.

**What you decide:** the in-flight items, and then approval of the whole report. The manager does not ask
while the coverage table has a gap. When you say yes, it runs the one command that applies the audit:

**The manager runs:**

```
<CLI> init --issue 1
```

```
wrote .apm/profile.json
imported issue #7
noted: adopt issue:7
wrote .apm/debt.json
```

It also lists each decision it recorded and each issue it imported.

If it refuses, it prints one line per reason, for example `finish first: branch:dark-mode is not merged into
main yet`. Fix the cause and run it again. A second run adds nothing.

A brand-new project with no code skips the audit. The manager writes a short design with you, then a plan
for the scaffold.

## 3. Ask for a feature

**What you say:** "Add a dark-mode toggle to the settings page."

**What it does:** the manager loads `apm:running-an-issue`. First it files an issue, so the work has a number:

**The manager runs:**

```
<CLI> github file --title "Add a dark-mode toggle to settings" --body-file .apm/tmp/issue-12.md --kind feature
```

```
filed #12: https://github.com/you/notes/issues/12
```

The issue is recorded as `queued`. If the lane is free it moves on at once. It sizes the work against one
pull request, and if the request is too big it splits it into sub-issues and tells you why in a line. Then
a planner writes the plan, and the manager checks it. You do not read the plan. You get a summary:

```
Plan for #12: a dark-mode toggle

What will change: a toggle on the settings page, saved per user, and a dark color theme.
How it is built: 4 tasks. The theme and the saved setting first, then the toggle, then the tests.
Cost if wrong: about an hour of rework. Nothing touches the login code.
Rulings I made for you: the setting is saved in the browser, not on the server.
Your decisions: how should I merge this? Merge commit, squash or rebase?
```

**What you decide:** this is your one approval. Say "yes, squash" or say what to change. A partial yes
("tasks 1 to 3 are fine") is not an approval, so the manager revises the plan and asks again.

After that it does not ask permission again. It sets the issue to `building`, runs a worker per task in its
own worktree, runs independent tasks side by side (at most three), and sends one plain line after each task:

```
Task 1 of 4 done: the theme colors now come from one place. Next: the saved setting. About 25 minutes left.
Task 2 of 4 done: the setting is saved between visits. Next: the toggle. About 15 minutes left.
```

It checks each worker's work itself, with the tests for the changed files, the size limits and
`<CLI> debt check`. The whole test suite runs once, at the end. That pacing is the default; the reasons are
in [the decision record](adr/0001-lean-pacing-by-default.md). A task gets its own review only if you ask,
if the profile says `"review": "per-task"`, or if it touches a path listed under `safety_critical`.

When every task is done, a reviewer reads the whole branch once. The manager records the result and runs
the merge gate with the `apm:merge-gate` skill:

**The manager runs:**

```
<CLI> review 12 --open 0 --criteria-met --evidence "Reviewed the whole branch; no findings."
<CLI> gate 12
```

```
PASS  1  clean tree
PASS  1  base merged
PASS  1  layers
PASS  1  test
PASS  2  debt
PASS  3  review
PASS  4  plan  3 criteria
merge gate: passed
```

The four criteria are: everything passes, no debt got worse, the final review is clean and current, and the
plan's promised documents exist. The gate runs the full suite and records nothing itself. If a check fails,
it says `merge gate: 1 failed; stop and ask`, and the manager sends the fix to a worker and runs the whole
gate again.

Then the manager opens the pull request, merges it the way you chose and closes the loop:

**The manager runs:**

```
<CLI> github close 12 --pr https://github.com/you/notes/pull/13
```

It tells you what shipped, every ruling it made and what each would cost if wrong. You did not have to
say "go ahead" for any of it.

## 4. Report a bug

**What you say:** "The export button downloads an empty file when there are no notes."

**What it does:** the same path as a feature, with one difference. A bug is planned with the reproduction
first. The failing test that shows the empty file is Task 1, and the manager finds the cause with the
`apm:systematic-debugging` skill before it plans the fix. It files the issue with `--kind bug`:

**The manager runs:**

```
<CLI> github file --title "Export downloads an empty file" --body-file .apm/tmp/issue-14.md --kind bug
```

**What you decide:** the plan, the same single approval as before.

## 5. When a worker finds a bug

Sometimes a worker building one thing notices a different bug. It never fixes what is outside its task. It
writes the bug down under **found elsewhere** in its report to the manager.

**What you say:** nothing.

**What it does:** the manager sends a debugger worker to find the root cause, write the failing test and fix
it. The debugger also names the instruction that let the bug through, such as a skill or a profile fact, so
that gets fixed too. Then it sorts the bug:

- **Related to the issue being built:** the fix is its own commit on the same branch, checked and reviewed
  like any other change.
- **Unrelated:** it files a new bug issue and mentions it in its next update. The branch's diff stays about
  its own issue.

```
Task 3 of 4 done: the toggle works. Found an unrelated bug in the date format; filed it as #15. Next: the tests.
```

**What you decide:** nothing, unless the fix would change the design or make a debt number worse. Those two
are the manager's cue to stop and ask you.

## 6. Ask where things stand

**What you say:** "Where are we?"

**What it does:** the manager answers from the project record, never from memory, using `brief`:

**The manager runs:**

```
<CLI> brief
```

```
In progress
- #12 Add a dark-mode toggle to settings [building] 2/4 tasks done
  running 3: implementer (sonnet)
Queued
- #14 Export downloads an empty file

Recently merged
- #9 Add a search box
```

It reports what is done, what is running, what is blocked, what waits on you and what comes next. This
is also what it reads at the start of every session, so a closed laptop or a reset context loses at most the
task that was running.

**What you decide:** whether to keep going. It offers to continue.

## 7. When the guard says no

Safety hooks check every command and every file write. Workers are denied destructive commands (`rm -rf`,
`git reset --hard`, force-push and the like), writes to protected paths, any `gh` call that writes to GitHub
and any command that changes the project record. The manager is held to the same rules for protected paths and destructive commands, and may file and
close issues freely.

A denial reads like this:

```
APM guard: destructive command (recursive rm): rm -rf build. Ask the user in chat; if they approve this exact
action, record it with <CLI> approve --command "<the exact full command>" --reason "<why>", then retry. Run
the approve call with the Bash tool, on its own, with the command in single quotes if it holds a double quote.
```

**What you say:** the manager stops and asks you in chat, naming the exact command and why it wants it:

> I need to run `rm -rf build` to clear stale build output. The guard denied it. Do I have your approval?

If you say "yes", it records a one-off approval and retries once:

**The manager runs:**

```
<CLI> approve --command 'rm -rf build' --reason "Clear stale build output; the user approved in chat."
```

**What you decide:** whether this exact action is fine. The approval lasts 10 minutes, covers only that
command in that folder, and never carries over to a different command. If the plan you approved already
names the action, the manager needs no extra approval, because the approved plan is the allowlist.

## 8. Debt

Debt means code over the size limits: functions over 15 lines of logic, files over 200, classes with seven
or more public methods. The rule is a ratchet: **no number may get worse.**

Ask "how big is the debt?" at any time, and the manager measures:

**The manager runs:**

```
<CLI> metrics
```

```
Functions over 15 lines of logic: 0 of 17
Files over 200 lines of logic: 0 of 2
Review flags -- classes with 7+ public methods: 0
Files whose functions could not be measured: 0
Files measured for size only (no function scanner for the language): 0
Files not measured: 0
```

The last line counts the text files in scope that the tool has no language for, such as a `.qrc` file or a
`Makefile`, with one row per kind when it is not 0. Docs, data files and binaries are not counted. A count above
0 means those files were not looked at, so the report is not the whole picture.

The manager runs `<CLI> debt check` on every task and again on the feature branch. It exits 0 when nothing
got worse. When it fails, it lists each regression, for example `new over-limit function: notes/web.py::render
(16 lines)`. The manager sends the task back for a split and never loosens the baseline to get past it.

**What you decide:** only two cases. If the baseline would get *worse*, the manager names each regression and
why, and waits. Only your yes in chat lets it record that with `--accept`. If debt got *better*, it tightens
the baseline on its own.

## 9. Settings you can change

Everything lives in `.apm/profile.json`. JSON has no comments, so this example is followed by a list that
explains each key. Every key shown exists. Leave out anything you do not need.

```json
{
  "framework_version": "0.3.2",
  "protected_paths": ["config/production.yml", "migrations/**"],
  "max_workers": 2,
  "models": {"implementer": "sonnet", "reviewer": "opus"},
  "write_roots": ["~/builds"],
  "standard": {
    "limits": {"function": 15, "file": 200, "public_methods": 7},
    "metrics": {"extra_exclude": ["**/generated/**"]},
    "debt_sources": [
      {
        "name": "todos",
        "command": "python tools/count_todos.py",
        "numbers": {"todos": "todos: (\\d+)"},
        "timeout": 120
      }
    ],
    "layers": [
      {"name": "core", "paths": ["notes/core/**"], "may_import": []},
      {"name": "web", "paths": ["notes/web/**"], "may_import": ["core", "outside"]}
    ],
    "adr_dir": "docs/adr/"
  },
  "workflow": {
    "commands": {
      "build": "python -m compileall -q notes",
      "test": "python -m pytest -q",
      "checkers": [{"name": "lint", "command": "ruff check ."}]
    },
    "merge_style": "squash",
    "lanes": [
      {"name": "web", "paths": ["notes/web/**"]},
      {"name": "core", "paths": ["notes/core/**"]}
    ],
    "review": "end",
    "safety_critical": ["notes/auth/**"],
    "gate_timeout": 900,
    "base": "main"
  }
}
```

- `framework_version`: the plugin version the project was set up with. The manager tells you when the
  installed plugin is newer and offers an upgrade.
- `protected_paths`: files no one may write or delete without your approval. `.git/**` and the state folder
  are always protected.
- `max_workers`: how many workers run at once. 3 is the most; you can only lower it.
- `models`: which model each role uses (`auditor`, `planner`, `implementer`, `debugger`, `reviewer`). Roles you
  leave out keep their defaults.
- `write_roots`: folders outside the project that shell commands may write, such as an out-of-tree build folder
  or a deploy target. `~` is your home folder; a relative path is relative to the main checkout; `\` and `/` both
  work. File tools still write only inside the project. Add one only when you mean it: the guard then lets the
  manager and every worker write there. The profile refuses an entry that opens more than one folder (an empty
  entry, a drive or share root such as `C:/`, `/c` or `\\server\share`, your bare home folder, a path made only of
  `.` and `..`) and a `%...%` variable, which the guard does not expand (write `~/out`, not `%USERPROFILE%\out`).
  An entry that is the main checkout or a folder holding it (`~/source/repos`) is ignored. A refused entry blocks
  every guarded tool call, the manager's and every worker's, until you fix `.apm/profile.json` by hand.
- `standard.limits`: the size limits the ratchet uses.
- `standard.metrics`: what to measure. `extra_exclude` adds folders to skip.
- `standard.debt_sources`: your own numbers to hold the line on. Each has a `command`, a regular expression
  with one group for each number, and a `timeout` in seconds.
- `standard.layers`: which folder may import which. `outside` means libraries beyond the standard library.
- `standard.adr_dir`: where decision records live.
- `workflow.commands`: the build, the test command and any extra `checkers`. The gate cannot run without a
  `test` command.
- `workflow.merge_style`: `merge`, `squash` or `rebase`. Leave it out and the manager asks at plan approval.
- `workflow.lanes`: one issue is active per lane at a time; others wait in the queue.
- `workflow.review`: `end` for one review of the whole branch, or `per-task` to review every task.
- `workflow.safety_critical`: paths where a task always gets its own review.
- `workflow.gate_timeout`: seconds each gate command may run. The default is 1800.
- `workflow.base`: the branch that work is cut from and merged into. The default is `main`.

If the profile has a mistake, the manager says which key and why. It does not guess.

## 10. Troubleshooting

**Adding the marketplace fails with only "Failed to add marketplace."** The likely cause is an old
local-folder marketplace with the same name, left behind when you uninstalled the plugin. Remove it with
`/plugin marketplace remove rogue-sentinel` in Claude Code, or
`claude plugin marketplace remove rogue-sentinel` in a terminal, then add the marketplace again.

**There is no `gh`, or it is not signed in.** The workflow still runs. `github file` and `github close` exit
with code 2 and print what failed, then how to do it by hand:

```
apm: gh is not installed
file it by hand, then record it with apm issue N
```

File the issue yourself on GitHub, then tell the manager the number. It records it with `<CLI> issue N`. The
same goes for `audit`, which lists what it could not read in its notes.

**The gate failed.** Read the `FAIL` lines. They name the criterion, the check and the reason, and the last
lines of a failing command's output follow. The full log of each command is under `.apm/tmp/gate/`.

```
FAIL  1  test  FAILED tests/test_settings.py::test_toggle_saves - assert 'dark' == 'light'
merge gate: 1 failed; stop and ask
```

The manager sends the failure to a worker, then runs the whole gate again. Fixing and rerunning only the
failed check does not count. Exit code 2 means the gate could not run at all, usually because no test
command is declared. Ask the manager to add one to the profile; it will check with you first.

**The review is stale.** Any commit after the review makes it stale, and the gate says so:

```
FAIL  3  review  the review was of 4c1a9e2, which is not HEAD (b7d03f1)
```

Ask for a new review of the current branch. It is recorded again with `<CLI> review`. A changed branch is
a new branch, so there is no shortcut.

**A worker keeps failing.** After two failures on a task, the manager retries once on a stronger model. If
that fails too, it stops and brings it to you.

**You are not sure what a session is doing, or why it went wrong.** Ask the manager. The `apm:session-diagnosis`
skill reads the session and explains it.

**Where to go next.** The skills the manager follows are in the `skills/` folder. The three workflows used
in this tutorial are `apm:initializing`, `apm:running-an-issue` and `apm:merge-gate`.
