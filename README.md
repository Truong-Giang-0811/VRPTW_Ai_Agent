# AI Agent VRPTW

Hệ thống quản lý giao hàng và tối ưu tuyến đường **VRPTW (Vehicle Routing Problem with Time Windows)**, tích hợp AI Agent để người quản lý có thể tương tác với dữ liệu và chức năng tối ưu tuyến đường bằng ngôn ngữ tự nhiên.

Project gồm:

- **Frontend:** React + Vite
- **Backend:** FastAPI + SQLAlchemy
- **AI Agent:** LangGraph + LangChain
- **MCP:** Model Context Protocol để cung cấp tools cho Agent
- **LLM:** OpenRouter
- **Database:** MySQL
- **Agent Memory:** SQLite
- **Routing/Distance:** OSRM
- **Observability:** LangSmith
- **Optimization:** GA / ACO / PSO

---

## 1. Kiến trúc tổng quan

```text
                        ┌─────────────────────┐
                        │      Frontend       │
                        │   React + Vite      │
                        │    localhost:5173   │
                        └──────────┬──────────┘
                                   │ HTTP
                                   ▼
                        ┌─────────────────────┐
                        │       Backend       │
                        │ FastAPI + LangGraph │
                        │    localhost:8000   │
                        └──────┬───────┬──────┘
                               │       │
                 ┌─────────────┘       └──────────────┐
                 ▼                                    ▼
        ┌─────────────────┐                  ┌─────────────────┐
        │      MySQL      │                  │  AI Agent / MCP │
        │ Business Data   │                  │ Tools + Memory  │
        └─────────────────┘                  └───────┬─────────┘
                                                     │
                              ┌──────────────────────┼─────────────────────┐
                              ▼                      ▼                     ▼
                       ┌─────────────┐       ┌─────────────┐       ┌─────────────┐
                       │  OpenRouter │       │  LangSmith  │       │    OSRM     │
                       │     LLM     │       │  Tracing    │       │ Routing API │
                       └─────────────┘       └─────────────┘       └─────────────┘
```

---

# 2. Yêu cầu môi trường

Trước khi chạy project, cần cài:

| Thành phần | Phiên bản khuyến nghị |
|---|---|
| Python | **3.12.x** |
| Node.js | **20.19+ hoặc 22.12+** |
| npm | Đi kèm Node.js |
| MySQL | 8.x hoặc tương thích MySQL |
| Git | Phiên bản mới |
| OS | Windows / Linux / macOS |

### Kiểm tra phiên bản

```bash
python --version
node --version
npm --version
mysql --version
git --version
```

> Backend hiện được phát triển và kiểm thử với Python 3.12. Frontend sử dụng Vite 8, yêu cầu Node.js `20.19+` hoặc `22.12+`.

---

# 3. Clone project từ GitHub

```bash
git clone <GITHUB_REPOSITORY_URL>
cd <PROJECT_FOLDER>
```

Project có cấu trúc:

```text
project/
├── backend/
│   ├── app/
│   ├── data/
│   ├── create_db.py
│   ├── main.py
│   ├── requirements.txt
│   └── .env.example
│
├── frontend/
│   ├── src/
│   ├── public/
│   ├── package.json
│   ├── package-lock.json
│   └── vite.config.js
│
└── README.md
```

---

# 4. Cấu hình Backend

## 4.1. Đi vào thư mục backend

```bash
cd backend
```

## 4.2. Tạo Python Virtual Environment

### Windows

```bash
py -3.12 -m venv .venv
```

Kích hoạt:

```bash
.venv\Scripts\activate
```

