#!/bin/bash
# =============================================================================
# MOMAT.SH — MỞ MẮT TRÌNH DUYỆT GỠ LỖI (macOS) CHO CHỊ ÁI NHI
# Mở Google Chrome cổng 9222 với Profile riêng ~/debug_profile
# =============================================================================
set -uo pipefail

CONG=9222
HO_SO="$HOME/debug_profile"
CHROME="/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"

TRANG=(
  "https://gemini.google.com/"
  "https://notebooklm.google.com/"
  "https://chat.zalo.me/"
  "https://drive.google.com/"
)

echo "====================================================================="
echo "  🌸 MỞ MẮT — KHỞI ĐỘNG TRÌNH DUYỆT CÓ MẮT & TAY (PORT $CONG)"
echo "====================================================================="

echo "[1/4] Kiểm tra tiến trình giữ cổng $CONG..."
CHU_CONG="$(lsof -ti:$CONG 2>/dev/null | head -1 || true)"
if [ -n "$CHU_CONG" ]; then
  TEN="$(ps -p "$CHU_CONG" -o comm= 2>/dev/null || true)"
  echo "    Cổng $CONG đang chạy bởi PID $CHU_CONG ($TEN). Đang làm mới..."
  kill -9 "$CHU_CONG" 2>/dev/null || true
  sleep 1
else
  echo "    Cổng $CONG đang sẵn sàng."
fi

echo "[2/4] Kiểm tra Google Chrome..."
if [ ! -x "$CHROME" ]; then
  echo "    ❌ Không tìm thấy Google Chrome tại: $CHROME"
  echo "    Chị Nhi vui lòng cài Google Chrome vào thư mục Applications nhé."
  exit 1
fi
echo "    ✅ Google Chrome: Sẵn sàng"

echo "[3/4] Khởi động Chrome Debug (Hồ sơ riêng: $HO_SO)..."
mkdir -p "$HO_SO"
"$CHROME" \
  --remote-debugging-port=$CONG \
  --user-data-dir="$HO_SO" \
  --no-first-run \
  --no-default-browser-check \
  "${TRANG[@]}" >/dev/null 2>&1 &

echo "[4/4] Kiểm tra kết nối cổng $CONG..."
for i in $(seq 1 15); do
  if curl -s --max-time 2 "http://127.0.0.1:$CONG/json/version" >/dev/null 2>&1; then
    echo "    ✅ [OK] Cổng $CONG đã mở thành công sau ${i}s! AI Agent đã kết nối được."
    echo ""
    echo "  👉 LẦN ĐẦU TIÊN: Cửa sổ Chrome này sẽ yêu cầu đăng nhập."
    echo "     Chị Nhi chỉ cần đăng nhập Google / Zalo MỘT LẦN DUY NHẤT."
    echo "     Hồ sơ sẽ được lưu vĩnh viễn, các phiên sau AI tự động có quyền truy cập."
    exit 0
  fi
  sleep 1
done

echo "    ⚠️ Cổng $CONG phản hồi chậm. Anh vui lòng kiểm tra lại lệnh: lsof -i:$CONG"
exit 1
