#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""bot_telegram.py — bot Telegram đặt lịch: nhắn một câu, có ngay sự kiện + link Meet.

Đúng luồng của Chung: gõ "Call với anh Hùng lúc 22h tối chủ nhật tuần này.
email duonghung@gmail.com" -> bot trả thẻ lịch kèm link Meet, và tự nhắc trước giờ.

Chạy:  python bot_telegram.py           (long-polling, Ctrl+C để dừng)
Cần:   TELEGRAM_BOT_TOKEN trong môi trường hoặc trong cau_hinh.json

Lệnh trong chat:
    <câu bất kỳ>      tạo lịch
    ?<câu>            chỉ xem trước, không tạo
    /lich [số ngày]   xem lịch sắp tới (mặc định 7 ngày)
    /huy <mã>         huỷ sự kiện
    /so               10 ghi chép gần nhất
    /id               xem chat id (dùng để điền telegram_chat_id)
    /giup             hướng dẫn
"""

from __future__ import annotations

import json
import os
import sys
import time
import traceback
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timedelta
from pathlib import Path

import sys
for _luong in (sys.stdout, sys.stderr):
    try:
        _luong.reconfigure(encoding='utf-8', errors='replace')
    except Exception:
        pass

sys.path.insert(0, str(Path(__file__).parent))
from lich import (MUI_GIO, THU_VIET, doc_cau_hinh, doc_so, lenh_huy,  # noqa: E402
                  lenh_nhac, lenh_them, the_lich, dich_vu)

CHU_KY_NHAC = 300  # giây — cứ 5 phút bot tự quét lịch để nhắc

GIUP = """<b>Bot lịch Thi Sen</b>

Nhắn thẳng một câu, ví dụ:
• <i>Call với anh Hùng lúc 22h tối chủ nhật tuần này. email duonghung@gmail.com</i>
• <i>Họp team 9h sáng mai trong 2 tiếng</i>
• <i>Gặp chị Nhung 2h chiều thứ 3 tuần sau</i>

