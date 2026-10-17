# Platform notes

## Live platform check: results (2026-10-17)

Run in a scratch repo set up with `apm setup` (plugin 0.1.0 installed at user scope from the local
`rogue-sentinel` marketplace, Claude Code 2.1.267), in a new desktop Code-tab session.

| # | Check | Result | Evidence |
|---|---|---|---|
| 1 | Install from the local marketplace | PASS | `claude plugin install apm@rogue-sentinel`: installed at user scope |
| 2 | Session runs as the manager; SessionStart briefing | PASS | The agent prompt opens "You are the APM manager…", and the context holds "No work recorded yet." |
| 3a | Worker guard in an isolated worktree | PASS | `rm -rf build`, `rm data/fleet.db` and `git -C "<path>" reset --hard` were each denied with an "APM guard:" reason. `data/fleet.db` survived. |
| 3b / 7 | Main-session `ask` | **FAIL under auto mode** | `git reset --hard` ran with no prompt after auto mode was switched on. The hook itself returns `ask` (verified by a simulated event). Auto mode resolves a hook's `ask` without showing the user a prompt. |
| 4 | 3-worker cap | PASS | The 4th dispatch was refused: "Concurrent subagent limit reached. You can run 3 subagents at once." |
| 5 | Spawn depth | PASS (env var not exercised) | Workers have no Agent tool (`disallowedTools: Agent`), which stops them first. |
| 6 | Superpowers disabled | PASS | No `superpowers:*` skills appear in the session. |
| 8 | Hook `cwd` in a worktree worker | PASS | The guard denied commands run inside the worker's isolation worktree. |
| 9 | `apm` reachable by name | **FAIL** | The plugin's `bin/` is **not** on the Bash tool's PATH. `apm` resolved to an unrelated npm package (`agentic-pm`, `%APPDATA%/npm/apm`). |
| 10 | `python` on the hook's PATH | PASS | Every guarded call got a JSON decision, and none got "the hook could not run". |

### Open issues from the live check
- **The `apm` CLI is not reachable as `apm`.** The doc claim that `bin/` is on the Bash PATH did not hold in
  the desktop app. The name also collides with npm's `agentic-pm`. The manager needs a command that
  doesn't depend on PATH.
- **Auto mode skips the main session's `ask`.** In the user's usual mode, the manager can run a destructive
  command without a prompt, which contradicts spec §9.2 ("only after the user approves that specific
  action"). This needs a decision: deny in the main session too, or accept the caveat.
- The spawn-depth env var was not exercised, because no worker role has the Agent tool.

## Verified from docs (2026-10-17)

These are the platform facts the plan relies on, verified against code.claude.com
docs on 2026-10-17. The items marked unverified in the plan are exactly what the
live check above will confirm.

- The main session runs as a named agent through the `"agent"` key in a project's
  `.claude/settings.json` (e.g. `"apm:manager"`) — set per project, **not** in the
  plugin's root `settings.json`, since that would force every project to use it.
- `CLAUDE_CODE_MAX_CONCURRENT_SUBAGENTS` caps how many subagents run at once.
  `CLAUDE_CODE_MAX_SUBAGENT_SPAWN_DEPTH=1` stops subagents from spawning subagents.
  Both are set through the project settings' `env`.
- A PreToolUse hook's stdin carries `tool_name`, `tool_input`, `cwd`, and `agent_id`
  (present only inside a subagent). Plugin hooks fire inside subagents. A hook decides
  by printing `{"hookSpecificOutput":{"hookEventName":"PreToolUse","permissionDecision":"deny"|"ask","permissionDecisionReason":"..."}}`
  and exiting 0.
- A SessionStart hook's stdout
  `{"hookSpecificOutput":{"hookEventName":"SessionStart","additionalContext":"..."}}`
  is injected as session context.
- On Windows, hook commands run through Git Bash. `${CLAUDE_PLUGIN_ROOT}` uses forward
  slashes, and (per the docs) `bin/` is on the Bash tool's PATH. The live check found it was not in the desktop app.
- A PreToolUse hook that exits 2 blocks the tool call, and its stderr is shown to Claude
  as the reason. Our hooks run through `bash hooks/run.sh <hook>`, which uses this to fail
  closed when `python` itself cannot run in an initialized project.
- A plugin is disabled per project with
  `"enabledPlugins": {"superpowers@claude-plugins-official": false}` in project settings.
- Unverified until the live check above: the `agent` key, both env caps, whether
  hooks fire in desktop Code-tab sessions, whether a hook `ask` still prompts under auto
  mode, the `cwd` a worktree-isolated subagent's hook event carries, and `python` on the
  hook's PATH.
