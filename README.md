# Hệ Thống Tra Cứu Tự Động

Chương trình tự động đăng nhập và tra cứu biển số xe / sổ hồng trên các trang được cấu hình sẵn bằng Selenium.

## Cài đặt thủ công

```bash
pip install -r app/requirements.txt
python app/tra_cuu_bien_so.py
```

## Tính năng chính

- Tự động đăng nhập và tra cứu trên 4 trang đã cấu hình.
- Hỗ trợ tra cứu biển số xe và sổ hồng.
- Log chuẩn theo định dạng thời gian | cấp độ | nội dung.
- Giữ trình duyệt Chrome mở sau khi hoàn tất để xem kết quả.
- Tự động cập nhật từ GitHub khi có phiên bản mới.

## Cách sử dụng nhanh (khuyến nghị)

1. Double-click `TraCuuNganChan.bat` ở thư mục gốc.
2. Chương trình sẽ tự động kiểm tra Python và cài đặt thư viện nếu cần.
3. Chọn loại tra cứu: [1] Biển số xe hoặc [2] Sổ hồng.
4. Nhập thông tin tra cứu khi được yêu cầu:
   - Biển số: ví dụ `30A-12345`
   - Sổ hồng: số seri sổ (bắt buộc), thửa đất số và tờ bản đồ số (tùy chọn)
5. Chờ chương trình tự động tra cứu, trình duyệt Chrome sẽ mở kết quả.

## Cấu trúc

### Entry Points
- `app/main.py` – Entry point chính với menu lựa chọn (được gọi từ TraCuuNganChan.bat).
- `app/tra_cuu_bien_so.py` – Entry point tra cứu biển số xe.
- `app/tra_cuu_so_hong.py` – Entry point tra cứu sổ hồng.

### Core Modules
- `app/core/automation.py` – Class WebAutomation cho tự động hóa trình duyệt.
- `app/core/config.py` – Quản lý cấu hình và credentials từ .env file.
- `app/core/logging_utils.py` – Utilities cho logging.
- `app/core/shared_utils.py` – Utilities dùng chung (update manager, tab switching).

### Services
- `app/services/bien_so_service.py` – Service xử lý tra cứu biển số.
- `app/services/so_hong_service.py` – Service xử lý tra cứu sổ hồng.

### Khác
- `app/requirements.txt` – Thư viện cần thiết.
- `app/update_manager.py` – Quản lý cập nhật tự động từ GitHub.
- `app/check_and_apply_update.py` – Script kiểm tra và áp dụng cập nhật.
- `TraCuuNganChan.bat` – File chạy chính ở thư mục gốc, gọi app/main.py.
- `_internal/HUONG_DAN_SU_DUNG.txt` – Hướng dẫn sử dụng cho người dùng.
- `_internal/README.md` – Tài liệu kỹ thuật này.

