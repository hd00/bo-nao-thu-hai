#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""dia_diem.py — sổ địa điểm + dựng link Google Maps để quy hoạch đường đi.

Mục đích: câu "gặp anh Văn Minh ở nvt 13h mai" tự gắn địa chỉ thật và link bản đồ
vào sự kiện, để lúc đi không phải tìm lại. Và trả lời được "từ nhà tới đó bao xa,
đi đường nào" bằng một link chỉ đường dựng sẵn.

Sổ nằm ở  ~/.quan_tri_lich/dia_diem.json  — KHÔNG nằm trong kho mã, vì đây là
địa chỉ nhà riêng và chỗ học của con.

    python dia_diem.py bang                       # xem sổ
    python dia_diem.py duong --tu nha --den nvt   # link chỉ đường
"""

from __future__ import annotations

import json
import re
import sys
import urllib.parse
from pathlib import Path

import sys
for _luong in (sys.stdout, sys.stderr):
    try:
        _luong.reconfigure(encoding='utf-8', errors='replace')
    except Exception:
        pass

THU_MUC = Path(__import__("os").environ.get("QUAN_TRI_LICH_HOME") or (Path.home() / ".quan_tri_lich"))
TEP_SO = THU_MUC / "dia_diem.json"


def doc_so() -> dict:
    if not TEP_SO.exists():
        return {}
    try:
        return json.loads(TEP_SO.read_text(encoding="utf-8")) or {}
    except json.JSONDecodeError:
        return {}


def _truy_van(d: dict) -> str:
    """Toạ độ chính xác hơn địa chỉ chữ — ưu tiên toạ độ nếu có."""
    return d.get("toa_do") or d.get("dia_chi") or d.get("ten") or ""


def link_xem(d: dict) -> str:
    q = _truy_van(d)
    return f"https://www.google.com/maps/search/?api=1&query={urllib.parse.quote(q)}" if q else ""


def link_duong(tu: dict, den: dict, kieu: str = "driving") -> str:
    a, b = _truy_van(tu), _truy_van(den)
    if not (a and b):
        return ""
    return ("https://www.google.com/maps/dir/?api=1"
            f"&origin={urllib.parse.quote(a)}&destination={urllib.parse.quote(b)}"
            f"&travelmode={kieu}")


def tim_trong_cau(cau: str, so: dict | None = None):
    """Câu có nhắc tên/bí danh địa điểm nào không. Khớp theo RANH GIỚI TỪ.

    Trả (khoa, ban_ghi) của địa điểm khớp DÀI NHẤT — để "cong ty" thắng "ty".
    """
    so = so if so is not None else doc_so()
    thap = cau.lower()
    ung = []
    for khoa, d in so.items():
        if not isinstance(d, dict) or d.get("bo_qua"):
            continue
        for ten in [khoa, d.get("ten", "")] + list(d.get("bi_danh") or []):
            ten = (ten or "").strip().lower()
            if not ten:
                continue
            if re.search(rf"(?<![\w]){re.escape(ten)}(?![\w])", thap):
                ung.append((len(ten), khoa, d))
    if not ung:
        return None, None
    ung.sort(reverse=True)
    return ung[0][1], ung[0][2]


def _in_bang(so: dict) -> None:
    if not so:
        print(f"Sổ địa điểm trống. Tạo {TEP_SO} theo mẫu trong SO_DIA_DIEM.md.")
        return
    print(f"📍 Sổ địa điểm — {TEP_SO}\n")
    for khoa, d in so.items():
        if not isinstance(d, dict):
            continue
        thieu = "" if (d.get("dia_chi") or d.get("toa_do")) else "   ⚠️ CHƯA CÓ ĐỊA CHỈ"
        print(f"• {khoa}{thieu}")
        print(f"    tên     : {d.get('ten', '—')}")
        print(f"    địa chỉ : {d.get('dia_chi') or '(trống)'}")
        if d.get("toa_do"):
            print(f"    toạ độ  : {d['toa_do']}")
        if d.get("bi_danh"):
            print(f"    bí danh : {', '.join(d['bi_danh'])}")
        if link_xem(d):
            print(f"    bản đồ  : {link_xem(d)}")
        if d.get("ghi_chu"):
            print(f"    ghi chú : {d['ghi_chu']}")


def main() -> int:
    import argparse
    p = argparse.ArgumentParser(description="Sổ địa điểm & chỉ đường Google Maps")
    con = p.add_subparsers(dest="lenh", required=True)
    con.add_parser("bang", help="xem toàn bộ sổ")
    d = con.add_parser("duong", help="dựng link chỉ đường giữa hai điểm")
    d.add_argument("--tu", required=True)
    d.add_argument("--den", required=True)
    d.add_argument("--kieu", default="driving",
                   choices=["driving", "two_wheeler", "walking", "transit"])

    t = p.parse_args()
    so = doc_so()
    if t.lenh == "bang":
        _in_bang(so)
        return 0

    thieu = [k for k in (t.tu, t.den) if k not in so]
    if thieu:
        print(f"Không có trong sổ: {', '.join(thieu)}. Chạy `dia_diem.py bang` xem tên đúng.",
              file=sys.stderr)
        return 1
    link = link_duong(so[t.tu], so[t.den], t.kieu)
    if not link:
        print("Một trong hai điểm chưa có địa chỉ hoặc toạ độ.", file=sys.stderr)
        return 1
    print(f"{so[t.tu].get('ten', t.tu)}  →  {so[t.den].get('ten', t.den)}")
    print(link)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
