"""The coverage inventory: every item of the old standard, and the framework file that covers it."""
from __future__ import annotations

import json
from pathlib import Path

PLUGIN_ROOT = Path(__file__).resolve().parent.parent.parent
INVENTORY_PATH = PLUGIN_ROOT / "standard" / "coverage.json"


class CoverageError(ValueError):
    """The inventory is malformed."""


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise CoverageError(message)


def _check_item(item: dict, source_ids: set[str], seen: set[str]) -> None:
    item_id = item.get("id")
    _require(bool(item_id) and item_id not in seen, f"duplicate or missing item id: {item_id!r}")
    seen.add(item_id)
    _require(item.get("source") in source_ids, f"{item_id}: unknown source {item.get('source')!r}")
    covers = item.get("covered_by")
    _require(isinstance(covers, list) and bool(covers), f"{item_id}: covered_by is empty")
    _require(all(isinstance(c, dict) and c.get("file") for c in covers), f"{item_id}: a cover has no file")


def load_inventory(path: Path) -> dict:
    inventory = json.loads(path.read_text(encoding="utf-8"))
    sources = inventory.get("sources")
    _require(isinstance(sources, list) and isinstance(inventory.get("items"), list), "needs sources and items")
    source_ids = {source["id"] for source in sources}
    _require(len(source_ids) == len(sources), "duplicate source id")
    seen: set[str] = set()
    for item in inventory["items"]:
        _check_item(item, source_ids, seen)
    return inventory


def _has_anchor(text: str, anchor: str) -> bool:
    if anchor.startswith("#"):
        return anchor in text.splitlines()
    return anchor in text


def _cover_gap(item_id: str, cover: dict, root: Path) -> str | None:
    target = root / cover["file"]
    if not target.is_file():
        return f"{item_id}: cover file missing: {cover['file']}"
    anchor = cover.get("anchor")
    if anchor and not _has_anchor(target.read_text(encoding="utf-8"), anchor):
        return f"{item_id}: anchor not found in {cover['file']}: {anchor}"
    return None


def find_gaps(inventory: dict, root: Path) -> list[str]:
    gaps = []
    for item in inventory["items"]:
        covers = item.get("covered_by") or []
        if not covers:
            gaps.append(f"{item['id']}: no cover")
        gaps.extend(g for c in covers if (g := _cover_gap(item["id"], c, root)))
    return gaps


def scan_source(inventory: dict, source_id: str, source_root: Path) -> list[str]:
    source = next(s for s in inventory["sources"] if s["id"] == source_id)
    items = [i for i in inventory["items"] if i["source"] == source_id]
    known = {i["source_path"] for i in items} | {n["path"] for n in source.get("not_methodology", [])}
    found = {p.relative_to(source_root).as_posix() for g in source.get("scan", []) for p in source_root.glob(g) if p.is_file()}
    problems = [f"not inventoried: {path}" for path in sorted(found - known)]
    problems += [f"missing in source: {i['source_path']}" for i in items if i.get("source_path") and not (source_root / i["source_path"]).is_file()]
    return problems


def _link(cover: dict) -> str:
    anchor = cover.get("anchor", "")
    label = f"{cover['file']} {anchor}".strip()
    slug = anchor.lstrip("#").strip().lower().replace(" ", "-") if anchor.startswith("#") else ""
    return f"[{label}](../{cover['file']}#{slug})" if slug else f"[{label}](../{cover['file']})"


def _source_table(source: dict, items: list[dict]) -> list[str]:
    lines = [f"## {source['title']}", "", f"Origin: {source['origin']}", "", "| Item | Covered by |", "|---|---|"]
    for item in items:
        covers = "<br>".join(_link(c) for c in item["covered_by"])
        lines.append(f"| {item['what']} | {covers} |")
    return lines + [""]


def render_table(inventory: dict) -> str:
    lines = ["# Coverage of the old standard", ""]
    for source in inventory["sources"]:
        items = [i for i in inventory["items"] if i["source"] == source["id"]]
        lines += _source_table(source, items)
    gaps = find_gaps(inventory, PLUGIN_ROOT)
    return "\n".join(lines + [f"**Gaps: {len(gaps)}**", ""])
