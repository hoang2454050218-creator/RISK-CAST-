# PROMPT CHO OMEN V2 (Claude Code)

## CONTEXT — Bạn đang ở project OMEN V2

OMEN V2 là Signal Intelligence Engine. Bên cạnh đó có RISKCAST V2 (project riêng) — Decision Intelligence Platform. Hai hệ thống cần nói chuyện được với nhau:

```
OMEN (port 8000) → signals → RISKCAST (port 8001) → decisions → WhatsApp alerts
```

Hiện tại OMEN đang chạy frontend demo (`npm run dev`), nhưng **API server (FastAPI) chưa chạy**.

RISKCAST V2 đã cấu hình xong client để gọi OMEN tại `http://localhost:8000`.

---

## NHIỆM VỤ 1: Khởi động OMEN API Server

Chạy OMEN API server trên port 8000 để RISKCAST có thể kết nối.

### Bước chạy:

```powershell
# Terminal mới (giữ nguyên terminal omen-demo đang chạy)
cd "C:\Users\RIM\OneDrive\Desktop\omen v2"
.venv\Scripts\activate

# Set PYTHONPATH để Python tìm được modules
$env:PYTHONPATH = "src"

# Chạy API server
uvicorn omen.main:app --host 0.0.0.0 --port 8000 --reload
```

### Kiểm tra:

```powershell
# Health check
curl http://localhost:8000/health

# Kết quả mong đợi:
# { "data": { "status": "healthy", "service": "omen", ... }, "meta": { "mode": "LIVE"|"DEMO", ... } }
```

---

## NHIỆM VỤ 2: Đảm bảo OMEN chạy LIVE mode với data thật

File `.env` hiện tại có:
- `OMEN_ALLOW_LIVE_MODE=true`
- `OMEN_MIN_REAL_SOURCE_RATIO=0.30`
- Các API key thật: `NEWS_API_KEY`, `AISSTREAM_API_KEY`, `FRED_API_KEY`, `ALPHAVANTAGE_API_KEY`

### Kiểm tra LIVE mode:

```powershell
# Check live gate status
curl -H "X-API-Key: dev-test-key" http://localhost:8000/api/v1/live-mode/status

# Check data sources
curl -H "X-API-Key: dev-test-key" http://localhost:8000/api/v1/multi-source/sources
```

### Nếu OMEN vẫn ở DEMO mode:

Kiểm tra lý do gate bị BLOCKED:
1. Xem log output khi server start — sẽ có dòng `live_gate_check` cho biết lý do
2. Đảm bảo `OMEN_ALLOW_LIVE_MODE=true` trong `.env`
3. Giảm `OMEN_MIN_REAL_SOURCE_RATIO` xuống `0.20` nếu cần (ít source online)
4. Kiểm tra kết nối mạng đến Polymarket API: `python -m scripts.polymarket_doctor`

---

## NHIỆM VỤ 3: Trigger Signal Generation từ data thật

Khi server đã chạy, trigger thu thập signals:

```powershell
# Refresh signals từ Polymarket
curl -X POST -H "X-API-Key: dev-test-key" "http://localhost:8000/api/v1/signals/refresh?limit=50&min_liquidity=500"

# Hoặc trigger background generator
curl -X POST -H "X-API-Key: dev-test-key" "http://localhost:8000/api/v1/signals/generate"

# Kiểm tra signals
curl -H "X-API-Key: dev-test-key" "http://localhost:8000/api/v1/signals/?limit=10&mode=live"
```

---

## NHIỆM VỤ 4: API Contract mà RISKCAST cần

RISKCAST V2 gọi các endpoints sau. Tất cả đều ĐÃ CÓ trong OMEN, chỉ cần đảm bảo chúng hoạt động:

### 4.1 Health Check
```
GET /health
```
Kết quả (sau ResponseWrapperMiddleware):
```json
{
  "data": { "status": "healthy", "service": "omen" },
  "meta": { "mode": "LIVE", "real_source_coverage": 0.57, "live_gate_status": "OPEN", ... }
}
```

