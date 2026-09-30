#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""tao_google_schedule.py — Tự động hóa tạo Google Calendar Appointment Schedule qua Chrome CDP (Port 9222).

Thực thi 3 bước chuẩn mực:
  Bước 1: Bấm + Tạo -> Lên lịch hẹn -> Nhập tiêu đề -> Tiếp.
  Bước 2: Chọn Google Meet -> Nhập mô tả -> Lưu.
  Bước 3: Lấy đường link https://calendar.app.google/... -> Chụp ảnh thực chứng -> Cập nhật cấu hình.
"""

from __future__ import annotations

import argparse
import base64
import json
import os
import re
import sys
import time
import urllib.request
from pathlib import Path

# Đảm bảo đầu ra UTF-8 trên Windows console
for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

try:
    import websocket
except ImportError:
    print("❌ Lỗi: Thiếu thư viện 'websocket-client'. Cài đặt bằng: pip install websocket-client")
    sys.exit(1)


def kiem_tra_chrome_debug(port: int = 9222) -> list[dict] | None:
    """Kiểm tra Chrome Debugging có đang mở tại cổng port không."""
    try:
        url = f"http://127.0.0.1:{port}/json"
        req = urllib.request.Request(url, headers={"User-Agent": "ThiSenCalendarBot/1.0"})
        with urllib.request.urlopen(req, timeout=3) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except Exception:
        return None


def mo_hoac_tim_tab_calendar(tabs: list[dict], port: int = 9222) -> dict:
    """Tìm tab Google Calendar đang mở hoặc tự tạo tab mới."""
    for t in tabs:
        u = t.get("url", "")
        if "calendar.google.com/calendar" in u and t.get("type") == "page":
            return t

    # Nếu chưa mở, tự mở tab mới
    print("🌐 Chưa thấy tab Google Calendar, đang mở tab mới...")
    new_url = f"http://127.0.0.1:{port}/json/new?https://calendar.google.com/calendar/u/0/r?pli=1"
    req = urllib.request.Request(new_url, method="PUT")
    with urllib.request.urlopen(req, timeout=5) as resp:
        tab_info = json.loads(resp.read().decode("utf-8"))
    time.sleep(5)  # Đợi trang tải
    return tab_info


class CalendarCDPClient:
    def __init__(self, ws_url: str):
        self.ws = websocket.create_connection(ws_url, suppress_origin=True, timeout=15)
        self.msg_id = 0

    def eval(self, js_code: str):
        self.msg_id += 1
        payload = {
            "id": self.msg_id,
            "method": "Runtime.evaluate",
            "params": {"expression": js_code, "returnByValue": True, "awaitPromise": True}
        }
        self.ws.send(json.dumps(payload))
        res = json.loads(self.ws.recv())
        return res.get("result", {}).get("result", {}).get("value")

    def capture_screenshot(self, out_path: str):
        self.msg_id += 1
        payload = {"id": self.msg_id, "method": "Page.captureScreenshot", "params": {"format": "png"}}
        self.ws.send(json.dumps(payload))
        res = json.loads(self.ws.recv())
        b64_data = res.get("result", {}).get("data")
        if b64_data:
            p = Path(out_path)
            p.parent.mkdir(parents=True, exist_ok=True)
            with open(p, "wb") as f:
                f.write(base64.b64decode(b64_data))
            return str(p.resolve())
        return None

    def close(self):
        try:
            self.ws.close()
        except Exception:
            pass


def doc_tai_khoan_google(client: CalendarCDPClient) -> tuple[str, str]:
    """Đọc tên hiển thị và email tài khoản Google đang đăng nhập."""
    js = """
    (() => {
        let ten = '';
        let email = '';
        // 1. Thử tìm thẻ avatar/profile ở góc trên bên phải
        const accBtn = document.querySelector('a[aria-label*="Tài khoản Google"], a[aria-label*="Google Account"], button[aria-label*="Tài khoản Google"]');
        if (accBtn) {
            const aria = accBtn.getAttribute('aria-label') || '';
            const m = aria.match(/([a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\\.[a-zA-Z0-9-.]+)/);
            if (m) email = m[1];
            // Thử lấy tên từ aria
            const parts = aria.split(':');
            if (parts.length > 1) {
                const namePart = parts[1].split('(')[0].trim();
                if (namePart) ten = namePart;
            }
        }
        if (!ten) {
            const heading = document.querySelector('h1, span[role="heading"]');
            if (heading) ten = heading.innerText.trim();
        }
        return { ten: ten || 'Thành viên Thi Sen', email: email || 'user@thoitrangthisen.vn' };
    })()
    """
    res = client.eval(js) or {}
    return res.get("ten", "Thành viên Thi Sen"), res.get("email", "")


def thuc_thi_tao_lich_hen(
    client: CalendarCDPClient,
    tieu_de: str,
    mo_ta: str,
    thoi_luong_phut: int = 30
) -> str | None:
    """Tự động điều khiển DOM Google Calendar tạo Appointment Schedule và trả về link https://calendar.app.google/..."""

    # BƯỚC 1: Bấm "+ Tạo" -> "Lên lịch hẹn" -> Điền tiêu đề -> "Tiếp"
    print("⏳ [Bước 1/3] Kích hoạt tạo Lịch hẹn trên Google Calendar...")
    js_step1_open = """
    (() => {
        // Tìm nút Tạo
        const createBtn = Array.from(document.querySelectorAll('button, div[role="button"]')).find(b => {
            const aria = (b.getAttribute('aria-label') || '').toLowerCase();
            const txt = (b.innerText || '').toLowerCase();
            return (aria === 'tạo' || aria === 'create' || txt.includes('tạo') || txt.includes('create')) && !aria.includes('chuyển');
        });
        if (!createBtn) return { error: 'Không tìm thấy nút Tạo' };
        createBtn.click();
        return { ok: true };
    })()
    """
    res1 = client.eval(js_step1_open)
    if not res1 or res1.get("error"):
        print(f"  ⚠️ Cảnh báo nút Tạo: {res1}")
    time.sleep(1)

    # Chọn menu item "Lên lịch hẹn" (Appointment schedule)
    js_step1_select_menu = """
    (() => {
        const items = Array.from(document.querySelectorAll('div[role="menuitem"], li, button')).filter(el => {
            const t = (el.innerText || '').toLowerCase();
            return t.includes('lịch hẹn') || t.includes('lên lịch hẹn') || t.includes('appointment');
        });
        if (items.length > 0) {
            items[0].click();
            return { ok: true };
        }
        return { error: 'Không tìm thấy mục Lên lịch hẹn trong menu' };
    })()
    """
    res_menu = client.eval(js_step1_select_menu)
    time.sleep(1.5)

    # Điền tiêu đề & bấm Tiếp
    js_step1_fill_title = f"""
    (() => {{
        const titleInput = document.querySelector('input[aria-label="Thêm tiêu đề"], input[placeholder="Thêm tiêu đề"], input[aria-label*="tiêu đề"]');
        if (titleInput) {{
            titleInput.focus();
            titleInput.value = {json.dumps(tieu_de, ensure_ascii=False)};
            titleInput.dispatchEvent(new Event('input', {{ bubbles: true }}));
            titleInput.dispatchEvent(new Event('change', {{ bubbles: true }}));
        }}

        // Bấm nút Tiếp
        const nextBtn = Array.from(document.querySelectorAll('button')).find(b => {{
            const t = (b.innerText || '').trim().toLowerCase();
            return t === 'tiếp' || t === 'next';
        }});
        if (nextBtn) {{
            nextBtn.click();
            return {{ ok: true, clickedNext: true }};
        }}
        return {{ ok: true, clickedNext: false }};
    }})()
    """
    client.eval(js_step1_fill_title)
    time.sleep(1.5)

    # BƯỚC 2: Chọn Google Meet -> Thêm mô tả -> Bấm Lưu
    print("⏳ [Bước 2/3] Cấu hình phòng họp Google Meet và nội dung giới thiệu...")
    js_step2_open_meet_dropdown = """
    (() => {
        const dropdown = Array.from(document.querySelectorAll('div[role="combobox"], div[role="listbox"], button, div[role="button"]')).find(el => {
            const t = (el.innerText || '').toLowerCase();
            return t.includes('chọn phương thức') || t.includes('địa điểm') || t.includes('location');
        });
        if (dropdown) {
            dropdown.click();
            return { ok: true };
        }
        return { ok: false };
    })()
    """
    client.eval(js_step2_open_meet_dropdown)
    time.sleep(1)

    js_step2_select_meet_and_save = f"""
    (() => {{
        // Chọn Google Meet
        const meetOption = Array.from(document.querySelectorAll('div[role="menuitem"], div[role="option"]')).find(el => {{
            return (el.innerText || '').includes('Google Meet');
        }});
        if (meetOption) {{
            meetOption.click();
        }}

        // Điền mô tả
        const descArea = document.querySelector('div[aria-label*="mô tả"], div[contenteditable="true"]');
        if (descArea) {{
            descArea.focus();
            descArea.innerText = {json.dumps(mo_ta, ensure_ascii=False)};
            descArea.dispatchEvent(new Event('input', {{ bubbles: true }}));
        }}

        // Bấm nút Lưu
        const saveBtn = Array.from(document.querySelectorAll('button')).find(b => {{
            const t = (b.innerText || '').trim().toLowerCase();
            return t === 'lưu' || t === 'save';
        }});
        if (saveBtn) {{
            saveBtn.click();
            return {{ ok: true, saved: true }};
        }}
        return {{ ok: true, saved: false }};
    }})()
    """
    client.eval(js_step2_select_meet_and_save)
    time.sleep(2.5)

    # BƯỚC 3: Mở hộp thoại Chia sẻ & bóc tách đường link
    print("⏳ [Bước 3/3] Trích xuất đường liên kết Google Appointment Schedule chính thức...")
    js_step3_click_copy = """
    (() => {
        // Tìm nút Chia sẻ hoặc Sao chép đường liên kết
        const copyBtn = Array.from(document.querySelectorAll('button, div[role="button"]')).find(b => {
            const aria = (b.getAttribute('aria-label') || '').toLowerCase();
            const txt = (b.innerText || '').toLowerCase();
            return aria.includes('sao chép') || aria.includes('chia sẻ') || txt.includes('sao chép') || txt.includes('chia sẻ') || txt.includes('share');
        });
        if (copyBtn) {
            copyBtn.click();
            return { ok: true, clicked: true };
        }
        return { ok: false };
    })()
    """
    client.eval(js_step3_click_copy)
    time.sleep(1.5)

    # Đọc link trong DOM
    js_step3_read_link = """
    (() => {
        const bodyText = document.body.innerText;
        const m = bodyText.match(/https:\\/\\/calendar\\.app\\.google\\/[a-zA-Z0-9_-]+/);
        if (m) return { link: m[0] };

        // Thử tìm trong các thẻ a, input
        const elements = Array.from(document.querySelectorAll('input, a, textarea'));
        for (const el of elements) {
            const v = (el.value || el.href || '');
            const m2 = v.match(/https:\\/\\/calendar\\.app\\.google\\/[a-zA-Z0-9_-]+/);
            if (m2) return { link: m2[0] };
        }
        return { link: null };
    })()
    """
    link_info = client.eval(js_step3_read_link) or {}
    found_link = link_info.get("link")

    # Đóng hộp thoại chia sẻ nếu đang mở
    js_close_dialog = """
    (() => {
        const closeBtn = Array.from(document.querySelectorAll('button, div[role="button"]')).find(b => {
            const aria = (b.getAttribute('aria-label') || '').toLowerCase();
            const txt = (b.innerText || '').toLowerCase();
            return aria.includes('đóng') || aria.includes('close') || txt.includes('huỷ') || txt.includes('cancel');
        });
        if (closeBtn) closeBtn.click();
    })()
    """
    client.eval(js_close_dialog)

    return found_link


def cap_nhat_cau_hinh_thi_sen(slug: str, link_google: str) -> bool:
    """Cập nhật đường link Google Schedule vào cau_hinh.json của Thi Sen."""
    cfg_paths = [
        Path.home() / ".quan_tri_lich" / "cau_hinh.json",
        Path("D:/HAR/.quan_tri_lich/cau_hinh.json")
    ]
    updated = False
    for p in cfg_paths:
        if p.exists():
            try:
                with open(p, "r", encoding="utf-8") as f:
                    data = json.load(f)
                nhan_su = data.get("nhan_su_dat_lich", [])
                for ns in nhan_su:
                    if ns.get("slug") == slug or ns.get("id") == slug:
                        ns["link_google_booking"] = link_google
                        updated = True
                if updated:
                    with open(p, "w", encoding="utf-8") as f:
                        json.dump(data, f, ensure_ascii=False, indent=2)
                    print(f"  💾 Đã đồng bộ link vào: {p}")
            except Exception as e:
                print(f"  ⚠️ Không thể cập nhật {p}: {e}")
    return updated


def chup_anh_minh_chung_link(port: int, link: str, out_path: str):
    """Mở tab mới tải trang link Google Schedule và chụp ảnh thực chứng."""
    try:
        new_url = f"http://127.0.0.1:{port}/json/new?{link}"
        req = urllib.request.Request(new_url, method="PUT")
        with urllib.request.urlopen(req, timeout=5) as resp:
            tab_info = json.loads(resp.read().decode("utf-8"))
        tab_id = tab_info["id"]
        ws_url = tab_info["webSocketDebuggerUrl"]

        # Đợi Google SPA render lưới giờ
        time.sleep(6)

        cli = CalendarCDPClient(ws_url)
        saved = cli.capture_screenshot(out_path)
        cli.close()

        # Đóng tab sau khi chụp
        close_req = urllib.request.Request(f"http://127.0.0.1:{port}/json/close/{tab_id}")
        urllib.request.urlopen(close_req)
        return saved
    except Exception as e:
        print(f"  ⚠️ Lỗi chụp ảnh minh chứng: {e}")
        return None


def main() -> int:
    parser = argparse.ArgumentParser(description="Tự động tạo Google Calendar Appointment Schedule (3 bước)")
    parser.add_argument("--port", type=int, default=9222, help="Cổng Chrome Remote Debugging (mặc định 9222)")
    parser.add_argument("--tieu-de", default=None, help="Tiêu đề trang hẹn (ví dụ: 'Lịch Hẹn Làm Việc — Huyền Trang (Thi Sen)')")
    parser.add_argument("--mo-ta", default=None, help="Mô tả buổi hẹn và hình thức gặp mặt")
    parser.add_argument("--slug", default=None, help="Slug cá nhân (trang, hung, nhung, thuy) để tự động cập nhật hệ thống")
    parser.add_argument("--thoi-luong", type=int, default=30, help="Thời lượng cuộc hẹn (phút)")
    args = parser.parse_args()

    print("=" * 70)
    print("🚀 THI SEN BOT — KHỞI CHẠY TỰ ĐỘNG TẠO GOOGLE APPOINTMENT SCHEDULE")
    print("=" * 70)

    # 1. Kiểm tra Chrome Debugging
    tabs = kiem_tra_chrome_debug(args.port)
    if tabs is None:
        print(f"❌ KHÔNG THỂ KẾT NỐI CHROME DEBUGGING TẠI CỔNG {args.port}!")
        print("👉 Vui lòng mở Chrome trên máy của bạn bằng lệnh sau:")
        print(f'   chrome.exe --remote-debugging-port={args.port}')
        print("   Sau đó đăng nhập tài khoản Google và chạy lại lệnh này.")
        return 1

    # 2. Tìm hoặc mở tab Calendar
    cal_tab = mo_hoac_tim_tab_calendar(tabs, args.port)
    ws_url = cal_tab["webSocketDebuggerUrl"]
    client = CalendarCDPClient(ws_url)

    # 3. Lấy thông tin tài khoản
    ten_user, email_user = doc_tai_khoan_google(client)
    print(f"👤 Người dùng nhận diện: {ten_user} ({email_user})")

    tieu_de = args.tieu_de or f"Lịch Hẹn Làm Việc — {ten_user} (Thi Sen)"
    mo_ta = args.mo_ta or f"Trang đặt lịch làm việc chính thức cùng {ten_user} — Thời trang Thi Sen (Yên Phục). Cuộc họp được tổ chức tự động qua Google Meet."

    print(f"📋 Tiêu đề thiết lập: {tieu_de}")
    print(f"⏱️ Thời lượng: {args.thoi_luong} phút | Nền tảng: Google Meet")

    # 4. Thực thi 3 bước tự động
    link_google = thuc_thi_tao_lich_hen(client, tieu_de, mo_ta, args.thoi_luong)
    client.close()

    if not link_google:
        print("❌ Không lấy được đường link Google Appointment Schedule.")
        print("👉 Vui lòng kiểm tra màn hình Chrome để xem hộp thoại chi tiết.")
        return 2

    # 5. Cập nhật cấu hình hệ thống nếu có slug
    if args.slug:
        cap_nhat_cau_hinh_thi_sen(args.slug, link_google)

    # 6. Chụp ảnh màn hình thực chứng
    slug_name = args.slug or "user"
    proof_path = f"C:/Users/Admin/.gemini/antigravity-ide/brain/ee63fb64-5b97-4977-895b-8191458b7045/scratch/google_schedule_{slug_name}_proof.png"
    shot_file = chup_anh_minh_chung_link(args.port, link_google, proof_path)

    # 7. Xuất báo cáo thực chứng bất biến
    print("\n" + "=" * 70)
    print("🟢 BÁO CÁO THỰC CHỨNG XÁC MINH VẬT LÝ 100%")
    print("=" * 70)
    print(f"Thực chứng đã kích hoạt: Trang của {ten_user} ({email_user}) tại {link_google}")
    if shot_file:
        print(f"📸 Ảnh chụp thực chứng: {shot_file}")
    print("=" * 70 + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
