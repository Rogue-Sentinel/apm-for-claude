from apm.layer_map import layer_overlaps

LAYERS = [
    {"name": "domain", "paths": ["src/core/**"], "may_import": []},
    {"name": "adapters", "paths": ["src/**/io/**"], "may_import": ["domain"]},
]


def test_layer_overlaps() -> None:
    paths = ["src/core/io/x.py", "src/core/y.py", "src/app/io/z.py"]

    assert layer_overlaps(paths, LAYERS) == [("src/core/io/x.py", "domain", "adapters")]


def test_disjoint_globs_have_no_overlaps() -> None:
    layers = [{"name": "a", "paths": ["a/**"], "may_import": []}, {"name": "b", "paths": ["b/**"], "may_import": []}]

    assert layer_overlaps(["a/x.py", "b/y.py"], layers) == []


def test_overlaps_are_sorted_by_path_and_name_each_pair_of_layers() -> None:
    layers = [*LAYERS, {"name": "ui", "paths": ["src/core/**"], "may_import": []}]
    paths = ["src/core/io/z.py", "src/core/io/a.py"]

    found = layer_overlaps(paths, layers)

    assert [(a, b) for p, a, b in found if p == "src/core/io/a.py"] == [
        ("domain", "adapters"), ("domain", "ui"), ("adapters", "ui"),
    ]
    assert found[0][0] == "src/core/io/a.py"


def test_one_layer_with_overlapping_globs_is_not_an_overlap() -> None:
    layers = [{"name": "a", "paths": ["a/**", "a/b/**"], "may_import": []}]

    assert layer_overlaps(["a/b/x.py"], layers) == []
