# -*- coding: utf-8 -*-
"""khe_trong.py — Quản lý khung giờ hành chính còn trống & Cổng đặt lịch tự động."""

from __future__ import annotations

import json
import os
import re
import sys
import uuid
from datetime import datetime, date, time, timedelta, timezone
from pathlib import Path

MUI_GIO = timezone(timedelta(hours=7))
THU_VIET = {1: "Thứ Hai", 2: "Thứ Ba", 3: "Thứ Tư", 4: "Thứ Năm", 5: "Thứ Sáu", 6: "Thứ Bảy", 7: "Chủ Nhật"}


def doc_gio_hanh_chinh(cfg: dict) -> dict:
    ghc = cfg.get("gio_hanh_chinh", {})
    return {
        "sang": ghc.get("sang", {"tu": "08:30", "den": "12:00"}),
        "chieu": ghc.get("chieu", {"tu": "13:30", "den": "17:30"}),
        "thu_lam_viec": ghc.get("thu_lam_viec", [1, 2, 3, 4, 5]),  # T2 đến T6
        "thoi_luong_mac_dinh": ghc.get("thoi_luong_mac_dinh", 30),
        "buoc_nhay_phut": ghc.get("buoc_nhay_phut", 30),
        "dem_truoc_phut": ghc.get("dem_truoc_phut", 60),  # Không cho đặt sát giờ (< 60 phút)
    }


def _parse_hhmm(s: str) -> time:
    parts = s.strip().split(":")
    return time(int(parts[0]), int(parts[1]))


def lay_danh_sach_nhan_su(cfg: dict) -> list[dict]:
    """Trả về danh sách nhân sự công ty cho phép người ngoài đặt lịch."""
    danh_ba = cfg.get("danh_ba", {})
    
    # Cấu hình tuỳ biến nếu có khai
    cau_hinh_ns = cfg.get("nhan_su_dat_lich")
    if cau_hinh_ns:
        for ns in cau_hinh_ns:
            ns["id"] = ns.get("slug") or ns.get("id")
            ns["slug"] = ns["id"]
        return cau_hinh_ns

    # Mặc định lấy từ danh bạ công ty
    mac_dinh = [
        {"id": "trang", "ten": "Huyền Trang", "chuc_danh": "CEO & Sáng lập Thi Sen", "email": "huyentrangfsh@gmail.com"},
        {"id": "hung", "ten": "Dương Mạnh Hùng", "chuc_danh": "Quản trị Công nghệ & Hệ thống", "email": "duonghung@gmail.com"}
    ]
    # Bổ sung thêm các nhân sự khác có trong danh bạ
    ds_id = {ns["id"] for ns in mac_dinh}
    for ten, email in danh_ba.items():
        k = ten.lower().strip()
        if k not in ds_id and email not in [ns["email"] for ns in mac_dinh]:
            mac_dinh.append({
                "id": k,
                "ten": ten.title(),
                "chuc_danh": "Thành viên Ban Điều Hành",
                "email": email
            })
    return mac_dinh


