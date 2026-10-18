import pytest

from apm.profile import Profile, ProfileError
from apm.standard_config import DEFAULT_EXCLUDES, DebtSource, Limits, MetricsConfig, load_standard


def _profile(standard: object) -> Profile:
    return Profile(framework_version="0.2.0", extra={"standard": standard})


def test_standard_defaults_without_profile() -> None:
    standard = load_standard(None)

    assert standard.limits == Limits(function=15, file=200, public_methods=7)
    assert standard.metrics == MetricsConfig()
    assert standard.metrics.include == () and standard.metrics.builtin is True
    assert standard.metrics.exclude == DEFAULT_EXCLUDES
    assert (standard.sources, standard.adr_dir, standard.ui) == ((), "docs/adr/", None)
    assert (dict(standard.review_patterns), standard.layers) == ({}, ())


def test_profile_without_standard_key_gives_defaults() -> None:
    profile = Profile(framework_version="0.2.0")

    assert load_standard(profile) == load_standard(None)


def test_profile_limits_override() -> None:
    standard = load_standard(_profile({"limits": {"function": 20, "public_methods": 9}}))

    assert standard.limits == Limits(function=20, file=200, public_methods=9)


@pytest.mark.parametrize("value", [0, -3, "15", 1.5, True, None])
def test_bad_limit_rejected(value: object) -> None:
    with pytest.raises(ProfileError, match="limits.function"):
        load_standard(_profile({"limits": {"function": value}}))


def test_unknown_limit_name_rejected() -> None:
    with pytest.raises(ProfileError, match="limits"):
        load_standard(_profile({"limits": {"method": 3}}))


def test_standard_must_be_an_object() -> None:
    with pytest.raises(ProfileError, match="standard must be an object"):
        load_standard(_profile(["limits"]))


def _source(**changes: object) -> dict:
    return {"name": "lint", "command": "make lint", "numbers": {"errors": r"(\d+) errors"}, **changes}


def test_debt_source_loads() -> None:
    standard = load_standard(_profile({"debt_sources": [_source()]}))

    assert standard.sources == (DebtSource("lint", "make lint", {"errors": r"(\d+) errors"}),)


@pytest.mark.parametrize("pattern", [r"\d+ errors", r"(\d+) of (\d+)", "(unclosed"])
def test_source_regex_needs_one_group(pattern: str) -> None:
    with pytest.raises(ProfileError, match="errors"):
        load_standard(_profile({"debt_sources": [_source(numbers={"errors": pattern})]}))


@pytest.mark.parametrize("changes", [{"name": ""}, {"command": ""}, {"name": 4}, {"numbers": []}, {"numbers": {"n": 5}}])
def test_bad_debt_source_rejected(changes: dict) -> None:
    with pytest.raises(ProfileError, match="debt_sources"):
        load_standard(_profile({"debt_sources": [_source(**changes)]}))


def test_source_without_name_key_rejected() -> None:
    bad = {"command": "make lint", "numbers": {}}
    with pytest.raises(ProfileError, match="debt_sources"):
        load_standard(_profile({"debt_sources": [bad]}))


def test_exclude_replaces_defaults_and_extra_exclude_adds() -> None:
    replaced = load_standard(_profile({"metrics": {"exclude": ["gen/**"]}}))
    added = load_standard(_profile({"metrics": {"extra_exclude": ["gen/**"]}}))

    assert replaced.metrics.exclude == ("gen/**",)
    assert added.metrics.exclude == DEFAULT_EXCLUDES + ("gen/**",)


def test_exclude_and_extra_exclude_combine() -> None:
    both = load_standard(_profile({"metrics": {"exclude": ["a/**"], "extra_exclude": ["b/**"]}}))

    assert both.metrics.exclude == ("a/**", "b/**")


def test_metrics_include_and_builtin() -> None:
    standard = load_standard(_profile({"metrics": {"include": ["src/**"], "builtin": False}}))

    assert standard.metrics.include == ("src/**",) and standard.metrics.builtin is False


@pytest.mark.parametrize("metrics", [
    {"include": "src/**"}, {"include": [3]}, {"exclude": [None]}, {"extra_exclude": "x"}, {"builtin": "no"},
])
def test_bad_metrics_rejected(metrics: dict) -> None:
    with pytest.raises(ProfileError, match="metrics"):
        load_standard(_profile({"metrics": metrics}))


def test_adr_dir_review_patterns_and_ui() -> None:
    standard = load_standard(_profile({
        "adr_dir": "decisions/", "ui": True, "review_patterns": {"naming": ["foo", "bar"]},
    }))

    assert standard.adr_dir == "decisions/" and standard.ui is True
    assert dict(standard.review_patterns) == {"naming": ("foo", "bar")}


def test_ui_false_is_kept_distinct_from_unset() -> None:
    assert load_standard(_profile({"ui": False})).ui is False


