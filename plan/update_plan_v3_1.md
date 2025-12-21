# Kế hoạch Update V3.1 - Smart Proxy View & Order Flow tói ưu chức năng xem chi tiết sản phẩm.
## 0. bối cảnh:
các link sản phẩm trong data từ gg sheet là link truy cập thẳng vào trang chi tiết của domain dropbuy dẫn đến khi click vào link truy cập trên md dẫn đến dropbuy, hậu quả là mất tính tự chủ 
## 1. Mục tiêu Chính
Tối ưu hóa trải nghiệm xem chi tiết sản phẩm. Thay vì chỉ vào thẳng link Dropbuy, hệ thống hiện ra trang html y chang với trang chi tiết sản phẩm của dropbuy nhưng tên miền là tên miền của hệ thống này.  
## CHÚ Ý QUAN TRỌNG : đây chỉ là luồng thay thế cho UC [click xem chi tiết sản phẩm], đừng tích hợp quá sâu làm thay đổi các feature/UC/model khác.CÁC FEATURE KHÁC VỀ AI, HIEN THI CHAT BOX,... ĐANG LÀM VIỆC TỐT, ĐỪNG ĐỀ XUẤT CẢ TIẾN CHÚNG. CÁI ĐÍCH LÀ CHUYỂN ĐƯỢC USER SANG TRANG SẢN PHẨM CHI TIẾT VỚI TÊN MIỀN CỦA HỆ THỐNG NÀY + CLICK MUA HÀNG/THÊM VÀO GIỎ ĐỂ TRỎ NGƯỢC VỀ HỆ THỐNG CHAT BOX HIỂN THI MESSAGE USER QUAN TÂM SẢN PHẨM KÈM THEO LINK ZALO SẢN PHẨM(KHÔNG DÙNG AI ĐỂ VIẾT MESSAGE NÀY, CẦN 1 TEMPLATE CHUNG ĐƠN GIẢN CHO MESSAGE LÀ "Bạn đang quan tâm [Tên SP]. Bấm vào link để chat với shop ngay.") + USER CLICK LINK ZALO CHUYỂN ĐẾN GROUP ZALO.

CHI TIẾT THÌ html CÀO ĐƯỢC TỪ DROPBUY SẼ:
1.  Hiển thị chuẩn giao diện gốc của Dropbuy.
2.  **Quan trọng:** Nút "Đặt hàng" sẽ được lập trình lại để dẫn khách quay lại chat Zalo với Shop, kèm tin nhắn mẫu.
3.  Khóa các tương tác thừa (menu, link khác) để khách tập trung mua hàng.

## 2. Luồng Hoạt động (User Flow)
1.  **Khách hàng:** Hỏi mua sản phẩm.
2.  **Bot:** hoạt động luồng chat như bình thường , trả về các md thông tin sản phẩm truy xuất từ data init gg sheet .
3.  **Khách hàng:** Click button "Xem chi tiết" của 1 sản phẩm trong các md đó.
4.  **Hệ thống (Backend):**
    -   Lấy tên sản phẩm từ thẻ md của sản phẩm được click xem chi tiết
    -   Kiểm tra Cache HTML của sản phẩm đó.
    -   Nếu có: Trả về HTML đó.
    -   Tôn chỉ : hiên được tối đa nội dung của html, (làm cho như test v3)+ tên miền là tên miền của hệ thống này.
    -   *Nếu chưa có:* Tự động cào từ Dropbuy về -> Lưu Cache.
    -   *Xử lý HTML:*
        -   Giữ nguyên giao diện đẹp.
        -   Chèn Script "đóng băng" các link/button khác (Header/Menu không bấm được).
        -   **Sửa nút "Đặt hàng":** nếu click -> về chat box, kèm nội dung soạn sẵn nhắn tới user trng chat box: *"Bạn đang quan tâm [Tên Sản Phẩm]. Bấm vào link để chat với shop ngay."*; có tìm lại và gắn link zalo của shop vào trong đó.
5.  **Khách hàng:** Bấm vào link zalo của shop trong tin nhắn trên chat box đó -> Mở app Zalo -> Chat ngay với Shop.

## 3. Chi tiết Kỹ thuật
## nguyên lý tôn chỉ : làm theo code trong thư mục test. tạo 1 product_view.py trong dự án với chức năng tham khảo từ test/server_v2.py
### A. Route Hiển thị (`/view/{product_id}`)
-   **Input:** Product ID (và URL gốc nếu cần cào mới).
-   **Logic Cào (Scraper):**
    -   Giữ nguyên logic của bản Test V3 hiện tại (giữ Header/Footer).
    -   Thêm bước `inject_custom_script(html, product_info)` trước khi trả về browser.

### B. Logic "Hack" HTML (`clean_html` nới rộng)
1.  **Freeze Page (Đóng băng):**
--> tham khảo test/server_v2.py
2.  **Hijack Order Button (Chiếm quyền nút Mua):**
--> tham khảo test/server_v2.py

### C. Chatbot Integration
-   Cập nhật `ai_service.py` để khi tạo message template, trường `link_san_pham` sẽ trỏ về `/view/{id}` thay vì link gốc. Link là tự sinh trước theo tên cột [Slug] của data, sau khi click sẽ check có hay không để cào html


## 4. Các bước triển khai (Action Items)
về công nghệ : khi người dùng click vào chi tiết sản phẩm của 1 md, hệ thống(main+index) sẽ lấy mã sản phẩm goi den product_view.py để cào html và trả về cho người dùng.

## 5. Kiểm thử
-   **Test 0:** full luồng chat với shop để ra md và click xem chi tiết sản phẩm có hạt động đúng không
-   **Test 1:** test html xem có giữ nguyên giao diện gốc của dropbuy không + tên miền là tên miền của hệ thống này+ chức năng chuyển tab bị giới hạn  ngoại trừ nút mua hàng.
-   **Test 2:** Bấm nút "Mua ngay/Thêm giỏ hàng" -> quay về giao diện main kèm thông báo nội dung cho user như 1 tin nhắn bot cho user 
-   **Test 3:** Bấm vào link Zalo của shop trên câu thong báo đó -> Mở app Zalo -> Chat ngay với Shop. 
