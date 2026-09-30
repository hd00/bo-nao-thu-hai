#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""lich.py — quản trị lịch: tạo/xem/đổi/huỷ sự kiện Google Calendar, ghi sổ, nhắc tự động.

Một câu tiếng Việt -> một sự kiện có link Meet, có khách mời, có nhắc — đúng mô hình
bot của Chung. Mọi lệnh đều in ra một "thẻ lịch" thống nhất để bot Telegram và
Claude dùng chung.

    python lich.py cap-quyen                       # một lần duy nhất: xin quyền Google
    python lich.py them "Call với anh Hùng 22h tối chủ nhật tuần này duonghung@gmail.com"
    python lich.py them "..." --nhap                # chỉ bóc tách, không tạo (xem trước)
    python lich.py xem --ngay 7                     # lịch 7 ngày tới
    python lich.py huy <ma_su_kien>
    python lich.py doi <ma_su_kien> "9h sáng mai"
    python lich.py nhac                             # quét & gửi nhắc (cron 5 phút/lần)

Cấu hình + token nằm ngoài kho mã, tại:  %USERPROFILE%\\.quan_tri_lich\\
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import urllib.parse
import urllib.request
import uuid
from datetime import datetime, timedelta
from pathlib import Path

import sys
for _luong in (sys.stdout, sys.stderr):
    try:
        _luong.reconfigure(encoding='utf-8', errors='replace')
    except Exception:
        pass

sys.path.insert(0, str(Path(__file__).parent))
import dia_diem as so_dia_diem  # noqa: E402
from phan_tich_vi import MUI_GIO, phan_tich  # noqa: E402

THU_MUC = Path(os.environ.get("QUAN_TRI_LICH_HOME") or (Path.home() / ".quan_tri_lich"))
TEP_CAU_HINH = THU_MUC / "cau_hinh.json"
TEP_TOKEN = THU_MUC / "token_calendar.json"
TEP_SO = THU_MUC / "so_lich.jsonl"
TEP_DA_NHAC = THU_MUC / "da_nhac.json"

PHAM_VI = ["https://www.googleapis.com/auth/calendar.events"]
MOC_NHAC = [60, 10]  # phút trước giờ họp — nhắc qua Telegram

# Chỉ sinh link Google Meet khi câu cho thấy đây là cuộc GỌI TRỰC TUYẾN.
# Việc đi đón con hay gặp mặt tại địa chỉ thật mà kèm link Meet là rác.
TU_KHOA_ONLINE = ("call", "meet", "online", "zoom", "teams", "gọi", "goi", "họp online")


# ------------------------------------------------------------------ cấu hình
def doc_cau_hinh() -> dict:
    cfg = {}
    if TEP_CAU_HINH.exists():
        cfg = json.loads(TEP_CAU_HINH.read_text(encoding="utf-8"))
    cfg.setdefault("lich_id", "primary")
    cfg.setdefault("nhac_popup", [60, 10])
    cfg.setdefault("danh_ba", {})           # "hùng" -> "duonghung@gmail.com"
    cfg["telegram_token"] = os.environ.get("TELEGRAM_BOT_TOKEN") or cfg.get("telegram_token", "")
    cfg["telegram_chat_id"] = os.environ.get("TELEGRAM_CHAT_ID") or cfg.get("telegram_chat_id", "")
    cfg.setdefault("client_secret", "")      # đường dẫn tệp OAuth client (desktop app)
    return cfg


def _ghi_cau_hinh(cfg: dict) -> None:
    THU_MUC.mkdir(parents=True, exist_ok=True)
    luu = {k: v for k, v in cfg.items() if k != "telegram_token" or not os.environ.get("TELEGRAM_BOT_TOKEN")}
    TEP_CAU_HINH.write_text(json.dumps(luu, ensure_ascii=False, indent=2), encoding="utf-8")


