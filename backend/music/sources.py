"""Download source integrations: Soulseek (slskd), Torrents (Prowlarr), and YouTube Music (yt-dlp)."""

import os
import re
import json
import time
import urllib.parse
import urllib.request
import subprocess
from typing import List, Dict, Any, Optional

SLSKD_URL = os.environ.get("SLSKD_URL", "http://127.0.0.1:5030")
SLSKD_API_KEY = os.environ.get("SLSKD_API_KEY", "")
PROWLARR_URL = os.environ.get("PROWLARR_URL", "http://127.0.0.1:9696")
PROWLARR_API_KEY = os.environ.get("PROWLARR_API_KEY", "")
TRANSMISSION_URL = os.environ.get("TRANSMISSION_URL", "http://127.0.0.1:9091/transmission/rpc")


def search_youtube_music(query: str, limit: int = 6) -> List[Dict[str, Any]]:
    """Searches YouTube Music for official audio tracks using yt-dlp."""
    cmd = [
        "yt-dlp",
        "--dump-json",
        "--flat-playlist",
        "--default-search", f"ytsearch{limit}",
        f"{query} audio",
    ]
    results = []
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, check=True, timeout=8)
        for line in proc.stdout.strip().split("\n"):
            if not line:
                continue
            item = json.loads(line)
            title = item.get("title", "")
            duration = item.get("duration") or 0.0
            uploader = item.get("uploader") or item.get("channel") or ""
            video_id = item.get("id") or item.get("url")
            url = f"https://www.youtube.com/watch?v={video_id}" if video_id and not video_id.startswith("http") else video_id

            is_official = ("topic" in uploader.lower() or "vevo" in uploader.lower() or "official" in title.lower())

            results.append({
                "source": "youtube_music",
                "id": video_id,
                "title": title,
                "artist": uploader.replace(" - Topic", "").strip(),
                "duration": float(duration),
                "url": url,
                "thumbnail": item.get("thumbnail") or item.get("thumbnails", [{}])[-1].get("url", ""),
                "is_official": is_official,
                "format_hint": "opus_native",
                "bitrate": 140,
                "size_mb": round((float(duration) * 140 * 1024 / 8) / (1024 * 1024), 2) if duration else 0.0,
            })
    except Exception as e:
        print(f"YouTube search error: {e}")
    return results


def download_youtube_music(url: str, output_dir: str) -> Optional[Dict[str, Any]]:
    """Downloads audio without creating an artwork sidecar."""
    out_tmpl = os.path.join(output_dir, "%(title)s.%(ext)s")
    cmd = [
        "yt-dlp",
        "--extractor-args", "youtube:player_client=android,web",
        "--no-playlist",
        "-f", "ba[ext=opus]/ba/b",
        "--extract-audio",
        "--audio-format", "opus",
        "-o", out_tmpl,
        "--print-json",
        url,
    ]
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, check=True)
        for line in reversed(proc.stdout.strip().split("\n")):
            if line.startswith("{") and line.endswith("}"):
                data = json.loads(line)
                target_file = data.get("_filename")
                base, _ = os.path.splitext(target_file)
                actual_opus = f"{base}.opus"
                return {
                    "file_path": actual_opus if os.path.exists(actual_opus) else target_file,
                    "title": data.get("title", ""),
                    "artist": data.get("uploader", "").replace(" - Topic", "").strip(),
                    "duration": data.get("duration", 0),
                }
    except Exception as e:
        print(f"yt-dlp download error: {e}")
    return None


def initiate_slskd_search(query: str) -> Optional[str]:
    """Starts an asynchronous Soulseek search on slskd and returns search ID immediately."""
    if not SLSKD_URL:
        return None

    api_key = os.environ.get("SLSKD_API_KEY", SLSKD_API_KEY)
    headers = {"Content-Type": "application/json"}
    if api_key:
        headers["X-API-Key"] = api_key

    try:
        req_data = json.dumps({"searchText": query}).encode("utf-8")
        req = urllib.request.Request(f"{SLSKD_URL}/api/v0/searches", data=req_data, headers=headers, method="POST")
        with urllib.request.urlopen(req, timeout=3) as resp:
            search_obj = json.loads(resp.read().decode())
            return search_obj.get("id")
    except Exception as e:
        print(f"slskd initiate search error: {e}")
        return None


