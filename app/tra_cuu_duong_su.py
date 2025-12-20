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
from core.logging_utils import log, log_section, set_gui_callback
from core.shared_utils import init_update_manager, switch_to_new_tab
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
    
    # Khởi tạo Chrome trước để mở ngay (không chờ update check)
    automation = WebAutomation(headless=headless)
    
    # Khởi động background update check sau khi Chrome đã mở (không block)
    init_update_manager()
    
    service = DuongSuService(automation)

    try:
        # Bước 1: Trang preventlistview (Site 1)
        log_section("TRANG 1: 115.79.139.172:8080/stp/preventlistview.do")
        service.search_site1(so_can_cuoc)

        # Bước 2: Trang 210.245.111.1/dsnc (Site 2)
        log_section("TRANG 2: 210.245.111.1/dsnc")
        switch_to_new_tab(automation.driver)
        service.search_site2(so_can_cuoc)

        # Bước 3: Trang hcm.cenm.vn (Site 3)
        log_section("TRANG 3: hcm.cenm.vn")
        switch_to_new_tab(automation.driver)
        service.search_site3(so_can_cuoc)

        # Bước 4: Trang 14.161.50.224/dang-nhap (Site 4)
        log_section("TRANG 4: 14.161.50.224/dang-nhap")
        switch_to_new_tab(automation.driver)
        service.search_site4(so_can_cuoc)

        log.info("")
        log.info("═ HOÀN TẤT")
        log.info("Đã tra cứu đương sự với số căn cước: %s", so_can_cuoc)

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

