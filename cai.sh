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
echo "   Xong 9 ngan"

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
if grep -q '^luu()' "$HOME/.zshrc" 2>/dev/null; then
  echo "   Da co san, khong ghi de"
else
  cat << 'LUU' >> "$HOME/.zshrc"

# --- nut luu: git add + commit + push goi trong 1 chu (Hung soan cho anh Minh) ---
luu() { git add -A && git commit -m "${1:-cap nhat}" && git push; }
LUU
  echo "   Xong. Tu gio go: luu \"mo ta viec vua lam\""
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
echo "  Tu do ve sau, moi lan xong viec chi go DUNG 1 DONG:"
echo "       luu \"xong bai mui huong\""
echo ""
echo "LUU Y: de thu muc lam viec o o may. DUNG de trong Google Drive."
echo "       Drive dong bo tung tep le, Git can ca cum doi cung nhip -> hong kho."
echo ""
