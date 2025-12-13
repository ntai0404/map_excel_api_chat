AI Chatbot Thương Mại Điện Tử Theo Vị Trí (Location-Based)

1. Tổng Quan

Hệ thống cho phép người dùng hỏi về sản phẩm/dịch vụ thông qua giao diện Chat. Hệ thống sẽ tự động xác định vị trí người dùng, tìm cửa hàng gần nhất (từ danh sách địa chỉ trong Google Sheets), lấy thông tin tồn kho/menu tại cửa hàng đó và dùng AI để tư vấn cá nhân hóa.

Hệ thống hỗ trợ đăng nhập qua Zalo OAuth để cá nhân hóa trải nghiệm người dùng và cho phép kết nối với nhóm Zalo của cửa hàng.

2. Actors (Tác nhân)

User (Khách hàng): Người sử dụng App/Web, cần tìm mua sản phẩm.

System (Backend): Xử lý logic tìm kiếm, tính toán khoảng cách, xác thực người dùng.

Zalo OAuth Service: Cung cấp API để xác thực người dùng qua tài khoản Zalo.

Google Maps Service: Cung cấp API để chuyển đổi địa chỉ (Geocoding) và tính khoảng cách.

Google Sheets (Database): Nơi lưu trữ danh sách cửa hàng (địa chỉ dạng text) và thông tin sản phẩm.

AI Engine (Gemini/GPT): Tổng hợp thông tin và sinh câu trả lời tự nhiên.

---

3. Use Case 1: "Đăng nhập với Zalo OAuth"

**Pre-conditions (Điều kiện tiên quyết)**

- Người dùng có tài khoản Zalo.
- Ứng dụng đã được đăng ký trên Zalo Developer Portal và có App ID, App Secret.
- Backend đã cấu hình đúng Redirect URI trong file `.env`.

**Basic Flow (Luồng chính)**

1. **User**: Truy cập trang đăng nhập (`login.html`).

2. **System**: Kiểm tra session trong `localStorage`:
   - Nếu đã có session hợp lệ (chưa hết hạn 24h) → Redirect về `index.html`.
   - Nếu chưa có hoặc đã hết hạn → Hiển thị trang đăng nhập.

3. **User**: Click nút "Đăng nhập với Zalo".

4. **Frontend**: 
   - Tạo `state` ngẫu nhiên (chống CSRF attack).
   - Lưu `state` vào `localStorage`.
   - Redirect user đến Zalo OAuth URL:
     ```
     https://oauth.zaloapp.com/v4/permission?
       app_id={ZALO_APP_ID}&
       redirect_uri={REDIRECT_URI}&
       state={STATE}
     ```

5. **Zalo OAuth Service**: Hiển thị trang xác thực Zalo.

6. **User**: Đăng nhập Zalo và cho phép ứng dụng truy cập thông tin cơ bản.

7. **Zalo OAuth Service**: Redirect về Backend callback URL với:
   - `code`: Authorization code
   - `state`: State đã gửi trước đó

8. **Backend** (`/auth/zalo/callback`):
   - Validate `code` có tồn tại.
   - Gọi Zalo API để đổi `code` → `access_token`:
     ```
     POST https://oauth.zaloapp.com/v4/access_token
     Headers: 
       - Content-Type: application/x-www-form-urlencoded
       - secret_key: {ZALO_APP_SECRET}
     Body:
       - app_id: {ZALO_APP_ID}
       - code: {code}
       - grant_type: authorization_code
     ```

9. **Backend**: Nhận `access_token` từ Zalo.

10. **Backend**: Gọi Zalo Graph API để lấy thông tin user:
    ```
    GET https://graph.zalo.me/v2.0/me?
      access_token={access_token}&
      fields=id,name,picture
    ```

11. **Backend**: 
    - Tạo `session_id` unique: `zalo_{user_id}_{timestamp}`.
    - Lưu session vào memory/database:
      ```python
      {
        "user_id": "...",
        "name": "...",
        "picture": "...",
        "login_time": "ISO timestamp",
        "type": "zalo"
      }
      ```

12. **Backend**: Redirect về Frontend với query params:
    ```
    http://127.0.0.1:5500/index.html?
      session_id={session_id}&
      user_type=zalo&
      user_name={encoded_name}&
      login_time={timestamp}
    ```

13. **Frontend**: 
    - Parse query params.
    - Lưu session info vào `localStorage`:
      - `session_id`
      - `user_type`
      - `user_name`
      - `login_time`
    - Hiển thị trang chính với thông tin user.

14. **User**: Sử dụng ứng dụng với trạng thái đã đăng nhập.

**Alternative Flows (Luồng thay thế)**

**A1. User chọn "Tiếp tục với tư cách khách"**
   - Frontend lưu `user_type = "guest"` vào `localStorage`.
   - Redirect về `index.html` mà không cần xác thực Zalo.
   - Một số tính năng có thể bị giới hạn (không hiển thị tên, không lưu lịch sử chat).

**A2. Zalo OAuth trả về lỗi**
   - Backend nhận `error` parameter trong callback.
   - Hiển thị trang lỗi với thông báo và link "Thử lại".
   - User có thể quay lại trang đăng nhập.

**A3. Không lấy được access token**
   - Backend gọi API Zalo nhưng không nhận được `access_token`.
   - Log lỗi chi tiết (error_description).
   - Hiển thị trang lỗi: "Không thể kết nối với Zalo. Vui lòng thử lại sau."