def tim_khe_trong(sv, cfg: dict, bat_dau_ngay: date | None = None, so_ngay: int = 7,
                   thoi_luong_phut: int = 30, nguoi_email: str | None = None) -> list[dict]:
    """Tìm toàn bộ khung giờ hành chính còn trống trên Google Calendar."""
    ghc = doc_gio_hanh_chinh(cfg)
    thoi_luong = thoi_luong_phut or ghc["thoi_luong_mac_dinh"]
    buoc_nhay = ghc["buoc_nhay_phut"]
    dem_truoc = ghc["dem_truoc_phut"]

    bay_gio = datetime.now(MUI_GIO)
    ngay_goc = bat_dau_ngay or bay_gio.date()

    t_min = datetime.combine(ngay_goc, time(0, 0, 0), tzinfo=MUI_GIO)
    t_max = datetime.combine(ngay_goc + timedelta(days=so_ngay), time(23, 59, 59), tzinfo=MUI_GIO)

    lich_id = cfg.get("lich_id", "primary")
    events = sv.events().list(
        calendarId=lich_id,
        timeMin=t_min.isoformat(),
        timeMax=t_max.isoformat(),
        singleEvents=True,
        orderBy="startTime",
    ).execute().get("items", [])

    busy_spans = []
    for e in events:
        bd = e["start"].get("dateTime") or e["start"].get("date")
        kt = e["end"].get("dateTime") or e["end"].get("date")
        if bd and kt:
            try:
                dt_bd = datetime.fromisoformat(bd) if "T" in bd else datetime.combine(date.fromisoformat(bd), time(0, 0), tzinfo=MUI_GIO)
                dt_kt = datetime.fromisoformat(kt) if "T" in kt else datetime.combine(date.fromisoformat(kt), time(23, 59, 59), tzinfo=MUI_GIO)
                busy_spans.append((dt_bd, dt_kt, e.get("summary", "")))
            except Exception:
                pass

    ket_qua = []
    t_sang_tu = _parse_hhmm(ghc["sang"]["tu"])
    t_sang_den = _parse_hhmm(ghc["sang"]["den"])
    t_chieu_tu = _parse_hhmm(ghc["chieu"]["tu"])
    t_chieu_den = _parse_hhmm(ghc["chieu"]["den"])

    windows = [(t_sang_tu, t_sang_den, "Sáng"), (t_chieu_tu, t_chieu_den, "Chiều")]

    for i in range(so_ngay):
        ngay_xet = ngay_goc + timedelta(days=i)
        thu = ngay_xet.isoweekday()
        if thu not in ghc["thu_lam_viec"]:
            continue

        for w_tu, w_den, buoi in windows:
            cur = datetime.combine(ngay_xet, w_tu, tzinfo=MUI_GIO)
            end_w = datetime.combine(ngay_xet, w_den, tzinfo=MUI_GIO)

            while cur + timedelta(minutes=thoi_luong) <= end_w:
                s_end = cur + timedelta(minutes=thoi_luong)
                if cur <= bay_gio + timedelta(minutes=dem_truoc):
                    cur += timedelta(minutes=buoc_nhay)
                    continue

                overlap = False
                for b_bd, b_kt, title in busy_spans:
                    if cur < b_kt and s_end > b_bd:
                        overlap = True
                        break

                if not overlap:
                    ket_qua.append({
                        "ngay": ngay_xet.isoformat(),
                        "thu": THU_VIET[thu],
                        "buoi": buoi,
                        "bat_dau": cur.isoformat(),
                        "ket_thuc": s_end.isoformat(),
                        "gio_bat_dau": cur.strftime("%H:%M"),
                        "gio_ket_thuc": s_end.strftime("%H:%M"),
                        "nhan_hien_thi": f"{THU_VIET[thu]} {ngay_xet.strftime('%d/%m')} ({cur.strftime('%H:%M')}–{s_end.strftime('%H:%M')})",
                        "thoi_luong": thoi_luong,
                    })
                cur += timedelta(minutes=buoc_nhay)

    return ket_qua


