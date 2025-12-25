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
from core.logging_utils import log, log_header, log_section, log_step, log_success, log_info, set_gui_callback
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
    
    # BƯỚC 1: Khởi tạo trình duyệt
    log_header("Khởi chạy trình duyệt", tag="BROWSER")
    automation = WebAutomation(headless=headless)
    log_success("Trình duyệt đã sẵn sàng")
    
    # BƯỚC 2: Khởi tạo hệ thống
    log_header("Khởi tạo hệ thống", tag="SYSTEM")
    log_step("Khởi tạo database...")
    db_manager.test_connection(silent=True)
    log_step("Kiểm tra cập nhật (chế độ nền)...")
    init_update_manager()
    
    # BƯỚC 3: Bắt đầu tra cứu
    log_header(f"Tra cứu biển số: {license_plate}", tag="SEARCH")
    service = BienSoService(automation)

    # Theo dõi trạng thái từng trang
    page_statuses = {}
    errors = []
    
    try:
        # Trang 1: preventlistview
        log_section("115.79.139.172:8080/stp/preventlistview.do", tag="TRANG 1")
        success = service.search_site1(license_plate)
        page_statuses["Trang 1"] = "thành công" if success else "thất bại"
        if not success:
            errors.append("Trang 1: Tra cứu thất bại")

        # Trang 2: 210.245.111.1/dsnc
        log_section("210.245.111.1/dsnc", tag="TRANG 2")
        switch_to_new_tab(automation.driver)
        success = service.search_site2(license_plate)
        page_statuses["Trang 2"] = "thành công" if success else "thất bại"
        if not success:
            errors.append("Trang 2: Tra cứu thất bại")

        # Trang 3: hcm.cenm.vn
        log_section("hcm.cenm.vn", tag="TRANG 3")
        switch_to_new_tab(automation.driver)
        success = service.search_site3(license_plate)
        page_statuses["Trang 3"] = "thành công" if success else "thất bại"
        if not success:
            errors.append("Trang 3: Tra cứu thất bại")

        # Trang 4: 14.161.50.224
        log_section("14.161.50.224", tag="TRANG 4")
        switch_to_new_tab(automation.driver)
        success = service.search_site4(license_plate)
        page_statuses["Trang 4"] = "thành công" if success else "thất bại"
        if not success:
            errors.append("Trang 4: Tra cứu thất bại")
        
        # Kết thúc tra cứu
        log_header("Hoàn tất tra cứu", tag="COMPLETE")
        log_success(f"Đã tra cứu biển số: {license_plate}")
        
        # Tạo chuỗi trạng thái chi tiết cho từng trang
        trang_thai = "; ".join([f"{page}: {status}" for page, status in page_statuses.items()])
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
