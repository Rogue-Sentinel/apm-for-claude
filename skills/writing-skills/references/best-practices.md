# Skill authoring best practices

Good skills are concise, well structured, and tested in real use. This is the authoring guidance
behind `apm:writing-skills`: how to write a skill an agent can find and follow, how to word a rule
so it holds, and how to draw the rare diagram that earns its place.

## Contents

- Concise is key
- Degrees of freedom
- Test with every model that will use it
- Names and descriptions
- Progressive disclosure
- Workflows and feedback loops
- Content
- Common patterns
- Evaluation and iteration
- Anti-patterns
- Skills with scripts
- Wording that holds under pressure
- Diagrams
- Checklist for an effective skill

## Concise is key

The context window is shared. A loaded skill competes with the system prompt, the conversation,
the other skills' descriptions, and the request itself. Only the name and description of every
skill are loaded up front; the body is read when the skill becomes relevant, and a reference file
only when it is needed. Once loaded, though, every word costs.

**Assume the agent is already very capable.** Add only what it does not know. Challenge every
piece: does the agent really need this explanation? Can I assume it knows this? Does this paragraph
justify its cost?

```
GOOD (about 50 tokens)
    ## Extract the text of a document
    Use the project's document reader:
        reader = openDocument("file.doc")
        text = reader.page(1).text()

BAD (about 150 tokens)
    ## Extract the text of a document
    Documents are a common file format that holds text, images and other content. To get the
    text out of one, you will need a library. There are many, but we recommend this one because
    it is easy to use and handles most cases. First install it, then you can use the code below...
```

The concise version assumes the agent knows what a document is and how a library works.

## Degrees of freedom

Match how specific the instructions are to how fragile and variable the task is.

| Freedom | Form | Use when |
|---------|------|----------|
| High | prose instructions ("analyze the structure; check for bugs and edge cases; suggest readability improvements; check the project's conventions") | several approaches are valid, the decision depends on context, heuristics guide the work |
| Medium | pseudo-code, or a script with parameters ("use this template, adapt as needed") | a preferred pattern exists, some variation is fine, configuration changes the behavior |
| Low | an exact script with few or no parameters ("run exactly this; do not change the command or add flags") | the operation is fragile and error-prone, consistency is critical, a sequence must be followed exactly |

Think of the agent on a path. On a **narrow bridge with cliffs on both sides** there is one safe way
forward: give exact instructions and guardrails (a data migration that must run in sequence). In an
**open field with no hazards**, many paths lead to the goal: give a direction and trust the agent to
find the best route (a code review, where context decides the approach).

## Test with every model that will use it

A skill adds to a model, so how well it works depends on the model. The framework assigns a model
to each role (by default haiku for auditor sweeps, sonnet for implementers, opus for the planner,
debugger and reviewer), and a profile can override them. Test a skill with every model the roles
that use it run on:

- **Haiku** (fast, economical): does the skill give enough guidance?
- **Sonnet** (balanced): is it clear and efficient?
- **Opus** (strong reasoning): does it avoid over-explaining?

What works for opus may need more detail for haiku. Aim for wording that works for all of them.

## Names and descriptions

**Name** by the activity: gerunds suit processes (`writing-skills`, `testing-skills`), and an
action or the core insight suits the rest (`condition-based-waiting`). Lowercase letters, digits and
hyphens, at most 64 characters, equal to the directory. Avoid vague names (`helper`, `utils`,
`tools`), overly generic ones (`documents`, `data`, `files`), and inconsistent patterns across the
skill set: consistent names make skills easier to reference, scan, organize and search.

**Description**: at most 1024 characters, injected into the system prompt, and read by an agent
choosing among possibly a hundred skills. It must carry enough for the agent to know when to load
this one.

- Always third person in effect: never "I can help you", never "you can use this to".
- Specific, with the key terms an agent would search for.
- Vague descriptions fail: "helps with documents", "processes data", "does stuff with files".

**The framework's rule here is stricter than general guidance.** General advice says a description
should state what the skill does and when to use it. The framework's descriptions say **only when**,
starting with `"Use when`, because a description that summarizes the workflow lets the agent skip
the body (see "The description says when" in the skill).

