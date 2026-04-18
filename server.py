"""
server.py — Backend FastAPI cho Alternate Tag Checker
Nhận danh sách URL, fetch HTML, parse alternate tags, trả về JSON.
"""

import asyncio
import re
import sys
import time
from datetime import datetime
from typing import List

# Buộc stdout dùng UTF-8 để print tiếng Việt trên Windows
if sys.stdout.encoding != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")

import httpx
import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

# ── Constants ──────────────────────────────────────────────────────────────────
TIMEOUT_S     = 10.0
MAX_RETRIES   = 3
RETRY_429_S   = 5.0
MAX_URLS      = 500
PORT          = 8000
USER_AGENT    = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/124.0.0.0 Safari/537.36"
)

# ── Logger (theo pattern CLAUDE.md) ───────────────────────────────────────────
class Logger:
    # In log ra console theo đúng format CLAUDE.md
    def _fmt(self, level: str, action: str, message: str) -> str:
        ts = datetime.now().strftime("%H:%M:%S")
        return f"[{ts}] {level:<7} [{action}] {message}"

    def info   (self, action: str, msg: str): print(self._fmt("INFO",    action, msg))
    def warn   (self, action: str, msg: str): print(self._fmt("WARN",    action, msg))
    def error  (self, action: str, msg: str): print(self._fmt("ERROR",   action, msg))
    def success(self, action: str, msg: str): print(self._fmt("SUCCESS", action, msg))

log = Logger()

