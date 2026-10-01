---
mo_ta: Hướng dẫn chị Ái Nhi tự xuất hồ sơ trợ lý "Kim cương" từ ChatGPT sang Second Brain mới — Claude không có quyền vào tài khoản ChatGPT của chị nên không tự lấy được
---

# Chuyển "Kim cương" từ ChatGPT sang Second Brain

> Việc này chị phải tự làm — Claude không đăng nhập được vào ChatGPT của chị. Mất khoảng 5 phút.

## Chị cần lấy gì
Những gì chị đã dạy cho "Kim cương" qua thời gian: cách xưng hô, văn phong, các nguyên tắc chị hay nhắc, thông tin về công việc/thương hiệu cá nhân của chị.

## Cách lấy — chọn 1 trong 2

### Cách A — Nếu "Kim cương" là một GPT riêng chị tạo (Explore GPTs → GPT của chị)
1. Mở GPT "Kim cương" trên ChatGPT.
2. Bấm biểu tượng ⋯ (hoặc Edit) → **Configure**.
3. Copy toàn bộ phần **Instructions** (hướng dẫn hệ thống chị đã viết cho nó).

### Cách B — Nếu chỉ là một cuộc trò chuyện dài, không phải GPT riêng
1. Vào Settings (ChatGPT) → **Data controls** → **Export data**.
2. ChatGPT gửi email kèm link tải một tệp zip chứa toàn bộ lịch sử chat.
3. Mở tệp `conversations.json`, tìm đoạn chat với "Kim cương", copy phần nội dung chị thấy quan trọng (không cần copy hết, chỉ phần mô tả cách làm việc/nguyên tắc).

## Dán vào đâu
Mở `~/brain/CLAUDE.md` bằng TextEdit hoặc bất kỳ trình soạn thảo nào, dán nội dung vừa copy vào cuối tệp, dưới một mục mới:

```
## 5. Những gì đã dạy cho Kim cương (mang sang từ ChatGPT)
<dán nội dung ở đây>
```

Lưu lại. Lần sau mở Claude trong `~/brain`, nó sẽ đọc và làm theo đúng những gì chị đã dạy "Kim cương" trước đây — không phải học lại từ đầu.
