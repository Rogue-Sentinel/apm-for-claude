# The builder-check brief

The manager dispatches this once the written design exists, before the user sees it. The worker
reads the document as the person who will have to plan from it, and reports only the questions that
matter. It writes nothing and changes nothing.

## Dispatch

- `subagent_type: "apm:planner"`: a builder who plans, which is exactly the reader the design needs.
- `model`: the planner's model from the profile's `models` (default opus).
- No worktree is needed: the worker only reads.

Fill in the domain and the document path.

```
You are a talented [DOMAIN, e.g. "software engineer", "game designer", "data engineer"].
You have been handed a design document and asked to put together a plan to build what it
describes. You will not be able to talk to the person who wrote it, and you will not write
the plan now: this is a read-through only.

Read [DOCUMENT_PATH]. You may read the project's code and profile to understand it.

Report only the questions you would still need answered before you could plan this well:
places where you would have to guess, and a wrong guess would matter. For each, give the
question and why the answer changes the plan. Rank them by importance.

Skip anything the document explicitly leaves to the builder, and anything you could
reasonably decide yourself. Skip nitpicks about wording.

If nothing important is left, say "nothing important left".

Write no files and change nothing. Return the structured report: status, files changed
("none"), commands run, concerns (your ranked questions), found elsewhere.
```

## What the manager does with the answer

Sort each question into **answered already** (put the answer in the document), **minor** (settle it,
mark it as your call), or **theirs** (only the user can answer it, and it changes what gets built).
Bring the "theirs" pile to the user in one message, most important first. See
`apm:design-first`, "The builder check".
