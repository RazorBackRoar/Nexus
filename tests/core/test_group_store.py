"""GroupStore round-trip and atomic-save behavior."""

import json
from pathlib import Path

from nexus.core.group_store import GroupStore
from nexus.core.models import BookmarkGroup, GroupItem


def _group(id: str = "grp_a1b2c3d4", name: str = "Sunday reading") -> BookmarkGroup:
    return BookmarkGroup(
        id=id,
        name=name,
        created_at="2026-07-16T18:20:00",
        items=[GroupItem(title="Example", url="https://example.com")],
    )


def test_load_missing_file_returns_empty(tmp_path: Path):
    store = GroupStore(tmp_path / "groups.json")
    assert store.load_groups() == []


def test_save_then_load_round_trips(tmp_path: Path):
    store = GroupStore(tmp_path / "groups.json")
    store.upsert_group(_group())
    reloaded = store.load_groups()
    assert len(reloaded) == 1
    assert reloaded[0].name == "Sunday reading"
    assert reloaded[0].items[0].url == "https://example.com"


def test_upsert_overwrites_by_id(tmp_path: Path):
    store = GroupStore(tmp_path / "groups.json")
    store.upsert_group(_group(name="Old name"))
    store.upsert_group(_group(name="New name"))
    groups = store.load_groups()
    assert len(groups) == 1
    assert groups[0].name == "New name"


def test_delete_removes_group(tmp_path: Path):
    store = GroupStore(tmp_path / "groups.json")
    store.upsert_group(_group(id="grp_keep"))
    store.upsert_group(_group(id="grp_drop"))
    store.delete_group("grp_drop")
    ids = [g.id for g in store.load_groups()]
    assert ids == ["grp_keep"]


def test_delete_missing_id_is_noop(tmp_path: Path):
    store = GroupStore(tmp_path / "groups.json")
    store.upsert_group(_group())
    store.delete_group("grp_does_not_exist")
    assert len(store.load_groups()) == 1


def test_save_creates_parent_directory(tmp_path: Path):
    store = GroupStore(tmp_path / "nested" / "dir" / "groups.json")
    store.upsert_group(_group())
    assert (tmp_path / "nested" / "dir" / "groups.json").exists()


def test_save_keeps_a_backup(tmp_path: Path):
    store = GroupStore(tmp_path / "groups.json")
    store.upsert_group(_group(name="v1"))
    store.upsert_group(_group(name="v2"))
    backup = tmp_path / "groups.json.bak"
    assert backup.exists()
    with open(backup, encoding="utf-8") as f:
        bak_data = json.load(f)
    assert bak_data[0]["name"] == "v1"


def test_load_falls_back_to_backup_on_corruption(tmp_path: Path):
    primary = tmp_path / "groups.json"
    backup = tmp_path / "groups.json.bak"
    primary.write_text("not valid json", encoding="utf-8")
    backup.write_text(
        json.dumps(
            [{"id": "grp_a", "name": "from bak", "created_at": "", "items": []}]
        ),
        encoding="utf-8",
    )
    store = GroupStore(primary)
    groups = store.load_groups()
    assert len(groups) == 1
    assert groups[0].id == "grp_a"


def test_get_group_returns_payload(tmp_path: Path):
    store = GroupStore(tmp_path / "groups.json")
    store.upsert_group(_group())
    fetched = store.get_group("grp_a1b2c3d4")
    assert fetched is not None
    assert fetched.name == "Sunday reading"


def test_get_group_missing_returns_none(tmp_path: Path):
    store = GroupStore(tmp_path / "groups.json")
    assert store.get_group("grp_missing") is None


def test_corrupted_items_in_one_group_does_not_lose_others(tmp_path: Path):
    """A single group with malformed items must not crash the whole load."""
    primary = tmp_path / "groups.json"
    primary.write_text(
        json.dumps(
            [
                {
                    "id": "grp_good",
                    "name": "good",
                    "created_at": "",
                    "items": [{"title": "t", "url": "https://x.com"}],
                },
                {
                    "id": "grp_bad",
                    "name": "bad",
                    "created_at": "",
                    "items": ["not a dict", {"title": "no url"}],
                },
            ]
        ),
        encoding="utf-8",
    )
    store = GroupStore(primary)
    groups = store.load_groups()
    # The good group survives; the bad group is dropped (its items
    # path raises AttributeError on the bare-string entry).
    assert [g.id for g in groups] == ["grp_good"]
