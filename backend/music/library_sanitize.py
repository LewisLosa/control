import argparse
import json
import shutil
import subprocess
import tempfile
from pathlib import Path


AUDIO_EXTENSIONS = {".flac", ".m4a", ".mp3", ".ogg", ".opus", ".wav", ".aac"}
SIDECAR_NAMES = {"cover.jpg", "cover.jpeg", "cover.png", "folder.jpg", "folder.png"}


def probe_artwork(path: Path) -> bool:
    result = subprocess.run(
        ["ffprobe", "-v", "error", "-select_streams", "v", "-show_entries", "stream=index", "-of", "csv=p=0", str(path)],
        capture_output=True,
        text=True,
    )
    return result.returncode == 0 and bool(result.stdout.strip())


def inventory(root: Path) -> list[dict[str, str]]:
    entries: list[dict[str, str]] = []
    for path in sorted(root.rglob("*")):
        if not path.is_file():
            continue
        if path.suffix.lower() in AUDIO_EXTENSIONS and probe_artwork(path):
            entries.append({"type": "embedded", "path": str(path)})
        elif path.name.lower() in SIDECAR_NAMES:
            entries.append({"type": "sidecar", "path": str(path)})
    return entries


def clean_embedded(path: Path, root: Path, backup_root: Path) -> None:
    relative = path.relative_to(root)
    backup = backup_root / relative
    backup.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(path, backup)
    with tempfile.NamedTemporaryFile(dir=path.parent, suffix=path.suffix, delete=False) as handle:
        temporary = Path(handle.name)
    command = [
        "ffmpeg", "-y", "-v", "error", "-i", str(path),
        "-map", "0:a:0", "-map_metadata", "0", "-map_chapters", "-1", "-c:a", "copy", str(temporary),
    ]
    result = subprocess.run(command)
    if result.returncode != 0 or not temporary.exists() or temporary.stat().st_size == 0:
        temporary.unlink(missing_ok=True)
        raise RuntimeError(f"ffmpeg artwork cleanup failed: {path}")
    temporary.replace(path)


def main() -> None:
    parser = argparse.ArgumentParser(description="Inventory and safely remove embedded music artwork")
    parser.add_argument("root", type=Path)
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--backup-dir", type=Path)
    args = parser.parse_args()
    root = args.root.resolve()
    if not root.is_dir():
        raise SystemExit(f"library directory does not exist: {root}")
    entries = inventory(root)
    print(json.dumps({"root": str(root), "count": len(entries), "entries": entries}, indent=2))
    if not args.apply:
        return
    if args.backup_dir is None:
        raise SystemExit("--apply requires --backup-dir")
    backup_root = args.backup_dir.resolve()
    backup_root.mkdir(parents=True, exist_ok=True)
    for entry in entries:
        if entry["type"] == "embedded":
            clean_embedded(Path(entry["path"]), root, backup_root)


if __name__ == "__main__":
    main()
