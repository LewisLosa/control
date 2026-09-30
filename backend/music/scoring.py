"""Intelligent Waterfall Decision Engine and Scoring Matrix (0 - 100 Quality Score).

Ranks candidates from Soulseek, Torrents, and YouTube Music to select the purest,
distortion-free audio while prioritizing exact title matches and penalizing
unwanted noise (remixes, covers, live concert boots, 1-hour loops).
"""

import re
from typing import List, Dict, Any, Optional

UNWANTED_TAGS = [
    "remix", "cover", "karaoke", "live", "canlı", "konser",
    "tribute", "parody", "parodi", "reaction", "tepki",
    "slowed", "reverb", "bass boosted", "nightcore", "instrumental",
    "enstrümantal", "guitar cover", "drum cover", "piano cover",
    "acoustic", "akustik", "sped up", "speed up", "1 hour", "1 saat",
    "loop", "mashup", "teaser", "snippet", "trailer"
]

VIDEO_CLUTTER_REGEX = re.compile(
    r"[\(\[\{][^\)\]\}]*(?:official\s*(?:video|audio|music\s*video|lyric\s*video|visualizer)?|lyrics?|video\s*klip|klip|hd|4k|remastered?|album\s*version|single\s*version)[^\)\]\}]*[\)\]\}]",
    re.IGNORECASE
)

LEADING_TRACK_NUM_REGEX = re.compile(r"^\d{1,4}[\s._-]+")


