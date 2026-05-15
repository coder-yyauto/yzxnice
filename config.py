import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()


class Config:
    SECRET_KEY = os.getenv("SECRET_KEY", "")
    if not SECRET_KEY:
        raise RuntimeError("SECRET_KEY 环境变量未设置，请设置后启动应用")
    DATABASE_URL = os.getenv("DATABASE_URL", "duckdb:///data/yzxnice.duckdb")
    SESSION_EXPIRE_HOURS = int(os.getenv("SESSION_EXPIRE_HOURS", "24"))
    DEFAULT_PASSWORD = os.getenv("DEFAULT_PASSWORD", "")
    if not DEFAULT_PASSWORD:
        raise RuntimeError("DEFAULT_PASSWORD 环境变量未设置，请设置后启动应用")
    APP_TITLE = os.getenv("APP_TITLE", "教学模拟平台")
    UPLOAD_DIR = os.getenv("UPLOAD_DIR", "static/uploads")
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024
    
    @property
    def absolute_upload_dir(self):
        """返回绝对路径的上传目录"""
        if os.path.isabs(self.UPLOAD_DIR):
            return self.UPLOAD_DIR
        # 相对于项目根目录
        base_dir = Path(__file__).parent
        return str(base_dir / self.UPLOAD_DIR)


config = Config()
