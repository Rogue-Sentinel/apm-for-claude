"""Unit tests for guard_targets: segments outside quotes, the words a segment writes, and where `cd` goes."""
from __future__ import annotations

import pytest

from apm.guard_data import mask_data, strip_heredoc_bodies
from apm.guard_targets import cd_target, command_readings, command_segments, write_targets

SEGMENTS = [
    ("a && b", ["a", "b"]),
    ("a | b; c", ["a", "b", "c"]),
    ("sed 's|a|b|' f && g", ["sed 's|a|b|' f", "g"]),
    ("x 2>&1 | y", ["x 2>&1", "y"]),
    ("x &>f", ["x &>f"]),
    ("x & y", ["x", "y"]),
    ('echo "a && b"', ['echo "a && b"']),
    ("a \\\n&& b", ["a", "b"]),
    ("a || b\nc", ["a", "b", "c"]),
    ("echo 'a; b' ; c", ["echo 'a; b'", "c"]),
    ("find . -exec ls {} \\; && g", ["find . -exec ls {} \\;", "g"]),
    ("x >| ../o/f", ["x >| ../o/f"]),
    ("x >| f | y", ["x >| f", "y"]),
    ("echo \\>| y", ["echo \\>", "y"]),
    ('Copy-Item a "C:\\x\\"; Remove-Item b', ['Copy-Item a "C:\\x\\"', "Remove-Item b"]),
    ('echo "a\\" b; rm x"', ['echo "a\\" b; rm x"']),
    ("a;;b;", ["a", "b"]),
]


@pytest.mark.parametrize(("text", "expected"), SEGMENTS)
def test_command_segments_split_only_outside_quotes(text, expected):
    assert command_segments(text) == expected


WRITES = [
    ("echo x >> a.md", ["a.md"]),
    ("tee -a a.md b.md", ["a.md", "b.md"]),
    ("cp a b c dir/", ["dir/"]),
    ("cp a", []),
    ("cp -t dir a b", ["dir"]),
    ("cp --target-directory=dir a", ["dir"]),
    ("cp --target-directory dir a", ["dir"]),
    ("mv a b", ["b"]),
    ("cp a b 2>/dev/null", ["/dev/null", "b"]),
    ("mkdir -p a b", ["a", "b"]),
    ("rm -f x", ["x"]),
    ("sed -i 's/a/b/' f1 f2", ["f1", "f2"]),
    ("sed -i -e 's/a/b/' -e 's/c/d/' f", ["f"]),
    ("sed -i.bak 's/a/b/' f", ["f"]),
    ("sed --in-place 's/a/b/' f", ["f"]),
    ("sed -ni 's/a/b/p' f", ["f"]),
    ("sed -n 's/a/b/p' f", []),
    ("sudo tee /etc/x", ["/etc/x"]),
    ("FOO=1 cp a b", ["b"]),
    ("/usr/bin/tee a", ["a"]),
    ("tee.exe a", ["a"]),
    ("cd x", []),
    ("x >| ../o/f", ["../o/f"]),
    ("(cp a ../o/)", ["../o/"]),
    ("( cp a ../o/ )", ["../o/"]),
    ("{ cd ../o", []),
    ("env FOO=1 nohup touch t", ["t"]),
    ("echo 'a > b'", []),
]


@pytest.mark.parametrize(("segment", "expected"), WRITES)
def test_the_words_a_segment_writes(segment, expected):
    assert write_targets(segment) == expected


POWERSHELL = [
    ("Set-Content -Path a.md -Value x", ["a.md"]),
    ("Set-Content a.md x", ["a.md", "x"]),
    ("Out-File -FilePath a.md -Append", ["a.md"]),
    ("Copy-Item a -Destination b", ["b"]),
    ("Copy-Item -Path a -Destination b -Recurse", ["b"]),
    ("Copy-Item a b", ["b"]),
    ("New-Item -ItemType Directory -Force d", ["d"]),
    ("New-Item -Path p -Name f", ["p"]),
    ("COPY-ITEM a b", ["b"]),
    ("Remove-Item x", ["x"]),
    ("Add-Content -Path a.md -Value x -Encoding utf8", ["a.md"]),
    ("Copy-Item a -DESTINATION b", ["b"]),
    ('Copy-Item a "C:\\x\\"', ["C:/x/"]),
    ("Copy-Item README.md C:\\other\\r.md", ["C:/other/r.md"]),
]


