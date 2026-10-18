# ADR-0005: The guard reads an apm CLI call and a `cat` heredoc as data only where bash reads them literally

## Status

Accepted, 2026-10-18. Builds on ADR-0002.

## Context

Issue 11 reported that the guard blocks `apm approve`. The user says yes in chat, the manager records the
approval, and the guard denies the recording. Four causes, each confirmed on the repo code:

1. **A backslash anywhere rules out the data exemption.** `guard_cli._UNSAFE` holds a backslash, so
   `is_cli_call` is false for any command that has one. The command scan then reads the unmasked `--command`
   value (`git rm -r -q .claude\skills\clean-code`) as a command to run and denies it. On Windows, the exact
   command to approve usually has a backslash.
2. **An approve call from the PowerShell tool is never exempt.** The exemption checks `tool_name == "Bash"`.
   The same call with forward slashes, run from PowerShell, is denied with the reported text. Nothing in the
   denial told the manager to use Bash.
3. **The echo shows the masked text.** The checks run on the masked command, and every reason appends the
   segment it was given. So `--reason "x"` is shown as `--reason ""`, and a heredoc line is shown as if it were
   the command.
4. **A heredoc body is data only for `git commit -F -`.** The body of `cat > body.md <<'EOF'` is split on
   newlines and each line is scanned as a command, so an issue body that quotes `git rm -r -q x` is denied.

ADR-0002 sets the threat model: a cooperative manager or worker making a mistake. Its rule 2 needs a reading
for this change, given under Decision, and two narrow deny-to-allow cases follow from it.

## Decision

**The guard reads an apm CLI call and a `cat` heredoc as data only where bash reads them literally.**

- **Backslash rule.** One plain call of this plugin's CLI, from Bash in the main session, stays a data call when
  its backslashes are ones bash reads literally: inside single quotes, or inside double quotes before any
  character except `"` or `\`. A backslash outside quotes, `\"` and `\\` inside double quotes, `$`, a backtick,
  a newline and a carriage return still rule the call out.
- **`cat` heredoc rule.** The body of a heredoc is read as data only when all of these hold:
  - the first non-blank line of the command holds a lone `cat`;
  - that line has one `>` or `>>` to an unquoted path of `[\w./:~-]` characters ending in `.md` or `.txt`;
  - that line has one `<<` or `<<-` heredoc with a single- or double-quoted tag, in either order with the
    redirect, and nothing else on the line;
  - the body ends at the first line that is the tag, with blanks allowed around it;
  - nothing after that end tag is masked, so it is scanned like any other command text.

  The file it writes is still checked.
- **Carriage-return rule.** Nothing in a command holding a carriage return is masked. Git Bash ends a heredoc at
  a line `TAG\r`, which the guard's end-of-line match does not see, so a mask could run past where bash ended
  the body. This also stops message arguments (`-m`, `--body` and the like) from being masked in such a command.
  Both fail closed: a few more commands are scanned whole and denied.
- **The exemption stays Bash-only and main-session-only.** PowerShell's quoting (`""`, and the curly quotes it
  treats as quotes) is not read. The denial and the instructions now say to record an approval with the Bash
  tool.
- **A denial echoes the command as typed**, once, not the masked segment.

How ADR-0002 rule 2 is read. Read literally, it makes any denial that becomes an allow a must-fix, which no
false-positive fix can meet. The user approved, on 2026-10-18, reading it for this change as: never allow a
command that does what the guard must stop. Under that reading exactly two classes of denial become allows:

- (a) A plain CLI call whose backslashes bash reads literally. The CLI only records text; it runs nothing the
  threat model names.
- (b) A first-line `cat` heredoc written to a `.md` or `.txt` file. `cat` only writes text.

Every other verdict is unchanged. The tests pin the realistic neighbors: a chained approve call, a backslash
bash reads as an escape, a heredoc that feeds code (`bash <<'EOF'`, `python - <<'PY'`, `cat <<'EOF' | bash`, a
script written then run), an unquoted tag, a `cat` heredoc after another line (`cd docs` on a line before it, or
`cd docs &&` before it), a destructive line after the end tag, a command holding a carriage return, and the file
a heredoc writes.

## Consequences

- An approve call with a Windows path in single quotes, or in double quotes without a trailing `\`, passes the
  hook from Bash.
- A path ending in `\` inside double quotes, `\\`, and `\"` still rule the call out. Use single quotes.
- A `.md` or `.txt` file written by a heredoc and then executed is a known limit, as in ADR-0002.
- A heredoc not on the first non-blank line, or with an unquoted tag, is still scanned.
- A command holding a carriage return is scanned whole, including its message arguments.
- A PowerShell-tool command with `<<` is masked the same way, but it runs nothing, because PowerShell does not
  parse `<<`.
- The echo of a long script is long.
- A PowerShell approve call is still denied. The instruction to use Bash is the fix.

## Alternatives considered

- **Any backslash inside quotes, read with bash's escapes.** Wider. Reasoning about `\"` inside strings is what
  the old rule avoided.
- **Forward slashes only, by instruction.** The approval must equal the retried command, which on Windows holds
  `\`.
- **Compare approvals with slashes normalized.** It approves a command the user did not see.
- **`shlex` with `punctuation_chars` as the reader.** Its rules differ from bash's in places a reviewer would
  then have to prove.
- **Exempt PowerShell.** New quoting rules to prove, and not needed while the Bash tool exists.
- **Mask every heredoc that has a quoted tag.** `bash <<'EOF'` is code.
