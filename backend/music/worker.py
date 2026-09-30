"""Asynchronous Queue Worker and Ingestion Daemon for music processing.

Handles task execution:
1. Downloads candidate from selected source (Soulseek / Torrent / YouTube Music).
2. Runs acoustic processing pipeline (SOXR resample, true-peak limiter, Opus encoding, tagging).
3. Moves organized files into `/nix/persist/media/music/{Artist}/{Album}/`.
4. Triggers Navidrome library scan via HTTP API.
"""

import os
import sys
import time
import shutil
import sqlite3
import urllib.request
import urllib.parse
from pathlib import Path
from typing import Optional, Dict, Any
from ..common import required_env

from .pipeline import process_audio, tag_opus_file, probe_audio
from .sources import download_youtube_music


def result_status(current_status: str, output_path: str, error: Optional[str]) -> str:
    """Return the terminal status without turning cancellation into failure."""
    if current_status == "cancelled":
        return "cancelled"
    if error or not os.path.isfile(output_path) or os.path.getsize(output_path) == 0:
        return "failed"
    return "completed"

DB_PATH = os.environ.get("MUSIC_DB_PATH", "/var/lib/music-hub/music.db")
TEMP_DOWNLOAD_DIR = os.environ.get("MUSIC_TEMP_DIR", "/var/lib/music-hub/temp")
MUSIC_LIBRARY_DIR = os.environ.get("MUSIC_LIBRARY_DIR", "/nix/persist/media/music")
NAVIDROME_URL = os.environ.get("NAVIDROME_URL", "http://127.0.0.1:4533")
NAVIDROME_ADMIN_USER = os.environ.get("ND_ADMIN_USER", "admin")
NAVIDROME_ADMIN_TOKEN = os.environ.get("ND_ADMIN_TOKEN", "")
NAVIDROME_ADMIN_SALT = os.environ.get("ND_ADMIN_SALT", "")


def sanitize_filename(name: str) -> str:
    """Sanitizes directory/file names for filesystem safety while preserving UTF-8 Turkish chars."""
    return "".join(c for c in name if c not in r'\/:*?"<>|').strip(" .")


def init_db():
    """Initializes SQLite database schema for task management."""
    Path(DB_PATH).parent.mkdir(parents=True, exist_ok=True)
    Path(TEMP_DOWNLOAD_DIR).mkdir(parents=True, exist_ok=True)
    Path(MUSIC_LIBRARY_DIR).mkdir(parents=True, exist_ok=True)

    with sqlite3.connect(DB_PATH) as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS tasks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                query TEXT,
                artist TEXT,
                title TEXT,
                album TEXT,
                source TEXT,
                source_id TEXT,
                source_url TEXT,
                score INTEGER DEFAULT 0,
                status TEXT DEFAULT 'pending', -- pending, downloading, processing, completed, failed, cancelled
                progress INTEGER DEFAULT 0,
                file_path TEXT,
                error TEXT,
                keep_metadata INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        conn.commit()


def trigger_navidrome_scan():
    """Notifies Navidrome to scan the music folder for new additions."""
    try:
        url = f"{NAVIDROME_URL}/api/scan"
        req = urllib.request.Request(url, method="POST")
        with urllib.request.urlopen(req, timeout=3) as resp:
            print("Navidrome library scan triggered successfully.")
    except Exception as e:
        print(f"Navidrome scan notification notice: {e}")