def get_slskd_search_status(search_id: str) -> Optional[Dict[str, Any]]:
    """Checks the status and completion of an ongoing slskd search."""
    if not SLSKD_URL or not search_id:
        return None

    api_key = os.environ.get("SLSKD_API_KEY", SLSKD_API_KEY)
    headers = {"Content-Type": "application/json"}
    if api_key:
        headers["X-API-Key"] = api_key

    try:
        req = urllib.request.Request(f"{SLSKD_URL}/api/v0/searches/{search_id}", headers=headers)
        with urllib.request.urlopen(req, timeout=3) as resp:
            return json.loads(resp.read().decode())
    except Exception as e:
        print(f"slskd get search status error: {e}")
        return None


def stop_slskd_search(search_id: str) -> bool:
    """Stops an ongoing slskd search and flushes all collected responses into the database."""
    if not SLSKD_URL or not search_id:
        return False

    api_key = os.environ.get("SLSKD_API_KEY", SLSKD_API_KEY)
    headers = {"Content-Type": "application/json"}
    if api_key:
        headers["X-API-Key"] = api_key

    try:
        req = urllib.request.Request(f"{SLSKD_URL}/api/v0/searches/{search_id}", headers=headers, method="PUT")
        with urllib.request.urlopen(req, timeout=3) as resp:
            return resp.status in (200, 204, 304)
    except Exception as e:
        print(f"slskd stop search error: {e}")
        return False


def parse_soulseek_filename(filename: str, query: Optional[str] = None):
    """Robust parser for Soulseek file paths with smart Artist - Title orientation resolution."""
    parts = [p for p in re.split(r"[\\/]", filename) if p]
    if not parts:
        return "Unknown Artist", "Unknown Track", "Singles"

    file_name = parts[-1]
    base_name, _ = os.path.splitext(file_name)

    # Strip leading track numbers like 01 -, 01. , 0128.
    clean_name = re.sub(r"^\d{1,4}[\s._-]+", "", base_name).strip()

    artist = ""
    title = ""
    album = ""

    # Check parent folder for Album and Artist
    if len(parts) >= 2:
        parent = parts[-2]
        # Clean folder names like (2011) Album or Artist - Album - Year
        if not artist and " - " in parent:
            parent_parts = parent.split(" - ")
            artist = parent_parts[0].strip()
            album = parent_parts[1].strip()
        else:
            album = parent

    if not artist and len(parts) >= 3:
        artist = parts[-3]

    if " - " in clean_name:
        p1, p2 = clean_name.split(" - ", 1)
        p1 = p1.strip()
        p2 = p2.strip()

        # Check orientation against user query
        # Handles cases like "Bu Partide Yalnızsın - Lin Pesto.mp3" vs "Lin Pesto - Bu Partide Yalnızsın.mp3"
        if query:
            q_clean = re.sub(r"[^\w\s]", " ", query.lower()).strip()
            p1_clean = re.sub(r"[^\w\s]", " ", p1.lower()).strip()
            p2_clean = re.sub(r"[^\w\s]", " ", p2.lower()).strip()

            if p1_clean in q_clean and p2_clean not in q_clean:
                # p1 matches query: it's the title, p2 is artist!
                title = p1
                artist = p2
            elif p2_clean in q_clean and p1_clean not in q_clean:
                artist = p1
                title = p2
            else:
                artist = p1
                title = p2
        else:
            artist = p1
            title = p2
    else:
        title = clean_name or base_name

    return (
        artist.strip() or "Various Artists",
        title.strip() or base_name,
        album.strip() or "Singles",
    )


