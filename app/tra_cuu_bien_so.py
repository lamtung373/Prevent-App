"""
Entry point cho hệ thống tra cứu biển số xe.

Script tự động hóa: Đăng nhập -> Nhập liệu -> Tìm kiếm
Sử dụng Selenium để tự động hóa trình duyệt web
"""

import sys
import traceback
from pathlib import Path
from typing import Callable, Optional

# Đảm bảo có thể import từ app khi chạy từ bất kỳ đâu
app_dir = Path(__file__).parent
if str(app_dir) not in sys.path:
    sys.path.insert(0, str(app_dir))

from core.automation import WebAutomation
from core.config import config
from core.logging_utils import log, log_section, set_gui_callback
from core.shared_utils import init_update_manager, switch_to_new_tab
from core.database import db_manager
from services.bien_so_service import BienSoService


def tra_cuu_bien_so(
    license_plate: str, 
    headless: bool = False, 
    gui_callback: Optional[Callable[[str], None]] = None
):
    """
    Tra cứu biển số đồng thời trên nhiều trang:
      - Trang 1: preventlistview
      - Trang 2: 210.245.111.1/dsnc
      - Trang 3: hcm.cenm.vn
      - Trang 4: 14.161.50.224/dang-nhap
    
    Args:
        license_plate: Biển số xe cần tra cứu
        headless: Chạy trình duyệt ở chế độ ẩn
        gui_callback: Callback để gửi log đến GUI (optional)
    """
    if gui_callback:
        set_gui_callback(gui_callback)
    
    # Khởi tạo Chrome trước để mở ngay (không chờ update check)
    automation = WebAutomation(headless=headless)
    
    # Khởi động background update check sau khi Chrome đã mở (không block)
    init_update_manager()
    
    service = BienSoService(automation)

    # Theo dõi lỗi để ghi vào ghi chú
    errors = []
    
    try:
        # Lấy cấu hình từ config
        site1_selectors = config.site1_selectors

        # Bước 1: Trang preventlistview (Site 1)
        log_section("TRANG 1: 115.79.139.172:8080/stp/preventlistview.do")
        try:
            service.search_site1(license_plate)
        except Exception as e:
            errors.append(f"Trang 1: {str(e)}")

        # Bước 2: Trang 210.245.111.1/dsnc (Site 2)
        log_section("TRANG 2: 210.245.111.1/dsnc")
        switch_to_new_tab(automation.driver)
        try:
            service.search_site2(license_plate)
        except Exception as e:
            errors.append(f"Trang 2: {str(e)}")

        # Bước 3: Trang hcm.cenm.vn (Site 3)
        log_section("TRANG 3: hcm.cenm.vn")
        switch_to_new_tab(automation.driver)
        try:
            service.search_site3(license_plate)
        except Exception as e:
            errors.append(f"Trang 3: {str(e)}")

        # Bước 4: Trang 14.161.50.224/dang-nhap (Site 4)
        log_section("TRANG 4: 14.161.50.224/dang-nhap")
        switch_to_new_tab(automation.driver)
        try:
            service.search_site4(license_plate)
        except Exception as e:
            errors.append(f"Trang 4: {str(e)}")
        
        log.info("")
        log.info("═ HOÀN TẤT")
        log.info("Đã tra cứu biển số: %s", license_plate)
        
        # Ghi lịch sử 1 lần sau khi hoàn tất tất cả các trang
        trang_thai = "thành công" if not errors else "lỗi"
        ghi_chu = "; ".join(errors) if errors else None
        db_manager.log_search(
            loai_tra_cuu="bien_so",
            thong_tin_tra_cuu=license_plate,
            trang_thai=trang_thai,
            ghi_chu=ghi_chu
        )

    except Exception as exc:
        log.error("Lỗi: %s", exc)
        traceback.print_exc()


def main():
    """Hàm main - Tra cứu biển số xe."""
    if len(sys.argv) > 1:
        license_plate = sys.argv[1].strip()
    else:
        license_plate = input("\nNhập biển số xe cần tra cứu (ví dụ: 30A-12345): ").strip()

    if not license_plate:
        log.error("Biển số không được để trống!")
        sys.exit(1)

    headless = False
    tra_cuu_bien_so(license_plate, headless=headless)


if __name__ == "__main__":
    main()
