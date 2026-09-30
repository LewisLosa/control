import os
import sys
import json
import urllib.request
import urllib.error

from ..common import required_env

SONARR_URL = os.environ.get("SONARR_URL", "http://127.0.0.1:8989/api/v3")
RADARR_URL = os.environ.get("RADARR_URL", "http://127.0.0.1:7878/api/v3")


def sonarr_headers(content_type=None):
    headers = {"X-Api-Key": required_env("SONARR_API_KEY")}
    if content_type:
        headers["Content-Type"] = content_type
    return headers


def radarr_headers(content_type=None):
    headers = {"X-Api-Key": required_env("RADARR_API_KEY")}
    if content_type:
        headers["Content-Type"] = content_type
    return headers

def auto_import_sonarr():
    try:
        req = urllib.request.Request(f"{SONARR_URL}/queue", headers=sonarr_headers())
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.load(resp)

        pending = [
            r for r in data.get("records", [])
            if r.get("status") == "completed" and r.get("trackedDownloadState") == "importPending"
        ]
        if not pending:
            return

        print(f"[arr-auto-import] Found {len(pending)} pending imports in Sonarr queue.")
        scan_req = urllib.request.Request(
            f"{SONARR_URL}/manualimport?folder=/nix/persist/media/downloads/tv-sonarr",
            headers=sonarr_headers()
        )
        with urllib.request.urlopen(scan_req, timeout=30) as resp:
            items = json.load(resp)

        import_files = []
        for it in items:
            series = it.get("series")
            episodes = it.get("episodes", [])
            rejections = it.get("rejections", [])
            if series and episodes and not rejections:
                import_files.append({
                    "path": it["path"],
                    "seriesId": series["id"],
                    "episodeIds": [e["id"] for e in episodes],
                    "quality": it["quality"],
                    "languages": it.get("languages", []),
                    "releaseGroup": it.get("releaseGroup"),
                    "indexerFlags": it.get("indexerFlags", 0)
                })

        if import_files:
            payload = {
                "name": "ManualImport",
                "importMode": "move",
                "files": import_files
            }
            cmd_req = urllib.request.Request(
                f"{SONARR_URL}/command",
                data=json.dumps(payload).encode("utf-8"),
                headers=sonarr_headers("application/json")
            )
            with urllib.request.urlopen(cmd_req, timeout=10) as resp:
                res = json.load(resp)
                print(f"[arr-auto-import] Triggered Sonarr ManualImport for {len(import_files)} files. Command ID: {res.get('id')}")
    except Exception as e:
        print(f"[arr-auto-import] Sonarr error: {e}", file=sys.stderr)

def auto_import_radarr():
    try:
        req = urllib.request.Request(f"{RADARR_URL}/queue", headers=radarr_headers())
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.load(resp)

        pending = [
            r for r in data.get("records", [])
            if r.get("status") == "completed" and r.get("trackedDownloadState") == "importPending"
        ]
        if not pending:
            return

        print(f"[arr-auto-import] Found {len(pending)} pending imports in Radarr queue.")
        scan_req = urllib.request.Request(
            f"{RADARR_URL}/manualimport?folder=/nix/persist/media/downloads/radarr",
            headers=radarr_headers()
        )
        with urllib.request.urlopen(scan_req, timeout=30) as resp:
            items = json.load(resp)

        import_files = []
        for it in items:
            movie = it.get("movie")
            rejections = it.get("rejections", [])
            if movie and not rejections:
                import_files.append({
                    "path": it["path"],
                    "movieId": movie["id"],
                    "quality": it["quality"],
                    "languages": it.get("languages", []),
                    "releaseGroup": it.get("releaseGroup"),
                    "indexerFlags": it.get("indexerFlags", 0)
                })

        if import_files:
            payload = {
                "name": "ManualImport",
                "importMode": "move",
                "files": import_files
            }
            cmd_req = urllib.request.Request(
                f"{RADARR_URL}/command",
                data=json.dumps(payload).encode("utf-8"),
                headers=radarr_headers("application/json")
            )
            with urllib.request.urlopen(cmd_req, timeout=10) as resp:
                res = json.load(resp)
                print(f"[arr-auto-import] Triggered Radarr ManualImport for {len(import_files)} files. Command ID: {res.get('id')}")
    except Exception as e:
        print(f"[arr-auto-import] Radarr error: {e}", file=sys.stderr)

def main():
    auto_import_sonarr()
    auto_import_radarr()

if __name__ == "__main__":
    main()
