"""`apm init`: apply the approved audit, or say why it cannot be applied yet."""
from __future__ import annotations

import argparse
import subprocess
from datetime import datetime, timezone

from apm.init_apply import apply, refusals
from apm.paths import PLUGIN_ROOT, Project

RUN = subprocess.run  # the one place git is run from; tests replace it


def init(project: Project, args: argparse.Namespace) -> int:
    root = project.worktree_root
    found = refusals(root, PLUGIN_ROOT, RUN)
    if found:
        print("\n".join(found))
        return 1
    actions = apply(root, args.issue, datetime.now(timezone.utc), RUN)
    print("\n".join(actions) or "nothing new")
    return 0
