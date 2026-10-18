# APM for Claude

APM turns a Claude Code session into a small project team. You talk to one agent, the manager. It files
the issues, hands the building to workers, checks their work itself, and tells you where things stand in
plain lines.

- **The manager is your one point of contact.** Workers never talk to you. Every question and every
  report comes through the manager.
- **Workers build in their own git worktrees.** A worker that goes wrong damages only its own copy.
- **Safety hooks guard every tool call.** Protected paths, destructive commands and `gh` writes are
  denied to workers, and to the manager unless you approve in chat.
- **A debt ratchet keeps the code from getting worse.** Function, file and class sizes are measured
  against limits, and no number may rise without your say-so.

You speak twice per piece of work: the request, and the approval of the plan. The manager does the rest.

## Requirements

- Claude Code (the desktop app or the CLI).
- Python 3.12 or newer. The plugin's scripts use only the standard library.
- git.
- `gh`, the GitHub CLI, signed in. This is optional. Without it, APM still works and tells you what to do
  by hand where it would have used GitHub.

## Install

The plugin lives in the `rogue-sentinel` marketplace. In Claude Code:

```
/plugin marketplace add Rogue-Sentinel/apm-for-claude
/plugin install apm@rogue-sentinel
```

Then set up each project you want it in. From the project's folder, run `apm setup`. The name `apm`
can belong to another tool on your PATH, so the safe form is the full path to the plugin's script:

```
python "<plugin folder>/scripts/apm_cli.py" setup
```

The plugin folder is under `~/.claude/plugins/cache/rogue-sentinel/apm/<version>/`. Setup makes the
manager the project's main agent, writes a starting profile in `.apm/profile.json`, and adds the state
folders to `.gitignore`. It is safe to run twice.

## Quick start

1. Open Claude Code in the project. You are now talking to the manager.
2. Say: "Set this project up." The manager audits it and shows you a report to approve.
3. Say what you want: "Add a dark-mode toggle to the settings page."
4. Read the plan summary and answer yes, or say what to change. That is your one approval.
5. Watch the one-line updates. The manager opens the pull request when the gate passes.

## Learn more

- [The tutorial](docs/tutorial.md) walks through a small project, step by step, with what you say, what
  the manager does and what you decide.
- [The design spec](docs/specs/2026-10-17-apm-for-claude-design.md) says why the framework works the way
  it does.
- [The coverage table](docs/coverage.md) shows where each rule of the older standard now lives.
- [The decision records](docs/adr/) explain choices a later reader would question, such as lean pacing.