def fetch_slskd_results(search_id: str, limit: int = 25, query: Optional[str] = None) -> List[Dict[str, Any]]:
    """Polls currently collected search responses for a search ID on slskd and ranks them."""
    if not SLSKD_URL or not search_id:
        return []

    api_key = os.environ.get("SLSKD_API_KEY", SLSKD_API_KEY)
    headers = {"Content-Type": "application/json"}
    if api_key:
        headers["X-API-Key"] = api_key

    q_tokens = [t for t in re.findall(r"\w+", (query or "").lower()) if len(t) > 2]
    candidates = []

    try:
        get_req = urllib.request.Request(f"{SLSKD_URL}/api/v0/searches/{search_id}/responses", headers=headers)
        with urllib.request.urlopen(get_req, timeout=10) as resp:
            responses = json.loads(resp.read().decode())

        for user_resp in responses:
            username = user_resp.get("username", "")
            has_free_upload = user_resp.get("hasFreeUploadSlot", False)
            upload_speed = user_resp.get("uploadSpeed", 0)
            queue_len = user_resp.get("queueLength", 0)

            for f in user_resp.get("files", []):
                # Filter out locked or unshared files immediately to prevent connection failures
                if f.get("isLocked", False):
                    continue

                filename = f.get("filename", "")
                ext = os.path.splitext(filename)[1].lower().strip(".")
                if ext not in ("flac", "wav", "mp3", "m4a", "opus"):
                    continue

                size_bytes = f.get("size", 0)
                bitrate = f.get("bitRate", 0)
                duration = f.get("length", 0)

                artist, title, album = parse_soulseek_filename(filename, query=query)
                title_lower = title.lower()
                combined_lower = f"{artist.lower()} {title_lower} {filename.lower()}"

                # Calculate preference score to avoid returning only the first user's files
                pref = 0
                if q_tokens:
                    matches = sum(1 for t in q_tokens if t in combined_lower)
                    match_ratio = matches / len(q_tokens)
                    if match_ratio >= 0.7:
                        pref += 100
                    elif match_ratio >= 0.4:
                        pref += 50
                    elif any(t in combined_lower for t in q_tokens):
                        pref += 20

                if ext in ("flac", "wav"):
                    pref += 40
                elif ext == "mp3" and bitrate >= 320:
                    pref += 20
                elif bitrate >= 256:
                    pref += 10

                if has_free_upload:
                    pref += 30
                elif queue_len > 80:
                    pref -= 25

                if upload_speed > 1024 * 512:
                    pref += 15

                # Deprioritize private vault directories
                if filename.startswith("@@") or "\\@@" in filename or "/@@" in filename:
                    pref -= 40

                candidates.append((pref, {
                    "source": "soulseek",
                    "id": f"{username}:{size_bytes}:{filename}",
                    "username": username,
                    "filename": filename,
                    "size_bytes": size_bytes,
                    "title": title,
                    "artist": artist,
                    "album": album,
                    "extension": ext,
                    "format_hint": "lossless" if ext in ("flac", "wav") else ext,
                    "bitrate": bitrate if bitrate else (800 if ext in ("flac", "wav") else 320),
                    "duration": float(duration),
                    "size_mb": round(size_bytes / (1024 * 1024), 2),
                    "has_free_slot": has_free_upload,
                    "speed_kb": round(upload_speed / 1024, 1),
                    "is_locked": False,
                }))

        # Sort all candidates by preference (highest quality & relevance first)
        candidates.sort(key=lambda x: x[0], reverse=True)
        return [c[1] for c in candidates[:limit]]
    except Exception as e:
        print(f"slskd fetch responses error: {e}")
        return []


def search_slskd(query: str, limit: int = 25, timeout: float = 6.0) -> List[Dict[str, Any]]:
    """Synchronously initiates and waits up to `timeout` seconds for Soulseek results."""
    search_id = initiate_slskd_search(query)
    if not search_id:
        return []

    start = time.time()
    while time.time() - start < timeout:
        time.sleep(0.6)
        st = get_slskd_search_status(search_id)
        if st and (st.get("isComplete") or st.get("fileCount", 0) >= 40):
            break

    stop_slskd_search(search_id)
    time.sleep(0.15)
    return fetch_slskd_results(search_id, limit=limit, query=query)


