# Boy scout improvement checklist

Use this as you are about to leave a file you changed. Pick **one or two** items, no more.

## Naming (1 to 2 minutes)
- [ ] Rename a single-letter or abbreviated variable to a descriptive name.
- [ ] Rename a function so its name says what it does.
- [ ] Fix a misleading name that no longer matches the behavior.

## Dead code (1 minute)
- [ ] Remove an unused import.
- [ ] Remove a commented-out block of code. Version control has the history.
- [ ] Remove an unused variable or function.
- [ ] Remove a to-do comment for work that is already done.

## Comments (1 to 2 minutes)
- [ ] Remove a comment that only restates the code.
- [ ] Update a comment that no longer matches the code.
- [ ] Replace a "what" comment with a well-named function.

## Structure (2 to 5 minutes)
- [ ] Extract a clearly bounded block into a named function.
- [ ] Inline a variable used once that adds no clarity.
- [ ] Replace a magic number with a named constant.
- [ ] Simplify a boolean expression: `if (x == true)` becomes `if (x)`.

## Formatting (1 minute)
- [ ] Fix inconsistent indentation in the section you changed.
- [ ] Add a blank line to separate logical blocks.
- [ ] Remove blank lines that break the reading flow.

## Safety rules

1. **Scope:** improve only files you are already changing.
2. **Size:** one or two improvements per file, per commit.
3. **Risk:** zero change in behavior. If in doubt, skip it.
4. **Tests:** run the suite after every improvement.
5. **Time:** anything over five minutes is a separate task, and a refactoring with its own commit.

## Examples of good boy scout changes

| Before | After | Time |
|--------|-------|------|
| `d  // elapsed time in days` | `elapsedDays` | 30 seconds |
| `// to do: remove after the migration` (the migration finished six months ago) | *(deleted)* | 10 seconds |
| `if (result != null and result.isValid() == true)` | `if (result?.isValid())`, or the language's null-safe equivalent | 30 seconds |
| an unused import of a helper library | *(deleted)* | 10 seconds |
