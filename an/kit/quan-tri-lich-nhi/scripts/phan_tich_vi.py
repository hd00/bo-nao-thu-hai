#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""phan_tich_vi.py — bóc tách lịch hẹn từ một câu tiếng Việt tự nhiên.

Vào:  "Call với anh Hùng lúc 22h tối chủ nhật tuần này. email duonghung@gmail.com"
Ra:   tiêu đề, giờ bắt đầu, giờ kết thúc, danh sách email khách mời.

Không gọi mạng, không phụ thuộc thư viện ngoài — để bot Telegram và CLI dùng chung
một bộ luật, khỏi lệch nhau. Múi giờ mặc định: Asia/Ho_Chi_Minh.
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone

import sys
for _luong in (sys.stdout, sys.stderr):
    try:
        _luong.reconfigure(encoding='utf-8', errors='replace')
    except Exception:
        pass

MUI_GIO = timezone(timedelta(hours=7))  # Asia/Ho_Chi_Minh, không lệch mùa
THOI_LUONG_MAC_DINH = 60  # phút

RE_EMAIL = re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+")

# thứ trong tuần -> isoweekday (2=thứ hai ... 8→chủ nhật=7)
THU = {
    "hai": 1, "2": 1,
    "ba": 2, "3": 2,
    "tu": 3, "tư": 3, "4": 3,
    "nam": 4, "năm": 4, "5": 4,
    "sau": 5, "sáu": 5, "6": 5,
    "bay": 6, "bảy": 6, "7": 6,
}


def _bo_dau(s: str) -> str:
    """Bỏ dấu tiếng Việt để bắt từ khoá kể cả khi người dùng gõ không dấu."""
    s = unicodedata.normalize("NFD", s)
    s = "".join(c for c in s if unicodedata.category(c) != "Mn")
    return s.replace("đ", "d").replace("Đ", "D").lower()


@dataclass
class KetQua:
    tieu_de: str
    bat_dau: datetime
    ket_thuc: datetime
    khach: list[str] = field(default_factory=list)
    canh_bao: list[str] = field(default_factory=list)
    doan_gio: bool = False   # True nếu phải đoán giờ vì câu không nói giờ

    def nhu_dict(self) -> dict:
        return {
            "tieu_de": self.tieu_de,
            "bat_dau": self.bat_dau.isoformat(),
            "ket_thuc": self.ket_thuc.isoformat(),
            "khach": self.khach,
            "canh_bao": self.canh_bao,
            "doan_gio": self.doan_gio,
        }


# ---------------------------------------------------------------- thời lượng
RE_THOI_LUONG = re.compile(
    r"(?:trong|keo dai|kéo dài|dai|dài)\s+(\d+(?:[.,]\d+)?)\s*"
    r"(tieng|tiếng|gio|giờ|h|phut|phút|p)\b\s*(ruoi|rưỡi)?"
)
# "nửa tiếng", "trong nửa tiếng"
RE_NUA_TIENG = re.compile(r"\bnua\s*(?:tieng|gio)\b")


def _boc_thoi_luong(raw: str, khong_dau: str):
    if RE_NUA_TIENG.search(khong_dau):
        return 30, RE_NUA_TIENG.search(khong_dau).span()
    m = RE_THOI_LUONG.search(khong_dau)
    if not m:
        return THOI_LUONG_MAC_DINH, None
    so = float(m.group(1).replace(",", "."))
    la_gio = m.group(2) in ("tieng", "tiếng", "gio", "giờ", "h")
    phut = so * 60 if la_gio else so
    if m.group(3):                       # "1 tiếng rưỡi" -> 90 phút
        phut += 30 if la_gio else 0.5
    return max(5, int(round(phut))), m.span()