def enqueue_slskd_download(username: str, filename: str, size: int) -> bool:
    """Sends a download request to slskd for a specific user file."""
    api_key = os.environ.get("SLSKD_API_KEY", SLSKD_API_KEY)
    headers = {"Content-Type": "application/json"}
    if api_key:
        headers["X-API-Key"] = api_key

    payload = json.dumps([{"filename": filename, "size": size}]).encode("utf-8")
    try:
        url = f"{SLSKD_URL}/api/v0/transfers/downloads/{urllib.parse.quote(username)}"
        req = urllib.request.Request(url, data=payload, headers=headers, method="POST")
        with urllib.request.urlopen(req, timeout=5) as resp:
            return resp.status in (200, 201, 202)
    except Exception as e:
        print(f"slskd download enqueue error: {e}")
        return False


def get_slskd_download_status(username: str, filename: str) -> Optional[Dict[str, Any]]:
    """Fetches the current transfer status of a specific file from slskd."""
    api_key = os.environ.get("SLSKD_API_KEY", SLSKD_API_KEY)
    headers = {"Content-Type": "application/json"}
    if api_key:
        headers["X-API-Key"] = api_key

    try:
        url = f"{SLSKD_URL}/api/v0/transfers/downloads/{urllib.parse.quote(username)}"
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=4) as resp:
            data = json.loads(resp.read().decode())
            for d in data.get("directories", []):
                for f in d.get("files", []):
                    f_name = f.get("filename", "")
                    if f_name == filename or f_name.endswith(filename) or filename.endswith(f_name):
                        return f
    except Exception as e:
        print(f"slskd get transfer status error: {e}")
    return None


def cancel_slskd_download(username: str, filename: str = "") -> bool:
    """Cancels and removes a download transfer from slskd."""
    api_key = os.environ.get("SLSKD_API_KEY", SLSKD_API_KEY)
    headers = {"Content-Type": "application/json"}
    if api_key:
        headers["X-API-Key"] = api_key

    try:
        file_id = None
        if filename:
            status_info = get_slskd_download_status(username, filename)
            if status_info:
                file_id = status_info.get("id")

        url = f"{SLSKD_URL}/api/v0/transfers/downloads/{urllib.parse.quote(username)}"
        if file_id:
            url += f"/{file_id}"
        req = urllib.request.Request(url, headers=headers, method="DELETE")
        with urllib.request.urlopen(req, timeout=4) as resp:
            return resp.status in (200, 204)
    except Exception as e:
        print(f"slskd cancel transfer error: {e}")
        return False


def find_file_size_in_slskd(username: str, filename: str) -> int:
    """Finds the file size from recent slskd search responses."""
    api_key = os.environ.get("SLSKD_API_KEY", SLSKD_API_KEY)
    headers = {"Content-Type": "application/json"}
    if api_key:
        headers["X-API-Key"] = api_key

    try:
        req = urllib.request.Request(f"{SLSKD_URL}/api/v0/searches", headers=headers)
        with urllib.request.urlopen(req, timeout=4) as resp:
            searches = json.loads(resp.read().decode())

        for s in reversed(searches[-6:]):
            s_id = s.get("id")
            if not s_id:
                continue
            r_req = urllib.request.Request(f"{SLSKD_URL}/api/v0/searches/{s_id}/responses", headers=headers)
            with urllib.request.urlopen(r_req, timeout=4) as r_resp:
                responses = json.loads(r_resp.read().decode())
                for user_resp in responses:
                    if user_resp.get("username") == username:
                        for f in user_resp.get("files", []):
                            f_name = f.get("filename", "")
                            if f_name == filename or f_name.endswith(filename) or filename.endswith(f_name):
                                return int(f.get("size", 0))
    except Exception as e:
        print(f"Error looking up file size in slskd: {e}")
    return 0


