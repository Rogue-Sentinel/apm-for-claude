# The issue body

Pass the body to `<CLI> github file --body-file PATH`. If the repository has an issue template for
the kind of issue, use its headings and labels and fill them in as below; the template wins where the
two differ. Write for the person who reads the issue in six months with none of this conversation.

## A feature

```
## What and why
One paragraph: what the user wants to be able to do, and why it matters to them.

## Acceptance
- A visible behavior that is true when this is done.
- Another, each one checkable.

## Out of scope
What this issue deliberately does not do, so it stays one pull request.

## Notes
Constraints the user stated, links to the design or earlier issues, the lane.
```

## A bug

```
## What happens
What the user sees, in their words.

## What should happen
The behavior they expected.

## How to reproduce
Numbered steps, the input used, and where it happens (version, environment, data).

## Evidence
The exact error text, a log line, or a screenshot. Paste, do not paraphrase.

## Notes
When it started, what changed around then, anything already ruled out.
```

## Debt

```
## What is wrong
The smell or the number, named, with the files or functions it lives in.

## Why it matters
What it makes slower, riskier or harder to change.

## The fix
The refactoring that pays it down, in the order `apm:refactoring` would do it.

## Done when
The number that must be lower, measured with `<CLI> metrics`.
```

A sub-issue ends with `Part of #P`; `--parent P` adds that line.