# -------------------------------------------------------------------- Google
def dich_vu(tuong_tac: bool = False):
    """Trả về service Calendar v3. Thiếu quyền -> báo cách cấp, không chết âm thầm."""
    from google.auth.transport.requests import Request
    from google.oauth2.credentials import Credentials
    from googleapiclient.discovery import build

    creds = None
    if TEP_TOKEN.exists():
        creds = Credentials.from_authorized_user_file(str(TEP_TOKEN), PHAM_VI)
    if creds and creds.expired and creds.refresh_token:
        creds.refresh(Request())
        TEP_TOKEN.write_text(creds.to_json(), encoding="utf-8")
    if not creds or not creds.valid:
        if not tuong_tac:
            raise SystemExit(
                "Chưa có quyền Google Calendar.\n"
                "Chạy:  python lich.py cap-quyen --client-secret <đường_dẫn_client_secret.json>"
            )
        creds = _xin_quyen()
    return build("calendar", "v3", credentials=creds, cache_discovery=False)


def _xin_quyen(duong_dan_client: str | None = None):
    from google_auth_oauthlib.flow import InstalledAppFlow

    cfg = doc_cau_hinh()
    tep = duong_dan_client or cfg.get("client_secret")
    if not tep or not Path(tep).exists():
        raise SystemExit("Thiếu tệp OAuth client. Xem CAI_DAT.md mục 1 để tải về từ Google Cloud.")
    flow = InstalledAppFlow.from_client_secrets_file(tep, PHAM_VI)
    creds = flow.run_local_server(port=0, prompt="consent")
    THU_MUC.mkdir(parents=True, exist_ok=True)
    TEP_TOKEN.write_text(creds.to_json(), encoding="utf-8")
    cfg["client_secret"] = str(Path(tep).resolve())
    cfg["cap_quyen_luc"] = datetime.now(MUI_GIO).isoformat()
    _ghi_cau_hinh(cfg)
    print(f"Đã cấp quyền. Token lưu tại {TEP_TOKEN}")
    return creds


# ----------------------------------------------------------------------- sổ
def ghi_so(ban_ghi: dict) -> None:
    THU_MUC.mkdir(parents=True, exist_ok=True)
    with TEP_SO.open("a", encoding="utf-8") as f:
        f.write(json.dumps(ban_ghi, ensure_ascii=False) + "\n")


def doc_so() -> list[dict]:
    if not TEP_SO.exists():
        return []
    ra = []
    for dong in TEP_SO.read_text(encoding="utf-8").splitlines():
        dong = dong.strip()
        if dong:
            try:
                ra.append(json.loads(dong))
            except json.JSONDecodeError:
                continue
    return ra


# ------------------------------------------------------------------ Telegram
def dang_im_lang(cfg: dict, bay_gio: datetime | None = None) -> str | None:
    """Đang trong khung cấm bắn Telegram thì trả về tên khung, không thì None.

    Dùng cho lúc người dùng đang lái xe hoặc đang ở cửa đóng gia đình. Rung điện
    thoại lúc cầm vô lăng là chuyện an toàn, không phải chuyện lịch sự.

    cau_hinh.json:
      "khung_im_lang": [
        {"ten": "lái xe đón con", "tu": "14:50", "den": "15:10", "ngay": "2026-09-20"},
        {"ten": "cửa đóng gia đình", "tu": "17:00", "den": "20:30"},
        {"ten": "giờ ngủ", "tu": "22:30", "den": "06:00", "thu": [1,2,3,4,5]}
      ]
    Phạm vi ngày — THIẾU LÀ ÁP MỌI NGÀY, nên việc một-lần phải khai rõ:
      "ngay": "YYYY-MM-DD"   chỉ đúng ngày đó   (giờ đưa đón con — đổi hằng ngày)
      "tru_ngay": [...]      trừ những ngày này  (ngoại lệ của khung thường trực)
      "thu" : [1..7]         theo thứ, 1=Hai    (lịch cố định hằng tuần)
      không khai gì          mọi ngày           (ranh giới thường trực như giờ gia đình)
    Khung qua nửa đêm (vd 22:30 -> 06:00) cũng hiểu đúng.
    """
    bay_gio = bay_gio or datetime.now(MUI_GIO)
    hm = bay_gio.strftime("%H:%M")
    for k in cfg.get("khung_im_lang") or []:
        tu, den = k.get("tu", ""), k.get("den", "")
        if not (tu and den):
            continue
        if k.get("ngay") and k["ngay"] != bay_gio.strftime("%Y-%m-%d"):
            continue
        if k.get("thu") and bay_gio.isoweekday() not in k["thu"]:
            continue
        if bay_gio.strftime("%Y-%m-%d") in (k.get("tru_ngay") or []):
            continue   # ngày ngoại lệ — vd tối có hẹn nên cửa gia đình đóng sớm hơn
        trong = (tu <= hm <= den) if tu <= den else (hm >= tu or hm <= den)
        if trong:
            return k.get("ten") or f"{tu}–{den}"
    return None


