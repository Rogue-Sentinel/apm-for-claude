from pathlib import Path

from apm.metrics import measure_tree, render_text
from apm.standard_config import Limits, MetricsConfig

ROOT = Path(__file__).resolve().parent.parent


def test_framework_meets_its_own_limits() -> None:
    report = measure_tree(ROOT, MetricsConfig(include=("scripts/**",)))
    limits = Limits()

    assert report.files, "the walk found no files under scripts/"
    assert report.over_functions(limits) == [], render_text(report, limits)
    assert report.over_files(limits) == [], render_text(report, limits)
    assert report.unmeasured() == [], render_text(report, limits)
