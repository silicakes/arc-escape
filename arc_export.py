#!/usr/bin/env python3
"""Export Arc browser spaces, folders and pinned tabs to a Netscape bookmarks HTML file.

The output imports into Chrome, Zen, Firefox, Safari, Brave, Edge, etc.
Each Arc space becomes a top-level folder; Arc folders (including nested ones)
become sub-folders; pinned tabs become bookmarks. Favorites (top apps) get their
own folder.

Usage:
    python3 arc_export.py                       # writes exports/arc_bookmarks.html
    python3 arc_export.py -o out.html --unpinned --split
"""

import argparse
import html
import json
import os
import sys
import time
from pathlib import Path


def find_sidebar():
    """Locate StorableSidebar.json on macOS or Windows (Arc ships as an MSIX package there)."""
    candidates = [Path.home() / "Library/Application Support/Arc/StorableSidebar.json"]
    local_appdata = os.environ.get("LOCALAPPDATA")
    if local_appdata:
        packages = Path(local_appdata) / "Packages"
        candidates += sorted(packages.glob("TheBrowserCompany.Arc*/LocalCache/Local/Arc/StorableSidebar.json"))
    for path in candidates:
        if path.exists():
            return path
    return candidates[0]


DEFAULT_SIDEBAR = find_sidebar()
DEFAULT_OUTPUT = Path("exports") / "arc_bookmarks.html"


def pairs(flat):
    """Arc stores maps as flat lists: [key, value, key, value, ...]."""
    return {flat[i]: flat[i + 1] for i in range(0, len(flat) - 1, 2) if isinstance(flat[i], str)}


def container_id(space, kind):
    """Find the item container ID for 'pinned' or 'unpinned' in a space."""
    ids = space.get("containerIDs", [])
    for i in range(0, len(ids) - 1, 2):
        if ids[i] == kind:
            return ids[i + 1]
    return None


def profile_name(space):
    profile = space.get("profile") or {}
    if "default" in profile:
        return None
    custom = profile.get("custom", {}).get("_0", {})
    return custom.get("directoryBasename") or "custom profile"


def item_title(item):
    tab = item.get("data", {}).get("tab")
    title = item.get("title") or (tab or {}).get("savedTitle")
    return (title or "").strip()


def build_node(item_id, items, seen):
    """Turn an Arc item into {'title', 'url'} or {'title', 'children'}; None if empty."""
    if item_id in seen or item_id not in items:
        return None
    seen.add(item_id)
    item = items[item_id]
    data = item.get("data", {})

    if "tab" in data:
        url = data["tab"].get("savedURL")
        if not url:
            return None
        return {"title": item_title(item) or url, "url": url, "created": item.get("createdAt")}

    # Folders ("list"), split views, easels, live folders etc. all carry childrenIds.
    children = [n for n in (build_node(c, items, seen) for c in item.get("childrenIds", [])) if n]
    if not children:
        return None
    if "list" not in data and len(children) == 1:
        return children[0]  # e.g. a split view collapsed to one tab
    title = item_title(item) or ("Split View" if "splitView" in data else "Untitled folder")
    return {"title": title, "children": children, "created": item.get("createdAt")}


def container_children(cid, items, seen):
    if not cid or cid not in items:
        return []
    return [n for n in (build_node(c, items, seen) for c in items[cid].get("childrenIds", [])) if n]


def extract(sidebar, include_unpinned):
    """Return a list of top-level folders (one per space plus Favorites)."""
    folders = []
    for container in sidebar["sidebar"]["containers"]:
        if "spaces" not in container or "items" not in container:
            continue
        items = pairs(container["items"])
        spaces = [s for s in pairs(container["spaces"]).values() if isinstance(s, dict)]
        # Skip the "standalone" Little Arc container: its spaces have no title.
        if not any(s.get("title") for s in spaces):
            continue
        seen = set()

        favorites = []
        for cid in (v for v in container.get("topAppsContainerIDs", []) if isinstance(v, str)):
            favorites += container_children(cid, items, seen)
        if favorites:
            folders.append({"title": "Favorites", "children": favorites})

        for space in spaces:
            title = space.get("title") or "Untitled space"
            profile = profile_name(space)
            if profile:
                title = f"{title} ({profile})"
            children = container_children(container_id(space, "pinned"), items, seen)
            if include_unpinned:
                unpinned = container_children(container_id(space, "unpinned"), items, seen)
                if unpinned:
                    children.append({"title": "Unpinned tabs", "children": unpinned})
            folders.append({"title": title, "children": children})
    return folders