def gui_telegram(noi_dung: str, chat_id: str | None = None,
                 bo_qua_im_lang: bool = False) -> bool:
    cfg = doc_cau_hinh()
    khung = None if bo_qua_im_lang else dang_im_lang(cfg)
    if khung:
        print(f"IM LẶNG ({khung}) — không bắn Telegram:\n  {noi_dung.splitlines()[0]}",
              file=sys.stderr)
        return False
    token = cfg.get("telegram_token")
    chat_id = chat_id or cfg.get("telegram_chat_id")
    if not token or not chat_id:
        return False
    du_lieu = urllib.parse.urlencode({
        "chat_id": chat_id,
        "text": noi_dung,
        "parse_mode": "HTML",
        "disable_web_page_preview": "true",
    }).encode()
    try:
        with urllib.request.urlopen(
            f"https://api.telegram.org/bot{token}/sendMessage", du_lieu, timeout=20
        ) as r:
            return json.loads(r.read()).get("ok", False)
    except Exception as loi:  # noqa: BLE001 — mất mạng không được làm hỏng việc tạo lịch
        print(f"LỖI TELEGRAM: {loi}", file=sys.stderr)
        return False


# ------------------------------------------------------------------- thẻ lịch
THU_VIET = {1: "Thứ Hai", 2: "Thứ Ba", 3: "Thứ Tư", 4: "Thứ Năm",
            5: "Thứ Sáu", 6: "Thứ Bảy", 7: "Chủ Nhật"}


def the_lich(bg: dict, tieu_de_dau: str = "✅ Đã thêm vào lịch:") -> str:
    bat_dau = datetime.fromisoformat(bg["bat_dau"])
    dong = [tieu_de_dau,
            f"📌 {bg['tieu_de']}",
            f"🕐 {THU_VIET[bat_dau.isoweekday()]} {bat_dau.strftime('%d/%m/%Y %H:%M')}"]
    if bg.get("khach"):
        dong.append("👥 " + ", ".join(bg["khach"]))
    if bg.get("dia_diem"):
        dong.append(f"📍 {bg['dia_diem']}")
    if bg.get("link_map"):
        dong.append(f"🗺️ {bg['link_map']}")
    if bg.get("link_meet"):
        dong.append(f"🎥 Link Meet: {bg['link_meet']}")
    if bg.get("canh_bao"):
        dong += [f"⚠️ {c}" for c in bg["canh_bao"]]
    return "\n".join(dong)


