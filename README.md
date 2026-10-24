# APM for Claude

APM turns a Claude Code session into a small project team. You talk to one agent, the manager. It files
the issues, hands the building to workers, checks their work itself, and tells you where things stand in
plain lines.

- **The manager is your one point of contact.** Workers never talk to you. Every question and every
  report comes through the manager.
- **Workers build in their own git worktrees.** A worker that goes wrong damages only its own copy.
- **Safety hooks guard every tool call.** Workers are denied protected paths, destructive commands and
  `gh` writes. The manager files and closes issues freely, but needs your approval in chat for a
  protected path or a destructive command.
- **A debt ratchet keeps the code from getting worse.** Function, file and class sizes are measured
  against limits, and no number may rise without your say-so.

You speak twice per piece of work: the request, and the approval of the plan. The manager does the rest.

## Requirements

- Claude Code (the desktop app or the CLI).
- Python 3.12 or newer, installed on your machine. The plugin's scripts use only the standard library, and
  you do not run them yourself. Claude and the manager do.
- git.
- `gh`, the GitHub CLI, signed in. This is optional. Without it, APM still works and tells you what to do
  by hand where it would have used GitHub.

## Install

The plugin lives in the `rogue-sentinel` marketplace.

If you installed APM from a local folder before, remove that marketplace first. Uninstalling the plugin
leaves it behind, and because it has the same name, adding this one fails with only "Failed to add
marketplace." Type `/plugin marketplace remove rogue-sentinel` in Claude Code, or
`claude plugin marketplace remove rogue-sentinel` in a terminal. A first install skips this step.

Then, in Claude Code:

```
/plugin marketplace add Rogue-Sentinel/apm-for-claude
/plugin install apm@rogue-sentinel
```

Then set up each project you want it in. Open Claude Code in the project and type this in the chat:

```
/apm:setup
```

Claude runs the setup for you. It makes the manager the project's main agent, writes a starting profile
in `.apm/profile.json`, and adds the state folders to `.gitignore`. It is safe to run twice. When it is
done, open a new Claude Code session in the project. That new session is the manager.

You never type a command-line command. The manager runs them for you.

One more command is optional: `/apm:branch-review [branch]` has a reviewer score a branch against its base.
Leave the branch out to review the current one.

## Quick start

1. Type `/apm:setup`, then open a new Claude Code session in the project. You are now talking to the manager.
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