# Arc timestamps are seconds since 2001-01-01 (Apple reference date).
APPLE_EPOCH_OFFSET = 978307200


def add_date(node):
    created = node.get("created")
    ts = int(created + APPLE_EPOCH_OFFSET) if created else int(time.time())
    return f' ADD_DATE="{ts}"'


def render(nodes, depth=1):
    pad = "    " * depth
    out = []
    for node in nodes:
        title = html.escape(node["title"])
        if "url" in node:
            out.append(f'{pad}<DT><A HREF="{html.escape(node["url"], quote=True)}"{add_date(node)}>{title}</A>')
        else:
            out.append(f"{pad}<DT><H3{add_date(node)}>{title}</H3>")
            out.append(f"{pad}<DL><p>")
            out.extend(render(node["children"], depth + 1))
            out.append(f"{pad}</DL><p>")
    return out


def to_html(folders):
    lines = [
        "<!DOCTYPE NETSCAPE-Bookmark-file-1>",
        "<!-- This is an automatically generated file. Exported from Arc. -->",
        '<META HTTP-EQUIV="Content-Type" CONTENT="text/html; charset=UTF-8">',
        "<TITLE>Bookmarks</TITLE>",
        "<H1>Bookmarks</H1>",
        "<DL><p>",
        *render(folders),
        "</DL><p>",
    ]
    return "\n".join(lines) + "\n"


def count(nodes):
    bookmarks = folders = 0
    for n in nodes:
        if "url" in n:
            bookmarks += 1
        else:
            folders += 1
            b, f = count(n["children"])
            bookmarks, folders = bookmarks + b, folders + f
    return bookmarks, folders


def print_tree(nodes, depth=0):
    for n in nodes:
        if "url" not in n:
            b, _ = count(n["children"])
            print(f"{'  ' * depth}📁 {n['title']} ({b})")
            print_tree(n["children"], depth + 1)


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("-i", "--input", type=Path, default=DEFAULT_SIDEBAR, help=f"path to StorableSidebar.json (default: {DEFAULT_SIDEBAR})")
    p.add_argument("-o", "--output", type=Path, default=DEFAULT_OUTPUT, help=f"output HTML file (default: {DEFAULT_OUTPUT})")
    p.add_argument("--unpinned", action="store_true", help="also export unpinned (Today) tabs into an 'Unpinned tabs' sub-folder")
    p.add_argument("--split", action="store_true", help="additionally write one HTML file per space (handy for Zen workspaces)")
    args = p.parse_args()

    # Windows consoles may not default to UTF-8; keep emoji/titles from crashing print().
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    if not args.input.exists():
        sys.exit(f"Not found: {args.input}\nIs Arc installed? Pass the file with --input.")

    with args.input.open(encoding="utf-8") as f:
        folders = extract(json.load(f), args.unpinned)
    if not folders:
        sys.exit("No spaces found in the sidebar file.")

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(to_html(folders), encoding="utf-8")
    b, f = count(folders)
    print_tree(folders)
    print(f"\nWrote {args.output} — {b} bookmarks in {f} folders.")

    if args.split:
        stem, suffix = args.output.stem, args.output.suffix or ".html"
        for folder in folders:
            safe = "".join(c if c.isalnum() or c in " -_" else "_" for c in folder["title"]).strip()
            path = args.output.with_name(f"{stem} - {safe}{suffix}")
            path.write_text(to_html(folder["children"]), encoding="utf-8")
            print(f"Wrote {path}")


if __name__ == "__main__":
    main()
