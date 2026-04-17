# ERRORS.md — Alternate Tag Checker

_Cập nhật: 2026-04-17 (auto end-session)_

---

## Lỗi đã gặp & cách fix

### 1. stdout encoding lỗi trên Windows (server.py)
- **Triệu chứng:** `UnicodeEncodeError` khi print tiếng Việt ra terminal Windows
- **Nguyên nhân:** Windows dùng cp1252 mặc định, tiếng Việt cần UTF-8
- **Fix:** Thêm reconfigure ngay đầu file trước khi import khác:
  ```python
  if sys.stdout.encoding != "utf-8":
      sys.stdout.reconfigure(encoding="utf-8")
      sys.stderr.reconfigure(encoding="utf-8")
  ```

### 2. Batch timeout quá ngắn (frontend)
- **Triệu chứng:** Cả batch 5 URLs bị abort trước khi server kịp retry từng URL
- **Nguyên nhân:** Frontend dùng cùng `TIMEOUT_MS = 10s` cho cả batch, nhưng server có thể mất tới 10s × 3 retries = 30s cho 1 URL
- **Fix:** Thêm `BATCH_TIMEOUT_MS = TIMEOUT_MS * 5` cho AbortController của batch request, giữ `TIMEOUT_MS` chỉ dùng làm reference

### 3. XSS trong log panel
- **Triệu chứng:** Nếu URL chứa `<script>` hoặc HTML entities, log panel có thể bị inject
- **Nguyên nhân:** innerHTML render log entry trực tiếp từ URL
- **Fix:** Thêm hàm `escHtml()` và wrap tất cả URL/message khi render vào log entry

### 4. CSV export bị lỗi encoding tiếng Việt trên Excel Windows
- **Triệu chứng:** File CSV mở bằng Excel hiện ký tự rác
- **Nguyên nhân:** Excel Windows mặc định đọc CSV theo Windows-1252, không tự nhận UTF-8
- **Fix:** Thêm BOM (`\uFEFF`) vào đầu Blob: `'\uFEFF' + header + rows`

---

## Lỗi tiềm ẩn chưa fix

- **CORS trên VPS:** Nếu `api.hanax.ink` đứng sau nginx, cần đảm bảo nginx không strip CORS headers của FastAPI — kiểm tra khi deploy
- **Redirect vô hạn:** `follow_redirects=True` trong httpx có thể loop nếu site có redirect cycle — httpx mặc định giới hạn 20 redirects, đủ an toàn
- **Memory:** Fetch 500 URLs × HTML lớn có thể dùng nhiều RAM trên server — cân nhắc giới hạn response size nếu VPS yếu