### 4.2 List Signals
```
GET /api/v1/signals/?limit=100&status=ACTIVE
Headers: X-API-Key: dev-test-key
```
Kết quả (sau ResponseWrapperMiddleware):
```json
{
  "data": {
    "signals": [
      {
        "signal_id": "OMEN-LIVEABC123",
        "title": "Red Sea shipping disruption probability",
        "description": "...",
        "probability": 0.72,
        "confidence_score": 0.85,
        "confidence_level": "HIGH",
        "category": "GEOPOLITICAL",
        "geographic": {
          "regions": ["Middle East", "Red Sea"],
          "chokepoints": ["bab-el-mandeb", "suez"]
        },
        "temporal": {
          "event_horizon": "2026-06-30",
          "resolution_date": "2026-06-30T00:00:00Z"
        },
        "evidence": [
          { "source": "Polymarket", "source_type": "market", "url": "..." }
        ],
        "generated_at": "2026-02-13T10:00:00Z"
      }
    ],
    "total": 50,
    "limit": 100,
    "offset": 0
  },
  "meta": { "mode": "LIVE", "real_source_coverage": 0.57, ... }
}
```

**RISKCAST cần các fields này từ mỗi signal:**
- `signal_id` — ID duy nhất
- `title` — Tên sự kiện
- `description` — Mô tả chi tiết
- `probability` — Xác suất (0-1), từ market data
- `confidence_score` — Độ tin cậy (0-1), OMEN tính
- `category` — GEOPOLITICAL, WEATHER, ECONOMIC, INFRASTRUCTURE, SECURITY, OTHER
- `geographic.chokepoints` — List chokepoints: "suez", "red_sea", "panama", "malacca", "hormuz", "bab-el-mandeb"
- `geographic.regions` — List regions
- `temporal.event_horizon` — Khi nào xảy ra
- `temporal.resolution_date` — Khi nào market resolve
- `evidence` — Array evidence items: `{ source, source_type, url }`
- `generated_at` hoặc `created_at` — Timestamp tạo signal

### 4.3 Get Single Signal
```
GET /api/v1/signals/{signal_id}
Headers: X-API-Key: dev-test-key
```

### 4.4 Refresh Signals (trigger real data fetch)
```
POST /api/v1/signals/refresh?limit=50
Headers: X-API-Key: dev-test-key
```

### 4.5 Multi-Source Signals
```
GET /api/v1/multi-source/signals
Headers: X-API-Key: dev-test-key
```

### 4.6 WebSocket (real-time updates)
```
ws://localhost:8000/ws
```
RISKCAST expects messages:
```json
{ "type": "signal_emitted", "data": { ...signal fields... } }
```

---

## NHIỆM VỤ 5: Tối ưu cho RISKCAST Integration

### 5.1 Đảm bảo ResponseWrapperMiddleware hoạt động

Middleware này wrap tất cả JSON responses trong `{ "data": ..., "meta": {...} }`. RISKCAST dựa vào format này.

Kiểm tra: Response từ `/api/v1/signals/` phải có cả `data` và `meta` keys.

### 5.2 Auth trong Dev Mode

RISKCAST gửi header `X-API-Key: dev-test-key`. Với `OMEN_DEV_AUTH_BYPASS=true` trong `.env`, mọi request với key `dev-test-key` đều được accept.

### 5.3 CORS

RISKCAST frontend chạy trên `http://localhost:5173` hoặc `http://localhost:3000`. Đảm bảo CORS config trong OMEN cho phép các origins này (hiện tại OMEN dev mode cho phép `*`).

---

## NHIỆM VỤ 6: Test End-to-End

Sau khi OMEN API server đã chạy, test từ RISKCAST:

```powershell
# Từ RISKCAST V2 directory
cd "C:\Users\RIM\OneDrive\Desktop\RISK CAST V2"
.venv\Scripts\activate
python scripts/test_omen_connection.py
```

Script này sẽ:
1. Check OMEN health (port 8000) 
2. Check RISKCAST health (port 8001)
3. Fetch signals từ OMEN
4. Parse thành RISKCAST format
5. Báo cáo kết quả

Thêm `--refresh` để trigger signal refresh:
```powershell
python scripts/test_omen_connection.py --refresh
```

---

## NHIỆM VỤ 7: Background Signal Generator

OMEN có background generator tự động fetch data định kỳ. Kiểm tra nó đã chạy chưa:

```powershell
curl -H "X-API-Key: dev-test-key" http://localhost:8000/api/v1/signals/generator/status
```

