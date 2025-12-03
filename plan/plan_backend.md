Kế Hoạch Triển Khai Backend (Python FastAPI)

1. Tổng quan Công nghệ

Framework: FastAPI (Hiệu năng cao, hỗ trợ Async, tự động tạo Docs).

Language: Python 3.9+.

AI Service: OpenAI API (gpt-3.5-turbo hoặc gpt-4o).

Database: Google Sheets (Sử dụng như một DB nhẹ để đọc danh sách cửa hàng).
đây là thông tin header của gg sheets
"store_id","store_name","address","category","product_info","promotion"

Geospatial Logic: geopy (Để tính khoảng cách giữa tọa độ User và Shop).

Data Processing: pandas (Để xử lý dữ liệu bảng từ Google Sheets).

Deployment: Uvicorn server.

2. Chuẩn bị Tài nguyên (Prerequisites)

Trước khi code, cần chuẩn bị các API Key và cấu hình:

OpenAI API Key: Đăng ký tại platform.openai.com.

Google Cloud Project:

Kích hoạt Google Sheets API.

Kích hoạt Google Maps Geocoding API (để chuyển địa chỉ text sang tọa độ - bước chuẩn bị dữ liệu).

Tạo Service Account -> Tải file JSON Credential (credentials.json).

Dữ liệu: File Google Sheet (hoặc CSV) đã có thông tin cửa hàng (như file CSV đã tạo ở bước trước).

3. Cấu trúc Thư mục Dự án

/backend-app
├── main.py             # File khởi chạy chính (FastAPI app)
├── requirements.txt    # Các thư viện cần thiết
├── .env                # Lưu API Key bảo mật
├── services/
│   ├── ai_service.py   # Logic gọi OpenAI
│   ├── sheet_service.py# Logic đọc dữ liệu từ Google Sheets
│   └── geo_service.py  # Logic tính toán khoảng cách
└── models.py           # Định nghĩa Pydantic Models (Input/Output)


4. Các bước Thực hiện Chi tiết

Bước 1: Cài đặt Môi trường (Environment Setup)

Cài đặt các thư viện cần thiết.
File requirements.txt:

fastapi
uvicorn
openai
pandas
gspread
oauth2client
geopy
python-dotenv


Bước 2: Chuẩn hóa Dữ liệu (Data Pre-processing)

Vấn đề: Google Sheets chứa địa chỉ dạng Text ("768 Đường Láng"), nhưng User gửi lên Lat/Long. Backend không thể so sánh Text với Lat/Long trực tiếp.
Giải pháp: Viết một script chạy 1 lần (one-time script) để Geocoding.

Đọc cột address từ Sheet.

Dùng Google Maps API (hoặc thư viện geopy với Nominatim - miễn phí nhưng chậm) để lấy Lat/Long.

Ghi ngược lại 2 cột latitude và longitude vào Sheet.

Kết quả: Dữ liệu trong Sheet sẽ có đầy đủ tọa độ để Backend tính toán nhanh.

Bước 3: Xây dựng Core Logic (Services)

A. Sheet Service (services/sheet_service.py)

Sử dụng gspread để kết nối Google Sheets bằng credentials.json.

Tải toàn bộ dữ liệu cửa hàng vào pandas DataFrame khi khởi động Server (Caching in-memory).

Lợi ích: Truy vấn cực nhanh, không cần gọi API Google Sheets mỗi lần user chat (tránh quota limit).

B. Geo Service (services/geo_service.py)

Input: user_lat, user_long và DataFrame danh sách cửa hàng.

Logic:

Duyệt qua danh sách cửa hàng.

Dùng geopy.distance.geodesic tính khoảng cách từ User đến từng Shop.

Sort (sắp xếp) theo khoảng cách tăng dần.

Lấy ra Shop đầu tiên (gần nhất).

Output: Thông tin chi tiết của Shop gần nhất (Tên, Info, Promo, Distance).

C. AI Service (services/ai_service.py)

Sử dụng thư viện openai.

Prompt Engineering:

System: Bạn là trợ lý ảo bán hàng.
Context: Khách hàng đang ở cách shop [Store Name] khoảng [Distance] km.
Thông tin shop: [Product Info]. Khuyến mãi: [Promotion].
Nhiệm vụ: Trả lời câu hỏi của khách hàng dựa trên thông tin shop. Mời khách đến địa chỉ [Address].
User Query: [User Message]


Bước 4: Xây dựng API với FastAPI (main.py)

Cấu hình CORS

Bắt buộc cấu hình allow_origins=["*"] để Frontend (chạy localhost hoặc domain khác) gọi được API.

Định nghĩa Data Model (models.py)

from pydantic import BaseModel

class ChatRequest(BaseModel):
    message: str
    latitude: float
    longitude: float

class StoreInfo(BaseModel):
    name: str
    address: str
    lat: float
    lng: float
    distance_km: float

class ChatResponse(BaseModel):
    reply: str
    nearest_store: StoreInfo
