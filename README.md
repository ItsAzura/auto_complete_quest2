# Auto Quiz Automation Tool

Công cụ tự động trả lời câu hỏi trắc nghiệm trên trang web `thitructuyen.vnmac.gov.vn` sử dụng Playwright.

## 📋 Tính năng
- **Tự động nhận diện bài thi:** Script sẽ tự động phát hiện khi bạn chuyển sang trang làm bài (`/BaiThi`) và có câu hỏi xuất hiện.
- **So khớp thông minh:** Sử dụng thuật toán so khớp mờ (Fuzzy Matching) để tìm đáp án chính xác nhất ngay cả khi có sự khác biệt nhỏ về dấu câu hoặc định dạng (A., B., 1., ...).
- **Thao tác Click an toàn:** Tự động kích hoạt các thành phần điều khiển (radio button/checkbox) bên trong thẻ đáp án.
- **Hỗ trợ Unicode:** Hiển thị tiếng Việt chuẩn trên terminal Windows.

## 🛠️ Yêu cầu hệ thống
- Python 3.8 trở lên.
- Trình duyệt Chromium (được cài đặt qua Playwright).

## 🚀 Cài đặt

1. **Tải/Copy mã nguồn** vào một thư mục trên máy tính.
2. **Cài đặt các thư viện cần thiết:**
   Mở Terminal (PowerShell hoặc CMD) tại thư mục dự án và chạy:
   ```bash
   pip install -r requirements.txt
   ```
3. **Cài đặt trình duyệt cho Playwright:**
   ```bash
   python -m playwright install chromium
   ```

## 📖 Hướng dẫn sử dụng

### Bước 1: Cập nhật dữ liệu câu hỏi
Mở file `questions_data.py` và điền danh sách câu hỏi - đáp án theo định dạng:
```python
QUESTIONS_DATA = [
    {
        "question": "Nội dung câu hỏi...",
        "answer": "Nội dung đáp án đúng..."
    },
    # Thêm các câu hỏi khác tại đây
]
```

### Bước 2: Chạy công cụ
Chạy lệnh sau trong terminal:
```bash
python auto_quiz.py
```

### Bước 3: Thao tác trên trình duyệt
1. Script sẽ mở trình duyệt và truy cập trang chủ cuộc thi.
2. Bạn tiến hành **nhập thông tin cá nhân** (họ tên, đơn vị, ...) một cách thủ công.
3. Nhấn nút **"Vào thi"** trên trang web.
4. **Chờ đợi:** Script sẽ tự động phát hiện khi trang bài thi tải xong (thông báo `🚀 Đã phát hiện câu hỏi trên trang!`).
5. **Tự động làm bài:** Script sẽ tự động quét và chọn đáp án cho tất cả các câu hỏi có trong dữ liệu.

### Bước 4: Kiểm tra và Nộp bài
- Sau khi script chạy xong, bạn hãy kiểm tra lại một lượt các đáp án đã chọn.
- Tự nhấn nút **"Nộp bài"** trên trình duyệt để hoàn tất.

## ⚠️ Lưu ý
- Script chỉ chọn những câu hỏi có trong file `questions_data.py`. Nếu câu hỏi lạ xuất hiện, script sẽ bỏ qua (Skipped).
- Không đóng terminal trong lúc script đang chạy.
- Nếu gặp lỗi "Execution context was destroyed", hãy bình tĩnh, script sẽ tự động thử lại sau vài giây khi trang load ổn định.
# auto_complete_quest2