Nếu chưa chạy, nó tự start khi server khởi động (xem `omen.infrastructure.background.signal_generator`).

Config trong `.env`:
```
OMEN_SIGNAL_POLL_INTERVAL=60          # Fetch mỗi 60 giây
OMEN_PERF_GENERATOR_MIN_INTERVAL_SECONDS=30
OMEN_PERF_GENERATOR_MAX_INTERVAL_SECONDS=300
```

---

## TÓM TẮT — Checklist

- [ ] 1. Mở terminal mới, chạy `uvicorn omen.main:app --host 0.0.0.0 --port 8000 --reload`
- [ ] 2. Check health: `curl http://localhost:8000/health`
- [ ] 3. Check live mode: `curl -H "X-API-Key: dev-test-key" http://localhost:8000/api/v1/live-mode/status`
- [ ] 4. Trigger refresh: `curl -X POST -H "X-API-Key: dev-test-key" "http://localhost:8000/api/v1/signals/refresh?limit=50"`
- [ ] 5. List signals: `curl -H "X-API-Key: dev-test-key" "http://localhost:8000/api/v1/signals/?limit=5"`
- [ ] 6. Verify response has `{ "data": { "signals": [...] }, "meta": { "mode": "LIVE|DEMO" } }`
- [ ] 7. Fix bất kỳ lỗi nào (import errors, missing dependencies, network issues)
- [ ] 8. Chạy test từ RISKCAST: `python scripts/test_omen_connection.py`

---

## KHI GẶP LỖI

### Import Error
```
ModuleNotFoundError: No module named 'omen'
```
**Fix:** Set `PYTHONPATH=src` trước khi chạy uvicorn.

### Database Connection Error
```
connection to server at "localhost" (::1), port 5432 failed
```
**Fix:** OMEN có thể chạy KHÔNG cần PostgreSQL (dùng in-memory repository). Kiểm tra startup logs.

### Polymarket Connection Error
```
SourceUnavailableError: Failed to fetch from Polymarket
```
**Fix:** Chạy `python -m scripts.polymarket_doctor` để kiểm tra DNS/network.

### Auth Error (401/403)
```
{"error": "UNAUTHORIZED", "message": "Invalid API key"}
```
**Fix:** Đảm bảo `OMEN_DEV_AUTH_BYPASS=true` và dùng header `X-API-Key: dev-test-key`.

---

## ARCHITECTURE REFERENCE

```
┌─────────────────────────────────────────────────────────┐
│                    OMEN V2 (port 8000)                  │
│                                                         │
│  ┌─────────────┐  ┌──────────┐  ┌───────────────┐     │
│  │ Polymarket  │  │ NewsAPI  │  │  AISStream    │     │
│  │  (real)     │  │  (real)  │  │   (real)      │     │
│  └──────┬──────┘  └────┬─────┘  └──────┬────────┘     │
│         └───────────────┼───────────────┘               │
│                         ▼                               │
│              ┌──────────────────┐                       │
│              │ Signal Pipeline  │                       │
│              │ (validate/enrich)│                       │
│              └────────┬─────────┘                       │
│                       ▼                                 │
│              ┌──────────────────┐                       │
│              │  Signal Repo     │                       │
│              │  (in-memory)     │                       │
│              └────────┬─────────┘                       │
│                       ▼                                 │
│              ┌──────────────────┐                       │
│              │   REST API       │──── /api/v1/signals/  │
│              │   WebSocket      │──── /ws               │
│              └──────────────────┘                       │
└────────────────────────┬────────────────────────────────┘
                         │ HTTP + WebSocket
                         ▼
┌─────────────────────────────────────────────────────────┐
│                  RISKCAST V2 (port 8001)                │
│                                                         │
│  ┌──────────────┐                                      │
│  │ OmenClient   │←─ Fetches signals from OMEN          │
│  └──────┬───────┘                                      │
│         ▼                                               │
│  ┌──────────────┐  ┌──────────────┐                    │
│  │   ORACLE     │  │   RISKCAST   │                    │
│  │ (Reality)    │→ │ (Decisions)  │                    │
│  └──────────────┘  └──────┬───────┘                    │
│                           ▼                             │
│                    ┌──────────────┐                     │
│                    │   ALERTER    │──── WhatsApp        │
│                    └──────────────┘                     │
└─────────────────────────────────────────────────────────┘
```
