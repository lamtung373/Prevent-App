"""
Entry point cho hệ thống tra cứu đương sự.

Tra cứu đương sự bằng số Căn cước công dân hoặc số Căn cước.
Cấu hình:
  - Trang 1: preventlistview - nhập số căn cước.
  - Trang 2: 210.245.111.1/dsnc - chọn radio rblTableType_2, nhập số căn cước vào txtP2.
  - Trang 3: hcm.cenm.vn - chọn menu Đương sự, nhập số căn cước vào so_cmt.
  - Trang 4: 14.161.50.224 - điều hướng đến URL với option2=1&keyword=số_căn_cước.
"""

import sys
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
from services.duong_su_service import DuongSuService


def tra_cuu_duong_su(
    so_can_cuoc: str,
    headless: bool = False,
    gui_callback: Optional[Callable[[str], None]] = None,
):
    """
    Tra cứu đương sự bằng số căn cước công dân.
    
    Args:
        so_can_cuoc: Số căn cước công dân hoặc số căn cước
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
    log_header(f"Tra cứu đương sự: {so_can_cuoc}", tag="SEARCH")
    service = DuongSuService(automation)

    # Theo dõi trạng thái từng trang
    page_statuses = {}
    errors = []
    
    try:
        # Trang 1: preventlistview
        log_section("115.79.139.172:8080/stp/preventlistview.do", tag="TRANG 1")
        success = service.search_site1(so_can_cuoc)
        page_statuses["Trang 1"] = "thành công" if success else "thất bại"
        if not success:
            errors.append("Trang 1: Tra cứu thất bại")

        # Trang 2: 210.245.111.1/dsnc
        log_section("210.245.111.1/dsnc", tag="TRANG 2")
        switch_to_new_tab(automation.driver)
        success = service.search_site2(so_can_cuoc)
        page_statuses["Trang 2"] = "thành công" if success else "thất bại"
        if not success:
            errors.append("Trang 2: Tra cứu thất bại")

        # Trang 3: hcm.cenm.vn
        log_section("hcm.cenm.vn", tag="TRANG 3")
        switch_to_new_tab(automation.driver)
        success = service.search_site3(so_can_cuoc)
        page_statuses["Trang 3"] = "thành công" if success else "thất bại"
        if not success:
            errors.append("Trang 3: Tra cứu thất bại")

        # Trang 4: 14.161.50.224
        log_section("14.161.50.224", tag="TRANG 4")
        switch_to_new_tab(automation.driver)
        success = service.search_site4(so_can_cuoc)
        page_statuses["Trang 4"] = "thành công" if success else "thất bại"
        if not success:
            errors.append("Trang 4: Tra cứu thất bại")

        # Kết thúc tra cứu
        log_header("Hoàn tất tra cứu", tag="COMPLETE")
        log_success(f"Đã tra cứu đương sự: {so_can_cuoc}")
        
        # Tạo chuỗi trạng thái chi tiết cho từng trang
        trang_thai = "; ".join([f"{page}: {status}" for page, status in page_statuses.items()])
        ghi_chu = "; ".join(errors) if errors else None
        
        db_manager.log_search(
            loai_tra_cuu="duong_su",
            thong_tin_tra_cuu=so_can_cuoc,
            trang_thai=trang_thai,
            ghi_chu=ghi_chu
        )

    except Exception as exc:  # pragma: no cover - bảo vệ runtime
        log.error("Lỗi: %s", exc)


def main():
    """Nhập thông tin và thực hiện tra cứu đương sự."""
    if len(sys.argv) > 1:
        so_can_cuoc = sys.argv[1].strip()
    else:
        so_can_cuoc = input("\nNhập số Căn cước công dân hoặc số Căn cước: ").strip()

    if not so_can_cuoc:
        log.error("Số căn cước không được để trống!")
        sys.exit(1)

    headless = False
    tra_cuu_duong_su(so_can_cuoc, headless=headless)


if __name__ == "__main__":
    main()

