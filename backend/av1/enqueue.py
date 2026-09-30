import os
import sys
import re
import sqlite3
from pathlib import Path

DB_PATH = "/var/lib/av1-queue/av1.db"

os.umask(0o002)

def parse_media_metadata(file_path):
    p = Path(file_path)
    filename = p.name
    parent = p.parent.name

    # 1. Season & Episode: S01E02, s2e05
    se_match = re.search(r'[Ss](\d+)[Ee](\d+)', filename)
    if se_match:
        season = int(se_match.group(1))
        episode = int(se_match.group(2))
        if re.match(r'^Season\s*\d+$', parent, re.IGNORECASE):
            series_title = p.parent.parent.name
        elif parent and parent.lower() not in ("shows", "media", "downloads"):
            series_title = parent
        else:
            series_title = filename[:se_match.start()].strip(" ._-").replace(".", " ")
        return series_title.strip().title(), season, episode

    # 2. Anime: Show - 01.mkv
    anime_match = re.search(r'-\s*(\d{1,3})(?:v\d)?(?:\.|\s|$)', filename)
    if anime_match:
        season = 1
        episode = int(anime_match.group(1))
        series_title = parent if (parent and parent.lower() not in ("shows", "media", "downloads")) else "Anime"
        return series_title.strip().title(), season, episode

    # 3. 1x02 pattern
    alt_match = re.search(r'(\d+)x(\d+)', filename)
    if alt_match:
        season = int(alt_match.group(1))
        episode = int(alt_match.group(2))
        series_title = parent if (parent and parent.lower() not in ("shows", "media", "downloads")) else "Series"
        return series_title.strip().title(), season, episode

    # Movie or generic
    series_title = parent if (parent and parent.lower() not in ("movies", "media", "downloads")) else filename
    return series_title.strip().title(), 9999, 9999

def get_db():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
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

def enqueue_targets(targets):
    init_db()
    video_exts = (".mkv", ".mp4", ".ts", ".avi", ".webm")
    files_to_add = []

    for t in targets:
        if os.path.isdir(t):
            for root, _, files in os.walk(t):
                for f in files:
                    if f.lower().endswith(video_exts):
                        files_to_add.append(os.path.join(root, f))
        elif os.path.isfile(t):
            if t.lower().endswith(video_exts):
                files_to_add.append(t)

    if not files_to_add:
        print("[av1-enqueue] No video files found to enqueue.")
        return 0

    added = 0
    with get_db() as conn:
        for f in files_to_add:
            title = os.path.basename(f)
            series_title, season_num, episode_num = parse_media_metadata(f)
            try:
                cur = conn.execute("""
                    INSERT OR IGNORE INTO queue (path, title, series_title, season_num, episode_num, status)
                    VALUES (?, ?, ?, ?, ?, 'pending')
                """, (f, title, series_title, season_num, episode_num))
                if cur.rowcount > 0:
                    order_tag = f"S{season_num:02d}E{episode_num:02d}" if season_num != 9999 else "Movie"
                    print(f"📥 [KUYRUĞA EKLENDİ] ({order_tag}) {title}")
                    added += 1
            except Exception as e:
                print(f"[av1-enqueue] Error inserting {title}: {e}", file=sys.stderr)

    return added

def main():
    if os.environ.get("sonarr_eventtype") == "Test" or os.environ.get("radarr_eventtype") == "Test":
        print("[av1-enqueue] Servarr test hook successful.")
        sys.exit(0)

    targets = []
    if "sonarr_episodefile_path" in os.environ:
        targets.append(os.environ["sonarr_episodefile_path"])
    elif "radarr_moviefile_path" in os.environ:
        targets.append(os.environ["radarr_moviefile_path"])
    else:
        targets.extend(sys.argv[1:])

    if not targets:
        print("Kullanım: av1-enqueue <dosya_veya_klasor>")
        sys.exit(1)

    enqueue_targets(targets)

if __name__ == "__main__":
    main()