Nếu dùng PowerShell và bị chặn script:

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
```

Sau đó:

```powershell
.venv\Scripts\Activate.ps1
```

### Linux / macOS

```bash
python3.12 -m venv .venv
source .venv/bin/activate
```

Sau khi kích hoạt thành công, terminal sẽ có dạng:

```text
(.venv) ...
```

---

# 5. Cài Python dependencies

Nâng cấp pip:

```bash
python -m pip install --upgrade pip
```

Cài dependencies:

```bash
pip install -r requirements.txt
```

Các thư viện quan trọng gồm:

- FastAPI
- Uvicorn
- SQLAlchemy
- PyMySQL
- AsyncMy
- LangChain
- LangGraph
- LangChain MCP Adapters
- MCP
- LangChain OpenAI
- LangSmith
- Scikit-learn
- HTTPX
- Requests

---

# 6. Cấu hình MySQL

Project sử dụng database:

```text
delivery_agent
```

## 6.1. Tạo database

Đăng nhập MySQL:

```bash
mysql -u root -p
```

Sau đó chạy:

```sql
CREATE DATABASE delivery_agent
CHARACTER SET utf8mb4
COLLATE utf8mb4_unicode_ci;
```

Kiểm tra:

```sql
SHOW DATABASES;
```

Thoát:

```sql
EXIT;
```

> Script `create_db.py` chỉ tạo các bảng dựa trên SQLAlchemy models. Nó không tự tạo database MySQL `delivery_agent`, vì vậy database cần được tạo trước.

---

# 7. Cấu hình file `.env`

Trong thư mục `backend`, copy file mẫu:

### Windows

```cmd
copy .env.example .env
```

### Linux / macOS

```bash
cp .env.example .env
```

Sau đó mở:

```text
backend/.env
```

và cấu hình.

## 7.1. Cấu hình database

Ví dụ:

```env
DB_HOST=localhost
DB_PORT=3306
DB_USER=root
DB_PASSWORD=
DB_NAME=delivery_agent
```

Nếu MySQL của bạn có password:

```env
DB_PASSWORD=your_mysql_password
```

---

# 8. Cấu hình OpenRouter

Agent sử dụng LLM thông qua OpenRouter.

Tạo API key trên OpenRouter và thêm vào:

```env
OPENROUTER_API_KEY=your_openrouter_api_key
```

Có thể chỉ định model:

```env
LLM_MODEL=your_model_name
```

Nếu không khai báo `LLM_MODEL`, backend sẽ sử dụng model mặc định được cấu hình trong code.

> Không commit API key lên GitHub.

---

# 9. Cấu hình LangSmith

LangSmith dùng để tracing và theo dõi quá trình chạy Agent.

Nếu muốn sử dụng LangSmith:

```env
LANGCHAIN_TRACING_V2=true
LANGCHAIN_ENDPOINT=https://api.smith.langchain.com
LANGCHAIN_API_KEY=your_langsmith_api_key
LANGCHAIN_PROJECT=agent-vrptw

LANGSMITH_TRACING=true
LANGSMITH_ENDPOINT=https://api.smith.langchain.com
LANGSMITH_API_KEY=your_langsmith_api_key
LANGSMITH_PROJECT=agent-vrptw
```

Nếu không cần LangSmith, có thể tắt tracing:

```env
LANGCHAIN_TRACING_V2=false
LANGSMITH_TRACING=false
```

và để API key trống.

---

# 10. Các biến môi trường Backend

Một file `.env` hoàn chỉnh có thể có dạng:

```env
# =========================
# MySQL
# =========================
DB_HOST=localhost
DB_PORT=3306
DB_USER=root
DB_PASSWORD=
DB_NAME=delivery_agent

# =========================
# LLM / OpenRouter
# =========================
OPENROUTER_API_KEY=your_openrouter_api_key
LLM_MODEL=your_model_name

# =========================
# Backend API
# =========================
BACKEND_API_URL=http://127.0.0.1:8000
BACKEND_API_TIMEOUT=180
BACKEND_API_TOKEN=

# =========================
# OSRM
# =========================
OSRM_BASE_URL=https://router.project-osrm.org
DISTANCE_PROVIDER=osrm
OSRM_TIMEOUT=30

