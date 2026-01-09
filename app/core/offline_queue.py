"""
Module quản lý hàng đợi offline cho log tra cứu.

Khi database không khả dụng, log tra cứu sẽ được lưu vào file JSON local.
Khi database kết nối lại thành công, các log pending sẽ được đồng bộ lên database.
"""

import json
import os
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any, Optional
from threading import Lock

from core.logging_utils import log, log_success, log_info


class OfflineQueue:
    """
    Quản lý hàng đợi offline cho log tra cứu.
    
    Thiết kế:
    - Sử dụng JSON file để lưu trữ (đơn giản, dễ debug)
    - Thread-safe với Lock
    - Tự động tạo thư mục nếu chưa tồn tại
    """
    
    _instance = None
    _lock = Lock()
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
        
        # Xác định đường dẫn file queue
        app_dir = Path(__file__).parent.parent  # app/
        self._data_dir = app_dir / "data"
        self._queue_file = self._data_dir / "offline_queue.json"
        
        # Đảm bảo thư mục data tồn tại
        self._data_dir.mkdir(parents=True, exist_ok=True)
        
        # Khởi tạo file nếu chưa tồn tại
        if not self._queue_file.exists():
            self._save_queue([])
        
        self._initialized = True
    
    def _load_queue(self) -> List[Dict[str, Any]]:
        """Load queue từ file JSON."""
        try:
            with open(self._queue_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except (json.JSONDecodeError, FileNotFoundError):
            return []
    
    def _save_queue(self, queue: List[Dict[str, Any]]) -> bool:
        """Lưu queue vào file JSON."""
        try:
            with open(self._queue_file, 'w', encoding='utf-8') as f:
                json.dump(queue, f, ensure_ascii=False, indent=2, default=str)
            return True
        except Exception as e:
            log.error("  ✗ Lỗi khi lưu offline queue: %s", e)
            return False
    
    def add(self, record: Dict[str, Any]) -> bool:
        """
        Thêm một record vào hàng đợi offline.
        
        Args:
            record: Dict chứa thông tin tra cứu cần lưu
            
        Returns:
            True nếu thêm thành công, False nếu có lỗi
        """
        with self._lock:
            try:
                queue = self._load_queue()
                
                # Thêm timestamp nếu chưa có
                if 'queued_at' not in record:
                    record['queued_at'] = datetime.now().isoformat()
                
                queue.append(record)
                
                if self._save_queue(queue):
                    log.debug("  📥 Đã lưu log tra cứu vào hàng đợi offline (%d pending)", len(queue))
                    return True
                return False
                
            except Exception as e:
                log.error("  ✗ Lỗi khi thêm vào offline queue: %s", e)
                return False
    
    def get_all(self) -> List[Dict[str, Any]]:
        """Lấy tất cả records trong queue."""
        with self._lock:
            return self._load_queue()
    
    def count(self) -> int:
        """Đếm số lượng records trong queue."""
        return len(self.get_all())
    
    def clear(self) -> bool:
        """Xóa toàn bộ queue."""
        with self._lock:
            return self._save_queue([])
    
    def remove_synced(self, count: int) -> bool:
        """
        Xóa các records đã được đồng bộ thành công.
        
        Args:
            count: Số lượng records đã đồng bộ (từ đầu queue)
            
        Returns:
            True nếu xóa thành công
        """
        with self._lock:
            try:
                queue = self._load_queue()
                remaining = queue[count:]  # Giữ lại các records chưa đồng bộ
                return self._save_queue(remaining)
            except Exception as e:
                log.error("  ✗ Lỗi khi xóa records đã đồng bộ: %s", e)
                return False
    
    def has_pending(self) -> bool:
        """Kiểm tra có records đang chờ đồng bộ không."""
        return self.count() > 0
    
    def get_queue_file_path(self) -> str:
        """Lấy đường dẫn file queue."""
        return str(self._queue_file)


# Singleton instance
offline_queue = OfflineQueue()
