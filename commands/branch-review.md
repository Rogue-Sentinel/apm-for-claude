---
description: "Review a branch against its base and give a scored quality scorecard. Takes an optional branch name."
argument-hint: "[branch]"
---

Review a branch for quality. The user typed `/apm:branch-review` with an optional branch name, which is
`$ARGUMENTS`. When `$ARGUMENTS` is empty, the branch is the current branch.

1. Dispatch an `apm:reviewer` worker. Fill its brief from `apm:code-review`
   (`references/reviewer-checklist.md`): the exact CLI line, the branch and its base, and the
   profile's limits and `standard.ui`. Tell it to run the `apm:branch-review` skill on that branch
   against its base. The reviewer writes no file.

2. When the reviewer reports, relay its scorecard to the user in plain words.