# =========================
# LangSmith
# =========================
LANGCHAIN_TRACING_V2=true
LANGCHAIN_ENDPOINT=https://api.smith.langchain.com
LANGCHAIN_API_KEY=your_langsmith_api_key
LANGCHAIN_PROJECT=agent-vrptw

LANGSMITH_TRACING=true
LANGSMITH_ENDPOINT=https://api.smith.langchain.com
LANGSMITH_API_KEY=your_langsmith_api_key
LANGSMITH_PROJECT=agent-vrptw
```

Các biến `OSRM_*` có giá trị mặc định trong code nên có thể giữ nguyên nếu sử dụng OSRM public server.

---

# 11. Tạo các bảng MySQL

Sau khi:

1. MySQL đang chạy.
2. Database `delivery_agent` đã được tạo.
3. `backend/.env` đã cấu hình đúng.

Chạy:

```bash
python create_db.py
```

Nếu thành công sẽ hiển thị:

```text
Da tao cac bang database thanh cong!
```

Có thể kiểm tra:

```sql
USE delivery_agent;
SHOW TABLES;
```

Project hiện có các nhóm dữ liệu chính:

- Vehicles
- Depots
- Delivery Orders
- Route Plans
- Vehicle Routes
- Route Stops

---

# 12. Chạy Backend

Đảm bảo đang ở:

```text
project/backend
```

và virtual environment đã được kích hoạt.

Chạy:

```bash
python main.py
```

Backend mặc định chạy tại:

```text
http://127.0.0.1:8000
```

Swagger:

```text
http://127.0.0.1:8000/docs
```

Health check:

```text
http://127.0.0.1:8000/health
```

Có thể kiểm tra nhanh:

```bash
curl http://127.0.0.1:8000/health
```

Kết quả hợp lệ sẽ có trạng thái tương tự:

```json
{
  "status": "ok",
  "mcp": "ready",
  "agent_runtime": "configured",
  "sqlite_memory": "ready"
}
```

---

# 13. MCP Server

MCP server không cần chạy bằng một terminal riêng.

Khi FastAPI khởi động, backend sẽ tự tạo MCP client và khởi chạy:

```text
python -m app.agent.mcp_server
```

MCP sử dụng `stdio` transport.

Luồng hoạt động:

```text
FastAPI
   │
   ▼
LangGraph Agent
   │
   ▼
MCP Client
   │
   ▼
MCP Server
   │
   ▼
Backend API
   │
   ▼