@pytest.mark.parametrize("standard", [
    {"adr_dir": ""}, {"adr_dir": 3}, {"ui": "yes"}, {"review_patterns": []},
    {"review_patterns": {"naming": "foo"}}, {"review_patterns": {"naming": [1]}},
])
def test_bad_adr_ui_and_patterns_rejected(standard: dict) -> None:
    with pytest.raises(ProfileError):
        load_standard(_profile(standard))


def test_layers_load_with_their_shape() -> None:
    layers = [
        {"name": "domain", "paths": ["src/domain/**"], "may_import": []},
        {"name": "app", "paths": ["src/app/**"], "may_import": ["domain"]},
    ]

    standard = load_standard(_profile({"layers": layers}))

    assert [layer["name"] for layer in standard.layers] == ["domain", "app"]
    assert standard.layers[1]["may_import"] == ["domain"]


@pytest.mark.parametrize("layer", [
    {"paths": ["a/**"], "may_import": []},
    {"name": "", "paths": ["a/**"], "may_import": []},
    {"name": "a", "may_import": []},
    {"name": "a", "paths": "a/**", "may_import": []},
    {"name": "a", "paths": [1], "may_import": []},
    {"name": "a", "paths": ["a/**"]},
    {"name": "a", "paths": ["a/**"], "may_import": [2]},
    {"name": "a", "paths": ["a/**"], "may_import": ["ghost"]},
    "domain",
])
def test_bad_layer_rejected(layer: object) -> None:
    with pytest.raises(ProfileError, match="layers"):
        load_standard(_profile({"layers": [layer]}))


def test_duplicate_layer_names_rejected() -> None:
    layer = {"name": "a", "paths": ["a/**"], "may_import": []}
    with pytest.raises(ProfileError, match="layers"):
        load_standard(_profile({"layers": [layer, layer]}))


def test_may_import_accepts_the_reserved_names_outside_and_star() -> None:
    layers = [
        {"name": "domain", "paths": ["d/**"], "may_import": []},
        {"name": "adapters", "paths": ["a/**"], "may_import": ["outside", "domain"]},
        {"name": "main", "paths": ["m/**"], "may_import": ["*"]},
    ]

    standard = load_standard(_profile({"layers": layers}))

    assert standard.layers[1]["may_import"] == ["outside", "domain"]
    assert standard.layers[2]["may_import"] == ["*"]


def test_may_import_still_rejects_other_undeclared_names() -> None:
    layer = {"name": "a", "paths": ["a/**"], "may_import": ["Outside"]}
    with pytest.raises(ProfileError, match="layers"):
        load_standard(_profile({"layers": [layer]}))


def test_a_layer_may_not_be_named_with_a_reserved_name() -> None:
    layer = {"name": "outside", "paths": ["a/**"], "may_import": []}
    with pytest.raises(ProfileError, match="layers"):
        load_standard(_profile({"layers": [layer]}))


def test_duplicate_debt_source_names_rejected() -> None:
    with pytest.raises(ProfileError, match="debt_sources.*lint"):
        load_standard(_profile({"debt_sources": [_source(), _source(command="make other")]}))


def test_debt_source_needs_at_least_one_number() -> None:
    for numbers in ({}, None):
        changes = {"numbers": numbers} if numbers is not None else {}
        source = {k: v for k, v in _source(**changes).items() if numbers is not None or k != "numbers"}
        with pytest.raises(ProfileError, match="debt_sources"):
            load_standard(_profile({"debt_sources": [source]}))


@pytest.mark.parametrize("standard, where", [
    ({"limit": {}}, "standard"),
    ({"metrics": {"includes": []}}, "metrics"),
    ({"debt_sources": [{**_source(), "regex": "x"}]}, "debt_sources"),
    ({"layers": [{"name": "a", "paths": [], "may_import": [], "color": "red"}]}, "layers"),
])
def test_unknown_keys_are_rejected(standard: dict, where: str) -> None:
    with pytest.raises(ProfileError, match=f"{where}.*unknown"):
        load_standard(_profile(standard))


@pytest.mark.parametrize("standard", [
    {"metrics": {"include": [""]}},
    {"metrics": {"exclude": ["a/**", ""]}},
    {"metrics": {"extra_exclude": [""]}},
    {"layers": [{"name": "a", "paths": [""], "may_import": []}]},
    {"review_patterns": {"naming": [""]}},
])
def test_empty_strings_rejected_in_globs_and_patterns(standard: dict) -> None:
    with pytest.raises(ProfileError):
        load_standard(_profile(standard))


def test_source_timeout_default_and_override() -> None:
    default = load_standard(_profile({"debt_sources": [_source()]})).sources[0]
    custom = load_standard(_profile({"debt_sources": [_source(timeout=30)]})).sources[0]

    assert (default.timeout, custom.timeout) == (300, 30)


@pytest.mark.parametrize("value", [0, -5, 1.5, "30", True, None])
def test_bad_source_timeout_rejected(value: object) -> None:
    with pytest.raises(ProfileError, match=r"debt_sources\[0\]\.timeout must be a positive integer"):
        load_standard(_profile({"debt_sources": [_source(timeout=value)]}))
