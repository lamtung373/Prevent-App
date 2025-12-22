"""
Update Manager - Tự động kiểm tra và cài đặt cập nhật từ GitHub
Chạy trong background, không block UI
"""

import json
import logging
import os
import shutil
import stat
import tempfile
import threading
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Callable, Optional
from zipfile import ZipFile

import requests

# Setup logger cho update manager
_update_logger = logging.getLogger("update_manager")
if not _update_logger.handlers:
    handler = logging.StreamHandler()
    handler.setFormatter(logging.Formatter("[Update] %(message)s"))
    _update_logger.addHandler(handler)
    _update_logger.setLevel(logging.INFO)
    _update_logger.propagate = False


class UpdateManager:
    """Quản lý cập nhật tự động từ GitHub Releases."""

    def __init__(self, version_file: str = "app/version.json", callback: Optional[Callable] = None):
        """
        Khởi tạo UpdateManager.

        Args:
            version_file: Đường dẫn đến file version.json
            callback: Hàm callback để cập nhật UI (status, progress)
        """
        self.version_file = Path(version_file)
        self.callback = callback
        self.update_ready = False
        self.update_zip_path = None
        self.latest_version = None
        self.download_progress = 0
        self._lock = threading.Lock()
        self._logger = _update_logger

    def load_version_info(self) -> dict:
        """Đọc thông tin version hiện tại."""
        try:
            if self.version_file.exists():
                with open(self.version_file, "r", encoding="utf-8") as f:
                    return json.load(f)
        except Exception:
            pass
        return {"version": "1.0.0", "github_repo": "", "last_check": None}

    def save_version_info(self, info: dict):
        """Lưu thông tin version."""
        try:
            self.version_file.parent.mkdir(parents=True, exist_ok=True)
            with open(self.version_file, "w", encoding="utf-8") as f:
                json.dump(info, f, indent=2, ensure_ascii=False)
        except Exception:
            pass

    def compare_versions(self, current: str, latest: str) -> bool:
        """
        So sánh version, trả về True nếu latest > current.

        Args:
            current: Version hiện tại (ví dụ: "1.0.0" hoặc "v1.0.0")
            latest: Version mới nhất (ví dụ: "1.0.1" hoặc "v1.0.1")
        """
        # Bỏ prefix "v" nếu có
        current = current.lstrip("vV")
        latest = latest.lstrip("vV")

        try:
            current_parts = [int(x) for x in current.split(".")]
            latest_parts = [int(x) for x in latest.split(".")]

            # Đảm bảo cùng độ dài
            max_len = max(len(current_parts), len(latest_parts))
            current_parts.extend([0] * (max_len - len(current_parts)))
            latest_parts.extend([0] * (max_len - len(latest_parts)))

            for c, l in zip(current_parts, latest_parts):
                if l > c:
                    return True
                if l < c:
                    return False
            return False
        except Exception:
            return False

    def _get_latest_version_silent(self) -> Optional[str]:
        """
        Lấy version mới nhất từ GitHub mà không log (dùng cho internal).
        
        Returns:
            Version string nếu thành công, None nếu lỗi
        """
        try:
            version_info = self.load_version_info()
            github_repo = version_info.get("github_repo", "").strip()

            if not github_repo or github_repo == "owner/repo-name":
                return None

            try:
                api_url = f"https://api.github.com/repos/{github_repo}/releases/latest"
                response = requests.get(api_url, timeout=10)

                if response.status_code == 200:
                    release_data = response.json()
                    tag_name = release_data.get("tag_name", "")
                    return tag_name.lstrip("vV") if tag_name else None
            except Exception:
                pass
        except Exception:
            pass
        return None

    def check_update(self) -> Optional[dict]:
        """
        Kiểm tra update từ GitHub Releases API.

        Returns:
            Dict chứa thông tin release mới nhất nếu có, None nếu không có hoặc lỗi
        """
        try:
            self._logger.info("Đang kiểm tra cập nhật...")
            version_info = self.load_version_info()
            github_repo = version_info.get("github_repo", "").strip()
            current_version = version_info.get("version", "1.0.0")

            if not github_repo or github_repo == "owner/repo-name":
                self._logger.warning("GitHub repo chưa được cấu hình trong version.json")
                return None

            try:
                # Gọi GitHub API với timeout 10 giây
                api_url = f"https://api.github.com/repos/{github_repo}/releases/latest"
                response = requests.get(api_url, timeout=10)

                if response.status_code == 200:
                    release_data = response.json()
                    tag_name = release_data.get("tag_name", "")

                    # So sánh version
                    is_newer = self.compare_versions(current_version, tag_name)
                    
                    if is_newer:
                        assets = release_data.get("assets", [])
                        zip_asset = None
                        for asset in assets:
                            asset_name = asset.get("name", "")
                            if asset_name.endswith(".zip"):
                                zip_asset = asset
                                break

                        if zip_asset:
                            asset_id = zip_asset.get("id")
                            download_url = zip_asset.get("browser_download_url")
                            
                            self._logger.info(f"Phát hiện phiên bản mới: {tag_name}")
                            return {
                                "version": tag_name,
                                "download_url": download_url,
                                "asset_id": asset_id,
                                "asset_name": zip_asset.get("name", ""),
                                "changelog": release_data.get("body", ""),
                                "release_date": release_data.get("published_at", ""),
                            }
                        else:
                            self._logger.warning("Không tìm thấy file .zip trong assets")
                    else:
                        self._logger.info("Đã ở phiên bản mới nhất")
                elif response.status_code == 404:
                    self._logger.error("Repo không tồn tại hoặc không có releases (404)")
                    return None
                elif response.status_code == 401:
                    self._logger.error("Unauthorized (401) - Không có quyền truy cập")
                    return None
                elif response.status_code == 403:
                    self._logger.error("Forbidden (403) - Không có quyền truy cập hoặc rate limit")
                    return None
                else:
                    self._logger.error(f"Lỗi API: Status {response.status_code}, Response: {response.text[:200]}")
            except requests.Timeout:
                self._logger.error("Timeout khi gọi GitHub API")
                return None
            except requests.RequestException as e:
                self._logger.error(f"Lỗi network khi gọi GitHub API: {e}")
                return None
            except (KeyError, ValueError, TypeError) as e:
                self._logger.error(f"Lỗi parse response từ GitHub API: {e}")
                return None
        except Exception as e:
            self._logger.error(f"Lỗi không mong đợi khi check update: {e}", exc_info=True)
            return None

        return None

    def download_update(self, download_url: str, progress_callback: Optional[Callable] = None) -> Optional[str]:
        """
        Tải file update về và lưu trong thư mục dự án.

        Args:
            download_url: URL để tải file zip
            progress_callback: Callback để cập nhật progress (percent)

        Returns:
            Đường dẫn đến file zip đã tải, None nếu lỗi
        """
        try:
            self._logger.info("Bắt đầu tải cập nhật")
            
            app_dir = self.version_file.parent
            root_dir = app_dir.parent
            updates_dir = root_dir / "_updates"
            updates_dir.mkdir(parents=True, exist_ok=True)
            
            try:
                zip_files = sorted(updates_dir.glob("update_*.zip"), key=lambda p: p.stat().st_mtime, reverse=True)
                if len(zip_files) > 3:
                    for old_zip in zip_files[3:]:
                        try:
                            old_zip.unlink()
                        except Exception:
                            pass
            except Exception:
                pass
            
            zip_path = updates_dir / f"update_{int(time.time())}.zip"

            # Tải file với progress
            response = requests.get(download_url, stream=True, timeout=60)
            
            if response.status_code != 200:
                self._logger.error(f"Lỗi tải file: HTTP {response.status_code}")
                if response.text:
                    self._logger.error(f"Nội dung lỗi: {response.text[:200]}")
            
            response.raise_for_status()

            total_size = int(response.headers.get("content-length", 0))
            downloaded = 0

            with open(zip_path, "wb") as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
                        downloaded += len(chunk)
                        if total_size > 0 and progress_callback:
                            progress = int((downloaded / total_size) * 100)
                            progress_callback(progress)
                        elif total_size == 0 and progress_callback:
                            progress_callback(0)

            self._logger.info("Tải cập nhật thành công")
            return str(zip_path)
        except requests.RequestException as e:
            self._logger.error(f"Lỗi khi tải file: {e}")
            return None
        except Exception as e:
            self._logger.error(f"Lỗi không mong đợi khi tải file: {e}", exc_info=True)
            return None

    def install_update(self, zip_path: str, app_dir: str = "app") -> bool:
        """
        Cài đặt update từ file zip. Hỗ trợ update cả thư mục app/ và các file/thư mục root.

        Args:
            zip_path: Đường dẫn đến file zip
            app_dir: Thư mục app cần update (dùng để xác định root)

        Returns:
            True nếu thành công, False nếu lỗi
        """
        app_path = Path(app_dir)
        root_dir = app_path.parent
        backup_root = root_dir / "update_backup"

        # Dùng chung handler để xóa file/dir readonly (tránh lỗi PermissionError trên Windows)
        def handle_remove_readonly(func, path, exc):
            """Xử lý readonly files khi xóa."""
            try:
                os.chmod(path, stat.S_IWRITE)
                func(path)
            except Exception:
                pass

        try:
            self._logger.info("Đang cài đặt cập nhật")
            
            if backup_root.exists():
                shutil.rmtree(backup_root, onerror=handle_remove_readonly)
            backup_root.mkdir(parents=True, exist_ok=True)

            if app_path.exists():
                shutil.copytree(app_path, backup_root / app_path.name)

            with ZipFile(zip_path, "r") as zip_ref:
                members = zip_ref.namelist()

                top_levels: set[str] = set()
                for m in members:
                    if not m or m.endswith("/"):
                        continue
                    part = m.replace("\\", "/").split("/")[0]
                    if part and part not in {"app", "__MACOSX", backup_root.name}:
                        top_levels.add(part)

                for comp in top_levels:
                    target = root_dir / comp
                    backup_target = backup_root / comp
                    if target.exists():
                        if target.is_dir():
                            shutil.copytree(target, backup_target)
                        else:
                            backup_target.parent.mkdir(parents=True, exist_ok=True)
                            shutil.copy2(target, backup_target)

                zip_ref.extractall(root_dir)

            version_info = self.load_version_info()
            if self.latest_version:
                old_version = version_info.get("version", "unknown")
                new_version = self.latest_version.lstrip("vV")
                # Chỉ log khi có thay đổi phiên bản thực sự
                if old_version != new_version:
                    version_info["version"] = new_version
                    self.save_version_info(version_info)
                    self._logger.info(f"Cập nhật phiên bản: {old_version} -> {new_version}")
                else:
                    # Vẫn cập nhật version_info để đảm bảo đồng bộ, nhưng không log
                    version_info["version"] = new_version
                    self.save_version_info(version_info)

            if backup_root.exists():
                try:
                    shutil.rmtree(backup_root, onerror=handle_remove_readonly)
                except Exception as e:
                    self._logger.warning(f"Không thể xóa backup (có thể do file đang được sử dụng): {e}")
                    self._logger.warning("Backup sẽ được giữ lại tại: %s", backup_root)

            zip_file = Path(zip_path)
            if zip_file.exists():
                try:
                    zip_file.unlink()
                except Exception as e:
                    self._logger.warning(f"Không thể xóa file update: {e}")

            self._logger.info("Cài đặt cập nhật thành công")
            return True
        except Exception as e:
            self._logger.error(f"Lỗi khi cài đặt update: {e}", exc_info=True)
            # Rollback từ backup nếu lỗi
            try:
                if backup_root.exists():
                    # Khôi phục app
                    app_backup = backup_root / app_path.name
                    if app_backup.exists():
                        if app_path.exists():
                            try:
                                shutil.rmtree(app_path, onerror=handle_remove_readonly)
                            except Exception as rm_error:
                                self._logger.warning(f"Không thể xóa app cũ: {rm_error}, thử copy đè...")
                        try:
                            shutil.copytree(app_backup, app_path)
                            self._logger.info("Đã khôi phục thư mục app")
                        except Exception as copy_error:
                            self._logger.error(f"Không thể khôi phục app: {copy_error}")

                    for item in backup_root.iterdir():
                        if item.name in {app_path.name}:
                            continue
                        target = root_dir / item.name
                        try:
                            if target.exists():
                                if target.is_dir():
                                    try:
                                        shutil.rmtree(target, onerror=handle_remove_readonly)
                                    except Exception:
                                        pass
                                else:
                                    try:
                                        target.unlink()
                                    except Exception:
                                        pass
                            
                            if item.is_dir():
                                shutil.copytree(item, target)
                            else:
                                target.parent.mkdir(parents=True, exist_ok=True)
                                shutil.copy2(item, target)
                            self._logger.info(f"Đã khôi phục {item.name}")
                        except Exception as restore_error:
                            self._logger.warning(f"Không thể khôi phục {item.name}: {restore_error}")
                
                self._logger.info("Rollback hoàn tất")
            except Exception as rollback_error:
                self._logger.error(f"Lỗi nghiêm trọng khi rollback: {rollback_error}", exc_info=True)
            return False

    def check_and_download_update(self):
        """Kiểm tra và tải update trong background thread."""
        try:
            self._logger.info("Kiểm tra cập nhật nền")
            update_info = self.check_update()
            if update_info:
                self.latest_version = update_info["version"]
                # Không log lại vì check_update() đã log rồi
                if self.callback:
                    self.callback("downloading", 0, f"Đang tải cập nhật {self.latest_version}...")

                def progress_cb(percent):
                    if self.callback:
                        self.callback("downloading", percent, f"Đang tải cập nhật {self.latest_version}... {percent}%")

                try:
                    zip_path = self.download_update(update_info["download_url"], progress_cb)

                    if zip_path:
                        with self._lock:
                            self.update_zip_path = zip_path
                            self.update_ready = True
                        # Chỉ log một lần, không log từ callback để tránh trùng lặp
                        self._logger.info(f"Cập nhật {self.latest_version} sẵn sàng")
                        if self.callback:
                            self.callback("ready", 100, f"Cập nhật {self.latest_version} sẵn sàng")
                    else:
                        self._logger.error("Tải cập nhật thất bại")
                        if self.callback:
                            self.callback("error", 0, "Tải cập nhật thất bại")
                except Exception as e:
                    self._logger.error(f"Lỗi khi download: {e}", exc_info=True)
                    if self.callback:
                        self.callback("error", 0, "Lỗi khi tải cập nhật")
            else:
                self._logger.info("Không có update mới")
        except Exception as e:
            self._logger.error(f"Lỗi khi check update: {e}", exc_info=True)

    def start_background_check(self, delay: float = 3.0):
        """
        Bắt đầu kiểm tra update trong background sau delay giây.

        Args:
            delay: Số giây chờ trước khi bắt đầu check
        """
        def check_thread():
            time.sleep(delay)
            self.check_and_download_update()

        thread = threading.Thread(target=check_thread, daemon=True)
        thread.start()

    def has_update_ready(self) -> bool:
        """Kiểm tra xem có update sẵn sàng để cài đặt không."""
        with self._lock:
            # Kiểm tra state trong memory trước
            if self.update_ready and self.update_zip_path is not None:
                return True
            
            # Nếu không có trong memory, kiểm tra file zip trong _updates folder
            try:
                app_dir = self.version_file.parent
                root_dir = app_dir.parent
                updates_dir = root_dir / "_updates"
                
                if updates_dir.exists():
                    # Tìm file zip mới nhất
                    zip_files = list(updates_dir.glob("update_*.zip"))
                    if zip_files:
                        # Sắp xếp theo thời gian tạo (mới nhất trước)
                        zip_files.sort(key=lambda p: p.stat().st_mtime, reverse=True)
                        latest_zip = zip_files[0]
                        
                        # Kiểm tra xem file có hợp lệ không (ít nhất 1KB)
                        if latest_zip.stat().st_size > 1024:
                            self._logger.info(f"Tìm thấy file update trong _updates/: {latest_zip.name}")
                            # Set state để có thể apply
                            self.update_zip_path = str(latest_zip)
                            self.update_ready = True
                            
                            # Lấy version từ GitHub nếu chưa có (không log để tránh trùng lặp)
                            if not self.latest_version:
                                try:
                                    # Dùng method silent để lấy version mà không log
                                    version = self._get_latest_version_silent()
                                    if version:
                                        self.latest_version = version
                                except Exception as e:
                                    self._logger.debug(f"Không thể lấy version từ GitHub: {e}")
                            
                            return True
            except Exception as e:
                self._logger.debug(f"Không thể kiểm tra _updates folder: {e}")
            
            return False

    def apply_update_on_exit(self, app_dir: str = "app") -> bool:
        """
        Áp dụng update khi đóng app.

        Args:
            app_dir: Thư mục app cần update

        Returns:
            True nếu thành công, False nếu lỗi
        """
        if not self.has_update_ready():
            return False

        with self._lock:
            zip_path = self.update_zip_path

        if zip_path and Path(zip_path).exists():
            return self.install_update(zip_path, app_dir)
        return False

