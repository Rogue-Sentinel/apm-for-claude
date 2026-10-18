# Credits

The framework's skills are its own wording, written from the sources below. Where a skill adapts
substantial material from an MIT-licensed source, that source is named here and its license notice
is reproduced in full, as the license requires.

## Sources

### helmedeiros/clean-code-skills

[helmedeiros/clean-code-skills](https://github.com/helmedeiros/clean-code-skills), at commit
`b9805c9`, by Helio Medeiros. MIT License (notice below).

Adapted, in the framework's own words and with language-neutral examples, into:

| Framework skill | Adapted from |
|-----------------|--------------|
| `branch-review` | `branch-review` (and its scoring-evidence guide), and the `branch-review` command |
| `clean-code-audit` | the `clean-code-audit` command |
| `clean-code` | `clean-code-boy-scout-rule` (and its improvement checklist), `refactor-rename` (its naming conventions) |
| `code-smells` | `clean-code-detect-smells` (and its smell catalog) |
| `refactoring` | `refactor-extract-method` (and its extraction heuristics), `refactor-rename`, `refactor-replace-conditional-with-polymorphism` (and its before-and-after examples) |
| `test-first` | `tdd-test-first` (and its checklist), `tdd-red-green-refactor` (and its cycle steps), `tdd-arrange-act-assert` (and its patterns) |
| `solid` | `solid-single-responsibility` (and its indicators), `solid-open-closed` (and its strategies), `solid-liskov-substitution` (and its violation examples), `solid-interface-segregation` (and its patterns), `solid-dependency-inversion` (and its patterns) |
| `object-design` | `oop-encapsulation` (and its checklist), `oop-composition-over-inheritance` (and its patterns) |
| `functional-core` | `fp-pure-functions` (and its purity rules), `fp-higher-order-functions` (and its patterns), `fp-error-handling` (and its result and option reference) |
| `clean-architecture` | `hexagonal-ports-adapters` (and its anatomy), `hexagonal-domain-isolation` (and its anti-corruption layer patterns) |

### obra/superpowers

[obra/superpowers](https://github.com/obra/superpowers), version 7.0.0, by Jesse Vincent. MIT License
(notice below).

| Framework skill | Adapted from |
|-----------------|--------------|
| `test-first` | `test-driven-development` (and its guide to writing good tests) |
| `systematic-debugging` | `systematic-debugging` (and its root-cause tracing, defense-in-depth and condition-based-waiting references, its waiting helpers and its polluter search) |
| `verification` | `verification-before-completion` |
| `code-review` | `requesting-code-review` (and its code-reviewer brief), `receiving-code-review` |
| `writing-skills` | `writing-skills` (and its guides to testing skills with subagents and persuasion principles, its instruction-file testing example, and its diagram conventions); its authoring best practices are Anthropic's skill-authoring documentation, bundled by superpowers, and the creation log of superpowers' `systematic-debugging` is carried as its debugging-skill example |
| `session-diagnosis` | `diagnosing-superpowers` (and its analyst prompts, references and templates), retargeted to APM sessions |

### The user's own working agreement

The limits and the definition of a line of logic, "extract before you add", "logic does not move
sideways", "refactor and behavior never share a commit", the rules against skipped, waiting and
weakened tests, the decision-record practice, the architecture rule that keeps frameworks and input
and output at the edges so the core is tested without them, and the idioms that absence is a typed
value and the clock is a parameter come from the working agreement and decision records of the
user's own earlier project. They carry no third-party license.

## License notices

### helmedeiros/clean-code-skills

```
MIT License

Copyright (c) 2025 Helio Medeiros

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
```

### obra/superpowers

```
MIT License

Copyright (c) 2025 Jesse Vincent

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
```
