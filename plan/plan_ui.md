Kế Hoạch Triển Khai Frontend (HTML/CSS/JS)

Dự án: Location-Based AI Chatbot cho E-commerce

1. Mục tiêu

Xây dựng giao diện người dùng gồm 2 thành phần chính:

Map View: Hiển thị vị trí người dùng và ghim (marker) cửa hàng được gợi ý.

Chatbox: Nơi người dùng hỏi và nhận câu trả lời từ AI.

2. Cấu trúc thư mục

Dự án sẽ được tổ chức đơn giản như sau:

/my-ai-shop-app
├── index.html      # Cấu trúc trang web
├── style.css       # Giao diện, màu sắc, bố cục
├── script.js       # Logic xử lý vị trí, chat và bản đồ
└── assets/         # Chứa icon marker (nếu có)


3. Chi tiết các bước thực hiện

Bước 1: HTML Structure (index.html)

Tạo khung sườn cho ứng dụng. Chia màn hình thành 2 phần (trên Mobile thì Map ở trên, Chat ở dưới; Desktop thì Map bên trái, Chat bên phải).

Head: Import CSS, Leaflet CSS/JS (thư viện bản đồ), FontAwesome (icon).

Body:

#map-container: Thẻ div chứa bản đồ.

#chat-container: Thẻ div chứa giao diện chat.

#chat-messages: Khu vực hiển thị lịch sử tin nhắn (có thanh cuộn).

#chat-input-area: Khu vực nhập liệu (Input text + Button Gửi + Button Gửi Vị Trí).

Bước 2: CSS Styling (style.css)

Tạo giao diện hiện đại, thân thiện.

Layout: Sử dụng Flexbox hoặc Grid để chia bố cục.

Responsive: Sử dụng Media Query. Trên màn hình nhỏ (< 768px), chiều cao Map là 40%, Chat là 60%.

Chat Styles:

Tin nhắn User: Căn phải, nền xanh, chữ trắng.

Tin nhắn AI: Căn trái, nền xám nhạt, chữ đen.

Hiệu ứng "Typing...": Animation dấu ba chấm khi chờ AI trả lời.

Map Styles: Đảm bảo bản đồ hiển thị full chiều cao/rộng của container.

Bước 3: JavaScript Logic (script.js)

Đây là phần quan trọng nhất, xử lý luồng nghiệp vụ.

3.1. Khởi tạo Bản đồ (Map Initialization)

Sử dụng Leaflet.js để load bản đồ mặc định.

Tạo hàm updateMap(lat, lng, storeData): Hàm này sẽ nhận tọa độ và danh sách cửa hàng để xóa marker cũ và thêm marker mới.

3.2. Xử lý Vị trí (Geolocation)

Sử dụng API trình duyệt: navigator.geolocation.getCurrentPosition.

Tạo hàm getUserLocation():

Khi người dùng bấm nút gửi hoặc mới vào app, hàm này kích hoạt.

Nếu thành công -> Lưu latitude, longitude vào biến toàn cục.

Nếu thất bại (User từ chối) -> Thông báo lỗi hoặc yêu cầu nhập địa chỉ tay.

3.3. Giả lập Backend & Kết nối AI (Simulation Logic)

Do chưa kết nối Python Server thật, ta viết một hàm mockFetchAIResponse(userMessage, userLocation) để giả lập:

Input: Câu hỏi user + Tọa độ.

Process (Giả lập):

Tính toán khoảng cách (logic đơn giản).

setTimeout 1.5s (để giả vờ AI đang suy nghĩ).

Output (JSON giả): Trả về dữ liệu đúng chuẩn JSON mà Backend thật sẽ trả về.

{
  "ai_response": "Cửa hàng ABC ở 123 Lê Lợi cách bạn 500m có bán sản phẩm này ạ.",
  "stores": [
    {"name": "Cửa hàng ABC", "lat": 10.77, "lng": 106.69, "info": "..."}
  ]
}


3.4. Xử lý Chat (UI Interaction)

Lắng nghe sự kiện click nút Gửi hoặc Enter.

Bước 1: Lấy text từ input -> Hiển thị lên khung chat (User message).

Bước 2: Gọi hàm getUserLocation để lấy tọa độ mới nhất.

Bước 3: Hiển thị bong bóng "AI đang nhập...".

Bước 4: Gọi hàm gửi dữ liệu (mock hoặc fetch thật).

Bước 5: Nhận phản hồi -> Xóa "đang nhập" -> Hiển thị tin nhắn AI -> Gọi updateMap để vẽ vị trí cửa hàng lên bản đồ.

4. Đặc tả dữ liệu API (Interface Contract)

Để Frontend và Backend (sau này) làm việc khớp nhau, cần thống nhất format JSON.

Request (Frontend gửi đi):

POST /api/chat
{
  "message": "Tôi muốn mua giày size 42",
  "location": {
    "lat": 21.0285,
    "lng": 105.8542
  }
}


Response (Backend trả về):

{
  "text": "Dựa trên vị trí của bạn tại Hoàn Kiếm, Shop X (cách 200m) đang có sẵn giày size 42 màu đen.",
  "map_data": {
    "user_marker": {"lat": 21.0285, "lng": 105.8542},
    "store_markers": [
      {
        "id": "shop_01",
        "name": "Shop X - Giày Đẹp",
        "lat": 21.0300,
        "lng": 105.8500,
        "description": "Giảm giá 10% hôm nay"
      }
    ]
  }
}


5. Lộ trình code (Checklist)

[ ] Tạo file HTML với 2 div chính (Map, Chat).

[ ] Nhúng Leaflet JS và hiển thị bản đồ Hà Nội/TP.HCM mặc định.

[ ] Viết CSS cho khung chat đẹp (giống Messenger/Zalo).

[ ] Viết JS lấy toạ độ user và hiển thị marker "Tôi đang ở đây".

[ ] Viết JS giả lập phản hồi của AI (Mock Data) để test giao diện.

[ ] Ghép logic: Chat -> Map update theo dữ liệu trả về.