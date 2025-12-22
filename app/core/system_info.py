"""
Module lấy thông tin hệ thống: thiết bị, IP, hostname, v.v.
"""

import platform
import socket
from typing import Dict, Optional
import requests


def get_system_info() -> Dict[str, Optional[str]]:
    """
    Lấy thông tin hệ thống: thiết bị, IP, hostname, OS.
    
    Returns:
        Dictionary chứa thông tin hệ thống
    """
    info = {
        'hostname': None,
        'ip_address': None,
        'mac_address': None,
        'os_name': None,
        'os_version': None,
        'machine': None,
        'processor': None,
        'username': None,
    }
    
    try:
        # Hostname
        info['hostname'] = socket.gethostname()
    except Exception:
        pass
    
    try:
        # IP Public trước, fallback local
        try:
            resp = requests.get("https://api.ipify.org", timeout=3)
            if resp.status_code == 200:
                info["ip_address"] = resp.text.strip()
        except Exception:
            pass

        # IP Address (lấy IP local) nếu chưa có
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        try:
            # Không cần kết nối thực sự, chỉ để lấy IP local
            s.connect(('8.8.8.8', 80))
            if not info.get("ip_address"):
                info['ip_address'] = s.getsockname()[0]
        except Exception:
            # Fallback: lấy IP từ hostname
            try:
                if not info.get("ip_address"):
                    info['ip_address'] = socket.gethostbyname(socket.gethostname())
            except Exception:
                pass
        finally:
            s.close()
    except Exception:
        pass
    
    try:
        # MAC Address (lấy MAC đầu tiên)
        import uuid
        mac = uuid.getnode()
        info['mac_address'] = ':'.join(['{:02x}'.format((mac >> elements) & 0xff) 
                                        for elements in range(0, 2*6, 2)][::-1])
    except Exception:
        pass
    
    try:
        # OS Information
        info['os_name'] = platform.system()
        info['os_version'] = platform.version()
        info['machine'] = platform.machine()
        info['processor'] = platform.processor()
    except Exception:
        pass
    
    try:
        # Username
        import getpass
        info['username'] = getpass.getuser()
    except Exception:
        pass
    
    return info


def get_device_name() -> str:
    """
    Lấy tên thiết bị (hostname + username nếu có).
    
    Returns:
        Tên thiết bị
    """
    info = get_system_info()
    parts = []
    
    if info.get('hostname'):
        parts.append(info['hostname'])
    
    if info.get('username'):
        parts.append(f"({info['username']})")
    
    return ' '.join(parts) if parts else 'Unknown'


def get_ip_address() -> Optional[str]:
    """
    Lấy địa chỉ IP của thiết bị.
    
    Returns:
        Địa chỉ IP hoặc None
    """
    info = get_system_info()
    return info.get('ip_address')

