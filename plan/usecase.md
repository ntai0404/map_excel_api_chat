AI Chatbot Thương Mại Điện Tử Theo Vị Trí (Location-Based)

1. Tổng Quan

Hệ thống cho phép người dùng hỏi về sản phẩm/dịch vụ thông qua giao diện Chat. Hệ thống sẽ tự động xác định vị trí người dùng, tìm cửa hàng gần nhất (từ danh sách địa chỉ trong Google Sheets), lấy thông tin tồn kho/menu tại cửa hàng đó và dùng AI để tư vấn cá nhân hóa.

2. Actors (Tác nhân)

User (Khách hàng): Người sử dụng App/Web, cần tìm mua sản phẩm.

System (Backend): Xử lý logic tìm kiếm, tính toán khoảng cách.

Google Maps Service: Cung cấp API để chuyển đổi địa chỉ (Geocoding) và tính khoảng cách.

Google Sheets (Database): Nơi lưu trữ danh sách cửa hàng (địa chỉ dạng text) và thông tin sản phẩm.

AI Engine (Gemini/GPT): Tổng hợp thông tin và sinh câu trả lời tự nhiên.

3. Use Case Chính: "Tìm sản phẩm & Tư vấn cửa hàng gần nhất"

Pre-conditions (Điều kiện tiên quyết)

Người dùng đã cấp quyền truy cập vị trí (GPS) cho ứng dụng.

Google Sheets chứa danh sách cửa hàng (Cột: Tên Shop, Địa chỉ text, Sản phẩm/Menu,...).

Basic Flow (Luồng chính)

User: Mở khung chat và nhập câu hỏi (Ví dụ: "Mình muốn tìm mua giày chạy bộ, size 42").

App (Client): Gửi yêu cầu lên Server gồm:

text_query: "Mình muốn tìm mua giày chạy bộ, size 42"

user_location: {lat: 10.762, long: 106.681} (Tọa độ GPS hiện tại).

Backend : gọi 1 lần gemini để phân tích ra [tên sản phẩm] + [loại hàng].
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

NEW: 
User hỏi về vị trí hiện tại thay vì click buttom:
    user nhập lệnh -> gửi gg như bước trên/ thêm logic ưu tiên phát hiện là câu hỏi về vị trí -> trả biến mylocation=true và thực thi chức năng trả lời vị trí như khi click vị trí 