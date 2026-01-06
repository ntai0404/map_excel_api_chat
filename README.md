# 📍 AI Smart Chatbot - Location Based Store Finder (DeepSeek V3)

Dự án Chatbot tích hợp AI (DeepSeek V3) giúp người dùng tìm kiếm sản phẩm và cửa hàng gần nhất dựa trên vị trí thực tế, hỗ trợ đăng nhập qua Zalo và quản lý dữ liệu linh hoạt từ Google Sheets. Phiên bản mới đã cải tiến mạnh mẽ hệ thống ghi nhận khách hàng tiềm năng (Lead Generation).

---

## 🚀 Hướng Dẫn Cài Đặt & Chạy Dự Án

### **📋 Yêu Cầu Hệ Thống**
- Python 3.8+
- Git
- DeepSeek API Key ([Lấy tại đây](https://platform.deepseek.com/))
- Zalo App ID & Secret ([Đăng ký tại đây](https://developers.zalo.me/))
- Google Sheet API (Service Account) để lưu Lead

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
- `openai` - Client kết nối DeepSeek API
- `geopy` - Tính khoảng cách GPS
- `httpx` - HTTP client cho Zalo OAuth
- `gspread` - Kết nối Google Sheets (ghi Lead)

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
# ===== AI Configuration (DeepSeek) =====
DEEPSEEK_API_KEY=sk-...  # Lấy từ https://platform.deepseek.com/
DEEPSEEK_BASE_URL=https://api.deepseek.com

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
│   ├── main.py                 # Entry point (FastAPI) & Lead Endpoints
│   ├── models.py               # Pydantic Models for Chat & Leads
│   ├── services/
│   │   ├── ai_service.py       # DeepSeek AI logic (V3)
│   │   ├── geo_service.py      # GPS & distance calculation
│   │   ├── sheet_service.py    # Google Sheets Loader & Lead Saver
│   │   └── product_view.py     # Proxy/Scraper cho trang sản phẩm
│   └── requirements.txt        # Python dependencies
├── plan/                       # Tài liệu thiết kế & Workflow
├── index.html                  # Giao diện Chat chính
├── login.html                  # Trang đăng nhập Zalo
├── avatar-display.js           # Xử lý thông tin người dùng
├── script_app.js               # Logic Chat, Map & Persistence (Main)
├── style.css                   # Stylesheet
├── .env.example                # File cấu hình mẫu
└── README.md                   # Tài liệu hướng dẫn
```

---

## ✨ Tính Năng Chính

### 🤖 **DeepSeek AI V3 Integration**
- **Smarter Interaction:** Sử dụng DeepSeek Chat V3 cho phản hồi tự nhiên và nhanh hơn.
- **3-Tier Fallback Strategy:** Xử lý thông minh khi không tìm thấy sản phẩm chính xác.
- **Intent Extraction:** Tự động trích xuất ý định tìm kiếm (sản phẩm, danh mục, địa điểm).

### 🚀 **Lead Generation & Persistence**
- **Deep Interest Tracking:** Ghi nhận chuỗi hành vi của người dùng (xem sản phẩm, bấm vào nhóm).
- **LocalStorage Persistence:** Dữ liệu không bị mất khi đóng tab hoặc tải lại trang (đến 24h).
- **Google Sheets Lead Saver:** Tự động lưu thông tin khách (Tên, SĐT, Avatar, Link Shop, Sản phẩm quan tâm) vào Sheet "Leads".
- **Smarter Match Logic:** Tự động khớp nút "Vào nhóm" với sản phẩm thực tế người dùng vừa xem.

### 🗺️ **Location-Based Features**
- Định vị GPS người dùng và tính khoảng cách geodesic.
- Hiển thị 5 cửa hàng gần nhất với thông tin chi tiết.
- Tích hợp bản đồ Leaflet trực quan.

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

### **v4.0 - DeepSeek Core & Lead Management System** (2026-01-06)
- ✅ **Core AI Upgrade**: Chuyển từ Gemini sang **DeepSeek Chat V3** (nhanh hơn, chính xác hơn).
- ✅ **Lead Submission Workflow**: Ghi dữ liệu khách hàng tiềm năng về Google Sheet "Leads" (Timestamp, Name, Phone, Product, Shop Link).
- ✅ **Mobile RAM Optimization**: Chuyển toàn bộ hệ thống lưu trữ sang `localStorage` để dữ liệu sống sót khi trình duyệt mobile bị reload ngầm.
- ✅ **Product-Resolution Engine**: Sửa lỗi lệch thông tin Shop/Sản phẩm bằng cơ chế "Tìm ngược từ cuối history" và ưu tiên hàng chưa gửi.
- ✅ **Smooth User Flow**: Tự động ghi nhớ số điện thoại để không hỏi lại nhiều lần trong cùng một phiên làm việc.
- ✅ **Avatar & Profile Capture**: Lưu trữ và hiển thị ảnh đại diện Zalo trong quá trình chốt đơn.

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
