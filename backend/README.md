py -3.12 -m venv .venv
.venv\Scripts\Activate
python -m pip install --upgrade pip
pip install ipykernel
pip install -r requirements.txt
python -m ipykernel install --user --name project_1 --display-name "Python 3.12 (Langgraph_code)"


python main.py



## API Documentation

### Base URL

Khi chạy FastAPI trên máy local:

```text
http://127.0.0.1:8000
```

Swagger UI:

```text
http://127.0.0.1:8000/docs
```

### 1. Vehicles — Quản lý phương tiện

| Method | Endpoint | Description |
|---|---|---|
| GET | `/api/vehicles/` | Get all vehicles |
| GET | `/api/vehicles/{item_id}` | Get vehicle by ID |
| POST | `/api/vehicles/` | Create a new vehicle |
| PATCH | `/api/vehicles/{item_id}` | Update vehicle information |
| DELETE | `/api/vehicles/{item_id}` | Delete a vehicle |

**Query parameters for listing vehicles**

| Parameter | Type | Default | Constraint | Description |
|---|---|---|---|---|
| `skip` | Integer | `0` | `>= 0` | Number of records to skip |
| `limit` | Integer | `100` | `1–500` | Maximum number of records to return |

**Example requests**

```http
GET /api/vehicles/?skip=0&limit=20
GET /api/vehicles/1
POST /api/vehicles/
PATCH /api/vehicles/1
DELETE /api/vehicles/1
```

**HTTP status codes**

| Status code | Meaning |
|---|---|
| `200 OK` | Request completed successfully |
| `201 Created` | Vehicle created successfully |
| `204 No Content` | Vehicle deleted successfully |
| `400 Bad Request` | Invalid request or empty update |
| `404 Not Found` | Resource not found |
| `409 Conflict` | Database constraint violation |
| `422 Unprocessable Entity` | Input validation failed |
| `500 Internal Server Error` | Database operation failed |

### Other resources

The project also defines database models for depots, delivery orders, route plans, vehicle routes, and route stops. Their API endpoints should be documented after verifying the corresponding router files.


## RAG / Kho tri thức

### Cấu hình

Thêm vào `backend/.env` (không commit API key):

```env
GOOGLE_API_KEY=your_google_ai_studio_api_key
RAG_EMBEDDING_MODEL=gemini-embedding-001
QDRANT_COLLECTION=vrptw_documents
RAG_CHUNK_SIZE=1000
RAG_CHUNK_OVERLAP=150
```

Qdrant chạy ở chế độ local persistent tại `backend/data/qdrant`; file gốc được lưu tại `backend/data/uploads/`. Lần upload/search đầu tiên cần gọi Google Embedding API.

### Cài thư viện

```bash
pip install -r requirements.txt
```

### API

- `POST /api/rag/upload` — multipart fields `file` và `user_id`.
- `GET /api/rag/documents?user_id=default` — liệt kê tài liệu đã index.
- `POST /api/rag/search` — JSON `{ "query": "...", "user_id": "default", "limit": 5 }`.
- `DELETE /api/rag/documents/{document_id}?user_id=default` — xóa file và các vector.

Các định dạng: PDF, DOCX, CSV, XLSX, XLS, TXT, MD, PY; giới hạn upload 20 MB. PDF scan không có text layer cần OCR trước.

### Lưu ý bảo mật / deploy

Hiện `user_id` được nhận từ request giống các API chat hiện có; đây chưa phải cơ chế xác thực danh tính. Trước khi mở hệ thống cho nhiều người dùng, cần lấy user ID từ phiên đăng nhập/JWT phía server, không tin giá trị do client tự gửi. Qdrant local và thư mục uploads phù hợp phát triển cục bộ; production cần persistent disk hoặc dịch vụ vector/object storage bền vững.
