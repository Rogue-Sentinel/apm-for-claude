import json
from pathlib import Path

import apm

ROOT = Path(__file__).resolve().parent.parent


def load(relative):
    return json.loads((ROOT / relative).read_text(encoding="utf-8"))


def test_plugin_manifest_version_matches_package():
    manifest = load(".claude-plugin/plugin.json")
    assert manifest["name"] == "apm"
    assert manifest["version"] == apm.VERSION


def test_marketplace_lists_apm_from_repo_root():
    marketplace = load(".claude-plugin/marketplace.json")
    assert marketplace["name"] == "rogue-sentinel"
    assert marketplace["owner"]["name"] == "Rogue-Sentinel"
    plugins = marketplace["plugins"]
    assert len(plugins) == 1
    assert plugins[0]["name"] == "apm"
    assert plugins[0]["source"] == "./"
    assert plugins[0]["description"].strip()