def search_prowlarr(query: str, limit: int = 10) -> List[Dict[str, Any]]:
    """Searches music indexers via Prowlarr."""
    api_key = os.environ.get("PROWLARR_API_KEY", PROWLARR_API_KEY)
    if not PROWLARR_URL or not api_key:
        return []

    # Send categories as repeated query params for ASP.NET Core compatibility
    params = urllib.parse.urlencode([
        ("query", query),
        ("type", "search"),
        ("categories", "3000"),
        ("categories", "3010"),
        ("categories", "3020"),
        ("categories", "3030"),
        ("categories", "3040"),
    ])
    headers = {"X-Api-Key": api_key, "Accept": "application/json"}
    results = []
    try:
        url = f"{PROWLARR_URL}/api/v1/search?{params}"
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=6) as resp:
            items = json.loads(resp.read().decode())

        if not isinstance(items, list):
            return []

        for item in items[:limit]:
            title = item.get("title", "")
            size = item.get("size", 0)
            seeders = item.get("seeders", 0)
            download_url = item.get("downloadUrl") or item.get("magnetUrl")
            indexer = item.get("indexer", "")

            if not download_url or seeders <= 0:
                continue

            is_flac = any(kw in title.lower() for kw in ("flac", "lossless", "24bit", "96khz", "24-96", "flac 24"))
            results.append({
                "source": "torrent",  # Matches frontend chip & queue source
                "id": download_url,
                "url": download_url,
                "download_url": download_url,
                "title": title,
                "artist": "",
                "album": "",
                "indexer": indexer,
                "seeders": seeders,
                "format_hint": "lossless" if is_flac else "lossy",
                "bitrate": 800 if is_flac else 320,
                "size_mb": round(size / (1024 * 1024), 2),
            })
    except Exception as e:
        print(f"Prowlarr search error: {e}")
    return results


def call_transmission_rpc(method: str, arguments: Optional[Dict[str, Any]] = None) -> Optional[Dict[str, Any]]:
    """Executes a JSON-RPC request to Transmission daemon with automatic CSRF token management."""
    transmission_url = os.environ.get("TRANSMISSION_URL", TRANSMISSION_URL)
    payload = json.dumps({"method": method, "arguments": arguments or {}}).encode("utf-8")
    headers = {"Content-Type": "application/json"}

    session_id = getattr(call_transmission_rpc, "_session_id", None)
    if session_id:
        headers["X-Transmission-Session-Id"] = session_id

    req = urllib.request.Request(transmission_url, data=payload, headers=headers, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=5) as resp:
            return json.loads(resp.read().decode())
    except urllib.error.HTTPError as e:
        if e.code == 409:
            new_token = e.headers.get("X-Transmission-Session-Id")
            if new_token:
                call_transmission_rpc._session_id = new_token
                headers["X-Transmission-Session-Id"] = new_token
                req2 = urllib.request.Request(transmission_url, data=payload, headers=headers, method="POST")
                with urllib.request.urlopen(req2, timeout=5) as resp2:
                    return json.loads(resp2.read().decode())
        print(f"Transmission RPC HTTP error: {e}")
    except Exception as e:
        print(f"Transmission RPC error: {e}")
    return None


