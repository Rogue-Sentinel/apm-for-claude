---
name: code-smells
description: "Use when reviewing a change or auditing a codebase for design problems, when code feels hard to work with for no obvious reason, or when preparing a refactoring plan and you need to find, rank and report code smells. Also use when the request mentions code smells, technical debt, reviewing code quality, or a systematic code quality assessment."
---

# Code smells

Find the surface signs of deeper design problems, rank them by what they cost, and report each one
so it can be acted on.

## When this applies

- You are reviewing a branch or a change.
- You are auditing a codebase, or a module of one.
- Code is "hard to work with" but nobody can say why.
- You are preparing a refactoring plan, or a list of debt issues.
- You want to give structured, actionable review feedback.

## The core rule

A smell is a surface sign that usually points at a deeper problem. **A smell is not a bug**: the
code works. It signals that the design is getting harder to understand, change or extend, and
smells caught early do not compound into costly structural problems. Report smells by impact, with
a fix, and never treat the whole list as urgent.

## Finding smells

Scan in four passes. The full catalog, with what each smell is, why it hurts and its fix, is in
[references/smell-catalog.md](references/smell-catalog.md).

1. **Bloaters**: things that have grown too large.

   | Smell | Detection rule |
   |-------|----------------|
   | Long method | more than the function limit (default 15 lines of logic) |
   | Large class | more than the file limit (default 200 lines of logic), or 7+ public methods; or a single type of about 200 lines, even in a file under the file limit (judged by the reviewer, not measured) |
   | Long parameter list | more than 3 parameters |
   | Data clumps | the same group of fields travels together in several places |
   | Primitive obsession | strings, numbers or booleans standing in for domain concepts |

2. **Couplers**: too much knowledge between parts.

   | Smell | Detection rule |
   |-------|----------------|
   | Feature envy | a method uses another type's data more than its own |
   | Inappropriate intimacy | two types reach into each other's internals |
   | Message chains | `a.getB().getC().getD().doSomething()` |
   | Middle man | a type delegates all its work to another |

3. **Change preventers**: patterns that make change risky.

   | Smell | Detection rule |
   |-------|----------------|
   | Divergent change | one type is modified for several unrelated reasons |
   | Shotgun surgery | one change means editing many types |
   | Parallel inheritance hierarchies | adding a subtype in one hierarchy forces one in another |

4. **Dispensables**: things that should not exist.

   | Smell | Detection rule |
   |-------|----------------|
   | Dead code | unreachable code, unused variables, functions never called, commented-out blocks |
   | Speculative generality | abstractions, hooks or parameters with only one user |
   | Duplicate code | identical or near-identical blocks in several places |
   | Lazy class | a type that does too little to justify itself |
   | Unnecessary comments | comments that restate the code, or no longer match it |

Use the numbers, not impressions, for the bloaters: `<CLI> metrics` lists every over-limit function
and file and every wide type. The one size signal it does not give is a single type of about 200
lines in a file under the limit: that is judged by the reviewer, not measured. The judgment smells (couplers, change preventers, most dispensables)
come from reading the code. `<CLI>` is the framework's command line, as the manager's prompt defines it.

## Severity

Rate each smell on three axes:

- **Frequency**: how often it occurs.
- **Impact**: how much it slows development. A smell in code that changes often is high impact; a
  smell in stable code that is rarely touched is low impact.
- **Effort**: how hard it is to fix.

Then place it:

| Impact \ effort | Low effort | Medium effort | High effort |
|-----------------|-----------|---------------|-------------|
| **High impact** | fix now | fix soon | plan it |
| **Medium impact** | fix under the boy scout rule | schedule | defer |
| **Low impact** | boy scout rule | defer | ignore |

Fix high-frequency, high-impact, low-effort smells first. Fix smells in code that is being worked
on; leave stable, rarely changed code alone. Before any fix, the code needs tests that pin its
behavior: if they are missing, adding them is the first fix.

## Reporting a smell

Each finding is one entry a reader can act on without asking you anything:

- **Where:** `path:line` and the name of the function or type.
- **Which smell**, by its catalog name.
- **Evidence:** the measured number (`<CLI> metrics`), or a short quote of the code that shows it.
- **Severity:** impact and effort, and the cell of the matrix it lands in.
- **Fix:** the refactoring that removes it, from the map below.
- **Scope:** whether it is in code the current work touches (paid down in this work, through an
  extract-before-you-add task) or elsewhere (a ranked issue for the user to schedule).

Smell to refactoring:

| Smell | Refactoring |
|-------|-------------|
| Long method | extract method |
| Large class | extract class |
| Long parameter list | introduce a parameter object |
| Data clumps | extract a class or value object |
| Primitive obsession | replace the primitive with a value object |
| Feature envy | move the method |
| Message chains | hide the delegate |
| Duplicate code | extract method, or pull the method up |
| Dead code | delete it |
| Middle man | remove the middle man, or inline the class |

The refactorings themselves are in `apm:refactoring`.

Example:

```
src/orders/checkout.ext:42  placeOrder
  Smell:    long method (bloater)
  Evidence: 38 lines of logic (limit 15), per <CLI> metrics
  Severity: high impact (changed in 9 of the last 20 commits), low effort -> fix now
  Fix:      extract method: validateOrder, calculateTotal, sendConfirmation
  Scope:    touched by this branch -> extract before you add
```

## References

- [references/smell-catalog.md](references/smell-catalog.md): every smell by category, with what it
  is, why it hurts and its fix, and the prioritization matrix.

## Common mistakes

- **Treating every smell as urgent.** Rank by impact; most smells are scheduled or deferred.
- **Refactoring without tests.** Fix the safety net first.
- **Chasing smells in code nobody changes.** Focus on active code.
- **Confusing a smell with a bug.** Smells are design issues, not functional defects; report a bug
  as a bug.
- **Applying a refactoring mechanically** without understanding the design problem underneath.
- **Reporting a smell with no evidence or no fix.** The reader cannot act on "this feels messy".