## Progressive disclosure

`SKILL.md` is an overview that points to detail as needed, like the table of contents of an
onboarding guide. Keep its body under 500 lines, and split it before it gets there.

```
a-skill/
    SKILL.md                      the overview and the core rule (loaded when triggered)
    references/
        catalog.md                a long catalog (loaded as needed)
        brief.md                  a dispatch brief (loaded as needed)
        evidence-by-language.md   the only place a language may be named
```

**Three patterns:**
1. **A high-level guide with references.** The common case inline; each advanced feature one line
   that links to its reference: "Form filling: see `references/forms.md`."
2. **Organized by domain.** For a skill covering several domains, one reference per domain, so a
   question about one loads only that one, and the rest cost nothing.
3. **Conditional detail.** The basic path inline, and the advanced one behind a link: "For tracked
   changes, see `references/redlining.md`."

**One level deep.** An agent that follows a link from a reference to another reference may read
only the first part of it. Every reference links directly from `SKILL.md`, and references do not
send the reader to further files.

**A table of contents** at the top of any reference over a hundred lines, so an agent reading only
the start still sees everything the file covers.

## Workflows and feedback loops

**Break a complex operation into clear, ordered steps.** For a long one, give a checklist the agent
can copy into its plan and tick off:

```
Progress:
[ ] 1. Read every source document
[ ] 2. Find the themes
[ ] 3. Cross-check each claim against its source
[ ] 4. Write the structured summary
[ ] 5. Check every citation; if one is incomplete, go back to 3
```