**A4. Session hết hạn (sau 24h)**
   - User truy cập lại ứng dụng.
   - Frontend kiểm tra `login_time` trong `localStorage`.
   - Nếu đã quá 24h → Xóa session và redirect về trang đăng nhập.

**A5. Verify session**
   - Frontend gọi API `/auth/verify?session_id={session_id}`.
   - Backend kiểm tra session có tồn tại và còn hạn không.
   - Trả về `{valid: true/false, user: {...}}`.

**Post-conditions (Kết quả)**
- User đã đăng nhập thành công với Zalo hoặc Guest.
- Session được lưu trữ và có thời hạn 24 giờ.
- Thông tin user có thể được sử dụng để cá nhân hóa trải nghiệm.

---

4. Use Case 2: "Tìm sản phẩm & Tư vấn cửa hàng gần nhất"

Pre-conditions (Điều kiện tiên quyết)

Người dùng đã cấp quyền truy cập vị trí (GPS) cho ứng dụng.

Google Sheets chứa danh sách cửa hàng (Cột: Tên Shop, Địa chỉ text, Sản phẩm/Menu,...).

Basic Flow (Luồng chính)

User: Mở khung chat và nhập câu hỏi (Ví dụ: "Mình muốn tìm mua giày chạy bộ, size 42").

App (Client): Gửi yêu cầu lên Server gồm:

text_query: "Mình muốn tìm mua giày chạy bộ, size 42"

user_location: {lat: 10.762, long: 106.681} (Tọa độ GPS hiện tại).

Backend : gọi 1 lần model để phân tích ra [tên sản phẩm] + [loại hàng].
AI engine : Trả về [tên sản phẩm] + [loại hàng].

Backend: Đọc danh sách cửa hàng từ Google Sheets.
Backend (logic xử lý [tên sản phẩm ] và [loại hàng]):
    if (có shop có cột sản phẩm có [tên sản phẩm]) 
        Thêm shop đó vào danh sách duyệt khoảng cách
    else
        Thêm shop có cột loại hàng có [loại hàng] vào danh sách duyệt khoảng cách 
Backend (Logic xử lý vị trí):

Do địa chỉ cửa hàng là dạng Text, hệ thống thực hiện Geocoding (hoặc dùng dữ liệu cache) để lấy tọa độ các cửa hàng.

Tính toán khoảng cách từ user_location đến tất cả các cửa hàng.

Filter: Chọn ra 01 cửa hàng gần nhất (Nearest Store).

Backend: Truy xuất thông tin chi tiết của cửa hàng đó từ Sheets (Ví dụ: Shop A, còn hàng giày size 42, đang giảm giá 10%).

AI Engine: Nhận Prompt chứa:
Context: ví dụ "Cửa hàng gần nhất là Shop A (cách 500m). Sản phẩm giày chạy bộ còn hàng. Khuyến mãi 10%."

Query: ví dụ "Mình muốn tìm mua giày chạy bộ..."

AI Engine: Sinh câu trả lời tư vấn (Ví dụ: "Chào bạn, Shop A cách bạn chỉ 500m đang có sẵn mẫu giày bạn thích và được giảm 10%...").
    Thay thế: nếu biến đầu vào là [loại hàng]
        -> Thêm lệnh cho AI giải thích rằng không có sẵn sản phẩm đó gần vị trí và đây là đề xuất thay thế cho sản phẩm cùng [loại hàng]

Backend: Trả về Response cho App (Text AI + Metadata vị trí để hiển thị map).

User: Nhận được câu trả lời và bản đồ chỉ đường.

Alternative Flows (Luồng thay thế)

User không bật vị trí: Hệ thống yêu cầu User nhập địa chỉ phường/quận hiện tại -> Geocoding địa chỉ đó ra tọa độ -> Tiếp tục luồng chính.

Không tìm thấy cửa hàng gần (bán kính > 10km): AI thông báo xin lỗi và đề xuất đặt hàng online thay vì đến cửa hàng.

User không hỏi về sản phẩm mà chỉ nói "xin chào/ tạm biệt/...": Giao quyền cho AI để trả lời ngắn gọn theo văn phong tương ứng.

User hỏi về vị trí hiện tại thay vì click button:
    user nhập lệnh -> gửi gg như bước trên/ thêm logic ưu tiên phát hiện là câu hỏi về vị trí -> trả biến mylocation=true và thực thi chức năng trả lời vị trí như khi click vị trí

**A6. User muốn tham gia nhóm Zalo của cửa hàng**
   - Sau khi nhận được danh sách cửa hàng gần nhất, mỗi cửa hàng hiển thị nút "Tham gia nhóm Zalo" (nếu có `zalo_group_link`).
   - User click vào link nhóm Zalo.
   - Mở Zalo app/web và tự động yêu cầu tham gia nhóm.
   - User có thể chat trực tiếp với chủ cửa hàng hoặc nhân viên để đặt hàng, hỏi thêm thông tin.

**Post-conditions (Kết quả)**
- User nhận được thông tin cửa hàng gần nhất phù hợp với nhu cầu.
- Bản đồ hiển thị vị trí user và các cửa hàng được đề xuất.
- User có thể kết nối trực tiếp với cửa hàng qua nhóm Zalo (nếu có).