# ── App & CORS ─────────────────────────────────────────────────────────────────
app = FastAPI(title="Alternate Tag Checker API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Pydantic models ────────────────────────────────────────────────────────────
class CheckRequest(BaseModel):
    urls: List[str]


# ── HTML attribute parser ──────────────────────────────────────────────────────
def get_attr(attrs: str, name: str) -> str | None:
    """Lấy giá trị một attribute từ chuỗi HTML attrs."""
    pattern = re.compile(
        rf'\b{re.escape(name)}\s*=\s*(?:"([^"]*)"|\'([^\']*)\'|([^\s/>]+))',
        re.IGNORECASE,
    )
    m = pattern.search(attrs)
    if not m:
        return None
    value = m.group(1) if m.group(1) is not None \
        else m.group(2) if m.group(2) is not None \
        else m.group(3)
    return value.strip()


# ── Alternate tag parser ───────────────────────────────────────────────────────
def parse_alternate_tags(html: str, source_url: str) -> list[dict]:
    """Parse tất cả thẻ <link rel='alternate'> trong <head> của HTML."""
    tags = []

    # Chỉ parse trong <head> để tránh false positive
    head_match = re.search(r"<head[\s\S]*?</head>", html, re.IGNORECASE)
    head = head_match.group(0) if head_match else html

    link_re = re.compile(r"<link\s([^>]+?)(?:\s*/?>)", re.IGNORECASE)

    for m in link_re.finditer(head):
        attrs = m.group(1)
        rel = get_attr(attrs, "rel")
        if not rel or rel.lower() != "alternate":
            continue

        href     = get_attr(attrs, "href") or ""
        hreflang = get_attr(attrs, "hreflang")
        media    = get_attr(attrs, "media")

        if hreflang:
            tag_type = "x-default" if hreflang.lower() == "x-default" else "hreflang"
            tags.append({"url": source_url, "type": tag_type, "value": hreflang, "altUrl": href})
        elif media:
            tags.append({"url": source_url, "type": "media", "value": media, "altUrl": href})

    return tags


# ── HTTP fetch với retry + exponential backoff ────────────────────────────────
async def fetch_html(client: httpx.AsyncClient, url: str, attempt: int = 0) -> str:
    """Fetch HTML của URL, retry tối đa MAX_RETRIES lần khi gặp lỗi."""
    try:
        resp = await client.get(url, timeout=TIMEOUT_S)

        if resp.status_code == 429:
            log.warn("RETRY", f"{url} → 429, đợi {int(RETRY_429_S)}s")
            await asyncio.sleep(RETRY_429_S)
            if attempt < MAX_RETRIES:
                return await fetch_html(client, url, attempt + 1)
            raise RuntimeError("429 Too Many Requests sau 3 lần thử")

        if resp.status_code >= 500:
            if attempt < MAX_RETRIES:
                log.warn("RETRY", f"{url} → HTTP {resp.status_code}, lần {attempt + 1}/{MAX_RETRIES}")
                await asyncio.sleep(1 * (2 ** attempt))
                return await fetch_html(client, url, attempt + 1)
            resp.raise_for_status()

        resp.raise_for_status()
        return resp.text

    except httpx.TimeoutException:
        if attempt < MAX_RETRIES:
            log.warn("RETRY", f"{url} timeout, lần {attempt + 1}/{MAX_RETRIES}")
            await asyncio.sleep(1 * (2 ** attempt))
            return await fetch_html(client, url, attempt + 1)
        raise RuntimeError(f"Timeout sau {MAX_RETRIES} lần thử")

    except (httpx.NetworkError, httpx.ConnectError) as exc:
        if attempt < MAX_RETRIES:
            log.warn("RETRY", f"{url} lỗi network, lần {attempt + 1}/{MAX_RETRIES}")
            await asyncio.sleep(1 * (2 ** attempt))
            return await fetch_html(client, url, attempt + 1)
        raise RuntimeError(str(exc))


# ── Kiểm tra một URL, trả về list kết quả ────────────────────────────────────
async def check_url(client: httpx.AsyncClient, url: str) -> list[dict]:
    """Fetch và parse alternate tags cho một URL."""
    t0 = time.time()
    try:
        html = await fetch_html(client, url)
        tags = parse_alternate_tags(html, url)
        ms   = int((time.time() - t0) * 1000)
        log.info("REQUEST", f"{url} → {len(tags)} alternate tags ({ms}ms)")

        if not tags:
            return [{"url": url, "type": "—", "value": "—", "altUrl": "(không tìm thấy)"}]
        return tags

    except Exception as exc:
        log.error("FAILED", f"{url} → {exc}")
        return [{"url": url, "type": "ERROR", "value": str(exc), "altUrl": "—"}]


# ── Endpoint POST /api/check-alternate ────────────────────────────────────────
@app.post("/api/check-alternate")
async def check_alternate(req: CheckRequest):
    """Nhận danh sách URL, trả về alternate tags tìm được."""
    urls = [u.strip() for u in req.urls if u.strip()]

    if not urls:
        return {"success": False, "error": "Danh sách URL rỗng."}

    if len(urls) > MAX_URLS:
        return {
            "success": False,
            "error": f"Tối đa {MAX_URLS} URLs mỗi lần. Hiện tại: {len(urls)}.",
        }

    t_start = time.time()
    log.info("BATCH_START", f"Bắt đầu xử lý {len(urls)} URLs")

    headers = {
        "User-Agent": USER_AGENT,
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.5",
        "Accept-Encoding": "gzip, deflate",
    }

    async with httpx.AsyncClient(
        headers=headers,
        follow_redirects=True,
        timeout=TIMEOUT_S,
    ) as client:
        # Chạy tất cả URL song song (frontend đã throttle theo batch)
        results_nested = await asyncio.gather(*[check_url(client, url) for url in urls])

    data    = [item for sublist in results_nested for item in sublist]
    elapsed = round(time.time() - t_start, 1)
    found   = sum(1 for r in data if r["type"] not in ("ERROR", "—"))
    errors  = sum(1 for r in data if r["type"] == "ERROR")

    log.success("DONE", f"Hoàn thành: {len(urls)} URLs, {found} alternates, {errors} lỗi, {elapsed}s")

    return {"success": True, "data": data}


# ── GET /fetch?url= — tương thích với frontend hiện tại ──────────────────────
@app.get("/fetch")
async def fetch_proxy(url: str):
    """Proxy fetch HTML cho một URL đơn (dùng cho frontend cũ)."""
    headers = {"User-Agent": USER_AGENT}
    async with httpx.AsyncClient(headers=headers, follow_redirects=True, timeout=TIMEOUT_S) as client:
        try:
            resp = await client.get(url)
            resp.raise_for_status()
            return resp.text
        except Exception as exc:
            log.error("FETCH_PROXY", f"{url} → {exc}")
            from fastapi import HTTPException
            raise HTTPException(status_code=502, detail=str(exc))


# ── Entry point ────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    log.info("SERVER", f"Khởi động Alternate Tag Checker API tại port {PORT}")
    uvicorn.run(app, host="0.0.0.0", port=PORT, log_level="warning")
