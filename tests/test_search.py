import os
import sys
import pytest
from PySide6.QtWidgets import QApplication, QTreeWidgetItem
from PySide6.QtCore import Qt

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

def _get_app() -> QApplication:
    app = QApplication.instance()
    if app is None:
        app = QApplication(sys.argv[:1])
    return app

def test_search_bookmarks():
    app = _get_app()
    from nexus.main import MainWindow

    # Initialize window
    window = MainWindow()

    # Clear existing bookmarks to have a clean state
    window.bookmark_tree.clear()

    # Helper to add item
    def add_item(name, type_str, url="", parent=None):
        data = {"name": name, "type": type_str, "url": url}
        if type_str == "folder":
             data["children"] = []
        return window._create_tree_item(data, parent)

    work_folder = add_item("Work", "folder")
    github_bk = add_item("GitHub", "bookmark", "https://github.com", work_folder)
    jira_bk = add_item("Jira", "bookmark", "https://jira.atlassian.com", work_folder)

    personal_folder = add_item("Personal", "folder")
    youtube_bk = add_item("YouTube", "bookmark", "https://youtube.com", personal_folder)
    reddit_bk = add_item("Reddit", "bookmark", "https://reddit.com", personal_folder)

    # Ensure everything is visible initially
    assert not work_folder.isHidden()
    assert not github_bk.isHidden()
    assert not jira_bk.isHidden()
    assert not personal_folder.isHidden()
    assert not youtube_bk.isHidden()
    assert not reddit_bk.isHidden()

    # Test 1: Search for "GitHub"
    # Should show Work folder, GitHub bookmark. Hide Jira bookmark. Hide Personal folder.
    window._filter_bookmarks("GitHub")

    assert not work_folder.isHidden()
    assert not github_bk.isHidden()
    assert jira_bk.isHidden()
    assert personal_folder.isHidden()

    # Test 2: Search for "Work" (Folder match)
    # Should show Work folder AND ALL its children. Hide Personal folder.
    window._filter_bookmarks("Work")

    assert not work_folder.isHidden()
    assert not github_bk.isHidden()
    assert not jira_bk.isHidden()
    assert personal_folder.isHidden()

    # Test 3: Search for "tube" (matches YouTube)
    window._filter_bookmarks("tube")
    assert work_folder.isHidden()
    assert not personal_folder.isHidden()
    assert not youtube_bk.isHidden()
    assert reddit_bk.isHidden()

    # Test 4: Clear search
    window._filter_bookmarks("")
    assert not work_folder.isHidden()
    assert not github_bk.isHidden()
    assert not jira_bk.isHidden()
    assert not personal_folder.isHidden()
    assert not youtube_bk.isHidden()
    assert not reddit_bk.isHidden()

    window.close()
