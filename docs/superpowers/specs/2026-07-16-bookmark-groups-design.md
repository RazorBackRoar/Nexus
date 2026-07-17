# Nexus Bookmark Groups — Design

**Status:** draft
**Date:** 2026-07-16
**Owner:** Mavis
**Codebase:** `/Users/home/Workspace/Apps/Nexus`

> **Terminology:** this spec uses "tab" and "folder" interchangeably
> for the rows in the sidebar (the user calls them tabs, the code
> calls them folders). They are the same thing.

## Goal

Let a Nexus user paste a Safari "Copy All Tabs" batch into the URL table,
save the batch as a **named group** under a chosen sidebar tab, and reuse
the group later (open it in Safari, drop it into another tab, or delete
it). The visual treatment must match the existing cosmic-glass design
language and the ten default tabs must use the explicit color palette
the user requested.

## Non-goals

- Syncing groups to iCloud, Chrome, or any other browser.
- Periodic/background polling of Safari windows.
- Group sharing or export.
- Editing individual items inside a saved group (rename / reorder /
  remove). v1 only supports rename, move, delete on the group itself.
- Detecting Safari tab changes after a group is saved — groups are
  snapshots, not live references.

## User-visible behavior

### Save flow

1. User pastes URLs into the URL table (Cmd+V or right-click → Paste).
2. User clicks **Save** in the button row.
3. A modal dialog appears with two fields:
   - **Group name** — text input, required, max 60 chars.
   - **Save into** — combo box listing the ten default tabs in
     fixed order followed by any user-created tabs. The currently
     selected sidebar tab is preselected.
4. User clicks **Save Group**.
5. The group is added to the target tab as a child row beneath the
   folder pill, the URL table is cleared, and a status-bar message
   confirms "Saved N URLs to *group name* in *tab*".

If the URL table is empty the Save button is disabled (already is
today; no change).

### Visual treatment

- **Default tabs** in the sidebar, top to bottom, with their fixed
  accent colors (final list, confirmed against the user's reference
  mockup `tabs.png`):

  | # | Tab | Color | Accent hex |
  |---|---|---|---|
  | 1 | Fun | Pink | `#E5738A` |
  | 2 | Misc | Orange | `#D4A05A` |
  | 3 | Tech | Blue | `#5B8DEF` |
  | 4 | Work | Red | `#E85A5A` |
  | 5 | Extra | Grey | `#8A95A8` |
  | 6 | Future | Brown | `#A87A5A` |
  | 7 | Hidden | Black | `#2A2A35` |
  | 8 | Special | White | `#F0F4FA` |
  | 9 | Favorites | Green | `#5BA86A` |
  | 10 | Sort | Black | `#2A2A35` |

  These names and colors **replace** the current six defaults
  (Favorites / Tech / Misc / Work / Later / News). Note: Hidden
  replaces the previously-suggested Private — its purpose is the
  same (a black tab where private/sensitive bookmarks go) but the
  user explicitly chose "Hidden" as the name.

  The ten fixed tabs ship in this order and are not reorderable.
  Custom folders added via the `+` button are appended after the
  ten defaults in creation order.

- **Groups** appear as a single indented row beneath their parent
  folder: small stack icon, group name (truncated with ellipsis),
  child-count badge `(N)`. No folder pill — clearly distinct from
  the pill that wraps each default tab. Hover shows a drag handle
  (or simply permits the drag from anywhere on the row).

- The existing **+** button is repurposed to open a new
  `NewFolderDialog` (see below) instead of the bare `QInputDialog`
  it uses today.

### New Folder dialog (replaces `QInputDialog`)

The "New Folder" modal — currently a single text field — grows a
color picker to the right of the name field:

- **Folder name** — text input, required, max 40 chars (matches the
  sidebar width).
- **Color** — a small palette of swatches (the ten default-tab
  colors, plus a "Custom…" option that opens `QColorDialog`).
  Selected swatch shows a thin border; clicking a swatch selects it.
- **OK / Cancel** as today.

The chosen color is persisted as the folder's accent and rendered
in the sidebar exactly like the ten defaults. This is what enables
the user's "create new bookmarks with a color" request.

### Drag and drop