# -------------------------------------------------------------------- giờ
# 22h, 22h30, 22 giờ 30, 22:30, 9g, "9 rưỡi"
RE_GIO = re.compile(r"(?<![\d/])(\d{1,2})\s*(?:h|g|gio|giờ|:)\s*(\d{1,2})?(?!\s*[/\d])")
RE_GIO_LUC = re.compile(r"(?:luc|lúc)\s+(\d{1,2})(?![\d/:h])")
RE_RUOI = re.compile(r"(\d{1,2})\s*(?:h|g|gio|giờ)?\s*(?:ruoi|rưỡi)")

BUOI = ("sang", "trua", "chieu", "toi", "dem")


def _boc_gio(khong_dau: str):
    """Trả (giờ, phút, span) hoặc None. Ưu tiên cụm 'Xh' rồi tới 'lúc X'."""
    m = RE_RUOI.search(khong_dau)
    if m:
        return int(m.group(1)), 30, m.span()
    for m in RE_GIO.finditer(khong_dau):
        gio = int(m.group(1))
        phut = int(m.group(2)) if m.group(2) else 0
        if gio > 24 or phut > 59:
            continue
        return gio, phut, m.span()
    m = RE_GIO_LUC.search(khong_dau)
    if m and int(m.group(1)) <= 24:
        return int(m.group(1)), 0, m.span()
    return None


def _ap_buoi(gio: int, khong_dau: str, vi_tri_gio: int) -> int:
    """'2h chiều' -> 14h. Chỉ xét buổi nằm sát cụm giờ (trước 12 ký tự, sau 12 ký tự)."""
    lan_can = khong_dau[max(0, vi_tri_gio - 12): vi_tri_gio + 14]
    buoi = next((b for b in BUOI if b in lan_can), None)
    if buoi is None:
        return gio % 24
    if buoi == "sang":
        return 0 if gio == 12 else gio
    if buoi == "trua":
        return 12 if gio in (12, 0) else (gio + 12 if gio < 11 else gio)
    if gio < 12:  # chieu / toi / dem
        return gio + 12
    return gio


# -------------------------------------------------------------------- ngày
RE_NGAY_THANG = re.compile(r"(?<!\d)(\d{1,2})\s*[/-]\s*(\d{1,2})(?:\s*[/-]\s*(\d{2,4}))?(?!\d)")
RE_NGAY_SO = re.compile(r"\bngay\s+(\d{1,2})\b(?!\s*[/-])")
RE_TUONG_DOI = re.compile(r"(?<!thu )(?<![a-z])(\d+)\s*(phut|phút|tieng|tiếng|gio|giờ|ngay|ngày|tuan|tuần)\s*(?:nua|nữa|sau)")
RE_THU = re.compile(r"\b(?:thu|thứ)\s*(hai|ba|tu|tư|nam|năm|sau|sáu|bay|bảy|[2-7])\b|\bt([2-7])\b")
RE_CN = re.compile(r"\b(?:chu nhat|chủ nhật|cn|chua nhat)\b")


def _tuan_lech(khong_dau: str) -> int:
    if re.search(r"tuan\s*(?:sau|toi|tới)", khong_dau):
        return 1
    if re.search(r"tuan\s*truoc", khong_dau):
        return -1
    if re.search(r"tuan\s*(?:nay|này)", khong_dau):
        return 0
    return None  # không nói tuần


