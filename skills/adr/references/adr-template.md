# ADR template

Copy everything below the line into `<adr_dir>/NNNN-the-decision-in-a-few-words.md`, where
`<adr_dir>` is the profile's `standard.adr_dir` (default `docs/adr/`) and `NNNN` is the next number.
Replace each guidance paragraph with the real text, then add a row to the directory's index.

---

# ADR-NNNN: The decision, stated as a fact

## Status

Accepted, YYYY-MM-DD.

<!-- Add any relation on the same line: "Supersedes ADR-NNNN." or "Amends ADR-NNNN." For a partial
supersession, name the part and say the rest stands. A superseded record's status becomes
"Superseded by ADR-MMMM." and nothing else in it changes. -->

## Context

What forced this decision. The situation, the facts and measurements, the failures it answers, with
the numbers and commits that prove them. Link the earlier records it builds on. Write for a reader
who was not there and does not know why this mattered.

## Decision

**The decision in one bold sentence.**

Then the rules that follow from it, as a short list if there are several, specific enough that a
reviewer can check the code against them. Say what is in scope and what is not.

## Consequences

What changes because of this, honestly:
- what becomes easier;
- what becomes harder, and what it costs;
- the risks and known weaknesses accepted;
- what remains to be checked or done later, and by whom.

## Alternatives considered

- **The first serious alternative.** What it was, and why it was rejected.
- **The second.** What it was, and why it was rejected.