# ------------------------------------------------------------------- lệnh
def lenh_them(cau: str, nhap: bool = False, im_lang: bool = False) -> dict:
    cfg = doc_cau_hinh()
    kq = phan_tich(cau)

    # tên trong danh bạ -> email khách mời (vd "hùng" -> duonghung@gmail.com)
    khach = list(kq.khach)
    thap = cau.lower()
    for ten, mail in (cfg.get("danh_ba") or {}).items():
        # khớp theo RANH GIỚI TỪ, không khớp chuỗi con — nếu không thì "trang chủ",
        # "trong trang" cũng kéo Trang vào danh sách mời và email bay đi oan.
        if re.search(rf"(?<![\w]){re.escape(ten.lower())}(?![\w])", thap) and mail not in khach:
            khach.append(mail)

    khoa_dd, dd = so_dia_diem.tim_trong_cau(cau)
    noi = dd.get("dia_chi") or dd.get("ten") if dd else None
    map_link = so_dia_diem.link_xem(dd) if dd else None

    ban_ghi = {
        "ma": None,
        "dia_diem": noi,
        "link_map": map_link,
        "tieu_de": kq.tieu_de,
        "bat_dau": kq.bat_dau.isoformat(),
        "ket_thuc": kq.ket_thuc.isoformat(),
        "khach": khach,
        "canh_bao": kq.canh_bao,
        "cau_goc": cau,
        "tao_luc": datetime.now(MUI_GIO).isoformat(),
        "link_meet": None,
        "link_lich": None,
        "trang_thai": "nhap" if nhap else "da_tao",
    }
    if nhap:
        if not im_lang:
            print(the_lich(ban_ghi, "👀 Xem trước (chưa tạo):"))
        return ban_ghi

    thap_kd = cau.lower()
    can_meet = any(t in thap_kd for t in TU_KHOA_ONLINE) or (bool(khach) and not noi)

    than = {
        "summary": kq.tieu_de,
        "description": f"Tạo tự động từ tin nhắn:\n{cau}",
        "start": {"dateTime": kq.bat_dau.isoformat(), "timeZone": "Asia/Ho_Chi_Minh"},
        "end": {"dateTime": kq.ket_thuc.isoformat(), "timeZone": "Asia/Ho_Chi_Minh"},
        "attendees": [{"email": e} for e in khach],
        **({"location": noi} if noi else {}),
        "reminders": {
            "useDefault": False,
            "overrides": [{"method": "popup", "minutes": m} for m in cfg["nhac_popup"]],
        },
        **({"conferenceData": {
            "createRequest": {
                "requestId": uuid.uuid4().hex,
                "conferenceSolutionKey": {"type": "hangoutsMeet"},
            }}} if can_meet else {}),
    }
    sv = dich_vu()
    su_kien = sv.events().insert(
        calendarId=cfg["lich_id"], body=than,
        conferenceDataVersion=1 if can_meet else 0, sendUpdates="all",
    ).execute()

    ban_ghi["ma"] = su_kien["id"]
    ban_ghi["link_lich"] = su_kien.get("htmlLink")
    ban_ghi["link_meet"] = su_kien.get("hangoutLink")
    ghi_so(ban_ghi)
    if not im_lang:
        print(the_lich(ban_ghi))
    return ban_ghi


def lenh_xem(so_ngay: int = 7) -> list[dict]:
    cfg = doc_cau_hinh()
    sv = dich_vu()
    bay_gio = datetime.now(MUI_GIO)
    ds = sv.events().list(
        calendarId=cfg["lich_id"],
        timeMin=bay_gio.isoformat(),
        timeMax=(bay_gio + timedelta(days=so_ngay)).isoformat(),
        singleEvents=True, orderBy="startTime", maxResults=50,
    ).execute().get("items", [])

    if not ds:
        print(f"Trống lịch trong {so_ngay} ngày tới.")
        return []
    print(f"📅 Lịch {so_ngay} ngày tới ({len(ds)} việc):\n")
    ra = []
    for sk in ds:
        bd = sk["start"].get("dateTime") or sk["start"].get("date")
        moc = datetime.fromisoformat(bd) if "T" in bd else None
        khi = f"{THU_VIET[moc.isoweekday()]} {moc.strftime('%d/%m %H:%M')}" if moc else f"Cả ngày {bd}"
        khach = [a["email"] for a in sk.get("attendees", []) if not a.get("self")]
        print(f"• {khi} — {sk.get('summary', '(không tên)')}"
              + (f"\n    👥 {', '.join(khach)}" if khach else "")
              + (f"\n    🎥 {sk['hangoutLink']}" if sk.get("hangoutLink") else "")
              + f"\n    🔖 {sk['id']}")
        ra.append({"ma": sk["id"], "tieu_de": sk.get("summary"), "bat_dau": bd, "khach": khach,
                   "link_meet": sk.get("hangoutLink")})
    return ra


def lenh_huy(ma: str) -> None:
    cfg = doc_cau_hinh()
    dich_vu().events().delete(calendarId=cfg["lich_id"], eventId=ma, sendUpdates="all").execute()
    ghi_so({"ma": ma, "trang_thai": "da_huy", "tao_luc": datetime.now(MUI_GIO).isoformat()})
    print(f"🗑️ Đã huỷ {ma} và báo cho khách mời.")


