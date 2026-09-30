import os
import subprocess
import sys
from pathlib import Path

from .encoding import build_vaapi_command, probe_media
from ..common import required_env


VIDEO_EXTENSIONS = {".mkv", ".mp4", ".avi", ".ts", ".webm"}


def encode_one(path: Path) -> bool:
    media = probe_media(str(path))
    if not media:
        print(f"[av1-encode] ffprobe failed: {path}", file=sys.stderr)
        return False
    stream = next((item for item in media.get("streams", []) if item.get("codec_type") == "video"), None)
    if not stream:
        return False
    if stream.get("codec_name") == "av1":
        print(f"[av1-encode] skipped AV1: {path}")
        return True

    width = int(stream.get("width") or 0)
    height = int(stream.get("height") or 0)
    try:
        numerator, denominator = (stream.get("r_frame_rate") or "24/1").split("/", 1)
        fps = float(numerator) / float(denominator)
    except (ValueError, ZeroDivisionError):
        fps = 24.0
    pixel_rate = width * height * max(fps, 1.0) / 1_000_000
    target = max(450, min(int(62 * (pixel_rate**0.76)), 6500))
    maximum = int(target * 1.6)
    temporary = path.with_name(f".{path.name}.av1.tmp.mkv")
    command = build_vaapi_command(str(path), str(temporary), stream, target, maximum)
    print(f"[av1-encode] {path} -> {target}k ({'10-bit+' if (stream.get('pix_fmt') or '').find('10') >= 0 else '8-bit'})")
    result = subprocess.run(command)
    if result.returncode != 0 or not temporary.exists() or temporary.stat().st_size == 0:
        temporary.unlink(missing_ok=True)
        return False
    path.unlink()
    temporary.replace(path)
    os.chmod(path, 0o664)
    try:
        import urllib.request

        request = urllib.request.Request(
            "http://127.0.0.1:8096/Library/Refresh?api_key=" + required_env("JELLYFIN_API_KEY"),
            method="POST",
        )
        urllib.request.urlopen(request, timeout=5).close()
    except Exception:
        pass
    return True


def main() -> None:
    if len(sys.argv) != 2:
        raise SystemExit("usage: av1-encode <file-or-directory>")
    target = Path(sys.argv[1])
    files = sorted(target.rglob("*") if target.is_dir() else [target])
    for path in files:
        if path.is_file() and path.suffix.lower() in VIDEO_EXTENSIONS and not encode_one(path):
            raise SystemExit(1)


if __name__ == "__main__":
    main()
