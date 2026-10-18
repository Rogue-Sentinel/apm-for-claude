---
name: design-first
description: "Use when the user asks for something large or unclear (an epic, a needs-design issue, a change across several layers, real tradeoffs) or anything where what they want and why is not yet known, before any plan is written or anything is built."
---

# Design first

You are very good at building. You build what you believe the user wants, and that belief is
usually thinner than it feels. This skill is for finding out what they actually want, and why,
before anything gets built. People often have not finished working out what they want; good
questions help them think it through. When you understand the why, you make the hundred decisions
they never mention the way they would have made them.

The manager runs this conversation. It is the user's only contact, so no worker ever holds it:
a worker that needs a design decision returns the question to the manager in its report.

## When this applies

Before you reply to a request, ask yourself: what do I know about what they want, and why?

- **Everything that matters is in the request** ("make the icon cornflower blue"). This is a quick,
  clear task. It skips the conversation and goes straight to the planner, and its plan still comes
  to the user for approval.
- **Something non-trivial is missing.** Start the conversation. This is always the case for a large
  or unclear request: an epic, an issue labeled as needing design, a change across several layers,
  or one with real tradeoffs.

While the conversation runs, the issue's status is `designing` (`<CLI> issue N --status designing`).
`<CLI>` is the framework's command line, as the manager's prompt defines it.

## The core rule

```
NOTHING IS BUILT UNTIL THE USER HAS APPROVED THE DESIGN, AND THEN THE PLAN
```

The design says what and why. The plan says how, task by task. The user approves each one
separately, in chat, and nothing is built before both approvals.

## Nothing is built before an approved design

**This is a hard gate.** Nothing gets built until the user approves the full description: the
design document for a large or unclear request, or the request itself for a small, clear one.
Building includes writing product code, scaffolding, installing dependencies, creating projects,
dispatching an implementer, and loading a build skill. Reading and exploring are fine.

Approval covers what you showed them. "Sounds good" to an idea in passing is not approval of a
document you have not written yet.

Two exceptions, both narrow:

1. **They opted out of the questions.** The conversation is done and its gate goes with it. The
   plan approval still holds: the request goes to the planner, and the plan comes back to them.
2. **A spike they said yes to** may be built (see "Approaches and tradeoffs"). It stays labeled
   throwaway. Keeping what it produced is a new request that comes back through this gate.

After the design is approved, the next step is splitting it into issues and planning each one
with `apm:writing-plans`, and nothing else. No implementation skill, no "quick start" on the code.

## Sizing the work

Once you understand what they want, pick a size and say it in plain words. They can override it.

| Size | The full description | Then |
|------|----------------------|------|
| A quick, clear task | the request itself | the planner writes a short plan; the user approves it |
| A small change | agreed in chat | the planner writes the plan; the user approves it |
| A project | a written design document | split into issues; each gets its own plan and approval |

If it grows mid-task, stop, say so, and step up a size. If this is really several independent
projects, say so, agree on an order with the user, and design them one at a time.

## Opening the conversation

Your first message is two things, in this order, and nothing else:

1. **One line** letting them know that if they would rather skip the questions and have you just
   start, they can say so. If they take you up on it, state any significant how-it-gets-made choice
   (platform, language, medium) in one plain line, then send the request to the planner. The plan
   still comes back for their approval.
2. **One open question** that gets them describing. Ask about a real moment or a concrete picture:
   "What's the moment you find yourself wishing this existed?" or "Tell me about the people who'll
   use it."

## One question at a time

**Each message ends with one question:** a single sentence, with no list of example answers
hanging off it. Use plain language, pitched just a little above where the user is. Match their
vocabulary, and never use process jargon. Be clear and concise and lead with what matters; when you
report what you found, give the most important findings and offer the rest.

- **Get them describing.** Open questions come first. Their own words carry intent your options
  cannot. Offer a short menu only when they are stuck. When they say "just guess" or "what do you
  think?", propose something concrete.
- **Questions that work** anchor in specifics: "Walk me through the last time...", "If it could only
  do one of these well, which?", "What would make you wince if I got it wrong?" A guess they can
  correct ("I'm guessing this is because X keeps biting you?") often beats a question.
