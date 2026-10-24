"""Mirror hw4/frontend to a folder outside OneDrive (used by run_site.command).

Copies a file only when its contents actually changed, so Vite doesn't see
"changed" config files every second and restart. Skips node_modules and dist.

    python sync_frontend.py SRC DEST          # one pass
    python sync_frontend.py SRC DEST --watch  # keep mirroring every second
"""

import os
import sys
import time
from pathlib import Path

SKIP = {"node_modules", "dist", ".vite", "__pycache__", ".DS_Store"}


def files(root: Path) -> dict[str, Path]:
    out = {}
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in SKIP]
        for name in filenames:
            if name in SKIP:
                continue
            p = Path(dirpath) / name
            out[str(p.relative_to(root))] = p
    return out


def sync(src: Path, dest: Path) -> int:
    changed = 0
    src_files = files(src)
    for rel, sp in src_files.items():
        dp = dest / rel
        try:
            data = sp.read_bytes()
        except OSError:
            continue  # OneDrive may hold a file for a moment; try next pass
        if dp.exists() and dp.read_bytes() == data:
            continue
        dp.parent.mkdir(parents=True, exist_ok=True)
        dp.write_bytes(data)
        changed += 1
    # remove files deleted from the source
    for rel, dp in files(dest).items():
        if rel not in src_files:
            try:
                dp.unlink()
                changed += 1
            except OSError:
                pass
    return changed


if __name__ == "__main__":
    src, dest = Path(sys.argv[1]), Path(sys.argv[2])
    dest.mkdir(parents=True, exist_ok=True)
    sync(src, dest)
    if "--watch" in sys.argv:
        while True:
            time.sleep(1)
            try:
                sync(src, dest)
            except Exception as e:  # keep the site running even if one pass fails
                print(f"[sync] {e}", file=sys.stderr)