@pytest.mark.parametrize(("segment", "expected"), POWERSHELL)
def test_the_words_a_powershell_segment_writes(segment, expected):
    assert write_targets(segment) == expected


def test_a_destination_with_a_trailing_backslash_before_another_command_is_a_target_of_the_first():
    first, second = command_segments('Copy-Item a "C:\\x\\"; Remove-Item b')

    assert (write_targets(first), write_targets(second)) == (["C:/x/"], ["b"])


GIT = [
    ("git commit -am x", ["."]),
    ("git -C ../o commit", ["../o"]),
    ("git -c a=b commit", ["."]),
    ("git -C ../o log", []),
    ("git status", []),
    ("git branch -a", []),
    ("git branch new", ["."]),
    ("git remote -v", []),
    ("git worktree list", []),
    ("git --version", []),
    ("git", []),
    ("git -C a -C b commit", ["a", "b"]),
    ("git stash show -p", []),
    ("git stash", ["."]),
    ("git stash list", []),
    ("git -C ../o stash -u", ["../o"]),
    ("git stash pop", ["."]),
    ("git config user.name x", ["."]),
    ("git -C ../o -c a=b push", ["../o"]),
]


@pytest.mark.parametrize(("segment", "expected"), GIT)
def test_git_writes_its_working_directory_unless_it_reads(segment, expected):
    assert write_targets(segment) == expected


@pytest.mark.parametrize(
    "segment", ["cat a b", "ls x", "grep x y", "python x.py out", "gh pr create --body-file b"]
)
def test_a_program_that_writes_nothing_has_no_targets(segment):
    assert write_targets(segment) == []


CD = [
    ("cd docs", "docs"),
    ("cd", "~"),
    ('cd "my dir"', "my dir"),
    ("cd -", None),
    ("pushd ../x", "../x"),
    ("Set-Location -Path x", "x"),
    ("sl x", "x"),
    ("cd docs 2>/dev/null", "docs"),
    ("ls", None),
    ("cd -P docs", "docs"),
    ("(cd ../o", "../o"),
    ("echo cd x", None),
]


@pytest.mark.parametrize(("segment", "expected"), CD)
def test_where_cd_goes(segment, expected):
    assert cd_target(segment) == expected


def _readings(command):
    """The readings Task 5 will judge: per reading, each segment's (cd word, written words)."""
    text = strip_heredoc_bodies(mask_data(command))
    return [[(cd_target(s), write_targets(s)) for s in reading] for reading in command_readings(text)]


def _written(command, reading=0):
    return [word for _, words in _readings(command)[reading] for word in words]


def _goes(command):
    return [cd for cd, _ in _readings(command)[0] if cd is not None]


RESERVED = [
    ('for f in *.log; do cp "$f" ~/out/; done', ["~/out/"]),
    ("if [ -d build ]; then mkdir -p ~/out/x; fi", ["~/out/x"]),
    ("if [ -d b ]; then echo y; else cp b ../o/; fi", ["../o/"]),
    ('while read f; do mv "$f" ../o/; done', ["../o/"]),
    ("! cp a ../o/", ["../o/"]),
    ("until false; do touch ../o/t; done", ["../o/t"]),
    ("if x; then git commit -am x; fi", ["."]),
    ("time cp a ../o/", ["../o/"]),
    ("if x; then ! rm ../o/f; fi", ["../o/f"]),
]


@pytest.mark.parametrize(("command", "expected"), RESERVED)
def test_a_shell_reserved_word_does_not_hide_the_program(command, expected):
    assert _written(command) == expected


