# 📍 AI Chatbot Tìm Kiếm Cửa Hàng Theo Vị Trí (Location-Based Store Finder)

Dự án Chatbot AI thông minh giúp người dùng tìm kiếm cửa hàng, sản phẩm gần nhất dựa trên vị trí thực tế, sử dụng dữ liệu từ Google Sheets và công nghệ AI (Google Gemini).

## ✨ Tính Năng Nổi Bật

*   **🤖 AI Chatbot Thông Minh:** Hiểu ngôn ngữ tự nhiên, phân tích ý định tìm kiếm (sản phẩm, danh mục, vị trí, xã giao).
*   **📍 Định Vị Người Dùng:** Tự động xác định vị trí người dùng (HTML5 Geolocation) để tìm cửa hàng gần nhất.
*   **🗺️ Bản Đồ Trực Quan:** Hiển thị vị trí người dùng và các cửa hàng trên bản đồ tương tác (OpenStreetMap & Leaflet).
*   **📊 Dữ Liệu Linh Hoạt:** Quản lý danh sách cửa hàng, sản phẩm trực tiếp trên Google Sheets (không cần Database phức tạp).
*   **🔍 Tìm Kiếm Đa Tầng:**
    1.  Ưu tiên tìm chính xác tên sản phẩm.
    2.  Tìm theo từ khóa chung (ví dụ: "điện thoại", "áo").
    3.  Tìm theo danh mục (ví dụ: "Thời trang", "Công nghệ").
*   **💬 Phản Hồi Tự Nhiên:** AI trả lời thân thiện, biết chào hỏi, cảm ơn, tạm biệt và xử lý các tình huống không tìm thấy hàng.

## 🛠️ Công Nghệ Sử Dụng

*   **Backend:** Python (FastAPI).
*   **AI Engine:** Google Gemini API (`gemini-2.0-flash-exp`).
*   **Database:** Google Sheets (CSV Export).
*   **Frontend:** HTML, CSS, JavaScript (Vanilla).
*   **Map:** OpenStreetMap, Leaflet.js.
*   **Distance Calculation:** Geopy (Haversine formula).

## 🚀 Cài Đặt & Chạy Dự Án

### 1. Yêu Cầu
*   Python 3.8 trở lên.
*   Tài khoản Google AI Studio (để lấy API Key).

### 2. Cài Đặt

1.  **Clone dự án:**
    ```bash
    git clone https://github.com/ntai0404/map_excel_api_chat.git
    cd map_excel_api_chat
    ```

2.  **Cài đặt thư viện:**
    ```bash
    pip install -r backend-app/requirements.txt
    ```

3.  **Cấu hình môi trường:**
    *   Tạo file `.env` tại thư mục gốc.
    *   Thêm API Key của bạn vào:
        ```env
        GEMINI_API_KEY=your_api_key_here
        ```

### 3. Chạy Server
```bash
python backend-app/main.py
```
*   Server sẽ chạy tại: `http://localhost:8000`
*   Giao diện Chat: Mở file `index.html` trên trình duyệt hoặc truy cập `http://localhost:8000` (nếu đã cấu hình static files).

## 📂 Cấu Trúc Thư Mục

```
map_excel_api_chat/
├── backend-app/
│   ├── main.py             # Server chính (FastAPI)
│   ├── requirements.txt    # Các thư viện cần thiết
│   └── services/
│       ├── ai_service.py   # Xử lý logic AI (Gemini)
│       ├── geo_service.py  # Tính toán khoảng cách
│       └── sheet_service.py# Đọc dữ liệu từ Google Sheets
├── index.html              # Giao diện chính
├── script.js               # Logic Frontend (Chat, Map, Location)
├── style.css               # Giao diện (CSS)
├── .env                    # Biến môi trường (API Key)
└── README.md               # Tài liệu hướng dẫn
```

## 📝 Lưu Ý
*   Dữ liệu cửa hàng được lấy từ link Google Sheet CSV công khai (được cấu hình trong `sheet_service.py`).
*   Để tính năng định vị hoạt động tốt nhất, hãy cho phép trình duyệt truy cập vị trí.

---
**Tác giả:** [ntai0404](https://github.com/ntai0404)
