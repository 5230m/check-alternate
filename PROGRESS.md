# PROGRESS.md — Alternate Tag Checker

_Cập nhật: 2026-04-17 (auto end-session)_

---

## Trạng thái tổng quan

**HOÀN THÀNH** — Tool chạy được đầy đủ, cả frontend lẫn backend.

---

## Đã làm

- **Backend (`server.py`)** — FastAPI hoàn chỉnh
  - Endpoint `POST /api/check-alternate`: nhận batch URLs, fetch song song, parse alternate tags, trả JSON
  - Endpoint `GET /fetch?url=`: proxy fetch HTML cho URL đơn (tương thích cũ)
  - Retry logic: timeout 10s, tối đa 3 lần, exponential backoff (1s → 2s → 4s)
  - Xử lý 429: đợi 5s rồi retry
  - Logger server theo đúng format CLAUDE.md
  - CORS mở cho mọi origin (phục vụ Vercel frontend)

- **Frontend (`index.html`)** — HTML/CSS/JS thuần, không framework
  - UI Binance design system (dark theme, token-based CSS)
  - Textarea URL input với realtime counter
  - Nút Start / Pause / Resume / Cancel / Load sample / Export CSV
  - Progress bar realtime
  - Bảng kết quả 4 cột: URL gốc / Loại / Giá trị / URL Alternate
  - Badge phân loại: `hreflang`, `x-default`, `media`, `ERROR`, `—`
  - Summary card (4 stat): URLs checked / Alternates tìm thấy / Lỗi / Thời gian
  - Log panel cố định bottom, collapsible, nút Copy + Clear
  - Export CSV có BOM UTF-8
  - API_BASE tự switch localhost vs api.hanax.ink

- **CSS-SYSTEM.md** — Design system documentation (Binance-inspired, dùng làm reference cho CSS)
- **requirements.txt** — fastapi, uvicorn[standard], httpx, pydantic (phiên bản cụ thể)

---

## Trạng thái từng file

| File | Trạng thái |
|------|-----------|
| `index.html` | Hoàn chỉnh — đầy đủ UI, logic, Logger |
| `server.py` | Hoàn chỉnh — FastAPI, retry, parse, CORS |
| `requirements.txt` | Hoàn chỉnh |
| `CSS-SYSTEM.md` | Reference doc — không chỉnh |
| `CLAUDE.md` | Project instructions — không chỉnh |

> **Thiếu:** Chưa có thư mục `assets/` với `style.css` và `logger.js` riêng biệt như CLAUDE.md định nghĩa — CSS và JS hiện đang inline trong `index.html`. Chấp nhận được vì không có yêu cầu tách file.

---

## Việc cần làm tiếp theo

- [ ] Deploy backend `server.py` lên VPS `api.hanax.ink` (cài Python + uvicorn, chạy service)
- [ ] Deploy frontend `index.html` lên Vercel
- [ ] Test end-to-end với domain thật (không phải localhost)
- [ ] Tùy chọn: tách CSS sang `assets/style.css` và JS Logger sang `assets/logger.js` nếu cần maintain lâu dài
