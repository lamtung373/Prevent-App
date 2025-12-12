"""
Script tự động kiểm tra, tải và cài đặt update từ GitHub.
Chạy sau khi tra cứu xong, không ảnh hưởng tốc độ tra cứu.
"""

import logging
import sys
from pathlib import Path

# Đảm bảo có thể import từ app khi chạy từ bất kỳ đâu
app_dir = Path(__file__).parent
if str(app_dir) not in sys.path:
    sys.path.insert(0, str(app_dir))

from update_manager import UpdateManager

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(message)s",
    handlers=[logging.StreamHandler()]
)
log = logging.getLogger(__name__)


def main():
    """Kiểm tra và cài đặt update tự động."""
    try:
        log.info("[Update] Kiểm tra cập nhật tự động")
        
        # Lấy đường dẫn app directory
        app_dir = Path(__file__).parent
        version_file = app_dir / "version.json"

        # Khởi tạo UpdateManager
        update_manager = UpdateManager(version_file=str(version_file))
        
        # Kiểm tra xem có update đã download sẵn không
        log.info("[Update] Kiểm tra cập nhật đã tải sẵn...")
        if update_manager.has_update_ready():
            log.info("[Update] Có cập nhật đã tải sẵn, đang cài đặt...")
            success = update_manager.apply_update_on_exit(app_dir=str(app_dir))
            if success:
                log.info("[Update] Cài đặt cập nhật thành công")
                if update_manager.latest_version:
                    log.info(f"[Update] Phiên bản mới: {update_manager.latest_version}")
                return 0
            else:
                log.error("[Update] Cài đặt cập nhật thất bại")
                return 1
        
        # Nếu chưa có update sẵn, kiểm tra và tải mới
        log.info("[Update] Không có update sẵn, đang kiểm tra GitHub...")
        update_info = update_manager.check_update()
        
        if not update_info:
            log.info("[Update] Không có cập nhật mới.")
            return 0
        
        latest_version = update_info.get("version", "unknown")
        log.info(f"[Update] Phát hiện phiên bản mới: {latest_version}")
        log.info("[Update] Đang tải cập nhật...")
        
        # Tải update với progress callback
        def progress_callback(percent):
            if percent % 25 == 0 or percent == 100:  # Chỉ log mỗi 25% hoặc khi xong
                log.info(f"Tiến độ tải: {percent}%")
        
        download_url = update_info.get("download_url")
        if not download_url:
            log.error("Không tìm thấy URL tải về.")
            return 1
        
        zip_path = update_manager.download_update(download_url, progress_callback)
        
        if not zip_path:
            log.error("[Update] Tải cập nhật thất bại")
            return 1
        
        log.info("[Update] Đã tải cập nhật, bắt đầu cài đặt...")
        
        # Cài đặt update
        success = update_manager.install_update(zip_path, app_dir=str(app_dir))
        
        if success:
            log.info("[Update] Cài đặt cập nhật thành công")
            log.info(f"[Update] Phiên bản mới: {latest_version}")
            return 0
        else:
            log.error("[Update] Cài đặt cập nhật thất bại")
            return 1
            
    except Exception as exc:
        log.error("[Update] Lỗi không mong đợi")
        log.error(f"[Update] Chi tiết: {exc}")
        import traceback
        log.error(traceback.format_exc())
        return 1


if __name__ == "__main__":
    sys.exit(main())