Lệnh:
/lich [số ngày] — xem lịch sắp tới
/huy &lt;mã&gt; — huỷ một sự kiện
/so — sổ lịch đã ghi
/id — xem chat id
?&lt;câu&gt; — chỉ xem trước, chưa tạo"""


def _goi(token: str, ham: str, **tham_so):
    du_lieu = urllib.parse.urlencode(
        {k: v for k, v in tham_so.items() if v is not None}).encode()
    with urllib.request.urlopen(
        f"https://api.telegram.org/bot{token}/{ham}", du_lieu, timeout=70
    ) as r:
        return json.loads(r.read())


def tra_loi(token: str, chat_id, van_ban: str) -> None:
    try:
        _goi(token, "sendMessage", chat_id=chat_id, text=van_ban,
             parse_mode="HTML", disable_web_page_preview="true")
    except Exception:  # noqa: BLE001
        traceback.print_exc()


def _lich_sap_toi(so_ngay: int) -> str:
    cfg = doc_cau_hinh()
    bay_gio = datetime.now(MUI_GIO)
    ds = dich_vu().events().list(
        calendarId=cfg["lich_id"], timeMin=bay_gio.isoformat(),
        timeMax=(bay_gio + timedelta(days=so_ngay)).isoformat(),
        singleEvents=True, orderBy="startTime", maxResults=30,
    ).execute().get("items", [])
    if not ds:
        return f"📅 Trống lịch trong {so_ngay} ngày tới."
    dong = [f"📅 <b>Lịch {so_ngay} ngày tới</b> ({len(ds)} việc)", ""]
    for sk in ds:
        bd = sk["start"].get("dateTime") or sk["start"].get("date")
        if "T" in bd:
            m = datetime.fromisoformat(bd)
            khi = f"{THU_VIET[m.isoweekday()]} {m.strftime('%d/%m %H:%M')}"
        else:
            khi = f"Cả ngày {bd}"
        dong.append(f"• <b>{khi}</b> — {sk.get('summary', '(không tên)')}")
        if sk.get("hangoutLink"):
            dong.append(f"   🎥 {sk['hangoutLink']}")
        dong.append(f"   🔖 <code>{sk['id']}</code>")
    return "\n".join(dong)


def xu_ly(token: str, chat_id, van_ban: str) -> None:
    van_ban = (van_ban or "").strip()
    if not van_ban:
        return
    thap = van_ban.lower()

    if thap.startswith(("/start", "/giup", "/help")):
        return tra_loi(token, chat_id, GIUP)
    if thap.startswith("/id"):
        return tra_loi(token, chat_id, f"chat id của bạn: <code>{chat_id}</code>")
    if thap.startswith("/lich"):
        phan = van_ban.split()
        so_ngay = int(phan[1]) if len(phan) > 1 and phan[1].isdigit() else 7
        return tra_loi(token, chat_id, _lich_sap_toi(so_ngay))
    if thap.startswith("/huy"):
        phan = van_ban.split(maxsplit=1)
        if len(phan) < 2:
            return tra_loi(token, chat_id, "Cú pháp: /huy &lt;mã sự kiện&gt; (xem mã bằng /lich)")
        lenh_huy(phan[1].strip())
        return tra_loi(token, chat_id, "🗑️ Đã huỷ và báo cho khách mời.")
    if thap.startswith("/so"):
        ds = doc_so()[-10:]
        if not ds:
            return tra_loi(token, chat_id, "Sổ lịch còn trống.")
        return tra_loi(token, chat_id, "📖 <b>Sổ lịch</b>\n" + "\n".join(
            f"• [{b.get('trang_thai')}] {b.get('bat_dau', '?')[:16].replace('T', ' ')} — "
            f"{b.get('tieu_de', '')}" for b in ds))

    xem_truoc = van_ban.startswith("?")
    cau = van_ban.lstrip("?").strip()
    try:
        bg = lenh_them(cau, nhap=xem_truoc, im_lang=True)
    except SystemExit as loi:
        return tra_loi(token, chat_id, f"⚠️ {loi}")
    except Exception as loi:  # noqa: BLE001
        traceback.print_exc()
        return tra_loi(token, chat_id, f"⚠️ Không tạo được lịch: {loi}")
    tra_loi(token, chat_id, the_lich(bg, "👀 Xem trước (chưa tạo):" if xem_truoc
                                     else "✅ Đã thêm vào lịch:"))


def main() -> int:
    cfg = doc_cau_hinh()
    # CỐ Ý dùng khoá riêng, KHÔNG dùng chung `telegram_token`. `telegram_token` chỉ để
    # GỬI (sendMessage) nên xài chung bot với daemon khác vô hại; còn bot này LẮNG NGHE
    # (getUpdates), mà Telegram chỉ cho một listener mỗi token. Tách khoá để không bao giờ
    # vô tình cướp bot của tele-dropzone hay living-schedule.
    token = os.environ.get("TELEGRAM_BOT_TOKEN") or cfg.get("telegram_token_bot")
    if not token:
        raise SystemExit(
            "Thiếu token RIÊNG cho bot đặt lịch.\n"
            "Bot này lắng nghe getUpdates nên PHẢI có bot riêng — không dùng chung\n"
            "`telegram_token` (đang trỏ tới bot gửi thông báo, có daemon khác sở hữu).\n"
            "Tạo bot mới bằng /newbot rồi điền vào `telegram_token_bot` trong cau_hinh.json."
        )
    cho_phep = {str(x) for x in (cfg.get("chat_cho_phep") or []) if x}
    if cfg.get("telegram_chat_id"):
        cho_phep.add(str(cfg["telegram_chat_id"]))

    try:
        toi = _goi(token, "getMe").get("result", {})
        print(f"Bot: @{toi.get('username')} ({toi.get('first_name')})")
        if any(x in (toi.get("username") or "").lower()
               for x in ("har_command_center", "har_living_schedule")):
            raise SystemExit(
                "Token này thuộc một bot ĐÃ CÓ daemon sở hữu (@har_command_center_bot ← "
                "tele-dropzone, @HAR_Living_Schedule_Bot ← living-schedule). Dùng chung sẽ "
                "gây 409 Conflict, hỏng cả hai. Tạo bot riêng bằng /newbot.")
    except urllib.error.HTTPError as loi:
        raise SystemExit(f"Token Telegram không dùng được ({loi.code}). Kiểm tra lại cau_hinh.json.") from loi

    offset, lan_nhac = None, 0.0
    print("Bot lịch đang chạy. Ctrl+C để dừng.")
    while True:
        try:
            kq = _goi(token, "getUpdates", offset=offset, timeout=30)
            for c in kq.get("result", []):
                offset = c["update_id"] + 1
                tin = c.get("message") or c.get("edited_message")
                if not tin or "text" not in tin:
                    continue
                chat_id = tin["chat"]["id"]
                if cho_phep and str(chat_id) not in cho_phep:
                    tra_loi(token, chat_id,
                            f"Chat này chưa được phép dùng bot. Chat id: <code>{chat_id}</code>")
                    continue
                xu_ly(token, chat_id, tin["text"])
        except KeyboardInterrupt:
            print("\nDừng bot.")
            return 0
        except urllib.error.HTTPError as loi:
            if loi.code == 409:
                # Bài học 09_LESSONS_LEARNED mục 4: hai tiến trình cùng getUpdates một
                # bot token -> tranh chấp, cả hai chập chờn. Thà chết hẳn còn hơn giành.
                raise SystemExit(
                    "409 Conflict — đã có tiến trình khác đang lắng nghe bot token này.\n"
                    "Bot lịch PHẢI dùng token riêng, không dùng chung với @har_command_center_bot\n"
                    "(tele-dropzone chạy 24/7 trên VPS). Tạo bot mới bằng /newbot, xem CAI_DAT.md mục 3."
                ) from loi
            traceback.print_exc()
            time.sleep(5)
        except Exception:  # noqa: BLE001 — mạng chập chờn không được giết bot
            traceback.print_exc()
            time.sleep(5)

        if time.time() - lan_nhac > CHU_KY_NHAC:
            lan_nhac = time.time()
            try:
                lenh_nhac()
            except Exception:  # noqa: BLE001
                traceback.print_exc()


if __name__ == "__main__":
    raise SystemExit(main())
