---
name: adr
description: "Use when a decision is made that a later reader would question, when a plan promises a decision record, or when an earlier decision is being reversed or amended and its record must be superseded."
---

# Architecture decision records

A decision a later reader would question is written down once, with what forced it, what was
chosen, what it costs and what was rejected, so nobody has to rediscover it or undo it by accident.

## When this applies

- You chose between real alternatives and the losing ones would look reasonable to a newcomer.
- You are accepting a cost on purpose: a limit, an exception to a rule, a known weakness.
- You are reversing or amending a decision that already has a record.
- A plan names a decision record as part of its work.
- A reviewer, or the user, asked "why is it like this?" and the answer is not in the code.

## The core rule

Records are written so that someone changing the code later understands why it is the way it is,
including the decisions that were wrong the first time. **A record is never edited once accepted**:
a changed decision gets a new record that supersedes the old one. A record the plan promised is part
of the work, not an extra.

## Where they live

The directory comes from the profile's `standard.adr_dir`; the default is `docs/adr/`. Files are
numbered in sequence with a short slug that states the decision:
`NNNN-the-decision-in-a-few-words.md` (for example `0012-schedules-are-fixed-at-dispatch.md`). The
directory holds an index (`README.md`) with one row per record: number, decision, status.

## When a decision needs an ADR

Write one when the decision:
- shapes the structure: a layer boundary, a dependency direction, where a kind of logic lives;
- picks one option over others a capable reader might prefer (a library, a format, a protocol, a
  storage model);
- accepts a cost deliberately: a limit, an exception to a standing rule, a known heuristic weakness,
  debt left in place;
- is hard or expensive to reverse;
- changes or replaces an earlier recorded decision;
- was promised by a plan.

Do not write one for a choice the code already explains, a convention the standard already states,
or anything a reader would not question. A record nobody will consult is noise.

## Writing one

Copy [references/adr-template.md](references/adr-template.md). Every record has these parts:

1. **Title:** `# ADR-NNNN: <the decision, stated as a fact>`. "The checker runs before merge", not
   "Checker options".
2. **Status:** `Accepted, <date>.`, plus any relation: `Supersedes ADR-NNNN.`, `Amends ADR-NNNN.`,
   or for an older record, `Superseded by ADR-NNNN.`
3. **Context:** what forced the decision. The facts, measurements and failures that made it
   necessary, with the numbers and commits that prove them. The reader should feel the pressure
   without having been there.
4. **Decision:** what was chosen, stated plainly in bold first, then the rules that follow from it.
   Specific enough to check against the code.
5. **Consequences:** what it costs and what it changes, honestly: what becomes easier, what becomes
   harder, the risks accepted, the weaknesses known, and what still has to be checked later.
6. **Alternatives considered:** each serious option, one bullet each, with why it was rejected.

Write it in the same change as the decision it records, so the reviewer sees both. Add its row to the
index. Link to the records it builds on or supersedes, and to the code or documents it governs.

## Superseding one

A reversed decision is never edited away; the history of why it changed is part of the record.

1. Write a new record whose status says `Supersedes ADR-NNNN.` If only part of the old decision
   changes, say exactly which part, and that the rest stands: "Supersedes the location decision of
   ADR-NNNN. The rest of ADR-NNNN stands."
2. Its context explains what changed since the old record: what the old decision cost in practice,
   what new facts arrived.
3. In the old record, change only its status line, to `Superseded by ADR-MMMM.` (or
   `Superseded in part by ADR-MMMM.` / `Amended by ADR-MMMM.`). Nothing else in it changes.
4. Update the old record's row in the index to the same status.

## Promised ADRs are acceptance criteria

**Any document a plan promises is part of the work, exactly like the code.** A plan that says "record
this in an ADR" is not done until that record exists, is accepted, and is linked from the index. One
project's plan called for three decision records; the features shipped and none were written, and the
reasons were lost. That is not shipping the plan.

- The planner names each promised record in the plan, in the task that makes the decision, with its
  working title.
- The builder writes it in that task, in the same change.
- The reviewer checks it exists and says what was decided; the merge gate requires every promised
  document to exist.
- If a promised record turns out to be unnecessary, or the decision changed, say so and get a
  decision (a worker tells the manager; the manager asks the user). Never drop it silently.

## References

- [references/adr-template.md](references/adr-template.md): the template, with guidance under each
  heading.

## Common mistakes

- **Editing an accepted record** to match a new decision, instead of superseding it.
- **Context with no evidence**: "it was slow" instead of the measurement and the commit.
- **A decision too vague to check** against the code.
- **Consequences that list only benefits.** Every real decision costs something; write it down.
- **No alternatives**, or alternatives that were never serious.
- **Writing the record after the fact**, in a later change, or not at all when the plan promised it.
- **A record for a trivial choice** the code already explains.
- **Forgetting the index**, or leaving the superseded record's status unchanged.