def _boc_ngay(khong_dau: str, bay_gio: datetime):
    """Trả (date, đã_nói_ngày: bool). Không nói gì -> hôm nay."""
    hom_nay = bay_gio.date()

    m = RE_NGAY_THANG.search(khong_dau)
    if m:
        ngay, thang = int(m.group(1)), int(m.group(2))
        nam = int(m.group(3)) if m.group(3) else hom_nay.year
        if nam < 100:
            nam += 2000
        try:
            d = datetime(nam, thang, ngay).date()
        except ValueError:
            return hom_nay, False
        if not m.group(3) and d < hom_nay:
            try:
                d = d.replace(year=nam + 1)
            except ValueError:
                pass
        return d, True

    m = RE_TUONG_DOI.search(khong_dau)
    if m:
        so, dv = int(m.group(1)), m.group(2)
        if dv.startswith(("phut", "phút")):
            return (bay_gio + timedelta(minutes=so)).date(), True
        if dv.startswith(("tieng", "tiếng", "gio", "giờ")):
            return (bay_gio + timedelta(hours=so)).date(), True
        if dv.startswith(("ngay", "ngày")):
            return hom_nay + timedelta(days=so), True
        return hom_nay + timedelta(weeks=so), True

    if re.search(r"\bngay kia\b|\bmot\b|\bmốt\b", khong_dau):
        return hom_nay + timedelta(days=2), True
    if re.search(r"\b(?:ngay )?mai\b", khong_dau):
        return hom_nay + timedelta(days=1), True
    if re.search(r"\bhom nay\b|(?<!tuan )\bnay\b", khong_dau):
        return hom_nay, True

    # thứ / chủ nhật
    iso_dich = None
    if RE_CN.search(khong_dau):
        iso_dich = 7
    else:
        m = RE_THU.search(khong_dau)
        if m:
            khoa = m.group(1) or m.group(2)
            iso_dich = THU.get(khoa)
    if iso_dich:
        lech_tuan = _tuan_lech(khong_dau)
        dau_tuan = hom_nay - timedelta(days=hom_nay.isoweekday() - 1)
        if lech_tuan is None:
            # không nói tuần -> lần xuất hiện gần nhất kể từ hôm nay
            d = hom_nay + timedelta(days=(iso_dich - hom_nay.isoweekday()) % 7)
        else:
            d = dau_tuan + timedelta(days=iso_dich - 1, weeks=lech_tuan)
        return d, True

    m = RE_NGAY_SO.search(khong_dau)
    if m:
        ngay = int(m.group(1))
        try:
            d = hom_nay.replace(day=ngay)
        except ValueError:
            return hom_nay, False
        if d < hom_nay:
            thang, nam = (hom_nay.month % 12) + 1, hom_nay.year + (hom_nay.month // 12)
            try:
                d = datetime(nam, thang, ngay).date()
            except ValueError:
                return hom_nay, False
        return d, True

    lech_tuan = _tuan_lech(khong_dau)
    if lech_tuan:
        return hom_nay + timedelta(weeks=lech_tuan), True
    return hom_nay, False


# ------------------------------------------------------------------ tiêu đề
RAC = [
    r"\bemail (?:cua|của)\b[^.,;]*", r"\bmoi\b\s*:?", r"\bmời\b\s*:?",
    r"\b(?:dat|đặt|tao|tạo|them|thêm) (?:lich|lịch)\b", r"\b(?:nhac|nhắc) (?:toi|tôi)\b",
    r"\bluc\b", r"\blúc\b", r"\bvao\b", r"\bvào\b",
    r"\btuan (?:nay|này|sau|toi|tới|truoc|trước)\b", r"\btuần (?:này|sau|tới|trước)\b",
    r"\b(?:thu|thứ)\s*(?:hai|ba|tu|tư|nam|năm|sau|sáu|bay|bảy|[2-7])\b", r"\bt[2-7]\b",
    r"\b(?:chu nhat|chủ nhật|cn)\b",
    r"\b(?:sang|sáng|trua|trưa|chieu|chiều|toi|tối|dem|đêm)\b",
    r"\b(?:hom nay|hôm nay|ngay mai|ngày mai|mai|ngay kia|ngày kia|mot|mốt)\b",
    r"(?<!tuan )\bnay\b",   # "tối nay", "chiều nay" — cắt nốt chữ 'nay' còn sót lại
    r"\bng[aà]y\s+\d{1,2}(?:\s*[/-]\s*\d{1,2}(?:\s*[/-]\s*\d{2,4})?)?\b",
    r"\d{1,2}\s*[/-]\s*\d{1,2}(?:\s*[/-]\s*\d{2,4})?",
    r"\d{1,2}\s*(?:h|g|gio|giờ|:)\s*\d{0,2}", r"\d{1,2}\s*(?:ruoi|rưỡi)",
    r"(?:trong|keo dai|kéo dài)\s+\d+(?:[.,]\d+)?\s*(?:tieng|tiếng|gio|giờ|h|phut|phút|p)\b\s*(?:ruoi|rưỡi)?",
    r"(?:trong\s+)?\bn[uư]a\s*(?:ti[eế]ng|gi[oờ])\b",
    r"\d+\s*(?:phut|phút|tieng|tiếng|gio|giờ|ngay|ngày|tuan|tuần)\s*(?:nua|nữa|sau)",
]
RE_RAC = re.compile("|".join(RAC), re.IGNORECASE)


def _lam_tieu_de(raw: str) -> str:
    s = RE_EMAIL.sub(" ", raw)
    # cắt rác trên bản có dấu bằng cách chiếu vị trí từ bản không dấu
    kd = _bo_dau(s)
    giu = [True] * len(s)
    for m in RE_RAC.finditer(kd):
        for i in range(m.start(), min(m.end(), len(s))):
            giu[i] = False
    s = "".join(c for c, k in zip(s, giu) if k)
    s = re.sub(r"[\s.,;:\-]+", " ", s).strip(" .,;:-")
    return s or "Lịch hẹn"


# -------------------------------------------------------------------- chính
def phan_tich(raw: str, bay_gio: datetime | None = None) -> KetQua:
    bay_gio = bay_gio or datetime.now(MUI_GIO)
    if bay_gio.tzinfo is None:
        bay_gio = bay_gio.replace(tzinfo=MUI_GIO)

    khach = RE_EMAIL.findall(raw)
    kd = _bo_dau(raw)

    thoi_luong, _ = _boc_thoi_luong(raw, kd)
    ngay, da_noi_ngay = _boc_ngay(kd, bay_gio)

    canh_bao: list[str] = []
    doan_gio = False
    g = _boc_gio(kd)
    if g:
        gio, phut, span = g
        gio = _ap_buoi(gio, kd, span[0])
    else:
        # "30 phút nữa" / "2 tiếng nữa" -> lấy luôn giờ tương đối
        m = RE_TUONG_DOI.search(kd)
        if m and m.group(2).startswith(("phut", "phút", "tieng", "tiếng", "gio", "giờ")):
            so = int(m.group(1))
            moc = bay_gio + (timedelta(minutes=so) if m.group(2).startswith(("phut", "phút"))
                             else timedelta(hours=so))
            gio, phut = moc.hour, moc.minute
        else:
            gio, phut = 9, 0
            doan_gio = True
            canh_bao.append("Câu không nói giờ — tạm đặt 09:00, sửa lại nếu sai.")

    bat_dau = datetime(ngay.year, ngay.month, ngay.day, gio % 24, phut, tzinfo=MUI_GIO)

    # không nói ngày mà giờ đã trôi qua -> hiểu là ngày mai
    if not da_noi_ngay and bat_dau < bay_gio:
        bat_dau += timedelta(days=1)
    if bat_dau < bay_gio:
        canh_bao.append("Mốc giờ nằm trong quá khứ — kiểm tra lại ngày.")

    return KetQua(
        tieu_de=_lam_tieu_de(raw),
        bat_dau=bat_dau,
        ket_thuc=bat_dau + timedelta(minutes=thoi_luong),
        khach=khach,
        canh_bao=canh_bao,
        doan_gio=doan_gio,
    )


if __name__ == "__main__":
    import json
    import sys

    cau = " ".join(sys.argv[1:]) or "Call với anh Hùng lúc 22h tối chủ nhật tuần này. email duonghung@gmail.com"
    print(json.dumps(phan_tich(cau).nhu_dict(), ensure_ascii=False, indent=2))
