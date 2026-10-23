# ADR-0007: A shell command may write only where its session may: the project, its worktree, the temp folders, the profile's write roots, and for the main session its memory folder

## Status

Accepted, 2026-10-22. Builds on ADR-0002, ADR-0005 and ADR-0006. Amends ADR-0002 (what the guard must stop) and
ADR-0006 (its consequence on Bash writes).

## Context

Issue 20 reported that a Bash or PowerShell command that writes outside the project is never checked by the guard,
while a Write or Edit there is denied. The cause, confirmed on the code at 05f044c: `decide` sends a command event
to `_command_violation`, which runs the worker rules, the state-directory check and `check_command`.
`check_command` matches words only against the profile's protected globs, which are checkout-relative. The command
path was never given the temp roots or the config dir; only `_file_violation` was, where `write_denial` returns
"outside" for a target under no allowed root. So no command was ever compared with the project's roots. The one
outside write a worker was denied was `~/.claude/settings.json`, because its trailing sub-path matches
`WORKER_PROTECTED`.

A probe through `hook_pretooluse.run` (a temp git repository with a profile, `O` a folder beside it) found every one
of these allowed for both the main session and a worker: `echo x >> <memory>/MEMORY.md`, `echo x>>O/notes.md`,
`python x.py 2>O/err.log`, `echo x | tee -a O/a.md`, `cp README.md O/`, `mv a.txt O/a.txt`, `mkdir -p O/new`,
`touch O/t`, `sed -i 's/a/b/' O/f.md`, `git -C O commit -am x`, `cd O && echo x > f.md`, `cd O && git commit -am x`,
`echo x > ../outside.md`, and from PowerShell `Set-Content -Path O/a.md -Value x`, `'x' | Out-File O/a.md`,
`Copy-Item README.md -Destination O/r.md` and `New-Item -ItemType File -Path O/n.md`.

No instruction asked for the gap. ADR-0002's list of what the guard must stop names "writes to a protected path or
to `.apm/`" and not "writes outside the project", so the command check was built around protected globs. ADR-0006
then recorded the gap as a consequence ("Bash writes outside the project are not checked by the guard").

The transcripts on this machine show the gap is used, by mistake and by routine. A prototype of the rule was run
over every Bash and PowerShell call of the two APM projects: 9,721 main-session calls and 19,914 worker calls. With
it active, every existing guard and hook test still passed (1308), so no current verdict changed. Once the reading
below removed the false positives a naive reading gave (a `|` inside a quoted `sed` script, `>` inside a Python or
C++ heredoc body, an escaped blank in a bash path), what remained were real outside writes:

- **A cross-repository incident.** An APM-repo session ran `cd ".../VirtualAirline Plugin for XP12" && git fetch ...;
  git worktree add -b apm-init ...` and `apm setup` there. That is the incident behind the user's "stay in this
  repo" rule. Eight main-session commands operated on another checkout.
- **XP12 routines.** In the VirtualAirline XP12 project the manager deploys the built plugin to
  `D:/X-Plane 12/Resources/plugins/VirtualAirline/` and backs up `D:/X-Plane 12/Output/VirtualAirline/career.db`
  (50 distinct commands), and builds and logs out of tree in `C:/Users/darby/vab/` and `C:/vaR`, as workarounds for
  the Windows path limit (56 distinct commands). Workers wrote build logs and diffs under `C:/Users/darby/vab/` in
  110 distinct commands.
- **Worker typos and overshoots.** `> /tmp_full_report.txt` and `rm -f ../../../../../../../tmp_tb.cpp` wrote to
  the drive root, and a worker ran `mkdir -p ~/.claude/plans`.

## Decision

**A Bash or PowerShell command may write only under the main checkout, the current worktree, the temp folders, the
profile's `write_roots` and, for the main session only, this project's memory folder. Any other write target is
denied, like a file-tool write outside the project.**

- **Which sessions.** Both the main session and workers. The user chose this (option B of the issue 20 plan) in chat
  on 2026-10-22: "Approve #20 with option B (both sessions)."
- **The roots.** The roots are those of the file tools (`guard_paths.in_scope` and `roots_for`), plus `/tmp`. The
  memory folder opens only for the main session, and only for paths strictly under it, as ADR-0006 says: another
  project's memory folder, the rest of the config dir and the folder path itself stay denied. The hook adds `/tmp`
  as a shell temp root (`SHELL_TEMP_ROOTS`) because Git Bash mounts it on the Windows temp folder and macOS keeps it
  apart from `tempfile.gettempdir()`. `/tmp` and the home folder reach only the command check, never the file tools.
- **What counts as a write target** (`guard_targets.write_targets`): a redirect's file; every word of `tee`,
  `touch`, `mkdir`, `rm`, `rmdir`, `unlink` and the PowerShell `Set-Content`, `Add-Content`, `Out-File`,
  `Tee-Object`, `New-Item` and `Remove-Item` with their aliases; the destination of `cp`, `mv`, `Copy-Item` and
  `Move-Item`; the files of `sed -i`; and the working directory (or each `-C` folder) of a `git` command that is not
  a read. A write a program makes on its own (`gh`, `pip`, `npm`, `claude plugin`, `git config --global`, a script)
  is outside the model, except that a `git` command writes its working directory.