- **Ground to cover.** This is territory, not a script. Never read these out as questions:
  - what kind of thing this is, and what makes it special;
  - why now, and what success looks like to them;
  - goals, non-goals and anti-goals (below);
  - prior art: what they have seen elsewhere, loved or hated;
  - current state: what exists now, and what they have tried;
  - the details they care about.
- **How it gets made.** Every project rests on choices of medium, tools, materials and resources:
  the platform, language and libraries for software. Find out early which choices they want to make,
  which they are handing to you, and what they already have. Someone with strong views will want to
  talk it through; someone counting on you needs sensible defaults, said in plain words. When there
  is existing work, build on what it already uses (the profile names it). **Any choice you make goes
  in the design as your call, never as something they agreed to.**
- **Look before you ask.** Reading this project's own code, profile, decision records and issues is
  routine: do it yourself, or dispatch an auditor for a large tree, without asking. Looking beyond
  the project (the user's other files, the web) is offered first: say what you would look for, and
  they decide.

**The manager waits for the answer.** It never pings. While it waits, it keeps working on anything
the conversation does not block, and parks only the blocked work. A question that blocks recorded
work goes on the record with `<CLI> question N --text TEXT --blocks ID`, and its answer with
`<CLI> resolve`, so a context reset does not lose it.

## Play it back

Play back as you go. As soon as you understand one part well enough to describe it (what it is for
and who it serves, say, or how one piece behaves), describe that part back in about 200 to 300
words, then return to questions about the next part. Playback and questions alternate through the
whole conversation; the last chunk covers whatever is left.

Mark anything you are guessing as your guess; only what they said goes in as theirs. End each
chunk by asking what is wrong or missing.

## Showing, not telling

Some things are understood better by seeing than by reading: something they will look at (a
screen, a page, a printout), a layout or arrangement, a flow or sequence of steps, options that
would look different from each other, or a structure that is easier to see than read (a diagram, a
timeline, a map). The first time one comes up, offer to show it, in a message of its own with
nothing else in it: "This might be easier if I show you. Want me to put up some mockups?" If they
decline, stay in text and do not offer again unless they raise it. If they accept, use whatever the
session can render (a page, a diagram, a throwaway clickable prototype) for mockups to react to and
side-by-side options, and decide per question: requirements, scope, tradeoffs and conceptual choices
stay in text, and a question *about* a screen is not automatically a visual question. Keep each
screen to two to four options, say on it what question it answers, match its fidelity to the
question (a wireframe for layout, polish only for a question about polish), use real content where
placeholder content would hide a problem, iterate on a screen until it settles before moving on, and
clear the stale screen when the conversation returns to text. Before you
send a playback chunk that describes something they will look at, check: if they have not seen the
offer yet, send the offer instead and hold the chunk for the next message; once they have accepted,
put a mockup beside the description.

## Goals, non-goals and anti-goals

Every design names three lists, in the user's words where they gave them:

- **Goals:** what it must do, and what success looks like.
- **Non-goals:** what it deliberately does not do, so nobody builds it "while they're in there".
- **Anti-goals:** what would make it a failure *even if it technically works*. Ask for these
  directly; they are the ones people forget to say. "What would make you wince if I got this wrong?"

```
goal:       a returning user resumes exactly where they stopped
non-goal:   syncing between two devices
anti-goal:  losing a single saved record, even after a crash mid-save
```

Anti-goals travel furthest. The planner turns them into structural acceptance criteria and review
focus lines, and the reviewer checks the work against them.

## Approaches and tradeoffs

**Think wide privately.** Before you propose anything, come up with several ideas and drop the weak
ones, including any that fight what they told you about why. Show the comparison only when it helps
them decide. When you do, show two or three approaches, the tradeoff each makes, and which you
recommend and why.

**Say defaults out loud.** A default they never heard is one they could not reject.

**Spike to feel things out.** A quick throwaway build is often the cheapest way to learn what they
want or whether something works. Offer one when it would help; when they just want to spike, get
out of the way. A spike runs only on their yes, in its own worktree, labeled throwaway. It gets no
tests or minimal ones, is not bulletproof, needs no plan, and is never merged. Bring what it taught
you back into the conversation. Keeping its code is a new request through this gate: an approved
design, an approved plan, and a rebuild from tests (`apm:test-first`).

## The design document

For a project, write a plain document that a talented builder in the domain could plan from without
going back to the user. Cover:

- intent, and the why;
- goals, non-goals and anti-goals;
- constraints;
- the parts of the how they decided, as they decided them;
- the calls you made, each marked as yours;
- what is left to the builder.

**Where it goes:** `docs/specs/YYYY-MM-DD-<topic>-design.md`, committed on the issue's branch, unless
the profile or the user names another place. The user's preference wins.

## The builder check

Before you hand the document over, a fresh worker reads it as the builder would. Dispatch the
planner role (`apm:planner`) with [references/builder-check-brief.md](references/builder-check-brief.md):
it reads the document and reports questions, and it writes nothing. When you tell the user you are
writing it up, say a reviewer will read it first and you may come back once with a few questions.
Do not hand the document over until the check is back.

Sort what the builder asks into three piles:

- **Answered already** by the conversation or the project: put the answer in the document.
- **Minor:** a sensible builder could settle it without changing what gets built. Settle it
  yourself, and mark it in the document as your call.
- **Theirs:** only the user can answer it, and the answer changes what gets built.

Bring the "theirs" pile in **one** message, most important first. This is the one place you ask
several questions at once, and it is the only round of questions the check produces. Update the
document with their answers, then hand it over with a short list of the calls you made, so they can
check those while reading. If no worker can be dispatched, read the document as that builder
yourself.

The user approves the document in chat. Until then it is a draft, however complete it looks.

## Splitting into issues

An approved design is split into **sub-issues**, and each goes through planning with its own plan
approval. The design is the parent; each sub-issue is one piece that:

- can be planned on its own, and produces working, tested software on its own;
- has a clear order relative to the others, with its dependencies stated;
- fits one lane, and touches as few layers as it can.

The manager files each one as a GitHub issue (with the repository's issue forms and labels, if it
has them), links it to the design document and the parent, and records it with
`<CLI> issue N --title TEXT --status planning` (or `queued`, when another issue already holds its
lane). Then each goes to the planner with the design document's path, one at a time per lane, and
each plan comes back to the user for approval before any of it is built.

If the design turns out to be one piece, it is one issue. Do not split for the sake of splitting.

## Red flags

| Thought | Reality |
|---------|---------|
| "I'll offer options to save them effort." | Options steer. Ask them to describe it first. |
| "I'll fill in sensible defaults." | Good. Say them out loud. A default they never heard is one they could not reject. |
| "I should explain the process first." | Ask your question. The process shows itself. |
| "They said 'sounds good' to the idea." | Approval covers what you showed them. A description you have not written is not approved. |
| "The spike works; I'll keep building on it." | Keeping it is a new request. Back through the gate. |
| "The design is approved, so I can start building." | The plan comes next, and the user approves it too. |
| "The user is away; I'll decide this one for them." | If it changes what gets built, it is theirs. Wait, and work on what it does not block. |
| "Three quick questions in one message will save time." | One question per message. The builder check's single round is the only exception. |

## References

- [references/builder-check-brief.md](references/builder-check-brief.md): the brief for the worker
  that reads the design as its builder.

## Common mistakes

- **Building, scaffolding or dispatching an implementer** before the design and the plan are both
  approved.
- **A list of questions in one message**, or a question with a menu of answers hanging off it.
- **Leading with options** instead of getting them describing.
- **Process jargon** in questions to the user.
- **Forgetting the anti-goals**, so the failure the user fears most is never written down.
- **Choices recorded as theirs** that were really yours.
- **Handing over the document before the builder check is back**, or asking the check's questions
  one at a time across several messages.
- **Asking the user what the code already says.** Read the project first.
- **One giant issue** for a design that has several independently shippable pieces, or splitting a
  design that is one piece.
- **Pinging the user** instead of waiting, or stopping all work while one question is open.
