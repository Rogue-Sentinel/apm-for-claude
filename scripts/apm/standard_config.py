"""The standard a project is held to: limits, what to measure, debt sources, and the layer map.

Everything here is read from the `standard` key of the profile (kept in `Profile.extra`), and every
part has a default, so a project with no profile, or no `standard` key, is measured against the
framework's own numbers.
"""
from __future__ import annotations

import re
from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import Any

from apm.profile import Profile, ProfileError

# Globs are compiled by the guard's glob compiler, so a match ignores case.
DEFAULT_EXCLUDES: tuple[str, ...] = (
    "**/node_modules/**", "**/vendor/**", "**/third_party/**", "**/dist/**", "**/build/**",
    "**/*.min.js", "**/*.generated.*", ".apm/**",
)
STANDARD_KEYS = ("limits", "metrics", "debt_sources", "adr_dir", "review_patterns", "ui", "layers")
METRICS_KEYS = ("include", "exclude", "extra_exclude", "builtin")
SOURCE_KEYS = ("name", "command", "numbers", "timeout")
LAYER_KEYS = ("name", "paths", "may_import")
# In `may_import`, "outside" means libraries beyond the standard library and "*" means every layer.
RESERVED_LAYERS: tuple[str, ...] = ("outside", "*")


@dataclass(frozen=True)
class Limits:
    function: int = 15
    file: int = 200
    public_methods: int = 7


@dataclass(frozen=True)
class MetricsConfig:
    include: tuple[str, ...] = ()
    exclude: tuple[str, ...] = DEFAULT_EXCLUDES
    builtin: bool = True


@dataclass(frozen=True)
class DebtSource:
    name: str
    command: str
    numbers: Mapping[str, str]
    timeout: int = 300


@dataclass(frozen=True)
class Standard:
    limits: Limits
    metrics: MetricsConfig
    sources: tuple[DebtSource, ...]
    adr_dir: str = "docs/adr/"
    review_patterns: Mapping[str, tuple[str, ...]] = field(default_factory=dict)
    ui: bool | None = None
    layers: tuple[Mapping[str, Any], ...] = ()


def load_standard(profile: Profile | None) -> Standard:
    """Read `profile.extra["standard"]`; raise ProfileError for any part that is malformed."""
    raw = profile.extra.get("standard", {}) if profile else {}
    _known(_object(raw, "standard"), STANDARD_KEYS, "standard")
    return Standard(
        limits=_limits(raw.get("limits", {})),
        metrics=_metrics(raw.get("metrics", {})),
        sources=_sources(raw.get("debt_sources", [])),
        adr_dir=_adr_dir(raw.get("adr_dir", "docs/adr/")),
        review_patterns=_review_patterns(raw.get("review_patterns", {})),
        ui=_ui(raw.get("ui")),
        layers=_layers(raw.get("layers", [])),
    )


def _known(given: dict[str, Any], allowed: tuple[str, ...], label: str) -> None:
    unknown = sorted(set(given) - set(allowed))
    if unknown:
        raise ProfileError(f"{label} has unknown keys: {', '.join(unknown)}")


def _object(value: object, label: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ProfileError(f"{label} must be an object")
    return value


def _text(value: object, label: str) -> str:
    if not isinstance(value, str) or not value:
        raise ProfileError(f"{label} must be a non-empty string")
    return value


def _strings(value: object, label: str) -> tuple[str, ...]:
    if not isinstance(value, list) or not all(isinstance(item, str) and item for item in value):
        raise ProfileError(f"{label} must be a list of non-empty strings")
    return tuple(value)


def _positive(value: object, label: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 1:
        raise ProfileError(f"{label} must be a positive integer")
    return value


def _limits(raw: object) -> Limits:
    given = _object(raw, "limits")
    _known(given, tuple(Limits.__dataclass_fields__), "limits")
    return Limits(**{name: _positive(value, f"limits.{name}") for name, value in given.items()})


def _metrics(raw: object) -> MetricsConfig:
    given = _object(raw, "metrics")
    _known(given, METRICS_KEYS, "metrics")
    builtin = given.get("builtin", True)
    if not isinstance(builtin, bool):
        raise ProfileError("metrics.builtin must be true or false")
    exclude = _strings(given["exclude"], "metrics.exclude") if "exclude" in given else DEFAULT_EXCLUDES
    extra = _strings(given.get("extra_exclude", []), "metrics.extra_exclude")
    include = _strings(given.get("include", []), "metrics.include")
    return MetricsConfig(include=include, exclude=exclude + extra, builtin=builtin)


def _sources(raw: object) -> tuple[DebtSource, ...]:
    if not isinstance(raw, list):
        raise ProfileError("debt_sources must be a list")
    sources = tuple(_source(item, f"debt_sources[{index}]") for index, item in enumerate(raw))
    names = [source.name for source in sources]
    for name in sorted({n for n in names if names.count(n) > 1}):
        raise ProfileError(f"debt_sources: duplicate name {name}")
    return sources


def _source(raw: object, label: str) -> DebtSource:
    given = _object(raw, label)
    _known(given, SOURCE_KEYS, label)
    numbers = _object(given.get("numbers"), f"{label}.numbers")
    if not numbers:
        raise ProfileError(f"{label}.numbers needs at least one entry")
    return DebtSource(
        _text(given.get("name"), f"{label}.name"),
        _text(given.get("command"), f"{label}.command"),
        {metric: _one_group(rx, f"{label} number {metric}") for metric, rx in numbers.items()},
        _positive(given.get("timeout", 300), f"{label}.timeout"),
    )


def _one_group(pattern: object, label: str) -> str:
    text = _text(pattern, label)
    try:
        groups = re.compile(text).groups
    except re.error as exc:
        raise ProfileError(f"{label}: regex does not compile: {exc}") from exc
    if groups != 1:
        raise ProfileError(f"{label}: regex needs exactly one group, found {groups}")
    return text


def _adr_dir(value: object) -> str:
    return _text(value, "adr_dir")


def _ui(value: object) -> bool | None:
    if value is not None and not isinstance(value, bool):
        raise ProfileError("ui must be true, false or unset")
    return value


def _review_patterns(raw: object) -> dict[str, tuple[str, ...]]:
    given = _object(raw, "review_patterns")
    return {_text(name, "review_patterns key"): _strings(patterns, f"review_patterns.{name}")
            for name, patterns in given.items()}


def _layers(raw: object) -> tuple[Mapping[str, Any], ...]:
    if not isinstance(raw, list):
        raise ProfileError("layers must be a list")
    layers = tuple(_layer(item, f"layers[{index}]") for index, item in enumerate(raw))
    names = [layer["name"] for layer in layers]
    if len(set(names)) != len(names) or set(names) & set(RESERVED_LAYERS):
        raise ProfileError(f"layers: names must be unique and not {' or '.join(RESERVED_LAYERS)}")
    for layer in layers:
        unknown = [name for name in layer["may_import"] if name not in (*names, *RESERVED_LAYERS)]
        if unknown:
            raise ProfileError(f"layers: {layer['name']} may import unknown layers {unknown}")
    return layers


def _layer(raw: object, label: str) -> dict[str, Any]:
    given = _object(raw, label)
    _known(given, LAYER_KEYS, label)
    return {
        "name": _text(given.get("name"), f"{label}.name"),
        "paths": list(_strings(given.get("paths"), f"{label}.paths")),
        "may_import": list(_strings(given.get("may_import"), f"{label}.may_import")),
    }