def lenh_doi(ma: str, cau_gio_moi: str) -> None:
    cfg = doc_cau_hinh()
    sv = dich_vu()
    sk = sv.events().get(calendarId=cfg["lich_id"], eventId=ma).execute()
    cu = datetime.fromisoformat(sk["start"]["dateTime"])
    dai = datetime.fromisoformat(sk["end"]["dateTime"]) - cu
    kq = phan_tich(cau_gio_moi)
    sk["start"] = {"dateTime": kq.bat_dau.isoformat(), "timeZone": "Asia/Ho_Chi_Minh"}
    sk["end"] = {"dateTime": (kq.bat_dau + dai).isoformat(), "timeZone": "Asia/Ho_Chi_Minh"}
    moi = sv.events().update(calendarId=cfg["lich_id"], eventId=ma, body=sk,
                             sendUpdates="all").execute()
    ghi_so({"ma": ma, "tieu_de": sk.get("summary"), "bat_dau": kq.bat_dau.isoformat(),
            "ket_thuc": (kq.bat_dau + dai).isoformat(), "trang_thai": "da_doi",
            "bat_dau_cu": cu.isoformat(), "link_meet": moi.get("hangoutLink"),
            "tao_luc": datetime.now(MUI_GIO).isoformat()})
    print(f"🔁 Đã dời: {sk.get('summary')}\n   {cu.strftime('%d/%m %H:%M')} → "
          f"{kq.bat_dau.strftime('%d/%m %H:%M')}")


def _bao_token_chet(loi: Exception, bay_gio: datetime) -> int:
    """Token hết hạn/hỏng -> bắn Telegram nhắc cấp lại quyền, tối đa 1 lần/ngày.

    Consent screen đang ở chế độ Testing nên Google cho refresh token sống 7 ngày.
    Không có chốt này thì tác vụ nhắc chạy nền sẽ chết lặng và không ai biết.
    """
    da = json.loads(TEP_DA_NHAC.read_text(encoding="utf-8")) if TEP_DA_NHAC.exists() else {}
    khoa = f"token_chet@{bay_gio.date().isoformat()}"
    loi_goi = ("⚠️ <b>Lịch mất quyền truy cập Google</b>\n"
               "Token đã hết hạn hoặc bị thu hồi — nhắc lịch đang NGỪNG chạy.\n"
               "Cấp lại: <code>python lich.py cap-quyen</code>\n"
               f"<i>{type(loi).__name__}: {str(loi)[:160]}</i>")
    if khoa not in da and gui_telegram(loi_goi):
        da[khoa] = bay_gio.isoformat()
        THU_MUC.mkdir(parents=True, exist_ok=True)
        TEP_DA_NHAC.write_text(json.dumps(da, ensure_ascii=False), encoding="utf-8")
    print(f"MẤT QUYỀN GOOGLE — nhắc lịch đang ngừng. Cấp lại: python lich.py cap-quyen\n  {loi}",
          file=sys.stderr)
    return 0


SONG_DUOC_NGAY = 7      # consent screen đang Testing -> refresh token sống 7 ngày
BAO_TRUOC_NGAY = 2      # còn ngần này ngày thì bắt đầu cảnh báo


def _canh_bao_token_sap_het(cfg: dict, bay_gio: datetime) -> None:
    """Báo TRƯỚC khi token chết, thay vì báo sau khi đã chết.

    App ở chế độ Testing nên Google chỉ cho refresh token sống 7 ngày. Không cảnh
    báo sớm thì đúng lúc cần dùng mới phát hiện — lúc đó đã trễ.
    """
    moc = cfg.get("cap_quyen_luc")
    if not moc:
        return
    try:
        het_han = datetime.fromisoformat(moc) + timedelta(days=SONG_DUOC_NGAY)
    except ValueError:
        return
    con = (het_han - bay_gio).total_seconds() / 86400
    if con > BAO_TRUOC_NGAY:
        return
    da = json.loads(TEP_DA_NHAC.read_text(encoding="utf-8")) if TEP_DA_NHAC.exists() else {}
    khoa = f"token_sap_het@{bay_gio.date().isoformat()}"
    if khoa in da:
        return
    tin = "\n".join([
        "⚠️ <b>Quyền Google Calendar sắp hết hạn</b>",
        f"Còn khoảng <b>{max(0, con):.1f} ngày</b> (hết lúc {het_han:%H:%M %d/%m}).",
        "Hết là ngừng nhắc lịch. Cấp lại: <code>python lich.py cap-quyen</code>",
        "<i>Muốn hết cảnh này thì Publish app sang Production.</i>",
    ])
    if gui_telegram(tin, bo_qua_im_lang=True):     # cảnh báo hỏng hệ thống — không im lặng
        da[khoa] = bay_gio.isoformat()
        THU_MUC.mkdir(parents=True, exist_ok=True)
        TEP_DA_NHAC.write_text(json.dumps(da, ensure_ascii=False), encoding="utf-8")
        print(f"Đã cảnh báo token sắp hết hạn (còn {con:.1f} ngày).")


