#!/bin/bash
# =============================================================================
# KHỞI TẠO BỘ NÃO CÁ NHÂN + ĐỒNG BỘ GITHUB — DÀNH CHO ANH NGUYỄN HẢI MINH
# macOS · Độc lập 100% · KHÔNG sudo · KHÔNG cần Homebrew
# =============================================================================
set -e
trap 'echo ""; echo "Co gian doan. Anh Minh chup man hinh gui Hung nhe, Hung boc lot."' ERR

echo "=========================================================="
echo "KHOI TAO BO NAO CA NHAN — ANH NGUYEN HAI MINH"
echo "=========================================================="

# --- 1. Duong dan he thong -------------------------------------------------
mkdir -p "$HOME/.local/bin"
grep -q '.local/bin' "$HOME/.zshrc" 2>/dev/null || echo 'export PATH="$HOME/.local/bin:$PATH"' >> "$HOME/.zshrc"
export PATH="$HOME/.local/bin:$PATH"

# --- 2. Claude Code --------------------------------------------------------
echo "== [1/5] Kiem tra Claude Code =="
if command -v claude >/dev/null 2>&1; then
  echo "   Da co san: $(command -v claude)"
else
  curl -fsSL https://claude.ai/install.sh | bash
fi
echo "   Claude Code: san sang"

# --- 3. Bo nao 9 ngan ------------------------------------------------------
echo "== [2/5] Dung cau truc Bo Nao tai ~/brain =="
BRAIN="$HOME/brain"
mkdir -p "$BRAIN"/{00-inbox,01-to-do,10-daily,20-meetings,30-projects,50-learning,70-decisions,90-people,private}

