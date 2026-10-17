# Platform notes

## Live platform check (Task 9, Step 5)

Controller ruling R8: Task 9 does **not** run the live check. Each check below is
recorded as pending and will be run with the user after the final review. If any
check fails then, write the fallback here as an open issue for Plan 3 and tell the
user — do not work around it silently.

1. `claude plugin marketplace add "C:/Users/darby/source/repos/Agentic Project Management"` (the local path), then `claude plugin install apm@rogue-sentinel`.
   — **pending — run with the user after the final review.**
2. In a scratch git repo, run `apm setup` from a session's Bash tool, then **commit setup's output** (`.claude/settings.json`, `.apm/profile.json`, `.gitignore`) in the scratch repo. Only then start a new **desktop Code-tab** session there. Confirm that the session runs as the manager, and that the SessionStart briefing (`No work recorded yet.`) appears.
   — **pending — run with the user after the final review.**
3. Ask the manager to dispatch an implementer with `isolation: "worktree"` that runs `rm -rf build`, and confirm the guard denies it. Ask the manager itself to run `git reset --hard`, and confirm a permission prompt appears.
   — **pending — run with the user after the final review.**
4. Ask the manager to dispatch 4 haiku workers at once, each told to sleep briefly. Confirm no more than 3 run, and record how a 4th is refused.
   — **pending — run with the user after the final review.**
5. Ask a worker to dispatch a subagent, and confirm it can't (spawn depth 1).
   — **pending — run with the user after the final review.**
6. Confirm superpowers' skills are not offered in that project.
   — **pending — run with the user after the final review.**
7. With the user's usual permission mode (including auto mode), have the manager run `git reset --hard`, and confirm the hook's `ask` still shows a permission prompt rather than being auto-approved.
   — **pending — run with the user after the final review.**
8. In an implementer dispatched with `isolation: "worktree"`, confirm the hook event's `cwd` is the worker's isolation worktree (not the main checkout), and that the guard still denies `rm -rf build` there.
   — **pending — run with the user after the final review.**
9. Confirm `apm` is reached from the Bash tool by name (`apm brief` runs without a path), in the main session and in a worktree session.
   — **pending — run with the user after the final review.**
10. Confirm `python` is on the hook's PATH: a guarded call gets a JSON decision, not the wrapper's "the hook could not run" block. (If it is not, `hooks/run.sh` blocks every guarded call in an initialized project.)
   — **pending — run with the user after the final review.**

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
  slashes, and `bin/` is on the Bash tool's PATH.
- A PreToolUse hook that exits 2 blocks the tool call, and its stderr is shown to Claude
  as the reason. Our hooks run through `bash hooks/run.sh <hook>`, which uses this to fail
  closed when `python` itself cannot run in an initialized project.
- A plugin is disabled per project with
  `"enabledPlugins": {"superpowers@claude-plugins-official": false}` in project settings.
- Unverified until the live check above: the `agent` key, both env caps, whether
  hooks fire in desktop Code-tab sessions, whether a hook `ask` still prompts under auto
  mode, the `cwd` a worktree-isolated subagent's hook event carries, and `python` on the
  hook's PATH.
