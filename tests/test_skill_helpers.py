"""The skill-test helpers read Markdown the way a renderer does."""
import pytest

from skill_helpers import british_spellings, local_links, prose_lines, section, sections

FOUR_BACKTICK_FENCE = """# Title
````
```
## inside the outer fence
```
## still inside
````
## After
"""
TILDE_FENCE = """~~~
## inside tildes
```
## still inside: a backtick line does not close a tilde fence
~~~
## After
"""
SHORT_CLOSER = """````
## inside
```
## still inside: a shorter fence does not close
````
## After
"""


@pytest.mark.parametrize("text", (FOUR_BACKTICK_FENCE, TILDE_FENCE, SHORT_CLOSER))
def test_headings_inside_any_fence_are_ignored(text):
    assert sections(text)[-1] == "## After"
    assert not [heading for heading in sections(text) if "inside" in heading]


def test_closing_fence_with_text_after_it_does_not_close():
    text = "```\n## a\n``` not a closer\n## b\n```\n## c\n"
    assert sections(text) == ["## c"]


def test_backtick_opener_with_a_backtick_in_its_info_is_not_a_fence():
    assert sections("``` a`b\n## seen\n") == ["## seen"]


def test_prose_lines_drop_fence_lines_and_their_contents():
    assert prose_lines("a\n~~~~\nb\n~~~~\nc") == ["a", "c"]


def test_section_runs_to_the_next_heading_of_its_level_and_keeps_fences():
    text = "## A\none\n### A1\ntwo\n```\n## fenced\n```\n## B\nthree\n"
    assert section(text, "## A") == "one\n### A1\ntwo\n```\n## fenced\n```"
    assert section(text, "### A1") == "two\n```\n## fenced\n```"
    assert section(text, "## B") == "three"


def test_section_ignores_a_fenced_copy_of_the_heading():
    assert section("```\n## A\nfenced\n```\n## A\nreal\n", "## A") == "real"


def test_links_inside_inline_code_do_not_count():
    assert local_links("see `[x](missing.md)` and ``[y](gone.md)`` but [z](real.md)") == ["real.md"]


def test_reference_style_definitions_are_links():
    text = "Read [the guide][g].\n\n[g]: references/guide.md#top\n  [h]: <references/with space.md>\n"
    assert local_links(text) == ["references/guide.md", "references/with space.md"]


def test_angle_bracket_inline_links_are_links():
    text = "[a](<references/a b.md>) and [c](references/c.md \"title\")"
    assert local_links(text) == ["references/a b.md", "references/c.md"]


def test_external_and_anchor_links_are_not_local():
    assert local_links("[a](https://example.com/x.md) [b](#heading) [c](mailto:x@y.z)") == []


@pytest.mark.parametrize("word", (
    "colour", "colours", "behaviour", "behaviours", "behavioural", "favour", "favourite", "centre",
    "centred", "organise", "organised", "recognised", "prioritising", "initialised", "normalised",
    "normalisation", "analyse", "analysed", "catalogue", "catalogued", "judgement", "judgements",
))
def test_british_forms_are_caught(word):
    assert british_spellings(f"The {word.capitalize()} and the {word}.") == [word.capitalize(), word]


@pytest.mark.parametrize("word", (
    "analyses", "analysis", "analyzes", "color", "behaviors", "favorite", "center", "centered",
    "organized", "recognizes", "catalog", "judgment", "normalization", "organism",
))
def test_american_forms_and_lookalikes_pass(word):
    assert british_spellings(f"one {word} here") == []
