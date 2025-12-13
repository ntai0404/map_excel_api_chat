Kế Hoạch Triển Khai (Technical Plan)

Thách thức chính

1. **Authentication & Session Management**: Cần hệ thống xác thực người dùng qua Zalo OAuth và quản lý session.

2. **Dữ liệu vị trí**: Dữ liệu vị trí trong Google Sheets là Text Address (ví dụ: "123 Đường Láng, Hà Nội"), nhưng User gửi lên là GPS Coordinates.
   -> Giải pháp: Cần chuẩn hóa dữ liệu (Geocoding) trước khi so sánh.

Các bước thực hiện

---

## Giai đoạn 0: Authentication System (Zalo OAuth)

### 0.1. Đăng ký Zalo Developer App

- Truy cập [Zalo Developer Portal](https://developers.zalo.me/)
- Tạo ứng dụng mới và lấy:
  - `ZALO_APP_ID`
  - `ZALO_APP_SECRET`
- Cấu hình Redirect URI: `http://127.0.0.1:8000/auth/zalo/callback`

### 0.2. Backend Configuration

**File `.env`:**
```env
ZALO_APP_ID=your_app_id_here
ZALO_APP_SECRET=your_app_secret_here
ZALO_REDIRECT_URI=http://127.0.0.1:8000/auth/zalo/callback
SESSION_SECRET_KEY=your-secret-key-change-in-production
```

**Dependencies (`requirements.txt`):**
- `httpx` - Để gọi Zalo OAuth APIs
- `python-dotenv` - Để load environment variables

### 0.3. Backend Implementation

**Endpoints cần implement:**

1. **`GET /auth/zalo/callback`**
   - Nhận `code` và `state` từ Zalo
   - Exchange code → access_token
   - Lấy user info từ Zalo Graph API
   - Tạo session_id và lưu vào memory/database
   - Redirect về frontend với session info

2. **`GET /auth/verify`**
   - Verify session_id có hợp lệ không
   - Check session timeout (24 hours)
   - Return user info nếu valid

**Session Storage:**
- Development: In-memory dictionary
- Production: Redis hoặc database table

**Session Structure:**
```python
{
  "session_id": "zalo_{user_id}_{timestamp}",
  "user_id": "zalo_user_id",
  "name": "User Name",
  "picture": "avatar_url",
  "login_time": "ISO timestamp",
  "type": "zalo" | "guest"
}
```

### 0.4. Frontend Implementation

**File `login.html`:**
- UI với 2 options:
  1. "Đăng nhập với Zalo" button
  2. "Tiếp tục với tư cách khách" button
- JavaScript xử lý:
  - Generate random `state` (CSRF protection)
  - Redirect đến Zalo OAuth URL
  - Session check (auto-redirect nếu đã login)

**File `index.html` updates:**
- Parse URL params khi redirect về từ backend
- Lưu session vào `localStorage`:
  - `session_id`
  - `user_type` (zalo/guest)
  - `user_name`
  - `login_time`
- Hiển thị thông tin user (avatar, tên)
- Check session timeout (24h)

**Session Management:**
```javascript
// Check session validity
const loginTime = new Date(localStorage.getItem('login_time'));
const now = new Date();
const hoursDiff = (now - loginTime) / (1000 * 60 * 60);

if (hoursDiff >= 24) {
  // Session expired
  localStorage.clear();
  window.location.href = 'login.html';
}
```

### 0.5. OAuth Flow

```
User → login.html
  ↓ Click "Đăng nhập Zalo"
Frontend → https://oauth.zaloapp.com/v4/permission
  ↓ User authenticates
Zalo → Backend /auth/zalo/callback (with code)
  ↓ Exchange code → access_token
Backend → Zalo Graph API (get user info)
  ↓ Create session
Backend → Redirect to index.html?session_id=...
  ↓ Save to localStorage
Frontend → Display user info
```

---


Giai đoạn 1: Chuẩn bị Dữ liệu (Data Preparation)

Tối ưu hóa hiệu năng: Không nên Geocode mỗi khi user chat, hãy Geocode trước.

Cấu trúc Google Sheets:

Cột A: Store ID

Cột B: Store Name

Cột C: Address (Text) (Input gốc)

Cột D: Inventory/Menu Info (Dữ liệu cho AI)

Cột E (New): Latitude (Tự động điền)

Cột F (New): Longitude (Tự động điền)

Script chuẩn hóa (Apps Script hoặc Python Cronjob):

Viết script chạy định kỳ check Cột C.

Gọi Google Maps Geocoding API để đổi "Address Text" -> "Lat/Long".

Lưu vào Cột E và F.

Lý do: Giúp việc truy vấn real-time nhanh hơn và tiết kiệm chi phí API Maps.

Giai đoạn 2: Backend Development (Python/Node.js)

API Endpoint (/chat): Nhận input text + lat/long user.

Logic "Find Nearest Store":

Lấy list cửa hàng (đã có Lat/Long từ Giai đoạn 1).

Sử dụng công thức Haversine Distance (tính khoảng cách đường chim bay giữa 2 tọa độ) để tìm min distance.

Lọc ra Top 1 hoặc Top 3 cửa hàng gần nhất.

Prompt Engineering (RAG):

Template:

Bạn là trợ lý ảo bán hàng.
Thông tin ngữ cảnh: Khách hàng đang ở [Vị trí User].
Cửa hàng gần nhất: [Tên Shop] tại [Địa chỉ], cách [Khoảng cách] km.
Thông tin sản phẩm tại shop này: [Dữ liệu Inventory].
Câu hỏi khách hàng: [User Input].
Hãy trả lời thân thiện, mời khách đến cửa hàng hoặc hướng dẫn đường đi.


Giai đoạn 3: Frontend (App/Web)

Location Permission: Xin quyền truy cập GPS (navigator.geolocation).

UI Chat: Hiển thị tin nhắn AI.

UI Maps: Nhận Metadata từ Backend (tọa độ Shop tìm được) để hiển thị Marker trên bản đồ nhúng.

Giai đoạn 4: Integration & Testing

Test trường hợp địa chỉ trong Sheet viết sai chính tả (Geocoding API trả về lỗi -> Xử lý ngoại lệ).

Test trường hợp User ở quá xa tất cả cửa hàng.