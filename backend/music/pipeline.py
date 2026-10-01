"""FFmpeg-only audio normalization and safe text tagging."""

import json
import os
import subprocess
import tempfile
from pathlib import Path
from typing import Any, Dict, Optional


TRUSTED_TAGS = (
    "TITLE",
    "ARTIST",
    "ALBUM",
    "ALBUMARTIST",
    "TRACKNUMBER",
    "DISCNUMBER",
    "DATE",
    "GENRE",
    "ISRC",
    "MUSICBRAINZ_TRACKID",
    "MUSICBRAINZ_ALBUMID",
    "MUSICBRAINZ_ARTISTID",
)


def _safe_text(value: Any) -> Optional[str]:
    if value is None:
        return None
    text = str(value).replace("\x00", "").replace("\r", " ").replace("\n", " ").strip()
    return text or None


def build_tag_arguments(metadata: Dict[str, Any]) -> list[str]:
    """Build FFmpeg arguments for trusted text fields only."""
    args = ["-map_metadata", "-1", "-map_chapters", "-1", "-map", "0:a:0"]
    for key in TRUSTED_TAGS:
        value = _safe_text(metadata.get(key.lower(), metadata.get(key)))
        if value is not None:
            args.extend(["-metadata", f"{key}={value}"])
    return args


def probe_audio(file_path: str) -> Dict[str, Any]:
    command = [
        "ffprobe",
        "-v",
        "error",
        "-select_streams",
        "a:0",
        "-show_entries",
        "stream=codec_name,bit_rate,sample_rate,channels:format=duration,size,bit_rate",
        "-of",
        "json",
        file_path,
    ]
    try:
        result = subprocess.run(command, capture_output=True, text=True, check=True)
        data = json.loads(result.stdout)
        stream = data.get("streams", [{}])[0]
        fmt = data.get("format", {})
        return {
            "codec": stream.get("codec_name", "unknown").lower(),
            "sample_rate": int(stream.get("sample_rate", 0)),
            "channels": int(stream.get("channels", 2)),
            "bit_rate": int(stream.get("bit_rate") or fmt.get("bit_rate") or 0),
            "duration": float(fmt.get("duration") or 0.0),
            "size": int(fmt.get("size") or 0),
        }
    except Exception as exc:
        return {"codec": "unknown", "error": str(exc), "duration": 0.0}


def process_audio(input_file: str, output_file: str, target_codec: str = "opus", target_bitrate: str = "160k") -> str:
    """Normalize audio while dropping all source metadata and image streams."""
    if target_codec != "opus":
        raise ValueError(f"unsupported target codec: {target_codec}")

    output = Path(output_file)
    output.parent.mkdir(parents=True, exist_ok=True)
    command = [
        "ffmpeg",
        "-y",
        "-hide_banner",
        "-loglevel",
        "error",
        "-i",
        input_file,
        "-map",
        "0:a:0",
        "-map_metadata",
        "-1",
        "-map_chapters",
        "-1",
        "-c:a",
        "libopus",
        "-b:a",
        target_bitrate,
        "-vbr",
        "on",
        "-compression_level",
        "10",
        "-af",
        "aresample=resampler=soxr:precision=28:cutoff=0.99:osr=48000,alimiter=limit=-1.0dB:level=false",
        str(output),
    ]
    subprocess.run(command, check=True)
    return str(output)


def tag_opus_file(
    opus_file: str,
    *,
    title: str,
    artist: str,
    album: Optional[str] = None,
    album_artist: Optional[str] = None,
    year: Optional[str] = None,
    track_number: Optional[int] = None,
    disc_number: Optional[int] = None,
    genre: Optional[str] = None,
    identifiers: Optional[Dict[str, str]] = None,
) -> bool:
    """Rewrite an Opus file with trusted text tags and no artwork."""
    metadata: Dict[str, Any] = {
        "title": title,
        "artist": artist,
        "album": album,
        "albumartist": album_artist,
        "date": year,
        "tracknumber": track_number,
        "discnumber": disc_number,
        "genre": genre,
    }
    if identifiers:
        metadata.update(identifiers)

    source = Path(opus_file)
    fd, temp_name = tempfile.mkstemp(prefix=f".{source.name}.", suffix=".opus", dir=source.parent)
    os.close(fd)
    try:
        command = [
            "ffmpeg",
            "-y",
            "-hide_banner",
            "-loglevel",
            "error",
            "-i",
            str(source),
            *build_tag_arguments(metadata),
            "-c:a",
            "copy",
            temp_name,
        ]
        subprocess.run(command, check=True)
        if not os.path.isfile(temp_name) or os.path.getsize(temp_name) == 0:
            raise RuntimeError("FFmpeg produced no tagged output")
        os.replace(temp_name, source)
        os.chmod(source, 0o664)
        return True
    except (OSError, subprocess.CalledProcessError, RuntimeError) as exc:
        try:
            os.unlink(temp_name)
        except FileNotFoundError:
            pass
        print(f"Error tagging {source}: {exc}", file=os.sys.stderr)
        return False