MySQL
```

Vì vậy chỉ cần chạy:

```bash
python main.py
```

là đủ để khởi tạo Agent runtime và MCP.

---

# 14. Agent Memory

Agent sử dụng SQLite cho:

- Short-term memory / LangGraph checkpoints
- Long-term memory

File database được tạo tại:

```text
backend/data/agent_memory.sqlite3
```

Không cần tạo thủ công.

Khi backend khởi động, hệ thống sẽ tự tạo database và bảng memory nếu chưa tồn tại.

> Nếu muốn reset toàn bộ memory của Agent trong môi trường development, có thể dừng backend và xóa file `backend/data/agent_memory.sqlite3`, sau đó chạy backend lại.

---

# 15. Cấu hình Frontend

Mở terminal thứ hai.

Từ thư mục project:

```bash
cd frontend
```

Cài Node.js dependencies:

```bash
npm install
```

Project sử dụng:

- React
- Vite
- React Leaflet
- Leaflet
- React Markdown
- Lucide React

---

# 16. Cấu hình URL Backend cho Frontend

Frontend hiện sử dụng:

```text
http://127.0.0.1:8000
```

Cấu hình nằm tại:

```text
frontend/src/constants/config.js
```

Có dạng:

```javascript
export const API_BASE_URL = 'http://127.0.0.1:8000'
```

Nếu backend chạy ở địa chỉ khác, sửa giá trị này.

Ví dụ:

```javascript
export const API_BASE_URL = 'http://192.168.1.100:8000'
```

---

# 17. Chạy Frontend

Trong thư mục `frontend`:

```bash
npm run dev
```

Vite sẽ chạy frontend tại:

```text
http://localhost:5173
```

Mở trình duyệt:

```text
http://localhost:5173
```

---

# 18. Chạy toàn bộ hệ thống

Cần mở **2 terminal**.

## Terminal 1 - Backend

```bash
cd backend
```

Kích hoạt virtual environment:

```bash
.venv\Scripts\activate
```

Chạy:

```bash
python main.py
```

Backend:

```text
http://127.0.0.1:8000
```

## Terminal 2 - Frontend

```bash
cd frontend
npm run dev
```

Frontend:

```text
http://localhost:5173
```

---

# 19. Kiểm tra hệ thống sau khi cài đặt

Thực hiện theo thứ tự:

### Bước 1 - Kiểm tra MySQL

```sql
USE delivery_agent;
SHOW TABLES;
```

### Bước 2 - Kiểm tra Backend

Mở:

```text
http://127.0.0.1:8000/
```

Phải nhận được thông báo:

```json
{
  "message": "AI Agent VRPTW API is running",
  "docs": "/docs"
}
```

### Bước 3 - Kiểm tra Agent runtime

Mở:

```text
http://127.0.0.1:8000/health
```

Kiểm tra:

```text
mcp = ready
agent_runtime = configured
sqlite_memory = ready
```

### Bước 4 - Kiểm tra Swagger

Mở:

```text
http://127.0.0.1:8000/docs
```

Có thể thử các API CRUD trực tiếp trên Swagger.

### Bước 5 - Kiểm tra Frontend

Mở:

```text
http://localhost:5173
```

### Bước 6 - Kiểm tra AI Agent

Mở giao diện Chatbot và gửi một câu hỏi đơn giản, ví dụ:

```text
Có bao nhiêu phương tiện trong hệ thống?
```

Agent phải sử dụng MCP/API để lấy dữ liệu thay vì tự đoán.

---

# 20. Kiểm tra tối ưu VRPTW

Sau khi đã có dữ liệu:

- Depot
- Vehicles
- Delivery Orders

có thể sử dụng Agent để yêu cầu tối ưu.

Ví dụ:

```text
Hãy tối ưu tuyến giao hàng cho kho 1 vào ngày 2026-10-22 bằng thuật toán GA.
```

Agent có thể sử dụng các thuật toán:

```text
GA  - Genetic Algorithm
ACO - Ant Colony Optimization
PSO - Particle Swarm Optimization
```

Các chế độ clustering hiện có:

```text
distance
spatiotemporal
```

---

# 21. OSRM

Project mặc định sử dụng OSRM public server:

```text
https://router.project-osrm.org
```

OSRM được sử dụng để lấy:

- Distance matrix
- Duration matrix
- Route geometry

Mặc định:

```env
DISTANCE_PROVIDER=osrm
```

Nếu muốn sử dụng Haversine/Euclidean approximation thay vì OSRM:

```env
DISTANCE_PROVIDER=euclidean
```

---

# 22. LangSmith

Nếu đã cấu hình LangSmith, sau khi chạy Agent có thể kiểm tra trace trong LangSmith.

Kiểm tra biến:

```env
LANGSMITH_TRACING=true
LANGSMITH_API_KEY=your_langsmith_api_key
LANGSMITH_PROJECT=agent-vrptw
```

Nếu tracing không hoạt động, kiểm tra:

1. API key có hợp lệ không.
2. `LANGSMITH_TRACING=true`.
3. Backend đã được restart sau khi sửa `.env`.
4. Project name trong LangSmith đúng với `LANGSMITH_PROJECT`.

---

# 23. Build Frontend production

Để build frontend:

```bash
cd frontend
npm run build
```

Kết quả được tạo trong:

```text
frontend/dist/
```

Preview production build:

```bash
npm run preview
```

---

# 24. Lint Frontend

Chạy:

```bash
npm run lint
```

Nếu muốn kiểm tra code trước khi commit:

```bash
npm run lint
npm run build
```

---

# 25. Các lỗi thường gặp

## Lỗi 1: `ModuleNotFoundError`

Ví dụ:

```text
ModuleNotFoundError: No module named 'fastapi'
```

Nguyên nhân thường là chưa kích hoạt virtual environment hoặc chưa cài dependencies.

Khắc phục:

```bash
cd backend
.venv\Scripts\activate
pip install -r requirements.txt
```

---

## Lỗi 2: Thiếu `DB_USER` hoặc `DB_NAME`

Nếu gặp:

```text
Thiếu DB_USER hoặc DB_NAME trong file .env
```

Kiểm tra:

```text
backend/.env
```

Ví dụ:

```env
DB_USER=root
DB_PASSWORD=
DB_HOST=localhost
DB_PORT=3306
DB_NAME=delivery_agent
```

---

## Lỗi 3: MySQL connection refused

Nếu gặp lỗi kết nối MySQL:

```text
Can't connect to MySQL server
```

Kiểm tra:

1. MySQL service đã chạy chưa.
2. Port có phải `3306` không.
3. `DB_USER` đúng không.
4. `DB_PASSWORD` đúng không.
5. Database `delivery_agent` đã được tạo chưa.

---

## Lỗi 4: Agent không khởi động

Nếu `/health` trả:

```text
agent_runtime = not_configured
```

kiểm tra terminal backend.

Các nguyên nhân phổ biến:

- `OPENROUTER_API_KEY` sai hoặc chưa cấu hình.
- Python dependencies chưa cài đầy đủ.
- MCP server không khởi động.
- Backend API không truy cập được.
- Lỗi import trong `app/agent`.

---

## Lỗi 5: MCP không ở trạng thái `ready`

Kiểm tra:

```text
http://127.0.0.1:8000/health
```

Nếu:

```json
{
  "mcp": "not_ready"
}
```

xem log backend để tìm lỗi khởi tạo MCP.

MCP server được backend tự khởi chạy, vì vậy không cần chạy thêm một terminal MCP riêng.

---

## Lỗi 6: Frontend không gọi được Backend

Nếu trình duyệt báo lỗi network/CORS:

Kiểm tra backend:

```text
http://127.0.0.1:8000/health
```

Sau đó kiểm tra:

```text
frontend/src/constants/config.js
```

Phải trỏ đúng:

```javascript
export const API_BASE_URL = 'http://127.0.0.1:8000'
```

---

## Lỗi 7: `npm install` hoặc Vite lỗi version Node

Kiểm tra:

```bash
node --version
```

Frontend sử dụng Vite 8, cần:

```text
Node.js 20.19+
```

hoặc:

```text
Node.js 22.12+
```

Khuyến nghị dùng Node.js LTS tương thích.

---

## Lỗi 8: Không có dữ liệu để Agent tối ưu

Agent không thể tối ưu tuyến nếu database chưa có dữ liệu cần thiết.

Cần tối thiểu kiểm tra:

```text
Depots
Vehicles
Delivery Orders
```

Có thể kiểm tra bằng Swagger:

```text
http://127.0.0.1:8000/docs
```

---

# 26. Bảo mật - QUAN TRỌNG

**Không commit các thông tin sau lên GitHub:**

```text
.env
API keys
Database passwords
LangSmith API keys
OpenRouter API keys
Access tokens
```

Đặc biệt không được commit:

```env
OPENROUTER_API_KEY=sk-or-...
LANGCHAIN_API_KEY=...
LANGSMITH_API_KEY=...
```

Repository chỉ nên chứa:

```text
.env.example
```

với giá trị mẫu:

```env
OPENROUTER_API_KEY=your_openrouter_api_key
LANGSMITH_API_KEY=your_langsmith_api_key
```

Nếu một API key đã từng được commit lên GitHub hoặc chia sẻ công khai, **không nên chỉ xóa nó khỏi file**. Hãy revoke/rotate key và tạo key mới.

---

# 27. Không commit các thư mục generated

Không nên đưa các thư mục/file sau lên GitHub:

```text
backend/.venv/
backend/__pycache__/
backend/app/**/__pycache__/
backend/data/agent_memory.sqlite3