def lenh_nhac(cua_so_phut: int = 6) -> int:
    """Quét lịch, gửi nhắc Telegram tại các mốc MOC_NHAC. Chạy định kỳ 5 phút/lần.

    Đã nhắc mốc nào thì ghi lại để không nhắc lại — cron chạy lệch giờ vẫn an toàn.
    """
    cfg = doc_cau_hinh()
    bay_gio = datetime.now(MUI_GIO)
    try:
        sv = dich_vu()
    except (Exception, SystemExit) as loi:  # SystemExit: thiếu token; Exception: RefreshError khi token hết hạn
        return _bao_token_chet(loi, bay_gio)
    _canh_bao_token_sap_het(cfg, bay_gio)
    ds = sv.events().list(
        calendarId=cfg["lich_id"], timeMin=bay_gio.isoformat(),
        timeMax=(bay_gio + timedelta(minutes=max(MOC_NHAC) + cua_so_phut)).isoformat(),
        singleEvents=True, orderBy="startTime",
    ).execute().get("items", [])

    da_nhac = json.loads(TEP_DA_NHAC.read_text(encoding="utf-8")) if TEP_DA_NHAC.exists() else {}
    so_gui = 0
    for sk in ds:
        bd = sk["start"].get("dateTime")
        if not bd:
            continue
        moc = datetime.fromisoformat(bd)
        con = (moc - bay_gio).total_seconds() / 60
        # bỏ mốc nhắc cho riêng một sự kiện — dùng khi mốc đó rơi vào giữa cuộc họp khác.
        # cau_hinh.json:  "bo_moc_nhac": {"<mã sự kiện>": [60]}
        bo = (cfg.get("bo_moc_nhac") or {}).get(sk["id"]) or []
        for m in MOC_NHAC:
            if m in bo:
                continue
            khoa = f"{sk['id']}@{moc.isoformat()}#{m}"
            if khoa in da_nhac or not (m - cua_so_phut <= con <= m):
                continue
            tin = "\n".join(filter(None, [
                f"⏰ <b>Còn {m} phút</b> nữa tới giờ:",
                f"📌 {sk.get('summary', '(không tên)')}",
                f"🕐 {moc.strftime('%H:%M %d/%m/%Y')}",
                f"🎥 {sk['hangoutLink']}" if sk.get("hangoutLink") else None,
            ]))
            # Khung im lặng sinh ra để chặn VIỆC CÔNG TY. Việc gia đình (đón con)
            # mà bị chặn thì chốt chặn phản tác dụng — cho phép vượt qua.
            uu_tien = sk["id"] in (cfg.get("nhac_uu_tien") or [])
            if gui_telegram(tin, bo_qua_im_lang=uu_tien):
                da_nhac[khoa] = bay_gio.isoformat()
                so_gui += 1
                print(f"Đã nhắc ({m}p): {sk.get('summary')}")
            else:
                print(f"[không gửi được Telegram] {tin}")

    # dọn khoá cũ hơn 2 ngày cho tệp khỏi phình
    nguong = bay_gio - timedelta(days=2)
    da_nhac = {k: v for k, v in da_nhac.items() if datetime.fromisoformat(v) > nguong}
    THU_MUC.mkdir(parents=True, exist_ok=True)
    TEP_DA_NHAC.write_text(json.dumps(da_nhac, ensure_ascii=False), encoding="utf-8")
    return so_gui


def lenh_so(so_dong: int = 20) -> None:
    ban_ghi = doc_so()[-so_dong:]
    if not ban_ghi:
        print(f"Sổ lịch trống ({TEP_SO}).")
        return
    print(f"📖 {len(ban_ghi)} ghi chép gần nhất — {TEP_SO}\n")
    for b in ban_ghi:
        print(f"[{b.get('trang_thai')}] {b.get('bat_dau', '?')[:16]} · {b.get('tieu_de', '')} "
              f"· {b.get('ma') or '-'}")




