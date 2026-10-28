<p align="center">
  <img src="assets/banner.svg" alt="arc-escape — take your spaces, folders & tabs with you" width="100%">
</p>

<p align="center">
  <img src="https://img.shields.io/badge/python-3.8%2B-3776AB?logo=python&logoColor=white" alt="Python 3.8+">
  <img src="https://img.shields.io/badge/platform-macOS%20%7C%20Windows-555?logo=apple&logoColor=white" alt="macOS | Windows">
  <img src="https://img.shields.io/badge/dependencies-none-brightgreen" alt="No dependencies">
  <img src="https://img.shields.io/badge/exports%20to-Zen%20%7C%20Chrome%20%7C%20Firefox-c86dd7" alt="Exports to Zen, Chrome, Firefox">
  <a href="LICENSE"><img src="https://img.shields.io/github/license/silicakes/arc-escape" alt="MIT License"></a>
  <a href="https://github.com/silicakes/arc-escape/stargazers"><img src="https://img.shields.io/github/stars/silicakes/arc-escape?style=flat" alt="GitHub stars"></a>
</p>

# arc-escape

Arc browser is being deprecated. This script exports your Arc **spaces, folders, sub-folders and pinned tabs** into a standard bookmarks HTML file. You can import that file into Zen, Chrome, Firefox, Brave, Edge or Safari.

Arc doesn't have a proper bookmark export. Everything lives in a `StorableSidebar.json` file, which the script finds automatically:

- **macOS:** `~/Library/Application Support/Arc/StorableSidebar.json`
- **Windows:** `%LOCALAPPDATA%\Packages\TheBrowserCompany.Arc_*\LocalCache\Local\Arc\StorableSidebar.json`

The script reads that file and keeps your structure:

| Arc | Export |
|---|---|
| Space | Top-level folder |
| Folder / sub-folder (any depth) | Nested folder |
| Pinned tab | Bookmark (with your custom title) |
| Favorites (top icons) | `Favorites` folder |
| Split view | Small folder holding its tabs |
| Unpinned "Today" tabs | `Unpinned tabs` sub-folder |

By default it exports everything, so you get your current Arc state. Use `--exclude` to leave sections out.

## Requirements

- macOS or Windows with Arc installed
- Python 3.8+ (standard library only, no dependencies). On Windows, use `python` or `py` in place of `python3`.

## Usage

Output goes to `./exports/`, which is git-ignored.

```bash
python3 arc_export.py                       # everything → exports/arc_bookmarks.html
python3 arc_export.py --exclude unpinned    # skip unpinned (Today) tabs
python3 arc_export.py --exclude unpinned --exclude favorites   # pinned items only
python3 arc_export.py --split               # also write one HTML file per space
python3 arc_export.py -i path/to/StorableSidebar.json -o out.html
```

The script prints a tree of what it exported:

```
📁 Favorites (3)
📁 Personal (11)
  📁 Recipes (2)
📁 Work (5)
  📁 Pull Requests (4)
...
Wrote exports/arc_bookmarks.html — 94 bookmarks in 12 folders.
```

## Importing

**Zen / Firefox:** open Bookmarks → Manage bookmarks (⌘⇧O). Click the **⇅** button and choose **Import Bookmarks from HTML…**. The imported folders appear under **Bookmarks Menu**. To recreate your spaces, create a Zen workspace for each one. Then open its folder with "Open All in Tabs" and pin the tabs you want to keep. Add Favorites to Essentials.

**Chrome / Brave / Edge:** open `chrome://bookmarks`, click ⋮ and choose **Import bookmarks**. To get something close to Arc's sidebar, right-click a space's folder and choose **Open all in new tab group**, then save the group.

## Notes

- The export is a snapshot of what's in Arc right now. Live folders, such as GitHub pull requests, are saved as static links.
- Only `StorableSidebar.json` is read. Arc is never modified.
- The generated HTML files contain your personal browsing data. They're written to `exports/`, which `.gitignore` excludes.
