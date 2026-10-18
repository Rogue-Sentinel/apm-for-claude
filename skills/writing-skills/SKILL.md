---
name: writing-skills
description: "Use when creating a skill, editing an existing one, or checking that a skill works before it ships, whether it is one of the framework's own skills or a project's domain skill, and when an agent ignored, misread or talked its way around a skill or an instruction file."
---

# Writing skills

Writing a skill is test-driven development applied to instructions. Watch an agent fail without
it, write the least that fixes that failure, watch the agent comply, then close the loopholes.

## When this applies

- Writing a new framework skill (`skills/<name>/SKILL.md`, invoked as `apm:<name>`).
- Writing or editing a project's **domain skill**, such as one that says how the project's screens
  look (see "Domain skills belong to the project").
- Editing any existing skill, even "just adding a section".
- An agent skipped, misread or rationalized around a skill, an agent prompt or an instruction file,
  and the wording has to change. A session diagnosis (`apm:session-diagnosis`) that traces a
  failure to an instruction ends here.

**What a skill is:** a reference for a proven technique, pattern, discipline or tool, that helps
future agents find and apply it. **What it is not:** a story of how one problem was solved once.

**Write one when** the technique was not obvious, it will be used again across projects or tasks,
and it applies broadly. **Do not write one** for a one-off solution, for a standard practice that is
documented well elsewhere, for a project convention (that goes in the project's instruction file,
its profile, or a domain skill), or for a mechanical constraint: if a regular expression or a check
can enforce it, automate it as a test or a checker, and keep skills for judgment.

**The kinds of skill**, which are tested differently (see "A skill is tested like code"):
- **Discipline:** a rule agents are tempted to break (test-first, verification).
- **Technique:** a method with steps (tracing a root cause, waiting on conditions).
- **Pattern:** a way of thinking about a problem (information hiding, a functional core).
- **Reference:** documentation to look things up in (a catalog, a command reference).

## The core rule

```
NO SKILL WITHOUT A FAILING TEST FIRST
```

This holds for new skills **and for edits** to existing ones. Wrote the skill before testing it?
Delete it and start over. Edited it without testing? The same violation. No exceptions: not for
"simple additions", not for "just a section", not for "documentation updates". Do not keep the
untested text as a "reference", and do not "adapt" it while you run the tests. Delete means delete.

**If you did not watch an agent fail without the skill, you do not know that the skill teaches the
right thing.** Breaking the letter of this rule is breaking its spirit. The cycle is the one in
`apm:test-first`; you need it before this skill makes sense.

## A skill is tested like code

| Test-first idea | For a skill |
|-----------------|-------------|
| The test | a scenario run by a subagent, under pressure |
| The production code | the skill document |
| Red | the agent breaks the rule without the skill (the baseline) |
| Green | the agent complies with the skill present |
| Refactor | close the loopholes and keep it compliant |
| Write the test first | run the baseline scenario before writing the skill |
| Watch it fail | record the agent's exact rationalizations, word for word |
| The least code | a skill that answers those failures, and nothing hypothetical |
| Watch it pass | the agent now complies |
| The refactor cycle | find a new rationalization, counter it, test again |

**Two kinds of test, and both come first.**

1. **The structural test** is a contract. In this framework, `tests/test_skills.py` checks every
   skill's shape, and a task's own test file (such as `tests/test_skills_quality.py`) checks the
   headings and references other tools anchor to, such as the coverage inventory. Write it, run it,
   and watch it fail before the skill exists. It proves the skill has its parts. It does not prove
   that an agent obeys them.
2. **The behavioral test** is a subagent scenario. It proves that an agent reading the skill does
   the right thing. See "Testing with subagents".

**Test by kind of skill:**

| Kind | Test with | It works when |
|------|-----------|---------------|
| Discipline | questions on the rules; pressure scenarios; three or more pressures combined | the agent follows the rule under the most pressure |
| Technique | applying it to a new scenario; variations and edge cases; missing information | the agent applies it correctly to a case it has not seen |
| Pattern | recognizing when it applies; applying it; counter-examples | the agent knows when to use it and when not to |
| Reference | finding the right entry; using what it found; the common cases | the agent finds the information and applies it correctly |

**Match the form of the guidance to the failure.** Before writing, classify the baseline failure,
because the form that fixes one kind of failure backfires on another:

| The baseline failure | The right form | The wrong form |
|----------------------|----------------|----------------|
| Breaks a rule under pressure (knows better, does it anyway) | a prohibition, a rationalization table and red flags | soft guidance ("prefer", "consider") |
| Complies, but the output has the wrong shape (bloated, buried verdict, restated spec) | a recipe or a contract: what the output is, its parts, in order | a list of prohibitions ("don't restate", "never narrate") |
| Leaves out a required element of something it already produces | a required field or slot in the template it fills | a prose reminder near the template |
| Should behave differently depending on a condition | a conditional on something observable ("if the brief exists, reference it") | an unconditional rule plus exemptions |

