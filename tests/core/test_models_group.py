"""GroupItem and BookmarkGroup are plain dataclasses."""

from nexus.core.models import BookmarkGroup, GroupItem


def test_group_item_stores_title_and_url():
    item = GroupItem(title="Example", url="https://example.com")
    assert item.title == "Example"
    assert item.url == "https://example.com"


def test_group_item_title_may_be_empty():
    item = GroupItem(title="", url="https://example.com")
    assert item.title == ""


def test_bookmark_group_minimum_fields():
    g = BookmarkGroup(id="grp_a1b2c3d4", name="Sunday reading", items=[])
    assert g.id == "grp_a1b2c3d4"
    assert g.name == "Sunday reading"
    assert g.items == []
    assert g.created_at  # auto-populated by default_factory=_now_iso