frontend/node_modules/
frontend/dist/
```

Các dependency sẽ được cài lại bằng:

```bash
pip install -r requirements.txt
```

và:

```bash
npm install
```

---

# 28. Quy trình cài đặt nhanh

Nếu máy đã có Python, Node.js và MySQL, quy trình cơ bản là:

### Backend

```bash
cd backend

py -3.12 -m venv .venv

.venv\Scripts\activate

pip install --upgrade pip

pip install -r requirements.txt

copy .env.example .env
```

Sau đó chỉnh:

```text
backend/.env
```

Tạo database:

```sql
CREATE DATABASE delivery_agent
CHARACTER SET utf8mb4
COLLATE utf8mb4_unicode_ci;
```

Tạo tables:

```bash
python create_db.py
```

Chạy backend:

```bash
python main.py
```

### Frontend

Mở terminal mới:

```bash
cd frontend
npm install
npm run dev
```

Mở:

```text
http://localhost:5173
```

---

# 29. Development workflow

Khi phát triển project:

```text
                    GitHub
                       │
                       ▼
                 Clone / Pull
                       │
          ┌────────────┴────────────┐
          ▼                         ▼
       Backend                   Frontend
          │                         │
    Python + venv              Node + npm
          │                         │
          ▼                         ▼
       FastAPI                    Vite
          │                         │
          └──────────┬──────────────┘
                     ▼
                  Browser
                     │
                     ▼
              AI Agent / VRPTW
