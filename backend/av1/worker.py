import os
import sys
import json
import time
import signal
import sqlite3
import subprocess
import urllib.request
from pathlib import Path
from ..common import required_env
from .encoding import build_vaapi_command, probe_media

DB_PATH = "/var/lib/av1-queue/av1.db"
CURRENT_PATH = "/var/lib/av1-queue/current.json"
TMP_CURRENT_PATH = "/var/lib/av1-queue/current.json.tmp"
VA_DEVICE = "/dev/dri/renderD128"
JELLYFIN_URL = "http://127.0.0.1:8096"

os.umask(0o002)

stop_requested = False

def sig_handler(signum, frame):
    global stop_requested
    stop_requested = True

signal.signal(signal.SIGINT, sig_handler)
signal.signal(signal.SIGTERM, sig_handler)

def get_db():
    conn = sqlite3.connect(DB_PATH, timeout=30.0)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode = WAL;")
    return conn

def init_db():
    with get_db() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS queue (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                path TEXT UNIQUE NOT NULL,
                title TEXT NOT NULL,
                series_title TEXT,
                season_num INTEGER DEFAULT 0,
                episode_num INTEGER DEFAULT 0,
                status TEXT NOT NULL DEFAULT 'pending',
                res_label TEXT,
                orig_bytes INTEGER DEFAULT 0,
                new_bytes INTEGER DEFAULT 0,
                saved_bytes INTEGER DEFAULT 0,
                saved_pct REAL DEFAULT 0.0,
                encode_time_sec INTEGER DEFAULT 0,
                error_msg TEXT,
                added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                started_at TIMESTAMP,
                completed_at TIMESTAMP
            );
        """)
        cols = [r[1] for r in conn.execute("PRAGMA table_info(queue)").fetchall()]
        if "series_title" not in cols:
            conn.execute("ALTER TABLE queue ADD COLUMN series_title TEXT;")
        if "season_num" not in cols:
            conn.execute("ALTER TABLE queue ADD COLUMN season_num INTEGER DEFAULT 0;")
        if "episode_num" not in cols:
            conn.execute("ALTER TABLE queue ADD COLUMN episode_num INTEGER DEFAULT 0;")

        conn.execute("CREATE INDEX IF NOT EXISTS idx_queue_status ON queue(status);")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_queue_sort ON queue(status, series_title, season_num, episode_num);")

def write_current_status(data):
    try:
        with open(TMP_CURRENT_PATH, "w", encoding="utf-8") as f:
            json.dump(data, f)
        os.replace(TMP_CURRENT_PATH, CURRENT_PATH)
    except Exception as e:
        print(f"[av1-worker] Error writing status: {e}", file=sys.stderr)

def calculate_dynamic_bitrate(width, height, fps):
    pixels = width * height
    fps_val = max(fps, 1.0)
    pixel_rate_m = (pixels * fps_val) / 1_000_000.0

    # Continuous power curve calibrated for AV1 10-bit + CAS 0.25:
    # 720p 24fps (~22M pix/s) -> ~650k
    # 1080p Cinema (~37M pix/s) -> ~950k
    # 1080p 16:9 (~50M pix/s) -> ~1200k
    # 1440p 2K (~88M pix/s) -> ~1870k
    # 2160p 4K (~199M pix/s) -> ~3480k
    target_kbps = int(round(62.0 * (pixel_rate_m ** 0.76)))
    target_kbps = max(450, min(target_kbps, 6500))
    maxrate_kbps = int(round(target_kbps * 1.6))
    return target_kbps, maxrate_kbps

def trigger_jellyfin_refresh():
    try:
        url = f"{JELLYFIN_URL}/Library/Refresh?api_key={required_env('JELLYFIN_API_KEY')}"
        req = urllib.request.Request(url, method="POST")
        with urllib.request.urlopen(req, timeout=5) as resp:
            print(f"[av1-worker] Jellyfin refresh triggered: {resp.status}")
    except Exception as e:
        print(f"[av1-worker] Jellyfin refresh warning: {e}", file=sys.stderr)

def process_item(item):
    item_id = item["id"]
    file_path = item["path"]
    title = item["title"]

    if not os.path.isfile(file_path):
        with get_db() as conn:
            conn.execute("UPDATE queue SET status = 'failed', error_msg = 'File not found', completed_at = CURRENT_TIMESTAMP WHERE id = ?", (item_id,))
        return

    with get_db() as conn:
        conn.execute("UPDATE queue SET status = 'encoding', started_at = CURRENT_TIMESTAMP WHERE id = ?", (item_id,))

    media_info = probe_media(file_path)
    if not media_info or "streams" not in media_info:
        with get_db() as conn:
            conn.execute("UPDATE queue SET status = 'failed', error_msg = 'FFprobe failed to read file', completed_at = CURRENT_TIMESTAMP WHERE id = ?", (item_id,))
        return

    video_stream = next((s for s in media_info["streams"] if s.get("codec_type") == "video"), None)
    if not video_stream:
        with get_db() as conn:
            conn.execute("UPDATE queue SET status = 'failed', error_msg = 'No video stream found', completed_at = CURRENT_TIMESTAMP WHERE id = ?", (item_id,))
        return

    src_codec = video_stream.get("codec_name", "unknown")
    width = int(video_stream.get("width", 0))
    height = int(video_stream.get("height", 0))

    # Calculate FPS
    r_fps = video_stream.get("r_frame_rate", "24/1")
    try:
        num, den = r_fps.split("/")
        fps = float(num) / float(den) if float(den) > 0 else 24.0
    except Exception:
        fps = 24.0

    # Duration & sizes
    fmt = media_info.get("format", {})
    duration_sec = float(fmt.get("duration", 0) or 0)
    orig_bytes = int(fmt.get("size", 0) or os.path.getsize(file_path))
    src_bitrate = int(fmt.get("bit_rate", 0) or 0)
    src_kbps = src_bitrate // 1000

    # Resolution label
    if width >= 3800 or height >= 2100:
        res_label = "4K"
    elif width >= 2500 or height >= 1400:
        res_label = "2K (1440p)"
    elif width >= 1900 or height >= 800:
        res_label = "1080p"
    else:
        res_label = "720p"
    res_full_label = f"{res_label} ({width}x{height})"

    target_kbps, maxrate_kbps = calculate_dynamic_bitrate(width, height, fps)

    # Smart skip: If already AV1
    if src_codec.lower() == "av1":
        with get_db() as conn:
            conn.execute("""
                UPDATE queue SET status = 'skipped', res_label = ?, orig_bytes = ?, new_bytes = ?,
                saved_pct = 0.0, error_msg = 'Already AV1', completed_at = CURRENT_TIMESTAMP
                WHERE id = ?
            """, (res_full_label, orig_bytes, orig_bytes, item_id))
        print(f"[av1-worker] Skipped {title}: Already AV1")
        return

    # Smart skip: If source video bitrate is already lower than or equal to target
    if src_kbps > 0 and src_kbps <= (target_kbps + 100):
        with get_db() as conn:
            conn.execute("""
                UPDATE queue SET status = 'skipped', res_label = ?, orig_bytes = ?, new_bytes = ?,
                saved_pct = 0.0, error_msg = 'Source bitrate already lower than target', completed_at = CURRENT_TIMESTAMP
                WHERE id = ?
            """, (res_full_label, orig_bytes, orig_bytes, item_id))
        print(f"[av1-worker] Skipped {title}: Source bitrate ({src_kbps}k) already <= target ({target_kbps}k)")
        return

    dir_path = os.path.dirname(file_path)
    base_name = os.path.basename(file_path)
    temp_file = os.path.join(dir_path, f".{base_name}.av1.tmp.mkv")

    total_frames = int(duration_sec * fps) if duration_sec > 0 else 0
    start_time = time.time()

    status_data = {
        "status": "encoding",
        "id": item_id,
        "title": title,
        "path": file_path,
        "res_label": res_full_label,
        "resolution": f"{width}x{height}",
        "fps": round(fps, 2),
        "source_codec": src_codec,
        "target_kbps": target_kbps,
        "maxrate_kbps": maxrate_kbps,
        "orig_bytes": orig_bytes,
        "duration_sec": int(duration_sec),
        "total_frames": total_frames,
        "frame": 0,
        "progress_pct": 0.0,
        "current_fps": 0.0,
        "speed": 0.0,
        "eta_sec": 0,
        "elapsed_sec": 0,
        "started_at": int(start_time)
    }
    write_current_status(status_data)

    cmd = build_vaapi_command(
        file_path,
        temp_file,
        video_stream,
        target_kbps,
        maxrate_kbps,
        va_device=VA_DEVICE,
        progress=True,
    )

    print(f"[av1-worker] Starting encode: {title} ({res_full_label}) -> AV1 {target_kbps}k (Pure GPU Zero-Copy) + Opus 128k")
    proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)

    last_update = 0
    try:
        while True:
            if stop_requested:
                proc.terminate()
                break
            line = proc.stdout.readline()
            if not line:
                if proc.poll() is not None:
                    break
                continue
            line = line.strip()
            if "=" in line:
                k, v = line.split("=", 1)
                if k == "frame":
                    try:
                        status_data["frame"] = int(v)
                    except ValueError:
                        pass
                elif k == "fps":
                    try:
                        status_data["current_fps"] = float(v)
                    except ValueError:
                        pass
                elif k == "speed":
                    v_clean = v.replace("x", "").strip()
                    try:
                        status_data["speed"] = float(v_clean)
                    except ValueError:
                        pass
                elif k == "out_time_us":
                    try:
                        out_us = int(v)
                        if duration_sec > 0:
                            pct = (out_us / (duration_sec * 1_000_000)) * 100.0
                            status_data["progress_pct"] = min(99.9, round(pct, 1))
                            speed = status_data.get("speed", 0.0)
                            if speed > 0:
                                rem_us = max(0, (duration_sec * 1_000_000) - out_us)
                                status_data["eta_sec"] = int((rem_us / 1_000_000) / speed)
                    except ValueError:
                        pass

            now = time.time()
            if now - last_update >= 1.0:
                status_data["elapsed_sec"] = int(now - start_time)
                write_current_status(status_data)
                last_update = now

        retcode = proc.wait()
    except Exception as e:
        proc.kill()
        retcode = -1
        print(f"[av1-worker] FFmpeg error: {e}", file=sys.stderr)

    if stop_requested:
        if os.path.exists(temp_file):
            os.remove(temp_file)
        with get_db() as conn:
            conn.execute("UPDATE queue SET status = 'pending', started_at = NULL WHERE id = ?", (item_id,))
        write_current_status({"status": "idle"})
        return

    if retcode == 0 and os.path.isfile(temp_file) and os.path.getsize(temp_file) > 0:
        new_bytes = os.path.getsize(temp_file)
        saved_bytes = max(0, orig_bytes - new_bytes)
        saved_pct = round((saved_bytes / orig_bytes) * 100.0, 1) if orig_bytes > 0 else 0.0
        encode_time = int(time.time() - start_time)

        # Atomic replace
        os.remove(file_path)
        os.replace(temp_file, file_path)
        try:
            os.chmod(file_path, 0o664)
        except Exception:
            pass

        with get_db() as conn:
            conn.execute("""
                UPDATE queue SET status = 'completed', res_label = ?, orig_bytes = ?, new_bytes = ?,
                saved_bytes = ?, saved_pct = ?, encode_time_sec = ?, completed_at = CURRENT_TIMESTAMP
                WHERE id = ?
            """, (res_full_label, orig_bytes, new_bytes, saved_bytes, saved_pct, encode_time, item_id))

        print(f"[av1-worker] Finished: {title} | {orig_bytes//1024//1024}MB -> {new_bytes//1024//1024}MB (%{saved_pct} saved) in {encode_time}s")
        trigger_jellyfin_refresh()
    else:
        stderr_out = proc.stderr.read() if proc.stderr else "Unknown error"
        if os.path.exists(temp_file):
            os.remove(temp_file)
        with get_db() as conn:
            conn.execute("UPDATE queue SET status = 'failed', error_msg = ?, completed_at = CURRENT_TIMESTAMP WHERE id = ?", (stderr_out[:250], item_id))
        print(f"[av1-worker] Failed encode for {title}: {stderr_out}", file=sys.stderr)

    write_current_status({"status": "idle"})

def main():
    print("[av1-worker] Worker service starting...")
    required_env("JELLYFIN_API_KEY")
    init_db()
    write_current_status({"status": "idle"})

    # Reset leftover 'encoding' items from crashes
    with get_db() as conn:
        conn.execute("UPDATE queue SET status = 'pending', started_at = NULL WHERE status = 'encoding'")

    while not stop_requested:
        with get_db() as conn:
            cur = conn.execute("SELECT * FROM queue WHERE status = 'pending' ORDER BY series_title ASC, season_num ASC, episode_num ASC, id ASC LIMIT 1")
            item = cur.fetchone()

        if item:
            process_item(dict(item))
        else:
            time.sleep(2.0)

    write_current_status({"status": "idle"})
    print("[av1-worker] Worker service stopped.")

if __name__ == "__main__":
    main()