def add_torrent_to_transmission(download_url_or_magnet: str, download_dir: str) -> Optional[int]:
    """Adds a torrent, magnet link, or Prowlarr download URL to Transmission and returns its ID."""
    import base64

    target = (download_url_or_magnet or "").strip()
    if not target:
        return None

    def _extract_id(rpc_res):
        if rpc_res and rpc_res.get("result") == "success":
            args = rpc_res.get("arguments", {})
            t_info = args.get("torrent-added") or args.get("torrent-duplicate")
            if t_info:
                return t_info.get("id")
        return None

    # 1. Direct Magnet Link
    if target.startswith("magnet:"):
        res = call_transmission_rpc("torrent-add", {
            "filename": target,
            "download-dir": download_dir,
        })
        return _extract_id(res)

    # 2. Local .torrent File
    if os.path.exists(target) and target.endswith(".torrent"):
        try:
            with open(target, "rb") as f:
                b64 = base64.b64encode(f.read()).decode("utf-8")
            res = call_transmission_rpc("torrent-add", {
                "metainfo": b64,
                "download-dir": download_dir,
            })
            return _extract_id(res)
        except Exception as e:
            print(f"Error reading local torrent file: {e}")

    # 3. HTTP / HTTPS Link (Prowlarr downloadUrl or indexer page)
    if target.startswith("http://") or target.startswith("https://"):
        # If it's an HTML page URL (like .html from Limetorrents) and not /download, resolve via Prowlarr
        if ("/download" not in target) and (".html" in target or "torrent" in target):
            try:
                url_slug = target.rstrip("/").split("/")[-1].replace(".html", "")
                url_slug = re.sub(r"-torrent-\d+$", "", url_slug)
                search_term = re.sub(r"[-_.]+", " ", url_slug).strip()
                if search_term:
                    prow_items = search_prowlarr(search_term, limit=10)
                    for p_it in prow_items:
                        if p_it.get("download_url") and ("/download" in p_it["download_url"]):
                            target = p_it["download_url"]
                            break
            except Exception as e:
                print(f"Error resolving HTML infoUrl to downloadUrl: {e}")

        # Fetch URL, catching 301/302 redirects to magnet: or reading bencoded .torrent data
        class NoRedirectHandler(urllib.request.HTTPRedirectHandler):
            def redirect_request(self, req, fp, code, msg, headers, newurl):
                if newurl.startswith("magnet:"):
                    return None
                return super().redirect_request(req, fp, code, msg, headers, newurl)

        opener = urllib.request.build_opener(NoRedirectHandler)
        try:
            req = urllib.request.Request(target, headers={"User-Agent": "Transmission/4.1.3"})
            with opener.open(req, timeout=12) as resp:
                data = resp.read()
                if data.startswith(b"d8:") or b"announce" in data[:100]:
                    b64 = base64.b64encode(data).decode("utf-8")
                    res = call_transmission_rpc("torrent-add", {
                        "metainfo": b64,
                        "download-dir": download_dir,
                    })
                    return _extract_id(res)
        except urllib.error.HTTPError as e:
            loc = e.headers.get("Location")
            if loc and loc.startswith("magnet:"):
                res = call_transmission_rpc("torrent-add", {
                    "filename": loc,
                    "download-dir": download_dir,
                })
                return _extract_id(res)
        except Exception as e:
            err_str = str(e)
            if "magnet:?" in err_str:
                m = re.search(r"magnet:\?[^\s'\"]+", err_str)
                if m:
                    res = call_transmission_rpc("torrent-add", {
                        "filename": m.group(0),
                        "download-dir": download_dir,
                    })
                    return _extract_id(res)
            print(f"Error resolving torrent redirect: {e}")

        # Fallback: pass URL directly to Transmission
        res = call_transmission_rpc("torrent-add", {
            "filename": target,
            "download-dir": download_dir,
        })
        return _extract_id(res)

    return None


def get_torrent_status(torrent_id: int) -> Optional[Dict[str, Any]]:
    """Polls progress, speed, status, and error details of a torrent in Transmission."""
    res = call_transmission_rpc("torrent-get", {
        "ids": [torrent_id],
        "fields": ["id", "name", "percentDone", "metadataPercentComplete", "status", "rateDownload", "errorString", "isFinished", "files", "downloadDir"],
    })
    if res and res.get("result") == "success":
        torrents = res.get("arguments", {}).get("torrents", [])
        if torrents:
            return torrents[0]
    return None


def remove_torrent_from_transmission(torrent_id: int, delete_local_data: bool = False) -> bool:
    """Removes a torrent from Transmission (optionally deleting files if cancelled)."""
    res = call_transmission_rpc("torrent-remove", {
        "ids": [torrent_id],
        "delete-local-data": delete_local_data,
    })
    return bool(res and res.get("result") == "success")


def download_youtube_music_fallback(query: str, output_dir: str) -> Optional[Dict[str, Any]]:
    """Searches YouTube Music and downloads the top official audio track as a seamless fallback."""
    try:
        candidates = search_youtube_music(query, limit=3)
        if not candidates:
            return None
        # Prefer official track first
        candidates.sort(key=lambda x: (x.get("is_official", False), -abs(x.get("duration", 0) - 200)), reverse=True)
        top = candidates[0]
        url = top.get("url")
        if not url:
            return None
        print(f"[fallback] Downloading YouTube Music fallback: {top.get('title')} ({url})")
        return download_youtube_music(url, output_dir)
    except Exception as e:
        print(f"[fallback] YouTube Music fallback error: {e}")
        return None
