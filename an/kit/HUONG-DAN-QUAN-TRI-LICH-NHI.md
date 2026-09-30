---
mo_ta: Hướng dẫn cài quan-tri-lich cho chị Ái Nhi — dùng khoá Google riêng của chị, không dùng chung với Hùng
---

# Cài đặt lịch cho chị Nhi (~15 phút, làm một lần)

Mã nguồn đã portable (dùng `Path.home()`), chỉ cần chị tự tạo khoá Google của riêng chị.
**Không dùng khoá của Hùng** — dùng chung sẽ làm lịch hai người lẫn vào nhau.

## Bước 1 — Đặt script vào bộ não
Chép cả thư mục `quan-tri-lich-nhi/` vào `~/brain/.claude/skills/quan-tri-lich/`.

## Bước 2 — Tạo khoá Google riêng (chị tự làm, dùng Google của chị)
1. Vào https://console.cloud.google.com/ → đăng nhập bằng Google của chị Nhi.
2. Tạo dự án mới (New Project), tên tuỳ ý, vd "Lich Ai Nhi".
3. Vào **APIs & Services → Library**, tìm "Google Calendar API", bấm **Enable**.
4. Vào **APIs & Services → OAuth consent screen**:
   - User Type: **External**.
   - Điền tên app, email chị — bấm Save.
   - Ở mục Test users, thêm chính email Gmail của chị.
5. Vào **APIs & Services → Credentials → Create Credentials → OAuth client ID**:
   - Application type: **Desktop app**.
   - Tạo xong, bấm **Download JSON** — lưu tệp này, ví dụ đặt tên `client_secret.json`.

## Bước 3 — Cấp quyền lần đầu
Mở Terminal:
```
cd ~/brain/.claude/skills/quan-tri-lich/scripts
python3 lich.py cap-quyen --client-secret /đường/dẫn/tới/client_secret.json
```
Trình duyệt tự mở, đăng nhập đúng tài khoản Google của chị, bấm cho phép.
Thấy dòng "unverified app" (ứng dụng chưa xác minh) thì bấm **Advanced → Go to (unsafe)** —
bình thường, vì đây là khoá riêng chị vừa tự tạo, không phải app công khai.

## Bước 4 — Dùng thử
```
python3 lich.py xem --ngay 7
```
Ra danh sách lịch 7 ngày tới (có thể rỗng nếu lịch trống) là xong.

## Từ đó về sau
Nói với Claude trong `~/brain`: "đặt lịch với X lúc Y giờ ngày Z" — AI tự gọi đúng script này.