def test_a_cd_in_a_condition_is_still_a_cd():
    assert _goes("if cd ../o; then git commit -am x; fi") == ["../o"]


STRAY_QUOTES = [
    ("# don't forget\ncd ../o && git commit -am x", ["."], ["../o"]),
    (
        "# Copy into the app's plugin folder\ncp -r build/plugin \"D:/Shared Apps/plugins/\"",
        ["D:/Shared Apps/plugins/"],
        [],
    ),
]


@pytest.mark.parametrize(("command", "written", "goes"), STRAY_QUOTES)
def test_a_stray_quote_does_not_stop_the_cutting(command, written, goes):
    assert (_written(command), _goes(command)) == (written, goes)


QUOTED_BACKSLASH = [
    ('Copy-Item -Path "build\\out\\" -Destination "C:\\Users\\me\\out\\" -Recurse', ["C:/Users/me/out/"]),
    ('Copy-Item "docs\\" "C:\\out\\"', ["C:/out/"]),
    ('Copy-Item a "docs\\"; Copy-Item c "C:\\out\\"', ["docs/", "C:/out/"]),
]


@pytest.mark.parametrize(("command", "expected"), QUOTED_BACKSLASH)
def test_the_powershell_reading_names_a_path_ending_in_backslash_and_quote(command, expected):
    assert _written(command, reading=1) == expected


def test_a_text_without_backslash_quote_has_only_the_bash_reading():
    assert command_readings("cp a ../o/ && ls") == [["cp a ../o/", "ls"]]


def test_the_bash_reading_comes_first_and_the_powershell_reading_second():
    command = 'Copy-Item a "C:\\x\\"; Remove-Item b'

    assert command_readings(command) == [command_segments(command), ['Copy-Item a "C:\\x/"', "Remove-Item b"]]


ASSIGNMENTS = [
    ("$null = New-Item -ItemType Directory -Force C:\\Users\\me\\out\\x", ["C:/Users/me/out/x"]),
    ("$f = New-Item -ItemType File -Path C:\\out\\a.md", ["C:/out/a.md"]),
    ("$f=New-Item -Path ../o/a.md", ["../o/a.md"]),
    ("$f =New-Item -Path ../o/a.md", ["../o/a.md"]),
    ("$f = (New-Item -Path ../o/a.md)", ["../o/a.md"]),
    ("$f = 3", []),
]


@pytest.mark.parametrize(("command", "expected"), ASSIGNMENTS)
def test_a_powershell_assignment_does_not_hide_the_cmdlet(command, expected):
    assert _written(command) == expected


COMMENTS = [
    ("cp a ../o/ # done", ["../o/"]),
    ("mkdir -p ~/out/x  # make the folder", ["~/out/x"]),
    ("# it's done\necho 'z' > ../o/f", ["../o/f"]),
    ("git log --format='#%h' > out.txt", ["out.txt"]),
    ("echo ${#arr[@]} > n.txt", ["n.txt"]),
    ("echo $# > n.txt", ["n.txt"]),
    ("echo a;# done\ncp a ../o/", ["../o/"]),
    ("(# done\ncp a ../o/)", ["../o/"]),
    ("Copy-Item a b <# note #>", ["b"]),
    ("<# it's #> cp a ../o/", ["../o/"]),
    ("<# one\ntwo #>\ncp a ../o/", ["../o/"]),
]


@pytest.mark.parametrize(("command", "expected"), COMMENTS)
def test_a_comment_is_not_read_as_a_command_or_an_argument(command, expected):
    assert _written(command) == expected


def test_a_hash_inside_a_word_is_not_a_comment():
    command = "curl http://x/a#b -o ../o/f --format=#%h"

    assert command_segments(command) == [command]


def test_a_hash_inside_quotes_is_not_a_comment():
    assert command_segments("echo 'a # b' && echo \"c # d\" ; e") == ["echo 'a # b'", 'echo "c # d"', "e"]
