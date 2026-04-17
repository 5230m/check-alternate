# CLAUDE.md — Alternate Tag Checker

> File này được Claude Code tự động đọc khi mở project.
> Đọc kỹ trước khi làm bất cứ thứ gì. Không được tự thêm feature ngoài yêu cầu.

---

## PROJECT OVERVIEW
- **Tool**: Alternate Tag Checker — kiểm tra các thẻ alternate trong `<head>` của URL
- **Owner**: 5230m
- **Frontend**: HTML/CSS/JS thuần, không framework
- **Backend**: Node.js + Express (nếu cần)
- **Deploy**: Vercel (frontend) + VPS api.hanax.ink (backend nếu có)

---

## LOCAL DEV SETUP

```bash
# Chạy backend local (nếu có)
node server.js
# → http://localhost:8000

# Frontend: mở trực tiếp index.html trên browser
# hoặc dùng Live Server extension trên VS Code
```

API switch tự động — bắt buộc dùng pattern này:
```javascript
const API_BASE = window.location.hostname === 'localhost'
  ? 'http://localhost:8000'
  : 'https://api.hanax.ink';
```

---

## TOOL REQUIREMENTS

### Input
- Textarea nhận danh sách URL (1 URL/dòng)
- Tối đa 500 URLs mỗi lần
- Nút "Start", "Pause", "Cancel"
- Nút "Load sample" để test nhanh

### Processing
- Fetch HTML của từng URL, parse `<head>` để tìm các thẻ alternate
- Hiện progress realtime: "Đang xử lý X/Y (Z%)"
- Batch size: 5 concurrent requests
- Delay: 500ms giữa mỗi batch

### Các loại alternate tag cần check
- **hreflang** — `<link rel="alternate" hreflang="en" href="...">` (ví dụ: `hreflang="en"`, `hreflang="vi"`)
- **media mobile** — `<link rel="alternate" media="only screen and (max-width: 640px)" href="...">`
- **x-default** — `<link rel="alternate" hreflang="x-default" href="...">`

### Output
- Bảng kết quả gồm: URL gốc / Loại alternate / Giá trị / URL alternate
- Nút Export CSV
- Summary cuối: tổng URL đã check / tổng alternate tìm thấy / tổng lỗi / thời gian chạy

---

## TECHNICAL REQUIREMENTS

### Constants — đặt ở đầu file, không hardcode
```javascript
const MAX_CONCURRENT  = 5;
const BATCH_DELAY_MS  = 500;
const TIMEOUT_MS      = 10000;
const MAX_RETRIES     = 3;
const MAX_URLS        = 500;
```

### Retry Logic
- Timeout mỗi request: 10s (AbortController)
- Retry tối đa 3 lần khi gặp lỗi network hoặc 5xx
- Exponential backoff: 1s → 2s → 4s
- Gặp 429 → đợi 5s rồi retry
- Sau 3 lần vẫn fail → đánh dấu FAILED, log lỗi, tiếp tục URL tiếp theo

### Batch Processing
```javascript
// Pattern bắt buộc dùng
async function processBatch(urls, batchSize = MAX_CONCURRENT) {
  for (let i = 0; i < urls.length; i += batchSize) {
    const batch = urls.slice(i, i + batchSize);
    await Promise.all(batch.map(u => checkUrl(u)));
    updateProgress(i + batchSize, urls.length);
    await sleep(BATCH_DELAY_MS);
  }
}
```

---

## UI & DESIGN CONSTRAINTS

Đọc file CSS-SYSTEM.md trước khi viết bất kỳ dòng CSS nào.
Tuân thủ 100% tokens, component classes và layout patterns trong đó.
Không được tự thêm màu, font, spacing ngoài những gì đã định nghĩa trong CSS-SYSTEM.md.
### Component classes bắt buộc dùng
```
.btn-primary   → action chính
.btn-outline   → action phụ
.btn-danger    → cancel/delete
.card          → container
.input-field   → input/textarea
.badge-ok      → status 2xx
.badge-warn    → status 3xx
.badge-error   → status 4xx/5xx
```

---

## LOGGING REQUIREMENTS

Log Panel cố định ở bottom (collapsible), bắt buộc implement:

```javascript
// Logger object — copy y hệt pattern này
const Logger = {
  log(level, action, message) {
    const time = new Date().toLocaleTimeString('vi-VN');
    this._appendToPanel({ time, level, action, message });
    console[level === 'error' ? 'error' : 'log']
      (`[${time}] [${level.toUpperCase()}] [${action}]`, message);
  },
  info   (action, msg) { this.log('info',    action, msg); },
  warn   (action, msg) { this.log('warn',    action, msg); },
  error  (action, msg) { this.log('error',   action, msg); },
  success(action, msg) { this.log('success', action, msg); },
};
```

Format log:
```
[10:23:45] INFO    [BATCH_START] Bắt đầu xử lý 50 URLs, batch 5
[10:23:46] INFO    [REQUEST] https://example.com → 3 alternate tags (124ms)
[10:23:47] WARN    [RETRY] https://slow-site.com timeout, lần 1/3
[10:23:49] ERROR   [FAILED] https://dead-site.com → ERR_CONNECTION_REFUSED
[10:23:50] SUCCESS [DONE] Hoàn thành: 48 URLs, 120 alternates, 2 lỗi, 12.4s
```

Màu theo level:
- INFO → #60a5fa, WARN → #fbbf24, ERROR → #f87171, SUCCESS → #4ade80

Nút: "Copy logs" + "Clear" + hiện số entries

---

## CODE QUALITY

- Mỗi function có comment 1 dòng tiếng Việt giải thích làm gì
- Magic numbers đặt tên const ở đầu file
- Error messages hiện cho user bằng tiếng Việt
- Không viết function quá 80 dòng — tách nhỏ ra
- Không để console.log debug trong code cuối

---

## KHÔNG ĐƯỢC

- Tự thêm feature ngoài requirements
- Hardcode URL, số, timeout vào giữa code
- Để API key trong frontend code
- Dùng `var` — chỉ dùng `const` và `let`
- Bỏ qua error handling
- Commit code có lỗi console

---

## FILE STRUCTURE

```
check-alternate/
├── CLAUDE.md          ← file này
├── index.html         ← UI chính
├── assets/
│   ├── style.css      ← styles
│   └── logger.js      ← Logger object dùng chung
└── docs/
    ├── PROGRESS.md    ← tiến độ
    └── ERRORS.md      ← lỗi đã gặp
```

---

## SESSION SUMMARY PROMPT

Cuối mỗi session, paste cái này để update PROGRESS.md:
```
Tóm tắt session vừa rồi:
1. Đã làm gì
2. Lỗi gặp phải và cách fix
3. Điều cần lưu ý session sau
Ngắn gọn, bullet points, tiếng Việt.
```