- **How a command is read for this check.** Message arguments are masked as `check_command` masks them. The body of a
  heredoc no shell runs is set aside (`strip_heredoc_bodies`): it is data to its program, a script or a message.
  The text is cut into segments only where an operator stands outside quotes (`command_readings`); when it holds
  `\"`, a PowerShell reading, where `\` escapes nothing, is cut and judged as well, and any reading that names an
  outside target denies. Each reading starts from the command's working directory, and a `cd` moves it for the
  segments after it in that reading. A device (`/dev/null`, `NUL`, `$null`) and a descriptor (`2>&1`) are no file.
  A leading `~`, `$HOME`, `${HOME}`, `$env:HOME` or `$env:USERPROFILE` names the home folder. A word that ends in a
  separator (`cp notes.md <memory>/`) names a folder written into, and is judged as a path inside it.
- **Order.** `outside_write` runs after the worker rules, the state-directory check and `check_command`, so every
  reason given before this change is given unchanged. A plan allowlist prefix covers a segment for this check as for
  `check_command`.
- **The denial.** It reads "command writes outside the project and the temp folders (<target>): <command>". In the
  main session it offers `approve --command`, which already lifts any command denial outside the state directory. A
  worker gets no remedy, as for every worker denial.
- **Write roots.** A project may list folders under the profile's `write_roots` that its shell commands write
  routinely (a deploy folder, an out-of-tree build). They apply to shell commands only, never to the file tools;
  they are folders the user approved; and they never lift another denial (a destructive command, a protected path,
  the state directory, the worker rules).

How ADR-0002 rule 2 is read: this change only adds denials, so it needs no reading of that rule. Every call allowed
before is still allowed unless it writes outside, and `write_roots` only narrows the new denial back toward the
verdict given before this change, for the folders it names.

## Consequences

- An outside write by habit or by misreading a path (an append to the memory folder from a worker, a build log in a
  home folder, a copy into another repository, a `cd` into one and a commit, a `..` or `/` overshoot) is now denied
  in both sessions and both tools.
- **Main-session routines that break**, each denied until that project lists the folder under `write_roots` or the
  user approves the one command: the XP12 deploys to the X-Plane folders, the out-of-tree builds and logs in
  `~/vab` and `C:/vaR`, a clone into `~/tmp-ccs`. In this repository, copying a session-diagnosis report to a folder
  the user names needs an approval, and so does editing global config through the shell (`~/.claude/settings.json`,
  `~/.claude/CLAUDE.md`), which the file tools already refuse.
- **The XP12 profile needs `write_roots` before that project upgrades.** Its workers write `C:/Users/darby/vab/`
  routinely, and a worker's denial has no approval.
- **The reading is new and heuristic.** It differs from `split_segments` and from ADR-0005's heredoc handling on
  purpose and only for this check. The destructive and protected checks still read every heredoc body, as ADR-0005
  says. A false positive found later is fixed by a pin and a narrower reading, never by dropping the check.
- **Known limits**, recorded in the docstrings of `guard_targets.py`, `guard_outside.py`, `guard_redirects.py` and
  `guard_data.py`: writes a program makes itself; PowerShell script blocks and the cmdlets the reader does not know;
  `bash -c '...'`, `eval` and `$(...)`; a target built from another variable, read as a relative name; `git
  --git-dir`, `--work-tree` and `git config --global`; and a session whose shell already sits outside the project,
  which is not guarded at all, because the project comes from the event's `cwd`.
- **`git` in another checkout is read by subcommand.** A read the list misses (`git -C ../o config --get x`) is a
  false denial there; inside the project every `git` command is allowed.
- The main session's `mkdir -p <memory>` is denied, as the file tools deny the folder path. The folder normally
  exists, because Claude Code makes it. With a trailing separator (`mkdir -p <memory>/`) the word is read as a
  write into the folder and is allowed; a recursive delete of the folder is still denied as destructive.

## Alternatives considered

- **Workers only (option A).** Rejected by the user: it leaves the manager's own plausible mistakes open, the
  cross-repository incident among them, and the main session's shell a side door to `~/.claude/settings.json` and
  to other projects' memory folders, which its file tools already may not write.
- **The main session checked only for other git checkouts and the config dir (option C).** Rejected: it needs a
  second, narrower root model to reason about, and still leaves a deploy to an arbitrary folder open.
- **An operating-system sandbox.** Rejected for now, as in ADR-0002: not portable across the supported platforms,
  and a different project.
- **Absolute `--path` approvals.** Rejected, as in ADR-0006: a second, wider class of allows for every path a user
  might approve. The main session's command approval covers the one-off case.
- **Write roots from an environment variable.** Rejected: a project's settings can set the environment, so a
  repository file could widen the check without the profile's review.
- **Denying every segment that is not a read after a `cd` outside.** Rejected: it denies `pytest` and builds run
  in another folder wholesale, where the write targets are what matters.
- **Reading heredoc bodies as the destructive check does.** Rejected: it produced the measured false positives
  (`>` inside Python and C++ bodies).