# ------------------------------------------------------------------ đặt lịch công khai & khe trống
def lenh_khe_trong(so_ngay: int = 7, thoi_luong: int = 30, nguoi: str | None = None, xuat_json: bool = False) -> list[dict]:
    import khe_trong
    cfg = doc_cau_hinh()
    sv = dich_vu()
    slots = khe_trong.tim_khe_trong(sv, cfg, so_ngay=so_ngay, thoi_luong_phut=thoi_luong, nguoi_email=nguoi)
    if xuat_json:
        print(json.dumps(slots, ensure_ascii=False, indent=2))
        return slots
    if not slots:
        print(f"Không còn khung giờ hành chính trống trong {so_ngay} ngày tới (thời lượng {thoi_luong}p).")
        return []
    print(f"📅 CÁC KHUNG GIỜ HÀNH CHÍNH CÒN TRỐNG ({len(slots)} khung, mỗi phiên {thoi_luong} phút):\n")
    theo_ngay = {}
    for s in slots:
        theo_ngay.setdefault(s["ngay"], []).append(s)
    from datetime import date
    for ngay_str, ds_s in theo_ngay.items():
        thu = ds_s[0]["thu"]
        dt = date.fromisoformat(ngay_str)
        sang = [f"{x['gio_bat_dau']}–{x['gio_ket_thuc']}" for x in ds_s if x["buoi"] == "Sáng"]
        chieu = [f"{x['gio_bat_dau']}–{x['gio_ket_thuc']}" for x in ds_s if x["buoi"] == "Chiều"]
        print(f"• {thu} {dt.strftime('%d/%m/%Y')} ({len(ds_s)} khung):")
        if sang:
            print(f"   🌅 Sáng (08:30–12:00):  {' | '.join(sang)}")
        if chieu:
            print(f"   🌇 Chiều (13:30–17:30): {' | '.join(chieu)}")
        print()
    return slots


def lenh_book(bat_dau: str, thoi_luong: int = 30, nguoi: str = "trang", ten: str = "",
              email: str = "", sdt: str = "", noi_dung: str = "Trao đổi công việc",
              xuat_json: bool = False) -> dict:
    import khe_trong
    cfg = doc_cau_hinh()
    sv = dich_vu()
    if "T" not in bat_dau:
        from phan_tich_vi import phan_tich
        kq = phan_tich(bat_dau)
        bat_dau_iso = kq.bat_dau.isoformat()
    else:
        bat_dau_iso = bat_dau
    kq_dat = khe_trong.dat_lich_cong_khai(
        sv=sv, cfg=cfg, bat_dau_iso=bat_dau_iso, thoi_luong_phut=thoi_luong,
        nguoi_tiep_don=nguoi, khach_ten=ten, khach_email=email,
        khach_sdt=sdt, noi_dung=noi_dung
    )
    if xuat_json:
        print(json.dumps(kq_dat, ensure_ascii=False, indent=2))
        return kq_dat
    dt_bd = datetime.fromisoformat(kq_dat["bat_dau"])
    print("✅ ĐÃ ĐẶT LỊCH THÀNH CÔNG VỚI ĐỐI TÁC / KHÁCH HÀNG:")
    print(f"📌 {kq_dat['tieu_de']}")
    print(f"🕐 {THU_VIET[dt_bd.isoweekday()]} {dt_bd.strftime('%d/%m/%Y %H:%M')} ({thoi_luong} phút)")
    print(f"👤 Khách: {kq_dat['khach_ten']} ({kq_dat['khach_email']})")
    print(f"💼 Người tiếp: {kq_dat['nguoi_tiep_don']} ({kq_dat['email_tiep_don']})")
    if kq_dat.get("link_meet"):
        print(f"🎥 Google Meet: {kq_dat['link_meet']}")
    print("📧 Thư mời và link Meet đã được Google tự động gửi tới email hai bên.")
    return kq_dat


def lenh_server(port: int = 8092) -> None:
    import web_booking
    web_booking.chay_server(port)

