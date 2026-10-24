# ADR-0006: The main session may write Claude Code's memory folder for its project, and a file-tool write outside the project cannot be approved

## Status

Accepted, 2026-10-18. Builds on ADR-0002 and ADR-0005. Amended by ADR-0007.

## Context

Issue 19 reported that the guard blocks Claude's own memory folder, and that the approval it offers cannot
unblock it. A session in another project tried to edit
`~/.claude/projects/<slug>/memory/MEMORY.md`, was denied as "outside the project", and recording the approval the
denial offered changed nothing. Three causes, each confirmed on the repo code:

1. **Outside the project, nothing can lift the denial.** `check_write` returns "outside the project" when the
   target is under no allowed root, and it does that before it reads any approved path. So no `--path` approval
   applies there.
2. **An approval glob is matched against a checkout-relative path, never an absolute one.** Even inside the
   project, `data/fleet.db` can be approved and `C:/repo/data/fleet.db` cannot.
3. **The denial offers `--path` every time in the main session,** including for command denials, which never
   read path approvals, and for `.apm/state/`, which no approval lifts.

A probe confirmed it: an Edit of the memory file in the main session was denied, and stayed denied with an
approval for the exact path, its forward-slash form, `*/memory/**` and `**`.

ADR-0002 sets the threat model: a cooperative manager or worker making a mistake. Its rule 2 needs a reading for
this change, given under Decision.

## Decision

**The main session may write, with the Write, Edit or NotebookEdit tool, the memory folder Claude Code keeps for
this project. Workers may not.**

- **The folder.** `memory_folder(main_root, config_dir)` in `scripts/apm/guard_paths.py` returns
  `config_dir / "projects" / <slug> / "memory"`. The slug is `str(main_root)` with every character outside
  `[A-Za-z0-9]` turned into `-` (`C:\Users\darby\source\repos\Agentic Project Management` becomes
  `C--Users-darby-source-repos-Agentic-Project-Management`). `main_root` is the main checkout, not the worktree:
  every worktree of a repository shares one memory folder. The function reads no file and no environment.
- **The config dir.** The hook (`_config_dir` in `scripts/hook_pretooluse.py`) reads `CLAUDE_CONFIG_DIR` when it
  is set and absolute, and uses `~/.claude` otherwise. A relative or empty value is ignored. The value comes from
  the user's shell or settings, not from a repository file, so a repository cannot widen the guard.
- **Where it applies.** `decide` takes the config dir and, for an event with no `agent_id` only, adds the folder
  to the roots a file write may land in, beside the temp roots. Only paths strictly under the folder open: the
  folder path itself does not. The path is normalized and resolved with `realpath` first, so `..` and a
  case-folded Windows path are read as they land. The `.apm/state/` check still comes first, and a path in the
  folder that sits inside a git checkout is still matched against the protected globs.
- **A linked folder opens nothing.** The folder opens only when it is a real folder: no part of its path below
  the config dir is a symlink or a junction. The guard resolves the config dir first, because `~/.claude` may
  legitimately sit behind a link, then compares the `realpath` of the folder with its normalized path (both
  case-folded on Windows). Any link below the config dir makes them differ. A `memory` folder, or its
  `projects/<slug>` parent, that is a link to a broader folder, such as a notes vault, gets the old denial for
  both the link path and the link target. Otherwise the target's `realpath` would put everything under the vault
  in reach of the file tools. A `memory` folder that does not exist is not a link, and no file is under it.

How ADR-0002 rule 2 is read. Read literally, it makes any denial that becomes an allow a must-fix, which no
false-positive fix can meet. The user approved, on 2026-10-18, reading it for this change as ADR-0005 did: never
allow a call that does what the guard must stop. The approval came with the plan for issue 19. Under that reading
exactly one class of denial becomes an allow:

- (a) A Write, Edit or NotebookEdit call from the main session whose target, after normalization and `realpath`,
  is strictly under `<config dir>/projects/<slug of main_root>/memory/`. Writing Claude Code's own memory for
  this project is none of the things ADR-0002 says the guard must stop.

Every other verdict is unchanged. The tests pin the realistic neighbors: a worker's write (Write, Edit and
NotebookEdit), the rest of the config dir (`settings.json`, `settings.local.json`, `CLAUDE.md`, a plugin file),
another project's memory folder, the worktree slug's memory folder, a file in the slug folder
(`<slug>/session.jsonl`), a memory folder or slug folder that is a link, the siblings
`memory2/` and `memory-old/`, `..` out of the folder, the folder path itself, the folder under `~/.claude` when
`CLAUDE_CONFIG_DIR` points elsewhere, and the in-project protections (`.git/**`, `.apm/state/**`, profile paths).

**A file-tool write outside the project stays unapprovable, and the denial stops offering an approval for it.**
Letting an absolute `--path` glob reach outside the project would add a second, wider class of allows for every
path a user might approve. A `--path` approval is checkout-relative, so the denial for a protected file names
the relative path to approve. The denial for such a write says no approval lifts it and asks the user to make the change;
the denial for a protected file names the checkout-relative path to approve; and the denial for APM state
points to the CLI. Each is a remedy in `guard._REMEDIES`, pinned by `tests/test_guard_remedies.py`.

## Consequences

- A session in the main checkout or in any worktree can maintain its project's memory without an approval.
- Known limits, each failing closed: the derived folder does not match, and the write is denied as before, a false
  positive only.
  - A long path that Claude Code truncates (and may hash) when it names the folder.
  - An `autoMemoryDirectory` setting that moves the folder. The guard does not read it.
  - A checkout reached through a symlink, where `realpath` differs from the path Claude Code used.
  - A symlink or junction inside the memory folder that points out of it. `realpath` follows it, and the target
    is outside the folder.
  - A mapped or `subst` drive, where `.resolve()` can turn `Z:\` into a UNC path, so the slug differs from the
    one Claude Code used.
  - On Windows, a `CLAUDE_CONFIG_DIR` written without a drive (`/c/Users/...`). `is_absolute()` rejects it, so
    the hook falls back to `~/.claude`.
- On macOS, a case-variant path to the memory folder is denied, which is only a false positive.
- If `~/.claude` is itself a git repository, this project's protected globs apply under it, which is again only
  false positives.
- Two checkouts whose paths sanitize alike (`C:\a b` and `C:\a-b`) share one folder. Claude Code shares it too.
- Bash writes outside the project are not checked by the guard, before or after this change. They are not changed
  here.

## Alternatives considered

- **Any `<config>/projects/*/memory/**`.** Wider: another project's memory would open.
- **The hook's `transcript_path`.** For a worktree session its folder is the worktree's slug, not the memory
  folder's.
- **Reading `autoMemoryDirectory`.** A repository's settings may set it, so a repository file could then widen
  the guard.
- **A profile setting.** Manual on each machine, and the main session can edit the profile.
- **Absolute `--path` globs that apply outside the project.** A wider class, as above.
