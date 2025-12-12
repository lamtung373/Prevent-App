"""
Config module - Load configuration và credentials từ .env file.
"""

import os
from pathlib import Path
from typing import Optional


class Config:
    """Quản lý cấu hình và credentials từ .env file."""
    
    _instance = None
    _initialized = False
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        if not self._initialized:
            self._load_env()
            Config._initialized = True
    
    def _load_env(self):
        """Load .env file từ thư mục gốc project."""
        try:
            # Tìm thư mục gốc (cùng cấp với app/)
            current_file = Path(__file__)
            root_dir = current_file.parent.parent.parent
            env_file = root_dir / ".env"
            
            if env_file.exists():
                with open(env_file, "r", encoding="utf-8") as f:
                    for line in f:
                        line = line.strip()
                        # Bỏ qua comment và dòng trống
                        if not line or line.startswith("#"):
                            continue
                        # Parse key=value
                        if "=" in line:
                            key, value = line.split("=", 1)
                            key = key.strip()
                            value = value.strip().strip('"').strip("'")
                            # Set vào environment variables
                            if key and value:
                                os.environ[key] = value
        except Exception:
            # Nếu không load được .env, sử dụng environment variables có sẵn
            pass
    
    def _get_env(self, key: str, default: Optional[str] = None) -> Optional[str]:
        """Lấy giá trị từ environment variable."""
        return os.getenv(key, default)
    
    # Site 1 - Preventlistview
    @property
    def site1_username(self) -> str:
        """Username cho site 1 (preventlistview)."""
        return self._get_env("SITE1_USERNAME", "xxxxxxxxxxxxxx")
    
    @property
    def site1_password(self) -> str:
        """Password cho site 1 (preventlistview)."""
        return self._get_env("SITE1_PASSWORD", "xxxxxxxxxxxxxx")
    
    @property
    def site1_base_url(self) -> str:
        """Base URL cho site 1."""
        return "http://115.79.139.172:8080/stp"
    
    @property
    def site1_search_url(self) -> str:
        """Search URL cho site 1."""
        return f"{self.site1_base_url}/preventlistview.do"
    
    @property
    def site1_selectors(self) -> dict:
        """Selectors cho site 1."""
        return {
            "username": "name=userName",
            "password": "name=password",
            "login_button": "#btnLogin",
            "search": "input[name='keySearch'], input#keySearch",
            "submit": "//input[@type='image' and contains(@src, 'btn_search.png')]",
        }
    
    # Site 2 - 210.245.111.1/dsnc
    @property
    def site2_username(self) -> str:
        """Username cho site 2."""
        return self._get_env("SITE2_USERNAME", "xxxxxxxxxxxxxx")
    
    @property
    def site2_password(self) -> str:
        """Password cho site 2."""
        return self._get_env("SITE2_PASSWORD", "xxxxxxxxxxxxxx")
    
    @property
    def site2_base_url(self) -> str:
        """Base URL cho site 2."""
        return "http://210.245.111.1/dsnc/Default.aspx"
    
    @property
    def site2_selectors(self) -> dict:
        """Selectors cho site 2."""
        return {
            "username": "#Login1_UserName",
            "password": "#Login1_Password",
            "login_button": "#Login1_LoginButton",
        }
    
    # Site 3 - hcm.cenm.vn (Trang 3)
    @property
    def site3_username(self) -> str:
        """Username cho site 3 (hcm.cenm.vn)."""
        return self._get_env("SITE3_USERNAME", "xxxxxxxxxxxxxx")
    
    @property
    def site3_password(self) -> str:
        """Password cho site 3 (hcm.cenm.vn)."""
        return self._get_env("SITE3_PASSWORD", "xxxxxxxxxxxxxx")
    
    @property
    def site3_base_url(self) -> str:
        """Base URL cho site 3 (hcm.cenm.vn)."""
        return "https://hcm.cenm.vn/"
    
    # Site 4 - 14.161.50.224 (Trang 4)
    @property
    def site4_username(self) -> str:
        """Username cho site 4 (14.161.50.224)."""
        return self._get_env("SITE4_USERNAME", "xxxxxxxxxxxxxx")
    
    @property
    def site4_password(self) -> str:
        """Password cho site 4 (14.161.50.224)."""
        return self._get_env("SITE4_PASSWORD", "xxxxxxxxxxxxxx")
    
    @property
    def site4_base_url(self) -> str:
        """Base URL cho site 4 (14.161.50.224)."""
        return "http://14.161.50.224/dang-nhap/"
    
    @property
    def site4_selectors(self) -> dict:
        """Selectors cho site 4 (14.161.50.224)."""
        return {
            "username": "input[name='login_username']",
            "password": "input[name='login_password']",
            "login_button": "button[type='submit']",
        }


# Singleton instance
config = Config()