def main() -> int:
    p = argparse.ArgumentParser(description="Quản trị lịch Thi Sen — Google Calendar + Telegram")
    con = p.add_subparsers(dest="lenh", required=True)

    a = con.add_parser("cap-quyen", help="xin quyền Google Calendar (một lần)")
    a.add_argument("--client-secret", default=None)

    b = con.add_parser("them", help="tạo sự kiện từ câu tiếng Việt")
    b.add_argument("cau", nargs="+")
    b.add_argument("--nhap", action="store_true", help="chỉ xem trước, không tạo")
    b.add_argument("--json", action="store_true")

    c = con.add_parser("xem", help="liệt kê lịch sắp tới")
    c.add_argument("--ngay", type=int, default=7)

    d = con.add_parser("huy", help="huỷ sự kiện")
    d.add_argument("ma")

    e = con.add_parser("doi", help="dời giờ sự kiện")
    e.add_argument("ma")
    e.add_argument("cau", nargs="+")

    f = con.add_parser("nhac", help="quét & gửi nhắc (chạy định kỳ)")
    f.add_argument("--cua-so", type=int, default=6)

    g = con.add_parser("so", help="xem sổ lịch đã ghi")
    g.add_argument("--dong", type=int, default=20)

    h = con.add_parser("khe-trong", help="tìm các khung giờ hành chính còn trống")
    h.add_argument("--ngay", type=int, default=7)
    h.add_argument("--thoi-luong", type=int, default=30)
    h.add_argument("--nguoi", default=None)
    h.add_argument("--json", action="store_true")

    i = con.add_parser("book", help="đối tác / khách hàng đặt lịch công khai")
    i.add_argument("--bat-dau", required=True, help="thời điểm bắt đầu (ISO hoặc câu giờ)")
    i.add_argument("--thoi-luong", type=int, default=30)
    i.add_argument("--nguoi", default="trang", help="tên hoặc email người tiếp đón (trang, hùng...)")
    i.add_argument("--ten", required=True, help="họ tên khách")
    i.add_argument("--email", required=True, help="email khách để nhận link Meet")
    i.add_argument("--sdt", default="", help="số điện thoại / zalo khách")
    i.add_argument("--noi-dung", default="Trao đổi công việc", help="mục đích cuộc gặp")
    i.add_argument("--json", action="store_true")

    j = con.add_parser("server", help="khởi động Web Portal Đặt Lịch")
    j.add_argument("--port", type=int, default=8092)

    k = con.add_parser("tao-google-schedule", help="tự động tạo Google Appointment Schedule qua Chrome debug 9222")
    k.add_argument("--port", type=int, default=9222)
    k.add_argument("--tieu-de", default=None)
    k.add_argument("--mo-ta", default=None)
    k.add_argument("--slug", default=None)
    k.add_argument("--thoi-luong", type=int, default=30)

    t = p.parse_args()
    if t.lenh == "cap-quyen":
        _xin_quyen(t.client_secret)
    elif t.lenh == "them":
        bg = lenh_them(" ".join(t.cau), nhap=t.nhap, im_lang=t.json)
        if t.json:
            print(json.dumps(bg, ensure_ascii=False, indent=2))
    elif t.lenh == "xem":
        lenh_xem(t.ngay)
    elif t.lenh == "huy":
        lenh_huy(t.ma)
    elif t.lenh == "doi":
        lenh_doi(t.ma, " ".join(t.cau))
    elif t.lenh == "nhac":
        print(f"Đã gửi {lenh_nhac(t.cua_so)} tin nhắc.")
    elif t.lenh == "so":
        lenh_so(t.dong)
    elif t.lenh == "khe-trong":
        lenh_khe_trong(so_ngay=t.ngay, thoi_luong=t.thoi_luong, nguoi=t.nguoi, xuat_json=t.json)
    elif t.lenh == "book":
        lenh_book(bat_dau=t.bat_dau, thoi_luong=t.thoi_luong, nguoi=t.nguoi,
                  ten=t.ten, email=t.email, sdt=t.sdt, noi_dung=t.noi_dung, xuat_json=t.json)
    elif t.lenh == "server":
        lenh_server(t.port)
    elif t.lenh == "tao-google-schedule":
        import tao_google_schedule
        sys.argv = [sys.argv[0]] + sys.argv[2:]
        return tao_google_schedule.main()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
