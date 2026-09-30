import json
import subprocess
from typing import Any


PROBE_FIELDS = ",".join(
    [
        "index",
        "codec_name",
        "codec_type",
        "width",
        "height",
        "pix_fmt",
        "bits_per_raw_sample",
        "profile",
        "color_range",
        "color_space",
        "color_primaries",
        "color_transfer",
        "color_trc",
        "color_primaries",
        "r_frame_rate",
        "bit_rate",
        "tags",
        "side_data_list",
    ]
)


def probe_media(file_path: str) -> dict[str, Any] | None:
    result = subprocess.run(
        [
            "ffprobe",
            "-v",
            "error",
            "-show_entries",
            f"stream={PROBE_FIELDS}:format=duration,size,bit_rate",
            "-of",
            "json",
            file_path,
        ],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        return None
    try:
        return json.loads(result.stdout)
    except json.JSONDecodeError:
        return None


def video_properties(stream: dict[str, Any]) -> dict[str, Any]:
    pix_fmt = (stream.get("pix_fmt") or "").lower()
    bits = int(stream.get("bits_per_raw_sample") or 0)
    if bits < 10 and any(marker in pix_fmt for marker in ("10", "12", "14", "16", "p010", "p016")):
        bits = 10 if "10" in pix_fmt or "p010" in pix_fmt else 12
    if bits < 8:
        bits = 8

    transfer = stream.get("color_transfer") or stream.get("color_trc") or ""
    primaries = stream.get("color_primaries") or ""
    side_data = stream.get("side_data_list") or []
    hdr = transfer in {"smpte2084", "arib-std-b67"} or (
        primaries == "bt2020" and bool(side_data)
    )
    hdr_mode = "pq" if transfer == "smpte2084" else "hlg" if transfer == "arib-std-b67" else None

    return {
        "pix_fmt": pix_fmt,
        "bit_depth": bits,
        "color_range": stream.get("color_range"),
        "color_space": stream.get("color_space"),
        "color_primaries": primaries,
        "color_transfer": transfer,
        "hdr": hdr,
        "hdr_mode": hdr_mode,
    }


def build_vaapi_command(
    input_path: str,
    output_path: str,
    stream: dict[str, Any],
    target_kbps: int,
    maxrate_kbps: int,
    va_device: str = "/dev/dri/renderD128",
    progress: bool = False,
) -> list[str]:
    properties = video_properties(stream)
    bit_depth = properties["bit_depth"]
    upload_format = "p010le" if bit_depth >= 10 else "nv12"
    command = [
        "ffmpeg",
        "-y",
        "-hide_banner",
        "-loglevel",
        "error",
        "-vaapi_device",
        va_device,
        "-i",
        input_path,
        "-map",
        "0:v:0",
        "-map",
        "0:a?",
        "-map",
        "0:s?",
        "-vf",
        f"format={upload_format},hwupload",
        "-c:v",
        "av1_vaapi",
        "-profile:v",
        "main",
        "-rc_mode",
        "VBR",
        "-b:v",
        f"{target_kbps}k",
        "-maxrate",
        f"{maxrate_kbps}k",
    ]
    ffmpeg_options = {
        "color_range": "-color_range",
        "color_primaries": "-color_primaries",
        "color_transfer": "-color_trc",
        "color_space": "-colorspace",
    }
    for option, ffmpeg_option in ffmpeg_options.items():
        value = properties.get(option)
        if value:
            command.extend([ffmpeg_option, value])
    if properties["hdr"]:
        command.extend(["-sei", "hdr"])
    command.extend(["-c:a", "libopus", "-b:a", "128k", "-ac", "2", "-c:s", "copy"])
    if progress:
        command.extend(["-progress", "pipe:1"])
    command.append(output_path)
    return command