def dat_lich_cong_khai(sv, cfg: dict, bat_dau_iso: str, thoi_luong_phut: int = 30,
                       nguoi_tiep_don: str = "trang", khach_ten: str = "",
                       khach_email: str = "", khach_sdt: str = "",
                       noi_dung: str = "Trao đổi công việc") -> dict:
    """Tạo lịch hẹn công khai, tự động sinh Google Meet và gửi email cho khách."""
    if not khach_ten or not khach_email:
        raise ValueError("Vui lòng cung cấp đầy đủ Họ tên và Email của người đặt lịch.")

    # Tìm email người tiếp đón trong công ty
    danh_ba = cfg.get("danh_ba", {})
    email_ns = None
    ten_ns = nguoi_tiep_don

    if "@" in nguoi_tiep_don:
        email_ns = nguoi_tiep_don
        # Tìm tên trong danh bạ nếu có
        for k, v in danh_ba.items():
            if v.lower() == email_ns.lower():
                ten_ns = k.title()
                break
    else:
        k = nguoi_tiep_don.lower().strip()
        email_ns = danh_ba.get(k)
        if not email_ns:
            # Tra cứu trong danh sách nhân sự mở rộng
            for ns in lay_danh_sach_nhan_su(cfg):
                if ns["id"] == k or ns["ten"].lower() == k:
                    email_ns = ns["email"]
                    ten_ns = ns["ten"]
                    break
        if not email_ns:
            email_ns = "huyentrangfsh@gmail.com"  # Fallback CEO

    # Tính thời gian
    dt_bd = datetime.fromisoformat(bat_dau_iso)
    if dt_bd.tzinfo is None:
        dt_bd = dt_bd.replace(tzinfo=MUI_GIO)
    dt_kt = dt_bd + timedelta(minutes=thoi_luong_phut)

    # Chốt chặn kiểm tra trùng giờ (Race Condition Poka-Yoke)
    lich_id = cfg.get("lich_id", "primary")
    kiem_tra_trung = sv.events().list(
        calendarId=lich_id,
        timeMin=dt_bd.isoformat(),
        timeMax=dt_kt.isoformat(),
        singleEvents=True,
    ).execute().get("items", [])

    for sk in kiem_tra_trung:
        s_bd = sk["start"].get("dateTime")
        s_kt = sk["end"].get("dateTime")
        if s_bd and s_kt:
            e_bd = datetime.fromisoformat(s_bd)
            e_kt = datetime.fromisoformat(s_kt)
            if dt_bd < e_kt and dt_kt > e_bd:
                raise ValueError(f"Khung giờ {dt_bd.strftime('%H:%M %d/%m')} vừa bị trùng với sự kiện khác: '{sk.get('summary')}'. Vui lòng chọn khung giờ khác.")

    tieu_de = f"[HẸN LỊCH] {khach_ten} x {ten_ns}: {noi_dung}"
    mo_ta = (
        f"📅 CUỘC HẸN ĐẶT QUA CỔNG HẸN LỊCH TỰ ĐỘNG THI SEN\n"
        f"--------------------------------------------------\n"
        f"👤 Khách mời / Đối tác: {khach_ten}\n"
        f"📧 Email: {khach_email}\n"
        f"📱 Số điện thoại / Zalo: {khach_sdt or '(Chưa cung cấp)'}\n"
        f"💼 Người tiếp đón: {ten_ns} ({email_ns})\n"
        f"🎯 Mục đích cuộc gặp: {noi_dung}\n"
        f"⏱️ Thời lượng: {thoi_luong_phut} phút\n"
        f"🎥 Phiên họp mặc định qua Google Meet được tạo tự động đính kèm sự kiện này."
    )

    attendees = [{"email": email_ns, "displayName": ten_ns},
                 {"email": khach_email, "displayName": khach_ten}]

    than_su_kien = {
        "summary": tieu_de,
        "description": mo_ta,
        "start": {"dateTime": dt_bd.isoformat(), "timeZone": "Asia/Ho_Chi_Minh"},
        "end": {"dateTime": dt_kt.isoformat(), "timeZone": "Asia/Ho_Chi_Minh"},
        "attendees": attendees,
        "reminders": {
            "useDefault": False,
            "overrides": [{"method": "popup", "minutes": m} for m in cfg.get("nhac_popup", [60, 10])],
        },
        "conferenceData": {
            "createRequest": {
                "requestId": uuid.uuid4().hex,
                "conferenceSolutionKey": {"type": "hangoutsMeet"},
            }
        },
    }

    su_kien = sv.events().insert(
        calendarId=lich_id,
        body=than_su_kien,
        conferenceDataVersion=1,
        sendUpdates="all",  # Báo qua email tự động cho cả 2 bên
    ).execute()

    link_meet = su_kien.get("hangoutLink")
    link_lich = su_kien.get("htmlLink")

    ket_qua = {
        "ma": su_kien["id"],
        "tieu_de": tieu_de,
        "bat_dau": dt_bd.isoformat(),
        "ket_thuc": dt_kt.isoformat(),
        "thoi_luong": thoi_luong_phut,
        "nguoi_tiep_don": ten_ns,
        "email_tiep_don": email_ns,
        "khach_ten": khach_ten,
        "khach_email": khach_email,
        "khach_sdt": khach_sdt,
        "noi_dung": noi_dung,
        "link_meet": link_meet,
        "link_lich": link_lich,
        "tao_luc": datetime.now(MUI_GIO).isoformat(),
        "trang_thai": "da_dat_cong_khai",
    }

    # Bắn Telegram thông báo nếu có cấu hình
    try:
        import dia_diem  # noqa: F401
        from lich import gui_telegram
        tin_tele = (
            f"🔔 <b>CÓ LỊCH HẸN MỚI TỪ ĐỐI TÁC / KHÁCH HÀNG:</b>\n"
            f"📌 {tieu_de}\n"
            f"🕐 {THU_VIET[dt_bd.isoweekday()]} {dt_bd.strftime('%d/%m/%Y %H:%M')} ({thoi_luong_phut} phút)\n"
            f"👤 Khách: <b>{khach_ten}</b> ({khach_email} | {khach_sdt or 'k có SĐT'})\n"
            f"💼 Người tiếp: <b>{ten_ns}</b>\n"
            f"🎯 Nội dung: {noi_dung}\n"
            + (f"🎥 Link Meet: {link_meet}\n" if link_meet else "")
            + "<i>(Đã gửi email mời và đính kèm link Google Meet)</i>"
        )
        gui_telegram(tin_tele, bo_qua_im_lang=True)
    except Exception as e:
        print(f"[Cảnh báo Telegram] {e}", file=sys.stderr)

    # Ghi sổ lịch
    try:
        from lich import ghi_so
        ghi_so(ket_qua)
    except Exception as e:
        print(f"[Cảnh báo Ghi Sổ] {e}", file=sys.stderr)

    return ket_qua
