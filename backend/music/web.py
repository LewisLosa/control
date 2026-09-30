"""Music Hub Web Server and Minimalist Cobalt-inspired Request Interface.

Features:
- Minimalist dark aesthetic matching encode.sengozhome.losa.dev (Cobalt.tools style).
- Real-time Server-Sent Events (SSE) streaming search across YT Music, Torrents, and Soulseek.
- Live progress bar showing exact search stages with zero artificial delays.
- "⏩ Soulseek'i Atla" (Skip Soulseek) button to immediately finalize without waiting for slow P2P peers.
- Live queue tracking with progress bars, status pills, and Navidrome quick-launch.
"""

import os
import sys
import time
import json
import sqlite3
import urllib.parse
import concurrent.futures
from http.server import HTTPServer, BaseHTTPRequestHandler
from socketserver import ThreadingMixIn
from typing import Dict, Any, List

from .sources import search_youtube_music, search_prowlarr, initiate_slskd_search, fetch_slskd_results, get_slskd_search_status, stop_slskd_search
from .scoring import rank_candidates, select_best_candidate
from .worker import init_db, DB_PATH
from ..common import required_env

PORT = int(os.environ.get("PORT", 8094))


class ThreadedHTTPServer(ThreadingMixIn, HTTPServer):
    daemon_threads = True
    allow_reuse_address = True

HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="tr">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
  <title>music • sengozhome</title>
  <meta name="theme-color" content="#0c0d10">
  <meta name="apple-mobile-web-app-capable" content="yes">
  <meta name="apple-mobile-web-app-status-bar-style" content="black-translucent">
  <link rel="manifest" href="/manifest.json">
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
      --emerald: #10b981;
      --emerald-glow: rgba(16, 185, 129, 0.15);
      --purple: #8b5cf6;
      --purple-glow: rgba(139, 92, 246, 0.15);
      --blue: #3b82f6;
      --amber: #f59e0b;
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
      padding: 2rem 1rem 4rem 1rem;
      min-height: 100vh;
    }
    .container {
      width: 100%;
      max-width: 640px;
      display: flex;
      flex-direction: column;
      gap: 1.25rem;
    }

    /* Header - Cobalt / Encode style */
    header {
      display: flex;
      align-items: center;
      justify-content: space-between;
      border-bottom: 1px solid var(--border-subtle);
      padding-bottom: 0.9rem;
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
    }
    .status-pill.active {
      color: #34d399;
      border-color: rgba(52, 211, 153, 0.3);
      background: rgba(16, 185, 129, 0.06);
    }
    .status-pill.active .dot {
      width: 6px;
      height: 6px;
      border-radius: 50%;
      background: #34d399;
      box-shadow: 0 0 8px #34d399;
      animation: pulse 1.6s infinite ease-in-out;
    }
    @keyframes pulse {
      0%, 100% { opacity: 1; transform: scale(1); }
      50% { opacity: 0.4; transform: scale(0.85); }
    }

    /* Stats Grid */
    .stats-grid {
      display: grid;
      grid-template-columns: repeat(3, 1fr);
      gap: 0.6rem;
    }
    .stat-card {
      background: var(--card);
      border: 1px solid var(--border);
      border-radius: var(--radius-lg);
      padding: 0.75rem 0.9rem;
      display: flex;
      flex-direction: column;
      gap: 0.25rem;
    }
    .stat-label {
      font-size: 10px;
      font-weight: 600;
      color: var(--text-dim);
      text-transform: uppercase;
      letter-spacing: 0.05em;
    }
    .stat-value {
      font-size: 14px;
      font-weight: 600;
      font-family: var(--font-mono);
      color: var(--text);
    }

    /* Main Action Card */
    .card {
      background: var(--card);
      border: 1px solid var(--border);
      border-radius: var(--radius-xl);
      padding: 1.25rem;
      display: flex;
      flex-direction: column;
      gap: 1rem;
      box-shadow: 0 12px 40px rgba(0, 0, 0, 0.45);
    }

    /* Search Input Box */
    .search-box {
      display: flex;
      gap: 0.5rem;
      align-items: center;
      background: var(--card-inner);
      border: 1px solid var(--border);
      border-radius: var(--radius-lg);
      padding: 4px 6px 4px 12px;
      transition: all 0.2s ease;
    }
    .search-box:focus-within {
      border-color: rgba(255, 255, 255, 0.25);
      box-shadow: 0 0 0 1px rgba(255, 255, 255, 0.1);
    }
    .search-input {
      flex: 1;
      background: transparent;
      border: none;
      outline: none;
      color: var(--text);
      font-size: 13px;
      padding: 8px 0;
    }
    .search-input::placeholder {
      color: var(--text-dim);
    }

    /* Buttons */
    .btn {
      display: inline-flex;
      align-items: center;
      justify-content: center;
      gap: 5px;
      background: var(--card);
      border: 1px solid var(--border);
      color: var(--text);
      font-size: 12px;
      font-family: var(--font-mono);
      font-weight: 500;
      padding: 7px 12px;
      border-radius: var(--radius-md);
      cursor: pointer;
      transition: all 0.2s ease;
      user-select: none;
      white-space: nowrap;
    }
    .btn:hover {
      border-color: var(--border-hover);
      background: var(--card-hover);
    }
    .btn:active {
      transform: scale(0.98);
    }
    .btn-primary {
      background: rgba(255, 255, 255, 0.08);
      border-color: rgba(255, 255, 255, 0.16);
      color: #fff;
    }
    .btn-primary:hover {
      background: rgba(255, 255, 255, 0.14);
      border-color: rgba(255, 255, 255, 0.28);
    }
    .btn-auto {
      background: linear-gradient(135deg, rgba(59, 130, 246, 0.2), rgba(139, 92, 246, 0.25));
      border-color: rgba(139, 92, 246, 0.4);
      color: #c4b5fd;
    }
    .btn-auto:hover {
      background: linear-gradient(135deg, rgba(59, 130, 246, 0.3), rgba(139, 92, 246, 0.35));
      border-color: rgba(139, 92, 246, 0.6);
      color: #fff;
    }
    .btn-skip {
      background: rgba(245, 158, 11, 0.1);
      border-color: rgba(245, 158, 11, 0.3);
      color: #fbbf24;
      font-size: 11px;
      padding: 4px 10px;
    }
    .btn-skip:hover {
      background: rgba(245, 158, 11, 0.2);
    }

    /* Live Search Progress Box */
    .progress-box {
      background: var(--card-inner);
      border: 1px solid var(--border);
      border-radius: var(--radius-lg);
      padding: 0.9rem 1rem;
      display: flex;
      flex-direction: column;
      gap: 0.6rem;
      animation: fadeIn 0.2s ease;
    }
    @keyframes fadeIn {
      from { opacity: 0; transform: translateY(-4px); }
      to { opacity: 1; transform: translateY(0); }
    }
    .progress-header {
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 8px;
    }
    .progress-status {
      font-size: 12px;
      font-family: var(--font-mono);
      color: var(--emerald);
      display: flex;
      align-items: center;
      gap: 6px;
    }
    .progress-track {
      width: 100%;
      height: 6px;
      background: rgba(255, 255, 255, 0.04);
      border: 1px solid var(--border-subtle);
      border-radius: var(--radius-full);
      overflow: hidden;
    }
    .progress-fill {
      height: 100%;
      background: linear-gradient(90deg, #10b981, #34d399);
      border-radius: var(--radius-full);
      transition: width 0.25s ease;
      box-shadow: 0 0 10px rgba(52, 211, 153, 0.4);
    }
    .progress-logs {
      font-size: 11px;
      font-family: var(--font-mono);
      color: var(--text-dim);
      display: flex;
      flex-direction: column;
      gap: 2px;
      max-height: 80px;
      overflow-y: auto;
    }
    .progress-log-item {
      display: flex;
      align-items: center;
      gap: 6px;
    }
    .progress-log-item.active {
      color: var(--text-muted);
    }

    /* Navigation Tabs */
    .tabs {
      display: flex;
      gap: 0.4rem;
      border-bottom: 1px solid var(--border-subtle);
      padding-bottom: 0.4rem;
    }
    .tab {
      padding: 6px 12px;
      border-radius: var(--radius-md);
      font-size: 12px;
      font-family: var(--font-mono);
      color: var(--text-dim);
      cursor: pointer;
      transition: all 0.15s ease;
      display: flex;
      align-items: center;
      gap: 6px;
    }
    .tab:hover {
      color: var(--text-muted);
    }
    .tab.active {
      color: var(--text);
      background: var(--card-inner);
      border: 1px solid var(--border);
    }
    .tab-badge {
      font-size: 10px;
      padding: 1px 6px;
      border-radius: var(--radius-full);
      background: rgba(255, 255, 255, 0.06);
      color: var(--text-muted);
    }

    /* Candidate & Queue Cards */
    .item-list {
      display: flex;
      flex-direction: column;
      gap: 0.5rem;
    }
    .item-card {
      background: var(--card-inner);
      border: 1px solid var(--border);
      border-radius: var(--radius-lg);
      padding: 0.75rem 0.9rem;
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 0.85rem;
      transition: all 0.2s ease;
    }
    .item-card:hover {
      border-color: var(--border-hover);
      background: #1c1e28;
    }
    .item-thumb {
      width: 44px;
      height: 44px;
      border-radius: var(--radius-md);
      object-fit: cover;
      background: #161822;
      flex-shrink: 0;
      border: 1px solid var(--border-subtle);
    }
    .item-info {
      flex: 1;
      min-width: 0;
      display: flex;
      flex-direction: column;
      gap: 3px;
    }
    .item-title {
      font-size: 13px;
      font-weight: 600;
      color: #fafafa;
      white-space: nowrap;
      overflow: hidden;
      text-overflow: ellipsis;
    }
    .item-artist {
      font-size: 11px;
      color: var(--text-muted);
      white-space: nowrap;
      overflow: hidden;
      text-overflow: ellipsis;
    }
    .item-thumb-fallback {
      display: flex;
      align-items: center;
      justify-content: center;
      font-size: 16px;
      background: var(--card);
      border: 1px solid var(--border-subtle);
      user-select: none;
    }
    .item-meta {
      display: flex;
      align-items: center;
      gap: 6px;
      flex-wrap: wrap;
      font-size: 11px;
      font-family: var(--font-mono);
      color: var(--text-dim);
    }

    /* Badges */
    .badge {
      font-size: 10px;
      font-family: var(--font-mono);
      padding: 2px 7px;
      border-radius: var(--radius-md);
      font-weight: 600;
      text-transform: uppercase;
      letter-spacing: 0.02em;
    }
    .badge-flac {
      color: #34d399;
      background: rgba(16, 185, 129, 0.1);
      border: 1px solid rgba(16, 185, 129, 0.25);
    }
    .badge-opus {
      color: #c084fc;
      background: rgba(192, 132, 252, 0.1);
      border: 1px solid rgba(192, 132, 252, 0.25);
    }
    .badge-mp3 {
      color: #fbbf24;
      background: rgba(245, 158, 11, 0.1);
      border: 1px solid rgba(245, 158, 11, 0.25);
    }
    .badge-score {
      color: #60a5fa;
      background: rgba(96, 165, 250, 0.1);
      border: 1px solid rgba(96, 165, 250, 0.2);
    }

    /* Queue Status Badges */
    .status-badge {
      font-size: 11px;
      font-family: var(--font-mono);
      padding: 4px 10px;
      border-radius: var(--radius-full);
      font-weight: 500;
      border: 1px solid transparent;
      white-space: nowrap;
    }
    .status-pending { color: #9ca3af; background: rgba(156, 163, 175, 0.1); border-color: rgba(156, 163, 175, 0.2); }
    .status-downloading { color: #60a5fa; background: rgba(59, 130, 246, 0.1); border-color: rgba(59, 130, 246, 0.3); }
    .status-processing { color: #c084fc; background: rgba(192, 132, 252, 0.1); border-color: rgba(192, 132, 252, 0.3); }
    .status-completed { color: #34d399; background: rgba(16, 185, 129, 0.1); border-color: rgba(16, 185, 129, 0.3); }
    .status-failed { color: #f87171; background: rgba(248, 113, 113, 0.1); border-color: rgba(248, 113, 113, 0.3); }

    .empty-state {
      text-align: center;
      padding: 2.5rem 1rem;
      color: var(--text-dim);
      font-size: 12px;
      font-family: var(--font-mono);
    }
  </style>
</head>
<body>
  <div class="container">
    <!-- Header -->
    <header>
      <div class="brand">
        <h1>music</h1>
        <span class="domain-pill">sengozhome</span>
      </div>
      <div class="status-pill active">
        <span class="dot"></span>
        <span>ready • opus 160k</span>
      </div>
    </header>

    <!-- Stats Grid -->
    <div class="stats-grid">
      <div class="stat-card">
        <div class="stat-label">Ses Standardı</div>
        <div class="stat-value" style="color: #34d399;">SOXR • -1dB</div>
      </div>
      <div class="stat-card">
        <div class="stat-label">Kaynaklar</div>
        <div class="stat-value">SLSK • TOR • YT</div>
      </div>
      <div class="stat-card">
        <div class="stat-label">Kuyruk Durumu</div>
        <div class="stat-value" id="statQueueCount">0 işlem</div>
      </div>
    </div>

    <!-- Main Card -->
    <div class="card">
      <!-- Search Input -->
      <div class="search-box">
        <input type="text" class="search-input" id="queryInput" placeholder="Şarkı, sanatçı veya Spotify / YouTube linki..." autocomplete="off"/>
        <button class="btn btn-auto" id="btnAuto" title="En yüksek kaliteli kaynağı otomatik seçip indir">⚡ Akıllı İndir</button>
        <button class="btn btn-primary" id="btnSearch" title="Tüm kaynakları tara ve listele">Ara</button>
      </div>

      <!-- Live Search Progression Box -->
      <div class="progress-box" id="progressBox" style="display: none;">
        <div class="progress-header">
          <div class="progress-status" id="progressStatus">
            <span class="dot" style="width: 6px; height: 6px; background: #34d399; border-radius: 50%;"></span>
            <span id="progressStatusText">Kaynaklar taranıyor...</span>
          </div>
          <button class="btn btn-skip" id="btnSkipSoulseek" style="display: none;">⏩ Soulseek'i Atla</button>
        </div>
        <div class="progress-track">
          <div class="progress-fill" id="progressFill" style="width: 15%;"></div>
        </div>
        <div class="progress-logs" id="progressLogs">
          <!-- Live stage log items -->
        </div>
      </div>

      <!-- Navigation Tabs -->
      <div class="tabs">
        <div class="tab active" id="tabResults" onclick="showTab('results')">
          <span>Sonuçlar</span>
          <span class="tab-badge" id="resultsCount">0</span>
        </div>
        <div class="tab" id="tabQueue" onclick="showTab('queue')">
          <span>Kuyruk</span>
          <span class="tab-badge" id="queueBadge">0</span>
        </div>
      </div>

      <!-- Results View -->
      <div id="resultsView">
        <div class="item-list" id="resultsList">
          <div class="empty-state">Aramak veya indirmek istediğiniz bir parça girin.</div>
        </div>
      </div>

      <!-- Queue View -->
      <div id="queueView" style="display: none;">
        <div class="item-list" id="queueList">
          <div class="empty-state">Kuyrukta bekleyen işlem yok.</div>
        </div>
      </div>
    </div>
  </div>

  <script>
    let currentTab = 'results';
    let currentEventSource = null;
    let accumulatedCandidates = [];

    function showTab(tab) {
      currentTab = tab;
      document.getElementById('tabResults').classList.toggle('active', tab === 'results');
      document.getElementById('tabQueue').classList.toggle('active', tab === 'queue');
      document.getElementById('resultsView').style.display = tab === 'results' ? 'block' : 'none';
      document.getElementById('queueView').style.display = tab === 'queue' ? 'block' : 'none';
      if (tab === 'queue') refreshQueue();
    }

    function addProgressLog(text, isDone = false) {
      const logs = document.getElementById('progressLogs');
      const item = document.createElement('div');
      item.className = 'progress-log-item' + (isDone ? '' : ' active');
      item.innerHTML = `<span>${isDone ? '✓' : '•'}</span> <span>${text}</span>`;
      logs.appendChild(item);
      logs.scrollTop = logs.scrollHeight;
    }

    function startStreamingSearch(query) {
      if (currentEventSource) {
        currentEventSource.close();
      }

      accumulatedCandidates = [];
      const box = document.getElementById('progressBox');
      const fill = document.getElementById('progressFill');
      const statusText = document.getElementById('progressStatusText');
      const skipBtn = document.getElementById('btnSkipSoulseek');
      const logs = document.getElementById('progressLogs');
      const list = document.getElementById('resultsList');

      box.style.display = 'flex';
      skipBtn.style.display = 'none';
      fill.style.width = '15%';
      statusText.textContent = 'Sorgu başlatılıyor...';
      logs.innerHTML = '';
      list.innerHTML = '<div class="empty-state">Kaynaklar canlı taranıyor...</div>';
      showTab('results');

      const url = '/api/search/stream?q=' + encodeURIComponent(query);
      currentEventSource = new EventSource(url);

      currentEventSource.onmessage = function(e) {
        try {
          const data = JSON.parse(e.data);

          if (data.progress) {
            fill.style.width = data.progress + '%';
          }
          if (data.status) {
            statusText.textContent = data.status;
          }
          if (data.log) {
            addProgressLog(data.log, data.is_done);
          }

          if (data.allow_skip) {
            skipBtn.style.display = 'inline-flex';
          }

          if (data.items && data.items.length > 0) {
            accumulatedCandidates = accumulatedCandidates.concat(data.items);
            renderResults(accumulatedCandidates);
          }

          if (data.stage === 'complete') {
            currentEventSource.close();
            currentEventSource = null;
            fill.style.width = '100%';
            statusText.textContent = 'Arama tamamlandı';
            skipBtn.style.display = 'none';
            if (data.final_results) {
              renderResults(data.final_results);
            }
            setTimeout(() => {
              box.style.display = 'none';
            }, 3000);
          }
        } catch (err) {
          console.error(err);
        }
      };

      currentEventSource.onerror = function() {
        if (currentEventSource) {
          currentEventSource.close();
          currentEventSource = null;
        }
        statusText.textContent = 'Arama sonuçlandırıldı';
        skipBtn.style.display = 'none';
        if (accumulatedCandidates.length > 0) {
          renderResults(accumulatedCandidates);
        }
        setTimeout(() => { box.style.display = 'none'; }, 2000);
      };
    }

    document.getElementById('btnSkipSoulseek').addEventListener('click', () => {
      if (currentEventSource) {
        currentEventSource.close();
        currentEventSource = null;
      }
      document.getElementById('progressFill').style.width = '100%';
      document.getElementById('progressStatusText').textContent = 'Soulseek atlandı. Mevcut sonuçlar listelendi.';
      document.getElementById('btnSkipSoulseek').style.display = 'none';
      renderResults(accumulatedCandidates);
      setTimeout(() => {
        document.getElementById('progressBox').style.display = 'none';
      }, 1500);
    });

    async function autoDownload() {
      const q = document.getElementById('queryInput').value.trim();
      if (!q) return;

      const statusText = document.getElementById('progressStatusText');
      const box = document.getElementById('progressBox');
      const fill = document.getElementById('progressFill');
      box.style.display = 'flex';
      fill.style.width = '30%';
      statusText.textContent = 'En kaliteli kaynak otomatik seçiliyor...';

      try {
        const res = await fetch('/api/auto-download', {
          method: 'POST',
          headers: {'Content-Type': 'application/json'},
          body: JSON.stringify({query: q})
        });
        const data = await res.json();
        fill.style.width = '100%';
        statusText.textContent = 'Kuyruğa eklendi!';
        setTimeout(() => { box.style.display = 'none'; }, 1500);
        showTab('queue');
        refreshQueue();
      } catch (err) {
        alert('Hata: ' + err.message);
        box.style.display = 'none';
      }
    }

    function renderResults(items) {
      const list = document.getElementById('resultsList');
      const badge = document.getElementById('resultsCount');
      badge.textContent = items.length;

      if (!items || items.length === 0) {
        list.innerHTML = '<div class="empty-state">Hiçbir kaynakta eşleşme bulunamadı.</div>';
        return;
      }

      list.innerHTML = items.map(item => {
        const badgeClass = item.format_hint === 'lossless' ? 'badge-flac' : (item.format_hint === 'opus_native' ? 'badge-opus' : 'badge-mp3');
        const badgeText = item.format_hint === 'lossless' ? 'FLAC' : (item.format_hint === 'opus_native' ? 'OPUS' : 'MP3');
        const thumbHtml = (item.thumbnail && item.thumbnail.startsWith('http'))
          ? `<img class="item-thumb" src="${escapeHtml(item.thumbnail)}" onerror="this.outerHTML='<div class=\\'item-thumb item-thumb-fallback\\'>🎵</div>'"/>`
          : `<div class="item-thumb item-thumb-fallback">🎵</div>`;
        const durText = item.duration ? Math.floor(item.duration / 60) + ':' + String(Math.floor(item.duration % 60)).padStart(2, '0') : '';
        const artistText = escapeHtml(item.artist || 'Bilinmeyen Sanatçı') + (item.album && item.album !== 'Singles' ? ' • ' + escapeHtml(item.album) : '');

        return `
          <div class="item-card">
            ${thumbHtml}
            <div class="item-info">
              <div class="item-title">${escapeHtml(item.title)}</div>
              <div class="item-artist">${artistText}</div>
              <div class="item-meta">
                <span class="badge ${badgeClass}">${badgeText}</span>
                <span class="badge badge-score">${item.score || 80}/100</span>
                <span>${item.source === 'youtube_music' ? 'YT MUSIC' : item.source.toUpperCase()}</span>
                ${durText ? '<span>' + durText + '</span>' : ''}
                ${item.bitrate ? '<span>' + item.bitrate + 'k</span>' : ''}
                ${item.size_mb ? '<span>' + item.size_mb + ' MB</span>' : ''}
              </div>
            </div>
            <button class="btn btn-primary" onclick='downloadCandidate(${JSON.stringify(item).replace(/'/g, "&#39;")})'>İndir</button>
          </div>
        `;
      }).join('');
    }

    async function downloadCandidate(item) {
      try {
        const res = await fetch('/api/download', {
          method: 'POST',
          headers: {'Content-Type': 'application/json'},
          body: JSON.stringify(item)
        });
        showTab('queue');
        refreshQueue();
      } catch (err) {
        alert('İndirme başlatılamadı: ' + err.message);
      }
    }

    async function refreshQueue() {
      try {
        const res = await fetch('/api/tasks');
        const tasks = await res.json();
        const list = document.getElementById('queueList');
        const badge = document.getElementById('queueBadge');
        const stat = document.getElementById('statQueueCount');

        badge.textContent = tasks.length;
        const activeCount = tasks.filter(t => t.status === 'downloading' || t.status === 'processing' || t.status === 'pending').length;
        stat.textContent = activeCount + ' aktif';

        if (!tasks || tasks.length === 0) {
          list.innerHTML = '<div class="empty-state">Kuyrukta bekleyen işlem yok.</div>';
          return;
        }

        list.innerHTML = tasks.map(t => {
          let statusLabel = t.status;
          if (t.status === 'completed') statusLabel = 'Navidrome Hazır';
          else if (t.status === 'downloading') statusLabel = 'İndiriliyor %' + t.progress;
          else if (t.status === 'processing') statusLabel = 'Opus İşleniyor';

          return `
            <div class="item-card">
              <div class="item-info">
                <div class="item-title">${escapeHtml(t.artist || '')} - ${escapeHtml(t.title || t.query)}</div>
                <div class="item-meta">
                  <span>${t.source.toUpperCase()}</span>
                  <span>${t.created_at}</span>
                  ${t.error ? '<span style="color: #f87171;">' + escapeHtml(t.error) + '</span>' : ''}
                </div>
              </div>
              <span class="status-badge status-${t.status}">${statusLabel}</span>
            </div>
          `;
        }).join('');
      } catch (err) {
        console.error(err);
      }
    }

    function escapeHtml(text) {
      const div = document.createElement('div');
      div.textContent = text || '';
      return div.innerHTML;
    }

    document.getElementById('btnSearch').addEventListener('click', () => {
      const q = document.getElementById('queryInput').value.trim();
      if (q) startStreamingSearch(q);
    });
    document.getElementById('btnAuto').addEventListener('click', autoDownload);
    document.getElementById('queryInput').addEventListener('keydown', (e) => {
      if (e.key === 'Enter') {
        const q = document.getElementById('queryInput').value.trim();
        if (q) startStreamingSearch(q);
      }
    });

    setInterval(() => {
      if (currentTab === 'queue') refreshQueue();
    }, 3000);
    refreshQueue();
  </script>
</body>
</html>
"""

MANIFEST_JSON = json.dumps({
    "name": "music • sengozhome",
    "short_name": "music",
    "start_url": "/",
    "display": "standalone",
    "background_color": "#0c0d10",
    "theme_color": "#0c0d10",
    "icons": [
        {
            "src": "data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 100 100'><circle cx='50' cy='50' r='50' fill='%2313141a'/><path d='M35 30v40l35-20z' fill='%2310b981'/></svg>",
            "sizes": "192x192 512x512",
            "type": "image/svg+xml"
        }
    ]
}, indent=2)


class MusicHubHandler(BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        pass

    def send_json(self, status_code: int, data: Any):
        body = json.dumps(data).encode("utf-8")
        self.send_response(status_code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path

        if path == "/":
            body = HTML_TEMPLATE.encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return

        if path == "/manifest.json":
            body = MANIFEST_JSON.encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "application/manifest+json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return

        # Real-time SSE streaming search endpoint
        if path in ("/api/search", "/api/search/stream"):
            qs = urllib.parse.parse_qs(parsed.query)
            query = qs.get("q", [""])[0].strip()
            if not query:
                self.send_response(400)
                self.end_headers()
                return

            self.send_response(200)
            self.send_header("Content-Type", "text/event-stream")
            self.send_header("Cache-Control", "no-cache")
            self.send_header("Connection", "keep-alive")
            self.end_headers()

            def send_event(data_dict):
                try:
                    payload = f"data: {json.dumps(data_dict)}\n\n"
                    self.wfile.write(payload.encode("utf-8"))
                    self.wfile.flush()
                    return True
                except Exception:
                    return False

            candidates = []

            # 1. Parallel execution: Trigger Soulseek search on slskd right at T=0
            send_event({
                "stage": "search_start",
                "progress": 10,
                "status": "Arama başlatıldı...",
                "log": "YouTube Music, Torrent ve Soulseek paralel sorgulanıyor...",
                "allow_skip": True
            })

            slskd_id = initiate_slskd_search(query)

            # 2. Run YouTube Music and Prowlarr in concurrent thread pool
            executor = concurrent.futures.ThreadPoolExecutor(max_workers=2)
            yt_future = executor.submit(search_youtube_music, query, 6)
            prow_future = executor.submit(search_prowlarr, query, 3)

            # 3. As soon as YouTube Music returns (typically 1s), immediately stream its results!
            try:
                yt_res = yt_future.result(timeout=6.0)
                if yt_res:
                    candidates.extend(yt_res)
                    ok = send_event({
                        "stage": "youtube_done",
                        "progress": 35,
                        "status": f"YouTube Music'ten {len(yt_res)} parça listelendi",
                        "log": f"YouTube Music: {len(yt_res)} resmi akış hazır",
                        "items": yt_res,
                        "allow_skip": True
                    })
                    if not ok:
                        executor.shutdown(wait=False)
                        return
            except Exception as e:
                print(f"YouTube search error: {e}")

            # 4. Check Prowlarr results when ready
            try:
                prow_res = prow_future.result(timeout=4.0)
                if prow_res:
                    candidates.extend(prow_res)
                    ok = send_event({
                        "stage": "prowlarr_done",
                        "progress": 45,
                        "status": f"Torrent: {len(prow_res)} sonuç bulundu",
                        "log": f"Torrent: {len(prow_res)} release eklendi",
                        "items": prow_res,
                        "allow_skip": True
                    })
                    if not ok:
                        executor.shutdown(wait=False)
                        return
            except Exception as e:
                print(f"Prowlarr search error: {e}")

            executor.shutdown(wait=False)

            # 5. Wait for Soulseek P2P network responses
            slsk_res = []
            if slskd_id:
                start_slsk = time.time()
                max_slsk_wait = 8.5  # Max search duration in seconds
                last_file_count = 0
                stable_cycles = 0
                resp_count = 0
                file_count = 0

                while True:
                    time.sleep(0.7)
                    elapsed = time.time() - start_slsk

                    status_info = get_slskd_search_status(slskd_id)
                    is_complete = False

                    if status_info:
                        is_complete = status_info.get("isComplete", False)
                        file_count = status_info.get("fileCount", 0)
                        resp_count = status_info.get("responseCount", 0)

                    calc_prog = min(92, int(45 + (elapsed / max_slsk_wait) * 47))

                    if file_count > 0:
                        status_str = f"Soulseek taranıyor ({resp_count} peer, {file_count} dosya inceleniyor)..."
                        log_str = f"Soulseek: {resp_count} kullanıcıdan {file_count} dosya bulundu"
                    else:
                        status_str = f"Soulseek taranıyor ({resp_count} peer yanıt verdi)..."
                        log_str = "Soulseek ağı taranıyor..."

                    ok = send_event({
                        "stage": "soulseek_poll",
                        "progress": calc_prog,
                        "status": status_str,
                        "log": log_str,
                        "allow_skip": True
                    })
                    if not ok:
                        # Client disconnected
                        stop_slskd_search(slskd_id)
                        return

                    # Track file count stability
                    if file_count > 0 and file_count == last_file_count:
                        stable_cycles += 1
                    else:
                        stable_cycles = 0
                    last_file_count = file_count

                    # Exit conditions:
                    if is_complete:
                        print(f"Soulseek search {slskd_id} completed naturally ({file_count} files, {resp_count} peers).")
                        break

                    if elapsed >= max_slsk_wait:
                        print(f"Soulseek search {slskd_id} hit timeout {max_slsk_wait}s ({file_count} files, {resp_count} peers).")
                        break

                    if file_count >= 80 and elapsed >= 5.0:
                        print(f"Soulseek search {slskd_id} collected plenty ({file_count} files) at {elapsed:.1f}s.")
                        break

                    if file_count >= 20 and elapsed >= 4.0 and stable_cycles >= 2:
                        print(f"Soulseek search {slskd_id} stabilized at {file_count} files at {elapsed:.1f}s.")
                        break

                # Critical: Stop search on slskd so it commits in-memory buffer to SQLite
                stop_slskd_search(slskd_id)
                time.sleep(0.15)

                # Fetch final set of top ranked Soulseek results
                slsk_res = fetch_slskd_results(slskd_id, limit=35, query=query)
                candidates.extend(slsk_res)

                send_event({
                    "stage": "soulseek_done",
                    "progress": 96,
                    "status": f"Soulseek tamamlandı ({len(slsk_res)} kaliteli kaynak seçildi)",
                    "log": f"Soulseek tamamlandı: {resp_count} peer ve {file_count} dosya arasından en iyiler seçildi.",
                    "items": slsk_res,
                    "allow_skip": False
                })

            # Final: Calculate quality scores and rank all candidates together
            ranked = rank_candidates(candidates, query=query)
            send_event({
                "stage": "complete",
                "progress": 100,
                "status": f"Arama tamamlandı ({len(ranked)} sonuç)",
                "log": f"Toplam {len(ranked)} kaynak puanlandı ve ses kalitesine göre sıralandı.",
                "is_done": True,
                "final_results": ranked,
                "items": ranked
            })
            return

        if path == "/api/tasks":
            with sqlite3.connect(DB_PATH) as conn:
                conn.row_factory = sqlite3.Row
                cur = conn.cursor()
                cur.execute("SELECT * FROM tasks ORDER BY id DESC LIMIT 25")
                tasks = []
                for row in cur.fetchall():
                    task = dict(row)
                    task.pop("keep_metadata", None)
                    tasks.append(task)
            self.send_json(200, tasks)
            return

        self.send_response(404)
        self.end_headers()

    def do_POST(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path
        length = int(self.headers.get("Content-Length", 0))
        post_data = self.rfile.read(length) if length > 0 else b"{}"

        try:
            body = json.loads(post_data.decode("utf-8"))
        except Exception:
            body = {}

        if path == "/api/download":
            source = body.get("source", "youtube_music")
            source_id = body.get("id", "")
            source_url = body.get("url") or body.get("download_url") or ""
            title = body.get("title", "")
            artist = body.get("artist", "")
            album = body.get("album", "")
            score = body.get("score", 0)

            if source in ("torrent", "prowlarr") and not source_url:
                if source_id and (source_id.startswith("http") or source_id.startswith("magnet:")):
                    source_url = source_id

            with sqlite3.connect(DB_PATH) as conn:
                cur = conn.cursor()
                cur.execute("""
                    INSERT INTO tasks (query, artist, title, album, source, source_id, source_url, score, status)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'pending')
                """, (title, artist, title, album, source, source_id, source_url, score))
                conn.commit()
                task_id = cur.lastrowid

            self.send_json(200, {"success": True, "task_id": task_id})
            return

        if path == "/api/auto-download":
            query = body.get("query", "").strip()
            if not query:
                self.send_json(400, {"error": "Missing query"})
                return

            candidates = []
            executor = concurrent.futures.ThreadPoolExecutor(max_workers=2)
            yt_f = executor.submit(search_youtube_music, query, 5)
            prow_f = executor.submit(search_prowlarr, query, 3)
            slsk_id = initiate_slskd_search(query)

            try:
                candidates.extend(yt_f.result(timeout=4.0) or [])
            except Exception:
                pass

            try:
                candidates.extend(prow_f.result(timeout=3.5) or [])
            except Exception:
                pass

            executor.shutdown(wait=False)

            if slsk_id:
                start_s = time.time()
                while time.time() - start_s < 6.0:
                    time.sleep(0.6)
                    st = get_slskd_search_status(slsk_id)
                    if st and (st.get("isComplete") or st.get("fileCount", 0) >= 40):
                        break
                stop_slskd_search(slsk_id)
                time.sleep(0.15)
                candidates.extend(fetch_slskd_results(slsk_id, limit=15, query=query))

            best = select_best_candidate(candidates, query=query)
            if not best:
                self.send_json(404, {"error": "No suitable candidate found"})
                return

            with sqlite3.connect(DB_PATH) as conn:
                cur = conn.cursor()
                cur.execute("""
                    INSERT INTO tasks (query, artist, title, album, source, source_id, source_url, score, status)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'pending')
                """, (
                    query,
                    best.get("artist", ""),
                    best.get("title", query),
                    best.get("album", "Singles"),
                    best.get("source", "youtube_music"),
                    best.get("id", ""),
                    best.get("url") or best.get("download_url", ""),
                    best.get("score", 0),
                ))
                conn.commit()
                task_id = cur.lastrowid

            self.send_json(200, {"success": True, "task_id": task_id, "selected": best})
            return

        if path == "/api/tasks/cancel":
            task_id = body.get("id")
            if not task_id:
                self.send_json(400, {"error": "Missing task id"})
                return

            with sqlite3.connect(DB_PATH) as conn:
                cur = conn.cursor()
                cur.execute("SELECT status FROM tasks WHERE id = ?", (task_id,))
                row = cur.fetchone()
                if not row:
                    self.send_json(404, {"error": "Task not found"})
                    return
                current_status = row[0]
                if current_status in ("completed",):
                    self.send_json(400, {"error": f"Cannot cancel task in '{current_status}' state"})
                    return
                cur.execute(
                    "UPDATE tasks SET status = 'cancelled', error = 'Kullanıcı tarafından iptal edildi', updated_at = CURRENT_TIMESTAMP WHERE id = ?",
                    (task_id,)
                )
                conn.commit()

            self.send_json(200, {"success": True, "task_id": task_id})
            return

        self.send_response(404)
        self.end_headers()


def run_server():
    required_env("PROWLARR_API_KEY")
    init_db()
    server_address = ("127.0.0.1", PORT)
    httpd = ThreadedHTTPServer(server_address, MusicHubHandler)
    print(f"Music Hub Web Server running at http://127.0.0.1:{PORT}")
    httpd.serve_forever()


if __name__ == "__main__":
    run_server()
