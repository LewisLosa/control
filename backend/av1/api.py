"""Local API for the Svelte AV1 dashboard."""

import json
import os
import sqlite3
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from urllib.parse import urlparse

from .enqueue import enqueue_targets, parse_media_metadata


DB_PATH = os.environ.get("AV1_DB_PATH", "/var/lib/av1-queue/av1.db")
HOST = os.environ.get("HOST", "127.0.0.1")
PORT = int(os.environ.get("PORT", "8095"))
API_PATHS = {"/api/status", "/api/enqueue"}


def _current_status() -> dict:
    path = Path(os.environ.get("AV1_CURRENT_PATH", "/var/lib/av1-queue/current.json"))
    if not path.exists():
        return {"status": "idle"}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {"status": "idle"}


def status_payload() -> dict:
    queue_items: list[dict] = []
    history_items: list[dict] = []
    stats = {
        "total_completed": 0,
        "total_orig_bytes": 0,
        "total_new_bytes": 0,
        "total_saved_bytes": 0,
        "total_saved_pct": 0.0,
    }

    if os.path.exists(DB_PATH):
        with sqlite3.connect(DB_PATH) as conn:
            conn.row_factory = sqlite3.Row
            queue_items = [
                dict(row)
                for row in conn.execute(
                    """
                    SELECT id, title, series_title, season_num, episode_num, path, added_at
                    FROM queue
                    WHERE status = 'pending'
                    ORDER BY series_title ASC, season_num ASC, episode_num ASC, id ASC
                    LIMIT 50
                    """
                )
            ]
            history_items = [
                dict(row)
                for row in conn.execute(
                    """
                    SELECT id, title, res_label, orig_bytes, new_bytes, saved_pct,
                           encode_time_sec, status, error_msg, completed_at
                    FROM queue
                    WHERE status IN ('completed', 'skipped', 'failed')
                    ORDER BY completed_at DESC
                    LIMIT 50
                    """
                )
            ]
            row = conn.execute(
                """
                SELECT COUNT(*) AS total_completed,
                       COALESCE(SUM(orig_bytes), 0) AS total_orig_bytes,
                       COALESCE(SUM(new_bytes), 0) AS total_new_bytes,
                       COALESCE(SUM(saved_bytes), 0) AS total_saved_bytes
                FROM queue
                WHERE status = 'completed'
                """
            ).fetchone()
            if row:
                stats.update(dict(row))
                if stats["total_orig_bytes"]:
                    stats["total_saved_pct"] = round(
                        stats["total_saved_bytes"] / stats["total_orig_bytes"] * 100, 1
                    )

    return {
        "current": _current_status(),
        "stats": stats,
        "queue": queue_items,
        "history": history_items,
    }


def enqueue_path(path: str) -> int:
    if not path or not os.path.exists(path):
        raise ValueError("Invalid or non-existent path")
    return enqueue_targets([path])


class Handler(BaseHTTPRequestHandler):
    def log_message(self, _format: str, *_args) -> None:
        return

    def _send_json(self, payload: dict, status: int = 200) -> None:
        body = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-cache")
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self) -> None:
        if urlparse(self.path).path == "/api/status":
            try:
                self._send_json(status_payload())
            except (OSError, sqlite3.Error) as exc:
                self._send_json({"ok": False, "error": str(exc)}, status=500)
            return
        self.send_error(404)

    def do_POST(self) -> None:
        if urlparse(self.path).path != "/api/enqueue":
            self.send_error(404)
            return
        try:
            length = int(self.headers.get("Content-Length", "0"))
            body = json.loads(self.rfile.read(length))
            added = enqueue_path(str(body.get("path", "")).strip())
        except (ValueError, json.JSONDecodeError, OSError, sqlite3.Error) as exc:
            self._send_json({"ok": False, "error": str(exc)}, status=400)
            return
        self._send_json({"ok": True, "added": added})


def main() -> None:
    server = HTTPServer((HOST, PORT), Handler)
    print(f"[av1-api] Listening on {HOST}:{PORT}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