cat << 'GITIGNORE' > "$BRAIN/.gitignore"
.DS_Store
private/*
!private/.env.example
!private/README.md
GITIGNORE

cat << 'ENV' > "$BRAIN/private/.env.example"
# Dien API key ca nhan cua anh Minh tai day (khong chia se ra ngoai)
ANTHROPIC_API_KEY=
GITIGNORE_NOTE=thu muc private/ da bi khoa, khong bao gio len GitHub
ENV

cat << 'PEOPLE' > "$BRAIN/90-people/README.md"
# Ngan 90-people — Ho so nguoi lam viec cung
Moi doi tac, khach hang, chuyen gia la 1 file markdown rieng (ten khong kem ngay):
Vi du: `hung-har.md`, `tran-lien-phuong.md`, `nguyen-the-anh.md`
PEOPLE

cat << 'MD' > "$BRAIN/CLAUDE.md"
---
mo_ta: Hiến pháp AI cá nhân của Nguyễn Hải Minh — chống ngợp chữ, chống văn AI, tích luỹ cuối ngày
---

# BỘ NÃO CÁ NHÂN — NGUYỄN HẢI MINH

AI đọc tệp này đầu MỌI phiên làm việc trong thư mục `~/brain`.

## 1. Luật viết — quan trọng nhất, đọc kỹ

Anh Minh làm nghề chữ nghĩa và **bắt bài được văn AI ngay từ câu đầu**.
Viết sai giọng là hỏng cả phiên.

- **Câu ngắn. Mỗi ý một dấu chấm.** Không nối ba mệnh đề vào một câu.
- **Cấm sáo ngữ AI:** "trong bối cảnh", "không chỉ… mà còn", "đáng chú ý là",
  "điều này cho thấy", "hãy cùng khám phá", mở bài bằng định nghĩa chung chung.
- **Cấm liệt kê ba vế cân đối** kiểu "nhanh hơn, rẻ hơn, tốt hơn".
- **Chống ngợp chữ:** trả lời gạch đầu dòng, đi thẳng vào việc. Không dẫn nhập.
- **Ít dấu vết kỹ thuật.** Mỗi từ kỹ thuật phải gắn với một hành động cụ thể.
  Không được để anh ấy phải đoán nghĩa. Nguyên văn anh ấy nói 29/09/2026:
  *"càng đọc thấy nó càng ngoằng ngèo"*, *"nhiều dấu vết kỹ thuật nên đọc cũng không rành lắm"*.
- **Mở bài bằng một hình ảnh cụ thể**, không bằng luận điểm trừu tượng —
  đúng cách anh ấy vẫn viết: ván cờ vua, con sói biển, chiếc khăn lau Apple.
- **Dám nói ngược đám đông** khi có căn cứ, và tự hạ giọng đúng lúc.

## 2. Luật số liệu — không được bịa

- Con số nào **chưa đo** thì ghi thẳng **CHƯA ĐO**. Không điền số cho đẹp.
- Lời khách kể lại là **[TỰ KHAI]**. Chỉ thành **[ĐÃ ĐỐI SOÁT]** khi có nguồn thứ hai.
- Trước khi viết một con số ra cho người ngoài đọc, **đếm lại tại chỗ**.

## 3. Chín ngăn

- `00-inbox/` — ném vào, không phân loại. Ý tưởng, link, ghi chú nhanh.
- `01-to-do/` — việc đang treo. AI đọc ngăn này mỗi sáng.
- `10-daily/` — nhật ký ngày, AI tự sinh.
- `20-meetings/` — biên bản gặp khách.
- `30-projects/` — từng khách, từng dự án. Về sau thành điển cứu.
- `50-learning/` — bài học, nguyên lý rút ra.
- `70-decisions/` — quyết định đã chốt kèm LÝ DO.
- `90-people/` — hồ sơ người làm việc cùng.
- `private/` — khoá API, dữ liệu mật. Đã khoá, không bao giờ lên GitHub.

## 4. Nghi thức cuối ngày

Khi anh Minh nói "tổng kết ngày", "xong rồi", hoặc cuối phiên:

1. AI tự đọc lại những việc đã trao đổi trong phiên.
2. Tự ghi vào `10-daily/YYYY-MM-DD.md` theo bốn mục:
   **Đã làm · Bẫy đã gặp · Số lần phải làm lại · Việc tồn**.
3. Ghi **số lần**, đừng ghi tính từ. "Gặp 3 lần" lọc được, "hay gặp" thì không.
4. Nhắc anh Minh gõ `luu "..."` để đẩy lên GitHub.
5. **Không bắt anh Minh tự gõ chép tay cuối ngày.**

## 5. Việc chuyên môn

Thuật ngữ giữ nguyên tiếng Anh: brand, positioning, insight, case-study,
SIM (Strategy Integration Model), BIM (Brand Integration Model).

Khi dựng case-study từ bài đã xuất bản, theo khung
**Bối cảnh – Cách làm – Kết quả**, và chừa ô `[CẦN ĐIỀN]` ở chỗ chưa có số thật.
MD

echo "   Xong 9 ngan + hien phap CLAUDE.md"

# --- 4. GitHub CLI (khong sudo, khong Homebrew) ----------------------------
echo "== [3/5] Kiem tra GitHub CLI =="
if command -v gh >/dev/null 2>&1; then
  echo "   Da co san: $(gh --version 2>/dev/null | head -1)"
else
  case "$(uname -m)" in
    arm64)  KIEN_TRUC="arm64" ;;
    x86_64) KIEN_TRUC="amd64" ;;
    *)      echo "   Khong nhan ra chip $(uname -m) — bo qua buoc nay"; KIEN_TRUC="" ;;
  esac
  if [ -n "$KIEN_TRUC" ]; then
    BAN="2.101.0"
    TEP="gh_${BAN}_macOS_${KIEN_TRUC}"
    TAM="$(mktemp -d)"
    echo "   Dang tai gh ${BAN} cho ${KIEN_TRUC}..."
    curl -fsSL -o "$TAM/gh.zip" \
      "https://github.com/cli/cli/releases/download/v${BAN}/${TEP}.zip"
    unzip -q "$TAM/gh.zip" -d "$TAM"
    cp "$TAM/${TEP}/bin/gh" "$HOME/.local/bin/gh"
    chmod +x "$HOME/.local/bin/gh"
    rm -rf "$TAM"
    echo "   Da cai: $("$HOME/.local/bin/gh" --version 2>/dev/null | head -1)"
  fi
fi

# --- 5. Nut LUU — 1 chu thay cho 3 lenh ------------------------------------
echo "== [4/5] Tao nut luu =="
# Kiem TUNG HAM RIENG. Ban dau chi kiem 'luu' -> may da cai tu truoc se
# khong bao gio nhan duoc ham 'lay' them sau nay. Anh Minh dung 3 may nen
# loi nay se dinh ngay. (Phat hien 29/09/2026)
THEM=0
if ! grep -q '^lay()' "$HOME/.zshrc" 2>/dev/null; then
  cat << 'LAY' >> "$HOME/.zshrc"

# lay : keo ban moi nhat ve TRUOC khi bat dau lam (Hung soan cho anh Minh)
lay() { git pull --rebase --autostash; }
LAY
  THEM=1; echo "   Da them: lay"
fi
if ! grep -q '^luu()' "$HOME/.zshrc" 2>/dev/null; then
  cat << 'LUU' >> "$HOME/.zshrc"

# luu : add + commit + push goi trong 1 chu, XONG viec thi go
luu() { git add -A && git commit -m "${1:-cap nhat}" && git push; }
LUU
  THEM=1; echo "   Da them: luu"
fi
if [ "$THEM" = "0" ]; then
  echo "   Ca hai da co san, khong ghi de"
else
  echo "   Mo may: lay   |   Xong viec: luu \"mo ta\""
fi

# --- 6. Ket --------------------------------------------------------------
echo "== [5/5] Kiem lai =="
echo "   brain     : $([ -d "$BRAIN" ] && echo OK || echo THIEU)"
echo "   claude    : $(command -v claude >/dev/null 2>&1 && echo OK || echo THIEU)"
echo "   gh        : $(command -v gh >/dev/null 2>&1 && echo OK || echo THIEU)"
echo ""
echo "=========================================================="
echo "XONG! BO NAO CA NHAN DA SAN SANG"
echo "=========================================================="
echo ""
echo "CON 2 VIEC ANH MINH TU LAM, MOI VIEC 1 DONG:"
echo ""
echo "  1) Noi may voi GitHub (lam 1 lan):"
echo "       gh auth login -w -p https"
echo "     No mo trinh duyet, anh bam dong y la xong."
echo ""
echo "  2) Dua 1 thu muc len GitHub (lam 1 lan cho moi thu muc):"
echo "       cd <thu muc cua anh>"
echo "       git init && git add -A && git commit -m \"lan dau\""
echo "       gh repo create <ten-kho> --private --source=. --remote=origin --push"
echo ""
echo "  Tu do ve sau, chi con 2 chu:"
echo "       lay                      <- MO MAY thi go, keo ban moi nhat ve"
echo "       luu \"xong bai mui huong\"  <- XONG VIEC thi go"
echo ""
echo "  QUAN TRONG khi anh dung NHIEU MAY: mo may nao cung go lay truoc."
echo "  Khong lam vay thi 2 may sua cung 1 cho se dung nhau."
echo ""
echo "LUU Y: de thu muc lam viec o o may. DUNG de trong Google Drive."
echo "       Drive dong bo tung tep le, Git can ca cum doi cung nhip -> hong kho."
echo ""