def normalize_text(text: str) -> str:
    """Cleans punctuation, clutter, and normalizes spacing for accurate comparison."""
    if not text:
        return ""
    # Strip leading track numbers
    text = LEADING_TRACK_NUM_REGEX.sub("", text)
    # Strip common video clutter brackets like (Official Video), [Audio], etc.
    text = VIDEO_CLUTTER_REGEX.sub("", text)
    # Lowercase & replace punctuation with space
    text = text.lower()
    text = re.sub(r"[^\w\s]", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def parse_query_intent(query: str) -> Dict[str, Any]:
    """Parses user query into artist and title components if formatted as 'Artist - Title'."""
    q = query.strip()
    for sep in (" - ", " – ", " — "):
        if sep in q:
            p1, p2 = q.split(sep, 1)
            return {
                "has_split": True,
                "part_a": p1.strip(),
                "part_b": p2.strip(),
                "raw": q,
            }
    return {
        "has_split": False,
        "part_a": "",
        "part_b": q,
        "raw": q,
    }


def calculate_relevance_score(item: Dict[str, Any], query: str) -> int:
    """Calculates 0 - 55 relevance score based on exact title match, artist match, and noise penalty."""
    if not query:
        return 25

    item_title = item.get("title") or ""
    item_artist = item.get("artist") or item.get("uploader") or item.get("channel") or ""
    raw_filename = item.get("filename") or ""

    norm_query = normalize_text(query)
    norm_title = normalize_text(item_title)
    norm_artist = normalize_text(item_artist)
    combined_haystack = f"{norm_artist} {norm_title} {raw_filename.lower()}".strip()

    # 1. Check for unwanted tags (remix, cover, live, karaoke, etc.)
    q_lower = query.lower()
    unwanted_found = False
    for tag in UNWANTED_TAGS:
        if tag in combined_haystack and tag not in q_lower:
            unwanted_found = True
            break

    intent = parse_query_intent(query)
    relevance = 0

    if intent["has_split"]:
        target_a = normalize_text(intent["part_a"])
        target_b = normalize_text(intent["part_b"])

        # Check orientation 1: part_a is artist, part_b is title
        match_a_artist = (target_a and (target_a in norm_artist or norm_artist in target_a))
        match_b_title = (target_b and (target_b == norm_title or target_b in norm_title))

        # Check orientation 2: part_a is title, part_b is artist
        match_a_title = (target_a and (target_a == norm_title or target_a in norm_title))
        match_b_artist = (target_b and (target_b in norm_artist or norm_artist in target_b))

        if (match_a_artist and match_b_title) or (match_a_title and match_b_artist):
            # Perfect Dual Match (Artist + Title)!
            matched_title = target_b if match_a_artist else target_a
            if norm_title == matched_title:
                relevance = 55  # 100% exact title & exact artist
            else:
                # Title contains extra words (e.g. remix or subtitle)
                extra_words = len(set(norm_title.split()) - set(matched_title.split()))
                relevance = max(25, 50 - (extra_words * 4))
        elif match_b_title or match_a_title:
            # Title matched, artist partial or missing
            matched_title = target_b if match_b_title else target_a
            if norm_title == matched_title:
                relevance = 45
            else:
                extra_words = len(set(norm_title.split()) - set(matched_title.split()))
                relevance = max(20, 40 - (extra_words * 4))
        elif match_a_artist or match_b_artist:
            # Only artist matched, title didn't match
            relevance = 10
        else:
            # Check token overlap
            q_tokens = [t for t in norm_query.split() if len(t) > 2]
            if q_tokens:
                title_matches = sum(1 for t in q_tokens if t in norm_title)
                ratio = title_matches / len(q_tokens)
                relevance = int(ratio * 30)
            else:
                relevance = 5
    else:
        # Single query (e.g. "Bu partide yalnızsın" or "lin pesto bu partide yalnızsın")
        # Check if item title matches query exactly
        # Note: If item title contains artist (e.g. "Lin Pesto - Bu Partide Yalnızsın"), strip artist
        stripped_title = norm_title
        if norm_artist and norm_artist in stripped_title:
            stripped_title = stripped_title.replace(norm_artist, "").strip()

        if norm_title == norm_query or stripped_title == norm_query:
            # Pure exact match: song name is exactly what user searched!
            relevance = 52
        elif norm_query in norm_title or norm_query in stripped_title:
            # Query is a substring of the title; penalize extra unnecessary words
            target_words = set(norm_query.split())
            title_words = set(stripped_title.split())
            extra_words = len(title_words - target_words)
            relevance = max(20, 48 - (extra_words * 4))
        else:
            # Check if query contains known artist
            if norm_artist and len(norm_artist) > 3 and norm_artist in norm_query:
                # User searched "Artist Title" without dash
                remaining_q = norm_query.replace(norm_artist, "").strip()
                if remaining_q and (remaining_q == norm_title or remaining_q == stripped_title):
                    relevance = 50
                elif remaining_q and remaining_q in norm_title:
                    relevance = 40
                else:
                    relevance = 15
            else:
                # Word-based overlap calculation
                q_tokens = [t for t in norm_query.split() if len(t) > 2]
                if q_tokens:
                    title_matches = sum(1 for t in q_tokens if t in norm_title)
                    ratio = title_matches / len(q_tokens)
                    relevance = int(ratio * 35)
                else:
                    relevance = 5

    # Apply heavy penalty if unwanted tags (remix, cover, live, etc.) are present
    if unwanted_found:
        relevance = max(0, relevance - 35)

    return min(55, relevance)


def calculate_quality_score(
    item: Dict[str, Any],
    query: Optional[str] = None,
    ref_duration: Optional[float] = None,
    prefer_album: bool = False,
) -> int:
    """Calculates a balanced 0 - 100 quality score for an audio candidate."""
    score = 0
    fmt = item.get("format_hint", "lossy").lower()
    bitrate = item.get("bitrate", 0)
    source = item.get("source", "")
    duration = item.get("duration", 0.0)
    filename = item.get("filename", "")

    # 1. Relevance Score (Max: 55 points) - Most decisive factor
    if query:
        relevance = calculate_relevance_score(item, query)
        score += relevance
    else:
        score += 35

    # 2. Format & Codec Fidelity (Max: 26 points)
    ext = item.get("extension", "")
    if fmt == "lossless" or ext in ("flac", "wav", "alac"):
        score += 26
    elif fmt == "opus_native" or (source == "youtube_music" and item.get("is_official")):
        score += 22  # Official clean digital master directly stream-copied
    elif bitrate >= 300 or (ext == "mp3" and bitrate >= 256):
        score += 18
    elif bitrate >= 192:
        score += 10
    else:
        score -= 30  # Low bitrate distortion

    # 3. Duration Accuracy (Max: 12 points) - Prevents concert bootlegs, intros, loops
    if ref_duration and ref_duration > 0 and duration > 0:
        diff = abs(duration - ref_duration)
        if diff <= 4.0:
            score += 12
        elif diff <= 9.0:
            score += 7
        elif diff <= 16.0:
            score += 2
        else:
            score -= 30  # Massive duration mismatch (teaser, concert clip, loop)
    elif 75 < duration < 500:
        score += 6

    # 4. Source Reliability & Transfer Viability (Max: 7 points)
    if source == "youtube_music":
        if item.get("is_official"):
            score += 7  # Guaranteed, instant transfer
        else:
            score += 3
    elif source == "soulseek":
        if item.get("is_locked"):
            score -= 30  # Locked private file will fail transfer!
        elif item.get("has_free_slot"):
            score += 7
        elif item.get("speed_kb", 0) > 1024:
            score += 5
        else:
            score += 2

        # Deprioritize private vault prefixes
        if filename.startswith("@@") or "\\@@" in filename or "/@@" in filename:
            score -= 10
    elif source in ("torrent", "prowlarr"):
        seeders = item.get("seeders", 0)
        if seeders >= 10:
            score += 7
        elif seeders >= 3:
            score += 4
        elif seeders == 0:
            score -= 25

    # 5. Context Preference (Album vs Single)
    clean_title_lower = (item.get("title") or "").lower()
    if prefer_album:
        if "album" in clean_title_lower or "discography" in clean_title_lower or item.get("size_mb", 0) > 100:
            score += 8
    else:
        if item.get("size_mb", 0) > 450 and source in ("torrent", "prowlarr"):
            score -= 15  # Avoid gigantic full discography when user just wants 1 track

    return max(0, min(100, score))


def rank_candidates(
    candidates: List[Dict[str, Any]],
    query: Optional[str] = None,
    ref_duration: Optional[float] = None,
    prefer_album: bool = False,
) -> List[Dict[str, Any]]:
    """Scores and sorts candidates in descending order of quality and reliability."""
    # Auto-detect reference duration from official YouTube Music track if not provided
    if not ref_duration and candidates:
        for c in candidates:
            if c.get("source") == "youtube_music" and c.get("is_official") and c.get("duration", 0) > 30:
                ref_duration = c["duration"]
                break

    for c in candidates:
        c["score"] = calculate_quality_score(
            c,
            query=query,
            ref_duration=ref_duration,
            prefer_album=prefer_album,
        )

    # Sort primarily by score, secondarily by size (larger lossless first)
    return sorted(candidates, key=lambda x: (x["score"], x.get("size_mb", 0)), reverse=True)


def select_best_candidate(
    candidates: List[Dict[str, Any]],
    query: Optional[str] = None,
    ref_duration: Optional[float] = None,
    min_score_threshold: int = 50,
) -> Optional[Dict[str, Any]]:
    """Selects the optimal candidate according to the waterfall algorithm."""
    ranked = rank_candidates(candidates, query=query, ref_duration=ref_duration)
    if not ranked:
        return None

    top = ranked[0]
    if top["score"] >= min_score_threshold:
        return top

    if top["score"] >= 30:
        return top
    return None
