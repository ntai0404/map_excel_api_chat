graph TD
    %% Node 1: User Action
    A["<b>USER</b><br>Click nút 'Quan tâm'"]
    
    %% Action 1
    A -->|"(1) Click button"| B

    %% Node 2: Frontend
    B["<b>WEBSITE / LANDING</b><br>- JS bắt sự kiện<br>- Gom data<br>name, phone, ..."]

    %% Action 2
    B -->|"(2) HTTP POST (JSON)"| C

    %% Node 3: Backend Processing
    C["<b>GOOGLE APPS SCRIPT (API)</b><br>Web App / Webhook<br>- doPost(e)<br>- Validate data<br>- Optional: check API key"]

    %% Action 3
    C -->|"(3) appendRow()"| D

    %% Node 4: Storage
    D["<b>GOOGLE SHEET</b><br>Sheet: 'Leads / Interest'<br>- Lưu từng click<br>- Tự động timestamp"]

## Kế hoạch: Quy trình Thu thập Khách hàng tiềm năng (Leads)

**Mục tiêu:** Ghi nhận sự kiện "Quan tâm" của người dùng và lưu vào Google Sheet để đội sales chăm sóc.

1.  **Kích hoạt (Trigger):** Người dùng bấm nút "Quan tâm" / "Vào nhóm" trong Chatbox.
2.  **Thu thập dữ liệu (Frontend):**
    *   `Script.js` bắt sự kiện click.
    *   **Ngữ cảnh (Context):** Trích xuất toàn bộ lịch sử chat liên quan đến "Mối quan tâm" (tên sản phẩm, câu hỏi...) để hiểu nhu cầu.
    *   **Thông tin User:** Tên User, Session ID (nếu đã đăng nhập).
    *   **Sản phẩm:** Thông tin sản phẩm/shop hiện tại.
3.  **Truyền tải (Transmission):**
    *   Frontend gửi một request `POST` ngầm (background) đến Backend API `/api/submit-lead`.
    *   Người dùng vẫn được chuyển hướng sang Zalo Group (tab mới) như bình thường, không bị gián đoạn.
4.  **Xử lý Backend:**
    *   Nhận JSON payload.
    *   Định dạng dòng dữ liệu: `[Thời gian, Tên User, Sản phẩm, Ngữ cảnh Chat, Trạng thái=Mới]`.
    *   Ghi thêm dòng (Append) vào Sheet `Leads` thông qua Google Sheets API.

---

### 5. Thiết kế Google Sheet (Cấu trúc dữ liệu)

Chúng ta sẽ tạo một Tab mới tên là **`Leads`** (hoặc `Quan_Tam`) trong file Google Sheet hiện có.

**Các cột dữ liệu (Columns):**

| Cột (Column) | Ý nghĩa | Ví dụ dữ liệu |
| :--- | :--- | :--- |
| **A - Timestamp** | Thời gian ghi nhận | `2024-05-20 14:30:05` |
| **B - User Name** | Tên khách hàng (nếu có) | `Nguyễn Văn A` (hoặc `Khách vãng lai`) |
| **C - User ID** | ID định danh (Session/Zalo ID) | `zalo_123456...` |
| **D - Product Name** | Sản phẩm đang xem | `Ghế Massage Hyundai AF01` |
| **E - Shop Name** | Tên cửa hàng | `Kho Tổng Hà Nội` |
| **G - Chat Context** | Tóm tắt nhu cầu (từ lịch sử chat) | `Khách hỏi giá và phí ship về Cầu Giấy...` |
| **H - Zalo Contact** | Liên hệ Zalo (SĐT/Link) | `098xxxxxxx` / `zalo.me/user_id` |
| **I - Zalo Group** | Link nhóm khách đã join | `https://zalo.me/g/abc...` |
| **K - Status** | Trạng thái xử lý (cho Sales) | `New` (Mới) / `Contacted` (Đã gọi) / `Done` |

### 6. Cơ chế ghi dữ liệu (Technical Flow)

Để đảm bảo hiệu suất và không làm chậm user, cơ chế ghi sẽ như sau:

1.  **Backend Service (`sheet_service.py`):**
    *   Sử dụng hàm có sẵn `append_row` (của thư viện `gspread` hoặc Google API).
    *   Hàm mới: `def save_lead_to_sheet(lead_data: dict) -> bool`
2.  **Xử lý bất đồng bộ (Async):**
    *   API `/api/submit-lead` sẽ trả về `200 OK` ngay lập tức cho Frontend sau khi nhận request.
    *   Việc ghi vào Google Sheet sẽ được chạy dưới dạng **Background Task** (`fastapi.BackgroundTasks`) để tránh việc User phải chờ hệ thống kết nối với Google.
3.  **Validation:**
    *   Kiểm tra trùng lặp: Nếu cùng 1 User bấm quan tâm cùng 1 sản phẩm trong vòng 5 phút -> Chỉ ghi nhận 1 lần hoặc update timestamp (tránh spam).

---

### 7. Cơ chế tách Context thông minh (Context Slicing)

Để đảm bảo nội dung chat gắn đúng với sản phẩm (tránh râu ông nọ cắm cằm bà kia), ta dùng cơ chế **"Mốc Sự Kiện" (Event Checkpoint)**:

1.  **Mốc bắt đầu:**
    *   Mỗi khi AI trả lời về một sản phẩm mới (hoặc User tìm kiếm mới), Frontend sẽ lưu lại thời điểm đó: `last_product_search_time`.
    *   Đồng thời lưu ID sản phẩm đó vào biến: `current_context_product_id`.

2.  **Mốc kết thúc:**
    *   Là lúc User bấm nút "Quan tâm".

3.  **Quy tắc cắt:**
    *   Hệ thống chỉ lấy các tin nhắn nằm trong khoảng `[last_product_search_time ... hiện tại]`.
    *   Nếu User hỏi liên miên 5 sản phẩm, thì khi bấm quan tâm SP thứ 5, hệ thống chỉ lấy đoạn chat **sau thời điểm** bắt đầu tìm kiếm SP thứ 5. Các đoạn chat về SP 1, 2, 3, 4 trước đó sẽ bị loại bỏ khỏi context của dòng này.

**Ví dụ Minh họa Logic:**
*   `10:00`: User tìm "Máy giặt". (AI set `context_start_time = 10:00`)
*   `10:01`: Hỏi "Máy này tốn điện không?"
*   `10:05`: User tìm tiếp "Tủ lạnh". (AI **Reset** `context_start_time = 10:05` -> Ngắt context máy giặt).
*   `10:06`: Hỏi "Tủ lạnh này bao nhiêu lít?"
*   `10:07`: **Bấm QUAN TÂM Tủ Lạnh.**
    *   -> Hệ thống chỉ lấy tin nhắn từ `10:05` trở đi (đoạn hỏi về Tủ lạnh).
    *   -> Đoạn hỏi về Máy giặt (10:00 - 10:01) tự động lọc bỏ.

Cách này đảm bảo độ chính xác **99%** cho Sales!