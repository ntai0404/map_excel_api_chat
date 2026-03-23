# Bản Cập Nhật Hệ Thống - 20/03/2026

## 1. Thay Đổi Key & AI Provider (NVIDIA)
Hệ thống đã chuyển đổi nhà cung cấp AI từ DeepSeek trực tiếp sang **NVIDIA API** để tăng cường tính ổn định và khả năng mở rộng.

*   **Model Hiện Tại**: `deepseek-ai/deepseek-v3.1` (Hosted on NVIDIA).
*   **API Key**: Cấu hình thông qua biến môi trường `NVIDIA_API_KEY`.
*   **Base URL**: `https://integrate.api.nvidia.com/v1`.

## 2. Các Thay Đổi Về Code & Tính Năng
*   **Tối Ưu Phản Hồi JSON**: Đã triển khai helper `extract_json` trong `ai_service.py` để xử lý các phản hồi JSON nằm trong khối markdown (```json ... ```), giúp tránh lỗi "Intent Extraction Error".
*   **Giám Sát Quota (Logging)**: Thêm tính năng tự động ghi log token sau mỗi yêu cầu AI.
    *   Log hiển thị dưới dạng: `📊 [AI-QUOTA-CHECK] Model: ... | Prompt: X | Completion: Y | TOTAL: Z`.
*   **Sửa Lỗi Bản Đồ (Location Sanity Check)**: 
    *   Thêm kiểm tra `isInVietnam()` trong `script_app.js`.
    *   Cảnh báo người dùng nếu trình duyệt trả về vị trí sai (ví dụ: Kansas/USA - lỗi phổ biến do cài đặt trình duyệt hoặc môi trường test).
*   **Sửa Lỗi Dịch Vụ**: Khắc phục lỗi `TypeError` trong hàm `find_nearest_stores` do thiếu tham số `max_distance_km`.

## 3. Thống Kê Hiệu Năng & Token (Ước Tính)
Dựa trên các log thực tế thu thập được trong quá trình kiểm thử:

| Chỉ số | Trung bình (Normal) | Truy vấn lớn (Category List) |
| :--- | :--- | :--- |
| **Token Đầu Vào (Prompt)** | 100 - 250 tokens | ~950 - 1000 tokens |
| **Token Đầu Ra (Completion)** | 60 - 80 tokens | 60 - 100 tokens |
| **Tổng Token (Total)** | **160 - 330 tokens** | **~1000 - 1100 tokens** |
| **Thời gian phản hồi** | ~1.5 - 3.0 giây | ~3.0 - 5.0 giây |

## 4. Sự Khác Biệt So Với Key Cũ
1.  **Độ ổn định**: NVIDIA API có tỷ lệ lỗi thấp hơn và không bị giới hạn gắt gao như các key miễn phí/thử nghiệm trước đó.
2.  **Khả năng xử lý**: Model V3.1 thông minh hơn, phân tích ý định (Intent) chính xác hơn so với các bản R1 Distill nhỏ.
3.  **Chi phí**: Token input được tối ưu hóa thông qua việc chọn lọc danh sách category truyền vào AI.

---
*Lưu ý: Luôn kiểm tra file `.env` để đảm bảo key `NVIDIA_API_KEY` là bản mới nhất.*
