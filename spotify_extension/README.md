# 🟢 Spotify Auto-Checkout Extension (Pro Edition)

Tiện ích mở rộng Chrome chuyên nghiệp giúp tự động hóa quá trình kiểm tra (check) và thanh toán trên trang checkout của Spotify. Được thiết kế tối ưu cho tốc độ và hiệu quả với các tính năng cao cấp.

---

## 🚀 Các Tính Năng Chính

### 1. Thuật Toán Gen Thẻ "Lý Tưởng" 🎲
- **Cơ chế Ngẫu nhiên Bảo mật**: Sử dụng `window.crypto.getRandomValues` kết hợp phép toán **Unbiased conversion** (chia cho `0x100000000`) để loại bỏ sai số modulo (modulo bias), đảm bảo tính ngẫu nhiên tuyệt đối của từng chữ số.
- **Hỗ trợ Pattern 'x'**: Cho phép linh hoạt nhập BIN theo định dạng `4111xxxx`, tool sẽ tự động lấp đầy các vị trí `x` bằng số ngẫu nhiên.
- **Vòng lặp Double-Verify**: Mỗi thẻ trước khi được đưa vào hàng đợi check đều phải vượt qua quy trình **Luhn Double-Check**. Thuật toán sẽ tính Checksum, sau đó kiểm tra lại toàn bộ dãy số một lần nữa để đảm bảo độ tin cậy 100%.

### 2. Live Card Preview (Real-time) ✨
- **Giao diện Glassmorphism**: Tích hợp một chiếc "thẻ ảo" ngay trong popup với hiệu ứng kính mờ và gradient màu sắc theo thương hiệu (Visa, Mastercard, Amex, v.v.).
- **Đồng bộ Tức thì**: Khi bạn nhập BIN, chọn Network, hay điền Expiry/CVV, thông tin trên thẻ ảo sẽ thay đổi theo từng phím bấm. 
- **Phát hiện mạng lưới (BIN Detection)**: Tự động hiển thị logo và màu sắc tương ứng ngay khi nhận diện được đầu số BIN.

### 3. Chế Độ Kiểm Tra Vô Tận (Infinite BIN Mode) ♾️
- Nhập BIN (6-8 chữ số đầu của thẻ).
- Tool sẽ tự động sinh thẻ ngẫu nhiên dựa trên thuật toán Luhn.
- Chạy liên tục cho từng thẻ mới cho đến khi tìm thấy thẻ **LIVE** hoặc người dùng bấm **Stop**.
- Giao diện tối giản: Chỉ hiển thị `Checking 15...` và biểu tượng `∞` để phản ánh đúng tính chất vô tận.

### 4. Chế Độ Danh Sách Thủ Công (Manual List) 📋
- Dán danh sách thẻ theo định dạng `Số thẻ|Tháng|Năm|CVV`.
- Giao diện nhập liệu tối ưu: Tháng, Năm và CVV được gộp chung một hàng ngang để tiết kiệm diện tích.

### 5. Công Nghệ Điền Thẻ Siêu Tốc (Direct Injection) ⚡
- **Filling cực nhanh**: Tool không giả lập gõ phím kiểu "mổ cò" mà đẩy nguyên dãy data vào input của Iframe.
- **Tương thích React**: Sử dụng `Object.getOwnPropertyDescriptor` để ghi đè thuộc tính `value` của HTMLInputElement, kích hoạt đầy đủ các sự kiện `input` và `change` mà React yêu cầu.

### 6. Vượt Lỗi Dùng Thử (Trial Rejection Bypass) 🚫
- Tự động phát hiện banner lỗi *"Your payment method was already used for an offer or trial"*.
- Thủ thuật thông minh: Tool sẽ gọi `window.history.back()` để đưa trang thanh toán về trạng thái chọn phương thức.
- Tự động click radio button `#option-cards` để mở lại form nhập liệu cho thẻ tiếp theo, giúp quá trình check không bị gián đoạn.

### 7. Quản lý Cài đặt (Advanced Settings) ⚙️
- **Delay cực thấp**: Hỗ trợ thiết lập Fill Delay từ **50ms** và Loop Delay từ **100ms**.
- **Lưu trữ cục bộ**: Toàn bộ cấu hình BIN mặc định, định dạng Ngày/CVV và Delay được lưu vào `chrome.storage.local`, tự động nạp lại khi mở extension.
- **Layout Tối giản**: Đã lược bỏ các ô nhập dư thừa (Quantity) ở màn hình chính để tập trung vào hiệu suất.

### 8. Hệ Thống Log & Statistics 📊
- Thống kê chi tiết: **Tried**, **Live**, **Dead**.
- Xuất dữ liệu: Nút **Export Log** cho phép tải về toàn bộ lịch sử check dưới dạng file `.txt`.

---

## 🛠️ Hướng Dẫn Sử Dụng

1. **Cài đặt**: 
   - Giải nén mã nguồn.
   - Truy cập `chrome://extensions`.
   - Bật *Developer Mode* và chọn *Load unpacked*, trỏ vào thư mục extension.
2. **Cài đặt tham số**:
   - Nhấn vào biểu tượng ⚙️ (Settings) để chỉnh Delay và thông tin mặc định.
3. **Bắt đầu**:
   - Truy cập trang thanh toán (Checkout) của Spotify.
   - Mở Popup, nhập BIN hoặc danh sách thẻ.
   - Nhấn **Run** để bắt đầu quá trình tự động hóa.
4. **Kết quả**:
   - Nếu thẻ **LIVE**, tool sẽ dừng lại và hiển thị thông báo.
   - Nếu thẻ **DEAD**, tool tự retry ngay lập tức.

---

## 📦 Thành Phần Kỹ Thuật

- **manifest.json**: Cấu hình quyền hạn (scripting, storage, activeTab).
- **background.js**: Runner trung tâm, quản lý vòng lặp và trạng thái vô tận.
- **content.js**: "Cánh tay" thực thi, tương tác trực tiếp DOM, xử lý Iframe PCI và sự kiện Submit.
- **cardGenerator.js**: Thuật toán sinh thẻ chuẩn ngân hàng (Luhn check).
- **popup.js/html/css**: Giao diện người dùng hiện đại với Flexbox và Grid layout.

---
*Ghi chú: Tool chỉ phục vụ mục đích học tập và tự động hóa quy trình cá nhân. Vui lòng sử dụng đúng quy định pháp luật.*