```

Mỗi khi clone project trên máy mới:

```bash
pip install -r backend/requirements.txt
npm install --prefix frontend
```

Sau đó chỉ cần cấu hình `.env`, MySQL và chạy hai service.

---

# 30. API Documentation

Sau khi backend chạy:

```text
Swagger UI:
http://127.0.0.1:8000/docs
```

Backend API bao gồm các nhóm chính:

```text
Vehicles
Depots
Delivery Orders
Route Plans
Vehicle Routes
Route Stops
Optimization
AI Agent
What-if
```

Swagger là nguồn chính để kiểm tra request/response schema của API.

---

# 31. Project Status

Project hiện bao gồm:

- [x] React frontend
- [x] FastAPI backend
- [x] MySQL database
- [x] SQLAlchemy ORM
- [x] LangGraph Agent
- [x] MCP tool layer
- [x] Agent short-term memory
- [x] Agent long-term memory
- [x] OpenRouter LLM
- [x] LangSmith tracing
- [x] OSRM routing
- [x] VRPTW optimization
- [x] GA
- [x] ACO
- [x] PSO
- [x] What-if scenario
- [x] Route management UI
- [x] Map visualization

---

# 32. License

Nếu project sử dụng license riêng, thay phần này bằng license của project.

Ví dụ:

```text
MIT License
```

---

## Tóm tắt

Để một người khác tải project từ GitHub về và chạy được hệ thống, họ cần thực hiện:

```text
1. Clone repository
        ↓
2. Cài Python 3.12
        ↓
3. Cài Node.js 20.19+
        ↓
4. Cài MySQL
        ↓
5. Tạo database delivery_agent
        ↓
6. Tạo Python virtual environment
        ↓
7. pip install -r requirements.txt
        ↓
8. Tạo backend/.env
        ↓
9. Cấu hình OpenRouter + MySQL + LangSmith
        ↓
10. python create_db.py
        ↓
11. python main.py
        ↓
12. npm install
        ↓
13. npm run dev
        ↓
14. Mở http://localhost:5173
```

**Backend:** `http://127.0.0.1:8000`

**Swagger:** `http://127.0.0.1:8000/docs`

**Frontend:** `http://localhost:5173`
