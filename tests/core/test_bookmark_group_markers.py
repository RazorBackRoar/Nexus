"""Group reference markers survive a save/load round trip."""

from nexus.core.bookmarks import BookmarkManager


def test_group_marker_round_trips(tmp_path):
    """A folder containing a group marker preserves the marker on reload."""
    manager = BookmarkManager(tmp_path / "bookmarks.json")
    raw = [
        {
            "name": "Favorites",
            "type": "folder",
            "children": [
                {"type": "group", "id": "grp_a1b2c3d4"},
                {"type": "group", "id": "grp_b2c3d4e5"},
            ],
        }
    ]
    assert manager.save_bookmarks_raw(raw) is True

    reloaded = manager.load_bookmarks_raw()
    assert reloaded[0]["children"][0] == {"type": "group", "id": "grp_a1b2c3d4"}
    assert reloaded[0]["children"][1] == {"type": "group", "id": "grp_b2c3d4e5"}


def test_group_marker_load_is_robust_to_unknown_keys(tmp_path):
    """Future keys on a group marker do not break loading."""
    manager = BookmarkManager(tmp_path / "bookmarks.json")
    raw = [
        {
            "name": "Favorites",
            "type": "folder",
            "children": [
                {"type": "group", "id": "grp_a1b2c3d4", "future_field": "ignored"},
            ],
        }
    ]
    manager.save_bookmarks_raw(raw)
    reloaded = manager.load_bookmarks_raw()
    assert reloaded[0]["children"][0]["id"] == "grp_a1b2c3d4"
