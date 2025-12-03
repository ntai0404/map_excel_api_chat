Kế Hoạch Triển Khai (Technical Plan)

Thách thức chính

Dữ liệu vị trí trong Google Sheets là Text Address (ví dụ: "123 Đường Láng, Hà Nội"), nhưng User gửi lên là GPS Coordinates.
-> Giải pháp: Cần chuẩn hóa dữ liệu (Geocoding) trước khi so sánh.

Các bước thực hiện

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