def process_task(task_id: int):
    """Executes a single download, encode, and ingestion task."""
    with sqlite3.connect(DB_PATH) as conn:
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        cur.execute("SELECT * FROM tasks WHERE id = ?", (task_id,))
        task = cur.fetchone()

    if not task:
        return

    # Update status to downloading
    update_task_status(task_id, "downloading", progress=20)
    source = task["source"]
    artist = task["artist"] or "Unknown Artist"
    title = task["title"] or task["query"]
    album = task["album"] or "Singles"

    work_dir = os.path.join(TEMP_DOWNLOAD_DIR, str(task_id))
    os.makedirs(work_dir, exist_ok=True)

    try:
        download_result = None
        if source == "youtube_music":
            url = task["source_url"] or f"https://www.youtube.com/watch?v={task['source_id']}"
            download_result = download_youtube_music(url, work_dir)
        elif source == "soulseek":
            parts = (task["source_id"] or "").split(":", 2)
            username = ""
            size_bytes = 0
            remote_filename = ""

            if len(parts) == 3 and parts[1].isdigit():
                username = parts[0]
                size_bytes = int(parts[1])
                remote_filename = parts[2]
            elif len(parts) >= 2:
                username = parts[0]
                remote_filename = ":".join(parts[1:])
                size_bytes = 0

            if not username or not remote_filename:
                raise RuntimeError("Invalid Soulseek source_id specification")

            from .sources import enqueue_slskd_download, get_slskd_download_status, find_file_size_in_slskd, cancel_slskd_download, download_youtube_music_fallback
            import glob, re

            if size_bytes <= 0:
                size_bytes = find_file_size_in_slskd(username, remote_filename)

            if size_bytes <= 0:
                raise RuntimeError(f"Could not determine Soulseek file size for {remote_filename}")

            base_name = re.split(r"[\\/]", remote_filename)[-1]

            try:
                success = enqueue_slskd_download(username, remote_filename, size_bytes)
                if not success:
                    raise RuntimeError(f"Failed to enqueue download on slskd for {username}")

                # Poll slskd API and filesystem for progress and completion
                target_file = None
                last_progress = 20
                for iteration in range(150):  # Up to 5 minutes
                    time.sleep(2)

                    # Check if task was cancelled by user
                    with sqlite3.connect(DB_PATH) as conn:
                        cur = conn.cursor()
                        cur.execute("SELECT status FROM tasks WHERE id = ?", (task_id,))
                        c_row = cur.fetchone()
                        if c_row and c_row[0] == "cancelled":
                            cancel_slskd_download(username, remote_filename)
                            raise RuntimeError("Kullanıcı tarafından iptal edildi")

                    # Check slskd transfer status
                    status_info = get_slskd_download_status(username, remote_filename)
                    is_completed = False
                    if status_info:
                        state = status_info.get("state", "")
                        pct = status_info.get("percentComplete", 0)
                        if any(err_kw in state for err_kw in ("Rejected", "Aborted", "Errored", "Cancelled", "TimedOut")):
                            err_msg = status_info.get("exception") or state
                            raise RuntimeError(f"Soulseek indirmesi başarısız ({state}): {err_msg}")
                        if "Completed" in state and "Succeeded" not in state:
                            err_msg = status_info.get("exception") or state
                            raise RuntimeError(f"Soulseek transferi tamamlanamadı ({state}): {err_msg}")
                        if "Completed, Succeeded" in state or "Succeeded" in state:
                            is_completed = True

                        # Map slskd percent (0-100) to task progress range (20-60)
                        if pct > 0:
                            calc_prog = int(20 + (pct * 0.4))
                            if calc_prog > last_progress:
                                last_progress = calc_prog
                                update_task_status(task_id, "downloading", progress=last_progress)

                    # Check if file has finished downloading and moved out of .incomplete
                    matches = glob.glob(f"/nix/persist/media/downloads/slskd/**/{base_name}", recursive=True)
                    for m in matches:
                        if "/.incomplete/" not in m and os.path.exists(m) and (is_completed or os.path.getsize(m) >= size_bytes):
                            target_file = m
                            break
                    if target_file:
                        break

                if target_file:
                    download_result = {
                        "file_path": target_file,
                        "artist": artist,
                        "title": title,
                        "duration": 0,
                    }
                else:
                    raise RuntimeError(f"Soulseek indirmesi zaman aşımına uğradı ({base_name})")

            except Exception as slsk_err:
                err_text = str(slsk_err)
                if "iptal edildi" in err_text:
                    raise

                print(f"[worker] Soulseek download failed: {err_text}. Attempting seamless YouTube Music fallback...")
                fallback_query = f"{artist} - {title}" if artist and artist not in ("Various Artists", "Unknown Artist") else (title or task["query"])
                fallback_res = download_youtube_music_fallback(fallback_query, work_dir)
                if fallback_res and os.path.exists(fallback_res.get("file_path", "")):
                    download_result = fallback_res
                    print(f"[worker] Fallback succeeded with YouTube Music: {download_result.get('title')}")
                else:
                    raise slsk_err

        elif source in ("torrent", "prowlarr"):
            download_url = task["source_url"] or task["source_id"]
            if not download_url:
                raise RuntimeError("Torrent indirme bağlantısı bulunamadı")

            from .sources import add_torrent_to_transmission, get_torrent_status, remove_torrent_from_transmission
            import glob

            torrent_dir = os.path.join("/nix/persist/media/downloads", f"task_{task_id}")
            os.makedirs(torrent_dir, exist_ok=True)
            try:
                os.chmod(torrent_dir, 0o775)
            except Exception:
                pass

            try:
                torrent_id = add_torrent_to_transmission(download_url, torrent_dir)
                if not torrent_id:
                    from .sources import search_prowlarr
                    search_q = task.get("title") or task.get("query", "")
                    p_items = search_prowlarr(search_q, limit=5)
                    for p_it in p_items:
                        if p_it.get("download_url"):
                            torrent_id = add_torrent_to_transmission(p_it["download_url"], torrent_dir)
                            if torrent_id:
                                break

                if not torrent_id:
                    raise RuntimeError("Torrent Transmission kuyruğuna eklenemedi")

                print(f"Torrent {torrent_id} added to Transmission for task {task_id}")
                target_file = None

                try:
                    for iteration in range(180):  # Up to 6 minutes
                        time.sleep(2)

                        # Check user cancellation
                        with sqlite3.connect(DB_PATH) as conn:
                            cur = conn.cursor()
                            cur.execute("SELECT status FROM tasks WHERE id = ?", (task_id,))
                            c_row = cur.fetchone()
                            if c_row and c_row[0] == "cancelled":
                                remove_torrent_from_transmission(torrent_id, delete_local_data=True)
                                shutil.rmtree(torrent_dir, ignore_errors=True)
                                raise RuntimeError("Kullanıcı tarafından iptal edildi")

                        st = get_torrent_status(torrent_id)
                        if not st:
                            continue

                        pct_done = st.get("percentDone", 0.0)
                        progress_val = max(20, min(58, int(20 + pct_done * 38)))
                        update_task_status(task_id, "downloading", progress=progress_val)

                        if st.get("errorString"):
                            raise RuntimeError(f"Transmission torrent hatası: {st.get('errorString')}")

                        if pct_done >= 1.0 or st.get("isFinished"):
                            break

                    # Locate the audio file in torrent_dir and downloadDir
                    search_dirs = [torrent_dir]
                    if st and st.get("downloadDir") and st["downloadDir"] not in search_dirs:
                        search_dirs.append(st["downloadDir"])

                    audio_files = []
                    for s_dir in search_dirs:
                        for a_ext in ("*.flac", "*.wav", "*.mp3", "*.m4a", "*.opus"):
                            audio_files.extend(glob.glob(os.path.join(s_dir, "**", a_ext), recursive=True))

                    if audio_files:
                        audio_files.sort(key=lambda f: os.path.getsize(f), reverse=True)
                        target_file = audio_files[0]
                        download_result = {
                            "file_path": target_file,
                            "artist": artist,
                            "title": title,
                            "duration": 0,
                        }
                    else:
                        raise RuntimeError("Torrent indirildi ancak içinde ses dosyası bulunamadı")
                finally:
                    remove_torrent_from_transmission(torrent_id, delete_local_data=False)

            except Exception as tor_err:
                err_text = str(tor_err)
                if "iptal edildi" in err_text:
                    raise

                print(f"[worker] Torrent download failed: {err_text}. Attempting seamless YouTube Music fallback...")
                from .sources import download_youtube_music_fallback
                fallback_query = f"{artist} - {title}" if artist and artist not in ("Various Artists", "Unknown Artist") else (title or task["query"])
                fallback_res = download_youtube_music_fallback(fallback_query, work_dir)
                if fallback_res and os.path.exists(fallback_res.get("file_path", "")):
                    download_result = fallback_res
                    print(f"[worker] Fallback succeeded with YouTube Music: {download_result.get('title')}")
                else:
                    raise tor_err

        if not download_result or not os.path.exists(download_result.get("file_path", "")):
            raise RuntimeError(f"Download failed from source {source}")

        raw_file = download_result["file_path"]
        # Refine artist / title if extracted by downloader
        if download_result.get("artist"):
            artist = download_result["artist"]
        if download_result.get("title"):
            title = download_result["title"]

        update_task_status(task_id, "processing", progress=60)

        # Destination structure: /nix/persist/media/music/{Artist}/{Album}/{Track}.opus
        clean_artist = sanitize_filename(artist) or "Unknown Artist"
        clean_album = sanitize_filename(album) or "Singles"
        clean_title = sanitize_filename(title) or "Track"

        dest_dir = os.path.join(MUSIC_LIBRARY_DIR, clean_artist, clean_album)
        os.makedirs(dest_dir, exist_ok=True)

        dest_file = os.path.join(dest_dir, f"{clean_title}.opus")
        temp_encoded = os.path.join(work_dir, "processed.opus")

        # Process audio with studio quality (SOXR 48k + true-peak limiter + libopus)
        process_audio(raw_file, temp_encoded, target_codec="opus", target_bitrate="160k")
        if not os.path.isfile(temp_encoded) or os.path.getsize(temp_encoded) == 0:
            raise RuntimeError("Audio encoder produced no output")

        if not tag_opus_file(opus_file=temp_encoded, title=title, artist=artist, album=album):
            raise RuntimeError("Audio metadata rewrite failed")

        # Move to permanent library
        shutil.move(temp_encoded, dest_file)

        # Trigger Navidrome quick scan
        trigger_navidrome_scan()

        update_task_status(task_id, "completed", progress=100, file_path=dest_file)

    except Exception as e:
        sys.stderr.write(f"Task {task_id} failed: {e}\n")
        # Don't overwrite 'cancelled' status set by user
        with sqlite3.connect(DB_PATH) as _conn:
            _cur = _conn.cursor()
            _cur.execute("SELECT status FROM tasks WHERE id = ?", (task_id,))
            _row = _cur.fetchone()
        if not _row or _row[0] != "cancelled":
            update_task_status(task_id, "failed", error=str(e))
    finally:
        # Cleanup temporary files
        shutil.rmtree(work_dir, ignore_errors=True)
        torrent_dir = os.path.join("/nix/persist/media/downloads", f"task_{task_id}")
        if os.path.exists(torrent_dir):
            shutil.rmtree(torrent_dir, ignore_errors=True)


