import os
import sys
import re
import json
import sqlite3
from pathlib import Path
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import parse_qs, urlparse

DB_PATH = "/var/lib/av1-queue/av1.db"
CURRENT_PATH = "/var/lib/av1-queue/current.json"
ASSETS_DIR = os.environ.get("AV1_ASSETS_DIR", "/var/lib/av1-queue/assets")
PORT = 8095

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

HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>encode • sengozhome</title>
  <style>
    :root {
      --bg: #0c0d10;
      --card: #13141a;
      --card-hover: #171821;
      --card-inner: #191b24;
      --border: rgba(255, 255, 255, 0.08);
      --border-subtle: rgba(255, 255, 255, 0.04);
      --border-hover: rgba(255, 255, 255, 0.16);
      --text: #f3f4f6;
      --text-muted: #9ca3af;
      --text-dim: #646a78;
      --accent: #e2e8f0;
      --accent-badge: rgba(255, 255, 255, 0.07);
      --emerald: #10b981;
      --emerald-glow: rgba(16, 185, 129, 0.15);
      --kita-pink: #f43f5e;
      --font-mono: ui-monospace, "SF Mono", "Geist Mono", "JetBrains Mono", Menlo, Consolas, monospace;
      --font-sans: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Inter", sans-serif;
      --radius-xl: 20px;
      --radius-lg: 14px;
      --radius-md: 10px;
      --radius-full: 9999px;
    }
    * { box-sizing: border-box; margin: 0; padding: 0; }
    body {
      background-color: var(--bg);
      color: var(--text);
      font-family: var(--font-sans);
      font-size: 13px;
      line-height: 1.5;
      -webkit-font-smoothing: antialiased;
      display: flex;
      justify-content: center;
      padding: 2.5rem 1rem 4rem 1rem;
      min-height: 100vh;
    }
    .container {
      width: 100%;
      max-width: 640px;
      display: flex;
      flex-direction: column;
      gap: 1.5rem;
    }

    /* Header - Cobalt.tools minimalist style */
    header {
      display: flex;
      align-items: center;
      justify-content: space-between;
      border-bottom: 1px solid var(--border-subtle);
      padding-bottom: 1rem;
    }
    .brand {
      display: flex;
      align-items: baseline;
      gap: 0.6rem;
    }
    .brand h1 {
      font-size: 18px;
      font-weight: 700;
      letter-spacing: -0.025em;
      color: var(--text);
    }
    .brand .domain-pill {
      font-size: 11px;
      font-family: var(--font-mono);
      color: var(--text-dim);
      background: rgba(255, 255, 255, 0.03);
      padding: 2px 8px;
      border-radius: var(--radius-full);
      border: 1px solid var(--border-subtle);
    }
    .status-pill {
      display: flex;
      align-items: center;
      gap: 6px;
      padding: 4px 12px;
      border-radius: var(--radius-full);
      font-size: 11px;
      font-family: var(--font-mono);
      font-weight: 500;
      border: 1px solid var(--border);
      background: var(--card-inner);
      transition: all 0.2s ease;
    }
    .status-pill .dot {
      width: 6px;
      height: 6px;
      border-radius: 50%;
    }
    .status-pill.idle {
      color: var(--text-muted);
    }
    .status-pill.idle .dot {
      background: #71717a;
    }
    .status-pill.active {
      color: #34d399;
      border-color: rgba(52, 211, 153, 0.3);
      background: rgba(16, 185, 129, 0.06);
    }
    .status-pill.active .dot {
      background: #34d399;
      box-shadow: 0 0 8px #34d399;
      animation: pulse 1.6s infinite ease-in-out;
    }
    @keyframes pulse {
      0%, 100% { opacity: 1; transform: scale(1); }
      50% { opacity: 0.4; transform: scale(0.85); }
    }

    /* Stats Grid - Monochrome cards */
    .stats-grid {
      display: grid;
      grid-template-columns: repeat(3, 1fr);
      gap: 0.75rem;
    }
    .stat-card {
      background: var(--card);
      border: 1px solid var(--border);
      border-radius: var(--radius-lg);
      padding: 0.9rem 1rem;
      display: flex;
      flex-direction: column;
      gap: 0.35rem;
      transition: border-color 0.2s;
    }
    .stat-card:hover {
      border-color: var(--border-hover);
    }
    .stat-label {
      font-size: 11px;
      font-weight: 500;
      color: var(--text-dim);
      text-transform: uppercase;
      letter-spacing: 0.05em;
    }
    .stat-value {
      font-size: 16px;
      font-weight: 600;
      font-family: var(--font-mono);
      letter-spacing: -0.02em;
      color: var(--text);
      display: flex;
      align-items: baseline;
      gap: 4px;
    }
    .stat-sub {
      font-size: 11px;
      color: var(--emerald);
      font-weight: 500;
    }

    /* Main Card */
    .card {
      background: var(--card);
      border: 1px solid var(--border);
      border-radius: var(--radius-xl);
      padding: 1.35rem;
      display: flex;
      flex-direction: column;
      gap: 1.15rem;
      box-shadow: 0 12px 40px rgba(0, 0, 0, 0.45);
      position: relative;
      overflow: hidden;
    }

    /* Anime Mascot Styling - Idle State (Kita Ikuyo) */
    .idle-mascot-box {
      display: flex;
      flex-direction: column;
      align-items: center;
      justify-content: center;
      padding: 1.25rem 1rem;
      text-align: center;
      gap: 0.75rem;
    }
    .mascot-img-wrap {
      position: relative;
      width: 140px;
      height: 190px;
      display: flex;
      align-items: center;
      justify-content: center;
    }
    .anime-mascot {
      width: 100%;
      height: 100%;
      object-fit: contain;
      filter: drop-shadow(0 10px 20px rgba(0, 0, 0, 0.6));
      animation: gentleFloat 4s ease-in-out infinite;
    }
    @keyframes gentleFloat {
      0%, 100% { transform: translateY(0); }
      50% { transform: translateY(-7px); }
    }
    .idle-title {
      font-size: 15px;
      font-weight: 600;
      color: var(--text);
      letter-spacing: -0.01em;
      display: flex;
      align-items: center;
      gap: 6px;
    }
    .idle-subtitle {
      font-size: 12px;
      color: var(--text-dim);
      max-width: 380px;
      line-height: 1.45;
    }
    .idle-badge {
      display: inline-flex;
      align-items: center;
      gap: 5px;
      background: rgba(244, 63, 94, 0.08);
      border: 1px solid rgba(244, 63, 94, 0.2);
      color: #fda4af;
      font-size: 11px;
      font-family: var(--font-mono);
      padding: 3px 10px;
      border-radius: var(--radius-full);
    }

    /* Active Encoding State */
    .active-header-row {
      display: flex;
      align-items: flex-start;
      justify-content: space-between;
      gap: 1rem;
    }
    .active-header-main {
      flex: 1;
      display: flex;
      flex-direction: column;
      gap: 0.5rem;
    }
    .card-title {
      font-size: 14px;
      font-weight: 600;
      letter-spacing: -0.015em;
      line-height: 1.4;
      word-break: break-all;
      color: #fafafa;
    }
    .bocchi-companion {
      flex-shrink: 0;
      width: 70px;
      height: 110px;
      position: relative;
      display: flex;
      flex-direction: column;
      align-items: center;
    }
    .bocchi-img {
      width: 100%;
      height: 100%;
      object-fit: contain;
      filter: drop-shadow(0 8px 16px rgba(0, 0, 0, 0.5));
      animation: breatheAnim 3s ease-in-out infinite;
    }
    @keyframes breatheAnim {
      0%, 100% { transform: scale(1); }
      50% { transform: scale(1.03) translateY(-2px); }
    }
    .mascot-speech {
      position: absolute;
      top: -12px;
      right: -10px;
      background: #1e1f29;
      border: 1px solid var(--border);
      color: #f472b6;
      font-size: 9px;
      font-family: var(--font-mono);
      font-weight: 600;
      padding: 1px 6px;
      border-radius: var(--radius-full);
      white-space: nowrap;
      box-shadow: 0 4px 10px rgba(0,0,0,0.4);
    }

    .badges {
      display: flex;
      flex-wrap: wrap;
      gap: 0.4rem;
      margin-top: 0.25rem;
    }
    .badge {
      font-size: 11px;
      font-family: var(--font-mono);
      padding: 3px 9px;
      border-radius: var(--radius-md);
      background: var(--card-inner);
      border: 1px solid var(--border);
      color: var(--text-muted);
    }
    .badge.highlight {
      color: var(--text);
      background: rgba(255, 255, 255, 0.05);
      border-color: var(--border-hover);
    }
    .badge.green {
      color: #34d399;
      background: rgba(16, 185, 129, 0.08);
      border-color: rgba(52, 211, 153, 0.25);
    }

    /* Progress bar */
    .progress-track {
      width: 100%;
      height: 8px;
      background: var(--card-inner);
      border: 1px solid var(--border-subtle);
      border-radius: var(--radius-full);
      overflow: hidden;
      margin-top: 0.25rem;
    }
    .progress-fill {
      height: 100%;
      background: linear-gradient(90deg, #10b981, #34d399);
      border-radius: var(--radius-full);
      transition: width 0.3s ease;
      box-shadow: 0 0 10px rgba(52, 211, 153, 0.4);
    }
    .progress-labels {
      display: flex;
      justify-content: space-between;
      font-size: 11px;
      font-family: var(--font-mono);
      color: var(--text-dim);
    }

    /* Technical details */
    details {
      border: 1px solid var(--border-subtle);
      border-radius: var(--radius-md);
      padding: 0.5rem 0.85rem;
      background: rgba(255, 255, 255, 0.015);
      transition: border-color 0.2s;
    }
    details[open] {
      border-color: var(--border);
      background: var(--card-inner);
    }
    summary {
      font-size: 11px;
      font-weight: 500;
      color: var(--text-dim);
      cursor: pointer;
      user-select: none;
    }
    summary:hover {
      color: var(--text-muted);
    }
    .details-table {
      width: 100%;
      margin-top: 0.6rem;
      border-collapse: collapse;
      font-family: var(--font-mono);
      font-size: 11px;
    }
    .details-table td {
      padding: 3px 0;
      color: var(--text-muted);
    }
    .details-table td:first-child {
      color: var(--text-dim);
      width: 90px;
    }

    /* Enqueue input bar - Cobalt.tools style */
    .enqueue-box {
      display: flex;
      gap: 0.5rem;
      margin-top: 0.4rem;
      padding-top: 0.85rem;
      border-top: 1px solid var(--border-subtle);
    }
    .enqueue-input {
      flex: 1;
      background: var(--card-inner);
      border: 1px solid var(--border);
      border-radius: var(--radius-md);
      padding: 8px 12px;
      color: var(--text);
      font-family: var(--font-mono);
      font-size: 11px;
      outline: none;
      transition: all 0.2s ease;
    }
    .enqueue-input:focus {
      border-color: var(--border-hover);
      background: #1d1f2b;
    }
    .enqueue-input::placeholder {
      color: var(--text-dim);
    }
    .enqueue-btn {
      background: var(--card-inner);
      border: 1px solid var(--border);
      color: var(--text);
      font-size: 12px;
      font-weight: 500;
      padding: 8px 16px;
      border-radius: var(--radius-md);
      cursor: pointer;
      transition: all 0.2s ease;
      white-space: nowrap;
    }
    .enqueue-btn:hover {
      background: rgba(255, 255, 255, 0.08);
      border-color: var(--border-hover);
    }

    /* Section Headers */
    .section-header {
      display: flex;
      align-items: center;
      justify-content: space-between;
      margin-bottom: 0.65rem;
      padding: 0 0.25rem;
    }
    .section-header span:first-child {
      font-size: 12px;
      font-weight: 600;
      text-transform: uppercase;
      letter-spacing: 0.05em;
      color: var(--text-dim);
    }
    .count-badge {
      font-size: 11px;
      font-family: var(--font-mono);
      color: var(--text-dim);
      background: rgba(255, 255, 255, 0.03);
      border: 1px solid var(--border-subtle);
      padding: 2px 7px;
      border-radius: var(--radius-full);
    }

    /* Lists */
    .list {
      display: flex;
      flex-direction: column;
      gap: 0.45rem;
    }
    .list-item {
      background: var(--card);
      border: 1px solid var(--border);
      border-radius: var(--radius-lg);
      padding: 0.75rem 1rem;
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 0.85rem;
      transition: border-color 0.2s, background-color 0.2s;
    }
    .list-item:hover {
      border-color: var(--border-hover);
      background-color: var(--card-hover);
    }
    .list-item-title {
      font-size: 12px;
      font-weight: 500;
      color: var(--text);
      white-space: nowrap;
      overflow: hidden;
      text-overflow: ellipsis;
      flex: 1;
    }
    .list-item-meta {
      display: flex;
      align-items: center;
      gap: 0.5rem;
      font-size: 11px;
      font-family: var(--font-mono);
      color: var(--text-dim);
      flex-shrink: 0;
    }
    .savings-pill {
      background: rgba(16, 185, 129, 0.08);
      border: 1px solid rgba(52, 211, 153, 0.25);
      color: #34d399;
      font-size: 10px;
      font-weight: 600;
      padding: 1px 6px;
      border-radius: 4px;
    }
    .skipped-pill {
      background: rgba(255, 255, 255, 0.04);
      border: 1px solid var(--border-subtle);
      color: var(--text-dim);
      font-size: 10px;
      padding: 1px 5px;
      border-radius: 3px;
    }
    .order-pill {
      background: rgba(255, 255, 255, 0.04);
      border: 1px solid var(--border);
      color: #93c5fd;
      font-size: 10px;
      padding: 1px 6px;
      border-radius: 4px;
      font-family: var(--font-mono);
      font-weight: 600;
    }
    .empty-placeholder {
      text-align: center;
      padding: 1.5rem;
      color: var(--text-dim);
      font-family: var(--font-mono);
      font-size: 11px;
      background: var(--card);
      border: 1px solid var(--border-subtle);
      border-radius: var(--radius-lg);
    }

    /* History Section - Fade Out Gradient & Show More Toggle */
    .history-wrapper {
      position: relative;
      max-height: 290px;
      overflow: hidden;
      transition: max-height 0.4s cubic-bezier(0.16, 1, 0.3, 1);
    }
    .history-wrapper.expanded {
      max-height: 3500px;
      overflow: visible;
    }
    .history-fade {
      position: absolute;
      bottom: 0;
      left: 0;
      right: 0;
      height: 110px;
      background: linear-gradient(to bottom, rgba(12, 13, 16, 0) 0%, rgba(12, 13, 16, 0.75) 50%, #0c0d10 100%);
      pointer-events: none;
      transition: opacity 0.3s ease;
    }
    .history-wrapper.expanded .history-fade {
      opacity: 0;
      display: none;
    }
    .show-more-container {
      display: flex;
      justify-content: center;
      margin-top: 0.6rem;
    }
    .show-more-btn {
      display: inline-flex;
      align-items: center;
      gap: 6px;
      background: var(--card);
      border: 1px solid var(--border);
      color: var(--text-muted);
      font-size: 11px;
      font-family: var(--font-mono);
      padding: 6px 16px;
      border-radius: var(--radius-full);
      cursor: pointer;
      transition: all 0.2s ease;
      box-shadow: 0 4px 12px rgba(0, 0, 0, 0.3);
    }
    .show-more-btn:hover {
      background: var(--card-hover);
      border-color: var(--border-hover);
      color: var(--text);
      transform: translateY(-1px);
    }
    .show-more-btn span.arrow {
      font-size: 12px;
      transition: transform 0.2s ease;
    }
  </style>
</head>
<body>
  <div class="container">
    <header>
      <div class="brand">
        <h1>encode</h1>
        <span class="domain-pill">sengozhome</span>
      </div>
      <div id="status-pill" class="status-pill idle">
        <span class="dot"></span>
        <span id="status-text">IDLE</span>
      </div>
    </header>

    <section class="stats-grid">
      <div class="stat-card">
        <div class="stat-label">Total Saved</div>
        <div class="stat-value">
          <span id="stat-saved">0.0 GB</span>
          <span id="stat-saved-pct" class="stat-sub">(0%)</span>
        </div>
      </div>
      <div class="stat-card">
        <div class="stat-label">Completed</div>
        <div class="stat-value"><span id="stat-completed">0</span></div>
      </div>
      <div class="stat-card">
        <div class="stat-label">In Queue</div>
        <div class="stat-value"><span id="stat-queued">0</span></div>
      </div>
    </section>

    <!-- Active Transcode Card -->
    <div id="active-card" class="card">
      <!-- Idle State with Kita Ikuyo Mascot -->
      <div id="active-idle" class="idle-mascot-box">
        <div class="mascot-img-wrap">
          <img src="/assets/kita.png" alt="Kita Ikuyo" class="anime-mascot" />
        </div>
        <div class="idle-title">All tasks done! ~OwO</div>
        <div class="idle-subtitle">No active transcode in queue. Ready for next downloads from Sonarr or Radarr...</div>
        <div class="idle-badge">✨ Kitaaan~ standing by</div>
      </div>

      <!-- Encoding State with Hitori Gotoh Mascot -->
      <div id="active-encoding" style="display: none;">
        <div class="active-header-row">
          <div class="active-header-main">
            <div id="cur-title" class="card-title"></div>
            <div class="badges">
              <span id="badge-res" class="badge highlight">1080p → AV1 10-bit</span>
              <span class="badge green">Radeon 740M GPU</span>
              <span class="badge">Opus 2.0 (128k)</span>
              <span id="badge-speed" class="badge highlight">0 fps (0x)</span>
            </div>
          </div>
          <div class="bocchi-companion">
            <img src="/assets/bocchi.png" alt="Hitori Gotoh" class="bocchi-img" />
            <span class="mascot-speech">Ganbatte! ⚙️</span>
          </div>
        </div>

        <div class="progress-track">
          <div id="progress-fill" class="progress-fill" style="width: 0%;"></div>
        </div>
        <div class="progress-labels">
          <span id="progress-pct-frames">0% • 0 frames</span>
          <span id="progress-eta-elapsed">ETA 0s • Elapsed 0s</span>
        </div>

        <details id="tech-details">
          <summary>Technical Details</summary>
          <table class="details-table">
            <tr><td>Source:</td><td id="td-source">-</td></tr>
            <tr><td>Encoder:</td><td id="td-encoder">-</td></tr>
            <tr><td>Audio:</td><td>Stereo Opus (128 kbps, 48kHz)</td></tr>
            <tr><td>Input Size:</td><td id="td-size">-</td></tr>
            <tr><td>File Path:</td><td id="td-path" style="word-break: break-all;">-</td></tr>
          </table>
        </details>
      </div>

      <div class="enqueue-box">
        <input type="text" id="enqueue-input" class="enqueue-input" placeholder="Enqueue path: /nix/persist/media/shows/..." />
        <button id="enqueue-btn" class="enqueue-btn">+ Enqueue</button>
      </div>
    </div>

    <!-- Pending Queue Section -->
    <div id="queue-section">
      <div class="section-header">
        <span>Pending Queue</span>
        <span id="queue-count-badge" class="count-badge">0 items</span>
      </div>
      <div id="queue-list" class="list">
        <div class="empty-placeholder">Queue is empty. Relaxing for now~ (´｡• ᵕ •｡`)</div>
      </div>
    </div>

    <!-- Recent Activity Section (With Fade Gradient & Show More Toggle) -->
    <div id="history-section">
      <div class="section-header">
        <span>Recent Activity</span>
        <span id="history-count-badge" class="count-badge">0 items</span>
      </div>
      <div class="history-wrapper" id="history-wrapper">
        <div id="history-list" class="list">
          <div class="empty-placeholder">No completed jobs yet.</div>
        </div>
        <div id="history-fade" class="history-fade"></div>
      </div>
      <div class="show-more-container" id="show-more-container" style="display: none;">
        <button id="show-more-btn" class="show-more-btn" onclick="toggleHistoryExpand()">
          <span id="show-more-arrow" class="arrow">↓</span>
          <span id="show-more-label">show more</span>
        </button>
      </div>
    </div>
  </div>

  <script>
    let isHistoryExpanded = false;
    let latestHistoryCount = 0;

    function formatBytes(bytes) {
      if (!bytes || bytes === 0) return '0 B';
      const k = 1024;
      const sizes = ['B', 'KB', 'MB', 'GB', 'TB'];
      const i = Math.floor(Math.log(bytes) / Math.log(k));
      return parseFloat((bytes / Math.pow(k, i)).toFixed(1)) + ' ' + sizes[i];
    }

    function formatDuration(sec) {
      if (!sec || sec <= 0) return '0s';
      const m = Math.floor(sec / 60);
      const s = sec % 60;
      return m > 0 ? m + 'm ' + s + 's' : s + 's';
    }

    function toggleHistoryExpand() {
      isHistoryExpanded = !isHistoryExpanded;
      applyHistoryExpandState();
    }

    function applyHistoryExpandState() {
      const wrapper = document.getElementById('history-wrapper');
      const fade = document.getElementById('history-fade');
      const container = document.getElementById('show-more-container');
      const arrow = document.getElementById('show-more-arrow');
      const label = document.getElementById('show-more-label');

      if (latestHistoryCount <= 4) {
        container.style.display = 'none';
        fade.style.display = 'none';
        wrapper.classList.add('expanded');
        return;
      }

      container.style.display = 'flex';
      if (isHistoryExpanded) {
        wrapper.classList.add('expanded');
        fade.style.display = 'none';
        arrow.textContent = '↑';
        label.textContent = 'show less';
      } else {
        wrapper.classList.remove('expanded');
        fade.style.display = 'block';
        arrow.textContent = '↓';
        label.textContent = 'show more (' + (latestHistoryCount - 4) + ' more)';
      }
    }

    async function updateStatus() {
      try {
        const res = await fetch('/api/status');
        const data = await res.json();

        // Stats
        const stats = data.stats || {};
        document.getElementById('stat-saved').textContent = formatBytes(stats.total_saved_bytes || 0);
        document.getElementById('stat-saved-pct').textContent = stats.total_saved_pct ? '(-' + stats.total_saved_pct + '%)' : '(0%)';
        document.getElementById('stat-completed').textContent = stats.total_completed || 0;
        document.getElementById('stat-queued').textContent = (data.queue || []).length;

        // Status Pill & Mascot state
        const cur = data.current || {};
        const pill = document.getElementById('status-pill');
        const statusText = document.getElementById('status-text');

        if (cur.status === 'encoding') {
          pill.className = 'status-pill active';
          statusText.textContent = 'ENCODING';
          document.getElementById('active-idle').style.display = 'none';
          document.getElementById('active-encoding').style.display = 'block';

          document.getElementById('cur-title').textContent = cur.title || '';
          document.getElementById('badge-res').textContent = (cur.res_label || '1080p') + ' → AV1 10-bit';
          document.getElementById('badge-speed').textContent = (cur.current_fps || 0) + ' fps (' + (cur.speed || 0) + 'x)';
          document.getElementById('progress-fill').style.width = (cur.progress_pct || 0) + '%';
          document.getElementById('progress-pct-frames').textContent = (cur.progress_pct || 0) + '% • ' + (cur.frame || 0).toLocaleString() + ' frames';
          document.getElementById('progress-eta-elapsed').textContent = 'ETA ' + formatDuration(cur.eta_sec) + ' • Elapsed ' + formatDuration(cur.elapsed_sec);

          document.getElementById('td-source').textContent = (cur.source_codec || 'UNKNOWN').toUpperCase() + ' (' + cur.resolution + ' @ ' + cur.fps + 'fps)';
          document.getElementById('td-encoder').textContent = 'AV1 VA-API (Radeon 740M, Dynamic ' + cur.target_kbps + 'k / Max ' + cur.maxrate_kbps + 'k)';
          document.getElementById('td-size').textContent = formatBytes(cur.orig_bytes);
          document.getElementById('td-path').textContent = cur.path || '';
        } else {
          pill.className = 'status-pill idle';
          statusText.textContent = 'IDLE';
          document.getElementById('active-encoding').style.display = 'none';
          document.getElementById('active-idle').style.display = 'flex';
        }

        // Queue
        const q = data.queue || [];
        const qList = document.getElementById('queue-list');
        if (q.length > 0) {
          document.getElementById('queue-count-badge').textContent = q.length + ' pending';
          qList.innerHTML = q.map((item, idx) => {
            let orderTag = '';
            if (item.season_num !== undefined && item.season_num !== null && item.season_num !== 9999 && item.episode_num !== undefined && item.episode_num !== null) {
              orderTag = `S${String(item.season_num).padStart(2, '0')}E${String(item.episode_num).padStart(2, '0')}`;
            } else if (item.season_num === 9999) {
              orderTag = 'Movie';
            }
            const badgeHtml = orderTag ? `<span class="order-pill">${orderTag}</span>` : '';
            return `
              <div class="list-item">
                <div class="list-item-title">#${idx + 1} ${item.title}</div>
                <div class="list-item-meta">
                  ${badgeHtml}
                  <span>queued</span>
                </div>
              </div>
            `;
          }).join('');
        } else {
          document.getElementById('queue-count-badge').textContent = '0 items';
          qList.innerHTML = '<div class="empty-placeholder">Queue is empty. Relaxing for now~ (´｡• ᵕ •｡`)</div>';
        }

        // History
        const hist = data.history || [];
        latestHistoryCount = hist.length;
        document.getElementById('history-count-badge').textContent = hist.length + ' items';

        const hList = document.getElementById('history-list');
        if (hist.length > 0) {
          hList.innerHTML = hist.map(item => {
            let badge = '';
            if (item.status === 'completed') {
              badge = `<span class="savings-pill">-${item.saved_pct}%</span>`;
            } else if (item.status === 'skipped') {
              badge = `<span class="skipped-pill">${item.error_msg || 'skipped'}</span>`;
            } else {
              badge = `<span class="skipped-pill" style="color:#f87171;">failed</span>`;
            }
            const sizeText = item.orig_bytes > 0 && item.new_bytes > 0
              ? `${formatBytes(item.orig_bytes)} → ${formatBytes(item.new_bytes)}`
              : (item.res_label || '');

            return `
              <div class="list-item">
                <div class="list-item-title">${item.title}</div>
                <div class="list-item-meta">
                  <span>${sizeText}</span>
                  ${badge}
                  <span>${formatDuration(item.encode_time_sec)}</span>
                </div>
              </div>
            `;
          }).join('');
        } else {
          hList.innerHTML = '<div class="empty-placeholder">No completed jobs yet.</div>';
        }

        applyHistoryExpandState();

      } catch (err) {
        console.error("Failed to fetch status:", err);
      }
    }

    // Manual Enqueue Button
    document.getElementById('enqueue-btn').addEventListener('click', async () => {
      const input = document.getElementById('enqueue-input');
      const path = input.value.trim();
      if (!path) return;

      const btn = document.getElementById('enqueue-btn');
      btn.disabled = true;
      btn.textContent = 'Adding...';

      try {
        const res = await fetch('/api/enqueue', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ path: path })
        });
        const resData = await res.json();
        if (resData.ok) {
          input.value = '';
          btn.textContent = 'Added (' + resData.added + ')!';
          setTimeout(() => { btn.textContent = '+ Enqueue'; btn.disabled = false; }, 1500);
          updateStatus();
        } else {
          alert('Error: ' + (resData.error || 'Failed to enqueue'));
          btn.textContent = '+ Enqueue';
          btn.disabled = false;
        }
      } catch (e) {
        alert('Network error: ' + e);
        btn.textContent = '+ Enqueue';
        btn.disabled = false;
      }
    });

    updateStatus();
    setInterval(updateStatus, 1500);
  </script>
