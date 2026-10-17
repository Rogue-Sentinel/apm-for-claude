# APM for Claude — Design

*Working name. Date: 2026-10-17. Status: draft for approval.*

## 1. Intent

A project-management framework for Claude Code in which **one manager agent runs the whole job** and
**dispatches worker subagents itself**. The user talks only to the manager. Workers never talk to the
user, and the user never copies a handoff prompt between chats.

It is modeled on [Agentic Project Management](https://github.com/sdi2200262/agentic-project-management)
(APM). APM has Planner, Manager and Worker roles that share files (Spec, Plan, Rules, Tracker,
Memory), but **the user is the relay**: they start each agent in a new conversation and carry
notices between them. That relay is the reason APM can't run unattended, and removing it is
the reason this framework exists.

Uncle Bob's **Clean Code and Clean Architecture** are built in as the working standard. The manager
and its reviewers enforce them, and leaving them to each worker's memory is not enough.

The framework has to drop into **existing projects** as well as start new ones. The first target is
`C:\Users\darby\source\repos\VirtualAirline Plugin for XP12`, a mature C++20 X-Plane plugin.

### Why now
The user wants to run in auto mode. APM's copy-paste handoffs keep the user in the loop for every step.
The user has also built up a strong personal standard (the VirtualAirline `CLAUDE.md`, 21 vendored
clean-code skills, a line-limit checker, an ADR practice, and the superpowers plugin's process). They
want that standard to become one framework they use for all projects from now on.

### What success looks like
- The user describes a feature, approves a plan, and comes back to it merged to `main`, built
  test-first, reviewed against the standard, with no copy-paste and no babysitting.
- Asking the manager "where are we?" in a fresh session gives an accurate briefing.
- No capability of the user's previous standard is lost.
- Nothing is ever destroyed by accident.

## 2. Goals, non-goals, anti-goals

**Goals**
- A single manager that plans the work, dispatches it, verifies it, records it, merges it and reports it.
- Workers chosen and briefed by the manager, including the **model** for each task.
- Clean Code and Clean Architecture as a **language-agnostic** standard, made concrete per project.
- Adoption in existing codebases through an **initial audit**, and a clean start for fresh projects.
- Durable project state, so work survives closed sessions and context resets.
- GitHub issues as the outward-facing tracker, filed and closed by the manager.

**Non-goals**
- Any assistant other than Claude Code. APM's multi-assistant support is dropped.
- Language-specific tooling built into the framework. Projects supply their own build, test and lint commands.
- CI as a merge gate. Local verification is the gate (the user's call).
- Notifications. When the manager needs the user, it waits in the chat.
- Coexisting with superpowers. The framework **replaces** it.

**Anti-goals (failure even if it "works")**
- **Deleting a database or any file by unnecessary mistake.** This is the user's top fear.
- Quietly dropping a plan's structural constraints and shipping only the features. This is the
  VirtualAirline `career_window.cpp` failure: a planned split was skipped, the file reached 2,617 lines,
  and three promised ADRs were never written.
- Lowering the bar below the user's previous standard.
- The user having to talk to a subagent, relay a message, or paste a prompt.
- Asking the user about routine work. Questions are reserved for what only they can decide.

## 3. Decisions the user made

These are fixed. The builder should not revisit them.

1. **The manager is the only point of contact.** It keeps the user updated and brings them questions
   and concerns. It owns every aspect of the workers, including which model each one runs on.
2. **The framework's standard overwrites a project's existing methodology files**, because this is the
   standard going forward. **No capability may be lost**: everything the old setup enforced or provided
   must be covered by the framework's version before the old files are replaced. Existing skills
   (VirtualAirline's clean-code skills, superpowers) are source material.
3. **Language agnostic.**
4. **Packaged as a Claude Code plugin** in its own repo, **installed once in Claude desktop**. **Init adds the
   project's folders and files** (see §5).
5. **Status is given by the manager on request.** The user doesn't read state files.
6. **The manager files and closes GitHub issues. Its own state is the source of truth.**
7. **The manager's job ends at merged to `main`.**
8. **CI is not a gate.** Tests must pass locally before anything is pushed.
9. **New features: the manager files a GitHub issue, then hands it to a planning agent.**
10. **The plan is shown to the user for approval before any building starts.**
11. **Bugs the user reports follow the feature path** (issue, planner, approval).
    **Bugs a worker finds mid-task belong to the manager.** It assigns a debugging agent to fix them
    properly, without stopping to ask the user.
12. **"Fixed properly" includes fixing the cause.** The VirtualAirline dataref unit bug came from a wrong
    instruction, so the fix corrects the instruction or project knowledge too.
13. **Superpowers is retired** in projects that use the framework.
14. **Initialization starts with an audit** that decides whether this is an existing codebase or a fresh project.
15. **At most 3 workers run at once.**
16. **Existing debt is handled as a ratchet** (accepted on the assistant's recommendation; see §8).
17. **When the user is needed, the manager waits for them.** No pings.
18. **Large or unclear features get a design conversation with the manager before planning**, then are split
    into sub-issues, each with its own plan approval. Small, clear features go straight to the planner.
19. **The framework repo is a private GitHub repo under the user's account, `Rogue-Sentinel`.**

## 4. Roles

| Role | Talks to | Default model | Job |
|---|---|---|---|
| **Manager** | User and workers | The session's model | Owns the project end to end. Files issues, dispatches workers, verifies, records state, merges, reports. |
| **Auditor** | Manager | Haiku for sweeps, Sonnet for synthesis | Surveys a codebase at init. Produces the profile draft, standards inventory and debt baseline. |
| **Planner** | Manager | Opus | Turns an issue into a plan: tasks, order, tests that prove each task, structural acceptance criteria. |
| **Implementer** | Manager | Sonnet (Haiku for mechanical edits) | Builds one task test-first in an isolated worktree. |
| **Debugger** | Manager | Opus | Root cause first, then a failing regression test, then the fix, then the fix to whatever caused it. |
| **Reviewer** | Manager | Opus | Checks a diff against the standard, the project profile and the plan's acceptance criteria. |

- Model defaults live in the framework, and a project profile can override them. If a worker fails the same
  task twice, the manager **retries on a stronger model** before escalating to the user.
- Workers never talk to the user. A worker that needs a decision returns it to the manager as a question,
  and the manager decides it or asks the user.
- Every worker returns a **structured report**: status (done / blocked / needs decision), files changed,
  commands run with their actual results, concerns, and anything found that belongs elsewhere. The manager
  trusts the commands it runs itself. A worker saying something passed doesn't count as proof.

### Platform constraint (important for the builder)
Claude Code subagents cannot spawn subagents. **The manager must therefore be the main session**, not a
subagent. The builder should find the most reliable way to make the main session *be* the manager in both
the CLI and the desktop app's Code tab. Candidates are a main-thread agent setting (`agent` in settings /
`--agent`), an output style, or a `SessionStart` hook plus instructions. The user mainly works in the
desktop app, where CLI flags aren't available.

## 5. Packaging and installation

- **Framework repo:** `C:\Users\darby\source\repos\Agentic Project Management`, made a git repo. It is a
  Claude Code plugin containing the agent definitions, the standard as skills, commands, hooks and templates,
  and a marketplace manifest. It is hosted as a **private GitHub repo under `Rogue-Sentinel`** (repo name is
  the builder's call).
- **Installed once, in Claude desktop** (the user's decision). The user adds the marketplace and installs
  the plugin at user level, so it's available in every project. Projects do not declare or pin the plugin
  in their own settings. Local-path installation is only for developing the framework itself.
- **Init writes the project's files.** Running init in a project creates everything that project needs:
  - the framework folder (name is the builder's call, e.g. `.apm/`) with the **project profile** and the
    pieces of **manager state** that live in the repo (§7);
  - the rewritten `CLAUDE.md` (the framework's methodology replaces the old methodology sections, and the
    project's domain knowledge is kept);
  - any project-level settings the framework needs, including **disabling superpowers** for that project;
  - the `apm/state` branch (§7).
  All of it is committed through the init branch and merged like any other work (§6.1).
- **The project records the framework version it was set up with**, in its profile. When the installed
  plugin is newer, the manager tells the user and offers to upgrade the project. **Upgrading a project** is
  a deliberate act: the manager rewrites what changed, reports it, and records the new version.

## 6. Workflows

### 6.1 Initialize (once per project)
1. The user runs the init command. The manager dispatches auditors (at most 3 at once) to survey the folder.
2. **The audit decides the mode.**
   - **Existing codebase:** language(s); build, test and lint commands; architecture and layers and their
     dependency direction; existing standards (**inventoried rule by rule** for the no-loss check);
     debt baseline; protected paths; work already in flight (e.g. VirtualAirline's `docs/superpowers`
     specs and plans for P1 and C1, and its open GitHub issues); and project-specific knowledge
     to keep.
   - **Fresh project:** the manager talks through architecture with the user (layers, domain boundaries,
     tooling), then scaffolds it clean from the first commit.
3. The manager presents an **audit report and a draft profile**, including the **capability coverage table**:
   each item of the old standard, and where the framework covers it. Anything not covered blocks the overwrite.
4. **The user approves.** Only then does the manager replace methodology files, write the profile, import
   in-flight work into its state, and commit it all on a branch it merges like any other work.

**In-flight work at adoption** (assistant's call):
- The audit reads from `origin/main`, because the local checkout may be stale. VirtualAirline's is 566 commits behind.
- It lists every in-flight item: unmerged branches and worktrees (e.g. `companion/writes`, 48 commits ahead
  with uncommitted files), specs and plans, and open issues. At the audit approval, the user decides each
  one: finish it first, adopt it, or leave it alone. **Init doesn't overwrite methodology files while
  the user has chosen to finish an in-flight branch first.**
- Imported plans are **not** treated as approved. Each one needs the user's approval under the framework
  before the manager builds from it.
- Stale worktrees and branches are **reported, never removed**, unless the user approves removing them.
- Existing debt issues (e.g. VirtualAirline's `[Debt]` epics #53–#66) are adopted into the ratchet's list,
  not duplicated.

**Overwrite vs keep.** The framework replaces *methodology*: the clean-code, TDD, review, refactoring and
process skills and commands, and the methodology sections of `CLAUDE.md`. It keeps *domain knowledge*,
meaning facts true only of that project, which the manager feeds to workers. In VirtualAirline that means
the `xp12-ui` and `ui-screen-structure` skills, the dataref unit warnings, environment paths, layer map,
and ADRs. Project rules that are really methodology choices (one PR per lane, merge commits never squash,
American spelling, issue forms) become **declared overrides in the profile**.

### 6.2 Feature, or a bug the user reports
1. The user describes it. The manager **files a GitHub issue** (using the repo's issue forms and labels if
   it has them) and cuts a branch from `main`, respecting any lane rules.
2. **Size check.** The manager judges whether the request is small and clear, or large or unclear (an epic,
   a `needs-design` issue, several layers, real tradeoffs). For a large or unclear request, the manager holds
   a **design conversation with the user**: one question at a time, playing back its understanding, covering
   goals, non-goals and anti-goals. It writes a design document, which a builder-check worker reads before
   the user approves it. The design is then split into **sub-issues**, and each goes through steps 3–6 with
   its own plan approval. Small, clear requests skip this step.
3. **The planner** reads the issue, codebase, profile and relevant ADRs and writes the plan. The plan must
   apply "extract before you add": when a task touches code over a limit, a pure-move refactor task comes first.
4. The manager shows the user a **plan summary**: goal, tasks in order, what will be tested, structural
   criteria, risks, and a link to the full plan file. **The user approves, edits or sends it back.**
5. **Build.** The manager dispatches implementers (at most 3 at once, only on tasks that don't share files),
   each in its own worktree. After each task: the manager runs the verification itself, a reviewer checks
   the diff, failures go back with findings, and state is updated.
6. **Integrate.** The manager merges `main` into the branch and runs the **merge gate** (§8). It pushes, opens
   the PR, and merges it with the project's merge style.
7. **Report.** It tells the user what shipped, closes the issue, and records the result.

**How many issues at once** (assistant's call). One active issue per lane. Lanes are defined in the profile,
and the default is a single lane. VirtualAirline declares two: the plugin, and the companion app. Other
issues wait in a queue the manager reports on. The 3-worker cap is shared across all active issues.

Planner questions only the user can answer come back through the manager. Once the plan is approved, the
manager runs to the merge without asking unless something comes up that the plan didn't settle.

### 6.3 A bug a worker finds mid-task
The manager dispatches a **debugger**: root cause, a failing regression test, the fix, and the correction
to any wrong instruction or project knowledge behind it. If it's related to the current work, the fix
lands on the same branch **as its own commit**. If not, the manager files an issue for it. Either way it
appears in the manager's next update. *Assistant's call:* if the fix turns out to need a design change or
to break the standard, the manager stops and raises it as a decision for the user.

### 6.4 Status
"Where are we?" returns a briefing built from state: done, in progress, blocked, waiting on the user, next.
The manager offers to continue.

### 6.5 Waiting on the user
The manager asks and waits. *Assistant's call:* while it waits, it keeps working on anything the open
question doesn't block, and parks only the blocked work.

## 7. State

The manager owns all state. Workers report and the manager records. State is updated **after every
task**, not at the end, so a crash or context reset loses at most the task that was running, and the
record shows which task that was.

Contents (format is the builder's call; it must be readable by the manager and diff-friendly in git):
- **Profile:** project facts, commands, layer map, protected paths, overrides, model overrides, framework version.
- **Debt baseline:** machine-readable numbers the ratchet compares against.
- **Per issue:** the approved plan, task ledger (status, worker, model, verification evidence),
  decisions, concerns.
- **Project log:** what shipped, when, and under which issue and PR.

GitHub issues mirror state outward. If they disagree, state wins.

**Where state lives** (assistant's call). Projects change `main` only through PRs, and the desktop app runs
each session in its own worktree, so state can't ride on a feature branch (a fresh session wouldn't see it)
or on `main` (that would bypass the PR rule). State therefore lives on a **dedicated state branch** (e.g.
`apm/state`) that only the manager commits to, pushed to `origin` after every task. Any session, worktree
or machine can read it with a fetch, and `main` keeps its PR-only rule. The profile itself is committed to
`main` through the init PR, and profile changes go through PRs like any other change.

## 8. The standard

### 8.1 Content
Language-agnostic Clean Code and Clean Architecture, carried as the framework's own skills and briefs.
**Baseline it must cover** (the union of the user's previous standard):

- From VirtualAirline: the 21 vendored skills (SOLID ×5; hexagonal ports/adapters and domain isolation;
  OOP encapsulation and composition over inheritance; FP pure functions, higher-order functions and error
  handling; refactor extract method, rename, and replace conditional with polymorphism; TDD test-first,
  red-green-refactor and arrange-act-assert; boy scout rule; detect smells); the `branch-review` 11-dimension
  scorecard (whose TypeScript- and React-specific checks become language-neutral or profile-driven); the
  `clean-code-audit` command; limits of **15 lines of logic per function, 200 per file, and a stated reason
  for 7+ public methods**; mandatory TDD with no skipped tests and no tests that wait on a person; a
  regression test before every bug fix; never weakening a test to get green; extract before you add;
  refactor and behavior never in the same commit; structural plan constraints as acceptance criteria;
  logic doesn't move sideways; ADRs for decisions; honest reporting.
- From superpowers: design-before-build with approval, written plans, subagent-driven execution with
  review between tasks, TDD, systematic debugging (root cause first), verification before claiming done,
  requesting and receiving code review, git worktrees, finishing a branch, parallel dispatch, and
  skill-writing discipline.

Limits are framework defaults that a project profile can override.

### 8.2 Enforcement
- **Mechanical where possible.** The profile lists the project's checkers (e.g. VirtualAirline's
  `check_clean_code.py`, `check_spelling.py`, `ctest`). Where a project has none, the framework supplies a
  language-agnostic default metrics tool for function and file size (builder's choice; `lizard` is one
  candidate) so the ratchet always has numbers.
- **Reviewer judgment** for what tools can't measure: naming, responsibility, dependency direction,
  whether a plan's structural criteria were truly met.

### 8.3 Debt ratchet
- The audit records the **baseline**. The merge gate **fails if any debt number gets worse**.
- Debt in code the work touches is paid down through extract-before-you-add tasks in the plan.
- Debt elsewhere becomes a **short, ranked list of GitHub issues** grouped by area. The user chooses when
  to pick them up.

### 8.4 Merge gate (all must hold to merge)
1. `main` is merged in, then the full build, tests and every profile checker pass locally, **run by the manager**.
2. No debt number is worse than the baseline.
3. The final review has no unresolved findings.
4. Every structural acceptance criterion in the approved plan is met. Promised docs and ADRs exist.

If any criterion can't be met, the manager **stops and asks**. It never merges partway, and it never
drops a criterion silently.

## 9. Safety (the top anti-goal)
Several layers, because no single rule is enough:
1. **Protected paths** in the profile: committed data (e.g. `data/fleet.db`), anything outside the repo
   (e.g. the X-Plane install and career saves in `Output/`), secrets and config. Nothing may write or
   delete them, **the manager included**. **A hook enforces this.** Relying on the instruction alone isn't enough.
2. **Destructive commands are blocked by a hook, for the manager and every worker:** `rm -rf`, `git clean`,
   `git reset --hard`, force-push, dropping or truncating a database, removing a worktree, and the like.
3. **The approved plan is the allowlist** (assistant's call). A plan may name specific protected-path writes,
   deletions or destructive steps, with a reason. For example, a task may regenerate `data/fleet.db` with
   `tools/build_fleet_db.py`. Approving the plan approves exactly those, and the hooks read the approved
   plan's allowlist. Anything **not** named in an approved plan stays blocked, and the manager must ask the
   user for that specific action. This keeps plan approval as the single touchpoint without opening a general hole.
4. **Deletion is planned, never a side effect.** It happens as a tracked git change. An unplanned deletion
   is flagged and reverted in review.
5. **Workers build in isolated worktrees**, so a misbehaving worker damages only its own copy.

## 10. Prior art
- **APM:** borrow the roles, the shared-file memory, and planning before implementation. Drop the
  user-as-relay, the handoff prompts and the multi-assistant CLI.
- **Superpowers:** source for process discipline (§8.1). Retired in adopted projects.
- **VirtualAirline's `CLAUDE.md` and skills:** source for the standard, and the first adoption target.

## 11. Left to the builder
- How the main session becomes the manager in CLI and desktop (§4 constraint).
- File formats and the folder name for profile and state. Plugin layout and command names.
- How hooks tell manager tool calls from worker tool calls (and the fallback if they can't).
- How to enforce the 3-worker cap.
- How worker worktree branches are integrated into the feature branch.
- The default metrics tool for projects without a checker.
- Exactly which files init writes into a project, within §5.
- Exact wording of every agent prompt and skill, provided §8.1 is covered in full.
- The final name (placeholder: "APM for Claude").

## 12. Acceptance for the framework itself
- Installed into VirtualAirline: the audit produces a coverage table with **every** item in §8.1 marked as
  covered, and the overwrite happens only after the user approves.
- A small feature runs from the user's description to merged with no copy-paste and exactly one user
  touchpoint after the request (plan approval).
- A protected-path write and a destructive command, attempted by a worker, are both blocked by hooks.
- A fresh session's "where are we?" briefing is accurate after a mid-task session kill.
