---
description: "Set up APM in this project: make the manager the main agent and write the starting profile."
allowed-tools: Bash
---

Set up APM in the current project. The user typed `/apm:setup`; they should not have to run anything
themselves. Do these steps in order.

1. Check that you are inside a git repository (for example with `git rev-parse --show-toplevel`). If you are
   not, stop. Tell the user in plain words that APM works inside a git repository, and that they can
   run `git init` for you or open Claude Code in the right folder. Change nothing.

2. Run the setup script with the Bash tool:

   `python "${CLAUDE_PLUGIN_ROOT}/scripts/apm_cli.py" setup`

   If `${CLAUDE_PLUGIN_ROOT}` shows up as plain text and was not replaced with a folder, find the plugin
   under `~/.claude/plugins/cache/rogue-sentinel/apm/<version>/`, pick the newest version folder, and run
   `scripts/apm_cli.py setup` from there instead. Never run a bare `apm`, because another tool on this
   machine may own that name.

3. Tell the user, in plain words, what setup did. It prints one line for each file it wrote. It writes
   `.claude/settings.json` (so the manager is the main agent), `.apm/profile.json` (the starting profile)
   and `.gitignore` (so the state folders stay out of git). If it printed nothing, say that everything was
   already set up. If it failed, give the error in plain words and stop.

4. Tell the user the last step: open a new Claude Code session in this project. That new session is the
   manager. Then say "Set this project up" to start the audit.

Do not write any other file, delete anything or run any destructive command. Setup is safe to run twice.