</body>
</html>
"""

def get_db():
    conn = sqlite3.connect(DB_PATH, timeout=10.0)
    conn.row_factory = sqlite3.Row
    return conn

class Handler(BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        return

    def do_HEAD(self):
        parsed = urlparse(self.path)
        if parsed.path in ("/", "/index.html"):
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
        elif parsed.path == "/api/status":
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.end_headers()
        elif parsed.path.startswith("/assets/"):
            name = os.path.basename(parsed.path)
            file_path = os.path.join(ASSETS_DIR, name)
            if not os.path.isfile(file_path):
                file_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets", name)
            if not os.path.isfile(file_path):
                file_path = os.path.join("/var/lib/av1-queue/assets", name)

            if os.path.isfile(file_path):
                self.send_response(200)
                mime = "image/png" if file_path.endswith(".png") else "image/webp"
                self.send_header("Content-Type", mime)
                self.end_headers()
            else:
                self.send_response(404)
                self.end_headers()
        else:
            self.send_response(404)
            self.end_headers()

    def do_GET(self):
        parsed = urlparse(self.path)
        if parsed.path == "/" or parsed.path == "/index.html":
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            self.wfile.write(HTML_TEMPLATE.encode("utf-8"))
        elif parsed.path.startswith("/assets/"):
            name = os.path.basename(parsed.path)
            file_path = os.path.join(ASSETS_DIR, name)
            if not os.path.isfile(file_path):
                file_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets", name)
            if not os.path.isfile(file_path):
                file_path = os.path.join("/var/lib/av1-queue/assets", name)

            if os.path.isfile(file_path):
                self.send_response(200)
                mime = "image/png" if file_path.endswith(".png") else "image/webp"
                self.send_header("Content-Type", mime)
                self.send_header("Cache-Control", "public, max-age=604800")
                self.end_headers()
                with open(file_path, "rb") as f:
                    self.wfile.write(f.read())
            else:
                self.send_response(404)
                self.end_headers()
        elif parsed.path == "/api/status":
            current_data = {"status": "idle"}
            if os.path.exists(CURRENT_PATH):
                try:
                    with open(CURRENT_PATH, "r", encoding="utf-8") as f:
                        current_data = json.load(f)
                except Exception:
                    pass

            queue_items = []
            history_items = []
            stats_data = {}

            if os.path.exists(DB_PATH):
                try:
                    with get_db() as conn:
                        q_rows = conn.execute("""
                            SELECT id, title, series_title, season_num, episode_num, path, added_at
                            FROM queue
                            WHERE status = 'pending'
                            ORDER BY series_title ASC, season_num ASC, episode_num ASC, id ASC
                            LIMIT 50
                        """).fetchall()
                        queue_items = [dict(r) for r in q_rows]

                        h_rows = conn.execute("""
                            SELECT id, title, res_label, orig_bytes, new_bytes, saved_pct, encode_time_sec, status, error_msg, completed_at
                            FROM queue WHERE status IN ('completed', 'skipped', 'failed')
                            ORDER BY completed_at DESC LIMIT 50
                        """).fetchall()
                        history_items = [dict(r) for r in h_rows]

                        s_row = conn.execute("""
                            SELECT
                                COUNT(*) as total_completed,
                                COALESCE(SUM(orig_bytes), 0) as total_orig,
                                COALESCE(SUM(new_bytes), 0) as total_new,
                                COALESCE(SUM(saved_bytes), 0) as total_saved
                            FROM queue WHERE status = 'completed'
                        """).fetchone()
                        if s_row:
                            total_orig = s_row["total_orig"]
                            total_saved = s_row["total_saved"]
                            pct = round((total_saved / total_orig) * 100.0, 1) if total_orig > 0 else 0.0
                            stats_data = {
                                "total_completed": s_row["total_completed"],
                                "total_orig_bytes": total_orig,
                                "total_new_bytes": s_row["total_new"],
                                "total_saved_bytes": total_saved,
                                "total_saved_pct": pct
                            }
                except Exception as e:
                    print(f"[av1-web] DB query error: {e}", file=sys.stderr)

            payload = {
                "current": current_data,
                "stats": stats_data,
                "queue": queue_items,
                "history": history_items
            }

            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Cache-Control", "no-cache")
            self.end_headers()
            self.wfile.write(json.dumps(payload).encode("utf-8"))
        else:
            self.send_response(404)
            self.end_headers()

    def do_POST(self):
        parsed = urlparse(self.path)
        if parsed.path == "/api/enqueue":
            length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(length).decode("utf-8")
            try:
                data = json.loads(body)
                target_path = data.get("path", "").strip()
            except Exception:
                target_path = ""

            if not target_path or not os.path.exists(target_path):
                self.send_response(400)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(json.dumps({"ok": False, "error": "Invalid or non-existent path"}).encode("utf-8"))
                return

            added_count = 0
            targets = []
            if os.path.isdir(target_path):
                for root, _, files in os.walk(target_path):
                    for f in files:
                        if f.lower().endswith((".mkv", ".mp4", ".ts", ".avi", ".webm")):
                            targets.append(os.path.join(root, f))
            else:
                targets.append(target_path)

            if os.path.exists(DB_PATH):
                with get_db() as conn:
                    for t in targets:
                        title = os.path.basename(t)
                        series_title, season_num, episode_num = parse_media_metadata(t)
                        existing = conn.execute("SELECT id FROM queue WHERE path = ? AND status IN ('pending', 'encoding', 'completed')", (t,)).fetchone()
                        if not existing:
                            conn.execute(
                                "INSERT INTO queue (path, title, series_title, season_num, episode_num, status) VALUES (?, ?, ?, ?, ?, 'pending')",
                                (t, title, series_title, season_num, episode_num)
                            )
                            added_count += 1
                    conn.commit()

            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps({"ok": True, "added": added_count}).encode("utf-8"))
        else:
            self.send_response(404)
            self.end_headers()

def main():
    server = HTTPServer(("", PORT), Handler)
    print(f"[av1-web] Serving minimalist transcode UI on port {PORT}...")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()

if __name__ == "__main__":
    main()