Prohibitions backfire on shaping problems: under a competing goal ("make the prompt
self-contained"), agents negotiate with "don't X", and in wording tests a prohibition produced more
of the unwanted content than a recipe did, and trended worse than no guidance at all. A recipe
leaves nothing to negotiate. Two rules for any form: **no nuance clauses** ("don't X unless it
matters" reopens the negotiation; make a real exception its own conditional on an observable
condition), and **exemption clauses do not scope** ("this limit doesn't apply to code blocks" still
suppresses code blocks; restructure so the rule cannot reach what must be exempt).

**Bulletproofing a discipline skill** (for a rule agents know and skip; not for shaping problems):
- **Close every loophole explicitly.** Do not only state the rule; forbid the specific workarounds
  ("do not keep it as a reference; do not adapt it; do not look at it; delete means delete").
- **Answer "spirit versus letter" early:** "Breaking the letter of the rule is breaking its spirit."
- **Build a rationalization table** from every excuse the baseline produced.
- **Make a red-flags list**, so an agent can catch itself rationalizing.
- **Put the symptoms of an impending violation in the description** ("when you wrote code before
  the test", "when testing by hand seems faster").

Why the firm wording works, and how to use it honestly, is in "Wording that holds under pressure" in
[references/best-practices.md](references/best-practices.md).

**Rationalizations for skipping the test:**

| Excuse | Reality |
|--------|---------|
| "The skill is obviously clear." | Clear to you is not clear to other agents. Test it. |
| "It's just a reference." | References have gaps and unclear sections. Test retrieval. |
| "Testing is overkill." | Untested skills have problems. Always. Fifteen minutes of testing saves hours. |
| "I'll test it if problems come up." | A problem means an agent could not use the skill. Test before it ships. |
| "It's too tedious to test." | Less tedious than debugging a bad skill in real work. |
| "I'm confident it's good." | Overconfidence guarantees problems. Test it anyway. |
| "Reading it through is enough." | Reading is not using. Test application scenarios. |
| "There's no time to test." | An untested skill costs more time when it fails. |

**One skill at a time.** Every skill in a batch has its own failing test, seen failing, and its own
verification before it counts as done; a task that writes several skills still finishes each one
properly. Shipping a batch of untested skills is shipping untested code.

## The description says when

The description is what an agent reads to decide whether to load the skill at all. It must answer
one question: **should I read this skill right now?**

- **In this framework it is quoted and starts with `"Use when`**, and the harness checks that.
- **It says when, never what the skill does or how.** When a description summarizes the workflow,
  agents follow the description and skip the body. A description that said "code review between
  tasks" led an agent to do one review where the skill's body required two; with the summary
  removed, the agent read the body and did both.
- **Name the triggers concretely:** symptoms, situations, error messages, and the words an agent
  would search for ("flaky", "hangs", "race condition", "timed out").
- **Describe the problem, not one technology's symptoms.** "When tests have race conditions or pass
  and fail inconsistently", not a function name from one language. A framework skill names no
  language, framework or project at all; a domain skill may.
- **Never first person**, and never addressed to the reader as "you can use this to". The
  description is injected into the system prompt.
- **Keep it short:** under 500 characters where possible, and never over 1024.

```
BAD   "Use when executing plans: dispatches a worker per task with a review between tasks"
      -- summarizes the workflow; agents follow this and skip the body
BAD   "For async testing"                        -- vague, and no "when"
BAD   "I can help when your tests are flaky"     -- first person
GOOD  "Use when executing an approved plan with independent tasks"
GOOD  "Use when tests have race conditions, timing dependencies, or pass and fail inconsistently"
```

**Name the skill by what you do, or by its core insight,** in active voice: `condition-based-waiting`
rather than `async-test-helpers`, `writing-skills` rather than `skill-creation`. Gerunds suit
processes. Lowercase letters, digits and hyphens only; the name equals the directory.

## Structure

**Every framework skill has the same shape**, which `tests/test_skills.py` enforces:

```
---
name: <the directory name>
description: "Use when <the triggering conditions, and the symptoms of an impending violation>"
---

# <Skill title>

<One or two sentences: the core principle.>

## When this applies

<The situations and symptoms, as a list. When it does not apply. Who in the framework uses it:
the manager, a worker, or both.>

## The core rule

<The rule in one sentence or one block. For a discipline skill, the bright line and "breaking the
letter is breaking the spirit".>

## <The sections the plan requires, then the technique, its examples in pseudo-code, a quick
reference table, red flags and a rationalization table for a discipline skill>

## References

- [references/<file>.md](references/<file>.md): <what it holds>

## Common mistakes

<What goes wrong, and the fix.>
```

- **The first `##` is `## When this applies`, the second is `## The core rule`, and the last is
  `## Common mistakes`.** There is exactly one `#` title.
- **Frontmatter:** `name` equal to the directory, and a quoted `description` starting with
  `"Use when`. An unquoted value never holds `: `.
- **Language-agnostic:** a framework skill names no language, framework or project, and its examples
  are pseudo-code. Language-specific evidence lives only in files named `references/*-by-language.md`.
  A test bans a fixed list of terms everywhere else.
- **Every supporting file is linked** from its `SKILL.md`, and every relative link resolves.
  Supporting files sit one level deep, in `references/`, and link to nothing further down.
- **American spelling** in every file under `skills/`; a test checks a fixed list of British forms.
- **Cross-reference other skills by name**, as `apm:<name>`, with a plain marker when it is
  required ("Required first: `apm:test-first`"). Never a path to another skill's file, and never a
  link that force-loads it.
- **The headings a plan names are a contract.** The coverage inventory and the skill tests anchor to
  them, so a required heading is written exactly as the plan wrote it.
- **Credit the source.** A skill adapted from substantial outside material gets a row in
  `skills/CREDITS.md`, and the source's license notice is carried there.

**One flat set of skills.** Every framework skill is a directory directly under `skills/`, so they
all share one searchable namespace; there are no categories or nesting.

**Keep the body lean.** Agents load a skill only when it is relevant, but once loaded, every word
competes with the work. Keep principles, concepts and code patterns under about 50 lines inline;
move a heavy catalog (a hundred lines or more), a long brief, a template or a reusable tool to
`references/`. The three shapes are a self-contained skill (everything inline), a skill with a
reusable tool or brief beside it, and a skill with heavy references. Word targets: a skill that
loads at the start of every session stays under about 150 words, one loaded in most conversations
under 200, and any other as short as its content allows. The framework's discipline skills run
longer than that, because they carry every rule, table and red flag in full, so they keep their
catalogs in references and their bodies under 500 lines. Count with `wc -w`. To save words: point at
a tool's own help instead of copying its flags; name another skill instead of repeating it; cut an
example to its essentials (a twenty-word exchange, not a forty-word one); and never explain what a
command already makes obvious, or give two examples of one pattern.

**One excellent example beats several mediocre ones.** In pseudo-code, complete enough to follow,
commented to say why, drawn from a real case, and showing the pattern clearly. Never the same
example in five languages, never a fill-in-the-blank template posing as an example, and never a
contrived one. A diagram earns its place only for a decision that is easy to get wrong; the
conventions are in [references/best-practices.md](references/best-practices.md), with the rest of
the authoring guidance: degrees of freedom, progressive disclosure, workflows and feedback loops,
templates, terminology, scripts, and the checklist.

**How agents find a skill,** and what to optimize for: an agent hits a problem ("tests are flaky"),
scans the skill descriptions, finds a match, reads the opening and the core rule to check it fits,
reads the quick reference, and loads an example or a reference only when it applies them. Put the
searchable words early.

## Domain skills belong to the project

A project's own skills that carry **domain knowledge**, facts true only of that project, belong to
the project, and the framework keeps them rather than replacing them. A skill that says how the
project's screens look, which tokens and colors to use, or how one subsystem's files are laid out is
domain knowledge. The framework replaces **methodology** (how to test, review, refactor, plan and
debug) with its own skills, and keeps the project's domain.

- **Where they live:** in the project, under its own skills directory (for example
  `.claude/skills/<name>/SKILL.md`), committed and changed through the project's normal pull
  requests. Never in the framework's `skills/`.
- **What changes in the rules:** a domain skill may name the project's language, frameworks, tools
  and paths, because that is what it is about. The banned-term list applies to framework skills,
  not to a project's domain skills. Everything else here still applies: the description says when,
  the skill is tested before it ships, and every file is linked.
- **How the manager uses them:** the audit at init inventories each one as domain knowledge to keep,
  and the manager names the relevant domain skill in a worker's brief, alongside the framework
  skills the worker invokes.
- **When a domain skill is wrong**, it is fixed like any wrong project knowledge: a debugger that
  traces a bug to it corrects it (`apm:systematic-debugging`), and the correction is tested like any
  skill edit.
- **When a skill mixes the two**, split it: the methodology part is covered by a framework skill,
  and the domain part stays. Nothing is deleted until the coverage inventory shows every rule it
  held is covered, and the user has approved the overwrite.

## Testing with subagents

**Who runs the tests.** Workers cannot dispatch agents, so the **manager runs the scenarios**. The
worker writing a skill writes the structural test and the pressure scenarios with the skill, and
reports them; the manager dispatches the baseline and the with-skill runs, at most the profile's
worker cap at once (three at most), reads every answer itself, and records the results. A scenario
never reaches the user: the subagent answers the manager.

**The cycle:**

1. **Red: the baseline.** Run each scenario without the skill. Record what the agent chose and its
   rationalizations, word for word. Note which pressures broke it.
2. **Green: the least skill.** Write a skill that answers those specific failures, and nothing
   hypothetical. Run the same scenarios with it. The agent should comply; if not, the skill is
   unclear or incomplete. Revise and run again.
3. **Refactor: close the loopholes.** A new rationalization gets an explicit negation in the rule,
   a row in the rationalization table, a red flag, and a symptom in the description. Then run every
   scenario again.
4. **Meta-test** when green will not come: ask the agent how the skill could have been written so
   that the right choice was unmistakable. "It was clear; I ignored it" needs a stronger founding
   principle. "It should have said X" is a wording gap: add X. "I didn't see that section" is an
   organization problem: make it prominent, and early.

**Micro-test the wording first** for guidance that shapes behavior, because full scenarios are slow:
one fresh sample per call, in the realistic context the guidance will live in (the whole skill or
brief, not the sentence alone), always with a no-guidance control (if the control does not fail,
there is nothing to fix), five or more repetitions per variant, every flagged match read by hand,
and the variance treated as a measure (wording that binds makes the repetitions converge).
Micro-tests check wording; they do not replace pressure scenarios for a discipline skill.

**A skill is bulletproof when** the agent picks the right option under the most pressure, cites the
skill's sections as its reason, acknowledges the temptation and follows the rule anyway, and the
meta-test says the skill was clear. It is not, while the agent finds new rationalizations, argues
that the skill is wrong, invents a hybrid approach, or asks permission while arguing hard for the
violation.

How to write pressure scenarios, the kinds of pressure, the setup text, plugging each hole, the
checklists and a worked campaign are in
[references/testing-skills-with-subagents.md](references/testing-skills-with-subagents.md).

**The checklist for each skill** (track every item as its own step):

```
RED
[ ] the structural test written, run, and seen failing
[ ] pressure scenarios written (three or more combined pressures for a discipline skill)
[ ] the scenarios run without the skill; the baseline recorded word for word
[ ] the patterns in the rationalizations and failures identified

GREEN
[ ] name: lowercase letters, digits and hyphens, equal to the directory
[ ] frontmatter: name, and a quoted description starting "Use when", under 1024 characters
[ ] the description gives triggers and symptoms, never the workflow, never first person
[ ] searchable words throughout (errors, symptoms, tools)
[ ] the opening states the core principle; the three fixed headings in their places
[ ] each baseline failure answered; the form of the guidance matches the kind of failure
[ ] wording that shapes behavior micro-tested against a no-guidance control (not for a pure reference)
[ ] examples inline, or a linked reference; one excellent example, in pseudo-code
[ ] the scenarios run with the skill; the agent complies

REFACTOR
[ ] new rationalizations found and countered explicitly
[ ] the rationalization table and the red flags list built from every run
[ ] every scenario run again; still compliant

QUALITY
[ ] a diagram only for a decision that is easy to get wrong
[ ] a quick reference; a common mistakes section; no storytelling
[ ] supporting files only for a heavy reference, a brief or a tool; every one linked
[ ] the whole test suite passes

SHIP
[ ] committed on the task's branch; the manager verifies, reviews and merges it
```

## References

- [references/testing-skills-with-subagents.md](references/testing-skills-with-subagents.md):
  pressure scenarios, the pressure types, plugging holes, meta-testing, the checklists, and a worked
  campaign that tests variants of an instruction file.
- [references/best-practices.md](references/best-practices.md): authoring guidance (conciseness,
  degrees of freedom, progressive disclosure, workflows, templates, scripts), wording that holds
  under pressure, the diagram conventions, and the checklist for an effective skill.

## Common mistakes

- **Writing the skill before running the baseline.** It then prevents what you imagine, not what
  agents actually do.
- **Only academic questions**, never a scenario that makes the agent want to break the rule.
- **A single pressure.** Agents resist one and break under three.
- **Paraphrasing the failure** ("the agent was wrong") instead of quoting the rationalization.
- **Generic counters** ("don't cheat") instead of naming the exact workaround.
- **Stopping after one green run.** Passing once is not bulletproof.
- **A description that summarizes the workflow**, so agents skip the body.
- **A prohibition list for a shaping problem**, where a recipe was needed.
- **Narrative examples** ("in that session we found..."), which are too specific to reuse.
- **The same example in several languages**, each mediocre, all to maintain.
- **Code inside a diagram**, or labels without meaning (step1, helper2).
- **Putting a project's domain knowledge into a framework skill**, or a methodology rule into a
  domain skill.
