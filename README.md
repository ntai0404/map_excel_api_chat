# 📍 AI Smart Chatbot - Location Based Store Finder

Dự án Chatbot tích hợp AI (Google Gemini) giúp người dùng tìm kiếm sản phẩm và cửa hàng gần nhất dựa trên vị trí thực tế, hỗ trợ đăng nhập qua Zalo và quản lý dữ liệu linh hoạt từ Google Sheets.

---

## 🚀 Hướng Dẫn Cài Đặt & Chạy Dự Án

### **📋 Yêu Cầu Hệ Thống**
- Python 3.8+
- Git
- Google Gemini API Key ([Lấy tại đây](https://aistudio.google.com/app/apikey))
- Zalo App ID & Secret ([Đăng ký tại đây](https://developers.zalo.me/))

---

### **1️⃣ Clone Dự Án**
```bash
git clone https://github.com/ntai0404/map_excel_api_chat.git
cd map_excel_api_chat
```

---

### **2️⃣ Cài Đặt Dependencies**
```bash
# Cài đặt thư viện Python
pip install -r backend-app/requirements.txt
```

**Danh sách thư viện chính:**
- `fastapi` - Web framework
- `uvicorn` - ASGI server
- `pandas` - Xử lý dữ liệu
- `google-generativeai` - Gemini AI
- `geopy` - Tính khoảng cách GPS
- `httpx` - HTTP client cho Zalo OAuth

---

### **3️⃣ Cấu Hình Environment Variables**

#### **A. Tạo file `.env`**
Copy file mẫu và chỉnh sửa:
```bash
cp .env.example .env
```

#### **B. Cấu hình cho Localhost**
Mở file `.env` và điền thông tin:

```env
# ===== Google AI Configuration =====
AI_API_KEY=AIzaSy...  # Lấy từ https://aistudio.google.com/app/apikey
AI_MODEL_NAME=gemini-2.5-flash-lite
AI_API_BASE=  # Để trống nếu dùng Gemini API chính thức

# ===== Zalo OAuth Configuration =====
ZALO_APP_ID=1234567890  # App ID từ Zalo Developer
ZALO_APP_SECRET=abcdef123456  # App Secret từ Zalo Developer
ZALO_REDIRECT_URI=http://127.0.0.1:8000/auth/zalo/callback

# ===== Security =====
SESSION_SECRET_KEY=your-random-secret-key-here
```

#### **C. Lấy Zalo App Credentials**
1. Truy cập: https://developers.zalo.me/
2. Tạo ứng dụng mới (hoặc dùng app có sẵn)
3. Vào **Settings** → Copy `App ID` và `App Secret`
4. Vào **OAuth Settings** → Thêm **Redirect URI**:
   ```
   http://127.0.0.1:8000/auth/zalo/callback
   ```
5. Thêm **Trusted Domains** (nếu có):
   ```
   127.0.0.1
   ```

---

### **4️⃣ Chạy Server**

```bash
# Di chuyển vào thư mục backend
cd backend-app

# Chạy server
python main.py
```

**Output mong đợi:**
```
Loading .env from: C:\...\map_excel_api_chat\.env
INFO:     Started server process [12345]
INFO:     Waiting for application startup.
INFO:     Application startup complete.
INFO:     Uvicorn running on http://0.0.0.0:8000 (Press CTRL+C to quit)
```

---

### **5️⃣ Truy Cập Ứng Dụng**

Mở trình duyệt và truy cập:
```
http://127.0.0.1:8000/
```

Hoặc:
```
http://127.0.0.1:8000/index.html
```

---

## 🌐 Deploy Lên Production (Ubuntu Server)

### **1️⃣ Chuẩn Bị Server**
```bash
# Update system
sudo apt update && sudo apt upgrade -y

# Cài Python & pip
sudo apt install python3 python3-pip -y

# Cài Git
sudo apt install git -y
```

### **2️⃣ Clone & Setup**
```bash
# Clone project
git clone https://github.com/ntai0404/map_excel_api_chat.git
cd map_excel_api_chat

# Cài dependencies
pip3 install -r backend-app/requirements.txt
```

### **3️⃣ Cấu Hình `.env` cho Production**
```env
# ===== Google AI Configuration =====
AI_API_KEY=AIzaSy...
AI_MODEL_NAME=gemini-2.5-flash-lite

# ===== Zalo OAuth Configuration =====
ZALO_APP_ID=1234567890
ZALO_APP_SECRET=abcdef123456
ZALO_REDIRECT_URI=https://vscode.oanhcuongdo.com/auth/zalo/callback  # ← Đổi domain

# ===== Security =====
SESSION_SECRET_KEY=production-secret-key-very-strong
```

### **4️⃣ Cập Nhật Zalo App Settings**
1. Vào Zalo Developer Console
2. Cập nhật **OAuth Redirect URI**:
   ```
   https://vscode.oanhcuongdo.com/auth/zalo/callback
   ```
3. Thêm **Trusted Domains**:
   ```
   vscode.oanhcuongdo.com
   ```
4. Tải file verify HTML → Upload lên server → Click "Xác thực"

### **5️⃣ Cập Nhật Frontend URL trong Code**
Mở file `backend-app/main.py`, tìm dòng:
```python
frontend_url = "http://127.0.0.1:8000/index.html"
```

Sửa thành:
```python
frontend_url = "https://vscode.oanhcuongdo.com/index.html"
```

### **6️⃣ Setup Nginx Reverse Proxy**
```nginx
server {
    listen 443 ssl;
    server_name vscode.oanhcuongdo.com;
    
    ssl_certificate /etc/letsencrypt/live/vscode.oanhcuongdo.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/vscode.oanhcuongdo.com/privkey.pem;
    
    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

### **7️⃣ Cài SSL Certificate**
```bash
sudo apt install certbot python3-certbot-nginx -y
sudo certbot --nginx -d vscode.oanhcuongdo.com
```

### **8️⃣ Chạy Server (Production)**
```bash
# Chạy background với nohup
cd backend-app
nohup python3 main.py > server.log 2>&1 &

# Hoặc dùng systemd (khuyến nghị)
sudo nano /etc/systemd/system/chatbot.service
```

**File `chatbot.service`:**
```ini
[Unit]
Description=AI Chatbot Service
After=network.target

[Service]
Type=simple
User=ubuntu
WorkingDirectory=/home/ubuntu/map_excel_api_chat/backend-app
ExecStart=/usr/bin/python3 main.py
Restart=always

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl daemon-reload
sudo systemctl enable chatbot
sudo systemctl start chatbot
sudo systemctl status chatbot
```

---

## 📂 Cấu Trúc Dự Án

```
map_excel_api_chat/
├── backend-app/
│   ├── main.py                 # Entry point (FastAPI)
│   ├── models.py               # Pydantic Models
│   ├── services/
│   │   ├── ai_service.py       # Gemini AI logic
│   │   ├── geo_service.py      # GPS & distance calculation
│   │   └── sheet_service.py    # Google Sheets data loader
│   └── requirements.txt        # Python dependencies
├── index.html                  # Main chat interface
├── login.html                  # Login page
├── avatar-display.js           # User/Guest display logic
├── script.js                   # Chat & Map logic
├── style.css                   # Main styles
├── .env.example                # Environment template
└── README.md                   # This file
```

---

## ✨ Tính Năng Chính

### 🤖 **AI-Powered Search v2.0**
- **Smart Product Filter:** AI tự động lọc sản phẩm phù hợp từ hàng nghìn items
- **3-Tier Fallback Strategy:** Xử lý thông minh khi không tìm thấy sản phẩm chính xác
- **Category-Based Recommendations:** Gợi ý sản phẩm cùng danh mục khi regex thất bại
- **General Inquiry Detection:** Nhận diện lời chào và câu hỏi chung

### 🗺️ **Location-Based Features**
- Định vị GPS người dùng
- Tính khoảng cách chính xác (geodesic)
- Hiển thị cửa hàng gần nhất trên bản đồ
- Popup thông tin chi tiết + link Zalo group

### 🔐 **Zalo Integration**
- OAuth V4 với PKCE
- Đăng nhập nhanh qua Zalo
- Liên kết trực tiếp đến Zalo OA/Group

### 📊 **Data Management**
- Đọc real-time từ Google Sheets
- Hỗ trợ multi-category products
- Auto-reload data khi Sheets thay đổi

---

## 🐛 Troubleshooting

### **Lỗi: `ModuleNotFoundError: No module named 'fastapi'`**
```bash
pip install -r backend-app/requirements.txt
```

### **Lỗi: `AI_API_KEY not found`**
- Kiểm tra file `.env` có tồn tại không
- Đảm bảo `.env` nằm ở thư mục gốc (không phải `backend-app/`)

### **Lỗi: Zalo Login không hoạt động**
- Kiểm tra `ZALO_REDIRECT_URI` khớp với Zalo Developer Console
- Đảm bảo domain đã được verify (Trusted Domains)

### **Lỗi: `KeyError: 'Giá niêm yết'`**
- Kiểm tra Google Sheets có cột "Giá niêm yết" không
- Đảm bảo tên cột chính xác (có dấu, viết hoa/thường đúng)

---

## 📝 Changelog

### **v3.1 - Product Links, OAuth PKCE & Session Management** (2025-12-15)
- ✅ Add product URL links - "🔗 Xem sản phẩm" button in product cards
- ✅ Implement Zalo OAuth V4 PKCE properly
  - Generate and save `code_verifier` to localStorage
  - Send `code_challenge` in authorization URL
  - Fix SyntaxError (illegal return statement in callback)
- ✅ Fix logout session persistence issues
  - Force session validation on every page load
  - Clear URL params after restoring session (prevent auto-login loop)
  - Proper localStorage/sessionStorage cleanup
- ✅ Add debug logging for product link data verification

### **v3.0 - AI-Powered Search v2.0** (2025-12-15)

- ✅ Add `smart_product_filter()` for AI Call #2
- ✅ Implement 3-tier fallback strategy
- ✅ Add category-based fallback when regex fails
- ✅ Fix shop card to display only AI-selected products
- ✅ Add distance display in shop card
- ✅ Fix price column name to "Giá niêm yết"
- ✅ Add `is_general_inquiry` detection for greetings
- ✅ Improve AI prompt for better category matching
- ✅ Add welcome message (shows once per session)
- ✅ Fix logout to clear all storage (localStorage + sessionStorage)

---

## 👨‍💻 Author

**Nguyễn Xuân Tài** - [ntai0404](https://github.com/ntai0404)

---

## 📄 License

This project is licensed under the MIT License.
