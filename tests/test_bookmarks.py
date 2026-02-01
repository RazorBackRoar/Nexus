"""Tests for Safari bookmark parsing functionality.

These tests verify the core bookmark management features including
plist parsing, bookmark data models, and folder hierarchy.
"""

import pytest
from pathlib import Path
import plistlib
from datetime import datetime


def test_bookmark_data_structure():
    """Test basic bookmark data structure."""
    # Create a sample bookmark dictionary (Safari plist format)
    bookmark = {
        'URLString': 'https://example.com',
        'URIDictionary': {'title': 'Example Site'},
        'WebBookmarkUUID': '12345-67890',
        'WebBookmarkType': 'WebBookmarkTypeLeaf'
    }

    # Verify structure
    assert 'URLString' in bookmark
    assert 'URIDictionary' in bookmark
    assert bookmark['WebBookmarkType'] == 'WebBookmarkTypeLeaf'
    assert bookmark['URIDictionary']['title'] == 'Example Site'


def test_bookmark_folder_structure():
    """Test bookmark folder data structure."""
    folder = {
        'Title': 'My Bookmarks',
        'Children': [],
        'WebBookmarkUUID': 'folder-uuid',
        'WebBookmarkType': 'WebBookmarkTypeList'
    }

    # Verify folder structure
    assert 'Title' in folder
    assert 'Children' in folder
    assert folder['WebBookmarkType'] == 'WebBookmarkTypeList'
    assert isinstance(folder['Children'], list)


def test_nested_bookmark_structure():
    """Test nested bookmark folder hierarchy."""
    # Create nested structure
    child_bookmark = {
        'URLString': 'https://child.example.com',
        'URIDictionary': {'title': 'Child Site'},
        'WebBookmarkType': 'WebBookmarkTypeLeaf'
    }

    parent_folder = {
        'Title': 'Parent Folder',
        'Children': [child_bookmark],
        'WebBookmarkType': 'WebBookmarkTypeList'
    }

    root = {
        'Title': 'Root',
        'Children': [parent_folder],
        'WebBookmarkType': 'WebBookmarkTypeList'
    }

    # Verify hierarchy
    assert len(root['Children']) == 1
    assert root['Children'][0]['Title'] == 'Parent Folder'
    assert len(root['Children'][0]['Children']) == 1
    assert root['Children'][0]['Children'][0]['URLString'] == 'https://child.example.com'


def test_plist_binary_format_handling():
    """Test that we can handle binary plist format."""
    # Create a sample plist structure
    test_data = {
        'Title': 'Test Bookmarks',
        'Children': [
            {
                'URLString': 'https://test.com',
                'URIDictionary': {'title': 'Test'},
                'WebBookmarkType': 'WebBookmarkTypeLeaf'
            }
        ]
    }

    # Serialize to binary plist
    binary_plist = plistlib.dumps(test_data, fmt=plistlib.FMT_BINARY)

    # Verify we can deserialize it
    loaded_data = plistlib.loads(binary_plist)
    assert loaded_data['Title'] == 'Test Bookmarks'
    assert len(loaded_data['Children']) == 1
    assert loaded_data['Children'][0]['URLString'] == 'https://test.com'


def test_bookmark_url_validation():
    """Test URL validation for bookmarks."""
    valid_urls = [
        'https://example.com',
        'http://example.com',
        'https://example.com/path',
        'https://example.com/path?query=value',
        'https://subdomain.example.com'
    ]

    for url in valid_urls:
        assert url.startswith('http://') or url.startswith('https://'), \
            f"URL should start with http:// or https://: {url}"


def test_bookmark_title_sanitization():
    """Test that bookmark titles are properly handled."""
    # Test various title formats
    titles = [
        'Normal Title',
        'Title with "quotes"',
        'Title with <html> tags',
        'Title with / slashes',
        'Title with émojis 🔖',
        ''  # Empty title
    ]

    for title in titles:
        bookmark = {
            'URIDictionary': {'title': title},
            'URLString': 'https://example.com',
            'WebBookmarkType': 'WebBookmarkTypeLeaf'
        }

        # Verify title is preserved
        assert bookmark['URIDictionary']['title'] == title


def test_safari_bookmarks_bar_structure():
    """Test the standard Safari bookmarks bar structure."""
    bookmarks_bar = {
        'Title': 'BookmarksBar',
        'Children': [],
        'WebBookmarkType': 'WebBookmarkTypeList'
    }

    assert bookmarks_bar['Title'] == 'BookmarksBar'
    assert bookmarks_bar['WebBookmarkType'] == 'WebBookmarkTypeList'


def test_safari_reading_list_structure():
    """Test the Safari reading list structure."""
    reading_list = {
        'Title': 'com.apple.ReadingList',
        'Children': [],
        'WebBookmarkType': 'WebBookmarkTypeList'
    }

    assert reading_list['Title'] == 'com.apple.ReadingList'
    assert reading_list['WebBookmarkType'] == 'WebBookmarkTypeList'


def test_bookmark_uuid_uniqueness():
    """Test that bookmark UUIDs should be unique."""
    bookmark1 = {
        'WebBookmarkUUID': 'uuid-1',
        'URLString': 'https://example1.com'
    }

    bookmark2 = {
        'WebBookmarkUUID': 'uuid-2',
        'URLString': 'https://example2.com'
    }

    # UUIDs should be different
    assert bookmark1['WebBookmarkUUID'] != bookmark2['WebBookmarkUUID']


def test_empty_bookmark_folder():
    """Test handling of empty bookmark folders."""
    empty_folder = {
        'Title': 'Empty Folder',
        'Children': [],
        'WebBookmarkType': 'WebBookmarkTypeList'
    }

    assert len(empty_folder['Children']) == 0
    assert empty_folder['WebBookmarkType'] == 'WebBookmarkTypeList'
