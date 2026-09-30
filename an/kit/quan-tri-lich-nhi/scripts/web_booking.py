# -*- coding: utf-8 -*-
"""web_booking.py — Máy chủ Web Portal Đặt Lịch Thi Sen (Google Calendar + Google Meet)."""

from __future__ import annotations

import json
import os
import sys
import urllib.parse
from datetime import datetime, date, timedelta, timezone
from http.server import HTTPServer, BaseHTTPRequestHandler
from pathlib import Path

MUI_GIO = timezone(timedelta(hours=7))

# Nạp các module quản trị lịch
sys.path.insert(0, str(Path(__file__).parent))
import lich
import khe_trong


HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="vi">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Cổng Đặt Lịch Hẹn — Thi Sen (Yên Phục)</title>
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=Be+Vietnam+Pro:ital,wght@0,400;0,500;0,600;0,700;0,800;0,900;1,400;1,700&family=Plus+Jakarta+Sans:wght@300;400;500;600;700;800&display=swap" rel="stylesheet">
  <style>
    :root {
      --font-display: 'Be Vietnam Pro', 'Plus Jakarta Sans', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
      --font-body: 'Plus Jakarta Sans', 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
      --bg-base: #0b0f19;
      --bg-card: rgba(18, 24, 38, 0.88);
      --bg-card-hover: rgba(26, 34, 52, 0.95);
      --border-color: rgba(255, 255, 255, 0.08);
      --border-active: #10b981;
      --text-main: #f8fafc;
      --text-muted: #94a3b8;
      --primary: #10b981;
      --primary-hover: #059669;
      --primary-glow: rgba(16, 185, 129, 0.25);
      --accent: #38bdf8;
      --accent-glow: rgba(56, 189, 248, 0.2);
    }
    * {
      box-sizing: border-box;
      margin: 0;
      padding: 0;
    }
    body {
      font-family: var(--font-body);
      background: radial-gradient(circle at 50% 0%, #172554 0%, #0b0f19 75%);
      color: var(--text-main);
      min-height: 100vh;
      display: flex;
      flex-direction: column;
      align-items: center;
      padding: 32px 16px;
      -webkit-font-smoothing: antialiased;
      -moz-osx-font-smoothing: grayscale;
      text-rendering: optimizeLegibility;
    }
    .container {
      width: 100%;
      max-width: 880px;
      background: var(--bg-card);
      backdrop-filter: blur(16px);
      border: 1px solid var(--border-color);
      border-radius: 24px;
      box-shadow: 0 25px 50px -12px rgba(0, 0, 0, 0.5), 0 0 30px rgba(16, 185, 129, 0.06);
      overflow: hidden;
      animation: fadeIn 0.4s ease-out;
    }
    @keyframes fadeIn {
      from { opacity: 0; transform: translateY(12px); }
      to { opacity: 1; transform: translateY(0); }
    }
    .header {
      padding: 36px 36px 24px;
      border-bottom: 1px solid var(--border-color);
      position: relative;
    }
    .badge-bar {
      display: flex;
      justify-content: space-between;
      align-items: center;
      margin-bottom: 14px;
      flex-wrap: wrap;
      gap: 10px;
    }
    .badge {
      display: inline-flex;
      align-items: center;
      gap: 6px;
      padding: 4px 12px;
      border-radius: 9999px;
      background: rgba(16, 185, 129, 0.12);
      border: 1px solid rgba(16, 185, 129, 0.3);
      color: #34d399;
      font-size: 13px;
      font-weight: 600;
    }
    .badge::before {
      content: "";
      width: 6px;
      height: 6px;
      border-radius: 50%;
      background: #10b981;
      box-shadow: 0 0 8px #10b981;
    }
    .portal-link {
      font-size: 13px;
      color: var(--accent);
      text-decoration: none;
      font-weight: 600;
      transition: color 0.2s;
    }
    .portal-link:hover {
      color: #7dd3fc;
      text-decoration: underline;
    }
    h1 {
      font-family: var(--font-display);
      font-size: 28px;
      font-weight: 800;
      letter-spacing: -0.02em;
      color: #ffffff;
      line-height: 1.35;
      padding: 0.1em 0;
      margin-bottom: 8px;
      text-shadow: 0 4px 20px rgba(0,0,0,0.5);
    }
    .subtitle {
      color: var(--text-muted);
      font-size: 15px;
      line-height: 1.5;
    }

    /* Personal Hero Card */
    .personal-hero {
      margin: 16px 0 6px;
      padding: 20px;
      background: linear-gradient(135deg, rgba(30, 41, 59, 0.7), rgba(15, 23, 42, 0.85));
      border: 1px solid rgba(56, 189, 248, 0.25);
      border-radius: 18px;
      display: flex;
      align-items: center;
      gap: 18px;
      box-shadow: 0 10px 25px -5px rgba(0, 0, 0, 0.3);
    }
    .hero-avatar {
      width: 64px;
      height: 64px;
      border-radius: 50%;
      background: linear-gradient(135deg, #10b981, #0284c7);
      display: flex;
      align-items: center;
      justify-content: center;
      font-family: var(--font-display);
      font-size: 24px;
      font-weight: 800;
      color: #fff;
      flex-shrink: 0;
      box-shadow: 0 0 20px rgba(16, 185, 129, 0.3);
    }
    .hero-info {
      flex: 1;
    }
    .hero-info h2 {
      font-family: var(--font-display);
      font-size: 20px;
      font-weight: 800;
      color: #ffffff;
      margin-bottom: 2px;
    }
    .hero-info .hero-role {
      font-size: 14px;
      color: var(--accent);
      font-weight: 600;
      margin-bottom: 4px;
    }
    .hero-info .hero-desc {
      font-size: 13px;
      color: var(--text-muted);
      line-height: 1.4;
    }
    .hero-actions {
      display: flex;
      flex-direction: column;
      gap: 8px;
      align-items: flex-end;
    }
    .copy-link-btn {
      padding: 6px 12px;
      border-radius: 8px;
      background: rgba(255, 255, 255, 0.08);
      border: 1px solid var(--border-color);
      color: #cbd5e1;
      font-size: 12px;
      font-weight: 600;
      cursor: pointer;
      display: flex;
      align-items: center;
      gap: 6px;
      transition: all 0.2s;
    }
    .copy-link-btn:hover {
      background: rgba(255, 255, 255, 0.16);
      color: #fff;
    }

    .step-section {
      padding: 28px 36px;
      border-bottom: 1px solid var(--border-color);
    }
    .step-section:last-child {
      border-bottom: none;
    }
    .section-title {
      font-family: var(--font-display);
      font-size: 16px;
      font-weight: 700;
      text-transform: uppercase;
      letter-spacing: 0.05em;
      color: #cbd5e1;
      margin-bottom: 16px;
      display: flex;
      align-items: center;
      gap: 10px;
    }
    .section-title span.num {
      width: 26px;
      height: 26px;
      border-radius: 50%;
      background: rgba(56, 189, 248, 0.15);
      color: var(--accent);
      display: flex;
      align-items: center;
      justify-content: center;
      font-size: 13px;
      font-weight: 800;
      border: 1px solid rgba(56, 189, 248, 0.3);
    }
    /* Grid Nhân sự */
    .host-grid {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
      gap: 14px;
    }
    .host-card {
      border: 1px solid var(--border-color);
      border-radius: 16px;
      padding: 16px;
      background: rgba(15, 23, 42, 0.6);
      cursor: pointer;
      transition: all 0.2s cubic-bezier(0.4, 0, 0.2, 1);
      display: flex;
      flex-direction: column;
      gap: 10px;
      position: relative;
    }
    .host-card-top {
      display: flex;
      align-items: center;
      gap: 14px;
    }
    .host-card:hover {
      background: var(--bg-card-hover);
      border-color: rgba(56, 189, 248, 0.4);
      transform: translateY(-2px);
    }
    .host-card.selected {
      border-color: var(--border-active);
      background: rgba(16, 185, 129, 0.12);
      box-shadow: 0 0 20px var(--primary-glow);
    }
    .avatar {
      width: 46px;
      height: 46px;
      border-radius: 50%;
      background: linear-gradient(135deg, #059669, #38bdf8);
      display: flex;
      align-items: center;
      justify-content: center;
      font-family: var(--font-display);
      font-weight: 800;
      font-size: 16px;
      color: #ffffff;
      flex-shrink: 0;
    }
    .host-info h4 {
      font-family: var(--font-display);
      font-size: 15px;
      font-weight: 700;
      color: #ffffff;
      margin-bottom: 2px;
    }
    .host-info p {
      font-size: 12px;
      color: var(--accent);
      font-weight: 600;
    }
    .host-bio {
      font-size: 12px;
      color: var(--text-muted);
      line-height: 1.4;
    }
    .host-direct-link {
      font-size: 11px;
      color: #64748b;
      margin-top: 4px;
      text-decoration: underline;
    }
    .host-direct-link:hover {
      color: var(--accent);
    }

    /* Duration Selector */
    .duration-chips {
      display: flex;
      gap: 10px;
      flex-wrap: wrap;
    }
    .chip {
      padding: 10px 20px;
      border-radius: 12px;
      border: 1px solid var(--border-color);
      background: rgba(15, 23, 42, 0.6);
      color: var(--text-muted);
      cursor: pointer;
      font-size: 14px;
      font-weight: 600;
      transition: all 0.2s;
    }
    .chip:hover {
      border-color: rgba(255, 255, 255, 0.2);
      color: #fff;
    }
    .chip.selected {
      background: var(--primary);
      color: #0b0f19;
      border-color: var(--primary);
      font-weight: 700;
      box-shadow: 0 0 16px var(--primary-glow);
    }
    /* Date Scroller */
    .date-scroller {
      display: flex;
      gap: 10px;
      overflow-x: auto;
      padding-bottom: 12px;
      scrollbar-width: thin;
    }
    .date-card {
      min-width: 110px;
      padding: 14px 10px;
      border-radius: 16px;
      border: 1px solid var(--border-color);
      background: rgba(15, 23, 42, 0.6);
      text-align: center;
      cursor: pointer;
      transition: all 0.2s;
      flex-shrink: 0;
    }
    .date-card:hover {
      border-color: rgba(56, 189, 248, 0.4);
    }
    .date-card.selected {
      border-color: var(--accent);
      background: rgba(56, 189, 248, 0.14);
      box-shadow: 0 0 16px var(--accent-glow);
    }
    .date-day {
      font-size: 12px;
      color: var(--text-muted);
      text-transform: uppercase;
      font-weight: 600;
      margin-bottom: 4px;
    }
    .date-num {
      font-family: var(--font-display);
      font-size: 18px;
      font-weight: 800;
      color: #ffffff;
    }
    /* Time Slots */
    .slots-container {
      margin-top: 14px;
    }
    .slot-group-title {
      font-size: 13px;
      color: #64748b;
      font-weight: 700;
      text-transform: uppercase;
      margin: 14px 0 8px;
    }
    .slots-grid {
      display: grid;
      grid-template-columns: repeat(auto-fill, minmax(130px, 1fr));
      gap: 10px;
    }
    .slot-btn {
      padding: 12px 10px;
      border-radius: 12px;
      border: 1px solid rgba(16, 185, 129, 0.3);
      background: rgba(16, 185, 129, 0.08);
      color: #34d399;
      font-size: 14px;
      font-weight: 700;
      cursor: pointer;
      text-align: center;
      transition: all 0.2s;
    }
    .slot-btn:hover {
      background: rgba(16, 185, 129, 0.2);
      border-color: #10b981;
      transform: translateY(-1px);
    }
    .slot-btn.selected {
      background: #10b981;
      color: #064e3b;
      border-color: #10b981;
      box-shadow: 0 0 16px var(--primary-glow);
    }
    .empty-slots {
      padding: 24px;
      text-align: center;
      color: var(--text-muted);
      font-size: 14px;
      background: rgba(15, 23, 42, 0.4);
      border-radius: 14px;
      border: 1px dashed var(--border-color);
    }
    /* Booking Form */
    .form-grid {
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 16px;
    }
    .full-width {
      grid-column: 1 / -1;
    }
    .input-group label {
      display: block;
      font-size: 13px;
      font-weight: 600;
      color: #cbd5e1;
      margin-bottom: 6px;
    }
    .input-group label span.req {
      color: #f43f5e;
    }
    .input-group input, .input-group textarea {
      width: 100%;
      background: rgba(15, 23, 42, 0.8);
      border: 1px solid var(--border-color);
      border-radius: 12px;
      padding: 12px 14px;
      color: #fff;
      font-family: var(--font-body);
      font-size: 14px;
      transition: all 0.2s;
    }
    .input-group input:focus, .input-group textarea:focus {
      outline: none;
      border-color: var(--accent);
      box-shadow: 0 0 0 3px rgba(56, 189, 248, 0.2);
    }
    .submit-btn {
      width: 100%;
      padding: 16px;
      background: linear-gradient(135deg, #10b981, #059669);
      color: #ffffff;
      border: none;
      border-radius: 14px;
      font-family: var(--font-display);
      font-size: 16px;
      font-weight: 700;
      cursor: pointer;
      transition: all 0.2s;
      box-shadow: 0 10px 25px -5px rgba(16, 185, 129, 0.4);
      display: flex;
      align-items: center;
      justify-content: center;
      gap: 10px;
    }
    .submit-btn:hover:not(:disabled) {
      background: linear-gradient(135deg, #059669, #047857);
      transform: translateY(-2px);
      box-shadow: 0 15px 30px -5px rgba(16, 185, 129, 0.6);
    }
    .submit-btn:disabled {
      opacity: 0.5;
      cursor: not-allowed;
    }
    /* Success Screen */
    .success-panel {
      padding: 48px 36px;
      text-align: center;
      display: none;
    }
    .success-icon {
      width: 72px;
      height: 72px;
      background: rgba(16, 185, 129, 0.15);
      border: 2px solid #10b981;
      border-radius: 50%;
      display: flex;
      align-items: center;
      justify-content: center;
      margin: 0 auto 24px;
      color: #10b981;
      font-size: 32px;
      box-shadow: 0 0 30px var(--primary-glow);
    }
    .meet-box {
      margin: 24px 0;
      padding: 20px;
      background: rgba(15, 23, 42, 0.8);
      border: 1px solid rgba(56, 189, 248, 0.3);
      border-radius: 16px;
    }
    .meet-link-btn {
      display: inline-flex;
      align-items: center;
      gap: 8px;
      padding: 12px 24px;
      background: #0284c7;
      color: #fff;
      text-decoration: none;
      font-weight: 700;
      border-radius: 12px;
      font-size: 15px;
      margin-top: 10px;
      transition: all 0.2s;
    }
    .meet-link-btn:hover {
      background: #0369a1;
      transform: translateY(-2px);
    }
    @media (max-width: 640px) {
      .header, .step-section { padding: 24px 20px; }
      .personal-hero { flex-direction: column; text-align: center; }
      .hero-actions { align-items: center; }
      .form-grid { grid-template-columns: 1fr; }
    }
  </style>
</head>
<body>

  <div class="container">
    <div class="header">
      <div class="badge-bar">
        <div class="badge">Google Calendar + Meet Tự Động</div>
        <a href="/" class="portal-link" id="switch-all-btn" style="display:none;">← Xem tất cả thành viên Thi Sen</a>
      </div>
      
      <h1 id="page-title">Đặt Lịch Hẹn — Thi Sen (Yên Phục)</h1>
      <p class="subtitle" id="page-subtitle">Chủ động chọn khung giờ hành chính còn trống để làm việc trực tiếp cùng Ban Điều Hành Thi Sen.</p>

      <!-- Personal Hero Profile (Tự động hiển thị khi vào link cá nhân) -->
      <div class="personal-hero" id="personal-hero" style="display: none;">
        <div class="hero-avatar" id="hero-avatar">HT</div>
        <div class="hero-info">
          <h2 id="hero-name">Họ Tên Nhân Sự</h2>
          <div class="hero-role" id="hero-role">Chức danh / Vai trò</div>
          <div class="hero-desc" id="hero-desc">Mô tả định hướng công việc và trao đổi chuyên môn.</div>
        </div>
        <div class="hero-actions">
          <button class="copy-link-btn" onclick="copyPersonalLink()" title="Sao chép link đặt lịch cá nhân">
            <span>📋</span> <span id="copy-btn-text">Sao chép link riêng</span>
          </button>
          <a href="#" target="_blank" id="google-schedule-link" class="portal-link" style="display:none; font-size:12px;">
            🔗 Mở Google Schedule
          </a>
        </div>
      </div>
    </div>

    <div id="booking-flow">
      <!-- BƯỚC 1: CHỌN NHÂN SỰ (Chỉ hiện khi ở Cổng chung) -->
      <div class="step-section" id="step-host-section">
        <div class="section-title"><span class="num">1</span> Chọn người bạn muốn gặp</div>
        <div class="host-grid" id="host-list">
          <!-- Render via JS -->
        </div>
      </div>

      <!-- BƯỚC 2: CHỌN THỜI LƯỢNG -->
      <div class="step-section">
        <div class="section-title"><span class="num">2</span> Thời lượng phiên gặp (mặc định 30 phút)</div>
        <div class="duration-chips">
          <div class="chip" data-min="15">15 phút</div>
          <div class="chip selected" data-min="30">30 phút (Khuyến nghị)</div>
          <div class="chip" data-min="45">45 phút</div>
          <div class="chip" data-min="60">60 phút</div>
        </div>
      </div>

      <!-- BƯỚC 3: CHỌN NGÀY & KHUNG GIỜ -->
      <div class="step-section">
        <div class="section-title"><span class="num">3</span> Chọn ngày & giờ hành chính còn trống</div>
        <div class="date-scroller" id="date-list">
          <!-- Render via JS -->
        </div>
        
        <div class="slots-container" id="slots-area">
          <div class="empty-slots">Đang tải các khung giờ khả dụng...</div>
        </div>
      </div>

      <!-- BƯỚC 4: THÔNG TIN KHÁCH MỜI -->
      <div class="step-section">
        <div class="section-title"><span class="num">4</span> Thông tin của bạn & Xác nhận</div>
        <form id="book-form" onsubmit="handleBook(event)">
          <div class="form-grid">
            <div class="input-group">
              <label>Họ và tên của bạn <span class="req">*</span></label>
              <input type="text" id="cust-name" required placeholder="Vd: Vũ Quang Đạt">
            </div>
            <div class="input-group">
              <label>Email nhận link Google Meet <span class="req">*</span></label>
              <input type="email" id="cust-email" required placeholder="Vd: dat@gmail.com">
            </div>
            <div class="input-group full-width">
              <label>Số điện thoại / Zalo</label>
              <input type="tel" id="cust-phone" placeholder="Vd: 0912 345 678">
            </div>
            <div class="input-group full-width">
              <label>Mục đích cuộc gặp <span class="req">*</span></label>
              <textarea id="cust-notes" rows="3" required placeholder="Vd: Trao đổi về kịch bản live TikTok và phân phối dòng sản phẩm Yên Phục..."></textarea>
            </div>
            <div class="full-width" style="margin-top: 12px;">
              <button type="submit" class="submit-btn" id="submit-btn">
                <span>🗓️ Xác Nhận Đặt Lịch & Tạo Google Meet</span>
              </button>
            </div>
          </div>
        </form>
      </div>
    </div>

    <!-- MÀN HÌNH THÀNH CÔNG -->
    <div class="success-panel" id="success-screen">
      <div class="success-icon">✓</div>
      <h2 style="font-family: var(--font-display); font-size: 26px; font-weight: 800; color: #fff; margin-bottom: 8px;">ĐẶT LỊCH THÀNH CÔNG!</h2>
      <p style="color: var(--text-muted); font-size: 15px;" id="success-msg">Cuộc hẹn của bạn đã được ghi nhận trên Google Calendar.</p>

      <div class="meet-box">
        <p style="font-size: 14px; color: #cbd5e1; margin-bottom: 6px;">🎥 <b>Đường link Google Meet chính thức:</b></p>
        <a href="#" target="_blank" class="meet-link-btn" id="meet-url">Vào phòng họp Google Meet</a>
      </div>

      <p style="font-size: 14px; color: #34d399; margin-bottom: 24px;">📧 Thư mời kèm link họp và file lịch đã được tự động gửi tới email của bạn.</p>

      <button onclick="location.reload()" class="chip selected" style="padding: 12px 28px; font-size: 15px;">Đặt thêm lịch khác</button>
    </div>
  </div>

  <script>
    let state = {
      hosts: [],
      selectedHost: null,
      isPersonalMode: false,
      duration: 30,
      selectedDate: null,
      selectedSlot: null,
      availableSlots: []
    };

    function parseSlugFromUrl() {
      const pathParts = window.location.pathname.replace(/^\\/|\\/$/g, '').split('/');
      if (pathParts.length === 2 && pathParts[0] === 'book') return pathParts[1].toLowerCase();
      if (pathParts.length === 1 && pathParts[0] !== '' && pathParts[0] !== 'book' && pathParts[0] !== 'index.html') {
        return pathParts[0].toLowerCase();
      }
      return null;
    }

    async function init() {
      try {
        const res = await fetch('/api/config');
        const data = await res.json();
        state.hosts = data.hosts;

        const slug = parseSlugFromUrl();
        const matchedHost = state.hosts.find(h => (h.slug && h.slug.toLowerCase() === slug) || (h.id && h.id.toLowerCase() === slug));

        if (matchedHost) {
          state.isPersonalMode = true;
          state.selectedHost = matchedHost.slug || matchedHost.id;
          setupPersonalMode(matchedHost);
        } else {
          state.isPersonalMode = false;
          if (state.hosts.length > 0) state.selectedHost = state.hosts[0].slug || state.hosts[0].id;
          document.getElementById('step-host-section').style.display = 'block';
          renderHosts();
        }

        renderDates();
      } catch (err) {
        console.error('Init error:', err);
      }
    }

    function setupPersonalMode(host) {
      document.getElementById('step-host-section').style.display = 'none';
      document.getElementById('switch-all-btn').style.display = 'inline-block';
      document.getElementById('page-title').innerText = `Đặt Lịch Gặp: ${host.ten}`;
      document.getElementById('page-subtitle').innerText = `Trang đặt lịch làm việc chính thức cùng ${host.ten} (${host.chuc_danh}).`;

      const hero = document.getElementById('personal-hero');
      hero.style.display = 'flex';
      document.getElementById('hero-avatar').innerText = host.avatar_text || host.ten.charAt(0);
      document.getElementById('hero-name').innerText = host.ten;
      document.getElementById('hero-role').innerText = host.chuc_danh;
      document.getElementById('hero-desc').innerText = host.mo_ta || `Trao đổi chuyên môn trực tiếp qua Google Meet.`;

      if (host.link_google_booking) {
        const gLink = document.getElementById('google-schedule-link');
        gLink.href = host.link_google_booking;
        gLink.style.display = 'inline-block';
      }
    }

    function copyPersonalLink() {
      const url = window.location.origin + '/book/' + state.selectedHost;
      navigator.clipboard.writeText(url).then(() => {
        const btnText = document.getElementById('copy-btn-text');
        const old = btnText.innerText;
        btnText.innerText = 'Đã sao chép link!';
        setTimeout(() => { btnText.innerText = old; }, 2000);
      }).catch(err => {
        prompt('Copy link đặt lịch cá nhân này:', url);
      });
    }

    function renderHosts() {
      const container = document.getElementById('host-list');
      container.innerHTML = state.hosts.map(h => {
        const hostId = h.slug || h.id;
        const isSel = hostId === state.selectedHost;
        return `
          <div class="host-card ${isSel ? 'selected' : ''}" onclick="selectHost('${hostId}')">
            <div class="host-card-top">
              <div class="avatar">${h.avatar_text || h.ten.charAt(0)}</div>
              <div class="host-info">
                <h4>${h.ten}</h4>
                <p>${h.chuc_danh}</p>
              </div>
            </div>
            <div class="host-bio">${h.mo_ta || ''}</div>
            <a href="/book/${hostId}" class="host-direct-link" onclick="event.stopPropagation()">🔗 Mở link riêng (/book/${hostId})</a>
          </div>
        `;
      }).join('');
    }

    function selectHost(id) {
      state.selectedHost = id;
      renderHosts();
      fetchSlots();
    }

    // Duration chips
    document.querySelectorAll('.chip').forEach(el => {
      el.addEventListener('click', () => {
        document.querySelectorAll('.chip').forEach(c => c.classList.remove('selected'));
        el.classList.add('selected');
        state.duration = parseInt(el.getAttribute('data-min'));
        fetchSlots();
      });
    });

    function renderDates() {
      const container = document.getElementById('date-list');
      const dates = [];
      const today = new Date();
      
      let d = new Date(today);
      d.setDate(d.getDate() + 1); // Bắt đầu từ ngày mai
      while (dates.length < 7) {
        const dayOfWeek = d.getDay();
        if (dayOfWeek !== 0) { // Loại Chủ Nhật
          dates.push(new Date(d));
        }
        d.setDate(d.getDate() + 1);
      }

      const dayNames = ['CN', 'T2', 'T3', 'T4', 'T5', 'T6', 'T7'];
      container.innerHTML = dates.map((dt, idx) => {
        const iso = dt.toISOString().split('T')[0];
        const isSel = idx === 0;
        if (isSel) state.selectedDate = iso;
        return `
          <div class="date-card ${isSel ? 'selected' : ''}" data-date="${iso}" onclick="selectDate('${iso}')">
            <div class="date-day">${dayNames[dt.getDay()]}</div>
            <div class="date-num">${dt.getDate()}/${dt.getMonth() + 1}</div>
          </div>
        `;
      }).join('');

      fetchSlots();
    }

    function selectDate(iso) {
      state.selectedDate = iso;
      document.querySelectorAll('.date-card').forEach(el => {
        el.classList.toggle('selected', el.getAttribute('data-date') === iso);
      });
      fetchSlots();
    }

    async function fetchSlots() {
      const area = document.getElementById('slots-area');
      area.innerHTML = '<div class="empty-slots">Đang quét khung giờ hành chính còn trống trên Google Calendar...</div>';
      state.selectedSlot = null;
      
      try {
        const res = await fetch(`/api/slots?ngay=${state.selectedDate}&thoi_luong=${state.duration}&nguoi=${state.selectedHost}`);
        const data = await res.json();
        state.availableSlots = data.slots || [];
        renderSlots();
      } catch (err) {
        area.innerHTML = '<div class="empty-slots" style="color:#f43f5e;">Lỗi kết nối kiểm tra lịch. Vui lòng thử lại.</div>';
      }
    }

    function renderSlots() {
      const area = document.getElementById('slots-area');
      if (state.availableSlots.length === 0) {
        area.innerHTML = '<div class="empty-slots">Không còn khung giờ trống trong ngày này. Vui lòng chọn ngày khác.</div>';
        return;
      }

      const morning = state.availableSlots.filter(s => s.buoi === 'Sáng');
      const afternoon = state.availableSlots.filter(s => s.buoi === 'Chiều');

      let html = '';
      if (morning.length > 0) {
        html += '<div class="slot-group-title">🌅 Buổi Sáng (08:30 – 12:00)</div><div class="slots-grid">';
        html += morning.map(s => `
          <div class="slot-btn ${state.selectedSlot === s.bat_dau ? 'selected' : ''}" onclick="selectSlot('${s.bat_dau}')">
            ${s.gio_bat_dau} - ${s.gio_ket_thuc}
          </div>
        `).join('');
        html += '</div>';
      }

      if (afternoon.length > 0) {
        html += '<div class="slot-group-title">🌇 Buổi Chiều (13:30 – 17:30)</div><div class="slots-grid">';
        html += afternoon.map(s => `
          <div class="slot-btn ${state.selectedSlot === s.bat_dau ? 'selected' : ''}" onclick="selectSlot('${s.bat_dau}')">
            ${s.gio_bat_dau} - ${s.gio_ket_thuc}
          </div>
        `).join('');
        html += '</div>';
      }

      area.innerHTML = html;
    }

    function selectSlot(iso) {
      state.selectedSlot = iso;
      renderSlots();
    }

    async function handleBook(e) {
      e.preventDefault();
      if (!state.selectedSlot) {
        alert('Vui lòng bấm chọn một khung giờ còn trống (màu xanh)!');
        return;
      }

      const btn = document.getElementById('submit-btn');
      btn.disabled = true;
      btn.innerHTML = '⏳ Đang tạo Google Meet & gửi thư mời...';

      const payload = {
        bat_dau: state.selectedSlot,
        thoi_luong: state.duration,
        nguoi: state.selectedHost,
        khach_ten: document.getElementById('cust-name').value.trim(),
        khach_email: document.getElementById('cust-email').value.trim(),
        khach_sdt: document.getElementById('cust-phone').value.trim(),
        noi_dung: document.getElementById('cust-notes').value.trim()
      };

      try {
        const res = await fetch('/api/book', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(payload)
        });
        const result = await res.json();
        
        if (res.ok && result.ok) {
          document.getElementById('booking-flow').style.display = 'none';
          document.getElementById('success-screen').style.display = 'block';
          document.getElementById('success-msg').innerText = `Lịch hẹn "${result.tieu_de}" đã được xác nhận vào lúc ${result.bat_dau_hien_thi}.`;
          const meetBtn = document.getElementById('meet-url');
          if (result.link_meet) {
            meetBtn.href = result.link_meet;
            meetBtn.innerText = `🎥 Vào Google Meet: ${result.link_meet}`;
          } else {
            meetBtn.style.display = 'none';
          }
        } else {
          alert('Không thể đặt lịch: ' + (result.error || 'Vui lòng kiểm tra lại.'));
          btn.disabled = false;
          btn.innerHTML = '🗓️ Xác Nhận Đặt Lịch & Tạo Google Meet';
        }
      } catch (err) {
        alert('Lỗi kết nối máy chủ đặt lịch: ' + err.message);
        btn.disabled = false;
        btn.innerHTML = '🗓️ Xác Nhận Đặt Lịch & Tạo Google Meet';
      }
    }

    window.onload = init;
  </script>
</body>
</html>
"""


class BookingHTTPHandler(BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        pass  # Không in log ồn ào

    def _gui_json(self, status: int, data: dict):
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(json.dumps(data, ensure_ascii=False).encode("utf-8"))

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def do_GET(self):
        pr = urllib.parse.urlparse(self.path)
        path = pr.path.strip("/")
        parts = path.split("/") if path else []

        # Kiểm tra xem có phải route booking page không (Portal hoặc Trang cá nhân)
        # Các mẫu: "", "book", "index.html", "book/<slug>", "<slug>"
        is_page = False
        if path in ("", "book", "index.html"):
            is_page = True
        elif len(parts) == 2 and parts[0] == "book":
            is_page = True
        elif len(parts) == 1 and parts[0] in ("hung", "trang", "nhung", "thuy"):
            is_page = True

        if is_page:
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            self.wfile.write(HTML_TEMPLATE.encode("utf-8"))
            return

        if path == "api/config":
            cfg = lich.doc_cau_hinh()
            hosts = khe_trong.lay_danh_sach_nhan_su(cfg)
            self._gui_json(200, {"hosts": hosts, "durations": [15, 30, 45, 60], "default_duration": 30})
            return

        if path == "api/slots":
            qs = urllib.parse.parse_qs(pr.query)
            str_ngay = qs.get("ngay", [None])[0]
            thoi_luong = int(qs.get("thoi_luong", [30])[0])
            nguoi = qs.get("nguoi", [None])[0]

            cfg = lich.doc_cau_hinh()
            sv = lich.dich_vu()
            
            ngay_goc = date.fromisoformat(str_ngay) if str_ngay else datetime.now(MUI_GIO).date()
            slots = khe_trong.tim_khe_trong(sv, cfg, bat_dau_ngay=ngay_goc, so_ngay=1,
                                            thoi_luong_phut=thoi_luong, nguoi_email=nguoi)
            self._gui_json(200, {"slots": slots})
            return

        self.send_response(404)
        self.end_headers()

    def do_POST(self):
        pr = urllib.parse.urlparse(self.path)
        path = pr.path.strip("/")
        if path == "api/book":
            len_head = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(len_head).decode("utf-8")
            try:
                data = json.loads(body)
                cfg = lich.doc_cau_hinh()
                sv = lich.dich_vu()

                ket_qua = khe_trong.dat_lich_cong_khai(
                    sv=sv,
                    cfg=cfg,
                    bat_dau_iso=data["bat_dau"],
                    thoi_luong_phut=int(data.get("thoi_luong", 30)),
                    nguoi_tiep_don=data.get("nguoi", "hung"),
                    khach_ten=data["khach_ten"],
                    khach_email=data["khach_email"],
                    khach_sdt=data.get("khach_sdt", ""),
                    noi_dung=data.get("noi_dung", "Trao đổi công việc")
                )

                dt_bd = datetime.fromisoformat(ket_qua["bat_dau"])
                bat_dau_hien_thi = f"{dt_bd.strftime('%H:%M')} ngày {dt_bd.strftime('%d/%m/%Y')}"

                self._gui_json(200, {
                    "ok": True,
                    "tieu_de": ket_qua["tieu_de"],
                    "bat_dau_hien_thi": bat_dau_hien_thi,
                    "link_meet": ket_qua.get("link_meet"),
                    "link_lich": ket_qua.get("link_lich"),
                    "nguoi_tiep_don": ket_qua["nguoi_tiep_don"],
                    "email_tiep_don": ket_qua["email_tiep_don"]
                })
            except Exception as e:
                self._gui_json(400, {"ok": False, "error": str(e)})
            return

        self.send_response(404)
        self.end_headers()


def chay_server(port: int = 8092):
    server = HTTPServer(("0.0.0.0", port), BookingHTTPHandler)
    print(f"🚀 CỔNG ĐẶT LỊCH THI SEN ĐANG CHẠY TẠI: http://localhost:{port}/")
    print(f"👉 Link trang chung:   http://localhost:{port}/")
    print(f"👉 Link riêng anh Hùng: http://localhost:{port}/book/hung")
    print(f"👉 Link riêng chị Trang: http://localhost:{port}/book/trang")
    print(f"👉 Link riêng Nhung:     http://localhost:{port}/book/nhung")
    print(f"👉 Link riêng Thúy:     http://localhost:{port}/book/thuy")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n🛑 Đã dừng máy chủ đặt lịch.")


if __name__ == "__main__":
    p = 8092
    if len(sys.argv) > 1 and sys.argv[1].isdigit():
        p = int(sys.argv[1])
    chay_server(p)
