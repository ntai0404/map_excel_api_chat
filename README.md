# 📍 AI Smart Chatbot - Location Based Store Finder

Dự án Chatbot tích hợp AI (Google Gemini) giúp người dùng tìm kiếm sản phẩm và cửa hàng gần nhất dựa trên vị trí thực tế, hỗ trợ đăng nhập qua Zalo và quản lý dữ liệu linh hoạt từ Google Sheets.

## ✨ Tính Năng Nổi Bật

### 🤖 AI & NLP (Google Gemini)
*   **Hiểu ngôn ngữ tự nhiên:** Phân tích ý định người dùng (tìm sản phẩm cụ thể, tìm theo danh mục, hỏi vị trí, giao tiếp xã giao).
*   **Phản hồi thông minh:** Trả lời dựa trên ngữ cảnh, tự động đề xuất cửa hàng phù hợp kể cả khi không tìm thấy sản phẩm chính xác (gợi ý thay thế).
*   **Trích xuất thông tin:** Tự động nhận diện tên sản phẩm, danh mục từ câu chat.

### 🗺️ Bản Đồ & Định Vị (Leaflet & OpenStreetMap)
*   **Định vị người dùng:** Xác định vị trí GPS chính xác.
*   **Trực quan hóa:** Hiển thị Marker người dùng và các cửa hàng gần nhất trên bản đồ.
*   **Tương tác:** Popup hiển thị thông tin chi tiết, đường dẫn Zalo OA của từng cửa hàng.

### 🛍️ Tìm Kiếm Sản Phẩm & Cửa Hàng
*   **Dữ liệu Real-time:** Đọc trực tiếp từ Google Sheets (không cần database riêng).
*   **Tìm kiếm đa tầng:**
    1.  Tìm chính xác tên sản phẩm.
    2.  Tìm theo danh mục (Category).
*   **Hiển thị sản phẩm:** Xem trước hình ảnh, giá bán của sản phẩm nổi bật ngay trong khung chat và trên bản đồ.

### 🔐 Tích Hợp Zalo
*   **Đăng nhập Zalo:** Hỗ trợ người dùng đăng nhập nhanh qua tài khoản Zalo.
*   **Liên kết Zalo OA:** Chuyển hướng người dùng đến nhóm Zalo của từng cửa hàng để tư vấn trực tiếp.

---

## 🛠️ Công Nghệ Sử Dụng

*   **Backend:** Python (FastAPI), Pandas (Data Processing).
*   **AI Engine:** Google Gemini API (`gemini-2.0-flash-lite` / `gemini-2.5-flash-lite`).
*   **Frontend:** HTML5, CSS3, JavaScript (Vanilla), Leaflet.js.
*   **Data Source:** Google Sheets (CSV Export).
*   **Deployment:** Hỗ trợ chạy local hoặc deploy lên server (Render, Railway...).

---

## 🚀 Cài Đặt & Chạy Dự Án

### 1. Chuẩn Bị
*   Python 3.8+
*   API Key Google Gemini (AI Studio).
*   Zalo App ID & Secret (cho tính năng đăng nhập).

### 2. Cài Đặt
```bash
# 1. Clone dự án
git clone https://github.com/ntai0404/map_excel_api_chat.git
cd map_excel_api_chat

# 2. Cài đặt thư viện
pip install -r backend-app/requirements.txt
```

### 3. Cấu Hình
Tạo file `.env` tại thư mục gốc:
```env
# Google AI
AI_API_KEY=your_gemini_api_key
AI_MODEL_NAME=gemini-2.5-flash-lite

# Zalo OAuth
ZALO_APP_ID=your_zalo_app_id
ZALO_APP_SECRET=your_zalo_app_secret
ZALO_REDIRECT_URI=http://127.0.0.1:8000/auth/zalo/callback

# Security
SESSION_SECRET_KEY=complex_secret_key
```

### 4. Chạy Server
```bash
python backend-app/main.py
```
*   Truy cập: `http://localhost:8000/index.html`

---

## 📂 Cấu Trúc Thư Mục
```
map_excel_api_chat/
├── backend-app/
│   ├── main.py             # Entry point (FastAPI)
│   ├── services/
│   │   ├── ai_service.py   # Xử lý Gemini AI
│   │   ├── geo_service.py  # Logic khoảng cách & bản đồ
│   │   └── sheet_service.py# Đọc dữ liệu Google Sheets
│   └── models.py           # Pydantic Models
├── index.html              # Giao diện chính
├── login.html              # Trang đăng nhập
├── avatar-display.js       # Quản lý hiển thị User/Guest
├── script.js               # Logic Chat & Map chính
└── ...
```

---

## 📝 Nhật Ký Cập Nhật (Update V3)
*   [x] Tối ưu hóa UI Header (Avatar/Button positioning).
*   [x] Sửa lỗi vòng lặp đăng nhập (Login Loop).
*   [x] Cấu hình lại AI Model phù hợp với Free Tier (`gemini-2.5-flash-lite`).
*   [x] Dọn dẹp code rác & tối ưu hiệu năng.

---
**Author:** [ntai0404](https://github.com/ntai0404)