- A group can be dragged from one tab to another tab header (or
  onto the tab's body) to move it.
- A group can be reordered within a tab by dragging up/down.
- The existing drag-and-drop for folders and individual bookmarks
  is unchanged.

### Context menu (right-click a group)

- **Open in Safari** — opens all items in the group using the
  current open-in-front-window path.
- **Rename** — inline edit on the row, with a `QInputDialog`
  fallback.
- **Move to…** — submenu listing the ten defaults + any custom
  tabs.
- **Delete** — confirm dialog, then remove from both the tree
  widget and `bookmark_groups.json`.

### Context menu (right-click a bookmark)

The current implementation has a Rename / Delete entry on bookmark
context menus. v1 makes the **Delete** action more discoverable and
adds a **Color** submenu so a user can recolor any individual
bookmark:

- **Open in Safari** — open the single bookmark.
- **Rename** — `QInputDialog` for a new name.
- **Color** — submenu listing the ten default swatches + Custom.
  Picking one updates the bookmark's accent and persists immediately.
- **Delete** — confirm dialog, then remove. (Already supported, but
  promoted to the top of the menu so it's the obvious action.)

The bookmark's color is stored on the `Bookmark` dataclass as an
optional accent (e.g. `accent: str | None = None`). When `None`, the
delegate uses the parent folder's accent.

### Persistence

- `bookmarks_v2.json` continues to hold the folder tree, but the
  serializer now also embeds groups (under each folder) so a single
  read brings the whole sidebar back.
- `bookmark_groups.json` is a **new** sidecar file holding the
  full payload for every group, keyed by group `id`. The tree
  stores only `{"type": "group", "id": "..."}` references; the
  group payload is loaded lazily from the sidecar when the group
  is opened, renamed, moved, or deleted.
- Both files use the existing atomic save / `.bak` pattern from
  `BookmarkManager.save_bookmarks`.

## Data model

The existing `Bookmark` and `BookmarkFolder` dataclasses grow two
new fields and a new marker type. New dataclasses for groups live
alongside them in `src/nexus/core/models.py`:

```python
@dataclass
class Bookmark:
    name: str
    url: str
    type: str = "bookmark"
    accent: str | None = None  # hex color, e.g. "#E5738A"; None = inherit folder

@dataclass
class BookmarkFolder:
    name: str
    children: list[BookmarkFolder | Bookmark | "GroupRef"] = field(default_factory=list)
    type: str = "folder"
    accent: str | None = None  # hex color set via the NewFolderDialog


@dataclass
class GroupItem:
    title: str   # may be "" if source had no title
    url: str

@dataclass
class BookmarkGroup:
    id: str               # 8-char random hex
    name: str
    created_at: str       # ISO 8601, e.g. "2026-07-16T18:20:00"
    items: list[GroupItem]
```

`GroupRef` is a marker dict, not a dataclass: `{"type": "group",
"id": str}`. It is deserialized by `BookmarkManager` as a raw
`dict` and resolved to a `QTreeWidgetItem` only at render time in
`MainWindow.load_bookmarks`.

## Storage

### `bookmark_groups.json`

```json
[
  {
    "id": "grp_a1b2c3d4",
    "name": "Sunday reading",
    "created_at": "2026-07-16T18:20:00",
    "items": [
      {"title": "Example Domain", "url": "https://example.com"},
      {"title": "", "url": "https://other.com"}
    ]
  }
]
```

Loaded by a new `GroupStore` class in `src/nexus/core/group_store.py`
that mirrors `BookmarkManager`:

- `load_groups() -> list[BookmarkGroup]`
- `save_groups(groups: list[BookmarkGroup]) -> bool`
- `get_group(group_id: str) -> BookmarkGroup | None`
- `upsert_group(group: BookmarkGroup) -> None`
- `delete_group(group_id: str) -> None`

All write methods are atomic (write to `.tmp`, rename, keep a `.bak`
on each successful overwrite).

### `bookmarks_v2.json`

Top-level shape is unchanged. Folder children now include group
reference markers alongside `Bookmark` and `BookmarkFolder`:

```json
{
  "name": "Favorites",
  "type": "folder",
  "accent": "#5BA86A",
  "children": [
    {"name": "Example", "type": "bookmark", "url": "https://example.com"},
    {"name": "Pink Site", "type": "bookmark", "url": "https://x.com", "accent": "#E5738A"},
    {"type": "group", "id": "grp_a1b2c3d4"}
  ]
}
```

When `BookmarkManager.load_bookmarks` encounters a group marker it
leaves it as-is in the returned `list[BookmarkNode]`; the
`MainWindow.load_bookmarks` walk resolves markers to `QTreeWidgetItem`s
on first render.

## Components

### New files

- `src/nexus/core/group_store.py` — `GroupStore` class (load, save,
  upsert, delete, get-by-id).
- `src/nexus/gui/dialogs/save_group_dialog.py` — modal `QDialog`
  with a name field and a target-folder combo box.
- `src/nexus/gui/dialogs/new_folder_dialog.py` — modal `QDialog`
  with a name field, a swatch palette, and a "Custom…" option
  that opens `QColorDialog`.
- `src/nexus/gui/widgets/group_row_delegate.py` — paint delegate
  for the indented group rows.
- `tests/core/test_group_store.py` — round-trip, atomic save, bad
  JSON recovery, missing-file default, `.bak` fallback.
- `tests/gui/test_save_group_dialog.py` — name validation, folder
  list, preselect, disabled state.
- `tests/gui/test_new_folder_dialog.py` — swatch selection,
  custom color, name validation, OK disabled when name is empty.
- `tests/gui/test_group_row_paint.py` — smoke test that paint
  doesn't crash with a 0/1/N-item group.

### Modified files

- `src/nexus/core/config.py` — add `BOOKMARK_GROUPS_FILE =
  "bookmark_groups.json"`.
- `src/nexus/core/models.py` — add `GroupItem`, `BookmarkGroup`,
  `GroupRef` marker.
- `src/nexus/core/bookmarks.py` — extend deserializer to skip
  group markers (let `GroupStore` own the payload); update
  serializer to emit group markers when walking a tree that
  contains them.
- `src/nexus/gui/main_window.py`:
  - Replace `DEFAULT_BOOKMARK_FOLDER_NAMES` with the new ten
    (Fun, Misc, Tech, Work, Extra, Future, Hidden, Special,
    Favorites, Sort).
  - Replace the `_resolve_folder_style` named-style map with one
    keyed on the new tab names + colors, plus a fallback that
    honors a folder's own `accent` field for user-created tabs.
  - Wire the **Save** button to a new `_save_urls_as_group` slot
    that opens the `SaveGroupDialog`, then writes the group via
    `GroupStore` and adds the row.
  - Render groups in the tree: a child of the folder
    `QTreeWidgetItem`, paint via `GroupRowDelegate`.
  - Add drag-and-drop for group rows: `setDragEnabled(True)`,
    override `dropMimeData` to handle `application/x-nexus-group`
    payloads.
  - Add the right-click context menu entries for groups.
- `src/nexus/gui/widgets.py` — `QTreeWidget` drag setup; the
  group drag mime type constant.

## Save flow detail

```python
def _save_urls_as_group(self) -> None:
    urls = self.url_table.get_all_urls()
    if not urls:
        return  # Save button is already disabled in this state
    dialog = SaveGroupDialog(parent=self, folders=self._folder_labels())
    if not dialog.exec():
        return
    name, target_folder = dialog.group_name, dialog.target_folder
    if not name.strip():
        return

    group = BookmarkGroup(
        id=generate_group_id(),
        name=name.strip(),
        created_at=datetime.now().isoformat(timespec="seconds"),
        items=[GroupItem(title=self._generate_bookmark_name(u), url=u) for u in urls],
    )
    self.group_store.upsert_group(group)

    # Insert marker into the in-memory tree and save the bookmark file.
    self._add_group_ref_to_folder(target_folder, group.id)
    self.bookmark_manager.save_bookmarks(self._tree_to_bookmarks())

    self.url_table.clear_table()
    self._set_status(f"Saved {len(urls)} URLs to '{name}' in {target_folder}")
```

## Error handling

| Failure | Behavior |
|---|---|
| `bookmark_groups.json` is corrupt | Log a warning, fall back to `bookmark_groups.json.bak`; if both fail, start with an empty list. The tree still loads (it just shows no groups). |
| `bookmark_groups.json` references an `id` not in the sidecar | The tree shows a placeholder row reading `(missing group)` (a tree-widget concept, not a model concept — rendered as a leaf item with `data.type == "missing_group"`) and the user can right-click → Delete to clean it up. |
| `SaveGroupDialog` is cancelled | No state change. URL table is preserved. |
| Group rename collides with an existing name in the same folder | Allowed (groups are uniquely identified by `id`); the sidebar truncates the displayed name. |
| User deletes a folder that contains groups | Groups are deleted; their entries are removed from `bookmark_groups.json` in the same atomic write. |

## Testing

- **Unit (group_store.py):**
  - Load returns `[]` for a missing file.
  - Load falls back to `.bak` when the primary file is corrupt.
  - `upsert_group` overwrites by id.
  - `delete_group` is a no-op on a missing id.
  - Save creates the parent directory if missing.
  - Save leaves a `.bak` after a successful overwrite.
- **Unit (bookmarks.py):** a folder containing both bookmarks and
  group markers round-trips through save/load without losing the
  markers.
- **GUI (save_group_dialog):** name field is required, max 60
  chars; folder list matches `DEFAULT_BOOKMARK_FOLDER_NAMES` order;
  preselect matches the currently active sidebar tab.
- **GUI (drag-and-drop):** dragging a group onto another folder
  calls `_move_group` and persists; the sidecar and the tree stay
  in sync.

## Migration

- The **ten** new default tab names replace the existing **six**.
  On `load_bookmarks`, `_normalize_bookmark_nodes` keeps any
  user-created folders and removes empty ones matching the *old*
  default set (`favorites`, `tech`, `misc`, `work`, `later`,
  `news`) so a user who never touched the defaults gets a tidy
  sidebar. The `apple`, `google`, `github`, `fun` removals are
  removed (those tabs no longer get auto-pruned; only the old
  defaults do).
- The new tabs are created in the fixed order Fun → Misc → Tech
  → Work → Extra → Future → Hidden → Special → Favorites → Sort,
  in the position the user saw in `tabs.png`. If a user already
  had a folder named, say, "Tech" with content, that folder is
  preserved in its original position and the new "Tech" tab is
  not duplicated — the existing folder is simply renamed to keep
  its data and shown in the new palette.
- Existing groups (none, since v1 ships with no prior version)
  need no migration.

## Out of scope (later)

- Open-all-in-Safari for a whole group (one click on the group
  → batch open). Trivial to add once groups exist; left for a
  follow-up so v1 stays focused.
- Group preview on hover.
- Search across group titles.