def update_task_status(
    task_id: int,
    status: str,
    progress: Optional[int] = None,
    file_path: Optional[str] = None,
    error: Optional[str] = None,
):
    """Updates task status in SQLite."""
    with sqlite3.connect(DB_PATH) as conn:
        updates = ["status = ?", "updated_at = CURRENT_TIMESTAMP"]
        params = [status]
        if progress is not None:
            updates.append("progress = ?")
            params.append(progress)
        if file_path is not None:
            updates.append("file_path = ?")
            params.append(file_path)
        if error is not None:
            updates.append("error = ?")
            params.append(error)
        params.append(task_id)

        sql = f"UPDATE tasks SET {', '.join(updates)} WHERE id = ?"
        conn.execute(sql, params)
        conn.commit()


def run_worker_loop():
    """Continuous worker daemon loop polling for pending tasks."""
    required_env("PROWLARR_API_KEY")
    init_db()
    print("Music Queue Worker started. Waiting for jobs...")
    while True:
        try:
            with sqlite3.connect(DB_PATH) as conn:
                cur = conn.cursor()
                cur.execute("SELECT id FROM tasks WHERE status = 'pending' ORDER BY id ASC LIMIT 1")
                row = cur.fetchone()

            if row:
                task_id = row[0]
                process_task(task_id)
            else:
                time.sleep(2)
        except Exception as e:
            print(f"Worker loop error: {e}")
            time.sleep(3)


if __name__ == "__main__":
    run_worker_loop()