**Close the loop: run the validator, fix the errors, repeat.** The validator can be a script ("run
the check; if it fails, read the message, fix, run it again; go on only when it passes") or a
document ("review the draft against the style guide's checklist; note each issue with its section;
revise; check again"). Either way the agent proceeds only when the check passes. In this framework
the loop is the test suite, the checkers and `apm debt check`.

## Content

**Nothing that goes stale.** Not "before August, use the old interface". Describe the current method,
and put the old one in a clearly marked "old patterns" section, if it is needed at all.

**One term per concept**, used throughout. Always "endpoint", not a mix of "endpoint", "URL",
"route" and "path"; always "field", not "field", "box", "element" and "control"; always "extract",
not "extract", "pull", "get" and "retrieve". Consistency is what lets an agent follow the
instructions exactly.

## Common patterns

**Templates**, as strict as the need. For a required format (a report, a data shape), say "always
use exactly this structure" and give it. For flexible output, give a sensible default and say to
adapt the sections to what the analysis finds. The framework's worker report and reviewer brief are
strict templates.

**Examples**, as input and output pairs, where quality depends on seeing them:

```
Input:  added user authentication with signed tokens
Output: feat(auth): authenticate with signed tokens
        Add the login endpoint and the token check.

Input:  fixed dates shown wrong in reports
Output: fix(reports): convert time zones before formatting dates
        Use UTC timestamps throughout report generation.
```

Then state the rule the examples follow: type(scope): a brief description, then the detail.

**Conditional workflows**, at a decision point: "Creating something new? Follow the creation steps.
Editing something that exists? Follow the editing steps." When the branches grow long, move each to
its own reference and say which to read.

## Evaluation and iteration

**Build the evaluations before the documentation**, so the skill solves real problems rather than
imagined ones:

1. **Find the gaps:** run the agent on representative tasks without the skill, and record the
   specific failures and missing context.
2. **Write three scenarios** that test those gaps.
3. **Measure the baseline** without the skill.
4. **Write the least instruction** that closes the gaps and passes the scenarios.
5. **Iterate:** run them, compare with the baseline, refine.

An evaluation names the skill, the request, the input files, and the expected behavior as a short
list of checkable outcomes ("reads every page", "saves the text to output.txt"). There is no
built-in runner; in this framework the manager runs them, as in `testing-skills-with-subagents.md`.

**Develop with two agents.** One instance (A) helps write and refine the skill; a fresh instance
(B), with the skill loaded, uses it on real tasks. Work a task through with A without a skill and
notice the context you keep supplying; ask A to capture that as a skill; review it for conciseness
("remove the explanation of what a win rate is; the agent knows"); improve its organization ("put
the schema in a reference; more tables will come"); test it with B on similar tasks; and bring what
B missed back to A ("B forgot the date filter; should the filter section be more prominent?"). Keep
alternating: B's real use shows the gaps, A fixes them. Gather feedback from others who use the
skill too: does it trigger when expected, are the instructions clear, what is missing?

**Watch how agents navigate the skill:**
- an unexpected reading order means the structure is less intuitive than you thought;
- a missed link means the link needs to be more explicit or more prominent;
- a reference read every time probably belongs in `SKILL.md`;
- a reference never read is probably unnecessary, or poorly signaled.

## Anti-patterns

- **Backslash paths.** Always forward slashes (`references/guide.md`), on every platform.
- **Too many options.** Not "use this tool, or that one, or another". Give a default, with one escape
  hatch: "use the project's reader; for a scanned document, use the recognition step instead".
- **A narrative example** ("in that session, an empty directory caused..."): too specific to reuse.
- **Several languages of the same example:** each mediocre, all a burden to maintain.
- **Code inside a diagram:** it cannot be copied, and is hard to read.
- **Generic labels** (helper1, step3, pattern4): every label should mean something.

## Skills with scripts

The framework's own skills carry no scripts: they point at `apm` commands, which are stdlib-only and
tested. A domain skill may bundle one. When it does:

- **Solve, do not punt.** Handle the error conditions in the script (a missing file gets a default
  and a message; a permission error gets an alternative) instead of failing and leaving the agent to
  work it out.
- **No unexplained constants.** Every value is justified where it is set ("requests usually finish
  within 30 seconds; the longer timeout allows for slow connections"), never a bare `47`.
- **Prefer a script for a deterministic operation**: more reliable than generated code, cheaper in
  context (only its output is read), faster, and consistent.
- **Say whether to run it or read it:** "run the analyzer to extract the fields" (most common) or
  "see the analyzer for the extraction algorithm".
- **Run it through its interpreter** in the instructions, never by a bare path: packaging can drop
  the executable bit.
- **Plan, validate, execute** for batch, destructive or high-stakes work: the agent writes its plan
  to a file, a script validates the plan with specific messages ("field X not found; the fields are
  A, B, C"), and only then is it applied, then verified.
- **Use what the agent can see.** When an input can be rendered as an image, have the agent look at
  it.
- **Name the dependencies, and do not assume they are installed.** List them, and verify they are
  available where the skill runs.
- **Name tools fully.** A tool from a connected server is named with its server, as
  `Server:tool_name`, so the agent can find it among several servers.
- **Organize for discovery:** descriptive file names (`form-validation-rules.md`, not `doc2.md`),
  directories by domain or feature, and large resources bundled freely, since a file costs nothing
  until it is read.

## Wording that holds under pressure

Agents respond to the same principles of influence that people do. Used honestly, they make a
critical practice hold when an agent is under pressure to skip it; in published experiments, these
techniques roughly doubled how often a model complied with an instruction. The test of honest use:
**would this wording serve the user's real interests, if the user fully understood it?** It is
legitimate for making sure a critical practice is followed and for preventing a predictable failure.
It is never legitimate for false urgency, guilt, or anything that works against the user.

| Principle | How it works in a skill | Use it for |
|-----------|-------------------------|-----------|
| **Authority** | imperative bright lines: "never", "always", "no exceptions" | discipline and safety rules; it removes the "is this an exception?" question |
| **Commitment** | explicit choices ("choose A, B or C"), stating which skill is in use, a tracked checklist | making a multi-step process actually happen |
| **Scarcity** | time-bound requirements: "before proceeding", "immediately after" | verification that must not slide to "later" |
| **Social proof** | universal norms: "every time"; failure modes: "a checklist without tracking gets skipped" | reinforcing a standard |
| **Unity** | shared goals: "we both want this right; I need your honest technical judgment" | collaborative and review work |
| **Reciprocity** | an obligation to return a favor | almost never; it reads as manipulation |
| **Liking** | wanting to please | never for compliance: it breeds sycophancy, the opposite of honest review |

```
AUTHORITY    GOOD  "Wrote code before the test? Delete it. Start over. No exceptions."
             BAD   "Consider writing tests first when feasible."
COMMITMENT   GOOD  "When you use a skill, say which one."
             BAD   "Consider mentioning which skill you are using."
SCARCITY     GOOD  "After each task, request a review before starting the next."
             BAD   "Review when convenient."
SOCIAL PROOF GOOD  "A checklist without tracking gets skipped. Every time."
             BAD   "Some find tracking helpful."
UNITY        GOOD  "We are colleagues; I need your honest technical judgment."
             BAD   "You should probably tell me if I'm wrong."
```

| Kind of skill | Use | Avoid |
|---------------|-----|-------|
| Discipline | authority, commitment, social proof | liking, reciprocity |
| Technique | moderate authority, unity | heavy authority |
| Collaborative | unity, commitment | authority, liking |
| Reference | clarity only | all of them |

**Why it works:** a bright line removes the decision, so there is nothing to rationalize; a clear
trigger with a required action ("when X, do Y") runs more reliably than "generally do Y"; and models
learned from human text, in which firm instructions precede compliance and stated commitments
precede the action.

**Before you word a rule, ask:** what kind of skill is it? What behavior must change? Which
principle applies (usually authority and commitment for a discipline)? Am I combining too many?
Does it serve the user's real interest?

The research: R. B. Cialdini, *Influence: The Psychology of Persuasion*, new and expanded edition
(2021), for the seven principles; and L. Meincke, D. Shapiro, A. L. Duckworth, E. Mollick,
L. Mollick and R. Cialdini, *Call Me a Jerk: Persuading AI to Comply with Objectionable Requests*
(University of Pennsylvania, 2025), which tested the principles over 28,000 conversations with
language models and found compliance rose from 33% to 72%, with authority, commitment and scarcity
the strongest. That study shows the same levers can push a model the wrong way; that is why the
honesty test above is part of the rule.

## Diagrams

Most of what a skill says is better as a list, a table or a numbered sequence: reference material
goes in tables, examples in code blocks, linear steps in numbered lists. A diagram earns its place
only for a decision that is easy to get wrong, a loop where an agent might stop too early, or a
choice between two approaches. When one is used, it is written as text inside a code block (an
indented decision tree, as in `apm:systematic-debugging`, or a graph description language), because
agents read the source, not a picture. Its conventions: a **question** ends with `?` and is a
decision node; an **action** starts with a verb; a **command** is written literally, as it is run; a
**state** describes a situation ("the test is failing"); a **warning** stands out as a stop ("NEVER
fix only the symptom"); the **entry and exit** are marked; edges out of a decision are labeled with
the answer ("yes", "no", the condition); and no label is generic. The source this skill was adapted
from also shipped a script that renders such diagrams to images for people to look at; the framework
leaves it out, because it needs an external renderer and a runtime the framework does not depend on,
and because a skill's reader is an agent reading the text.

## Checklist for an effective skill

**Core quality**
- [ ] The description is specific, has the key terms, and says when (in this framework, only when).
- [ ] The body of `SKILL.md` is under 500 lines; detail is in references.
- [ ] Nothing that goes stale, or it is in an "old patterns" section.
- [ ] One term per concept throughout.
- [ ] Examples are concrete, not abstract.
- [ ] References are one level deep, each with a table of contents if over a hundred lines.
- [ ] Workflows have clear steps, and quality-critical ones have a feedback loop.

**Scripts** (domain skills only)
- [ ] Scripts solve problems instead of punting to the agent; errors are handled helpfully.
- [ ] No unexplained constants; dependencies listed and verified.
- [ ] Forward slashes in every path; run through the interpreter; documented.
- [ ] Validation steps for critical or destructive operations.

**Testing**
- [ ] At least three evaluations written before the skill.
- [ ] Tested with every model the roles that use it run on.
- [ ] Tested in real use, not only in scenarios.
- [ ] Feedback from other users folded in, where there are any.
